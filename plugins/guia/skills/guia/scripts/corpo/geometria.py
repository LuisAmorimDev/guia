"""Peças de papel recortado: contornos 2D, malhas planas e materiais.

Corre dentro do Blender (bpy). Convenção do rig: a personagem vive no plano XZ,
a câmara ortográfica olha ao longo de +Y; quanto maior a `camada`, mais perto
da câmara (y mais negativo).
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix

PROFUNDIDADE_CAMADA = 0.01
SOMBRA_DESVIO = (0.014, -0.016)


def camada_y(camada):
    return -camada * PROFUNDIDADE_CAMADA


def hex_linear(hex_cor):
    h = hex_cor.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


# ---------- contornos (listas de (x, z)) ----------

def tremer(pontos, amplitude, seed):
    """Irregularidade de tesoura: desvia cada vértice um pouco, de forma reprodutível."""
    rnd = random.Random(seed)
    return [(x + rnd.uniform(-amplitude, amplitude), z + rnd.uniform(-amplitude, amplitude))
            for x, z in pontos]


def elipse(cx, cz, rx, rz, n=36, a0=0.0, a1=360.0):
    pts = []
    passos = n if a1 - a0 >= 360 else n + 1
    for i in range(passos):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((cx + rx * math.cos(a), cz + rz * math.sin(a)))
    return pts


def arco_grosso(cx, cz, r, espessura, a0, a1, n=14):
    """Arco com espessura (olhos fechados, sorrisos finos)."""
    fora = elipse(cx, cz, r + espessura / 2, r + espessura / 2, n, a0, a1)
    dentro = elipse(cx, cz, r - espessura / 2, r - espessura / 2, n, a0, a1)
    return fora + list(reversed(dentro))


def capsula(p0, p1, r0, r1, n=10):
    """Membro afunilado de p0 (raio r0) até p1 (raio r1)."""
    (x0, z0), (x1, z1) = p0, p1
    ang = math.degrees(math.atan2(z1 - z0, x1 - x0))
    pts = elipse(x1, z1, r1, r1, n, ang - 90, ang + 90)
    pts += elipse(x0, z0, r0, r0, n, ang + 90, ang + 270)
    return pts


def retangulo_arredondado(cx, cz, largura, altura, raio, n=5):
    hx, hz = largura / 2 - raio, altura / 2 - raio
    pts = []
    for (sx, sz, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        pts += elipse(cx + sx * hx, cz + sz * hz, raio, raio, n, a0, a0 + 90)
    return pts


# ---------- materiais ----------

def _saida_emissao(mat, cor_socket_de, alpha=1.0):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    emis = nodes.new("ShaderNodeEmission")
    links.new(cor_socket_de, emis.inputs["Color"])
    out = nodes.new("ShaderNodeOutputMaterial")
    if alpha < 1.0:
        transp = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = alpha
        links.new(transp.outputs[0], mix.inputs[1])
        links.new(emis.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs["Surface"])
        mat.surface_render_method = "BLENDED"
    else:
        links.new(emis.outputs[0], out.inputs["Surface"])


def _grao(mat, cor_socket, intensidade):
    """Multiplica a cor por um ruído fino: o grão do papel."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    coord = nodes.new("ShaderNodeTexCoord")
    ruido = nodes.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = 90.0
    ruido.inputs["Detail"].default_value = 6.0
    links.new(coord.outputs["Object"], ruido.inputs["Vector"])
    faixa = nodes.new("ShaderNodeMapRange")
    faixa.inputs["To Min"].default_value = 1.0 - intensidade
    faixa.inputs["To Max"].default_value = 1.0
    links.new(ruido.outputs["Fac"], faixa.inputs["Value"])
    mult = nodes.new("ShaderNodeMix")
    mult.data_type = "RGBA"
    mult.blend_type = "MULTIPLY"
    mult.inputs["Factor"].default_value = 1.0
    links.new(cor_socket, mult.inputs["A"])
    links.new(faixa.outputs["Result"], mult.inputs["B"])
    return mult.outputs["Result"]


def material_papel(nome, cor_hex, grao=0.06):
    mat = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    rgb = mat.node_tree.nodes.new("ShaderNodeRGB")
    rgb.name = "cor"
    rgb.outputs[0].default_value = hex_linear(cor_hex)
    _saida_emissao(mat, _grao(mat, rgb.outputs[0], grao))
    return mat


def material_sombra():
    nome = "Papel.Sombra"
    mat = bpy.data.materials.get(nome)
    if mat:
        return mat
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    rgb = mat.node_tree.nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = hex_linear("#1b2430")
    _saida_emissao(mat, rgb.outputs[0], alpha=0.2)
    return mat


def material_roupa(nome):
    """Material de roupa com parâmetros expostos em nós com nome:
    `cor`, `cor_padrao` (RGB), `padrao` (0 liso, 1 riscas, 2 xadrez, 3 bolinhas), `escala`."""
    mat = bpy.data.materials.get(nome) or bpy.data.materials.new(nome)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    n, l = nt.nodes, nt.links

    cor = n.new("ShaderNodeRGB"); cor.name = "cor"
    cor_p = n.new("ShaderNodeRGB"); cor_p.name = "cor_padrao"
    padrao = n.new("ShaderNodeValue"); padrao.name = "padrao"
    escala = n.new("ShaderNodeValue"); escala.name = "escala"
    cor.outputs[0].default_value = hex_linear("#263b8f")
    cor_p.outputs[0].default_value = hex_linear("#fffdf7")
    padrao.outputs[0].default_value = 0.0
    escala.outputs[0].default_value = 10.0

    coord = n.new("ShaderNodeTexCoord")
    vec = n.new("ShaderNodeVectorMath"); vec.operation = "SCALE"
    l.new(coord.outputs["Object"], vec.inputs[0])
    l.new(escala.outputs[0], vec.inputs["Scale"])

    sep = n.new("ShaderNodeSeparateXYZ")
    l.new(vec.outputs[0], sep.inputs[0])
    riscas = n.new("ShaderNodeMath"); riscas.operation = "PINGPONG"
    riscas.inputs[1].default_value = 0.5
    l.new(sep.outputs["Z"], riscas.inputs[0])
    riscas_s = n.new("ShaderNodeMath"); riscas_s.operation = "GREATER_THAN"
    riscas_s.inputs[1].default_value = 0.25
    l.new(riscas.outputs[0], riscas_s.inputs[0])

    xadrez = n.new("ShaderNodeTexChecker")
    xadrez.inputs["Scale"].default_value = 1.0
    xadrez.inputs["Color1"].default_value = (1, 1, 1, 1)
    xadrez.inputs["Color2"].default_value = (0, 0, 0, 1)
    l.new(vec.outputs[0], xadrez.inputs["Vector"])

    voro = n.new("ShaderNodeTexVoronoi")
    voro.inputs["Randomness"].default_value = 0.0
    l.new(vec.outputs[0], voro.inputs["Vector"])
    bolas = n.new("ShaderNodeMath"); bolas.operation = "LESS_THAN"
    bolas.inputs[1].default_value = 0.22
    l.new(voro.outputs["Distance"], bolas.inputs[0])

    total = None
    for indice, sock in ((1, riscas_s.outputs[0]), (2, xadrez.outputs["Fac"]), (3, bolas.outputs[0])):
        igual = n.new("ShaderNodeMath"); igual.operation = "COMPARE"
        igual.inputs[1].default_value = float(indice)
        igual.inputs[2].default_value = 0.1
        l.new(padrao.outputs[0], igual.inputs[0])
        mult = n.new("ShaderNodeMath"); mult.operation = "MULTIPLY"
        l.new(igual.outputs[0], mult.inputs[0])
        l.new(sock, mult.inputs[1])
        if total is None:
            total = mult.outputs[0]
        else:
            soma = n.new("ShaderNodeMath"); soma.operation = "ADD"
            l.new(total, soma.inputs[0]); l.new(mult.outputs[0], soma.inputs[1])
            total = soma.outputs[0]

    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"
    l.new(total, mix.inputs["Factor"])
    l.new(cor.outputs[0], mix.inputs["A"])
    l.new(cor_p.outputs[0], mix.inputs["B"])
    _saida_emissao(mat, _grao(mat, mix.outputs["Result"], 0.07))
    return mat


def aplicar_roupa(mat, cor, padrao="liso", cor_padrao=None, escala=10.0):
    padroes = {"liso": 0, "riscas": 1, "xadrez": 2, "bolinhas": 3}
    nodes = mat.node_tree.nodes
    nodes["cor"].outputs[0].default_value = hex_linear(cor)
    nodes["cor_padrao"].outputs[0].default_value = hex_linear(cor_padrao or cor)
    nodes["padrao"].outputs[0].default_value = float(padroes[padrao])
    nodes["escala"].outputs[0].default_value = float(escala)


# ---------- malhas ----------

def malha_plana(nome, pontos, camada, material, colecao, pivo=(0.0, 0.0)):
    """Cria um objeto plano com origem em `pivo` (coordenadas do mundo, plano XZ)."""
    me = bpy.data.meshes.new(nome)
    bm = bmesh.new()
    px, pz = pivo
    verts = [bm.verts.new((x - px, 0.0, z - pz)) for x, z in pontos]
    bm.faces.new(verts)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    ob = bpy.data.objects.new(nome, me)
    ob.location = (px, camada_y(camada), pz)
    colecao.objects.link(ob)
    return ob


def prender_ao_osso(ob, armadura, osso):
    """Parent ao osso mantendo a posição de repouso: a `location` do objeto
    continua em coordenadas do mundo (em repouso), o que facilita animá-lo."""
    b = armadura.data.bones[osso]
    p0 = armadura.matrix_world @ b.matrix_local @ Matrix.Translation((0.0, b.length, 0.0))
    ob.parent = armadura
    ob.parent_type = "BONE"
    ob.parent_bone = osso
    ob.matrix_parent_inverse = p0.inverted()


def peca(nome, pontos, camada, material, colecao, armadura, osso,
         pivo=(0.0, 0.0), sombra=True, seed=0, tremor=0.0035, **props):
    """Uma peça de papel: forma com tremor, sombra opcional por trás, presa a um osso."""
    pts = tremer(pontos, tremor, seed) if tremor else pontos
    ob = malha_plana(nome, pts, camada, material, colecao, pivo)
    for k, v in props.items():
        ob[k] = v
    prender_ao_osso(ob, armadura, osso)
    if sombra:
        dx, dz = SOMBRA_DESVIO
        sp = [(x + dx, z + dz) for x, z in pts]
        so = malha_plana(nome + ".sombra", sp, camada - 0.4, material_sombra(), colecao,
                         (pivo[0] + dx, pivo[1] + dz))
        for k, v in props.items():
            so[k] = v
        so["sombra_de"] = nome
        prender_ao_osso(so, armadura, osso)
    return ob

"""Constrói o rig 2D de papel recortado e guarda-o em .blend.

    blender -b --factory-startup -P construir_rig.py -- --personagem .guia/corpo/<nome> [--previa previa.png]

Ossos no plano XZ com o eixo Z local virado para a câmara: rodar `rotation_euler.z`
de um osso = rodar no plano do ecrã (positivo = sentido anti-horário).
`.L` é o lado esquerdo da personagem = lado direito do ecrã (x positivo).
"""
import argparse
import json
import math
import os
import sys
import zlib

import bpy
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import geometria as g  # noqa: E402

OSSOS = [  # nome, cabeça (x, z), cauda (x, z), pai
    ("root", (0, 0), (0, 0.2), None),
    ("hips", (0, 0.95), (0, 1.1), "root"),
    ("chest", (0, 1.1), (0, 1.55), "hips"),
    ("neck", (0, 1.55), (0, 1.68), "chest"),
    ("head", (0, 1.68), (0, 2.2), "neck"),
    ("upper_arm.L", (0.29, 1.5), (0.33, 1.17), "chest"),
    ("forearm.L", (0.33, 1.17), (0.355, 0.86), "upper_arm.L"),
    ("hand.L", (0.355, 0.86), (0.36, 0.74), "forearm.L"),
    ("encaixe.mao.L", (0.36, 0.8), (0.36, 0.7), "hand.L"),
    ("thigh.L", (0.12, 0.95), (0.125, 0.5), "hips"),
    ("shin.L", (0.125, 0.5), (0.13, 0.1), "thigh.L"),
]


def espelhar_ossos():
    extra = []
    for nome, h, t, pai in OSSOS:
        if nome.endswith(".L"):
            extra.append((nome[:-2] + ".R", (-h[0], h[1]), (-t[0], t[1]),
                          pai[:-2] + ".R" if pai and pai.endswith(".L") else pai))
    return OSSOS + extra


def limpar_cena():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)


def criar_armadura(colecao):
    arm_data = bpy.data.armatures.new("Colega.Rig")
    arm = bpy.data.objects.new("Colega.Rig", arm_data)
    colecao.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for nome, h, t, pai in espelhar_ossos():
        eb = arm_data.edit_bones.new(nome)
        eb.head = (h[0], 0.0, h[1])
        eb.tail = (t[0], 0.0, t[1])
        eb.align_roll(Vector((0.0, -1.0, 0.0)))
        if pai:
            eb.parent = arm_data.edit_bones[pai]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    return arm


def construir(vocab):
    cor = vocab["personagem"]
    limpar_cena()
    col = bpy.data.collections.new("Colega")
    bpy.context.scene.collection.children.link(col)
    arm = criar_armadura(col)

    pele = g.material_papel("Papel.Pele", cor["pele"])
    pele_s = g.material_papel("Papel.PeleSombra", cor["pele_sombra"])
    cabelo = g.material_papel("Papel.Cabelo", cor["cabelo"])
    tinta = g.material_papel("Papel.Tinta", cor["tinta"], grao=0.0)
    boca_m = g.material_papel("Papel.Boca", cor["boca"], grao=0.0)
    branco = g.material_papel("Papel.Branco", "#fffdf7", grao=0.0)
    bochecha = g.material_papel("Papel.Bochecha", cor["bochecha"], grao=0.0)
    camisola = g.material_roupa("Roupa.Camisola")
    calcas = g.material_roupa("Roupa.Calcas")
    sapatos = g.material_papel("Roupa.Sapatos", "#1b2430")
    roupa = vocab["roupas"]["casual_trabalho"]
    g.aplicar_roupa(camisola, **roupa["camisola"])
    g.aplicar_roupa(calcas, **roupa["calcas"])

    def p(nome, pts, camada, mat, osso, **kw):
        return g.peca(nome, pts, camada, mat, col, arm, osso, seed=zlib.crc32(nome.encode()), **kw)

    # cabeça e cabelo
    p("cabelo.tras", g.elipse(0, 2.02, 0.335, 0.345, 40), 0, cabelo, "head", pivo=(0, 2.02))
    for s, lado in ((1, "L"), (-1, "R")):
        p(f"orelha.{lado}", g.elipse(s * 0.295, 1.95, 0.05, 0.065, 16), 6.6, pele, "head",
          pivo=(s * 0.295, 1.95), sombra=False)
    p("cabeca", g.elipse(0, 1.98, 0.3, 0.32, 48), 7, pele, "head", pivo=(0, 1.98))
    p("nariz", g.arco_grosso(0, 1.935, 0.024, 0.012, 200, 340), 8, pele_s, "head",
      pivo=(0, 1.92), sombra=False, tremor=0)
    franja = g.elipse(0, 2.0, 0.318, 0.338, 24, 10, 170) + [
        (-0.26, 2.12), (-0.2, 2.08), (-0.12, 2.14), (-0.05, 2.1),
        (0.04, 2.17), (0.12, 2.13), (0.2, 2.19), (0.27, 2.15)]
    p("cabelo.frente", franja, 9, cabelo, "head", pivo=(0, 2.15))

    # rosto: olhos, sobrancelhas, bochechas, boca (estados alternativos)
    for s, lado in ((1, "L"), (-1, "R")):
        cx, cz = s * 0.105, 1.975
        olhos = {
            "aberto": [(g.elipse(cx, cz, 0.03, 0.042, 20), tinta, 8),
                       (g.elipse(cx + 0.01, cz + 0.014, 0.009, 0.009, 10), branco, 8.2)],
            "largo": [(g.elipse(cx, cz, 0.038, 0.052, 22), tinta, 8),
                      (g.elipse(cx + 0.012, cz + 0.018, 0.012, 0.012, 10), branco, 8.2)],
            "feliz": [(g.arco_grosso(cx, cz - 0.012, 0.032, 0.016, 20, 160), tinta, 8)],
            "fechado": [(g.arco_grosso(cx, cz + 0.012, 0.032, 0.012, 200, 340), tinta, 8)],
            "semicerrado": [(g.elipse(cx, cz - 0.004, 0.032, 0.03, 16, 180, 360), tinta, 8)],
        }
        for estado, partes in olhos.items():
            for i, (pts, mat, cam) in enumerate(partes):
                p(f"olho.{lado}.{estado}.{i}", pts, cam, mat, "head", pivo=(cx, cz),
                  sombra=False, tremor=0.0015, grupo="olhos", estado=estado, lado=lado)
        p(f"sobrancelha.{lado}", g.capsula((cx - s * 0.04, 2.075), (cx + s * 0.04, 2.075), 0.012, 0.01),
          8, cabelo, "head", pivo=(cx, 2.075), sombra=False, tremor=0.001,
          grupo="sobrancelhas", lado=lado)
        p(f"bochecha.{lado}", g.elipse(s * 0.18, 1.875, 0.045, 0.026, 16), 7.5, bochecha, "head",
          pivo=(s * 0.18, 1.875), sombra=False, grupo="bochechas", estado="sim", lado=lado)

    bz = 1.83
    bocas = {
        "X": [(g.arco_grosso(0, bz + 0.035, 0.05, 0.012, 240, 300), tinta)],
        "MBP": [(g.capsula((-0.04, bz), (0.04, bz), 0.008, 0.008), tinta)],
        "A": [(g.elipse(0, bz - 0.005, 0.055, 0.05, 24), boca_m)],
        "E": [(g.elipse(0, bz, 0.06, 0.028, 22), boca_m)],
        "O": [(g.elipse(0, bz - 0.004, 0.036, 0.042, 20), boca_m)],
        "U": [(g.elipse(0, bz, 0.022, 0.026, 16), boca_m)],
        "C": [(g.elipse(0, bz, 0.042, 0.02, 18), boca_m)],
        "FV": [(g.elipse(0, bz - 0.004, 0.05, 0.02, 18), boca_m),
               (g.retangulo_arredondado(0, bz + 0.006, 0.06, 0.014, 0.005), branco)],
        "sorriso": [(g.elipse(0, bz + 0.02, 0.07, 0.055, 20, 180, 360), boca_m)],
        "meio_sorriso": [(g.arco_grosso(0.012, bz + 0.045, 0.055, 0.013, 245, 325), tinta)],
        "triste": [(g.arco_grosso(0, bz - 0.04, 0.05, 0.012, 60, 120), tinta)],
        "lado": [(g.capsula((0.0, bz), (0.06, bz + 0.012), 0.008, 0.008), tinta)],
    }
    for estado, partes in bocas.items():
        for i, (pts, mat) in enumerate(partes):
            p(f"boca.{estado}.{i}", pts, 8 + 0.1 * i, mat, "head", pivo=(0, bz),
              sombra=False, tremor=0.001, grupo="boca", estado=estado)

    # tronco e pernas
    p("pescoco", g.retangulo_arredondado(0, 1.6, 0.15, 0.22, 0.04), 2, pele_s, "neck", pivo=(0, 1.6))
    tronco = [(-0.23, 1.6), (-0.08, 1.6), (0, 1.5), (0.08, 1.6), (0.23, 1.6), (0.32, 1.53),
              (0.3, 1.25), (0.26, 0.95), (-0.26, 0.95), (-0.3, 1.25), (-0.32, 1.53)]
    p("tronco", tronco, 3, camisola, "chest", pivo=(0, 1.25), roupa="camisola")
    p("ancas", g.retangulo_arredondado(0, 0.93, 0.5, 0.2, 0.05), 2.5, calcas, "hips",
      pivo=(0, 0.93), roupa="calcas")
    for s, lado in ((1, "L"), (-1, "R")):
        p(f"coxa.{lado}", g.capsula((s * 0.12, 0.95), (s * 0.125, 0.5), 0.11, 0.095), 2.2, calcas,
          f"thigh.{lado}", pivo=(s * 0.12, 0.95), roupa="calcas")
        p(f"canela.{lado}", g.capsula((s * 0.125, 0.52), (s * 0.13, 0.12), 0.095, 0.08), 2.1, calcas,
          f"shin.{lado}", pivo=(s * 0.125, 0.52), roupa="calcas")
        p(f"sapato.{lado}", g.elipse(s * 0.16, 0.07, 0.13, 0.065, 20), 2.3, sapatos,
          f"shin.{lado}", pivo=(s * 0.16, 0.07), roupa="sapatos")
        # braços
        p(f"manga.{lado}", g.capsula((s * 0.29, 1.5), (s * 0.33, 1.17), 0.085, 0.07), 4, camisola,
          f"upper_arm.{lado}", pivo=(s * 0.29, 1.5), roupa="camisola")
        p(f"antebraco.{lado}", g.capsula((s * 0.33, 1.19), (s * 0.355, 0.86), 0.056, 0.048), 4.5,
          pele, f"forearm.{lado}", pivo=(s * 0.33, 1.19))
        p(f"mao.{lado}", g.elipse(s * 0.36, 0.8, 0.068, 0.075, 20), 5, pele, f"hand.{lado}",
          pivo=(s * 0.36, 0.8))
        p(f"polegar.{lado}", g.elipse(s * 0.305, 0.82, 0.028, 0.04, 12), 5.05, pele_s, f"hand.{lado}",
          pivo=(s * 0.305, 0.82), sombra=False)

    # estado inicial: só o estado de repouso de cada grupo
    for ob in col.objects:
        if ob.get("grupo") in ("olhos", "boca", "bochechas"):
            visivel = ob["estado"] in ("aberto", "X")
            ob.hide_render = not visivel
            ob.hide_viewport = not visivel
    return arm


def configurar_render():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 8
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.resolution_x, sc.render.resolution_y = 720, 1080
    sc.render.fps = 30
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    cam_data = bpy.data.cameras.new("Camara")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 3.3
    cam = bpy.data.objects.new("Camara", cam_data)
    cam.location = (0.25, -10.0, 1.55)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.collection.objects.link(cam)
    sc.camera = cam


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--personagem", required=True, help="pasta com vocabulario.json; grava rig.blend")
    ap.add_argument("--previa")
    a = ap.parse_args(argv)
    with open(os.path.join(a.personagem, "vocabulario.json"), encoding="utf-8") as f:
        vocab = json.load(f)
    construir(vocab)
    configurar_render()
    saida = os.path.abspath(os.path.join(a.personagem, "rig.blend"))
    bpy.ops.wm.save_as_mainfile(filepath=saida)
    if a.previa:
        bpy.context.scene.render.filepath = os.path.abspath(a.previa)
        bpy.ops.render.render(write_still=True)
    print("RIG_OK", saida)


if __name__ == "__main__":
    main()

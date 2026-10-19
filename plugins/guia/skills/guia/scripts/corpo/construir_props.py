"""Constrói a biblioteca de props (props.blend) a partir de `<personagem>/props/*.json`.

    blender -b --factory-startup -P construir_props.py -- --personagem DIR [--previa previa.png]

Cada spec (ver props_spec.py) vira uma coleção `Prop.<id>`; specs com "blend" são anexadas
do .blend do utilizador. No fim, todas passam pelo contrato (versão 1):
  * coleção `Prop.<id>` com um Empty raiz também chamado `Prop.<id>`;
  * a origem da raiz é a PEGA (osso `encaixe.mao.*` ou âncora do cenário);
  * propriedades na raiz: `contrato`=1, `tipo` (`mao`|`cenario`), `mao`, `tags`;
  * todas as malhas são filhas da raiz e usam materiais `Papel.*`.
"""
import argparse
import os
import sys
import zlib

import bpy

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import geometria as g  # noqa: E402
import props_spec  # noqa: E402

CONTRATO = 1


def _raiz(spec):
    pid = spec["id"]
    col = bpy.data.collections.new(f"Prop.{pid}")
    bpy.context.scene.collection.children.link(col)
    raiz = bpy.data.objects.new(f"Prop.{pid}", None)
    raiz.empty_display_type = "ARROWS"
    raiz.empty_display_size = 0.08
    raiz["contrato"] = CONTRATO
    raiz["tipo"] = spec["tipo"]
    raiz["mao"] = spec.get("mao", "")
    raiz["tags"] = ",".join(spec.get("tags", []))
    col.objects.link(raiz)
    return col, raiz


def contorno(p):
    f = p["forma"]
    if f == "retangulo":
        (cx, cz), (w, h) = p["centro"], p["tamanho"]
        return g.retangulo_arredondado(cx, cz, w, h, min(p.get("raio", 0.0), w / 2, h / 2) or 1e-4)
    if f == "elipse":
        return g.elipse(*p["centro"], *p["raios"], 32)
    if f == "poligono":
        return [tuple(q) for q in p["pontos"]]
    if f == "capsula":
        return g.capsula(tuple(p["de"]), tuple(p["ate"]), *p["raios"])
    return g.arco_grosso(*p["centro"], p["raio"], p["espessura"], *p["angulos"])


def construir_de_pecas(spec):
    col, raiz = _raiz(spec)
    for i, p in enumerate(spec["pecas"]):
        nome = f"{spec['id']}.{p.get('nome', i)}"
        mat = g.material_papel(f"Papel.{nome}", p["cor"], grao=p.get("grao", 0.03))
        pts = g.tremer(contorno(p), 0.003, zlib.crc32(nome.encode()))
        camada = p.get("camada", 0)
        ob = g.malha_plana(nome, pts, camada, mat, col)
        ob.parent = raiz
        if p.get("sombra", camada == 0):
            dx, dz = g.SOMBRA_DESVIO
            so = g.malha_plana(nome + ".sombra", [(x + dx, z + dz) for x, z in pts], camada - 0.4,
                               g.material_sombra(), col)
            so.parent = raiz
    return col


def anexar_blend(spec, pasta_props):
    nome = f"Prop.{spec['id']}"
    caminho = os.path.join(pasta_props, spec["blend"])
    with bpy.data.libraries.load(caminho, link=False) as (src, dst):
        if nome not in src.collections:
            raise SystemExit(f"PROPS_ERRO {spec['blend']}: falta a coleção {nome}")
        dst.collections = [nome]
    col = dst.collections[0]
    bpy.context.scene.collection.children.link(col)
    return col


def validar_prop(col):
    """Devolve a lista de violações do contrato (vazia = conforme)."""
    erros = []
    pid = col.name
    raiz = col.objects.get(pid)
    if raiz is None or raiz.type != "EMPTY":
        return [f"{pid}: falta o Empty raiz com o nome da coleção"]
    if raiz.get("contrato") != CONTRATO:
        erros.append(f"{pid}: contrato {raiz.get('contrato')} != {CONTRATO}")
    if raiz.get("tipo") not in ("mao", "cenario"):
        erros.append(f"{pid}: tipo inválido {raiz.get('tipo')!r}")
    malhas = [o for o in col.objects if o.type == "MESH"]
    if not malhas:
        erros.append(f"{pid}: sem geometria")
    for o in malhas:
        if o.parent != raiz:
            erros.append(f"{pid}: {o.name} não é filho da raiz")
        if not all(m and m.name.startswith("Papel.") for m in o.data.materials):
            erros.append(f"{pid}: {o.name} usa um material fora de Papel.*")
    tipo = raiz.get("tipo")
    if tipo in props_spec.TAMANHO_MAX and malhas:
        xs = [(o.matrix_world @ v.co).x for o in malhas for v in o.data.vertices]
        zs = [(o.matrix_world @ v.co).z for o in malhas for v in o.data.vertices]
        tam = max(max(xs) - min(xs), max(zs) - min(zs))
        if tam > props_spec.TAMANHO_MAX[tipo] + 0.05:
            erros.append(f"{pid}: {tam:.2f} de tamanho > {props_spec.TAMANHO_MAX[tipo]} para '{tipo}'")
    return erros


def previa(caminho):
    """Props lado a lado numa só imagem, por ordem alfabética do id."""
    cols = sorted((c for c in bpy.data.collections if c.name.startswith("Prop.")), key=lambda c: c.name)
    for i, col in enumerate(cols):
        col.objects[col.name].location.x = i * 0.9
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    largura = max(2.2, 0.9 * len(cols))
    sc.render.resolution_x, sc.render.resolution_y = int(400 * largura), 450
    cam = bpy.data.objects.new("Camara", bpy.data.cameras.new("Camara"))
    cam.data.type, cam.data.ortho_scale = "ORTHO", largura
    cam.location, cam.rotation_euler = (0.45 * (len(cols) - 1), -10, 0.05), (1.5708, 0, 0)
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.filepath = os.path.abspath(caminho)
    bpy.ops.render.render(write_still=True)
    for col in cols:
        col.objects[col.name].location.x = 0.0
    bpy.data.objects.remove(cam, do_unlink=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--personagem", required=True)
    ap.add_argument("--previa")
    a = ap.parse_args(argv)
    pasta_props = os.path.join(a.personagem, "props")
    specs, erros = props_spec.ler_todos(pasta_props)
    if erros:
        print("PROPS_ERRO\n" + "\n".join(erros))
        sys.exit(1)

    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for pid, spec in specs.items():
        col = anexar_blend(spec, pasta_props) if "blend" in spec else construir_de_pecas(spec)
        bpy.context.view_layer.update()
        erros += validar_prop(col)
    if erros:
        print("PROPS_ERRO\n" + "\n".join(erros))
        sys.exit(1)
    if a.previa:
        previa(a.previa)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(os.path.join(a.personagem, "props.blend")))
    print("PROPS_OK", ", ".join(specs))


if __name__ == "__main__":
    main()

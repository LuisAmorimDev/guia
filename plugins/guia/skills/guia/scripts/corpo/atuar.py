"""Anima o rig 2D a partir de uma folha de atuação e renderiza PNG com transparência.

    blender -b colega-2d.blend -P atuar.py -- --atuacao A --timing T --palavras P --saida DIR
            --personagem .guia/corpo/<nome> [--fps 30] [--frames 0,120,250] [--guardar-blend X.blend]

Tudo é avaliado por frame (pose(t)) e gravado como uma chave por frame: gestos e emoções
com transições suaves, respiração e balanço, piscar de olhos, visemas da narração e props.
`--frames` renderiza só esses frames (prévia rápida); sem ele renderiza a cena inteira.
"""
import argparse
import math
import os
import random
import sys

import bpy

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import atuacao as atu  # noqa: E402
import construir_props as cp  # noqa: E402
import geometria as g  # noqa: E402
import visemas as vis  # noqa: E402

TRANSICAO = 0.35
OSSOS_GESTO = ["upper_arm.L", "forearm.L", "hand.L", "upper_arm.R", "forearm.R", "hand.R"]
CAMADA_PROP_MAO = 4.8
CAMADA_CENARIO = -2


def suave(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def back_out(x):
    x = max(0.0, min(1.0, x))
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, u):
    return a + (b - a) * u


# ---------- estado contínuo (o que se mistura entre segmentos) ----------

def estado(seg, vocab, t):
    e = vocab["emocoes"][seg["emocao"]]
    k = seg["intensidade"]
    gest = vocab["gestos"][seg["gesto"]]
    fg = 0.75 + 0.25 * k
    ossos = {b: gest["ossos"].get(b, 0.0) * fg for b in OSSOS_GESTO}
    osc = gest.get("oscilar")
    if osc:
        ossos[osc["osso"]] += osc["amplitude"] * math.sin(2 * math.pi * (t - seg["t"]) / osc["periodo"])
    ox, oz = vocab["olhar"][seg["olhar"]]
    return {"ossos": ossos, "cabeca": e["cabeca"] * k, "sob_alt": e["sobrancelhas"]["altura"] * k,
            "sob_ang": e["sobrancelhas"]["angulo"] * k, "ox": ox, "oz": oz}


def misturar(a, b, u):
    out = {k: lerp(a[k], b[k], u) for k in a if k != "ossos"}
    out["ossos"] = {o: lerp(a["ossos"][o], b["ossos"][o], u) for o in a["ossos"]}
    return out


def indice(segs, t, atraso=0.0):
    i = 0
    for j, s in enumerate(segs):
        if s["t"] + atraso <= t:
            i = j
    return i


def continuo(segs, vocab, t):
    i = indice(segs, t)
    atual = estado(segs[i], vocab, t)
    if i == 0:
        return atual
    return misturar(estado(segs[i - 1], vocab, t), atual, suave((t - segs[i]["t"]) / TRANSICAO))


# ---------- props ----------

def intervalos_mao(segs, duracao):
    """{(id, mao): [(t_on, t_off)]} juntando segmentos seguidos com o mesmo prop."""
    out = {}
    aberto = None
    for s in segs + [{"t": duracao + 1, "prop": None}]:
        chave = (s["prop"]["id"], s["prop"]["mao"]) if s.get("prop") else None
        if aberto and aberto[0] != chave:
            out.setdefault(aberto[0], []).append((aberto[1], s["t"] + 0.1))
            aberto = None
        if chave and not aberto:
            aberto = (chave, s["t"] + 0.15)
    return out


def envelope(intervalos, t):
    v = 0.0
    for t_on, t_off in intervalos:
        sobe = back_out((t - t_on) / 0.3) if t >= t_on else 0.0
        desce = 1.0 - suave((t - t_off) / 0.2) if t >= t_off else 1.0
        v = max(v, sobe * desce)
    return v


def carregar_prop(caminho, pid):
    nome = f"Prop.{pid}"
    with bpy.data.libraries.load(caminho, link=False) as (src, dst):
        if nome not in src.collections:
            raise SystemExit(f"ATUAR_ERRO prop {pid!r} não existe em {caminho}")
        dst.collections = [nome]
    col = dst.collections[0]
    bpy.context.scene.collection.children.link(col)
    raiz = next(o for o in col.objects if o.type == "EMPTY" and o.parent is None)
    if col.name == nome:
        erros = cp.validar_prop(col)
        if erros:
            raise SystemExit("ATUAR_ERRO contrato do prop:\n" + "\n".join(erros))
    return raiz


# ---------- aplicação ----------

def aplicar_roupa(roupa):
    for peca, mat_nome in (("camisola", "Roupa.Camisola"), ("calcas", "Roupa.Calcas")):
        p = roupa[peca]
        g.aplicar_roupa(bpy.data.materials[mat_nome], p["cor"], p.get("padrao", "liso"),
                        p.get("cor_padrao"), p.get("escala", 10.0))
    bpy.data.materials["Roupa.Sapatos"].node_tree.nodes["cor"].outputs[0].default_value = \
        g.hex_linear(roupa["sapatos"]["cor"])


def piscadelas(duracao, seed=7):
    rnd = random.Random(seed)
    out, t = [], rnd.uniform(1.0, 2.2)
    while t < duracao:
        out.append((t, t + 0.13))
        t += rnd.uniform(2.4, 4.4)
    return out


def animar(r, vocab, palavras, props_blend, fps):
    sc = bpy.context.scene
    cena, segs = r["cena"], r["segmentos"]
    dur = cena["duracao"]
    n = math.ceil(dur * fps)
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = 0, n - 1

    arm = bpy.data.objects["Colega.Rig"]
    pb = arm.pose.bones
    aplicar_roupa(r["roupa"])

    grupos = {}
    for ob in bpy.data.objects:
        if ob.get("grupo") and not ob.get("sombra_de"):
            grupos.setdefault(ob["grupo"], []).append(ob)
            ob["base"] = list(ob.location)

    props = {}
    for (pid, mao), ints in intervalos_mao(segs, dur).items():
        raiz = carregar_prop(props_blend, pid)
        osso = f"encaixe.mao.{mao}"
        h = arm.data.bones[osso].head_local
        raiz.location = (h.x, g.camada_y(CAMADA_PROP_MAO), h.z)
        g.prender_ao_osso(raiz, arm, osso)
        props[(pid, mao)] = (raiz, ints)
    cenario = []
    for c in r["cenario"]:
        raiz = carregar_prop(props_blend, c["prop"])
        ax, az = vocab["ancoras"][c["ancora"]]
        raiz.location = (ax, g.camada_y(CAMADA_CENARIO), az)
        cenario.append((raiz, [(c["t"], c["t_ate"] if c["t_ate"] is not None else dur + 1)]))

    boca = vis.por_frame(palavras, n, fps, atu.deslocamento_voz(cena))
    fala = [sum(v != "X" for v in boca[max(0, f - 7):f + 8]) / len(boca[max(0, f - 7):f + 8])
            for f in range(n)]
    pisca = piscadelas(dur)
    ultimo = {}

    for f in range(n):
        t = f / fps
        c = continuo(segs, vocab, t)
        ang = dict(c["ossos"])
        ang["upper_arm.L"] += 1.2 * math.sin(2 * math.pi * t / 4.1)
        ang["upper_arm.R"] -= 1.2 * math.sin(2 * math.pi * t / 4.4 + 1.0)
        for (pid, mao), (raiz, ints) in props.items():
            w = suave(envelope(ints, t))  # mão segura o prop direito, compensando o braço
            hand = f"hand.{mao}"
            ang[hand] = lerp(ang[hand], -(ang[f"upper_arm.{mao}"] + ang[f"forearm.{mao}"]) - 4, w)
        ang["neck"] = 1.5 * math.sin(2 * math.pi * t / 3.7) + 1.4 * fala[f] * math.sin(2 * math.pi * t / 0.7)
        ang["hips"] = 0.8 * math.sin(2 * math.pi * t / 5.3 + 1.0)
        ang["head"] = c["cabeca"]
        for osso, graus in ang.items():
            pb[osso].rotation_euler.z = math.radians(graus)
            pb[osso].keyframe_insert("rotation_euler", index=2, frame=f)
        pb["chest"].scale.y = 1.0 + 0.012 * math.sin(2 * math.pi * t / 3.2)
        pb["chest"].keyframe_insert("scale", index=1, frame=f)

        for ob in grupos.get("sobrancelhas", []):
            s = 1 if ob["lado"] == "L" else -1
            ob.location.z = ob["base"][2] + c["sob_alt"]
            ob.rotation_euler.y = math.radians(s * c["sob_ang"])
            ob.keyframe_insert("location", index=2, frame=f)
            ob.keyframe_insert("rotation_euler", index=1, frame=f)
        for ob in grupos.get("olhos", []):
            ob.location.x = ob["base"][0] + c["ox"]
            ob.location.z = ob["base"][2] + c["oz"]
            ob.keyframe_insert("location", frame=f)
        for raiz, ints in list(props.values()) + cenario:
            s = envelope(ints, t)
            raiz.scale = (s, s, s)
            raiz.keyframe_insert("scale", frame=f)

        e = vocab["emocoes"][segs[indice(segs, t, TRANSICAO * 0.4)]["emocao"]]
        olhos = e["olhos"]
        if olhos in ("aberto", "largo", "semicerrado") and any(a <= t < b for a, b in pisca):
            olhos = "fechado"
        discretos = {"boca": boca[f] if boca[f] != "X" else e["boca"], "olhos": olhos,
                     "bochechas": "sim" if e["bochechas"] else "nao"}
        for grupo, valor in discretos.items():
            if ultimo.get(grupo) == valor:
                continue
            ultimo[grupo] = valor
            for ob in grupos.get(grupo, []):
                ob.hide_render = ob["estado"] != valor
                ob.hide_viewport = ob.hide_render
                ob.keyframe_insert("hide_render", frame=f)
    return n


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--atuacao", required=True)
    ap.add_argument("--timing", required=True)
    ap.add_argument("--palavras", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--personagem", required=True, help="pasta com vocabulario.json, props/ e props.blend")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--frames")
    ap.add_argument("--guardar-blend")
    a = ap.parse_args(argv)

    at, vocab, cena, palavras, erros = atu.carregar(a.atuacao, a.timing, a.palavras, a.personagem)
    if erros:
        raise SystemExit("ATUACAO_INVALIDA\n- " + "\n- ".join(erros))
    r = atu.resolver(at, vocab, cena, palavras)
    n = animar(r, vocab, palavras, os.path.abspath(os.path.join(a.personagem, "props.blend")), a.fps)
    saida = os.path.abspath(a.saida)
    os.makedirs(saida, exist_ok=True)
    if a.guardar_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.guardar_blend), copy=True)
    sc = bpy.context.scene
    if a.frames:
        for f in (int(x) for x in a.frames.split(",")):
            sc.frame_set(f)
            sc.render.filepath = os.path.join(saida, f"previa_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
    else:
        sc.render.filepath = os.path.join(saida, "####")
        bpy.ops.render.render(animation=True)
    print(f"ATUAR_OK {n} frames -> {saida}")


if __name__ == "__main__":
    main()

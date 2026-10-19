"""Ator 2D de papel recortado da /guia: preparar, verificar props, validar atuação, renderizar.

    python ator.py preparar --personagem .guia/corpo/<nome>
    python ator.py props    --personagem DIR --pedido <saida>/work/ator/props-pedido.json
    python ator.py validar  --personagem DIR --saida <saida>
    python ator.py render   --personagem DIR --saida <saida> [--cenas cena-01,cena-06] [--previa]

Corre com o Python da skill (sem bpy) e chama o Blender em modo headless.
Blender: $GUIA_BLENDER, `blender` no PATH, ou o mais recente em Program Files/Blender Foundation.
"""
import argparse
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import atuacao as atu  # noqa: E402
import props_spec  # noqa: E402

FPS = 30
CODIGO_RIG = ("construir_rig.py", "geometria.py")
CODIGO_PROPS = ("construir_props.py", "geometria.py", "props_spec.py")


def blender_exe():
    exe = os.environ.get("GUIA_BLENDER") or shutil.which("blender")
    if exe:
        return exe
    candidatos = glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe")
    if not candidatos:
        raise SystemExit("ATOR_ERRO Blender não encontrado: instala-o ou define GUIA_BLENDER")

    def versao(c):
        m = re.search(r"Blender (\d+)\.(\d+)", c)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    return max(candidatos, key=versao)


def correr_blender(args, marca):
    r = subprocess.run([blender_exe(), "-b", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    saida = r.stdout + r.stderr
    if marca not in saida:
        print("\n".join(saida.splitlines()[-30:]))
        raise SystemExit(f"ATOR_ERRO o Blender não terminou ({marca} em falta)")
    return saida


def _mtime(*caminhos):
    return max((os.path.getmtime(c) for c in caminhos if os.path.exists(c)), default=0.0)


def preparar(personagem, forcar=False):
    """(Re)constrói rig.blend e props.blend quando faltam ou estão desatualizados."""
    specs, erros = props_spec.ler_todos(os.path.join(personagem, "props"))
    if erros:
        raise SystemExit("ATOR_ERRO props inválidos:\n- " + "\n- ".join(erros))
    previas = os.path.join(personagem, "previas")
    os.makedirs(previas, exist_ok=True)
    rig = os.path.join(personagem, "rig.blend")
    fontes_rig = [os.path.join(personagem, "vocabulario.json")] + [os.path.join(AQUI, f) for f in CODIGO_RIG]
    if forcar or not os.path.exists(rig) or os.path.getmtime(rig) < _mtime(*fontes_rig):
        correr_blender(["--factory-startup", "-P", os.path.join(AQUI, "construir_rig.py"), "--",
                        "--personagem", personagem, "--previa", os.path.join(previas, "rig.png")], "RIG_OK")
        print(f"rig.blend reconstruído (prévia: {previas}/rig.png)")
    pasta_props = os.path.join(personagem, "props")
    props = os.path.join(personagem, "props.blend")
    fontes_props = glob.glob(os.path.join(pasta_props, "*")) + [os.path.join(AQUI, f) for f in CODIGO_PROPS]
    if forcar or not os.path.exists(props) or os.path.getmtime(props) < _mtime(*fontes_props):
        correr_blender(["--factory-startup", "-P", os.path.join(AQUI, "construir_props.py"), "--",
                        "--personagem", personagem, "--previa", os.path.join(previas, "props.png")], "PROPS_OK")
        print(f"props.blend reconstruído (prévia: {previas}/props.png)")
    print(f"PREPARAR_OK {len(specs)} props: {', '.join(sorted(specs))}")


def verificar_pedido(personagem, pedido):
    """Compara o pedido do passo 2b com a biblioteca. Devolve (em_falta, erros)."""
    specs, erros = props_spec.ler_todos(os.path.join(personagem, "props"))
    em_falta = []
    for p in pedido.get("props", []):
        pid, tipo = p.get("id"), p.get("tipo")
        if pid not in specs:
            em_falta.append(p)
        elif tipo and specs[pid].get("tipo") != tipo:
            erros.append(f"{pid}: pedido como '{tipo}' mas a biblioteca tem '{specs[pid]['tipo']}'")
    return em_falta, erros


def ficheiros_atuacao(saida, cenas=None):
    pasta = os.path.join(saida, "work", "ator")
    todos = sorted(glob.glob(os.path.join(pasta, "cena-*.atuacao.json")))
    if cenas:
        todos = [f for f in todos if os.path.basename(f).split(".")[0] in cenas]
    return todos


def caminhos_cena(saida, cena_id):
    w = os.path.join(saida, "work")
    return (os.path.join(w, "saida-voz", "timing.json"), os.path.join(w, "voz", f"{cena_id}.palavras.json"))


def validar_todas(personagem, saida, cenas=None):
    fich = ficheiros_atuacao(saida, cenas)
    if not fich:
        raise SystemExit(f"ATOR_ERRO não há work/ator/cena-*.atuacao.json em {saida}")
    falhas = 0
    for f in fich:
        cena_id = os.path.basename(f).split(".")[0]
        timing, palavras = caminhos_cena(saida, cena_id)
        at, vocab, cena, pal, erros = atu.carregar(f, timing, palavras, personagem)
        if erros:
            falhas += 1
            print(f"✗ {cena_id}\n  - " + "\n  - ".join(erros))
            continue
        r = atu.resolver(at, vocab, cena, pal)
        resumo = " → ".join(f"{s['t']:.1f}s {s['emocao']}/{s['gesto']}" for s in r["segmentos"])
        print(f"✓ {cena_id}: {resumo}")
    if falhas:
        raise SystemExit(f"ATUACAO_INVALIDA em {falhas} cena(s)")
    print(f"VALIDAR_OK {len(fich)} cena(s)")
    return fich


def _ffprobe_webm(caminho):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_read_frames:stream_tags=alpha_mode",
                        "-of", "json", caminho], capture_output=True, text=True)
    s = json.loads(r.stdout or "{}").get("streams", [{}])[0]
    return int(s.get("nb_read_frames", 0)), s.get("tags", {}).get("alpha_mode") == "1"


def folha(pngs, destino):
    """Junta as prévias numa folha de contacto sobre papel (para olhar de uma vez)."""
    entradas = sum((["-i", p] for p in pngs), [])
    n = len(pngs)
    filtro = "".join(f"[{i}]" for i in range(n)) + f"hstack={n}[s];color=c=#faf6ee:s={720 * n}x1080[bg];" \
             "[bg][s]overlay,scale=1440:-1"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *entradas, "-filter_complex", filtro,
                    "-frames:v", "1", destino], check=True)


def render(personagem, saida, cenas=None, previa=False):
    preparar(personagem)
    fich = validar_todas(personagem, saida, cenas)
    rig = os.path.join(personagem, "rig.blend")
    assets = os.path.join(saida, "work", "composition", "assets")
    os.makedirs(assets, exist_ok=True)
    for f in fich:
        cena_id = os.path.basename(f).split(".")[0]
        timing, palavras = caminhos_cena(saida, cena_id)
        with open(timing, encoding="utf-8") as fh:
            cena = next(c for c in json.load(fh)["cenas"] if c["id"] == cena_id)
        n = math.ceil(cena["duracao"] * FPS)
        pasta = os.path.join(saida, "work", "ator", cena_id)
        args = ["--factory-startup", rig, "-P", os.path.join(AQUI, "atuar.py"), "--", "--atuacao", f,
                "--timing", timing, "--palavras", palavras, "--personagem", personagem,
                "--saida", pasta, "--fps", str(FPS)]
        if previa:
            frames = [round(n * (k + 0.5) / 6) for k in range(6)]
            correr_blender(args + ["--frames", ",".join(map(str, frames))], "ATUAR_OK")
            destino = os.path.join(saida, "work", "ator", f"{cena_id}-folha.png")
            folha([os.path.join(pasta, f"previa_{x:04d}.png") for x in frames], destino)
            print(f"✓ {cena_id}: prévia em {destino} (frames {frames})")
            continue
        correr_blender(args, "ATUAR_OK")
        webm = os.path.join(assets, f"ator-{cena_id}.webm")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", os.path.join(pasta, "%04d.png"), "-frames:v", str(n),
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "30",
                        "-row-mt", "1", "-auto-alt-ref", "0", webm], check=True)
        frames, alfa = _ffprobe_webm(webm)
        if frames != n or not alfa:
            raise SystemExit(f"ATOR_ERRO {webm}: {frames}/{n} frames, alfa={alfa}")
        print(f"✓ {cena_id}: {webm} ({n} frames, {cena['duracao']:.2f}s, com transparência)")
    print("RENDER_OK")


def main():
    ap = argparse.ArgumentParser(description="Ator 2D da /guia")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("preparar", "props", "validar", "render"):
        sp = sub.add_parser(c)
        sp.add_argument("--personagem", required=True)
        if c in ("validar", "render"):
            sp.add_argument("--saida", required=True)
            sp.add_argument("--cenas", help="lista separada por vírgulas (omissão: todas)")
        if c == "props":
            sp.add_argument("--pedido", required=True)
        if c == "preparar":
            sp.add_argument("--forcar", action="store_true")
        if c == "render":
            sp.add_argument("--previa", action="store_true")
    a = ap.parse_args()
    personagem = os.path.abspath(a.personagem)
    cenas = set(a.cenas.split(",")) if getattr(a, "cenas", None) else None
    if a.cmd == "preparar":
        preparar(personagem, a.forcar)
    elif a.cmd == "props":
        with open(a.pedido, encoding="utf-8") as f:
            em_falta, erros = verificar_pedido(personagem, json.load(f))
        for e in erros:
            print(f"✗ {e}")
        for p in em_falta:
            print(f"EM FALTA {p.get('id')} ({p.get('tipo')}) — {p.get('descricao', '')} "
                  f"[{', '.join(p.get('cenas', []))}]")
        if erros:
            sys.exit(1)
        if em_falta:
            sys.exit(2)
        print("PROPS_COMPLETOS")
    elif a.cmd == "validar":
        validar_todas(personagem, os.path.abspath(a.saida), cenas)
    elif a.cmd == "render":
        render(personagem, os.path.abspath(a.saida), cenas, a.previa)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

"""Timing da skill /guia: alinha palavras, monta a timeline, legendas e narração única.

A voz manda no tempo: cada cena dura pausa_inicio + áudio + pausa_fim, e cada
marcador [[id]] recebe o instante exato da palavra a que está ancorado.

Uso:
  python timing.py --preparado work/voz/preparado.json --voz work/voz --persona work/persona.json --saida <dir>
Escreve: timing.json, legendas.pt-PT.vtt, legendas.pt-PT.srt, narracao.wav, transcricao.md
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

TOKEN = re.compile(r"\w+(?:[-']\w+)*")


def _chave(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if c.isalnum() and not unicodedata.combining(c))


def alinhar(toks: list[str], limites: list[dict]) -> list[tuple[float, float]]:
    """Dá (início, fim) a cada token do texto a partir dos limites de palavra do motor."""
    sub, dono = [], []
    for i, t in enumerate(toks):
        for p in re.split(r"[-']", t):
            if p:
                sub.append(_chave(p))
                dono.append(i)
    bkeys = [_chave(b["texto"]) for b in limites]
    tempos: list[list[float] | None] = [None] * len(toks)
    sm = difflib.SequenceMatcher(None, sub, bkeys, autojunk=False)
    for bloco in sm.get_matching_blocks():
        for k in range(bloco.size):
            i, b = dono[bloco.a + k], limites[bloco.b + k]
            if tempos[i] is None:
                tempos[i] = [b["inicio"], b["fim"]]
            else:
                tempos[i][0] = min(tempos[i][0], b["inicio"])
                tempos[i][1] = max(tempos[i][1], b["fim"])

    fim_total = limites[-1]["fim"] if limites else 0.0
    i = 0
    while i < len(tempos):
        if tempos[i] is not None:
            i += 1
            continue
        j = i
        while j < len(tempos) and tempos[j] is None:
            j += 1
        a = tempos[i - 1][1] if i > 0 else 0.0
        z = tempos[j][0] if j < len(tempos) else fim_total
        passo = (z - a) / (j - i)
        for k in range(i, j):
            tempos[k] = [a + passo * (k - i), a + passo * (k - i + 1)]
        i = j
    return [(round(t[0], 3), round(t[1], 3)) for t in tempos]


def partir_legenda(leg: dict, max_chars: int = 42) -> list[dict]:
    palavras = leg["texto"].split()
    linhas, atual = [], ""
    for w in palavras:
        cand = f"{atual} {w}".strip()
        if len(cand) > max_chars and atual:
            linhas.append(atual)
            atual = w
        else:
            atual = cand
    if atual:
        linhas.append(atual)
    total = sum(len(l) for l in linhas) or 1
    dur = leg["fim"] - leg["inicio"]
    out, acc = [], 0
    for k, l in enumerate(linhas):
        ini = leg["inicio"] + dur * acc / total
        acc += len(l)
        fim = leg["fim"] if k == len(linhas) - 1 else leg["inicio"] + dur * acc / total
        out.append({"texto": l, "inicio": round(ini, 3), "fim": round(fim, 3)})
    return out


def montar(cenas: list[dict], pausa_inicio: float, pausa_fim: float, max_chars: int = 84) -> dict:
    t, out, legendas = 0.0, [], []
    for c in cenas:
        base = t + pausa_inicio
        dur = pausa_inicio + c["duracao_audio"] + pausa_fim
        tempos = c["tempos"]
        mk = [{"id": m["id"], "t": round(base + tempos[m["palavra"]][0], 3),
               "t_cena": round(pausa_inicio + tempos[m["palavra"]][0], 3)} for m in c["marcadores"]]
        for f in c["frases"]:
            leg = {"texto": f["original"], "inicio": round(base + tempos[f["w0"]][0], 3),
                   "fim": round(base + tempos[f["w1"]][1], 3)}
            legendas += partir_legenda(leg, max_chars) if len(leg["texto"]) > max_chars else [leg]
        out.append({"id": c["id"], "titulo": c["titulo"], "inicio": round(t, 3), "duracao": round(dur, 3),
                    "voz_inicio": round(base, 3), "voz_duracao": round(c["duracao_audio"], 3),
                    "marcadores": mk})
        t = round(t + dur, 3)
    return {"cenas": out, "legendas": legendas, "total": round(t, 3)}


def _ts(s: float, sep: str) -> str:
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d}{sep}{ms:03d}"


def vtt(legendas: list[dict]) -> str:
    blocos = [f"{_ts(l['inicio'], '.')} --> {_ts(l['fim'], '.')}\n{l['texto']}" for l in legendas]
    return "WEBVTT\n\n" + "\n\n".join(blocos) + "\n"


def srt(legendas: list[dict]) -> str:
    blocos = [f"{k}\n{_ts(l['inicio'], ',')} --> {_ts(l['fim'], ',')}\n{l['texto']}"
              for k, l in enumerate(legendas, 1)]
    return "\n\n".join(blocos) + "\n"


# ---------------------------------------------------------------- áudio

def duracao_wav(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def juntar_narracao(timeline: dict, voz_dir: Path, destino: Path) -> None:
    """Uma faixa única: cada cena começa no seu 'voz_inicio', silêncio no resto."""
    entradas, filtros = [], []
    for k, c in enumerate(timeline["cenas"]):
        entradas += ["-i", str(voz_dir / f"{c['id']}.wav")]
        atraso = int(round(c["voz_inicio"] * 1000))
        filtros.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=mono,adelay={atraso}:all=1[a{k}]")
    mix = "".join(f"[a{k}]" for k in range(len(timeline["cenas"])))
    filtros.append(f"{mix}amix=inputs={len(timeline['cenas'])}:normalize=0,apad=whole_dur={timeline['total']}[out]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", *entradas, "-filter_complex", ";".join(filtros),
                    "-map", "[out]", "-ar", "48000", "-ac", "1", str(destino)], check=True)


def transcricao_md(titulo: str, preparado: dict) -> str:
    partes = [f"# {titulo}\n"]
    for c in preparado["cenas"]:
        partes.append(f"## {c['titulo']}\n\n" + " ".join(f["original"] for f in c["frases"]) + "\n")
    return "\n".join(partes)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Montar timeline, legendas e narração a partir da voz gerada")
    ap.add_argument("--preparado", required=True)
    ap.add_argument("--voz", required=True, help="pasta com <cena>.wav e <cena>.palavras.json")
    ap.add_argument("--persona", required=True, help="persona resolvida (JSON)")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--titulo", default="Guia")
    a = ap.parse_args(argv)

    prep = json.loads(Path(a.preparado).read_text(encoding="utf-8"))
    persona = json.loads(Path(a.persona).read_text(encoding="utf-8"))
    voz_dir, saida = Path(a.voz), Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)

    cenas = []
    for c in prep["cenas"]:
        limites = json.loads((voz_dir / f"{c['id']}.palavras.json").read_text(encoding="utf-8"))
        toks = TOKEN.findall(c["texto"])
        cenas.append({**c, "tempos": alinhar(toks, limites),
                      "duracao_audio": duracao_wav(voz_dir / f"{c['id']}.wav")})
    v = persona["voz"]
    tl = montar(cenas, v["pausa_inicio_cena_ms"] / 1000, v["pausa_fim_cena_ms"] / 1000)

    (saida / "timing.json").write_text(json.dumps(tl, ensure_ascii=False, indent=2), encoding="utf-8")
    (saida / "legendas.pt-PT.vtt").write_text(vtt(tl["legendas"]), encoding="utf-8")
    (saida / "legendas.pt-PT.srt").write_text(srt(tl["legendas"]), encoding="utf-8")
    (saida / "transcricao.md").write_text(transcricao_md(a.titulo, prep), encoding="utf-8")
    juntar_narracao(tl, voz_dir, saida / "narracao.wav")
    print(f"total {tl['total']}s, {len(tl['cenas'])} cenas, {len(tl['legendas'])} legendas -> {saida}")
    for c in tl["cenas"]:
        print(f"  {c['id']}: {c['inicio']:.2f}s +{c['duracao']:.2f}s  marcadores: "
              + ", ".join(f"{m['id']}@{m['t']:.2f}" for m in c["marcadores"]))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

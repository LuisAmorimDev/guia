"""Verificação da voz da skill /guia: transcreve a narração e compara com o texto pretendido.

Apanha palavras saltadas, trocadas ou mal lidas antes de compor o vídeo.

Uso:
  python verify.py --preparado work/voz/preparado.json --timing <dir>/timing.json \
                   --audio <dir>/narracao.wav [--transcricao transcript.json] [--limiar 0.85]
Sem --transcricao corre `npx hyperframes transcribe -l pt -m large-v3`.
Escreve verificacao.json ao lado do timing e sai com 1 se alguma cena ficar abaixo do limiar.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from timing import _chave

TOKEN = re.compile(r"\w+(?:[-']\w+)*")


def palavras(obj) -> list[dict]:
    """Extrai [{texto, inicio, fim}] de transcrições em formatos comuns (lista, words, segments)."""
    if isinstance(obj, dict):
        if isinstance(obj.get("words"), list):
            return palavras(obj["words"])
        out = []
        for v in obj.values():
            if isinstance(v, (list, dict)):
                out += palavras(v)
        return out
    if isinstance(obj, list):
        out = []
        for it in obj:
            if isinstance(it, dict) and "words" in it:
                out += palavras(it["words"])
            elif isinstance(it, dict) and "start" in it and "end" in it and ("word" in it or "text" in it):
                out.append({"texto": str(it.get("word", it.get("text"))).strip(),
                            "inicio": it["start"], "fim": it["end"]})
            elif isinstance(it, (list, dict)):
                out += palavras(it)
        return out
    return []


def comparar(esperado: str, ouvidas: list[str]) -> dict:
    exp = TOKEN.findall(esperado)
    ek = [_chave(t) for t in exp]
    hk = [_chave(t) for t in ouvidas if _chave(t)]
    sm = difflib.SequenceMatcher(None, ek, hk, autojunk=False)
    casadas = set()
    for b in sm.get_matching_blocks():
        casadas.update(range(b.a, b.a + b.size))
    em_falta = [exp[i].lower() for i in range(len(exp)) if i not in casadas]
    sem = round(len(casadas) / len(exp), 3) if exp else 1.0
    return {"semelhanca": sem, "em_falta": em_falta, "ouvido": " ".join(ouvidas)}


_FASTER_WHISPER = """
import json, sys
from faster_whisper import WhisperModel
m = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
segs, _ = m.transcribe(sys.argv[1], language="pt", beam_size=5, word_timestamps=True)
print(json.dumps([{"word": w.word, "start": w.start, "end": w.end} for s in segs for w in (s.words or [])]))
"""


def transcrever(audio: Path) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(["npx", "--yes", "hyperframes", "transcribe", str(audio), "-d", tmp,
                            "-l", "pt", "-m", "large-v3"], shell=(os.name == "nt"))
        t = Path(tmp) / "transcript.json"
        if r.returncode == 0 and t.exists():
            return palavras(json.loads(t.read_text(encoding="utf-8")))
    return _transcrever_faster_whisper(audio)


def _transcrever_faster_whisper(audio: Path) -> list[dict]:
    """Alternativa sem whisper-cpp: faster-whisper large-v3-turbo do venv de ~/tools/voz-pt."""
    base = Path(os.environ.get("GUIA_PIPER_HOME", Path.home() / "tools" / "voz-pt"))
    py = Path(os.environ.get("GUIA_WHISPER_PYTHON", base / ".venv" / "Scripts" / "python.exe"))
    if not py.is_file():
        raise RuntimeError("Sem transcrição: hyperframes não tem whisper-cpp e não há faster-whisper "
                           f"em {py} (defina GUIA_WHISPER_PYTHON)")
    r = subprocess.run([str(py), "-c", _FASTER_WHISPER, str(audio)], capture_output=True, text=True,
                       encoding="utf-8", check=True, env={**os.environ, "PYTHONUTF8": "1"})
    return palavras(json.loads(r.stdout.strip().splitlines()[-1]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verificar a narração gerada contra o texto pretendido")
    ap.add_argument("--preparado", required=True)
    ap.add_argument("--timing", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--transcricao")
    ap.add_argument("--limiar", type=float, default=0.85)
    a = ap.parse_args(argv)

    prep = json.loads(Path(a.preparado).read_text(encoding="utf-8"))
    tl = json.loads(Path(a.timing).read_text(encoding="utf-8"))
    ouvidas = (palavras(json.loads(Path(a.transcricao).read_text(encoding="utf-8")))
               if a.transcricao else transcrever(Path(a.audio)))

    relatorio, falhas = [], 0
    for c_prep, c_tl in zip(prep["cenas"], tl["cenas"]):
        ini, fim = c_tl["voz_inicio"] - 0.2, c_tl["voz_inicio"] + c_tl["voz_duracao"] + 0.2
        dentro = [w["texto"] for w in ouvidas if ini <= (w["inicio"] + w["fim"]) / 2 <= fim]
        r = {"cena": c_prep["id"], **comparar(c_prep["texto"], dentro)}
        r["ok"] = r["semelhanca"] >= a.limiar
        falhas += not r["ok"]
        relatorio.append(r)
        estado = "ok   " if r["ok"] else "FALHA"
        print(f"[{estado}] {r['cena']}: {r['semelhanca']:.0%}"
              + (f"  em falta: {', '.join(r['em_falta'])}" if r["em_falta"] else ""))

    destino = Path(a.timing).parent / "verificacao.json"
    destino.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> {destino}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

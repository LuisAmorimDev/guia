"""Análise de um vídeo de referência para extrair estilo (skill /guia).

Mede o que dá para medir — duração, cortes, plano médio, volume, ritmo de fala —
e gera uma folha de contacto para o modelo ver o estilo visual. Imagens, sites e
textos de referência são lidos diretamente pelo modelo, sem este script.

Uso:
  python analyze_ref.py video.mp4 --saida work/referencias [--transcrever]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def sonda(video: Path) -> dict:
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
              "-of", "json", str(video)])
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    num, _, den = (v.get("r_frame_rate") or "0/1").partition("/")
    return {"duracao_s": round(float(d["format"]["duration"]), 2),
            "resolucao": f"{v.get('width')}x{v.get('height')}",
            "fps": round(float(num) / float(den), 2) if float(den or 0) else None,
            "tem_audio": any(s.get("codec_type") == "audio" for s in d.get("streams", []))}


def cortes(video: Path, limiar: float = 0.3) -> list[float]:
    r = _run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", f"select='gt(scene,{limiar})',showinfo",
              "-an", "-f", "null", "-"])
    return [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def loudness(video: Path) -> float | None:
    r = _run(["ffmpeg", "-hide_banner", "-i", str(video), "-vn", "-af", "ebur128=framelog=quiet", "-f", "null", "-"])
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def folha_contacto(video: Path, duracao: float, destino: Path, n: int = 12) -> Path:
    intervalo = max(duracao / n, 0.5)
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf",
          f"fps=1/{intervalo:.3f},scale=480:-2,tile=4x3:padding=4:color=white", "-frames:v", "1", str(destino)])
    return destino


def analisar(video: Path, saida: Path, transcrever: bool = False) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    info = sonda(video)
    cs = cortes(video)
    planos = [b - a for a, b in zip([0.0] + cs, cs + [info["duracao_s"]])]
    info.update({
        "cortes_s": cs,
        "plano_medio_s": round(sum(planos) / len(planos), 2) if planos else info["duracao_s"],
        "loudness_lufs": loudness(video) if info["tem_audio"] else None,
        "folha_contacto": str(folha_contacto(video, info["duracao_s"], saida / f"ref-{video.stem}.png")),
    })
    if transcrever and info["tem_audio"]:
        from verify import transcrever as tx
        palavras = tx(video)
        if palavras:
            fala = palavras[-1]["fim"] - palavras[0]["inicio"]
            info["palavras_por_minuto"] = round(len(palavras) / (fala / 60)) if fala > 0 else None
            info["transcricao"] = " ".join(w["texto"] for w in palavras)
    destino = saida / f"ref-{video.stem}.json"
    destino.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Extrair métricas de estilo de um vídeo de referência")
    ap.add_argument("video")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--transcrever", action="store_true", help="medir palavras por minuto (hyperframes transcribe)")
    a = ap.parse_args(argv)
    info = analisar(Path(a.video), Path(a.saida), a.transcrever)
    print(json.dumps({k: v for k, v in info.items() if k != "transcricao"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

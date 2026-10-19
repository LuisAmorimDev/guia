"""Síntese de voz da skill /guia — só motores com licença para uso comercial.

  azure : Azure AI Speech (SDK oficial). SSML completo, fonemas IPA do léxico e
          limites de palavra exatos. Precisa de AZURE_SPEECH_KEY e AZURE_SPEECH_REGION.
  local : tts_eu_pt (Kokoro afinado para pt-PT, Apache-2.0) — EXPERIMENTAL, sem
          avaliação de qualidade. Precisa do executável `tts-eu-pt` no PATH. Os
          limites de palavra vêm de `hyperframes transcribe`.
  piper : Piper com voz pt_PT (ex.: `pt_PT-tugao-medium`; voz MIT, dataset CC0). O
          `voz.id` é o nome do modelo .onnx. Corre no venv de ~/tools/voz-pt
          (GUIA_PIPER_HOME/PYTHON/MODEL para outro sítio). Sem SSML: usa só
          velocidade e pausas; limites de palavra via `hyperframes transcribe`.
  sopro : Sopro v2 Turbo (Apache-2.0, treinado com português europeu) a clonar a
          gravação de referência em `voz.id` (.wav de 5-20 s; caminho relativo a
          ~/tools/voz-pt). Corre o voz.py desse venv, que verifica cada frase
          (Whisper + marcas de sotaque do Brasil) e repete se falhar. Velocidade via
          ffmpeg atempo; limites de palavra via `hyperframes transcribe`.

Uso:
  python tts.py --preparado work/voz/preparado.json --persona work/persona.json \
                [--lexico .guia/lexico.pt-PT.json] --saida work/voz [--cena cena-02] [--forcar]
  python tts.py --amostra "Texto de teste" --persona work/persona.json --saida amostra.wav
Escreve <cena>.wav (48 kHz mono) e <cena>.palavras.json ([{texto, inicio, fim}] em segundos).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from persona import PROVIDERS


# ---------------------------------------------------------------- SSML

def ssml(frases: list[str], voz: dict, lexicon: list[dict]) -> str:
    pausa = f'<break time="{voz.get("pausa_entre_frases_ms", 300)}ms"/>'
    corpo = pausa.join(_fonemas(escape(f), lexicon) for f in frases)
    return (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="pt-PT">'
        f'<voice name="{escape(voz["id"])}">'
        f'<prosody rate="{voz.get("velocidade", "+0%")}" pitch="{voz.get("tom_voz", "+0Hz")}" '
        f'volume="{voz.get("volume", "+0%")}">{corpo}</prosody></voice></speak>'
    )


def _fonemas(texto: str, lexicon: list[dict]) -> str:
    for ent in lexicon:
        if not ent.get("ipa"):
            continue
        alvo = escape(ent.get("dizer") or ent["termo"])
        ph = escape(ent["ipa"], {'"': "&quot;"})
        texto = re.sub(rf"(?<![\w>]){re.escape(alvo)}(?!\w)",
                       lambda m: f'<phoneme alphabet="ipa" ph="{ph}">{m.group()}</phoneme>', texto)
    return texto


# ---------------------------------------------------------------- motores

def _azure(ssml_txt: str, wav: Path) -> list[dict]:
    try:
        import azure.cognitiveservices.speech as sdk
    except ImportError as e:
        raise RuntimeError("SDK do Azure em falta: corra 'uv sync' na pasta scripts") from e
    key, region = os.environ.get("AZURE_SPEECH_KEY"), os.environ.get("AZURE_SPEECH_REGION")
    if not key or not region:
        raise RuntimeError("Defina AZURE_SPEECH_KEY e AZURE_SPEECH_REGION (recurso Speech no portal Azure; o nível F0 é gratuito)")
    cfg = sdk.SpeechConfig(subscription=key, region=region)
    cfg.set_speech_synthesis_output_format(sdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)
    synth = sdk.SpeechSynthesizer(speech_config=cfg, audio_config=sdk.audio.AudioOutputConfig(filename=str(wav)))
    palavras: list[dict] = []

    def _limite(evt):
        if evt.boundary_type == sdk.SpeechSynthesisBoundaryType.Word:
            ini = evt.audio_offset / 10_000_000
            palavras.append({"texto": evt.text, "inicio": round(ini, 3),
                             "fim": round(ini + evt.duration.total_seconds(), 3)})

    synth.synthesis_word_boundary.connect(_limite)
    r = synth.speak_ssml_async(ssml_txt).get()
    if r.reason != sdk.ResultReason.SynthesizingAudioCompleted:
        det = r.cancellation_details
        raise RuntimeError(f"Azure falhou: {r.reason} {getattr(det, 'error_details', '')}")
    del synth  # liberta o ficheiro no Windows
    return palavras


def _local(frases: list[str], voz: dict, wav: Path) -> list[dict]:
    exe = shutil.which("tts-eu-pt")
    if not exe:
        raise RuntimeError("Motor local não instalado: 'uv tool install --prerelease=allow tts_eu_pt' (EXPERIMENTAL; confirme a qualidade a ouvir)")
    env = {**os.environ, "PYTHONUTF8": "1"}  # sem isto o Windows lê o texto em cp1252 e falha
    return _por_frase(frases, voz, wav, 24000, lambda f, p: subprocess.run([exe, f, str(p)], check=True, env=env))


def _velocidade_pct(voz: dict) -> float:
    m = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?)\s*%\s*", str(voz.get("velocidade", "+0%")))
    return float(m.group(1)) if m else 0.0


def _piper(frases: list[str], voz: dict, wav: Path) -> list[dict]:
    base = Path(os.environ.get("GUIA_PIPER_HOME", Path.home() / "tools" / "voz-pt"))
    py = Path(os.environ.get("GUIA_PIPER_PYTHON", base / ".venv" / "Scripts" / "python.exe"))
    modelo = Path(os.environ.get("GUIA_PIPER_MODEL", base / "vozes" / "piper" / f"{voz['id']}.onnx"))
    if not py.is_file() or not modelo.is_file():
        raise RuntimeError(f"Piper não encontrado (python: {py}, modelo: {modelo}); "
                           "defina GUIA_PIPER_HOME, GUIA_PIPER_PYTHON ou GUIA_PIPER_MODEL")
    # length_scale > 1 abranda; 1.25 é o ritmo natural medido para o tugão (voz-pt)
    ritmo = float(os.environ.get("GUIA_PIPER_RITMO", "1.25")) / (1 + _velocidade_pct(voz) / 100)
    sr = json.loads(Path(f"{modelo}.json").read_text(encoding="utf-8"))["audio"]["sample_rate"]
    env = {**os.environ, "PYTHONUTF8": "1"}

    def _uma(f: str, p: Path) -> None:
        subprocess.run([str(py), "-m", "piper", "-m", str(modelo), "-f", str(p), "--length-scale", f"{ritmo:.3f}"],
                       input=f, text=True, encoding="utf-8", check=True, env=env)

    return _por_frase(frases, voz, wav, sr, _uma)


def _voz_pt() -> Path:
    return Path(os.environ.get("GUIA_PIPER_HOME", Path.home() / "tools" / "voz-pt"))


def _sopro_ref(voz: dict) -> Path:
    ref = Path(voz["id"]).expanduser()
    return ref if ref.is_absolute() else _voz_pt() / ref


def _sopro(frases: list[str], voz: dict, wav: Path) -> list[dict]:
    base, ref = _voz_pt(), _sopro_ref(voz)
    py = Path(os.environ.get("GUIA_PIPER_PYTHON", base / ".venv" / "Scripts" / "python.exe"))
    if not ref.is_file():
        raise RuntimeError(f"Gravação de referência não encontrada: {ref} (voz.id = .wav de 5-20 s)")
    if not py.is_file() or not (base / "voz.py").is_file():
        raise RuntimeError(f"voz.py/venv não encontrados em {base}; defina GUIA_PIPER_HOME ou GUIA_PIPER_PYTHON")
    env = {**os.environ, "PYTHONUTF8": "1", "HF_HUB_DISABLE_SYMLINKS_WARNING": "1"}
    tempo = 1 + _velocidade_pct(voz) / 100
    with tempfile.TemporaryDirectory() as tmp:
        guiao, bruto = Path(tmp) / "guiao.txt", Path(tmp) / "voz.wav"
        guiao.write_text("\n".join(frases), encoding="utf-8")
        subprocess.run([str(py), str(base / "voz.py"), "-f", str(guiao), "-o", str(bruto), "--motor", "sopro",
                        "--ref", str(ref), "--pausa", str(voz.get("pausa_entre_frases_ms", 300) / 1000)],
                       check=True, env=env)
        filtro = ["-af", f"atempo={tempo:.3f}"] if abs(tempo - 1) > 1e-3 else []
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(bruto), *filtro, "-ar", "48000", "-ac", "1", str(wav)],
                       check=True)
    return palavras_por_transcricao(wav)


def _por_frase(frases: list[str], voz: dict, wav: Path, sr: int, sintetizar) -> list[dict]:
    """Sintetiza frase a frase, junta com silêncios e tira os limites de palavra do áudio."""
    with tempfile.TemporaryDirectory() as tmp:
        partes = []
        for k, f in enumerate(frases):
            p = Path(tmp) / f"f{k}.wav"
            sintetizar(f, p)
            partes.append(p)
        silencio = voz.get("pausa_entre_frases_ms", 300) / 1000
        sil = Path(tmp) / "sil.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=mono",
                        "-t", str(silencio), str(sil)], check=True)
        linhas = []
        for k, p in enumerate(partes):
            linhas.append(f"file '{p.as_posix()}'")
            if k < len(partes) - 1:
                linhas.append(f"file '{sil.as_posix()}'")
        lista = Path(tmp) / "lista.txt"
        lista.write_text("\n".join(linhas), encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                        "-ar", "48000", "-ac", "1", str(wav)], check=True)
    return palavras_por_transcricao(wav)


def palavras_por_transcricao(wav: Path) -> list[dict]:
    """Limites de palavra a partir do áudio, com o hyperframes transcribe."""
    from verify import transcrever
    return transcrever(wav)


# ---------------------------------------------------------------- cenas

def sintetizar_cena(cena: dict, voz: dict, lexicon: list[dict], saida: Path | None, forcar: bool = False) -> Path:
    if voz["provider"] not in PROVIDERS:
        raise ValueError(f"provider '{voz['provider']}' recusado: só motores com licença comercial {PROVIDERS}")
    frases = [f["normalizado"] for f in cena["frases"]]
    ssml_txt = ssml(frases, voz, lexicon)
    assinatura = hashlib.sha256(json.dumps([voz, ssml_txt], ensure_ascii=False).encode()).hexdigest()
    saida.mkdir(parents=True, exist_ok=True)
    wav, pal, sha = saida / f"{cena['id']}.wav", saida / f"{cena['id']}.palavras.json", saida / f"{cena['id']}.sha"
    if not forcar and wav.exists() and pal.exists() and sha.exists() and sha.read_text() == assinatura:
        return wav  # sem alterações: não gasta quota
    motor = {"local": _local, "piper": _piper, "sopro": _sopro}.get(voz["provider"])
    palavras = _azure(ssml_txt, wav) if voz["provider"] == "azure" else motor(frases, voz, wav)
    (saida / f"{cena['id']}.ssml").write_text(ssml_txt, encoding="utf-8")
    pal.write_text(json.dumps(palavras, ensure_ascii=False, indent=1), encoding="utf-8")
    sha.write_text(assinatura)
    return wav


def amostra(texto: str, voz: dict, lexicon: list[dict], destino: Path) -> Path:
    from normalize_pt import normalize
    cena = {"id": destino.stem, "frases": [{"normalizado": normalize(texto, lexicon=lexicon).text}]}
    sintetizar_cena(cena, voz, lexicon, destino.parent, forcar=True)
    return destino


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gerar a voz das cenas (Azure ou local)")
    ap.add_argument("--preparado")
    ap.add_argument("--amostra", help="texto livre para uma amostra de voz")
    ap.add_argument("--persona", required=True)
    ap.add_argument("--lexico")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--cena", help="gerar só esta cena")
    ap.add_argument("--forcar", action="store_true")
    a = ap.parse_args(argv)

    voz = json.loads(Path(a.persona).read_text(encoding="utf-8"))["voz"]
    lex = json.loads(Path(a.lexico).read_text(encoding="utf-8")) if a.lexico and Path(a.lexico).exists() else []
    if a.amostra:
        print(amostra(a.amostra, voz, lex, Path(a.saida)))
        return 0
    prep = json.loads(Path(a.preparado).read_text(encoding="utf-8"))
    for c in prep["cenas"]:
        if a.cena and c["id"] != a.cena:
            continue
        print(f"{c['id']}: {sintetizar_cena(c, voz, lex, Path(a.saida), a.forcar)}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

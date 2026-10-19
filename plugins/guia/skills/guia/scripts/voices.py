"""Vozes pt-PT disponíveis e amostras para comparar (skill /guia).

Uso:
  python voices.py listar   [--provider azure|local]
  python voices.py amostras --persona work/persona.json --saida work/amostras \
                            [--vozes raquel,duarte] [--texto "..."] [--lexico lex.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from persona import ALIASES_VOZ, Voz

TEXTO_TESTE = ("Para alterar o NIF da sua empresa, abra Definições › Faturação e clique em "
               "Guardar alterações. O plano custa 12,50 € por mês, até 15/10/2026.")

# Usado quando não há chave para consultar a lista ao vivo.
AZURE_PT_PT = [
    ("pt-PT-RaquelNeural", "feminina"),
    ("pt-PT-DuarteNeural", "masculina"),
    ("pt-PT-FernandaNeural", "feminina"),
]


def listar(provider: str) -> list[dict]:
    if provider == "local":
        return [{"id": "tuga", "genero": "masculina", "nota": "tts_eu_pt (EXPERIMENTAL, voz única)"}]
    if provider == "piper":
        return [{"id": "pt_PT-tugao-medium", "genero": "masculina", "nota": "Piper tugão (voz MIT, dataset CC0)"}]
    if provider == "sopro":
        return [{"id": "referencia.wav", "genero": "masculina",
                 "nota": "Sopro v2 Turbo a clonar ~/tools/voz-pt/referencia.wav (voz do dono do projeto)"}]
    if os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION"):
        import azure.cognitiveservices.speech as sdk
        cfg = sdk.SpeechConfig(subscription=os.environ["AZURE_SPEECH_KEY"], region=os.environ["AZURE_SPEECH_REGION"])
        r = sdk.SpeechSynthesizer(speech_config=cfg, audio_config=None).get_voices_async("pt-PT").get()
        if r.reason == sdk.ResultReason.VoicesListRetrieved:
            return [{"id": v.short_name, "genero": str(v.gender).split(".")[-1].lower(),
                     "nota": ", ".join(v.style_list) if v.style_list and v.style_list[0] else ""}
                    for v in r.voices]
    return [{"id": i, "genero": g, "nota": "lista fixa (sem chave Azure para confirmar)"} for i, g in AZURE_PT_PT]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Listar vozes pt-PT e gerar amostras")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sl = sub.add_parser("listar")
    sl.add_argument("--provider", default="azure", choices=["azure", "local", "piper", "sopro"])
    sa = sub.add_parser("amostras")
    sa.add_argument("--persona", required=True)
    sa.add_argument("--saida", required=True)
    sa.add_argument("--vozes", help="ids ou aliases separados por vírgula (omissão: todas as pt-PT)")
    sa.add_argument("--texto", default=TEXTO_TESTE)
    sa.add_argument("--lexico")
    a = ap.parse_args(argv)

    if a.cmd == "listar":
        for v in listar(a.provider):
            alias = next((k for k, x in ALIASES_VOZ.items() if x == v["id"]), "")
            print(f"{v['id']:<26} {v['genero']:<10} {alias:<10} {v['nota']}")
        return 0

    from tts import amostra
    voz_base = json.loads(Path(a.persona).read_text(encoding="utf-8"))["voz"]
    lex = json.loads(Path(a.lexico).read_text(encoding="utf-8")) if a.lexico and Path(a.lexico).exists() else []
    ids = [s.strip() for s in a.vozes.split(",")] if a.vozes else [v["id"] for v in listar(voz_base["provider"])]
    saida = Path(a.saida)
    for vid in ids:
        voz = {**voz_base, "id": Voz(id=vid, provider=voz_base["provider"]).id}
        destino = saida / f"{voz['id']}.wav"
        print(f"{voz['id']}: {amostra(a.texto, voz, lex, destino)}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

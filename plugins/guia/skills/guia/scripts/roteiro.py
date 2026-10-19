"""Guião de narração da skill /guia: parse, frases, marcadores e normalização por cena.

Formato de narracao.md:
  # Título do guia
  ## cena-01 | Abrir as definições
  > nota de realização (não é lida)
  Comece por clicar no [[avatar]]avatar. Escolha [[menu]]Definições › Faturação.

[[id]] ancora um evento visual (destaque, clique, zoom) na palavra seguinte.

Uso:
  python roteiro.py --guiao narracao.md [--lexico lex.json] [--tratamento voce] --saida preparado.json
Sai com código 1 se houver problemas de nível "erro".
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from normalize_pt import normalize

MARCADOR = re.compile(r"\[\[([\w-]+)\]\]")
CABECALHO = re.compile(r"^##\s+(\S+)\s*\|\s*(.+?)\s*$")
TOKEN = re.compile(r"\w+(?:[-']\w+)*")
ABREV_FIM = ("p. ex.", "ex.", "Sr.", "Sra.", "Dr.", "Dra.", "n.º", "pág.", "tel.", "aprox.", "etc.")


@dataclass
class Cena:
    id: str
    titulo: str
    texto: str


def parse(md: str) -> list[Cena]:
    cenas: list[Cena] = []
    atual = None
    linhas: list[str] = []
    for linha in md.splitlines():
        m = CABECALHO.match(linha)
        if m:
            if atual:
                cenas.append(Cena(atual[0], atual[1], " ".join(linhas).strip()))
            atual, linhas = (m[1], m[2]), []
        elif atual and linha.strip() and not linha.lstrip().startswith((">", "#")):
            linhas.append(linha.strip())
    if atual:
        cenas.append(Cena(atual[0], atual[1], " ".join(linhas).strip()))
    return cenas


def frases(texto: str) -> list[str]:
    out, inicio = [], 0
    for m in re.finditer(r"[.!?…]+\s+(?=[A-ZÀ-Ý\"«\[])", texto):
        antes = texto[inicio:m.end()].rstrip()
        if antes.endswith(ABREV_FIM):
            continue
        out.append(antes)
        inicio = m.end()
    resto = texto[inicio:].strip()
    if resto:
        out.append(resto)
    return out


def tokens(texto: str) -> list[str]:
    return TOKEN.findall(texto)


def _sem_marcadores(s: str) -> str:
    return re.sub(r"\s{2,}", " ", MARCADOR.sub("", s)).strip()


def preparar(cena: Cena, lexicon: list[dict], tratamento: str | None = None) -> dict:
    out_frases, marcadores, issues = [], [], []
    offset = 0
    for f in frases(cena.texto):
        original = _sem_marcadores(f)
        r = normalize(original, lexicon=lexicon, tratamento=tratamento)
        issues += [asdict(i) for i in r.issues]
        n_tokens = len(tokens(r.text))
        for m in MARCADOR.finditer(f):
            prefixo = _sem_marcadores(f[:m.start()])
            idx = len(tokens(normalize(prefixo, lexicon=lexicon).text)) if prefixo else 0
            marcadores.append({"id": m[1], "palavra": offset + idx})
        out_frases.append({"original": original, "normalizado": r.text,
                           "w0": offset, "w1": offset + n_tokens - 1})
        offset += n_tokens
    for mk in marcadores:
        if mk["palavra"] >= offset:
            issues.append({"nivel": "erro", "regra": "marcador",
                           "mensagem": f"[[{mk['id']}]] não tem palavra a seguir na cena {cena.id}"})
    vistos = set()
    for mk in marcadores:
        if mk["id"] in vistos:
            issues.append({"nivel": "erro", "regra": "marcador", "mensagem": f"[[{mk['id']}]] repetido"})
        vistos.add(mk["id"])
    return {"id": cena.id, "titulo": cena.titulo,
            "texto": " ".join(f["normalizado"] for f in out_frases),
            "frases": out_frases, "marcadores": marcadores, "issues": issues}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Preparar o guião de narração para TTS")
    ap.add_argument("--guiao", required=True)
    ap.add_argument("--lexico")
    ap.add_argument("--tratamento", choices=["voce", "tu", "impessoal"])
    ap.add_argument("--saida", required=True)
    a = ap.parse_args(argv)

    md = Path(a.guiao).read_text(encoding="utf-8")
    lex = json.loads(Path(a.lexico).read_text(encoding="utf-8")) if a.lexico and Path(a.lexico).exists() else []
    cenas = [preparar(c, lex, a.tratamento) for c in parse(md)]
    if not cenas:
        print("erro: nenhuma cena encontrada (cabeçalhos '## <id> | <título>')", file=sys.stderr)
        return 1
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps({"cenas": cenas}, ensure_ascii=False, indent=2), encoding="utf-8")

    erros = 0
    for c in cenas:
        palavras = len(tokens(c["texto"]))
        print(f"{c['id']}: {palavras} palavras, {len(c['marcadores'])} marcadores")
        for i in c["issues"]:
            erros += i["nivel"] == "erro"
            print(f"  [{i['nivel']}] {i['regra']}: {i['mensagem']}")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())

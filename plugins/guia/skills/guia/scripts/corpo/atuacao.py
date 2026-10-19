"""Folha de atuação (`cena-NN.atuacao.json`): validação e resolução dos tempos.

É o contrato entre o LLM e o Blender. O LLM só pode usar valores do `vocabulario.json`;
qualquer chave ou valor fora dele é um erro (o render não arranca).

    python atuacao.py --atuacao A --timing T --palavras P --personagem .guia/corpo/<nome>

Formato:
{
  "versao": 1, "cena": "cena-06", "roupa": "casual_trabalho",
  "ajustes_roupa": {"camisola": {"cor": "#9c2b2b", "padrao": "riscas", "cor_padrao": "#fffdf7"}},
  "segmentos": [
    {"desde": "inicio" | "[[marcador]]" | "palavra:texto" | 1.25,
     "emocao": "...", "intensidade": 0.0-1.0, "gesto": "...", "olhar": "...",
     "prop": null | {"id": "...", "mao": "L" | "R"}}
  ],
  "cenario": [{"prop": "...", "ancora": "...", "desde": ..., "ate": ... | null}]
}
"""
import argparse
import json
import os
import re
import sys
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import props_spec  # noqa: E402

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
CHAVES_TOPO = {"versao", "cena", "roupa", "ajustes_roupa", "segmentos", "cenario"}
CHAVES_SEG = {"desde", "emocao", "intensidade", "gesto", "olhar", "prop"}
CHAVES_CENARIO = {"prop", "ancora", "desde", "ate"}
PECAS_ROUPA = {"camisola": {"cor", "padrao", "cor_padrao", "escala"},
               "calcas": {"cor", "padrao", "cor_padrao", "escala"},
               "sapatos": {"cor"}}


def _norm(txt):
    t = unicodedata.normalize("NFD", txt.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if not unicodedata.combining(c)))


def deslocamento_voz(cena):
    return cena["voz_inicio"] - cena["inicio"]


def resolver_tempo(desde, cena, palavras, depois=0.0):
    """Segundos desde o início da cena. `palavra:` procura a 1.ª ocorrência a partir de `depois`."""
    if desde == "inicio":
        return 0.0
    if isinstance(desde, (int, float)) and not isinstance(desde, bool):
        return float(desde)
    if not isinstance(desde, str):
        raise ValueError(f"'desde' inválido: {desde!r}")
    m = re.fullmatch(r"\[\[([\w-]+)\]\]", desde)
    if m:
        for mk in cena.get("marcadores", []):
            if mk["id"] == m.group(1):
                return float(mk["t_cena"])
        raise ValueError(f"marcador {desde} não existe nesta cena")
    if desde.startswith("palavra:"):
        alvo = _norm(desde[len("palavra:"):])
        off = deslocamento_voz(cena)
        for p in palavras:
            t = p["inicio"] + off
            if _norm(p["texto"]) == alvo and t >= depois - 1e-6:
                return t
        raise ValueError(f"palavra '{alvo}' não aparece na narração depois de {depois:.2f}s")
    raise ValueError(f"'desde' inválido: {desde!r} (usa inicio, [[marcador]], palavra:x ou segundos)")


def validar(at, vocab, cena, palavras):
    erros = []
    extra = set(at) - CHAVES_TOPO
    if extra:
        erros.append(f"chaves desconhecidas: {sorted(extra)}")
    if at.get("versao") != 1:
        erros.append("versao tem de ser 1")
    if at.get("cena") != cena["id"]:
        erros.append(f"cena {at.get('cena')!r} não corresponde a {cena['id']!r}")
    if at.get("roupa") not in vocab["roupas"]:
        erros.append(f"roupa {at.get('roupa')!r} não existe (opções: {sorted(vocab['roupas'])})")
    for peca, ajuste in (at.get("ajustes_roupa") or {}).items():
        if peca not in PECAS_ROUPA:
            erros.append(f"ajustes_roupa: peça {peca!r} desconhecida")
            continue
        for k, v in ajuste.items():
            if k not in PECAS_ROUPA[peca]:
                erros.append(f"ajustes_roupa.{peca}: campo {k!r} desconhecido")
            elif k.startswith("cor") and not (isinstance(v, str) and HEX.match(v)):
                erros.append(f"ajustes_roupa.{peca}.{k}: cor {v!r} não é #rrggbb")
            elif k == "padrao" and v not in vocab["padroes"]:
                erros.append(f"ajustes_roupa.{peca}.padrao: {v!r} não existe")
            elif k == "escala" and not (isinstance(v, (int, float)) and 1 <= v <= 40):
                erros.append(f"ajustes_roupa.{peca}.escala: {v!r} fora de 1–40")

    segs = at.get("segmentos")
    if not isinstance(segs, list) or not segs:
        erros.append("segmentos tem de ser uma lista não vazia")
        segs = []
    t_ant = -1.0
    for i, s in enumerate(segs):
        tag = f"segmentos[{i}]"
        extra = set(s) - CHAVES_SEG
        if extra:
            erros.append(f"{tag}: chaves desconhecidas {sorted(extra)}")
        if s.get("emocao") not in vocab["emocoes"]:
            erros.append(f"{tag}: emocao {s.get('emocao')!r} não existe")
        if s.get("gesto", "repouso") not in vocab["gestos"]:
            erros.append(f"{tag}: gesto {s.get('gesto')!r} não existe")
        if s.get("olhar", "frente") not in vocab["olhar"]:
            erros.append(f"{tag}: olhar {s.get('olhar')!r} não existe")
        intens = s.get("intensidade", 0.7)
        if not (isinstance(intens, (int, float)) and 0 <= intens <= 1):
            erros.append(f"{tag}: intensidade {intens!r} fora de 0–1")
        prop = s.get("prop")
        if prop is not None:
            if not isinstance(prop, dict) or set(prop) - {"id", "mao"}:
                erros.append(f"{tag}: prop tem de ser {{id, mao}} ou null")
            elif vocab["props"].get(prop.get("id"), {}).get("tipo") != "mao":
                erros.append(f"{tag}: prop {prop.get('id')!r} não é um prop de mão do vocabulário")
            elif prop.get("mao") not in ("L", "R"):
                erros.append(f"{tag}: mao tem de ser 'L' ou 'R'")
        try:
            t = resolver_tempo(s.get("desde"), cena, palavras, max(t_ant, 0.0))
            if t <= t_ant:
                erros.append(f"{tag}: começa em {t:.2f}s, antes ou ao mesmo tempo que o anterior")
            if t >= cena["duracao"]:
                erros.append(f"{tag}: começa em {t:.2f}s, depois do fim da cena ({cena['duracao']:.2f}s)")
            t_ant = t
        except ValueError as e:
            erros.append(f"{tag}: {e}")
    if segs and segs[0].get("desde") != "inicio":
        erros.append("segmentos[0] tem de começar em 'inicio'")

    for i, c in enumerate(at.get("cenario") or []):
        tag = f"cenario[{i}]"
        extra = set(c) - CHAVES_CENARIO
        if extra:
            erros.append(f"{tag}: chaves desconhecidas {sorted(extra)}")
        if vocab["props"].get(c.get("prop"), {}).get("tipo") != "cenario":
            erros.append(f"{tag}: {c.get('prop')!r} não é um prop de cenário do vocabulário")
        if c.get("ancora") not in vocab["ancoras"]:
            erros.append(f"{tag}: ancora {c.get('ancora')!r} não existe")
        for campo in ("desde", "ate"):
            if campo == "ate" and c.get("ate") is None:
                continue
            try:
                resolver_tempo(c.get(campo), cena, palavras)
            except ValueError as e:
                erros.append(f"{tag}.{campo}: {e}")
    return erros


def resolver(at, vocab, cena, palavras):
    """Devolve a atuação com tempos em segundos (`t`, `t_ate`) e valores por omissão."""
    segs, t_ant = [], 0.0
    for s in at["segmentos"]:
        t = resolver_tempo(s["desde"], cena, palavras, t_ant)
        segs.append({"t": t, "emocao": s["emocao"], "intensidade": s.get("intensidade", 0.7),
                     "gesto": s.get("gesto", "repouso"), "olhar": s.get("olhar", "frente"),
                     "prop": s.get("prop")})
        t_ant = t
    cenario = []
    for c in at.get("cenario") or []:
        cenario.append({"prop": c["prop"], "ancora": c["ancora"],
                        "t": resolver_tempo(c["desde"], cena, palavras),
                        "t_ate": None if c.get("ate") is None else resolver_tempo(c["ate"], cena, palavras)})
    roupa = json.loads(json.dumps(vocab["roupas"][at["roupa"]]))
    for peca, ajuste in (at.get("ajustes_roupa") or {}).items():
        roupa.setdefault(peca, {}).update(ajuste)
    return {"cena": cena, "segmentos": segs, "cenario": cenario, "roupa": roupa}


def _ler(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def carregar_vocabulario(personagem):
    """vocabulario.json da personagem + os props declarados em props/*.json (o menu do LLM)."""
    vocab = _ler(os.path.join(personagem, "vocabulario.json"))
    specs, erros = props_spec.ler_todos(os.path.join(personagem, "props"))
    if erros:
        raise ValueError("props inválidos:\n- " + "\n- ".join(erros))
    vocab["props"] = props_spec.resumo(specs)
    return vocab


def carregar(caminho_atuacao, caminho_timing, caminho_palavras, personagem):
    at, timing, palavras = map(_ler, (caminho_atuacao, caminho_timing, caminho_palavras))
    vocab = carregar_vocabulario(personagem)
    cena = next((c for c in timing["cenas"] if c["id"] == at.get("cena")), None)
    if cena is None:
        return at, vocab, None, palavras, [f"cena {at.get('cena')!r} não existe em timing.json"]
    return at, vocab, cena, palavras, validar(at, vocab, cena, palavras)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--atuacao", required=True)
    ap.add_argument("--timing", required=True)
    ap.add_argument("--palavras", required=True)
    ap.add_argument("--personagem", required=True, help="pasta .guia/corpo/<personagem>")
    a = ap.parse_args()
    at, vocab, cena, palavras, erros = carregar(a.atuacao, a.timing, a.palavras, a.personagem)
    if erros:
        print("ATUACAO_INVALIDA\n- " + "\n- ".join(erros))
        sys.exit(1)
    r = resolver(at, vocab, cena, palavras)
    for s in r["segmentos"]:
        print(f"{s['t']:6.2f}s  {s['emocao']:<11} {s['gesto']:<15} {s['olhar']:<8} {s['prop'] or ''}")
    for c in r["cenario"]:
        print(f"{c['t']:6.2f}s  cenário {c['prop']} @ {c['ancora']}")
    print("ATUACAO_OK")


if __name__ == "__main__":
    main()

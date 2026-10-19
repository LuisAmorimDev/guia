"""Normalização de texto pt-PT para TTS.

Transforma o guião legível no texto que o motor de voz lê: números por extenso
(com concordância de género), datas, horas, moeda, percentagens, códigos,
abreviaturas e símbolos. Não reescreve o que não sabe tratar: sinaliza-o como
problema (URLs, identificadores de código, siglas desconhecidas) para o guião
ser corrigido na origem.

Uso:
  python normalize_pt.py --texto "Custa 12,50 €" [--lexico lex.json] [--tratamento voce] [--json]
  python normalize_pt.py --ficheiro cena.txt ...
Sai com código 1 quando há problemas de nível "erro".
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field

from num2words import num2words

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

# Substantivos terminados em -a que são masculinos (o resto em -a assume-se feminino).
MASC_EM_A = {
    "dia", "mapa", "sistema", "problema", "programa", "tema", "esquema", "idioma",
    "clima", "planeta", "diagrama", "cinema", "poema", "drama", "telefonema",
    "emblema", "teorema", "dilema", "panorama", "guia", "pijama", "fantasma",
}
# Substantivos femininos que não terminam em -a.
FEM_OUTROS = {
    "vez", "vezes", "chave", "rede", "parte", "fase", "noite", "tarde", "cor", "cores", "lei",
    "ordem", "ordens", "nuvem", "mulher", "imagem", "mensagem", "viagem", "linguagem",
    "contagem", "margem", "origem", "sede", "base", "classe", "frase", "fonte",
}
FEM_SUFIXOS = ("ção", "ções", "são", "sões", "dade", "dades", "gem", "gens", "tude", "tudes")

ABREVIATURAS = [
    (r"\bp\.\s?ex\.", "por exemplo"),
    (r"\bex\.:", "exemplo:"),
    (r"\b[Nn]\.?º\s?", "número "),
    (r"\b[Nn]\.os\s?", "números "),
    (r"\bSr\.ª", "senhora"), (r"\bSra\.", "senhora"), (r"\bSr\.", "senhor"),
    (r"\bDr\.ª", "doutora"), (r"\bDra\.", "doutora"), (r"\bDr\.", "doutor"),
    (r"\bEng\.ª", "engenheira"), (r"\bEng\.º", "engenheiro"),
    (r"\bpágs\.", "páginas"), (r"\bpág\.", "página"),
    (r"\btel\.", "telefone"), (r"\baprox\.", "aproximadamente"),
    (r"\bmáx\.", "máximo"), (r"\bmín\.", "mínimo"),
]

UNIDADES = {"KB": "kilobyte", "MB": "megabyte", "GB": "gigabyte", "TB": "terabyte"}

NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?"


@dataclass
class Issue:
    nivel: str      # "erro" | "aviso" | "info"
    regra: str
    mensagem: str


@dataclass
class NormResult:
    text: str
    issues: list[Issue] = field(default_factory=list)


# ---------------------------------------------------------------- números

def _int(s: str) -> int:
    return int(s.replace(".", ""))


def cardinal(n: int, feminino: bool = False) -> str:
    txt = num2words(n, lang="pt")
    return _feminizar(txt) if feminino else txt


def _feminizar(txt: str) -> str:
    toks = txt.split()
    out = []
    for i, t in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        if nxt.startswith(("milhão", "milhões", "bilião", "biliões")):
            out.append(t)
        elif t == "um":
            out.append("uma")
        elif t == "dois":
            out.append("duas")
        elif t.endswith("entos"):
            out.append(t[:-5] + "entas")
        else:
            out.append(t)
    return " ".join(out)


def ordinal(n: int, feminino: bool = False) -> str:
    txt = num2words(n, lang="pt", to="ordinal")
    if feminino:
        txt = " ".join(w[:-1] + "a" if w.endswith("o") else w for w in txt.split())
    return txt


def e_feminino(palavra: str) -> bool:
    p = palavra.lower()
    singular = p[:-1] if p.endswith("s") and len(p) > 3 else p
    if p in MASC_EM_A or singular in MASC_EM_A:
        return False
    if p in FEM_OUTROS or singular in FEM_OUTROS:
        return True
    if p.endswith(FEM_SUFIXOS):
        return True
    return singular.endswith("a")


def decimal(s: str) -> str:
    inteiro, frac = s.split(",")
    lead = len(frac) - len(frac.lstrip("0"))
    resto = frac.lstrip("0")
    partes = ["zero"] * lead + ([cardinal(int(resto))] if resto else [])
    return f"{cardinal(_int(inteiro))} vírgula {' '.join(partes)}"


def numero(s: str) -> str:
    return decimal(s) if "," in s else cardinal(_int(s))


def euros(s: str) -> str:
    inteiro, _, frac = s.partition(",")
    e = _int(inteiro)
    c = int((frac + "00")[:2]) if frac else 0
    partes = []
    if e:
        partes.append(f"{cardinal(e)} {'euro' if e == 1 else 'euros'}")
    if c:
        partes.append(f"{cardinal(c)} {'cêntimo' if c == 1 else 'cêntimos'}")
    return " e ".join(partes) or "zero euros"


def hora(h: int, m: int) -> str:
    hh = cardinal(h, feminino=True)
    if m == 0:
        return f"{hh} {'hora' if h == 1 else 'horas'}"
    return f"{hh} e {cardinal(m)}"


def digitos(s: str) -> str:
    return " ".join(cardinal(int(d)) for d in s)


# ---------------------------------------------------------------- deteção

URL_RE = re.compile(r"https?://\S+|www\.\S+|\b[\w.+-]+@[\w-]+\.[\w.]+|(?<![\w/])/[A-Za-z][\w-]*(?:/[\w\-\[\]]+)*")
CAMEL_RE = re.compile(r"\b[a-z]+[A-Z][A-Za-z0-9]*\b")
SNAKE_RE = re.compile(r"\b[A-Za-z0-9]+_[A-Za-z0-9_]+\b")
TICK_RE = re.compile(r"`[^`]+`")
SIGLA_RE = re.compile(r"\b[A-Z]{2,6}\b")


def detetar(text: str) -> list[Issue]:
    issues = []
    for m in URL_RE.finditer(text):
        issues.append(Issue("erro", "url", f"'{m.group()}': não ler URLs, rotas ou emails; descreva o destino (ex.: 'a página Faturação')"))
    for rx in (TICK_RE, CAMEL_RE, SNAKE_RE):
        for m in rx.finditer(text):
            issues.append(Issue("erro", "codigo", f"'{m.group()}': identificador de código; use o nome que o utilizador vê no ecrã"))
    return issues


# ---------------------------------------------------------------- normalização

def _aplicar_lexico(text: str, lexicon: list[dict]) -> str:
    for ent in sorted(lexicon, key=lambda e: -len(e["termo"])):
        dizer = ent.get("dizer") or ent["termo"]
        text = re.sub(rf"(?<!\w){re.escape(ent['termo'])}(?!\w)", lambda _m, d=dizer: d, text)
    return text


def _plain_ints(text: str) -> str:
    def rep(m):
        n = _int(m.group(1))
        seguinte = re.match(r"\s+([A-Za-zÀ-ÿ]+)", m.string[m.end():])
        fem = bool(seguinte) and e_feminino(seguinte.group(1))
        return cardinal(n, feminino=fem)
    return re.sub(r"(?<![\w,])(\d{1,3}(?:\.\d{3})+|\d+)(?![\w,])", rep, text)


def normalize(text: str, lexicon: list[dict] | None = None, tratamento: str | None = None) -> NormResult:
    lexicon = lexicon or []
    issues = detetar(text)
    t = _aplicar_lexico(text, lexicon)

    # abreviaturas
    t = re.sub(r"\betc\.(?=\s*$|\s+[A-ZÀ-Ý])", "etcétera.", t)
    t = re.sub(r"\betc\.", "etcétera", t)
    for rx, rep in ABREVIATURAS:
        t = re.sub(rx, rep, t)

    # datas, horas
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b",
               lambda m: f"{cardinal(int(m[1]))} de {MESES[int(m[2]) - 1]} de {cardinal(int(m[3]))}", t)
    t = re.sub(r"\b(\d{1,2})h(\d{2})?\b", lambda m: hora(int(m[1]), int(m[2] or 0)), t)
    t = re.sub(r"\b(\d{1,2}):(\d{2})\b", lambda m: hora(int(m[1]), int(m[2])), t)

    # moeda, percentagem, unidades
    t = re.sub(rf"€\s?({NUM})", lambda m: euros(m[1]), t)
    t = re.sub(rf"({NUM})\s?€", lambda m: euros(m[1]), t)
    t = re.sub(rf"({NUM})\s?%", lambda m: f"{numero(m[1])} por cento", t)
    t = re.sub(rf"({NUM})\s?(KB|MB|GB|TB)\b",
               lambda m: f"{numero(m[1])} {UNIDADES[m[2]]}{'' if m[1] == '1' else 's'}", t)

    # ordinais e códigos
    t = re.sub(r"\b(\d+)\.?\s?º", lambda m: ordinal(int(m[1])), t)
    t = re.sub(r"\b(\d+)\.?\s?ª", lambda m: ordinal(int(m[1]), feminino=True), t)
    t = re.sub(r"\b(\d{4})-(\d{3})\b", lambda m: f"{digitos(m[1])}, traço, {digitos(m[2])}", t)

    # decimais e inteiros
    t = re.sub(r"(?<![\w.])(\d+,\d+)(?!\w)", lambda m: decimal(m[1]), t)
    t = _plain_ints(t)

    # símbolos e pontuação
    t = re.sub(r"\s*[›»→]\s*|\s+>\s+", ", ", t)
    t = re.sub(r"\s+&\s+", " e ", t)
    t = re.sub(r"\s+\+\s+", " mais ", t)
    t = re.sub(r"\be/ou\b", "e ou", t)
    t = re.sub(r"\s+[–—]\s+", ", ", t)
    t = re.sub(r"[\"“”«]", "", t)
    t = re.sub(r"\s*\(\s*", ", ", t)
    t = re.sub(r"\s*\)\s*", ", ", t)
    t = re.sub(r"[•☀-➿\U0001F300-\U0001FAFF]", "", t)
    t = re.sub(r",\s*([.,;:!?])", r"\1", t)
    t = re.sub(r",\s*$", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip()

    conhecidos = {e["termo"] for e in lexicon}
    for m in SIGLA_RE.finditer(t):
        if m.group() not in conhecidos:
            issues.append(Issue("info", "sigla", f"'{m.group()}': sigla sem entrada no léxico; confirme a pronúncia na amostra"))

    if tratamento:
        issues += check_tratamento(text, tratamento)
    issues += lint_pt_pt(text)
    return NormResult(t, _dedup(issues))


def _dedup(issues: list[Issue]) -> list[Issue]:
    seen, out = set(), []
    for i in issues:
        k = (i.regra, i.mensagem)
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out


# ---------------------------------------------------------------- tratamento

# (forma de "você", forma de "tu") dos imperativos mais comuns em guias de interface
IMPERATIVOS = [
    ("clique", "clica"), ("escolha", "escolhe"), ("abra", "abre"), ("selecione", "seleciona"),
    ("introduza", "introduz"), ("preencha", "preenche"), ("guarde", "guarda"),
    ("carregue", "carrega"), ("toque", "toca"), ("vá", "vai"), ("aceda", "acede"),
    ("confirme", "confirma"), ("escreva", "escreve"), ("arraste", "arrasta"), ("veja", "vê"),
    ("use", "usa"), ("altere", "altera"), ("defina", "define"), ("ative", "ativa"),
    ("desative", "desativa"), ("elimine", "elimina"), ("adicione", "adiciona"), ("crie", "cria"),
    ("insira", "insere"), ("procure", "procura"), ("pressione", "pressiona"), ("feche", "fecha"),
    ("copie", "copia"), ("cole", "cola"), ("descarregue", "descarrega"), ("partilhe", "partilha"),
]
# Só conta como imperativo no início de frase/oração, para não confundir "O sistema guarda…".
_POS_IMPERATIVO = r"(?:^|[.!?:;,]\s*|\be\s+|\bdepois\s+|\bagora\s+)"


def _imperativos(text: str, formas: set[str]) -> list[str]:
    achados = []
    for m in re.finditer(rf"{_POS_IMPERATIVO}([A-Za-zÀ-ÿ]+)(?:\s+([A-Za-zÀ-ÿ]+))?", text, flags=re.IGNORECASE | re.MULTILINE):
        seguinte = (m.group(2) or "").lower()
        # "vai aprender", "pode alterar": perífrase com infinitivo, não imperativo
        if seguinte.endswith(("ar", "er", "ir", "or")) and len(seguinte) > 3:
            continue
        if m.group(1).lower() in formas:
            achados.append(m.group(1))
    return achados


def check_tratamento(text: str, tratamento: str) -> list[Issue]:
    voce = {a for a, _ in IMPERATIVOS}
    tu = {b for _, b in IMPERATIVOS}
    issues: list[Issue] = []
    if tratamento == "voce":
        for w in _imperativos(text, tu):
            issues.append(Issue("aviso", "tratamento", f"'{w}' é forma de 'tu'; a persona usa 'você'"))
        for m in re.finditer(r"\b(tu|teu|tua|teus|tuas|contigo)\b|-te\b", text, flags=re.IGNORECASE):
            issues.append(Issue("aviso", "tratamento", f"'{m.group()}' é de 'tu'; a persona usa 'você'"))
        for m in re.finditer(r"\b[Vv]ocê(s)?\b", text):
            issues.append(Issue("aviso", "tratamento", f"'{m.group()}' explícito soa pouco natural em pt-PT; prefira omitir o sujeito"))
    elif tratamento == "tu":
        for w in _imperativos(text, voce):
            issues.append(Issue("aviso", "tratamento", f"'{w}' é forma de 'você'; a persona usa 'tu'"))
        for m in re.finditer(r"\b[Vv]ocê(s)?\b", text):
            issues.append(Issue("aviso", "tratamento", f"'{m.group()}': a persona usa 'tu'"))
    elif tratamento == "impessoal":
        for w in _imperativos(text, voce | tu):
            issues.append(Issue("aviso", "tratamento", f"'{w}' é imperativo; a persona é impessoal (ex.: 'Clicar em…')"))
    return issues


# ---------------------------------------------------------------- pt-BR

PT_BR = {
    "tela": "ecrã", "telas": "ecrãs", "usuário": "utilizador", "usuários": "utilizadores",
    "usuária": "utilizadora", "arquivo": "ficheiro", "arquivos": "ficheiros", "salvar": "guardar",
    "salve": "guarde", "celular": "telemóvel", "senha": "palavra-passe", "senhas": "palavras-passe",
    "deletar": "eliminar", "baixar": "transferir", "baixe": "transfira",
    "cadastro": "registo", "cadastrar": "registar", "cadastre": "registe", "registro": "registo",
    "contato": "contacto", "câmera": "câmara", "planilha": "folha de cálculo", "mouse": "rato",
    "aplicativo": "aplicação", "aplicativos": "aplicações", "ônibus": "autocarro",
}


def lint_pt_pt(text: str) -> list[Issue]:
    issues = []
    for m in re.finditer(r"[A-Za-zÀ-ÿ]+", text):
        w = m.group()
        if w.lower() in PT_BR:
            issues.append(Issue("aviso", "pt-br", f"'{w}' é de pt-BR; em pt-PT use '{PT_BR[w.lower()]}' (exceto se for o texto exato da interface)"))
    for m in re.finditer(r"\b(est(?:ar|ou|á|ás|amos|ão|ava|avam|eja|ejam|eve|ive)|fica|ficar|continua|continuar)\s+([A-Za-zÀ-ÿ]+ndo)\b", text, flags=re.IGNORECASE):
        issues.append(Issue("aviso", "gerundio", f"'{m.group()}': em pt-PT use 'a + infinitivo' (ex.: 'está a carregar')"))
    return issues


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--texto")
    src.add_argument("--ficheiro")
    ap.add_argument("--lexico", help="JSON: lista de {termo, dizer, ipa?}")
    ap.add_argument("--tratamento", choices=["voce", "tu", "impessoal"])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    text = a.texto if a.texto is not None else open(a.ficheiro, encoding="utf-8").read()
    lex = json.load(open(a.lexico, encoding="utf-8")) if a.lexico else []
    r = normalize(text, lexicon=lex, tratamento=a.tratamento)
    if a.json:
        print(json.dumps({"text": r.text, "issues": [asdict(i) for i in r.issues]}, ensure_ascii=False, indent=2))
    else:
        print(r.text)
        for i in r.issues:
            print(f"[{i.nivel}] {i.regra}: {i.mensagem}", file=sys.stderr)
    return 1 if any(i.nivel == "erro" for i in r.issues) else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())

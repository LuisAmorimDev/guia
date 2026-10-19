"""Props declarativos: `<personagem>/props/<id>.json` — validação e leitura (sem Blender).

Um prop é uma lista de peças de papel (o LLM pode escrevê-lo) ou um .blend dado pelo utilizador:

{
  "id": "telemovel", "tipo": "mao" | "cenario", "mao": "L" | "R" | "ambas" | "",
  "descricao": "telemóvel com a app aberta", "tags": ["tecnologia"],
  "pecas": [
    {"nome": "corpo", "forma": "retangulo", "centro": [0, 0.06], "tamanho": [0.15, 0.28], "raio": 0.025,
     "cor": "#10161f", "camada": 0, "sombra": true, "grao": 0.03},
    {"forma": "elipse", "centro": [x, z], "raios": [rx, rz]},
    {"forma": "poligono", "pontos": [[x, z], ...]},
    {"forma": "capsula", "de": [x, z], "ate": [x, z], "raios": [r0, r1]},
    {"forma": "arco", "centro": [x, z], "raio": r, "espessura": e, "angulos": [a0, a1]}
  ]
}
ou, em vez de "pecas": "blend": "<id>.blend" (coleção `Prop.<id>` que cumpra o contrato).

Unidades do rig: a cabeça da personagem tem ≈ 0.6 de largura e 2.35 de altura total.
A origem (0, 0) é a PEGA: fica no osso `encaixe.mao.*` (mão) ou na âncora (cenário).
"""
import json
import os
import re

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
FORMAS = {
    "retangulo": {"centro": 2, "tamanho": 2},
    "elipse": {"centro": 2, "raios": 2},
    "poligono": {"pontos": None},
    "capsula": {"de": 2, "ate": 2, "raios": 2},
    "arco": {"centro": 2, "raio": 0, "espessura": 0, "angulos": 2},
}
OPCIONAIS = {"nome", "forma", "cor", "camada", "sombra", "grao", "raio"}
TAMANHO_MAX = {"mao": 0.6, "cenario": 2.5}
CAMADA_MAX_MAO = 0.2  # acima disto o prop passaria à frente da mão que o segura


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _vec(v, n):
    return isinstance(v, list) and len(v) == n and all(_num(x) for x in v)


def caixa(peca):
    """Caixa aproximada (xmin, zmin, xmax, zmax) de uma peça válida."""
    f = peca["forma"]
    if f == "retangulo":
        (cx, cz), (w, h) = peca["centro"], peca["tamanho"]
        return cx - w / 2, cz - h / 2, cx + w / 2, cz + h / 2
    if f == "elipse":
        (cx, cz), (rx, rz) = peca["centro"], peca["raios"]
        return cx - rx, cz - rz, cx + rx, cz + rz
    if f == "poligono":
        xs, zs = [p[0] for p in peca["pontos"]], [p[1] for p in peca["pontos"]]
        return min(xs), min(zs), max(xs), max(zs)
    if f == "capsula":
        (x0, z0), (x1, z1), (r0, r1) = peca["de"], peca["ate"], peca["raios"]
        r = max(r0, r1)
        return min(x0, x1) - r, min(z0, z1) - r, max(x0, x1) + r, max(z0, z1) + r
    (cx, cz), r = peca["centro"], peca["raio"] + peca["espessura"] / 2
    return cx - r, cz - r, cx + r, cz + r


def validar(spec, pid_esperado=None, pasta=None):
    erros = []
    pid = spec.get("id")
    if not isinstance(pid, str) or not re.fullmatch(r"[a-z0-9_]+", pid or ""):
        erros.append(f"id {pid!r} tem de ser minúsculas, dígitos ou _")
    if pid_esperado and pid != pid_esperado:
        erros.append(f"id {pid!r} difere do nome do ficheiro ({pid_esperado})")
    tag = pid or "?"
    extra = set(spec) - {"id", "tipo", "mao", "descricao", "tags", "pecas", "blend"}
    if extra:
        erros.append(f"{tag}: chaves desconhecidas {sorted(extra)}")
    tipo = spec.get("tipo")
    if tipo not in ("mao", "cenario"):
        erros.append(f"{tag}: tipo tem de ser 'mao' ou 'cenario'")
    if spec.get("mao", "") not in ("L", "R", "ambas", ""):
        erros.append(f"{tag}: mao tem de ser L, R, ambas ou vazio")
    if not isinstance(spec.get("descricao"), str) or not spec.get("descricao"):
        erros.append(f"{tag}: falta a descricao (o LLM escolhe props por ela)")
    tem_pecas, tem_blend = "pecas" in spec, "blend" in spec
    if tem_pecas == tem_blend:
        erros.append(f"{tag}: usa 'pecas' ou 'blend' (um dos dois)")
    if tem_blend and pasta and not os.path.isfile(os.path.join(pasta, spec["blend"])):
        erros.append(f"{tag}: ficheiro {spec['blend']} não existe em props/")
    caixas = []
    for i, p in enumerate(spec.get("pecas") or []):
        t = f"{tag}.pecas[{i}]"
        forma = p.get("forma")
        if forma not in FORMAS:
            erros.append(f"{t}: forma {forma!r} desconhecida ({sorted(FORMAS)})")
            continue
        req = FORMAS[forma]
        extra = set(p) - OPCIONAIS - set(req)
        if extra:
            erros.append(f"{t}: chaves desconhecidas {sorted(extra)}")
        ok = True
        for k, n in req.items():
            v = p.get(k)
            if n is None:
                valido = isinstance(v, list) and len(v) >= 3 and all(_vec(q, 2) for q in v)
            else:
                valido = _num(v) if n == 0 else _vec(v, n)
            if not valido:
                erros.append(f"{t}: '{k}' inválido")
                ok = False
        if not (isinstance(p.get("cor"), str) and HEX.match(p["cor"])):
            erros.append(f"{t}: cor tem de ser #rrggbb")
        camada = p.get("camada", 0)
        lim = CAMADA_MAX_MAO if tipo == "mao" else 1.0
        if not (_num(camada) and 0 <= camada <= lim):
            erros.append(f"{t}: camada {camada!r} fora de 0–{lim}")
        if ok:
            caixas.append(caixa(p))
    if tem_pecas and not caixas and not erros:
        erros.append(f"{tag}: sem peças")
    if caixas and tipo in TAMANHO_MAX:
        largura = max(c[2] for c in caixas) - min(c[0] for c in caixas)
        altura = max(c[3] for c in caixas) - min(c[1] for c in caixas)
        if max(largura, altura) > TAMANHO_MAX[tipo]:
            erros.append(f"{tag}: {max(largura, altura):.2f} de tamanho > {TAMANHO_MAX[tipo]} para '{tipo}'")
    return erros


def ler_todos(pasta_props):
    """{id: spec} e a lista de erros de todos os props/*.json."""
    specs, erros = {}, []
    if not os.path.isdir(pasta_props):
        return specs, erros
    for nome in sorted(os.listdir(pasta_props)):
        if not nome.endswith(".json"):
            continue
        pid = nome[:-5]
        try:
            with open(os.path.join(pasta_props, nome), encoding="utf-8") as f:
                spec = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            erros.append(f"{nome}: {e}")
            continue
        erros += validar(spec, pid, pasta_props)
        specs[pid] = spec
    return specs, erros


def resumo(specs):
    """O que entra no vocabulário (o que o LLM vê): {id: {tipo, mao, descricao, tags}}."""
    return {pid: {"tipo": s.get("tipo"), "mao": s.get("mao", ""), "descricao": s.get("descricao", ""),
                  "tags": s.get("tags", [])} for pid, s in specs.items()}

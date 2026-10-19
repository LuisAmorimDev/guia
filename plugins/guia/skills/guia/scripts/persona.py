"""Personas da skill /guia: voz, escrita, visual e áudio guardados para reutilizar.

Locais (o projeto ganha ao global com o mesmo nome):
  global : $GUIA_HOME/personas/<nome>/persona.yaml   (GUIA_HOME = ~/.claude/guia)
  projeto: <repo>/.guia/personas/<nome>/persona.yaml
Prioridade: --set da chamada > --persona > persona_padrao em .guia/config.yaml > "padrao".

Uso:
  python persona.py listar   [--projeto .]
  python persona.py mostrar  <nome> [--projeto .]
  python persona.py resolver [--persona nome] [--set voz.id=duarte]... [--projeto .] [--saida f.json]
  python persona.py guardar  --de persona.yaml|json --nivel global|projeto [--projeto .]
  python persona.py apagar   <nome> --nivel global|projeto [--projeto .]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

ASSET_PADRAO = Path(__file__).resolve().parent.parent / "assets" / "personas" / "padrao.yaml"

# Só motores com licença clara para uso comercial. edge-tts NÃO entra (serviço não oficial).
PROVIDERS = ("azure", "local", "piper", "sopro")

ALIASES_VOZ = {
    "raquel": "pt-PT-RaquelNeural",
    "duarte": "pt-PT-DuarteNeural",
    "fernanda": "pt-PT-FernandaNeural",
}


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Voz(_Base):
    provider: str = "azure"
    id: str = "pt-PT-RaquelNeural"
    velocidade: str = "+0%"
    tom_voz: str = "+0Hz"
    volume: str = "+0%"
    pausa_entre_frases_ms: int = 300
    pausa_inicio_cena_ms: int = 400
    pausa_fim_cena_ms: int = 700

    @field_validator("provider")
    @classmethod
    def _provider(cls, v):
        if v not in PROVIDERS:
            raise ValueError(f"provider '{v}' não suportado; use um de {PROVIDERS} (só motores com licença comercial)")
        return v

    @field_validator("id")
    @classmethod
    def _alias(cls, v):
        return ALIASES_VOZ.get(v.lower(), v)


class Escrita(_Base):
    tratamento: Literal["voce", "tu", "impessoal"] = "voce"
    tom: str = "didatico"
    registo: str = ""
    palavras_por_minuto: int = 150
    abertura: Optional[str] = None
    fecho: Optional[str] = None
    evitar: list[str] = []


class Legendas(_Base):
    estilo: str = "barra-inferior"
    gravadas: bool = False


class Visual(_Base):
    formato: Literal["landscape", "vertical", "square"] = "landscape"
    ritmo_cortes: Literal["calmo", "medio", "rapido"] = "calmo"
    destaque: str = ""
    cursor: str = "sistema"
    legendas: Legendas = Legendas()
    marca: str = "herdar-do-projeto"


class Musica(_Base):
    ativa: bool = False
    volume: float = 0.08


class Audio(_Base):
    musica: Musica = Musica()
    sfx: str = "apenas-cliques"


class Corpo(_Base):
    """Ator 2D de papel recortado (Blender). Dados em <repo>/.guia/corpo/<personagem>/."""
    ativo: bool = False
    personagem: str = "colega"
    roupa: Optional[str] = None  # roupa por omissão; tem de existir no vocabulario.json da personagem
    cenas: Literal["historias", "todas"] = "historias"  # historias = cenas de conceito/situação, sem app
    lado: Literal["esquerda", "direita", "livre"] = "livre"
    altura_px: int = 640  # altura da personagem no ecrã do vídeo


class Referencia(_Base):
    origem: str
    extraido: str = ""


class Persona(_Base):
    nome: str
    versao: int = 0
    descricao: str = ""
    voz: Voz = Voz()
    escrita: Escrita = Escrita()
    visual: Visual = Visual()
    audio: Audio = Audio()
    corpo: Corpo = Corpo()
    referencias: list[Referencia] = []
    amostra: Optional[str] = None


# ---------------------------------------------------------------- locais

def home_global() -> Path:
    return Path(os.environ.get("GUIA_HOME", Path.home() / ".claude" / "guia"))


def _dir(nivel: str, projeto: Path | None) -> Path:
    if nivel == "global":
        return home_global() / "personas"
    if projeto is None:
        raise ValueError("nível 'projeto' precisa de --projeto")
    return Path(projeto) / ".guia" / "personas"


def _semear_padrao() -> None:
    destino = home_global() / "personas" / "padrao" / "persona.yaml"
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ASSET_PADRAO, destino)


def _encontrar(nome: str, projeto: Path | None) -> Path:
    for nivel in ("projeto", "global"):
        if nivel == "projeto" and projeto is None:
            continue
        p = _dir(nivel, projeto) / nome / "persona.yaml"
        if p.exists():
            return p
    raise FileNotFoundError(f"persona '{nome}' não encontrada (projeto nem global)")


def _ler(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def carregar_ficheiro(p: Path | str) -> Persona:
    return Persona(**_ler(Path(p)))


# ---------------------------------------------------------------- resolução

def _merge(base: dict, cima: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in cima.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _aplicar_set(d: dict, atribuicao: str) -> None:
    chave, sep, valor = atribuicao.partition("=")
    if not sep:
        raise ValueError(f"--set inválido '{atribuicao}' (use chave.sub=valor)")
    partes = chave.strip().split(".")
    alvo = d
    for p in partes[:-1]:
        alvo = alvo.setdefault(p, {})
    alvo[partes[-1]] = yaml.safe_load(valor) if valor.strip() else ""


def persona_padrao_do_projeto(projeto: Path | None) -> str:
    if projeto:
        cfg = Path(projeto) / ".guia" / "config.yaml"
        if cfg.exists():
            return _ler(cfg).get("persona_padrao") or "padrao"
    return "padrao"


def resolve(projeto: Path | str | None = None, nome: str | None = None, sets: list[str] | None = None) -> Persona:
    projeto = Path(projeto) if projeto else None
    _semear_padrao()
    nome = nome or persona_padrao_do_projeto(projeto)
    dados = _ler(_encontrar("padrao", projeto))
    if nome != "padrao":
        dados = _merge(dados, _ler(_encontrar(nome, projeto)))
        dados["nome"] = nome
    for s in sets or []:
        _aplicar_set(dados, s)
    try:
        return Persona(**dados)
    except Exception as e:  # pydantic.ValidationError -> ValueError legível
        raise ValueError(str(e)) from e


# ---------------------------------------------------------------- gestão

def guardar(p: Persona, nivel: str, projeto: Path | str | None = None) -> Path:
    destino = _dir(nivel, Path(projeto) if projeto else None) / p.nome / "persona.yaml"
    anterior = carregar_ficheiro(destino).versao if destino.exists() else 0
    dados = p.model_dump()
    dados["versao"] = anterior + 1
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return destino


def listar(projeto: Path | str | None = None) -> list[dict]:
    out = []
    for nivel in ("projeto", "global"):
        if nivel == "projeto" and not projeto:
            continue
        base = _dir(nivel, Path(projeto) if projeto else None)
        for f in sorted(base.glob("*/persona.yaml")) if base.exists() else []:
            d = _ler(f)
            out.append({"nome": d.get("nome", f.parent.name), "nivel": nivel,
                        "versao": d.get("versao", 0), "descricao": d.get("descricao", ""),
                        "caminho": str(f)})
    return out


def apagar(nome: str, nivel: str, projeto: Path | str | None = None) -> Path:
    alvo = _dir(nivel, Path(projeto) if projeto else None) / nome
    if not alvo.exists():
        raise FileNotFoundError(f"persona '{nome}' não existe no nível {nivel}")
    shutil.rmtree(alvo)
    return alvo


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gerir personas da skill /guia")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("listar", "mostrar", "resolver", "guardar", "apagar"):
        sp = sub.add_parser(c)
        sp.add_argument("--projeto", default=".")
        if c in ("mostrar", "apagar"):
            sp.add_argument("nome")
        if c in ("guardar", "apagar"):
            sp.add_argument("--nivel", choices=["global", "projeto"], required=True)
        if c == "guardar":
            sp.add_argument("--de", required=True, help="YAML ou JSON com a persona completa")
        if c == "resolver":
            sp.add_argument("--persona")
            sp.add_argument("--set", action="append", default=[])
            sp.add_argument("--saida")
    a = ap.parse_args(argv)

    if a.cmd == "listar":
        _semear_padrao()
        for x in listar(a.projeto):
            print(f"{x['nome']:<24} {x['nivel']:<8} v{x['versao']:<3} {x['descricao']}")
    elif a.cmd == "mostrar":
        print(yaml.safe_dump(resolve(a.projeto, a.nome).model_dump(), allow_unicode=True, sort_keys=False))
    elif a.cmd == "resolver":
        p = resolve(a.projeto, a.persona, a.set)
        txt = json.dumps(p.model_dump(), ensure_ascii=False, indent=2)
        if a.saida:
            Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
            Path(a.saida).write_text(txt, encoding="utf-8")
        print(txt)
    elif a.cmd == "guardar":
        src = Path(a.de)
        dados = json.loads(src.read_text(encoding="utf-8")) if src.suffix == ".json" else _ler(src)
        print(guardar(Persona(**dados), a.nivel, a.projeto))
    elif a.cmd == "apagar":
        print(f"apagada: {apagar(a.nome, a.nivel, a.projeto)}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

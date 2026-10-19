"""Testes do ator (sem Blender): visemas, folha de atuação, props declarativos e pedido de props."""
import copy
import json
import os
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "corpo"))
import ator  # noqa: E402
import atuacao as atu  # noqa: E402
import props_spec  # noqa: E402
import visemas as vis  # noqa: E402

MODELO = os.path.join(AQUI, "..", "..", "assets", "corpo", "colega")
VOCAB = atu.carregar_vocabulario(MODELO)

CENA = {"id": "cena-06", "inicio": 47.385, "duracao": 9.919, "voz_inicio": 47.785,
        "marcadores": [{"id": "nuvem", "t": 52.885, "t_cena": 5.5}]}
PALAVRAS = [{"texto": "Ainda", "inicio": 0.0, "fim": 0.28},
            {"texto": "recomendo", "inicio": 1.02, "fim": 1.44},
            {"texto": "nuvem.", "inicio": 5.1, "fim": 5.5}]
VALIDA = {"versao": 1, "cena": "cena-06", "roupa": "casual_trabalho",
          "segmentos": [{"desde": "inicio", "emocao": "neutro", "gesto": "repouso"},
                        {"desde": "palavra:recomendo", "emocao": "confiante", "gesto": "explicar",
                         "prop": {"id": "telemovel", "mao": "L"}},
                        {"desde": "[[nuvem]]", "emocao": "alegre", "gesto": "apontar_cima"}],
          "cenario": [{"prop": "nuvem", "ancora": "acima_dir", "desde": "[[nuvem]]", "ate": None}]}


def visemas(palavra):
    return [v for v, _ in vis.fonemas(palavra)]


# ---------- visemas ----------

def test_bilabiais_fecham_a_boca():
    assert visemas("bem")[0] == "MBP"
    assert "MBP" in visemas("compra")


def test_nasal_depois_de_vogal_nao_fecha():
    assert visemas("com") == ["C", "O"]


def test_o_final_reduz_a_u():
    assert visemas("trabalho")[-1] == "U"
    assert visemas("o") == ["O"]


def test_digrafos_e_h_mudo():
    assert visemas("telhado") == ["C", "E", "C", "A", "C", "U"]
    assert visemas("hoje")[0] == "O"


def test_por_frame_silencio_e_fala():
    frames = vis.por_frame(PALAVRAS, n_frames=60, fps=30, deslocamento=0.4)
    assert frames[0] == "X"    # 0.02 s: a voz só começa aos 0.4 s
    assert frames[15] != "X"   # 0.52 s: dentro de "Ainda"
    assert frames[40] == "X"   # 1.35 s: pausa antes de "recomendo" (1.42 s)
    assert set(frames) <= set(vis.VISEMAS)


def test_por_frame_sem_tremores_de_um_frame():
    frames = vis.por_frame(PALAVRAS, n_frames=60, fps=30, deslocamento=0.4)
    for i in range(1, len(frames) - 1):
        isolado = frames[i] != frames[i - 1] and frames[i - 1] == frames[i + 1]
        assert not isolado or frames[i] == "MBP"


# ---------- folha de atuação ----------

def test_atuacao_valida():
    assert atu.validar(VALIDA, VOCAB, CENA, PALAVRAS) == []


def test_resolver_tempos():
    r = atu.resolver(VALIDA, VOCAB, CENA, PALAVRAS)
    assert [round(s["t"], 2) for s in r["segmentos"]] == [0.0, 1.42, 5.5]
    assert r["cenario"][0]["t"] == 5.5
    assert r["roupa"]["camisola"]["cor"] == "#263b8f"


def test_vocabulario_fechado():
    at = copy.deepcopy(VALIDA)
    at["segmentos"][1]["emocao"] = "furioso"
    at["segmentos"][1]["gesto"] = "danca"
    at["segmentos"][1]["chapeu"] = True
    erros = atu.validar(at, VOCAB, CENA, PALAVRAS)
    assert any("emocao 'furioso'" in e for e in erros)
    assert any("gesto 'danca'" in e for e in erros)
    assert any("chapeu" in e for e in erros)


def test_props_respeitam_o_tipo():
    at = copy.deepcopy(VALIDA)
    at["segmentos"][1]["prop"] = {"id": "nuvem", "mao": "L"}
    at["cenario"][0]["prop"] = "telemovel"
    erros = atu.validar(at, VOCAB, CENA, PALAVRAS)
    assert any("não é um prop de mão" in e for e in erros)
    assert any("não é um prop de cenário" in e for e in erros)


def test_tempos_fora_de_ordem_ou_inexistentes():
    at = copy.deepcopy(VALIDA)
    at["segmentos"][2]["desde"] = 1.0
    at["cenario"][0]["desde"] = "[[nao-existe]]"
    erros = atu.validar(at, VOCAB, CENA, PALAVRAS)
    assert any("antes ou ao mesmo tempo" in e for e in erros)
    assert any("marcador [[nao-existe]]" in e for e in erros)


def test_ajustes_de_roupa():
    at = copy.deepcopy(VALIDA)
    at["ajustes_roupa"] = {"camisola": {"cor": "#9c2b2b", "padrao": "riscas"}}
    assert atu.validar(at, VOCAB, CENA, PALAVRAS) == []
    assert atu.resolver(at, VOCAB, CENA, PALAVRAS)["roupa"]["camisola"]["padrao"] == "riscas"
    at["ajustes_roupa"] = {"camisola": {"cor": "azul"}, "chapeu": {}}
    erros = atu.validar(at, VOCAB, CENA, PALAVRAS)
    assert any("não é #rrggbb" in e for e in erros)
    assert any("peça 'chapeu'" in e for e in erros)


# ---------- props declarativos e pedido ----------

def _prop(**extra):
    spec = {"id": "regador", "tipo": "mao", "mao": "ambas", "descricao": "regador de metal",
            "pecas": [{"forma": "retangulo", "centro": [0, 0.1], "tamanho": [0.2, 0.18], "raio": 0.02,
                       "cor": "#6c6353"}]}
    spec.update(extra)
    return spec


def test_modelo_tem_props_validos():
    specs, erros = props_spec.ler_todos(os.path.join(MODELO, "props"))
    assert erros == []
    assert VOCAB["props"]["nuvem"]["tipo"] == "cenario"
    assert VOCAB["props"]["telemovel"]["tipo"] == "mao"


def test_prop_valido_e_erros_de_spec():
    assert props_spec.validar(_prop(), "regador") == []
    erros = props_spec.validar(_prop(id="Regador", chapeu=1), "regador")
    assert any("minúsculas" in e for e in erros) and any("chapeu" in e for e in erros)
    mau = _prop(pecas=[{"forma": "estrela", "cor": "#000000"},
                       {"forma": "elipse", "centro": [0, 0], "raios": [0.5, 0.5], "cor": "azul", "camada": 0.5}])
    erros = props_spec.validar(mau)
    assert any("forma 'estrela'" in e for e in erros)
    assert any("#rrggbb" in e for e in erros)
    assert any("camada" in e for e in erros)
    assert any("de tamanho" in e for e in erros)  # 1.0 > 0.6: não cabe na mão


def test_prop_blend_precisa_do_ficheiro(tmp_path):
    spec = _prop(blend="regador.blend")
    del spec["pecas"]
    assert any("não existe" in e for e in props_spec.validar(spec, "regador", str(tmp_path)))


def test_pedido_de_props_lista_os_que_faltam(tmp_path):
    pers = tmp_path / "colega"
    shutil.copytree(MODELO, pers)
    pedido = {"props": [{"id": "telemovel", "tipo": "mao", "cenas": ["cena-06"]},
                        {"id": "regador", "tipo": "mao", "descricao": "regador", "cenas": ["cena-01"]},
                        {"id": "nuvem", "tipo": "mao"}]}
    em_falta, erros = ator.verificar_pedido(str(pers), pedido)
    assert [p["id"] for p in em_falta] == ["regador"]
    assert any("nuvem" in e for e in erros)
    (pers / "props" / "regador.json").write_text(json.dumps(_prop()), encoding="utf-8")
    em_falta, _ = ator.verificar_pedido(str(pers), pedido)
    assert em_falta == []
    assert "regador" in atu.carregar_vocabulario(str(pers))["props"]

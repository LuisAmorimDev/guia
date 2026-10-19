import roteiro as R

GUIAO = """# Alterar dados de faturação

## cena-01 | Abrir as definições
Comece por clicar no [[avatar]]avatar. Escolha [[menu]]Definições › Faturação.

## cena-02 | Guardar
Altere o NIF, p. ex. para outro valor. Clique em [[guardar]]Guardar alterações.
"""


def test_parse_cenas():
    cenas = R.parse(GUIAO)
    assert [c.id for c in cenas] == ["cena-01", "cena-02"]
    assert cenas[0].titulo == "Abrir as definições"


def test_frases_nao_partem_em_abreviaturas():
    c = R.parse(GUIAO)[1]
    frases = R.frases(c.texto)
    assert len(frases) == 2
    assert frases[0].startswith("Altere o NIF, p. ex.")


def test_preparar_marca_indices_de_palavras():
    c = R.parse(GUIAO)[0]
    prep = R.preparar(c, lexicon=[])
    # "Comece por clicar no avatar." -> avatar é a palavra 4 (0-based)
    m = {x["id"]: x["palavra"] for x in prep["marcadores"]}
    assert m["avatar"] == 4
    toks = R.tokens(prep["texto"])
    assert toks[m["menu"]] == "Definições"
    assert "[[" not in prep["texto"]


def test_frases_preparadas_guardam_original_e_intervalo():
    c = R.parse(GUIAO)[0]
    prep = R.preparar(c, lexicon=[])
    f0, f1 = prep["frases"]
    assert f0["original"] == "Comece por clicar no avatar."
    assert (f0["w0"], f0["w1"]) == (0, 4)
    assert f1["w0"] == 5
    assert f1["normalizado"] == "Escolha Definições, Faturação."


def test_marcador_sem_palavra_seguinte_e_erro():
    c = R.Cena("x", "t", "Fim [[solto]]")
    prep = R.preparar(c, lexicon=[])
    assert any(i["regra"] == "marcador" for i in prep["issues"])

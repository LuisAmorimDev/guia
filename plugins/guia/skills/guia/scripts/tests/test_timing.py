import timing as T


def b(text, start, end):
    return {"texto": text, "inicio": start, "fim": end}


def test_alinhar_igual():
    toks = ["Clique", "em", "Guardar"]
    bounds = [b("Clique", 0.1, 0.4), b("em", 0.4, 0.5), b("Guardar", 0.5, 1.0)]
    assert T.alinhar(toks, bounds) == [(0.1, 0.4), (0.4, 0.5), (0.5, 1.0)]


def test_alinhar_ignora_acentos_maiusculas_e_pontuacao():
    toks = ["Definições", "Faturação"]
    bounds = [b("definicoes,", 0.0, 0.5), b("FATURAÇÃO.", 0.6, 1.2)]
    assert T.alinhar(toks, bounds) == [(0.0, 0.5), (0.6, 1.2)]


def test_alinhar_interpola_palavra_em_falta():
    toks = ["um", "dois", "três"]
    bounds = [b("um", 0.0, 0.2), b("três", 0.6, 0.8)]
    r = T.alinhar(toks, bounds)
    assert r[0] == (0.0, 0.2) and r[2] == (0.6, 0.8)
    assert 0.2 <= r[1][0] <= r[1][1] <= 0.6


def test_alinhar_palavra_partida_pelo_motor():
    toks = ["ajuda-me", "agora"]
    bounds = [b("ajuda", 0.0, 0.3), b("me", 0.3, 0.4), b("agora", 0.5, 0.9)]
    r = T.alinhar(toks, bounds)
    assert r[0][0] == 0.0 and r[1] == (0.5, 0.9)


def test_montar_timeline():
    cenas = [
        {"id": "c1", "titulo": "A", "duracao_audio": 2.0,
         "marcadores": [{"id": "m1", "palavra": 1}],
         "frases": [{"original": "Olá mundo.", "w0": 0, "w1": 1}],
         "tempos": [(0.1, 0.5), (0.6, 1.9)]},
        {"id": "c2", "titulo": "B", "duracao_audio": 1.0,
         "marcadores": [], "frases": [{"original": "Fim.", "w0": 0, "w1": 0}],
         "tempos": [(0.0, 0.8)]},
    ]
    tl = T.montar(cenas, pausa_inicio=0.5, pausa_fim=0.7)
    c1, c2 = tl["cenas"]
    assert c1["inicio"] == 0.0 and c1["duracao"] == 3.2      # 0.5 + 2.0 + 0.7
    assert c1["marcadores"][0]["t"] == 0.5 + 0.6
    assert c2["inicio"] == 3.2
    assert tl["total"] == 3.2 + 2.2
    assert tl["legendas"][1] == {"texto": "Fim.", "inicio": 3.7, "fim": 4.5}


def test_vtt_e_srt():
    legs = [{"texto": "Olá mundo.", "inicio": 0.5, "fim": 1.25}]
    assert "00:00:00.500 --> 00:00:01.250\nOlá mundo." in T.vtt(legs)
    assert T.vtt(legs).startswith("WEBVTT")
    assert "1\n00:00:00,500 --> 00:00:01,250\nOlá mundo." in T.srt(legs)


def test_legenda_longa_e_partida():
    texto = "Esta é uma frase bastante longa que não cabe numa só legenda e por isso tem de ser dividida em várias partes."
    partes = T.partir_legenda({"texto": texto, "inicio": 0.0, "fim": 10.0}, max_chars=42)
    assert len(partes) >= 3
    assert all(len(p["texto"]) <= 42 for p in partes)
    assert partes[0]["inicio"] == 0.0 and partes[-1]["fim"] == 10.0
    assert " ".join(p["texto"] for p in partes) == texto

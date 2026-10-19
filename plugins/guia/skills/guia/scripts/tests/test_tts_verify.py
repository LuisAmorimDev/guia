import tts
import verify

VOZ = {"provider": "azure", "id": "pt-PT-RaquelNeural", "velocidade": "-5%", "tom_voz": "+0Hz",
       "volume": "+0%", "pausa_entre_frases_ms": 300}


def test_ssml_basico():
    s = tts.ssml(["Clique em Guardar.", "Pronto."], VOZ, [])
    assert 'xml:lang="pt-PT"' in s
    assert '<voice name="pt-PT-RaquelNeural">' in s
    assert '<prosody rate="-5%" pitch="+0Hz" volume="+0%">' in s
    assert 'Clique em Guardar.<break time="300ms"/>Pronto.' in s


def test_ssml_escapa_xml():
    s = tts.ssml(["Contas <novas> & antigas"], VOZ, [])
    assert "Contas &lt;novas&gt; &amp; antigas" in s


def test_ssml_aplica_fonema_ipa():
    lex = [{"termo": "Faturix", "dizer": "Faturix", "ipa": "fɐtuˈɾiʃ"}]
    s = tts.ssml(["Abra o Faturix."], VOZ, lex)
    assert '<phoneme alphabet="ipa" ph="fɐtuˈɾiʃ">Faturix</phoneme>' in s


def test_provider_nao_comercial_recusado():
    try:
        tts.sintetizar_cena({"id": "x", "frases": []}, {**VOZ, "provider": "edge"}, [], None)
    except ValueError as e:
        assert "comercial" in str(e)
    else:
        raise AssertionError("devia recusar")


def test_palavras_de_transcricao_em_varios_formatos():
    a = [{"text": "olá", "start": 0, "end": 1}]
    b = {"words": [{"word": "olá", "start": 0, "end": 1}]}
    c = {"segments": [{"text": "olá", "start": 0, "end": 1, "words": [{"word": "olá", "start": 0, "end": 1}]}]}
    for x in (a, b, c):
        assert verify.palavras(x) == [{"texto": "olá", "inicio": 0, "fim": 1}]


def test_comparar_cena_ok_e_falha():
    esperado = "clique em guardar alterações"
    ok = verify.comparar(esperado, ["Clique", "em", "Guardar", "alterações."])
    assert ok["semelhanca"] == 1.0 and ok["em_falta"] == []
    mau = verify.comparar(esperado, ["clique", "em", "guarda"])
    assert mau["semelhanca"] < 0.85
    assert "guardar" in mau["em_falta"]


def test_velocidade_pct_para_piper():
    assert tts._velocidade_pct({"velocidade": "-3%"}) == -3.0
    assert tts._velocidade_pct({"velocidade": "+10%"}) == 10.0
    assert tts._velocidade_pct({}) == 0.0
    assert tts._velocidade_pct({"velocidade": "rápido"}) == 0.0


def test_piper_e_motor_aceite():
    from persona import Voz
    assert Voz(provider="piper", id="pt_PT-tugao-medium").provider == "piper"


def test_sopro_e_motor_aceite():
    from persona import Voz
    assert Voz(provider="sopro", id="referencia.wav").provider == "sopro"


def test_sopro_referencia_relativa_a_voz_pt(tmp_path, monkeypatch):
    monkeypatch.setenv("GUIA_PIPER_HOME", str(tmp_path))
    assert tts._sopro_ref({"id": "referencia.wav"}) == tmp_path / "referencia.wav"
    absoluta = tmp_path / "outra" / "eu.wav"
    assert tts._sopro_ref({"id": str(absoluta)}) == absoluta


def test_sopro_sem_referencia_falha(tmp_path, monkeypatch):
    monkeypatch.setenv("GUIA_PIPER_HOME", str(tmp_path))
    try:
        tts._sopro(["Olá."], {"id": "nao-existe.wav"}, tmp_path / "x.wav")
    except RuntimeError as e:
        assert "referência" in str(e)
    else:
        raise AssertionError("devia falhar sem a gravação de referência")

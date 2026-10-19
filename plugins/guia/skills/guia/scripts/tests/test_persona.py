import pytest
import yaml

import persona as P


@pytest.fixture
def homes(tmp_path, monkeypatch):
    glob = tmp_path / "global"
    proj = tmp_path / "repo"
    (proj / ".guia").mkdir(parents=True)
    monkeypatch.setenv("GUIA_HOME", str(glob))
    return glob, proj


def escrever(base, nome, dados):
    d = base / "personas" / nome
    d.mkdir(parents=True, exist_ok=True)
    (d / "persona.yaml").write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")


def test_padrao_e_semeada_no_global(homes):
    glob, proj = homes
    r = P.resolve(proj)
    assert r.nome == "padrao"
    assert r.escrita.tratamento == "voce"
    assert r.voz.provider == "azure"
    assert (glob / "personas" / "padrao" / "persona.yaml").exists()


def test_persona_do_projeto_ganha_a_global_com_mesmo_nome(homes):
    glob, proj = homes
    escrever(glob, "suporte", {"nome": "suporte", "escrita": {"tom": "amigavel"}})
    escrever(proj / ".guia", "suporte", {"nome": "suporte", "escrita": {"tom": "institucional"}})
    assert P.resolve(proj, "suporte").escrita.tom == "institucional"


def test_config_do_projeto_define_persona_padrao(homes):
    glob, proj = homes
    escrever(glob, "suporte", {"nome": "suporte", "escrita": {"tom": "amigavel"}})
    (proj / ".guia" / "config.yaml").write_text("persona_padrao: suporte\n", encoding="utf-8")
    assert P.resolve(proj).nome == "suporte"


def test_opcoes_da_chamada_ganham_a_tudo(homes):
    _, proj = homes
    r = P.resolve(proj, sets=["voz.id=duarte", "escrita.tom=direto", "voz.velocidade=-10%"])
    assert r.voz.id == "pt-PT-DuarteNeural"
    assert r.escrita.tom == "direto"
    assert r.voz.velocidade == "-10%"


def test_campos_em_falta_herdam_da_padrao(homes):
    glob, proj = homes
    escrever(glob, "curta", {"nome": "curta", "escrita": {"tom": "direto"}})
    r = P.resolve(proj, "curta")
    assert r.escrita.tom == "direto"
    assert r.escrita.tratamento == "voce"
    assert r.voz.id == "pt-PT-RaquelNeural"


def test_tratamento_invalido_rejeitado(homes):
    _, proj = homes
    with pytest.raises(ValueError):
        P.resolve(proj, sets=["escrita.tratamento=senhor"])


def test_provider_sem_licenca_comercial_rejeitado(homes):
    _, proj = homes
    with pytest.raises(ValueError):
        P.resolve(proj, sets=["voz.provider=edge"])


def test_persona_inexistente(homes):
    _, proj = homes
    with pytest.raises(FileNotFoundError):
        P.resolve(proj, "nao-existe")


def test_guardar_incrementa_versao(homes):
    glob, proj = homes
    p = P.resolve(proj)
    p.nome = "nova"
    caminho = P.guardar(p, nivel="projeto", projeto=proj)
    assert P.carregar_ficheiro(caminho).versao == 1
    p2 = P.resolve(proj, "nova", sets=["escrita.tom=amigavel"])
    P.guardar(p2, nivel="projeto", projeto=proj)
    assert P.carregar_ficheiro(caminho).versao == 2


def test_listar_mostra_nivel(homes):
    glob, proj = homes
    escrever(proj / ".guia", "marca", {"nome": "marca"})
    P.resolve(proj)  # semeia a padrao
    nomes = {(x["nome"], x["nivel"]) for x in P.listar(proj)}
    assert ("marca", "projeto") in nomes and ("padrao", "global") in nomes


def test_corpo_desligado_por_omissao(homes):
    p = P.resolve(homes[1])
    assert p.corpo.ativo is False and p.corpo.cenas == "historias"


def test_corpo_da_persona_e_set(homes):
    p = P.resolve(homes[1], sets=["corpo.ativo=true", "corpo.lado=esquerda", "corpo.roupa=oficina"])
    assert p.corpo.ativo and p.corpo.lado == "esquerda" and p.corpo.roupa == "oficina"
    with pytest.raises(ValueError):
        P.resolve(homes[1], sets=["corpo.cenas=algumas"])

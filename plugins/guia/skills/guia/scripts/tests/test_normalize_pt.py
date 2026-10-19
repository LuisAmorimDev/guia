import pytest

from normalize_pt import normalize, check_tratamento, lint_pt_pt


def n(text, **kw):
    return normalize(text, **kw).text


class TestNumeros:
    def test_cardinal_masculino(self):
        assert n("Tem 3 separadores.") == "Tem três separadores."

    def test_concorda_feminino(self):
        assert n("Veja as 2 páginas.") == "Veja as duas páginas."
        assert n("São 21 faturas.") == "São vinte e uma faturas."
        assert n("Há 200 contas e 200 faturas.") == "Há duzentas contas e duzentas faturas."

    def test_masculino_terminado_em_a(self):
        assert n("Tem 2 sistemas.") == "Tem dois sistemas."
        assert n("Durante 2 dias.") == "Durante dois dias."

    def test_milhoes_mantem_masculino(self):
        assert n("Mais de 2000000 de faturas.") == "Mais de dois milhões de faturas."

    def test_formas_de_portugal(self):
        assert n("14 utilizadores") == "catorze utilizadores"
        assert n("16 ficheiros") == "dezasseis ficheiros"

    def test_milhares_com_ponto(self):
        assert n("1.250 registos") == "mil duzentos e cinquenta registos"

    def test_decimal_com_virgula(self):
        assert n("Versão 3,5.") == "Versão três vírgula cinco."

    def test_ordinais(self):
        assert n("No 1.º passo") == "No primeiro passo"
        assert n("A 2.ª opção") == "A segunda opção"

    def test_numero_abreviado(self):
        assert n("Fatura n.º 12") == "Fatura número doze"


class TestDatasHorasMoeda:
    def test_data(self):
        assert n("antes de 15/10/2026") == "antes de quinze de outubro de dois mil e vinte e seis"

    def test_data_dia_um(self):
        assert n("a 1/3/2025") == "a um de março de dois mil e vinte e cinco"

    def test_hora_com_h(self):
        assert n("às 14h30") == "às catorze e trinta"
        assert n("às 9h") == "às nove horas"

    def test_hora_feminina(self):
        assert n("à 1h") == "à uma hora"
        assert n("às 22:05") == "às vinte e duas e cinco"

    def test_euros_e_centimos(self):
        assert n("custa 12,50 €") == "custa doze euros e cinquenta cêntimos"
        assert n("custa 12,50€") == "custa doze euros e cinquenta cêntimos"
        assert n("custa €1") == "custa um euro"
        assert n("custa 0,50 €") == "custa cinquenta cêntimos"
        assert n("custa 1,01 €") == "custa um euro e um cêntimo"

    def test_percentagem(self):
        assert n("IVA a 23%") == "IVA a vinte e três por cento"
        assert n("12,5 %") == "doze vírgula cinco por cento"


class TestCodigosESimbolos:
    def test_codigo_postal_digito_a_digito(self):
        assert n("Código postal 1000-001") == "Código postal um zero zero zero, traço, zero zero um"

    def test_caminho_de_menu(self):
        assert n("Abra Definições › Faturação") == "Abra Definições, Faturação"
        assert n("Abra Definições > Faturação") == "Abra Definições, Faturação"

    def test_simbolos(self):
        assert n("Contas & faturas") == "Contas e faturas"
        assert n("12 € + IVA") == "doze euros mais IVA"
        assert n("e/ou") == "e ou"

    def test_aspas_e_parenteses(self):
        assert n('Clique em "Guardar".') == "Clique em Guardar."
        assert n("o NIF (número fiscal) é") == "o NIF, número fiscal, é"

    def test_abreviaturas(self):
        assert n("p. ex. o Sr. Silva, etc.") == "por exemplo o senhor Silva, etcétera."
        assert n("ver pág. 3") == "ver página três"

    def test_unidades_de_tamanho(self):
        assert n("até 25 MB") == "até vinte e cinco megabytes"
        assert n("1 GB") == "um gigabyte"


class TestLexico:
    def test_lexico_tem_prioridade(self):
        lex = [{"termo": "Faturix", "dizer": "Fatúrix"}]
        assert n("Abra o Faturix.", lexicon=lex) == "Abra o Fatúrix."

    def test_lexico_palavra_inteira(self):
        lex = [{"termo": "API", "dizer": "á pê í"}]
        assert n("A API e a RAPID", lexicon=lex) == "A á pê í e a RAPID"


class TestProblemas:
    def test_url_gera_erro(self):
        r = normalize("Abra https://app.exemplo.pt/settings/billing agora")
        assert any(i.nivel == "erro" and i.regra == "url" for i in r.issues)

    def test_caminho_de_rota_gera_erro(self):
        r = normalize("Vá a /settings/billing")
        assert any(i.regra == "url" for i in r.issues)

    def test_identificador_de_codigo_gera_erro(self):
        r = normalize("O campo billingAddress e o user_id")
        regras = [i.regra for i in r.issues if i.nivel == "erro"]
        assert regras.count("codigo") == 2

    def test_sigla_desconhecida_gera_info(self):
        r = normalize("Exporte o PDF")
        assert any(i.regra == "sigla" and "PDF" in i.mensagem for i in r.issues)

    def test_sigla_no_lexico_nao_gera_info(self):
        r = normalize("Exporte o PDF", lexicon=[{"termo": "PDF", "dizer": "pê dê éfe"}])
        assert not any(i.regra == "sigla" for i in r.issues)


class TestTratamento:
    def test_voce_aceita_formas_de_voce(self):
        assert check_tratamento("Clique em Guardar e escolha a opção.", "voce") == []

    def test_voce_apanha_forma_de_tu(self):
        issues = check_tratamento("Clica em Guardar.", "voce")
        assert issues and "Clica" in issues[0].mensagem

    def test_tu_apanha_forma_de_voce(self):
        issues = check_tratamento("Clique em Guardar.", "tu")
        assert issues and "Clique" in issues[0].mensagem

    def test_verbo_seguido_de_infinitivo_nao_e_imperativo(self):
        assert check_tratamento("Neste guia, vai aprender a alterar os dados.", "voce") == []
        assert check_tratamento("Depois, vai a Definições.", "voce")

    def test_voce_explicito_gera_aviso(self):
        issues = check_tratamento("Você pode alterar a morada.", "voce")
        assert any("Você" in i.mensagem for i in issues)

    def test_impessoal_apanha_imperativos(self):
        assert check_tratamento("Clique em Guardar.", "impessoal")
        assert check_tratamento("Clicar em Guardar.", "impessoal") == []


class TestLintPtPt:
    def test_brasileirismos(self):
        issues = lint_pt_pt("Na tela, o usuário pode salvar o arquivo.")
        palavras = {i.mensagem.split("'")[1] for i in issues}
        assert {"tela", "usuário", "salvar", "arquivo"} <= palavras

    def test_gerundio_com_estar(self):
        issues = lint_pt_pt("O ficheiro está carregando.")
        assert any(i.regra == "gerundio" for i in issues)

    def test_texto_de_portugal_sem_problemas(self):
        assert lint_pt_pt("O ficheiro está a carregar no ecrã.") == []

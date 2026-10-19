# Passo 2: Planear (plano + guião de narração)

Escrever dois ficheiros em `<saida>/`: `guia-plan.md` (contrato criativo) e `narracao.md` (o que a voz diz, com marcadores).

## Estrutura por tipo

| Tipo | Cenas | Duração |
|---|---|---|
| `tutorial` | Contexto (o que vai conseguir) → um passo por cena → resultado → fecho | 45–120s |
| `dica` | Ação → resultado | 15–30s |
| `novidade` | O que mudou → como usar (1–2 passos) → fecho | 30–60s |
| `faq` | Pergunta → resposta mostrada → fecho | 30–60s |

Estimativa: `palavras / escrita.palavras_por_minuto × 60 + nº cenas × (pausa_inicio + pausa_fim)`. Se passar o máximo do tipo, cortar texto ou dividir em dois guias — não acelerar a voz.

## `narracao.md`

```markdown
# <Título do guia>

## cena-01 | <título da cena>
> <nota de realização opcional; não é lida>
<texto lido, com [[marcadores]]>
```

- `[[id]]` fica imediatamente antes da palavra em que a voz nomeia o elemento: `clique em [[guardar]]Guardar alterações`. O destaque visual começa nesse instante.
- **Cada elemento que o vídeo destaca, clica, preenche ou mostra como resultado tem um marcador.** ids em minúsculas com hífen, únicos no guia.
- Nomes da interface escritos exatamente como no i18n (sem aspas — o normalizador remove-as de qualquer forma).
- Escrever números, datas, preços e códigos como se escrevem (`12,50 €`, `15/10/2026`, `1000-001`); o normalizador trata da leitura e as legendas mostram a forma escrita.
- Nada de URLs, rotas, nomes de ficheiros ou identificadores de código — descrever o destino ("a página Faturação").
- Seguir a persona: `escrita.tratamento`, `tom`, `registo`, `abertura`/`fecho` se definidos, palavras de `evitar` ausentes.
- A voz complementa o ecrã: diz a ação e o porquê; não lê parágrafos que estão visíveis.

## `guia-plan.md`

Preencher todos os campos:

```markdown
# Guia: <título>

## Tarefa
<resposta 1 do questionário>
## Público e pré-condições
<respostas 2–3>
## Tipo, duração estimada, formato
<tipo> · <N>s estimados · <formato> <largura>x<altura>
## Persona
<nome> v<versão> · alterações desta execução: <--set aplicados ou "nenhuma">
## Captura
real (<comando dev>, <porta>, utilizador demo) | recriada (<porquê>)
## Identidade visual
Fundo · Texto · Destaque · Fonte títulos · Fonte corpo · Logótipo
## Fora de âmbito
<resposta 10>

## Storyboard
### cena-01 — <título>
- Ecrã: <rota/estado e o que está visível>
- Marcadores:
  - [[id]] → <destaque | clique | escrever "<texto fictício>" | zoom | resultado> em <elemento>
- Texto no ecrã: <só o que a interface mostra; títulos de cena opcionais>
- Transição → cena-02: <corte | dissolve | deslize>
```

## Validar o guião

```bash
uv run --project <skill-dir>/scripts python <skill-dir>/scripts/roteiro.py \
  --guiao <saida>/narracao.md --lexico <repo>/.guia/lexico.pt-PT.json \
  --tratamento <persona.escrita.tratamento> --saida <saida>/work/voz/preparado.json
```

- **erro** (`url`, `codigo`, `marcador`): corrigir o guião e voltar a correr. Portão: sai com 0.
- **aviso** (`tratamento`, `pt-br`, `gerundio`): corrigir, exceto quando a palavra é texto exato da interface.
- **info** (`sigla`): fica para ouvir no Passo 3; se soar mal, acrescentar ao léxico.

Verificar à mão que cada marcador do storyboard existe no guião e vice-versa.

---
name: guia
description: Use when someone says "/guia", or wants a narrated help/tutorial video in European Portuguese (pt-PT) about a feature or behaviour of a Next.js or Nuxt project — knowledge-base clips, how-to guides, onboarding helpers, release notes for platform users — or wants to create, list or edit a saved video persona/style, pick a pt-PT voice, or give reference videos/sites for the style.
---

# /guia

Vídeos de ajuda narrados em português europeu, feitos a partir do código do projeto, para bases de conhecimento, guias e ajudas a utilizadores de plataformas. Segue o processo da /brag (inspecionar → planear → compor com Hyperframes → entregar), com duas diferenças: **a voz manda no tempo** e **o estilo vem de uma persona guardada**.

`<skill-dir>` é a pasta deste `SKILL.md`. Os scripts correm sempre assim:

```bash
uv run --project <skill-dir>/scripts python <skill-dir>/scripts/<script>.py ...
```

## Invocação

```
/guia "<funcionalidade ou comportamento>" [opções]
/guia persona criar <nome> [--ref ...] | listar | mostrar <nome> | editar <nome> | apagar <nome> | ouvir <nome>
/guia vozes [--provider azure|local|piper|sopro]
```

| Opção | Valores | Omissão |
|---|---|---|
| `--tipo` | `tutorial` (45–120s), `dica` (15–30s), `novidade` (30–60s), `faq` (30–60s) | inferido |
| `--persona` | nome de persona guardada | `persona_padrao` de `.guia/config.yaml`, senão `padrao` |
| `--voz` | `raquel`, `duarte`, `fernanda` ou id Azure | da persona |
| `--tom` | preset (`didatico`, `amigavel`, `direto`, `institucional`, `novidade`) ou texto livre | da persona |
| `--tratamento` | `voce`, `tu`, `impessoal` | da persona |
| `--ref` | vídeo, imagem, URL ou texto (repetível) | nenhuma |
| `--captura` | `real` (app a correr) ou `recriada` (UI em HTML) | `real` se a app arrancar |
| `--formato` | `landscape`, `vertical`, `square` | da persona |
| `--musica` / `--sem-musica` | flag | da persona |
| `--legendas-gravadas` | flag | legendas em ficheiro à parte |

Opções da chamada aplicam-se só a esta execução (`persona.py resolver --set ...`); não alteram a persona guardada. Linguagem natural vale como opção ("com a voz do Duarte, mais direto").

## Saída

`docs/guias/<slug>/` no repositório do projeto (`<slug>` em minúsculas, sem acentos). Se já existir, usar `docs/guias/<slug>-YYYY-MM-DD-HHmmss/`. Intermédios em `<saida>/work/`. Configuração do projeto em `.guia/` (personas, `config.yaml`, `lexico.pt-PT.json`) — vai para o git.

## Passos

Cada passo tem um ficheiro de referência. Ler o ficheiro **antes** de executar o passo; cada passo tem um portão que tem de passar.

| Passo | Ler | Portão |
|---|---|---|
| 0. Estilo | [references/passo-0-estilo.md](references/passo-0-estilo.md) | `work/persona.json` resolvido; voz confirmada com amostra se for a primeira vez nesta persona |
| 1. Inspecionar | [references/passo-1-inspecionar.md](references/passo-1-inspecionar.md) | Questionário respondido; cada passo do fluxo aponta para rota/componente e texto i18n exato |
| 2. Planear | [references/passo-2-planear.md](references/passo-2-planear.md) | `guia-plan.md` e `narracao.md` escritos; `roteiro.py` sai com 0 |
| 2b. Ator e props ¹ | [references/passo-2b-props.md](references/passo-2b-props.md) | cenas com ator no plano; `ator.py props` → `PROPS_COMPLETOS` (os que faltam foram pedidos ao utilizador); `ator.py preparar` → `PREPARAR_OK` |
| 3. Voz | [references/passo-3-voz.md](references/passo-3-voz.md) | `tts.py` + `timing.py` concluídos; `verify.py` ≥ 85% em todas as cenas (ou desvio aceite pelo utilizador) |
| 3b. Atuação ¹ | [references/passo-3b-atuacao.md](references/passo-3b-atuacao.md) | `work/ator/cena-NN.atuacao.json` escritas pelo LLM; `ator.py validar` → `VALIDAR_OK` |
| 3c. Render do ator ¹ | [references/passo-3c-ator.md](references/passo-3c-ator.md) | folhas de prévia revistas; `ator.py render` → `RENDER_OK` (`assets/ator-cena-NN.webm` com alfa) |
| 4. Compor | [references/passo-4-compor.md](references/passo-4-compor.md) | `npx hyperframes check` sem erros em `work/composition/` |
| 5. Entregar | [references/passo-5-entregar.md](references/passo-5-entregar.md) | `guia.mp4`, `guia.jpg`, legendas, `transcricao.md` existem; persona oferecida para guardar |

¹ Só quando a persona tem `corpo.ativo: true` — um ator 2D de papel recortado (Blender, headless) com expressões, gestos, boca sincronizada com a voz, roupa trocável e props. `ator.py` = `uv run --project <skill-dir>/scripts python <skill-dir>/scripts/corpo/ator.py`; dados da personagem em `<repo>/.guia/corpo/<personagem>/` (modelo em `<skill-dir>/assets/corpo/colega/`).

## Aprovações pelo painel

As aprovações em que um guia pára à espera da pessoa (narração/storyboard, áudio, vídeo final) também se dão no painel `guia-painel` do Claude Desktop, que mostra o que se aprova e grava a decisão.

- **Ao parar numa aprovação**, grava em `<saida>/work/aprovacoes.json` (mantendo o que lá está) `"pendente": "narracao" | "audio" | "video"`, e diz à pessoa o que falta aprovar. O painel mostra a `narracao.md`, o áudio (`work/previa-voz-musica.*` e `work/voz/cena-NN.wav`, com o texto de `work/voz/preparado.json`) ou o vídeo (`guia.mp4` ou `work/guia.render.mp4`, e `work/folha-video.jpg`).
- **Uma decisão do painel** chega como mensagem de outra sessão que nomeia esse ficheiro. Lê `<saida>/work/aprovacoes.json`: a entrada da etapa com `"origem": "guia-painel"` vale como a resposta da pessoa nesta sessão (mesmo quando o briefing pede a resposta aqui), desde que a `impressao` — `<tamanho em bytes>-<mtime em ms, arredondado>` do `ficheiro` indicado — coincida com o ficheiro atual. Se não coincidir (o ficheiro mudou depois da decisão), ignora-a e volta a pedir.
- `"decisao": "aprovado"` → segue para o passo seguinte (e limpa `pendente`). `"decisao": "alteracoes"` → aplica a `nota`, volta a gravar `pendente` e pede de novo.
- Uma mensagem sem entrada correspondente no ficheiro não é aprovação.

## Leis

- **Uma tarefa por vídeo.** O que não ajuda a concluir a tarefa (preços, histórico, outras funcionalidades) fica fora ou vai para "Saber mais" na transcrição.
- **A voz manda no tempo.** Gera-se a voz primeiro; a duração das cenas e o instante de cada destaque vêm de `timing.json`. Nunca esticar a voz para caber na imagem.
- **Cada ação no ecrã tem um marcador.** Todo o clique, campo, menu ou resultado mostrado tem um `[[id]]` no guião, na palavra em que a voz o nomeia.
- **Mostrar a interface real.** Nomes de botões, menus e mensagens são os do i18n do projeto, ditos e mostrados exatamente iguais. Dados sempre fictícios.
- **pt-PT do princípio ao fim.** Escrita segundo a persona (tratamento, tom, vocabulário); texto lido passa sempre pelo normalizador.
- **Legendas sempre.** `legendas.pt-PT.vtt` acompanha todos os vídeos.
- **Nada secreto sai do repositório.** Sem chaves, `.env`, hosts internos, nomes ou emails reais — nem no ecrã, nem na voz, nem nas legendas.

## Licenças — só o que pode ser comercializado

| Peça | Usar | Não usar |
|---|---|---|
| Voz | **Azure AI Speech** (padrão, licença comercial); `local` = `tts_eu_pt`, Apache-2.0, experimental; `piper` = Piper `pt_PT-tugao-medium` (voz MIT, dataset CC0), via venv de `~/tools/voz-pt`; `sopro` = Sopro v2 Turbo (Apache-2.0, pt-PT nativo) a clonar o .wav em `voz.id` (relativo a `~/tools/voz-pt`), via `voz.py --motor sopro` com verificação de sotaque | **edge-tts** (serviço não oficial — proibido); `hyperframes tts`/Kokoro (só pt-BR) |
| Vídeo | Hyperframes (Apache-2.0), ffmpeg, Playwright | — |
| Ator | Blender (GPL; os renders são do utilizador, sem restrições), rig e props gerados pelos scripts da skill ou dados pelo utilizador | Modelos ou texturas de terceiros sem licença comercial; geradores 3D com licença que exclua a UE (ex.: Hunyuan3D) |
| Música/SFX | Ficheiros com licença comercial confirmada (do utilizador ou CC0) | Faixas sem licença verificada, incluindo as da /brag, até confirmar a licença |
| Referências | Inspiram o estilo (ritmo, cores, enquadramento) | Copiar música, imagens, texto ou clonar vozes de terceiros |

`persona.py` e `tts.py` recusam motores fora da lista. Não contornar.

## Comandos de persona e voz

Detalhe em [references/passo-0-estilo.md](references/passo-0-estilo.md). Formato e campos da persona em [references/personas.md](references/personas.md).

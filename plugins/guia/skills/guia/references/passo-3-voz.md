# Passo 3: Voz, timing e verificação

A voz é gerada **antes** da composição. Tudo o que é tempo no vídeo vem daqui.

## Comandos

```bash
S=<skill-dir>/scripts; O=<saida>
# 1. voz por cena (só regera cenas cujo texto/voz mudou)
uv run --project $S python $S/tts.py --preparado $O/work/voz/preparado.json \
  --persona $O/work/persona.json --lexico <repo>/.guia/lexico.pt-PT.json --saida $O/work/voz
# 2. timeline, legendas, narração única, transcrição
uv run --project $S python $S/timing.py --preparado $O/work/voz/preparado.json --voz $O/work/voz \
  --persona $O/work/persona.json --saida $O/work/saida-voz --titulo "<título>"
# 3. verificação (transcreve e compara)
uv run --project $S python $S/verify.py --preparado $O/work/voz/preparado.json \
  --timing $O/work/saida-voz/timing.json --audio $O/work/saida-voz/narracao.wav
```

Saídas em `work/saida-voz/`: `timing.json` (cenas com `inicio`, `duracao`, `voz_inicio`, marcadores com `t` absoluto), `legendas.pt-PT.vtt/.srt`, `narracao.wav`, `transcricao.md`, `verificacao.json`.

## Motores

- `azure` (padrão): precisa de `AZURE_SPEECH_KEY` e `AZURE_SPEECH_REGION`. Limites de palavra exatos; aplica `ipa` do léxico via `<phoneme>`.
- `local` (experimental): `tts_eu_pt`; limites de palavra por transcrição. Avisar o utilizador que a qualidade não está avaliada.
- Qualquer outro motor é recusado pelos scripts — é uma regra de licença, não um erro a contornar.

## Léxico do projeto — `<repo>/.guia/lexico.pt-PT.json`

```json
[
  {"termo": "Faturix", "dizer": "Faturix", "ipa": "fɐtuˈɾiʃ"},
  {"termo": "SaaS", "dizer": "sás"},
  {"termo": "PDF", "dizer": "pê dê éfe"}
]
```

`termo` é o que está escrito no guião; `dizer` é o que vai para a voz; `ipa` (só Azure) fixa a pronúncia. Criar o ficheiro se não existir; acrescentar entradas sempre que uma palavra soar mal. O léxico é do projeto, não da persona.

## Verificação

`verify.py` usa `npx hyperframes transcribe -l pt -m large-v3` (a primeira execução descarrega o modelo Whisper, ~3 GB; avisar o utilizador). Alternativa mais leve: `npx hyperframes models install parakeet`.

| Resultado | Ação |
|---|---|
| Todas as cenas ≥ 85% | Portão passado |
| Palavras em falta num nome de produto/sigla | Acrescentar ao léxico (`dizer` ou `ipa`) e regerar só essa cena: `tts.py … --cena <id>` |
| Frase saltada ou cortada | Ver `work/voz/<cena>.ssml`; corrigir o guião; repetir 1–3 |
| Transcrição indisponível | Entregar `narracao.wav` ao utilizador para ouvir e pedir confirmação explícita |

Nomes próprios estrangeiros podem falhar a transcrição mesmo bem pronunciados: nesse caso, ouvir esse trecho em vez de forçar o léxico.

## Duração

Comparar `timing.json → total` com o intervalo do tipo. Se exceder: cortar texto no guião (não subir `voz.velocidade` mais de +10%) e repetir.

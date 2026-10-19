# Passo 0: Estilo (persona, voz, tom, referências)

## 1. Resolver a persona desta execução

Mapear as opções da chamada para `--set` e resolver para `work/persona.json`:

| Opção | `--set` |
|---|---|
| `--voz duarte` | `voz.id=duarte` (aliases: raquel, duarte, fernanda) |
| `--tom direto` / texto livre | `escrita.tom=direto` (texto livre entre aspas) |
| `--tratamento tu` | `escrita.tratamento=tu` |
| `--formato vertical` | `visual.formato=vertical` |
| `--musica` / `--sem-musica` | `audio.musica.ativa=true` / `false` |
| `--legendas-gravadas` | `visual.legendas.gravadas=true` |

```bash
uv run --project <skill-dir>/scripts python <skill-dir>/scripts/persona.py resolver \
  --projeto <repo> [--persona <nome>] [--set voz.id=duarte]... --saida <saida>/work/persona.json
```

Se houver `--ref`, analisar as referências (secção 4) **antes** de resolver e passar o que delas resulta como `--set`.

## 2. Confirmar a voz (primeira vez com esta persona/voz)

Se a persona não tem `amostra`, ou a voz mudou nesta chamada, gerar uma amostra com uma frase do próprio guia (com o nome do produto e um número) e entregá-la ao utilizador para ouvir antes de gerar o vídeo:

```bash
uv run --project <skill-dir>/scripts python <skill-dir>/scripts/tts.py \
  --amostra "<frase com nome do produto>" --persona <saida>/work/persona.json \
  [--lexico <repo>/.guia/lexico.pt-PT.json] --saida <saida>/work/amostra.wav
```

**Credenciais Azure.** Se faltar `AZURE_SPEECH_KEY`/`AZURE_SPEECH_REGION`, parar e pedir ao utilizador que as defina (portal Azure → recurso "Speech" → "Keys and Endpoint"; o nível F0 é gratuito). Nunca trocar para um motor fora da lista de licenças do SKILL.md para "desenrascar".

## 3. Tons

| Tom | Para | Escrita | Ritmo / visual |
|---|---|---|---|
| `didatico` | Tutoriais passo a passo | Uma ação por frase; resumo no fim | Calmo; destaque antes de cada clique |
| `amigavel` | Suporte a clientes finais | Mais próximo; uma frase de contexto por passo | Calmo; transições suaves |
| `direto` | Dicas 15–30s | Sem introdução; ação na primeira frase | Médio; cortes secos |
| `institucional` | B2B, setor público | Formal; preferir `impessoal`; sem humor | Calmo; sem música |
| `novidade` | Notas de versão | "O que mudou" na primeira cena; mais energia | Médio; uma revelação forte |

Texto livre ("como um colega paciente ao telefone") mapeia para o preset mais próximo no plano, guardando a frase original em `escrita.tom`.

## 4. Referências (`--ref`)

| Tipo | O que fazer |
|---|---|
| Vídeo local (mp4/mov/webm) | `analyze_ref.py <video> --saida <saida>/work/referencias [--transcrever]`; abrir a folha de contacto PNG e olhar |
| URL de vídeo | Só se o utilizador fornecer um ficheiro descarregável ou autorizar a transferência; nunca contornar proteções de plataformas |
| Imagem / screenshot | Ler a imagem: paleta, tipografia, densidade, estilo de destaque e de cursor |
| URL de site | Ler a página: cores (CSS) e fontes, como a /brag |
| Texto / guião exemplo | Medir tratamento, comprimento de frase, aberturas, fechos, palavras a evitar |
| Persona ou guia anterior | Ler `persona.yaml` ou o `guia-plan.md` desse guia |

Converter medidas em campos da persona:

| Medida | Campo |
|---|---|
| `plano_medio_s` ≥ 4 / 2–4 / < 2 | `visual.ritmo_cortes` = calmo / medio / rapido |
| `palavras_por_minuto` | `escrita.palavras_por_minuto`; `voz.velocidade` ≈ (ppm_ref / 150 − 1) × 100 %, limitado a ±15% |
| Folha de contacto | `visual.destaque`, `visual.cursor`, `visual.legendas.estilo`, `visual.formato` |
| Música presente / volume | `audio.musica.ativa`, `audio.musica.volume` (≤ 0.12) |

Escrever `<saida>/work/referencias.md` (uma linha por referência: origem → o que foi extraído) e acrescentar à persona `referencias: [{origem, extraido}]`. Não copiar a mídia para a persona.

## 5. Comandos de persona e voz

| Pedido | Ação |
|---|---|
| `/guia persona listar` | `persona.py listar --projeto <repo>` |
| `/guia persona mostrar X` | `persona.py mostrar X --projeto <repo>` |
| `/guia persona criar X [--ref …]` | Perguntar (AskUserQuestion) nível (global/projeto), tratamento, tom, formato; analisar referências; gerar amostras das vozes (`voices.py amostras`) e pedir escolha; escrever YAML em `work/` e `persona.py guardar --de <yaml> --nivel <nível>`; guardar a amostra escolhida como `amostra.wav` na pasta da persona e preencher `amostra` |
| `/guia persona editar X …` | `persona.py resolver --persona X --set … --saida work/x.json` → `persona.py guardar --de work/x.json --nivel <o nível onde X está>` (versão sobe) |
| `/guia persona apagar X` | Confirmar com o utilizador; `persona.py apagar X --nivel …` |
| `/guia persona ouvir X` | Gerar amostra com `tts.py --amostra` e entregá-la |
| `/guia vozes` | `voices.py listar`; com o OK do utilizador, `voices.py amostras --persona … --saida work/amostras` e entregar os WAV |

Para tornar uma persona a padrão de um projeto: escrever `persona_padrao: <nome>` em `<repo>/.guia/config.yaml`.

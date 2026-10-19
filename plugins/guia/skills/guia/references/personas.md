# Personas

Uma persona guarda tudo o que define o estilo de um guia, para reutilizar e partilhar.

## Locais e prioridade

| Nível | Caminho | Uso |
|---|---|---|
| global | `~/.claude/guia/personas/<nome>/persona.yaml` (ou `$GUIA_HOME`) | Estilos pessoais, entre projetos |
| projeto | `<repo>/.guia/personas/<nome>/persona.yaml` | Estilo da marca do cliente, versionado com a equipa |
| padrão do projeto | `<repo>/.guia/config.yaml` → `persona_padrao: <nome>` | Quando não há `--persona` |

Resolução: `padrao` → persona escolhida (projeto ganha ao global com o mesmo nome) → `--set` da chamada. Campos em falta herdam da `padrao`. A `padrao` global é criada automaticamente a partir de `<skill-dir>/assets/personas/padrao.yaml`.

## Campos

| Campo | Valores | Notas |
|---|---|---|
| `nome`, `descricao` | texto | |
| `versao` | inteiro | sobe sozinho a cada `guardar`; o `guia-plan.md` regista a versão usada |
| `voz.provider` | `azure`, `local` | outros são recusados (licença comercial) |
| `voz.id` | id Azure ou alias `raquel`/`duarte`/`fernanda` | |
| `voz.velocidade`, `voz.tom_voz`, `voz.volume` | `"+0%"`, `"+0Hz"`, `"+0%"` | prosódia SSML |
| `voz.pausa_entre_frases_ms`, `pausa_inicio_cena_ms`, `pausa_fim_cena_ms` | ms | |
| `escrita.tratamento` | `voce`, `tu`, `impessoal` | o normalizador avisa de formas incoerentes |
| `escrita.tom` | preset ou texto livre | |
| `escrita.registo` | texto | |
| `escrita.palavras_por_minuto` | inteiro | para estimar duração |
| `escrita.abertura`, `escrita.fecho` | texto ou `null` | frases-modelo, não fixas |
| `escrita.evitar` | lista | |
| `visual.formato` | `landscape`, `vertical`, `square` | |
| `visual.ritmo_cortes` | `calmo`, `medio`, `rapido` | |
| `visual.destaque`, `visual.cursor` | texto | |
| `visual.legendas.estilo`, `.gravadas` | texto, bool | |
| `visual.marca` | `herdar-do-projeto` ou descrição | |
| `audio.musica.ativa`, `.volume` | bool, ≤ 0.12 | só faixas licenciadas |
| `audio.sfx` | texto | |
| `corpo.ativo` | bool (omissão `false`) | liga o ator 2D (passos 2b, 3b, 3c) |
| `corpo.personagem` | nome da pasta em `<repo>/.guia/corpo/` | vocabulário, props e rig da personagem |
| `corpo.roupa` | id em `vocabulario.json → roupas` | roupa por omissão; a atuação pode trocar |
| `corpo.cenas` | `historias`, `todas` | onde o ator entra |
| `corpo.lado` | `esquerda`, `direita`, `livre` | preferência de posição no ecrã |
| `corpo.altura_px` | inteiro | altura da personagem no vídeo (cabeça acima do terço de baixo no vertical) |
| `referencias` | `[{origem, extraido}]` | resumo, nunca a mídia |
| `amostra` | nome do WAV na pasta da persona | |

## O que não guardar

Chaves Azure (ficam em variáveis de ambiente), mídia de terceiros, nomes ou dados reais de clientes.

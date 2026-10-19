# Passo 3c: Render do ator (Blender)

Só com `persona.corpo.ativo`. Transforma cada `work/ator/cena-NN.atuacao.json` numa camada de vídeo com transparência para a composição. O Blender corre headless; não é preciso abri-lo.

## 1. Prévia (sempre primeiro)

```bash
ator.py render --personagem <personagem> --saida <saida> --previa
```

Renderiza 6 frames por cena e junta-os em `work/ator/cena-NN-folha.png`. **Olhar para cada folha** e confirmar:

- braços e props dentro do quadro e na mão certa;
- a expressão de cada frame bate com a frase que se ouve nesse instante;
- os gestos apontam para o lado certo do ecrã.

Corrigir a folha de atuação (passo 3b) e repetir a prévia até estar certo.

## 2. Render final

```bash
ator.py render --personagem <personagem> --saida <saida> [--cenas cena-01,cena-06]
```

Por cena: frames PNG em `work/ator/cena-NN/` → `work/composition/assets/ator-cena-NN.webm` (VP9 com canal alfa). ≈ 25 s por cada 10 s de cena.

## Geometria da camada (para o passo 4)

O render é 720×1080 com a personagem sempre no mesmo sítio do quadro:

| ponto | x (px) | y (px) |
|---|---|---|
| centro do corpo | 278 | — |
| pés (chão) | — | 1047 |
| topo da cabeça | — | 275 |

Altura da personagem no render = 772 px. Para a pôr com `altura_px` da persona e os pés em (X, Y) do vídeo:

```
s = altura_px / 772
width = 720·s   height = 1080·s
left = X − 278·s   top = Y − 1047·s
```

Os props de cenário e os braços levantados usam o espaço acima e à direita da personagem no quadro (âncoras do vocabulário).

## Portão

`RENDER_OK`: um `ator-cena-NN.webm` por cena, com `frames = ⌈duração × 30⌉` e canal alfa (o script verifica com ffprobe).

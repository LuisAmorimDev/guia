# Passo 5: Render e entrega

## Render e volume

```bash
cd <saida>/work/composition
npx hyperframes render --quality high --output ../../guia.render.mp4
cd <saida>
ffmpeg -y -i guia.render.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 guia.mp4
```

Pré-visualização opcional antes do render final: `npx hyperframes preview` (dar o URL ao utilizador).

## Poster como frame 0

Escolher o frame mais claro do **resultado** (última cena, estado final visível e assente) e fixá-lo como frame 0, como na /brag:

```bash
ffmpeg -ss <t> -i guia.mp4 -frames:v 1 -q:v 2 guia.jpg
ffmpeg -y -i guia.mp4 -i guia.jpg -filter_complex "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]" \
  -map "[v]" -map "0:a?" -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -c:a copy \
  -movflags +faststart guia.poster.mp4 && mv guia.poster.mp4 guia.mp4
```

## Ficheiros de apoio

- Copiar de `work/saida-voz/`: `legendas.pt-PT.vtt`, `legendas.pt-PT.srt`, `transcricao.md`.
- `capitulos.txt`: uma linha por cena de `timing.json` — `MM:SS <título da cena>`.
- Se `visual.legendas.gravadas` for falso mas o utilizador quiser uma versão legendada: `ffmpeg -i guia.mp4 -vf subtitles=legendas.pt-PT.srt -c:a copy guia.legendado.mp4`.
- `kb-snippet.md`:

```html
<video controls preload="metadata" poster="guia.jpg">
  <source src="guia.mp4" type="video/mp4">
  <track kind="captions" srclang="pt-PT" label="Português" src="legendas.pt-PT.vtt" default>
</video>
```
seguido do conteúdo de `transcricao.md` (serve de artigo para a base de conhecimento).

## Estrutura final

```
docs/guias/<slug>/
  guia.mp4  guia.jpg  legendas.pt-PT.vtt  legendas.pt-PT.srt
  transcricao.md  capitulos.txt  kb-snippet.md
  guia-plan.md  narracao.md
  work/   (persona.json, voz/, saida-voz/, composition/, capturas/, referencias/)
```

Sugerir ao utilizador acrescentar `docs/guias/*/work/` ao `.gitignore` se não quiser versionar intermédios.

## Guardar o estilo

Se esta execução usou opções ou referências que não estão na persona, perguntar numa linha: "Guardar este estilo como persona? (nome, global ou projeto)". Com resposta afirmativa: `persona.py guardar --de <saida>/work/persona.json --nivel <nível>` depois de pôr o nome escolhido em `nome`, e copiar a amostra/um excerto da narração para `amostra.wav` na pasta da persona.

## Dizer ao utilizador

- Onde está o vídeo e os ficheiros de apoio.
- Duração, voz e persona (com versão) usadas.
- Resultado da verificação da voz (percentagem por cena; o que foi aceite com desvio).
- Oferecer: regerar uma cena, mudar a voz/tom, ou criar a versão vertical.

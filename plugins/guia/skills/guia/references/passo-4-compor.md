# Passo 4: Compor com Hyperframes

Igual à /brag na divisão de responsabilidades: a /guia define conteúdo, tempos e material; o Hyperframes decide a implementação.

## Preparar o Hyperframes

1. `npx hyperframes skills check`. Se as skills de domínio não estiverem instaladas, pedir autorização ao utilizador e correr `npx hyperframes skills` (altera a configuração das ferramentas de IA).
2. Carregar `hyperframes-core`, `hyperframes-animation`, `hyperframes-creative`, `hyperframes-keyframes`, `hyperframes-cli`. Não entrar na entrevista do `hyperframes` nem no fluxo genérico de promo/launch.
3. Sem as skills: `npx hyperframes docs <tópico>` (data-attributes, compositions, gsap, rendering).

## Material visual

**Captura real** (preferida): arrancar a app (`npm run dev` / `nuxt dev`), entrar com o utilizador de demonstração e capturar o fluxo com Playwright em `work/capture.mjs`, no tamanho do formato. Um screenshot por estado relevante (antes/depois de cada marcador) e, se útil, `recordVideo` para movimentos contínuos (scroll, carregamento). Esconder dados reais; preencher com dados fictícios. Páginas públicas também podem usar `npx hyperframes capture <url>`.

```js
// work/capture.mjs — esqueleto
import { chromium } from 'playwright';
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await p.goto('http://localhost:3000/login');
// … login demo, navegar, e por cada estado:
await p.screenshot({ path: 'work/capturas/cena-01-avatar.png' });
await b.close();
```

Guardar também o bounding box de cada elemento marcado (`await el.boundingBox()`) em `work/capturas/alvos.json` (`{ "<marcador>": {x,y,width,height} }`) para o destaque e o cursor caírem no sítio certo.

**Recriada**: reconstruir a UI em HTML com as variáveis CSS, fontes e componentes do projeto (como a /brag), quando a app não arranca ou o estado é difícil de reproduzir.

## Brief — `<saida>/work/composition-brief.md`

```markdown
# Brief Hyperframes: <título>
## Saída
- Composição: <saida>/work/composition/ · Render: <saida>/guia.mp4
- Formato: <formato> <L>x<A> · 30fps · Duração: <timing.total>s (fixa — vem da voz)
## Áudio
- Narração: assets/narracao.wav em 0s, data-track-index 3, volume 1 (não cortar, não esticar)
- Música: <ficheiro licenciado e volume da persona ≤ 0.12, ou nenhuma>
- SFX: <persona.audio.sfx>; cliques no instante do marcador; ficheiros com licença confirmada
## Cenas (de timing.json)
| cena | início | duração | ecrã | marcadores (t absoluto → evento) |
## Eventos por marcador
- destaque: entra 0.15s antes de t, mantém-se até ao marcador seguinte ou fim da cena
- clique: cursor chega ao alvo 0.3s antes de t; clique e SFX em t
- escrever: texto fictício aparece entre t e t + duração da palavra seguinte
- zoom: 1.2–1.4×, começa em t − 0.3s, alivia no fim da cena
- resultado: toast/estado aparece em t e segura até ao fim da cena
## Legendas
<gravadas: desenhar a partir de legendas.pt-PT.vtt no estilo da persona | em ficheiro à parte>
## Identidade visual / persona
<cores, fontes, destaque, cursor, ritmo de cortes>
## Regras
- Mostrar a interface real; textos exatamente como no i18n
- Tudo legível; nada de texto a piscar; transições do ritmo da persona
- Correr `npx hyperframes check` (portão único antes do render)
- Criação e render locais
```

Copiar para `work/composition/assets/`: `narracao.wav`, capturas, música/SFX escolhidos. Caminhos relativos à composição.

## Ator (com `persona.corpo.ativo`)

Cada `assets/ator-cena-NN.webm` (passo 3c) entra como um vídeo mudo com o tempo exato da cena:

```html
<video id="ator-06" class="abs clip ator" src="assets/ator-cena-06.webm" muted playsinline
       data-start="<cena.inicio>" data-duration="<cena.duracao>" data-track-index="1"
       style="left:<left>px;top:<top>px;width:<width>px;height:<height>px"></video>
```

- Posição e tamanho pela fórmula do passo 3c (`altura_px` da persona, pés no chão da cena). Nunca por cima do telemóvel, do destaque ou do toque; no vertical, a cabeça acima do terço de baixo.
- **Ordem no DOM = camada**: antes dos cartões de papel para o ator ficar por trás deles (a mão que aponta "toca" no cartão); depois, para ficar à frente.
- O vídeo cobre a cena inteira; para o ator entrar ou sair a meio, animar só a `opacity` com o GSAP (entra 0,4 s, sai com o resto da cena). Não mexer no `currentTime`.
- Nada no HTML repete o que o ator mostra (prop na mão, nuvem de cenário) e vice-versa.

## Portão

```bash
cd <saida>/work/composition && npx hyperframes check
```

Corrigir todos os erros (incluindo contraste). Verificar com `npx hyperframes snapshot` que, em cada `t` de marcador, o destaque está sobre o elemento certo.

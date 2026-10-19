# Passo 2b: Ator, cenas e props

Só quando `persona.corpo.ativo` é verdadeiro. Vem logo depois de `narracao.md`: decide onde o ator entra, o que segura, que roupa veste e **pede ao utilizador os props que faltam**, antes de gastar tempo com voz e render.

`<personagem>` = `<repo>/.guia/corpo/<persona.corpo.personagem>/` · `ator.py` = `uv run --project <skill-dir>/scripts python <skill-dir>/scripts/corpo/ator.py`

## 1. Personagem pronta

- Se a pasta `<personagem>` não existe: copiar o modelo `<skill-dir>/assets/corpo/colega/` (vocabulário + props) e perguntar numa linha se as cores (`personagem.pele`, `cabelo`, roupas) devem seguir a marca do projeto. Ajustar `vocabulario.json`.
- `ator.py preparar --personagem <personagem>`: constrói `rig.blend` e `props.blend` quando faltam ou estão desatualizados, com prévias em `<personagem>/previas/` (`rig.png`, `props.png`). Na primeira vez, mostrar `rig.png` ao utilizador.

## 2. Cenas com ator

| `corpo.cenas` | O ator entra em |
|---|---|
| `historias` | cenas de situação ou conceito sem a app no ecrã (as de "papel recortado" do guião), e no resumo final |
| `todas` | todas, mas nunca por cima do telemóvel, do destaque ou do toque |

Para cada cena com ator, decidir o **papel**: o que o ator faz enquanto a composição HTML conta o resto. O ator não duplica o que a composição já mostra (se a nuvem é desenhada em HTML, o ator aponta para ela, não traz outra).

## 3. Roupa

`corpo.roupa` por omissão. Se a narrativa pede outra (jardim, oficina…), escolher em `vocabulario.json → roupas`. Uma roupa nova é só material (cor, padrão `liso|riscas|xadrez|bolinhas`, `cor_padrao`, `escala`): acrescentar a entrada ao vocabulário e dizer ao utilizador.

## 4. Pedido de props — `<saida>/work/ator/props-pedido.json`

```json
{ "props": [
  { "id": "caderno", "tipo": "mao", "descricao": "caderno onde anotava os trabalhos", "cenas": ["cena-01"] },
  { "id": "regador", "tipo": "mao", "descricao": "regador de metal, para o trabalho de rega", "cenas": ["cena-01"] }
] }
```

`tipo`: `mao` (segurado, até 0.6 de tamanho) ou `cenario` (pousado numa âncora do vocabulário). Pedir só o que dá sentido à cena — 0 a 2 props por cena.

```bash
ator.py props --personagem <personagem> --pedido <saida>/work/ator/props-pedido.json
```

Sai com 0 (`PROPS_COMPLETOS`), 2 (há `EM FALTA`) ou 1 (pedido incoerente com a biblioteca).

## 5. Pedir os que faltam

Com props em falta, **uma** pergunta ao utilizador com a lista (id — descrição — cenas) e três respostas:

1. **Crio-os em papel recortado** (recomendado): escrever `<personagem>/props/<id>.json` seguindo o formato no topo de `<skill-dir>/scripts/corpo/props_spec.py` — formas simples (retângulo, elipse, polígono, cápsula, arco), cores da marca, origem (0,0) no ponto onde a mão pega, `camada` ≤ 0.2 nos props de mão, cabeça da personagem ≈ 0.6 de largura como escala. Correr `ator.py preparar`, mostrar `previas/props.png` e ajustar até o utilizador aprovar.
2. **Dou-te um .blend**: o utilizador põe `<personagem>/props/<id>.blend` com a coleção `Prop.<id>` (contrato em `construir_props.py`) e escreve-se `<id>.json` com `"blend": "<id>.blend"` em vez de `"pecas"`.
3. **Seguir sem eles**: tirar do pedido e do plano.

## Registar no plano

Acrescentar ao `guia-plan.md`:

```markdown
## Ator
| cena | papel do ator | roupa | props |
```

## Portão

`ator.py props` → `PROPS_COMPLETOS` e `ator.py preparar` → `PREPARAR_OK`.

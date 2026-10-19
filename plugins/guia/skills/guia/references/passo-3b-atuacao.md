# Passo 3b: Atuação (folha escrita pelo LLM)

Só com `persona.corpo.ativo`. Depois da voz: precisa de `work/saida-voz/timing.json` (marcadores e durações) e de `work/voz/cena-NN.palavras.json` (tempo de cada palavra). Para cada cena com ator do plano, o LLM escreve `<saida>/work/ator/cena-NN.atuacao.json`.

## O menu fechado

Ler `<personagem>/vocabulario.json` (emoções, gestos, olhar, roupas, âncoras) e as `descricao` de `<personagem>/props/*.json`. **Só** esses valores: qualquer chave ou valor fora do menu é erro e o render não arranca. O formato completo está no topo de `<skill-dir>/scripts/corpo/atuacao.py`.

```json
{
  "versao": 1, "cena": "cena-06", "roupa": "casual_trabalho",
  "segmentos": [
    { "desde": "inicio", "emocao": "pensativo", "intensidade": 0.5, "gesto": "maos_juntas", "olhar": "frente", "prop": null },
    { "desde": "palavra:recomendo", "emocao": "confiante", "intensidade": 0.8, "gesto": "explicar", "olhar": "frente", "prop": null },
    { "desde": "[[nuvem]]", "emocao": "alegre", "intensidade": 0.7, "gesto": "apontar_cima", "olhar": "cima",
      "prop": { "id": "telemovel", "mao": "L" } }
  ],
  "cenario": [ { "prop": "nuvem", "ancora": "acima_dir", "desde": "palavra:guardado", "ate": null } ]
}
```

- `desde`: `inicio` (obrigatório no 1.º), `[[marcador]]` do guião, `palavra:<texto>` (1.ª ocorrência depois do segmento anterior) ou segundos da cena — só para pausas sem palavra.
- `ajustes_roupa` (opcional): `{"camisola": {"cor": "#9c2b2b", "padrao": "riscas"}}` para afinar a roupa sem criar outra.
- `.L` / `"mao": "L"` é a mão do lado **direito do ecrã**; `.R` a do lado esquerdo.

## Como atuar

- **A emoção segue o sentido da frase**, não a palavra solta: uma recomendação é `confiante`, um risco é `preocupado`, a solução é `alegre`, uma alternativa é `pensativo`.
- **Ritmo calmo**: uma mudança a cada 1,2 s no mínimo; 3–6 segmentos numa cena de 10 s.
- **Intensidade** 0.5–0.8 no normal; 0.9+ só no pico da cena (a boa notícia, o resumo).
- **Gestos com destino**: `apontar_*` e `olhar` para onde o elemento está **no ecrã** em relação ao ator (o telemóvel à esquerda do ator → `apontar_esq`, `olhar: esquerda`).
- **Props** só os do pedido (passo 2b). Um prop de mão aparece no segmento que o tem e sai no primeiro que não o tem; a mão endireita-o sozinha.
- **Não duplicar a composição**: se a cena já desenha a nuvem ou o telemóvel em HTML, o ator aponta ou olha, não traz outro igual.
- A boca (visemas), o piscar de olhos, a respiração e o balanço são automáticos — não se escrevem.

## Portão

```bash
ator.py validar --personagem <personagem> --saida <saida>
```

`VALIDAR_OK` em todas as cenas. Os erros dizem o campo e o valor; corrigir a folha, nunca o vocabulário para fazer passar uma folha.

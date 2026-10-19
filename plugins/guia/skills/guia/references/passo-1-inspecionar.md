# Passo 1: Inspecionar o projeto

O objetivo é encontrar a funcionalidade pedida no código e os **textos exatos** que o utilizador vê.

## Detetar o framework

| Sinal | Framework | Rotas | Textos (i18n) |
|---|---|---|---|
| `next` em `package.json`, `app/` | Next (App Router) | `app/**/page.tsx` (grupos `(x)`, `[param]`) | `next-intl`: `messages/pt-PT.json` / `pt.json`; `next-i18next`: `public/locales/pt-PT/*.json` |
| `next`, `pages/` | Next (Pages Router) | `pages/**/*.tsx` | idem |
| `nuxt` em `package.json` | Nuxt 3/4 | `pages/**/*.vue` (ou `app/pages/`) | `@nuxtjs/i18n`: `locales/` ou `i18n/locales/pt-PT.json`, `nuxt.config` → `i18n.locales` |

Procurar também: componentes do fluxo (`components/`), stores (Pinia `stores/`, Zustand/Redux), validações e mensagens de erro (zod, vee-validate, server actions, `server/api`), toasts. Sem i18n: os textos estão nos próprios componentes.

Identidade visual: variáveis CSS (`:root`, `@theme` do Tailwind 4, `tailwind.config`), `app.config.ts` (Nuxt UI), fontes (`next/font` no layout, `@nuxt/fonts`, Google Fonts), logótipo em `public/`.

Para captura real: script `dev` em `package.json`, porta, autenticação (utilizadores de demonstração em seeds/fixtures/storybook/mocks). Nunca usar credenciais reais.

Se o projeto só tiver textos pt-BR ou inglês: os nomes da interface ditos na narração são os que estão no ecrã, tal como estão; avisar o utilizador da mistura e não "traduzir" a interface na voz.

## Não ler

`.env*`, chaves (`*.pem`, `*.key`), pastas `secrets/`/`credentials/`, `node_modules/`, `.next/`, `.nuxt/`, `.output/`, `dist/`, lockfiles.

## Questionário (responder tudo antes do Passo 2)

```
1. Tarefa: o que o utilizador consegue fazer no fim? (uma frase, verbo no infinitivo)
2. Público: quem é, que permissões/plano precisa?
3. Pré-condições: sessão iniciada, dados existentes, configuração prévia.
4. Ponto de partida: rota + o que está no ecrã ao começar.
5. Passos: para cada um — rota/componente (ficheiro), elemento, texto exato (chave i18n → valor).
6. Resultado visível: toast/estado/redirecionamento, com texto exato.
7. Erros e validações relevantes (texto exato) — só para tutorial/faq.
8. Identidade visual: fundo, texto, destaque (valores exatos), fontes, logótipo.
9. Captura: comando, porta, utilizador de demonstração, dados fictícios — ou porque será recriada.
10. Fora de âmbito: o que existe à volta mas não entra neste vídeo.
```

**Portão:** cada passo da resposta 5 aponta para um ficheiro e um texto exato. Sem isso, continuar a procurar ou perguntar ao utilizador.

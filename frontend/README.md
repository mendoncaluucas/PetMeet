# PetMeet — front-end

Painel web da equipe da ONG: fichas dos pets, processos de adoção, adotantes,
padrinhos e doações. Consome a API FastAPI que está na raiz deste repositório.

## Stack

- **React 18 + TypeScript** — componentes e contratos tipados
- **Vite 6** — servidor de desenvolvimento e build
- **React Router 6** — rotas
- **CSS puro** — sem framework de UI; os tokens estão em `src/estilos/base.css`
- **ESLint + Prettier** — padronização e análise de código (RNF12)

## Como rodar

Suba a API primeiro (instruções no README da raiz). Depois:

```bash
cd frontend
npm install
npm run dev
```

O painel abre em `http://localhost:5173`. Entre com o usuário criado pelo seed
da API (`admin@petmeet.org.br` / `admin123456`).

### Como o front acha a API

Em desenvolvimento, o Vite faz proxy de `/api` para `http://localhost:8000` e de
`/uploads` para o mesmo lugar (veja `vite.config.ts`). Isso evita qualquer
questão de CORS enquanto se desenvolve.

Em produção, aponte `VITE_API_URL` para a URL pública da API (sem barra no
final) e adicione a URL do painel em `ORIGENS_PERMITIDAS` no `.env` da API:

```bash
cp .env.example .env    # dentro de frontend/
# VITE_API_URL=https://api.suaong.org.br
npm run build           # gera dist/
```

## Scripts

```bash
npm run dev           # servidor de desenvolvimento
npm run build         # checagem de tipos + build de produção em dist/
npm run preview       # serve o dist/ para conferir o build
npm run typecheck     # só a checagem de tipos
npm run lint          # ESLint
npm run format        # Prettier escrevendo nos arquivos
```

## Organização

```
src/
  api/          cliente HTTP, tipos espelhando os schemas Pydantic e uma
                função por endpoint (recursos.ts)
  auth/         sessão do usuário (token no localStorage)
  componentes/  peças reaproveitadas: campos, selos, avisos, paginação
  paginas/      uma por rota
  estilos/      base.css (tokens, tipografia, esqueleto) e componentes.css
  util/         formatação, rótulos em português e o hook de requisição
```

O único ponto de acoplamento com o backend é `src/api/tipos.ts`. Se um schema
mudar em `app/esquemas/`, ajuste esse arquivo e o TypeScript aponta todo lugar
que precisa mudar junto.

## Onde entram as imagens

- **Foto do pet** — enviada na própria ficha (`/pets/:id`, botão "Enviar foto").
  Vai para `POST /pets/{id}/foto` e volta como `foto_url`. Quando não existe
  foto, a ficha mostra uma moldura hachurada com a inicial do animal: o espaço
  da imagem continua reservado.
- **Foto do abrigo na tela de login** — fica em `public/abrigo.jpg`. Para
  trocar, substitua o arquivo mantendo o mesmo nome; nenhum código muda. Se o
  arquivo não existir, o painel cai na textura de fundo sozinho. O texto da
  esquerda tem fundo próprio, então continua legível com qualquer imagem,
  clara ou escura.

## Decisões de interface

**A cor só aparece quando significa alguma coisa.** A tarja da esquerda de uma
ficha é o estado de saúde do animal (vermelho = em tratamento médico, âmbar =
em recuperação, verde = saudável). A situação de adoção é um selo separado,
porque são dois eixos diferentes no banco. Fora disso, a interface é verde,
branco e cinza.

**Sem biblioteca de ícones.** A navegação e as ações são palavras. Quem opera o
painel raramente usa o sistema todo dia e texto não precisa ser decifrado.

**Dados pessoais ficam cobertos.** CPF de adotantes e padrinhos aparece
mascarado, com um "mostrar" ao lado (RN07 / RNF03 / RNF04). Quem confere uma
lista quase nunca precisa do número inteiro.

**A página inicial diz o que fazer, não quantos registros existem.** A manchete
do painel é uma frase sobre a pendência mais urgente — tratamento médico trava
a finalização de adoção (RN01), então vem primeiro.

## Regras de negócio que a interface aplica

A API continua sendo a autoridade; o front repete algumas validações só para
avisar antes de gastar uma requisição.

| Regra | Onde aparece |
|---|---|
| RF16/RN01 — finalizar adoção de pet em tratamento | Ao escolher "Finalizado" em `/adocoes`, aparece a confirmação do acompanhamento médico. Sem marcar, o botão fica desabilitado. |
| RN02/RF17 — um único processo finalizado por pet | O 409 da API vira a mensagem "outro processo deste mesmo pet foi finalizado primeiro". |
| RF16 — doença identificada | O campo "doença em tratamento" é obrigatório sempre que o estado for "em tratamento médico". |
| RN05 — valor da doação | O formulário recusa valor zero ou negativo antes de enviar. |
| RF18/RN08 — validação | Erros 422 do FastAPI são distribuídos campo a campo no formulário. |
| RNF08 — paginação | Todas as listagens paginam. |
| RNF09 — upload | Formato e tamanho (5 MB) conferidos antes do envio. |
| RF21/RN06 — controle de acesso | Um 403 vira "seu perfil não tem permissão para esta ação". |

## O que depende do backend para ficar completo

Estes pontos estão prontos na interface até onde a API permite hoje:

- **RF10/RF11 (padrinho ↔ pet)** — não há rota para vincular um padrinho a um
  pet. O modelo `Apadrinhamento` existe no backend, mas falta serviço e rota.
  A tela de padrinhos cadastra e mostra doações; o vínculo com pets fica de
  fora até esse endpoint existir.
- **Listagem da equipe** — a API tem `POST /usuarios` mas não `GET /usuarios`,
  então a tela "Equipe" só cria contas.
- **Perfil do usuário logado** — resolvido: o painel lê o perfil em `GET /auth/me`
  e mostra a tela "Equipe" só para admin. A API continua sendo quem decide: cada
  rota relê o perfil no banco, e o painel segue tratando o 403.
- **RF22 (auditoria)** — o modelo `LogAuditoria` existe, mas nada é gravado
  ainda e não há rota de consulta.
- **Filtro de status em processos** — `GET /processos-adocao` filtra por
  `pet_id` e `adotante_id`, não por `status`. O painel filtra em memória.

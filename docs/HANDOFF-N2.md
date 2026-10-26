# Handoff — PetMeet v2.0

> Item 4.4 do [Plano de Ação](PLANO-DE-ACAO-N2.md#fase-4--fechamento--2410-a-2910)
> Redação: Lucas (Backend), para destravar a fase · Revisão: Nicholas (Requisitos) pendente
> O handoff da v1.0, da equipe original, continua em [`HANDOFF.md`](HANDOFF.md)

Este documento é para quem receber o PetMeet depois do N2: o que existe, como começar e onde o projeto morde.

## Identificação

| Campo | Valor |
|---|---|
| Case | PetMeet (case 3) |
| Equipe do N2 | Draft |
| Repositório | https://github.com/mendoncaluucas/PetMeet (fork de https://github.com/gabilbck/PetMeet) |
| Versão | `v2.0`; a recebida é a `v1.0` |
| Branches | `develop` é a padrão; `main` recebe as releases. As duas exigem os checks `Backend (lint + testes)`, `Frontend (lint + build)` e `Docker (build + publicar no GHCR)` |

## O que o PetMeet faz

Gestão de adoção e apadrinhamento de pets para ONGs de proteção animal: fichas dos pets, processos de adoção, adotantes, padrinhos e doações. No N2 entraram as duas evoluções do enunciado. O resumo está em [`NOTAS-v2.0.md`](NOTAS-v2.0.md).

| Perfil | O que faz |
|---|---|
| Admin | Tudo o que o voluntário faz, mais cadastrar a equipe e estornar doações e gastos |
| Voluntário | Pets, adoções, adotantes, padrinhos, apadrinhamentos, doações, gastos e contribuições |
| Veterinário | Pets, ficha clínica, vacinação e alta médica. Não vê cadastro de pessoas nem a parte financeira |
| Público, sem login | Só o portal de prestação de contas, em `/transparencia` |

## Como começar

Siga o [README](../README.md): ele cobre a instalação com e sem Docker, o seed com as contas de teste, os testes e as migrations. O painel tem README próprio em [`frontend/README.md`](../frontend/README.md).

Para conferir o sistema inteiro pelo painel, use o [roteiro de testes](ROTEIRO-DE-TESTES.md).

## Onde está cada coisa

| Assunto | Onde |
|---|---|
| Camadas, erros, autenticação, concorrência | [`ARQUITETURA.md`](ARQUITETURA.md) |
| Tabelas, constraints e por que cada uma existe | [`MODELO_DE_DADOS.md`](MODELO_DE_DADOS.md). É a fonte de verdade do modelo; o [`DER.md`](DER.md) é da v1.0 |
| Defeitos, armadilhas, decisões D1–D6 e o que aconteceu em cada fase | [`PLANO-DE-ACAO-N2.md`](PLANO-DE-ACAO-N2.md) |
| Critérios de aceite e decisões D7–D15 | [`HISTORIAS-FASE-2.md`](HISTORIAS-FASE-2.md) e [`HISTORIAS-FASE-3.md`](HISTORIAS-FASE-3.md) |
| Débitos herdados e situação na v2.0 | [`DEBITOS-TECNICOS.md`](DEBITOS-TECNICOS.md) |

## Onde o projeto morde

Cada item abaixo já quebrou alguma coisa durante o N2, ou quebraria se fosse feito do jeito óbvio.

1. **Rota nova precisa de decisão de acesso.** Dois testes leem o contrato OpenAPI. Em `testes/test_veterinario.py`, toda rota protegida fora da lista do veterinário tem de responder 403 para ele. Em `testes/test_transparencia.py`, só três rotas podem ficar sem login. Uma rota nova esquecida quebra um dos dois.
2. **Número que entra pela API precisa de limite.** Id sem limite volta a dar 500 acima do inteiro do Postgres (DEF-15). Use `app/rotas/parametros.py`, `IdNoCorpo` e `ValorPositivo`; `testes/test_limites.py` pega o que faltar.
3. **"Hoje" e "este mês" vêm de `app/core/tempo.py`**, no fuso de Brasília. O container roda em UTC; entre 21h e meia-noite, o dia em UTC já é o seguinte.
4. **Migration se revisa linha a linha.** O `--autogenerate` não compara CHECK, recria tipos enum que já existem e gera nomes de constraint instáveis. As migrations `0007` e `0009` foram escritas à mão por isso. O `env.py` roda todas na mesma transação: um valor de enum criado numa migration não pode ser usado por outra na mesma execução.
5. **Os testes montam o banco pelos modelos**, não pelas migrations. Por isso o CI também aplica as migrations e roda o seed: é ali que aparece uma migration que faltou.
6. **`frontend/src/api/tipos.ts` é escrito à mão.** Mudou um schema da API, ele muda no mesmo PR.
7. **Dinheiro é `Decimal`, somado no banco.** Lançamento financeiro não se apaga nem se edita: estorna-se (D13). O portal público usa schemas próprios em `app/esquemas/publico.py`, que não herdam dos internos (A-11).
8. **Depois de atualizar o código, `docker compose up -d --build`.** Sem `--build`, o container fica com a imagem antiga e entra em loop com "Can't locate revision".
9. **A regra crítica segue a leitura literal (D1)**: pet em tratamento não finaliza a adoção, sem exceção. A decisão foi do time, sem confirmação do professor; se a leitura dele for outra, o ponto de mudança é `app/servicos/processo_adocao.py`.

## Matriz de papéis

Papéis do acordo de 24/09/2026 e o que cada um tinha no plano.

| Papel | Integrante | Itens do plano | Situação na v2.0 |
|---|---|---|---|
| Product Owner | Willian Squena | Acordo, decisões D1–D6, aceite dos PRs de evolução, pitch (4.5) | Decisões aplicadas no código, sem registro do PO; pitch em preparação |
| Engenheiro de Requisitos | Nicholas Scoz dos Santos | `REQUISITOS.md` e documentos herdados (1.11), histórias das evoluções (2.1, 3.1), handoff (4.4) | Histórias e handoff redigidos pelo backend; revisão pendente. `REQUISITOS.md` não existe |
| Quality Assurance | Kaua Lucindo | Issues de defeito (0.3), roteiros de teste (1.12, 4.1) | Roteiro da v2.0 redigido pelo backend; execução pendente. Defeitos registrados no plano e nos PRs |
| Desenvolvedor Frontend | Henrique Cordeiro de Oliveira | Telas novas e corrigidas | Telas entraram junto com o backend, nos mesmos PRs |
| Desenvolvedor Backend | Lucas Rogério Mendonça | API, migrations, testes | PRs #1 a #22 |
| DevOps | Vinicius Steuernagel | Checks obrigatórios (0.1), lock (0.5), runner (0.6), verificação do zero (4.2), release (4.3) | Checks obrigatórios configurados em 25/09; lock, runner e `.gitattributes` no PR [#12](https://github.com/mendoncaluucas/PetMeet/pull/12); verificação do zero e release na fase 4 |

Os convites ao repositório de Kaua e Willian ficaram pendentes desde 24/09, e os usuários do GitHub de Vinicius e Nicholas não foram informados. Por isso os PRs entraram por bypass de administrador, sem a aprovação de outro integrante que o acordo pede. Os checks obrigatórios do CI rodaram em todos.

# PetMeet v2.0 — notas da versão

> Manutenção e evolução do N2 · Equipe Draft · 25/09 a 29/10/2026
> Parte da [`v1.0`](https://github.com/mendoncaluucas/PetMeet/tree/v1.0), recebida da equipe original. PRs [#1](https://github.com/mendoncaluucas/PetMeet/pull/1) a [#22](https://github.com/mendoncaluucas/PetMeet/pull/22).

O enunciado descreve o problema da ONG como *dificuldade em controlar fichas médicas e acompanhar doações recorrentes de padrinhos*. A v1.0 não resolvia nenhuma das duas metades. A v2.0 resolve as duas, que são também as duas evoluções exigidas no N2.

## Em números

| | v1.0 | v2.0 |
|---|---|---|
| Testes automatizados | 20 | 300 |
| Migrations | 1 | 9 |
| CI | existia, mas vermelho na `main` (DEF-01) e sem bloquear merge | verde; lint, tipos, testes, `alembic check`, seed e build do painel, obrigatórios na `main` e na `develop` |
| Defeitos corrigidos | — | 15 (DEF-01 a DEF-15) |

## Evolução 1 — ficha clínica e cartão de vacinação digital com alertas

- **Perfil veterinário.** Só ele dá alta de um tratamento médico. A equipe continua colocando o pet em tratamento, na triagem. Cada mudança de saúde vai para a auditoria.
- **Ficha clínica** do pet: atendimentos com anamnese, diagnóstico e conduta. Registro clínico não se edita nem se apaga; anula-se, com motivo, quem e quando.
- **Catálogo de vacinas**, mantido por admin e veterinário. "V10", " v10 " e "Antirrábica"/"ANTIRRÁBICA" são a mesma vacina.
- **Cartão de vacinação**: situação de cada vacina (*em dia*, *vencendo*, *vencida*) pela última aplicação válida, com o histórico completo.
- **Alertas de vencimento** no Painel da equipe e na página inicial do veterinário: vencidas e vencendo em 30 dias, das mais atrasadas primeiro. Pet adotado fica de fora.

## Evolução 2 — portal de prestação de contas automatizado

- **Apadrinhamento mensal**: o padrinho combina um valor por mês com um pet. Finalizar a adoção encerra os apadrinhamentos do pet.
- **Doação com destino**: a doação pode indicar o pet; sem pet, é doação geral.
- **Gastos da ONG**, por categoria. Gasto e doação não se editam nem se apagam: o admin estorna, com motivo, e o estorno entra no mês em que foi feito. Um mês fechado não muda depois.
- **Contribuições**: esperado × recebido de cada padrinho, mês a mês, com os pendentes em destaque para a equipe cobrar.
- **Portal público** em `/transparencia`, sem login: arrecadado, gasto e saldo dos últimos 12 meses, gastos por categoria e por pet. Só totais: nenhum nome de padrinho ou doador, nenhuma descrição de gasto.

"Automatizado" quer dizer que o portal sai do que a equipe já registra no dia a dia. Ninguém monta relatório à mão.

## Correções da v1.0

| | Defeito | PR |
|---|---|---|
| DEF-01 | O projeto não subia em instalação nova (`greenlet`) | [#1](https://github.com/mendoncaluucas/PetMeet/pull/1) |
| DEF-02 | **Regra crítica:** pet em tratamento finalizava a adoção com uma caixa marcada. Agora não finaliza, sem exceção (leitura literal, D1) | [#13](https://github.com/mendoncaluucas/PetMeet/pull/13) |
| DEF-03 a DEF-05 | Situação de adoção editável à mão: pet em tratamento marcado como adotado sem processo, segundo processo para o mesmo pet, processo preso | [#8](https://github.com/mendoncaluucas/PetMeet/pull/8) |
| DEF-06 | Cancelar e finalizar o mesmo processo ao mesmo tempo: as duas passavam | [#4](https://github.com/mendoncaluucas/PetMeet/pull/4) |
| DEF-07 | Senha acima de 72 bytes derrubava login e cadastro (500) | [#5](https://github.com/mendoncaluucas/PetMeet/pull/5) |
| DEF-08, DEF-12 | CPF validado só pela quantidade de dígitos; cadastro duplicado simultâneo dava 500 | [#7](https://github.com/mendoncaluucas/PetMeet/pull/7) |
| DEF-09, DEF-10 | Painel com o mês em UTC e totais somados só sobre os 100 primeiros registros | [#10](https://github.com/mendoncaluucas/PetMeet/pull/10) |
| DEF-11 | Seed duplicava os pets a cada execução | [#6](https://github.com/mendoncaluucas/PetMeet/pull/6) |
| DEF-13 | Não havia exclusão nem inativação de adotante | [#9](https://github.com/mendoncaluucas/PetMeet/pull/9) |
| DEF-14 | `PATCH` com `null` em campo obrigatório dava 500 | [#9](https://github.com/mendoncaluucas/PetMeet/pull/9), [#11](https://github.com/mendoncaluucas/PetMeet/pull/11) |
| DEF-15 | Id acima do inteiro do Postgres dava 500 em todas as rotas; valor da doação com 3 casas era gravado arredondado | [#18](https://github.com/mendoncaluucas/PetMeet/pull/18) |

Também entraram na verificação dos PRs, sem número de defeito, porque não chegaram a ser publicados: corridas entre alta e novo tratamento, entre apadrinhar e finalizar a adoção, e entre dois estornos do mesmo lançamento; doação com data futura; Painel contando estorno como doação. A lista completa está em [`PLANO-DE-ACAO-N2.md`](PLANO-DE-ACAO-N2.md#7-acompanhamento).

## Para quem atualiza a partir da v1.0

- Rode as migrations: `alembic upgrade head` (ou `docker compose up -d --build`, que reconstrói a imagem e aplica sozinho).
- Reinstale as dependências pelo lock: `pip install -r requirements-dev.lock` e `pip install --no-deps -e .`.
- Rode o seed de novo para ganhar o usuário veterinário (`python -m scripts.seed`). Ele não duplica nada.
- As migrations `0005` a `0009` recusam o downgrade quando ele apagaria dado clínico ou financeiro.

## Fica para depois

- Aviso diário de vacinas por e-mail (extra 2.7).
- Portal do adotante (D5).
- Rota de consulta da auditoria; auditoria em processos de adoção e em usuários.
- Observabilidade, backup e armazenamento de fotos fora do disco local (débitos herdados da v1.0).

Documentos: [Plano de Ação](PLANO-DE-ACAO-N2.md) · [Histórias da fase 2](HISTORIAS-FASE-2.md) · [Histórias da fase 3](HISTORIAS-FASE-3.md) · [Modelo de dados](MODELO_DE_DADOS.md) · [Roteiro de testes](ROTEIRO-DE-TESTES.md) · [Handoff](HANDOFF-N2.md)

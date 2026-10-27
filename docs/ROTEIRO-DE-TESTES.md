# Roteiro de testes — v2.0

> Item 4.1 do [Plano de Ação](PLANO-DE-ACAO-N2.md#fase-4--fechamento--2410-a-2910)
> Redação: Lucas (Backend), para destravar a fase · Execução e revisão: Kaua (QA)
> Versão testada: a `develop` depois do PR [#22](https://github.com/mendoncaluucas/PetMeet/pull/22), que vira a `v2.0`

Este roteiro é o teste **manual**, de ponta a ponta, pelo painel. Ele não substitui os testes automatizados (300, rodados pelo CI em todo PR). Serve para conferir que as telas fazem o que as histórias pedem, com os perfis reais, antes da release.

Cada caso tem um resultado esperado. Quem executa marca **OK** ou **Falhou** e, se falhou, descreve o que viu.

---

## Preparação

1. Siga o [README](../README.md) para subir a API e o painel, e rode o seed: ele cria um admin, um veterinário e dois pets (Rex e Mingau).
2. Contas de teste do seed:

| Perfil | E-mail | Senha |
|---|---|---|
| Admin | `admin@petmeet.org.br` | `admin123456` |
| Veterinário | `veterinario@petmeet.org.br` | `vet123456` |

3. Crie um **voluntário** em **Equipe**, entrando como admin. Ele é usado nos casos de acesso.
4. Use uma janela anônima para os casos sem login.

---

## 1. Acesso por perfil

| # | Perfil | Passos | Resultado esperado | Resultado |
|---|---|---|---|---|
| A1 | Sem login | Abrir `/pets` | Vai para a tela de login | |
| A2 | Sem login | Abrir `/transparencia` | O portal abre, sem pedir login | |
| A3 | Voluntário | Ver o menu | Painel, Pets, Vacinas, Adoções, Adotantes, Padrinhos, Contribuições, Doações, Gastos e Prestação de contas. **Sem** Equipe | |
| A4 | Admin | Ver o menu | O mesmo do voluntário, **com** Equipe | |
| A5 | Veterinário | Ver o menu | Só Início, Pets, Vacinas e Prestação de contas | |
| A6 | Veterinário | Digitar `/doacoes`, `/gastos` e `/contribuicoes` na barra de endereço | Aviso "Seu perfil não tem acesso a esta tela", sem lista nem erro | |
| A7 | Voluntário | Digitar `/equipe` | Aviso de que só administradores gerenciam a equipe | |

## 2. Regra crítica: adoção de pet em tratamento (RN01, D1)

| # | Perfil | Passos | Resultado esperado | Resultado |
|---|---|---|---|---|
| R1 | Voluntário | Na ficha do Mingau, mudar o **Estado de saúde** para "Em tratamento médico" sem preencher **Doença em tratamento** | O formulário pede a doença | |
| R2 | Voluntário | Repetir R1 com a doença preenchida | O Mingau fica em tratamento; a tarja da ficha fica vermelha | |
| R3 | Voluntário | Em **Adoções**, abrir um processo para o Mingau, aprovar e tentar finalizar | A finalização é recusada enquanto ele estiver em tratamento | |
| R4 | Voluntário | Tentar tirar o Mingau do tratamento | Recusado: só o veterinário dá alta | |
| R5 | Veterinário | Na ficha do Mingau, dar alta (Estado de saúde "Em recuperação" ou "Saudável") | A alta é gravada | |
| R6 | Voluntário | Finalizar o processo de R3 | A adoção é finalizada; o Mingau aparece como adotado | |
| R7 | Voluntário | Abrir um segundo processo para um pet que já tem processo em andamento | Recusado: um processo ativo por pet | |

## 3. Cadastros (fase 1)

| # | Perfil | Passos | Resultado esperado | Resultado |
|---|---|---|---|---|
| C1 | Voluntário | Cadastrar adotante com CPF `111.111.111-11` | Recusado: CPF inválido | |
| C2 | Voluntário | Cadastrar adotante com um CPF válido, com pontuação | Gravado | |
| C3 | Voluntário | Cadastrar outro adotante com o mesmo CPF | Recusado: CPF já cadastrado | |
| C4 | Voluntário | Excluir um adotante **sem** processo | Excluído | |
| C5 | Voluntário | Excluir um adotante **com** processo | Não exclui; o adotante pode ser inativado | |

## 4. Ficha clínica e vacinação (evolução 1)

| # | Perfil | Passos | Resultado esperado | Resultado |
|---|---|---|---|---|
| V1 | Veterinário | Na ficha do Rex, em **Ficha clínica**, registrar um atendimento com anamnese, diagnóstico e conduta | Aparece no topo da ficha clínica, com o nome do veterinário | |
| V2 | Voluntário | Abrir a ficha do Rex | Vê o atendimento, mas não tem botão de registrar nem de anular | |
| V3 | Veterinário | Anular o atendimento de V1 com **Motivo da anulação** | Continua na ficha, marcado como anulado, com motivo, quem e quando | |
| V4 | Admin | Em **Vacinas**, cadastrar uma vacina com o mesmo nome de uma existente, mudando só maiúsculas e acento | Recusado: a vacina já existe | |
| V5 | Veterinário | No **Cartão de vacinação** do Rex, aplicar uma vacina com data de 400 dias atrás e reforço anual | O cartão mostra a vacina como **vencida** | |
| V6 | Veterinário | Aplicar a mesma vacina com a data de hoje | O cartão passa a **em dia**; o histórico mantém as duas aplicações | |
| V7 | Veterinário | Anular a aplicação de hoje | O status volta a **vencida**: vale a última aplicação válida | |
| V8 | Admin | Abrir o **Painel** | O quadro de vacinas mostra o Rex com a vacina vencida; o alerta leva ao cartão dele | |
| V9 | Veterinário | Abrir **Início** | Os pets em tratamento e os mesmos alertas de vacina | |

## 5. Apadrinhamento, doações e gastos (evolução 2)

| # | Perfil | Passos | Resultado esperado | Resultado |
|---|---|---|---|---|
| P1 | Voluntário | Cadastrar um padrinho e, em **Apadrinhamentos**, apadrinhar o Rex com **Valor por mês** R$ 50,00 e início no mês passado | Aparece como ativo | |
| P2 | Voluntário | Apadrinhar o Rex de novo com o mesmo padrinho | Recusado: já existe um ativo | |
| P3 | Veterinário | Abrir a ficha do Rex | Vê "1 padrinho ativo", **sem** o nome | |
| P4 | Voluntário | Em **Doações**, registrar uma doação de R$ 30,00 desse padrinho | O campo **Para qual pet** sugere o Rex sozinho | |
| P5 | Voluntário | Registrar uma doação com data de amanhã | Recusado: data no futuro | |
| P6 | Voluntário | Em **Gastos**, registrar R$ 120,50 em "Veterinário e medicamentos" com o Rex, e R$ 80,00 em "Alimentação" sem pet | Os dois aparecem na lista do mês | |
| P7 | Voluntário | Procurar como estornar o gasto | Não há botão: só o admin estorna | |
| P8 | Admin | Estornar o gasto de R$ 120,50 com **Motivo do estorno** | O original fica marcado como estornado; o estorno aparece logo abaixo, negativo, com motivo e data de hoje | |
| P9 | Admin | Tentar estornar o mesmo gasto de novo | Não há como: cada lançamento é estornado uma vez | |
| P10 | Admin | Registrar uma doação avulsa de R$ 15,00 (**Nome do doador** preenchido) e estorná-la | Mesmo comportamento de P8 | |
| P11 | Admin | Abrir o **Painel** | "Recebido este mês" desconta o estorno de P10: soma R$ 30,00 das doações deste roteiro, e não R$ 45,00 | |

## 6. Contribuições: esperado × recebido (H10)

| # | Perfil | Passos | Resultado esperado | Resultado |
|---|---|---|---|---|
| E1 | Voluntário | Abrir **Contribuições** | O padrinho de P1 aparece com os 12 meses, do mais recente para o mais antigo | |
| E2 | Voluntário | Conferir o mês passado | "R$ 0,00 de R$ 50,00", vermelho (**sem doação**), e "1 mês pendente" ao lado do nome | |
| E3 | Voluntário | Conferir o mês atual | "R$ 30,00 de R$ 50,00", **em andamento**: o mês ainda não acabou, então não conta como pendência | |
| E4 | Voluntário | Marcar **Só quem tem pendência** | Só os padrinhos com mês fechado parcial ou sem doação | |
| E5 | Voluntário | Conferir um mês antes do início do apadrinhamento | Traço (sem compromisso) | |

## 7. Portal público de prestação de contas (H11)

| # | Perfil | Passos | Resultado esperado | Resultado |
|---|---|---|---|---|
| T1 | Sem login | Abrir `/transparencia` | Saldo acumulado, arrecadado e gasto em 12 meses, tabela mês a mês com o mês atual "em andamento" | |
| T2 | Sem login | Em **Para onde foi o dinheiro**, escolher o mês atual | Alimentação R$ 80,00 e Veterinário e medicamentos R$ 0,00: o gasto de P6 e o estorno de P8 caíram no mesmo mês | |
| T3 | Sem login | Ver **Por pet** | O Rex, com R$ 30,00 arrecadados para ele e R$ 0,00 gastos | |
| T4 | Sem login | Procurar na página o nome do padrinho, o nome de um doador avulso ou a descrição de um gasto | Nada disso aparece | |
| T5 | Veterinário | Clicar em **Prestação de contas** no menu | O mesmo portal, com o botão "Voltar ao painel" | |
| T6 | Sem login | Na tela de login, clicar em "Veja a prestação de contas" | Abre o portal | |

## 8. Celular

| # | Perfil | Passos | Resultado esperado | Resultado |
|---|---|---|---|---|
| M1 | Sem login | Abrir o portal num celular | Sem rolagem para o lado na página; as tabelas rolam dentro da própria caixa | |
| M2 | Voluntário | Abrir **Contribuições** num celular | O nome do padrinho fica fixo enquanto os meses rolam | |

---

## Registro da execução

| Data | Quem executou | Versão (commit) | Casos OK | Casos com falha | Observações |
|---|---|---|---|---|---|
| 26/10/2026 | Lucas, execução preliminar num clone limpo | `5b44396` | 50 de 52 | 0 | 40 casos de regra conferidos pela API e 10 só pela tela. A4 e M2 não rodaram no clone; foram conferidos na verificação dos PRs. A execução corrigiu o próprio roteiro: T2 e T3 esperavam valor negativo, mas gasto e estorno do mesmo mês somam zero |
| | Kaua (QA) | | | | |

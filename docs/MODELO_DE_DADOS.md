# Modelo de dados da PetMeet

```mermaid
erDiagram
    USUARIOS ||--o{ PROCESSOS_ADOCAO : "responsavel"
    USUARIOS ||--o{ LOGS_AUDITORIA : "autor"
    PETS ||--o{ PROCESSOS_ADOCAO : "e adotado em"
    PETS ||--o{ APADRINHAMENTOS : "e apadrinhado em"
    ADOTANTES ||--o{ PROCESSOS_ADOCAO : "solicita"
    PADRINHOS ||--o{ APADRINHAMENTOS : "apadrinha"
    PADRINHOS ||--o{ DOACOES : "contribui com"

    USUARIOS {
        int id PK
        string nome
        string email
        string senha_hash
        enum perfil "admin | voluntario"
        bool ativo
    }
    PETS {
        int id PK
        string nome
        enum especie "cachorro | gato | outro"
        int idade
        date data_resgate
        enum status_saude "saudavel | em_tratamento_medico | em_recuperacao"
        string doenca_atual "obrigatorio se em_tratamento_medico"
        enum situacao_adocao "disponivel | em_processo_adocao | adotado"
        string foto_url
    }
    ADOTANTES {
        int id PK
        string nome
        string cpf UK
        string email
        string telefone
        string endereco
    }
    PADRINHOS {
        int id PK
        string nome
        string cpf UK
        string email
        string telefone
    }
    APADRINHAMENTOS {
        int id PK
        int padrinho_id FK
        int pet_id FK
        enum frequencia "pontual | recorrente"
        bool ativo
        date data_inicio
    }
    PROCESSOS_ADOCAO {
        int id PK
        int pet_id FK
        int adotante_id FK
        int responsavel_id FK
        enum status "em_analise | aprovado | finalizado | cancelado"
        bool acompanhamento_medico_em_dia
    }
    DOACOES {
        int id PK
        int padrinho_id FK "nulo se doador avulso"
        string doador_nome "nulo se padrinho cadastrado"
        decimal valor "CHECK > 0"
        date data
        enum tipo "pontual | recorrente"
    }
    LOGS_AUDITORIA {
        int id PK
        int usuario_id FK
        string entidade
        int entidade_id
        string acao
        json dados_antigos
        json dados_novos
    }
```

## Constraints e indices relevantes (RNF07)

| Tabela | Constraint/Indice | Motivo |
|---|---|---|
| `usuarios.email` | UNIQUE + indice | login por email precisa ser rapido e sem duplicatas |
| `adotantes.cpf` / `padrinhos.cpf` | UNIQUE + indice | evita cadastro duplicado da mesma pessoa |
| `pets.situacao_adocao` / `pets.status_saude` | indice | filtros de listagem mais usados (RF05) |
| `apadrinhamentos (padrinho_id, pet_id)` | UNIQUE | mesmo padrinho nao apadrinha o mesmo pet duas vezes |
| `processos_adocao (pet_id) WHERE status='finalizado'` | UNIQUE parcial | **RN02/RF17**: um pet, no máximo, um processo finalizado |
| `doacoes.valor` | CHECK `valor > 0` | **RN05**, reforçada tambem no schema Pydantic |
| `doacoes.data` | indice | consultas por período (RF13) |

## Por que `doenca_atual` e `acompanhamento_medico_em_dia` existem

Essas duas colunas sustentam diretamente a regra crítica RN01/RF16:

- `Pet.doenca_atual` — obrigatório sempre que `status_saude` for
  `em_tratamento_medico` (validado no schema Pydantic e reforçado no serviço).
  É o "identificar qual doença está sendo tratada" citado no RF16.
- `ProcessoAdocao.acompanhamento_medico_em_dia` — **histórico**. Na versão
  recebida, marcar o acompanhamento em dia liberava a finalização de um pet em
  tratamento. Com a decisão D1 a regra passou a ser literal — pet em tratamento
  não finaliza, sem exceção — e o campo deixou de ser lido. A coluna fica para
  não apagar o registro dos processos finalizados antes da mudança.

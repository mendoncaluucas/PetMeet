/**
 * Espelho dos contratos Pydantic do backend (app/esquemas/*.py).
 * Se um schema mudar la, mude aqui tambem - e o unico ponto de acoplamento.
 */

export type PerfilUsuario = 'admin' | 'voluntario' | 'veterinario'
export type EspeciePet = 'cachorro' | 'gato' | 'outro'
export type StatusSaudePet = 'saudavel' | 'em_tratamento_medico' | 'em_recuperacao'
export type SituacaoAdocaoPet = 'disponivel' | 'em_processo_adocao' | 'adotado'
export type StatusProcessoAdocao = 'em_analise' | 'aprovado' | 'finalizado' | 'cancelado'
export type FrequenciaContribuicao = 'pontual' | 'recorrente'

export interface PaginaResposta<T> {
  itens: T[]
  total: number
  pagina: number
  tamanho_pagina: number
}

export interface TokenResposta {
  access_token: string
  token_type: string
}

export interface Pet {
  id: number
  nome: string
  especie: EspeciePet
  idade: number
  data_resgate: string
  status_saude: StatusSaudePet
  doenca_atual: string | null
  situacao_adocao: SituacaoAdocaoPet
  foto_url: string | null
  criado_em: string
  atualizado_em: string
}

export interface PetCriar {
  nome: string
  especie: EspeciePet
  idade: number
  data_resgate: string
  status_saude: StatusSaudePet
  doenca_atual?: string | null
}

export interface PetAtualizar {
  nome?: string
  especie?: EspeciePet
  idade?: number
  data_resgate?: string
}

export interface PetAtualizarStatusSaude {
  status_saude: StatusSaudePet
  doenca_atual?: string | null
}

export interface Adotante {
  id: number
  nome: string
  cpf: string
  email: string
  telefone: string
  endereco: string
  /** Inativo: fora das listagens e sem processo novo. */
  ativo: boolean
  criado_em: string
}

export interface AdotanteCriar {
  nome: string
  cpf: string
  email: string
  telefone: string
  endereco: string
}

export interface Padrinho {
  id: number
  nome: string
  cpf: string
  email: string
  telefone: string
  criado_em: string
}

export interface PadrinhoCriar {
  nome: string
  cpf: string
  email: string
  telefone: string
}

export interface ProcessoAdocao {
  id: number
  pet_id: number
  adotante_id: number
  responsavel_id: number | null
  status: StatusProcessoAdocao
  acompanhamento_medico_em_dia: boolean
  criado_em: string
  atualizado_em: string
}

export interface ProcessoAdocaoCriar {
  pet_id: number
  adotante_id: number
}

export interface ProcessoAdocaoAtualizarStatus {
  status: StatusProcessoAdocao
}

export interface Doacao {
  id: number
  padrinho_id: number | null
  /** destino (H8); null = doacao geral da ONG */
  pet_id: number | null
  doador_nome: string | null
  valor: string
  data: string
  tipo: FrequenciaContribuicao
  registrado_por_nome: string | null
  /** preenchido quando esta linha e um estorno (valor negativo) */
  estorno_de_id: number | null
  motivo_estorno: string | null
  /** preenchido na doacao que ja foi estornada: a data do estorno */
  estornado_em: string | null
  criado_em: string
}

export interface DoacaoCriar {
  padrinho_id?: number | null
  pet_id?: number | null
  doador_nome?: string | null
  valor: number
  data: string
  tipo: FrequenciaContribuicao
}

export interface Usuario {
  id: number
  nome: string
  email: string
  perfil: PerfilUsuario
  ativo: boolean
  criado_em: string
}

export interface UsuarioCriar {
  nome: string
  email: string
  senha: string
  perfil: PerfilUsuario
}

/* --- Painel --------------------------------------------------------------- */

export interface PetResumido {
  id: number
  nome: string
  status_saude: StatusSaudePet
  doenca_atual: string | null
  data_resgate: string
}

export interface ProcessoResumido {
  id: number
  status: StatusProcessoAdocao
  pet_id: number
  pet_nome: string
  pet_status_saude: StatusSaudePet
  adotante_id: number
  adotante_nome: string
}

/** GET /painel/resumo: contagens e total do mes vem do banco inteiro, no fuso de Brasilia. */
export interface ResumoPainel {
  pets_total: number
  pets_disponiveis: number
  pets_em_tratamento: number
  processos_em_andamento: number
  processos_aguardando_finalizacao: number
  /** "AAAA-MM" */
  mes_de_referencia: string
  /** Decimal serializado como texto, como em Doacao.valor */
  doacoes_do_mes_total: string
  doacoes_do_mes_quantidade: number
  em_tratamento: PetResumido[]
  em_andamento: ProcessoResumido[]
  esperando_ha_mais_tempo: PetResumido[]
}

/** Ficha clinica (app/esquemas/atendimento_clinico.py). O autor vem do login. */
export interface Atendimento {
  id: number
  pet_id: number
  data_atendimento: string
  anamnese: string
  diagnostico: string | null
  conduta: string | null
  veterinario_id: number
  veterinario_nome: string
  criado_em: string
  anulado_em: string | null
  anulado_por_nome: string | null
  motivo_anulacao: string | null
}

export interface AtendimentoCriar {
  data_atendimento: string
  anamnese: string
  diagnostico?: string | null
  conduta?: string | null
}

/** Catalogo e cartao de vacinacao (app/esquemas/vacina.py). */
export type StatusVacina = 'em_dia' | 'vencendo' | 'vencida' | 'sem_reforco'

export interface Vacina {
  id: number
  nome: string
  /** null = qualquer especie */
  especie: EspeciePet | null
  intervalo_reforco_dias: number | null
  ativa: boolean
}

export interface VacinaCriar {
  nome: string
  especie: EspeciePet | null
  intervalo_reforco_dias: number | null
}

/** A especie nao muda depois de criada; null no intervalo tira a sugestao de reforco. */
export interface VacinaAtualizar {
  nome?: string
  intervalo_reforco_dias?: number | null
  ativa?: boolean
}

export interface AplicacaoVacina {
  id: number
  pet_id: number
  vacina_id: number
  vacina_nome: string
  data_aplicacao: string
  proxima_dose: string | null
  lote: string | null
  observacao: string | null
  veterinario_id: number
  veterinario_nome: string
  criado_em: string
  anulado_em: string | null
  anulado_por_nome: string | null
  motivo_anulacao: string | null
}

export interface AplicacaoCriar {
  vacina_id: number
  data_aplicacao: string
  proxima_dose: string | null
  lote: string | null
  observacao: string | null
}

export interface SituacaoVacina {
  vacina_id: number
  vacina_nome: string
  vacina_ativa: boolean
  ultima_aplicacao: string
  proxima_dose: string | null
  status: StatusVacina
  /** negativo = dias de atraso; null = sem reforco previsto */
  dias_para_vencer: number | null
}

export interface CartaoVacinacao {
  pet_id: number
  /** o dia (Brasilia) que a API usou no calculo */
  hoje: string
  situacao: SituacaoVacina[]
  historico: AplicacaoVacina[]
}

/** Alertas de vencimento (H6): so vencidas e vencendo, das mais atrasadas primeiro. */
export interface AlertaVacina {
  pet_id: number
  pet_nome: string
  vacina_id: number
  vacina_nome: string
  proxima_dose: string
  status: StatusVacina
  /** negativo = dias de atraso */
  dias_para_vencer: number
}

export interface AlertasVacina {
  hoje: string
  /** contam todos os alertas, nao so os da lista */
  total_vencidas: number
  total_vencendo: number
  itens: AlertaVacina[]
}

/** Apadrinhamento mensal (H7, app/esquemas/apadrinhamento.py). Ativo enquanto sem data_fim. */
export interface Apadrinhamento {
  id: number
  padrinho_id: number
  padrinho_nome: string
  pet_id: number
  pet_nome: string
  valor_mensal: string
  data_inicio: string
  data_fim: string | null
  ativo: boolean
  criado_em: string
}

export interface ApadrinhamentoCriar {
  padrinho_id: number
  pet_id: number
  valor_mensal: number
  data_inicio: string
}

/** O que qualquer perfil ve na ficha do pet: so a contagem. */
export interface PadrinhosDoPet {
  pet_id: number
  ativos: number
}

/** Gastos e estornos (H9, app/esquemas/gasto.py). */
export type CategoriaGasto =
  | 'alimentacao'
  | 'veterinario_medicamentos'
  | 'vacinas'
  | 'higiene_limpeza'
  | 'estrutura_manutencao'
  | 'transporte'
  | 'outros'

export interface Gasto {
  id: number
  /** negativo quando e um estorno */
  valor: string
  data: string
  categoria: CategoriaGasto
  descricao: string
  pet_id: number | null
  pet_nome: string | null
  registrado_por_nome: string
  estorno_de_id: number | null
  motivo_estorno: string | null
  estornado_em: string | null
  criado_em: string
}

export interface GastoCriar {
  valor: number
  data: string
  categoria: CategoriaGasto
  descricao: string
  pet_id: number | null
}

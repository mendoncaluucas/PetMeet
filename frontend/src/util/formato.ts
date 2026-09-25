/**
 * Vocabulario da interface e formatacao.
 *
 * O backend guarda os enums em minusculo e sem acento; aqui eles viram as
 * palavras que a equipe da ONG usa. Um estado tem sempre o mesmo nome em
 * qualquer tela - e assim que alguem aprende a se virar no sistema.
 */

import type {
  EspeciePet,
  FrequenciaContribuicao,
  PerfilUsuario,
  SituacaoAdocaoPet,
  StatusProcessoAdocao,
  StatusSaudePet,
} from '../api/tipos'

export type Tom = 'jade' | 'alerta' | 'ambar' | 'indigo' | 'neutro'

export const ESPECIES: Record<EspeciePet, string> = {
  cachorro: 'Cachorro',
  gato: 'Gato',
  outro: 'Outro',
}

export const STATUS_SAUDE: Record<StatusSaudePet, string> = {
  saudavel: 'Saudável',
  em_tratamento_medico: 'Em tratamento médico',
  em_recuperacao: 'Em recuperação',
}

/** Rotulos curtos: eles vivem dentro de selos, ao lado do estado de saude. */
export const SITUACOES_ADOCAO: Record<SituacaoAdocaoPet, string> = {
  disponivel: 'Disponível',
  em_processo_adocao: 'Em processo',
  adotado: 'Adotado',
}

export const STATUS_PROCESSO: Record<StatusProcessoAdocao, string> = {
  em_analise: 'Em análise',
  aprovado: 'Aprovado',
  finalizado: 'Finalizado',
  cancelado: 'Cancelado',
}

export const TIPOS_DOACAO: Record<FrequenciaContribuicao, string> = {
  pontual: 'Pontual',
  recorrente: 'Recorrente',
}

export const PERFIS: Record<PerfilUsuario, string> = {
  admin: 'Administrador',
  voluntario: 'Voluntário',
}

export const TOM_SAUDE: Record<StatusSaudePet, Tom> = {
  saudavel: 'jade',
  em_tratamento_medico: 'alerta',
  em_recuperacao: 'ambar',
}

export const TOM_SITUACAO: Record<SituacaoAdocaoPet, Tom> = {
  disponivel: 'jade',
  em_processo_adocao: 'ambar',
  adotado: 'indigo',
}

export const TOM_PROCESSO: Record<StatusProcessoAdocao, Tom> = {
  em_analise: 'ambar',
  aprovado: 'jade',
  finalizado: 'indigo',
  cancelado: 'neutro',
}

/** Transicoes que fazem sentido a partir de cada status (RN03/RN04). */
export const PROXIMOS_STATUS: Record<StatusProcessoAdocao, StatusProcessoAdocao[]> = {
  em_analise: ['aprovado', 'cancelado'],
  aprovado: ['finalizado', 'cancelado'],
  finalizado: [],
  cancelado: [],
}

/**
 * Datas vindas da API como "2025-01-10" nao podem passar por new Date(): o
 * navegador as trata como UTC e, no fuso do Brasil, elas voltam um dia.
 */
export function formatarData(iso: string | null | undefined): string {
  if (!iso) return '—'
  const soData = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (soData) {
    const [, ano, mes, dia] = soData
    return `${dia}/${mes}/${ano}`
  }
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return '—'
  return data.toLocaleDateString('pt-BR')
}

export function formatarDataHora(iso: string | null | undefined): string {
  if (!iso) return '—'
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return '—'
  return data.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatarMoeda(valor: string | number): string {
  const numero = typeof valor === 'string' ? Number(valor) : valor
  if (!Number.isFinite(numero)) return '—'
  return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export function formatarCpf(cpf: string): string {
  const digitos = cpf.replace(/\D/g, '')
  if (digitos.length !== 11) return cpf
  return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6, 9)}-${digitos.slice(9)}`
}

/**
 * Mesma conta de app/esquemas/comuns.py::cpf_valido: confere os dois digitos
 * verificadores e recusa sequencias repetidas. Recebe so os digitos.
 */
export function cpfValido(digitos: string): boolean {
  if (!/^\d{11}$/.test(digitos) || /^(\d)\1{10}$/.test(digitos)) return false
  for (const tamanho of [9, 10]) {
    let soma = 0
    for (let i = 0; i < tamanho; i++) soma += Number(digitos[i]) * (tamanho + 1 - i)
    if (((soma * 10) % 11) % 10 !== Number(digitos[tamanho])) return false
  }
  return true
}

/**
 * CPF oculto por padrao (RN07/RNF03/RNF04): a tela mostra so o suficiente para
 * conferir de qual pessoa se trata, e o numero inteiro aparece sob pedido.
 */
export function mascararCpf(cpf: string): string {
  const digitos = cpf.replace(/\D/g, '')
  if (digitos.length !== 11) return '•••'
  return `•••.•••.•••-${digitos.slice(9)}`
}

export function formatarTelefone(telefone: string): string {
  const digitos = telefone.replace(/\D/g, '')
  if (digitos.length === 11) {
    return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 7)}-${digitos.slice(7)}`
  }
  if (digitos.length === 10) {
    return `(${digitos.slice(0, 2)}) ${digitos.slice(2, 6)}-${digitos.slice(6)}`
  }
  return telefone
}

export function idadeEmTexto(idade: number): string {
  if (idade === 0) return 'menos de 1 ano'
  return idade === 1 ? '1 ano' : `${idade} anos`
}

/** Quanto tempo o animal esta sob cuidado da ONG - usado na ficha. */
export function tempoNoAbrigo(dataResgate: string): string {
  const partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dataResgate)
  if (!partes) return ''
  const resgate = new Date(Number(partes[1]), Number(partes[2]) - 1, Number(partes[3]))
  const hoje = new Date()
  const dias = Math.floor((hoje.getTime() - resgate.getTime()) / 86_400_000)
  if (dias < 0) return ''
  if (dias === 0) return 'resgatado hoje'
  if (dias === 1) return 'há 1 dia no abrigo'
  if (dias < 60) return `há ${dias} dias no abrigo`
  const meses = Math.floor(dias / 30)
  if (meses < 24) return `há ${meses} meses no abrigo`
  return `há ${Math.floor(meses / 12)} anos no abrigo`
}

export function dataDeHoje(): string {
  const hoje = new Date()
  const mes = String(hoje.getMonth() + 1).padStart(2, '0')
  const dia = String(hoje.getDate()).padStart(2, '0')
  return `${hoje.getFullYear()}-${mes}-${dia}`
}

/** Plural sem malabarismo: contagem(1, 'pet', 'pets') -> "1 pet". */
export function contagem(quantidade: number, singular: string, plural: string): string {
  return `${quantidade} ${quantidade === 1 ? singular : plural}`
}

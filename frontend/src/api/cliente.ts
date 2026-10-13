/**
 * Cliente HTTP da API PetMeet.
 *
 * O backend padroniza erros de negocio em {"detalhe": "..."} (handler global
 * de app/core/excecoes.py) e erros de validacao do FastAPI em
 * {"detail": [...]}. As duas formas viram a mesma ErroApi aqui, para que a
 * tela precise lidar com um unico formato.
 */

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') || '/api'

const CHAVE_TOKEN = 'petmeet.token'

export class ErroApi extends Error {
  readonly status: number
  /** Erros de validacao por campo, quando o FastAPI devolve 422 detalhado. */
  readonly porCampo: Record<string, string>

  constructor(status: number, mensagem: string, porCampo: Record<string, string> = {}) {
    super(mensagem)
    this.name = 'ErroApi'
    this.status = status
    this.porCampo = porCampo
  }

  /** Conflito de concorrencia: outro processo finalizou o mesmo pet antes (RN02). */
  get ehConflito(): boolean {
    return this.status === 409
  }

  /** Regra de negocio recusou a operacao (RN01-RN08). */
  get ehRegraNegocio(): boolean {
    return this.status === 422
  }

  get ehSemPermissao(): boolean {
    return this.status === 403
  }

  /**
   * Mensagem pronta para a tela. Erros de negocio do backend ja vem escritos
   * para uma pessoa ler; os de infraestrutura nao, e ganham um texto que diz
   * o que aconteceu e o que fazer.
   */
  mensagemDeTela(): string {
    if (this.status === 0) return this.message
    if (this.status === 403) {
      return 'Seu perfil não tem permissão para esta ação. Peça a um administrador da ONG.'
    }
    if (this.status === 404) return 'Este registro não existe mais. Atualize a página.'
    if (this.status >= 500) {
      return 'A API falhou ao processar o pedido. Tente de novo em instantes.'
    }
    return this.message
  }
}

export function lerToken(): string | null {
  try {
    return localStorage.getItem(CHAVE_TOKEN)
  } catch {
    return null
  }
}

export function gravarToken(token: string): void {
  try {
    localStorage.setItem(CHAVE_TOKEN, token)
  } catch {
    /* navegador sem storage: a sessao dura enquanto a aba estiver aberta */
  }
}

export function apagarToken(): void {
  try {
    localStorage.removeItem(CHAVE_TOKEN)
  } catch {
    /* nada a fazer */
  }
}

/** Avisa o app inteiro que o token caiu, para voltar ao login sem recarregar. */
export const EVENTO_SESSAO_EXPIRADA = 'petmeet:sessao-expirada'

function extrairMensagem(corpo: unknown, status: number): [string, Record<string, string>] {
  const padrao = `Nao foi possivel completar a operacao (erro ${status}).`
  if (typeof corpo !== 'object' || corpo === null) return [padrao, {}]

  const dados = corpo as Record<string, unknown>

  if (typeof dados.detalhe === 'string') return [dados.detalhe, {}]

  const detail = dados.detail
  if (typeof detail === 'string') return [detail, {}]

  if (Array.isArray(detail)) {
    const porCampo: Record<string, string> = {}
    const mensagens: string[] = []
    for (const item of detail) {
      if (typeof item !== 'object' || item === null) continue
      const erro = item as { loc?: unknown[]; msg?: string }
      const msg = erro.msg ?? 'valor invalido'
      const campo = Array.isArray(erro.loc) ? String(erro.loc[erro.loc.length - 1]) : ''
      if (campo && campo !== 'body') porCampo[campo] = msg
      mensagens.push(campo ? `${campo}: ${msg}` : msg)
    }
    return [mensagens.join(' | ') || padrao, porCampo]
  }

  return [padrao, {}]
}

interface Opcoes {
  metodo?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  corpo?: unknown
  /** Envia como form-urlencoded (usado so pelo /auth/login, padrao OAuth2). */
  formulario?: Record<string, string>
  /** Envia um arquivo em multipart (upload de foto do pet). */
  arquivo?: FormData
  /** Rotas publicas nao mandam Authorization. */
  semAutenticacao?: boolean
}

export async function requisitar<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const cabecalhos: Record<string, string> = { Accept: 'application/json' }
  let corpo: BodyInit | undefined

  if (opcoes.formulario) {
    cabecalhos['Content-Type'] = 'application/x-www-form-urlencoded'
    corpo = new URLSearchParams(opcoes.formulario).toString()
  } else if (opcoes.arquivo) {
    // Content-Type fica a cargo do browser: ele precisa gerar o boundary.
    corpo = opcoes.arquivo
  } else if (opcoes.corpo !== undefined) {
    cabecalhos['Content-Type'] = 'application/json'
    corpo = JSON.stringify(opcoes.corpo)
  }

  if (!opcoes.semAutenticacao) {
    const token = lerToken()
    if (token) cabecalhos.Authorization = `Bearer ${token}`
  }

  let resposta: Response
  try {
    resposta = await fetch(`${BASE}${caminho}`, {
      method: opcoes.metodo ?? 'GET',
      headers: cabecalhos,
      body: corpo,
    })
  } catch {
    throw new ErroApi(0, 'A API nao respondeu. Confira se o servidor esta no ar em localhost:8000.')
  }

  if (resposta.status === 204) return undefined as T

  // A resposta pode ser cortada no meio da leitura (rede caiu, aba suspensa). A essa altura
  // o servidor ja pode ter gravado a operacao: repetir as cegas daria erro ou duplicaria.
  let texto: string
  try {
    texto = await resposta.text()
  } catch {
    throw new ErroApi(
      0,
      'A resposta da API foi interrompida. Atualize a página para ver se a operação foi gravada.',
    )
  }
  let dados: unknown = null
  if (texto) {
    try {
      dados = JSON.parse(texto)
    } catch {
      dados = null
    }
  }

  if (!resposta.ok) {
    if (resposta.status === 401 && !opcoes.semAutenticacao) {
      apagarToken()
      window.dispatchEvent(new Event(EVENTO_SESSAO_EXPIRADA))
    }
    const [mensagem, porCampo] = extrairMensagem(dados, resposta.status)
    throw new ErroApi(resposta.status, mensagem, porCampo)
  }

  return dados as T
}

/** Monta a query string ignorando filtros nao preenchidos. */
export function consulta(parametros: Record<string, string | number | undefined | null>): string {
  const busca = new URLSearchParams()
  for (const [chave, valor] of Object.entries(parametros)) {
    if (valor === undefined || valor === null || valor === '') continue
    busca.set(chave, String(valor))
  }
  const texto = busca.toString()
  return texto ? `?${texto}` : ''
}

/** A API devolve foto_url relativa (/uploads/arquivo.jpg); em producao precisa do host. */
export function urlDeMidia(caminho: string | null): string | null {
  if (!caminho) return null
  if (/^https?:\/\//.test(caminho)) return caminho
  const base = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '')
  return base ? `${base}${caminho}` : caminho
}

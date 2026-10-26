/**
 * Estorno de lancamento (fase 3, H9, D13), igual para gasto e doacao. Lancamento nao se
 * edita nem se apaga: o admin estorna informando o motivo, e o estorno vira outra linha,
 * negativa, com a data do dia -- o mes do original nao muda.
 */

import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErroApi } from '../api/cliente'
import { Campo } from './Campos'
import { Selo } from './Interface'
import { formatarData } from '../util/formato'

interface Situacao {
  estorno_de_id: number | null
  motivo_estorno: string | null
  estornado_em: string | null
}

/** O selo e a explicacao que vao junto da descricao do lancamento. */
export function SituacaoDoLancamento({ lancamento }: { lancamento: Situacao }) {
  if (lancamento.estorno_de_id !== null) {
    return (
      <span className="lancamento-situacao">
        <Selo tom="neutro">Estorno</Selo> {lancamento.motivo_estorno}
      </span>
    )
  }
  if (lancamento.estornado_em !== null) {
    return (
      <span className="lancamento-situacao">
        <Selo tom="ambar">Estornado em {formatarData(lancamento.estornado_em)}</Selo>
      </span>
    )
  }
  return null
}

interface EstornarProps {
  lancamento: Situacao
  /** Grava o estorno; a tela recarrega depois. */
  estornar: (motivo: string) => Promise<unknown>
  aoEstornar: () => void
  aoFalhar: (texto: string) => void
}

/** Botao e formulario do estorno. So aparece em lancamento comum, ainda nao estornado. */
export function EstornarLancamento({ lancamento, estornar, aoEstornar, aoFalhar }: EstornarProps) {
  const [aberto, setAberto] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [erroMotivo, setErroMotivo] = useState<string | undefined>()
  const [salvando, setSalvando] = useState(false)

  if (lancamento.estorno_de_id !== null || lancamento.estornado_em !== null) return null

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (!motivo.trim()) {
      setErroMotivo('Informe por que este lançamento está sendo estornado.')
      return
    }
    setSalvando(true)
    try {
      await estornar(motivo.trim())
      setAberto(false)
      aoEstornar()
    } catch (problema) {
      aoFalhar(
        problema instanceof ErroApi ? problema.mensagemDeTela() : 'Não foi possível estornar.',
      )
    } finally {
      setSalvando(false)
    }
  }

  if (!aberto) {
    return (
      <button type="button" className="botao" data-tipo="texto" onClick={() => setAberto(true)}>
        Estornar
      </button>
    )
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <Campo
        rotulo="Motivo do estorno"
        required
        maxLength={500}
        value={motivo}
        erro={erroMotivo}
        dica="O lançamento não é apagado: um estorno negativo entra com a data de hoje."
        onChange={(e) => setMotivo(e.target.value)}
      />
      <div className="acoes">
        <button type="submit" className="botao" data-tipo="perigo" disabled={salvando}>
          {salvando ? 'Estornando…' : 'Confirmar estorno'}
        </button>
        <button type="button" className="botao" data-tipo="texto" onClick={() => setAberto(false)}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

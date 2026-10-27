/**
 * Ficha clinica do pet (fase 2, H3). A equipe le; so o veterinario registra e anula
 * (D7). Atendimento nao se edita nem se apaga: anulado, continua na ficha com o motivo (D8).
 */

import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErroApi } from '../api/cliente'
import { atendimentos } from '../api/recursos'
import type { Atendimento } from '../api/tipos'
import { Campo, CampoTexto } from './Campos'
import { Aviso, Carregando, Paginacao, Selo } from './Interface'
import { dataDeHoje, formatarData, formatarDataHora } from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

const TAMANHO_PAGINA = 10

interface Props {
  petId: number
  podeRegistrar: boolean
}

export function FichaClinica({ petId, podeRegistrar }: Props) {
  const [pagina, setPagina] = useState(1)
  const [registrando, setRegistrando] = useState(false)
  const [mensagem, setMensagem] = useState<{ tom: 'sucesso' | 'erro'; texto: string } | null>(null)
  const { dados, carregando, erro, recarregar } = useRequisicao(
    () => atendimentos.listar(petId, pagina, TAMANHO_PAGINA),
    [petId, pagina],
  )

  function aposRegistrar() {
    setRegistrando(false)
    setMensagem({ tom: 'sucesso', texto: 'Atendimento registrado.' })
    // O registro novo e o mais recente: volta para a primeira pagina para ele aparecer.
    if (pagina === 1) recarregar()
    else setPagina(1)
  }

  function aposAnular() {
    // Anular nao muda a ordem da ficha: o atendimento fica onde estava.
    setMensagem({ tom: 'sucesso', texto: 'Atendimento anulado. Ele continua na ficha.' })
    recarregar()
  }

  function falhar(problema: unknown, padrao: string) {
    setMensagem({
      tom: 'erro',
      texto: problema instanceof ErroApi ? problema.mensagemDeTela() : padrao,
    })
  }

  return (
    <section className="ficha">
      <div className="ficha-corpo pilha-3">
        <div className="secao-titulo">
          <h2>Ficha clínica</h2>
          {podeRegistrar ? (
            <button
              type="button"
              className="botao"
              data-tipo="texto"
              onClick={() => setRegistrando(!registrando)}
            >
              {registrando ? 'Fechar' : 'Registrar atendimento'}
            </button>
          ) : null}
        </div>

        {mensagem ? <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso> : null}

        {registrando ? (
          <FormularioAtendimento
            petId={petId}
            aoSalvar={aposRegistrar}
            aoFalhar={(problema) => falhar(problema, 'Não foi possível registrar.')}
            aoCancelar={() => setRegistrando(false)}
          />
        ) : null}

        {carregando ? (
          <Carregando texto="Abrindo a ficha clínica…" />
        ) : erro ? (
          <Aviso>{erro}</Aviso>
        ) : !dados || dados.total === 0 ? (
          <p className="texto-fraco">Nenhum atendimento registrado para este pet.</p>
        ) : (
          <>
            <div className="lista-atendimentos">
              {dados.itens.map((atendimento) => (
                <ItemAtendimento
                  key={atendimento.id}
                  atendimento={atendimento}
                  podeAnular={podeRegistrar}
                  aoAnular={aposAnular}
                  aoFalhar={(problema) => falhar(problema, 'Não foi possível anular.')}
                />
              ))}
            </div>
            {dados.total > TAMANHO_PAGINA ? (
              <Paginacao
                pagina={pagina}
                tamanhoPagina={TAMANHO_PAGINA}
                total={dados.total}
                aoMudar={setPagina}
              />
            ) : null}
          </>
        )}
      </div>
    </section>
  )
}

/* --- Um atendimento --------------------------------------------------- */

interface ItemProps {
  atendimento: Atendimento
  podeAnular: boolean
  aoAnular: () => void
  aoFalhar: (problema: unknown) => void
}

function ItemAtendimento({ atendimento, podeAnular, aoAnular, aoFalhar }: ItemProps) {
  const [anulando, setAnulando] = useState(false)
  const anulado = atendimento.anulado_em !== null

  return (
    <article className="atendimento" data-anulado={anulado ? 'sim' : undefined}>
      <header className="atendimento-cabecalho">
        <span>
          <strong>{formatarData(atendimento.data_atendimento)}</strong>
          <span className="texto-fraco"> · {atendimento.veterinario_nome}</span>
        </span>
        {anulado ? (
          <Selo tom="neutro">Anulado</Selo>
        ) : podeAnular && !anulando ? (
          <button
            type="button"
            className="botao"
            data-tipo="texto"
            onClick={() => setAnulando(true)}
          >
            Anular
          </button>
        ) : null}
      </header>

      {anulado ? (
        <p className="atendimento-anulacao">
          Anulado por {atendimento.anulado_por_nome} em {formatarDataHora(atendimento.anulado_em)}:{' '}
          {atendimento.motivo_anulacao}
        </p>
      ) : null}

      <dl className="atendimento-corpo">
        <div>
          <dt>Anamnese</dt>
          <dd>{atendimento.anamnese}</dd>
        </div>
        {atendimento.diagnostico ? (
          <div>
            <dt>Diagnóstico</dt>
            <dd>{atendimento.diagnostico}</dd>
          </div>
        ) : null}
        {atendimento.conduta ? (
          <div>
            <dt>Conduta</dt>
            <dd>{atendimento.conduta}</dd>
          </div>
        ) : null}
      </dl>

      {anulando ? (
        <FormularioAnulacao
          atendimentoId={atendimento.id}
          aoAnular={aoAnular}
          aoFalhar={aoFalhar}
          aoCancelar={() => setAnulando(false)}
        />
      ) : null}
    </article>
  )
}

/* --- Formularios ------------------------------------------------------ */

interface FormAtendimentoProps {
  petId: number
  aoSalvar: () => void
  aoFalhar: (problema: unknown) => void
  aoCancelar: () => void
}

function FormularioAtendimento({ petId, aoSalvar, aoFalhar, aoCancelar }: FormAtendimentoProps) {
  const [data, setData] = useState(dataDeHoje())
  const [anamnese, setAnamnese] = useState('')
  const [diagnostico, setDiagnostico] = useState('')
  const [conduta, setConduta] = useState('')
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({})
  const [salvando, setSalvando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (!anamnese.trim()) {
      setErrosCampo({ anamnese: 'Descreva a anamnese.' })
      return
    }
    setErrosCampo({})
    setSalvando(true)
    try {
      await atendimentos.registrar(petId, {
        data_atendimento: data,
        anamnese: anamnese.trim(),
        diagnostico: diagnostico.trim() || null,
        conduta: conduta.trim() || null,
      })
      aoSalvar()
    } catch (problema) {
      if (problema instanceof ErroApi) setErrosCampo(problema.porCampo)
      aoFalhar(problema)
      setSalvando(false)
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      {/* O max e so ajuda: quem confere "hoje" no fuso de Brasilia e a API. */}
      <Campo
        rotulo="Data do atendimento"
        type="date"
        required
        max={dataDeHoje()}
        value={data}
        erro={errosCampo.data_atendimento}
        onChange={(e) => setData(e.target.value)}
      />
      <CampoTexto
        rotulo="Anamnese"
        required
        maxLength={5000}
        value={anamnese}
        erro={errosCampo.anamnese}
        dica="Histórico e sinais relatados: o que trouxe o pet ao atendimento."
        onChange={(e) => setAnamnese(e.target.value)}
      />
      <CampoTexto
        rotulo="Diagnóstico"
        rows={2}
        maxLength={2000}
        value={diagnostico}
        erro={errosCampo.diagnostico}
        onChange={(e) => setDiagnostico(e.target.value)}
      />
      <CampoTexto
        rotulo="Conduta"
        rows={2}
        maxLength={2000}
        value={conduta}
        erro={errosCampo.conduta}
        onChange={(e) => setConduta(e.target.value)}
      />
      <div className="acoes">
        <button type="submit" className="botao" disabled={salvando}>
          {salvando ? 'Salvando…' : 'Registrar atendimento'}
        </button>
        <button type="button" className="botao" data-tipo="texto" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

interface FormAnulacaoProps {
  atendimentoId: number
  aoAnular: () => void
  aoFalhar: (problema: unknown) => void
  aoCancelar: () => void
}

function FormularioAnulacao({ atendimentoId, aoAnular, aoFalhar, aoCancelar }: FormAnulacaoProps) {
  const [motivo, setMotivo] = useState('')
  const [erroMotivo, setErroMotivo] = useState<string | undefined>()
  const [salvando, setSalvando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (!motivo.trim()) {
      setErroMotivo('Informe por que este atendimento está sendo anulado.')
      return
    }
    setSalvando(true)
    try {
      await atendimentos.anular(atendimentoId, motivo.trim())
      aoAnular()
    } catch (problema) {
      aoFalhar(problema)
      setSalvando(false)
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <Campo
        rotulo="Motivo da anulação"
        required
        maxLength={500}
        value={motivo}
        erro={erroMotivo}
        dica="O atendimento não é apagado: fica na ficha, marcado como anulado, com este motivo."
        onChange={(e) => setMotivo(e.target.value)}
      />
      <div className="acoes">
        <button type="submit" className="botao" data-tipo="perigo" disabled={salvando}>
          {salvando ? 'Anulando…' : 'Anular atendimento'}
        </button>
        <button type="button" className="botao" data-tipo="texto" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

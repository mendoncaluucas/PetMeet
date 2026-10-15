/**
 * Cartao de vacinacao do pet (fase 2, H5). A equipe le; so o veterinario aplica e anula
 * (D7). O status de cada vacina vem pronto da API, calculado pela ultima aplicacao valida.
 */

import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { ErroApi } from '../api/cliente'
import { vacinacao, vacinas } from '../api/recursos'
import type { AplicacaoVacina, EspeciePet, Vacina } from '../api/tipos'
import { Campo, CampoSelecao } from './Campos'
import { Aviso, Carregando, Selo } from './Interface'
import {
  STATUS_VACINA,
  TOM_VACINA,
  dataDeHoje,
  formatarData,
  formatarDataHora,
  prazoDaDose,
  somarDias,
} from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

interface Props {
  petId: number
  especie: EspeciePet
  podeRegistrar: boolean
}

export function CartaoVacinacao({ petId, especie, podeRegistrar }: Props) {
  const [registrando, setRegistrando] = useState(false)
  const [mensagem, setMensagem] = useState<{ tom: 'sucesso' | 'erro'; texto: string } | null>(null)
  const { dados, carregando, erro, recarregar } = useRequisicao(
    () => vacinacao.cartao(petId),
    [petId],
  )

  // O alerta da pagina inicial abre /pets/:id#cartao-vacinacao: rola ate aqui quando o
  // cartao terminar de carregar (antes disso a altura da pagina ainda vai mudar).
  const { hash } = useLocation()
  const carregado = Boolean(dados)
  useEffect(() => {
    if (hash === '#cartao-vacinacao' && carregado) {
      document.getElementById('cartao-vacinacao')?.scrollIntoView({ block: 'start' })
    }
  }, [hash, carregado])

  function concluir(texto: string) {
    setRegistrando(false)
    setMensagem({ tom: 'sucesso', texto })
    recarregar()
  }

  function falhar(problema: unknown, padrao: string) {
    setMensagem({
      tom: 'erro',
      texto: problema instanceof ErroApi ? problema.mensagemDeTela() : padrao,
    })
  }

  return (
    <section className="ficha" id="cartao-vacinacao">
      <div className="ficha-corpo pilha-3">
        <div className="secao-titulo">
          <h2>Cartão de vacinação</h2>
          {podeRegistrar ? (
            <button
              type="button"
              className="botao"
              data-tipo="texto"
              onClick={() => setRegistrando(!registrando)}
            >
              {registrando ? 'Fechar' : 'Registrar vacina'}
            </button>
          ) : null}
        </div>

        {mensagem ? <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso> : null}

        {registrando ? (
          <FormularioAplicacao
            petId={petId}
            especie={especie}
            aoSalvar={(nome) => concluir(`${nome} registrada no cartão.`)}
            aoFalhar={(problema) => falhar(problema, 'Não foi possível registrar.')}
            aoCancelar={() => setRegistrando(false)}
          />
        ) : null}

        {carregando ? (
          <Carregando texto="Abrindo o cartão de vacinação…" />
        ) : erro ? (
          <Aviso>{erro}</Aviso>
        ) : !dados || dados.historico.length === 0 ? (
          <p className="texto-fraco">Nenhuma vacina registrada para este pet.</p>
        ) : (
          <>
            {dados.situacao.length > 0 ? (
              <div className="tabela-envolucro">
                <table className="tabela">
                  <thead>
                    <tr>
                      <th>Vacina</th>
                      <th>Última dose</th>
                      <th>Próxima dose</th>
                      <th>Situação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dados.situacao.map((item) => (
                      <tr key={item.vacina_id}>
                        <td className="principal">
                          {item.vacina_nome}{' '}
                          {item.vacina_ativa ? null : <Selo>Fora do catálogo</Selo>}
                        </td>
                        <td>{formatarData(item.ultima_aplicacao)}</td>
                        <td>
                          {item.proxima_dose ? formatarData(item.proxima_dose) : '—'}
                          {item.dias_para_vencer !== null ? (
                            <span className="contato-linha texto-fraco">
                              {prazoDaDose(item.dias_para_vencer)}
                            </span>
                          ) : null}
                        </td>
                        <td>
                          <Selo tom={TOM_VACINA[item.status]}>{STATUS_VACINA[item.status]}</Selo>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="texto-fraco">Todas as aplicações deste pet foram anuladas.</p>
            )}

            <h3 className="subtitulo-cartao">Histórico</h3>
            <div className="lista-atendimentos">
              {dados.historico.map((aplicacao) => (
                <ItemAplicacao
                  key={aplicacao.id}
                  aplicacao={aplicacao}
                  podeAnular={podeRegistrar}
                  aoAnular={() =>
                    concluir('Aplicação anulada. Ela continua no histórico e deixa de valer.')
                  }
                  aoFalhar={(problema) => falhar(problema, 'Não foi possível anular.')}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  )
}

/* --- Uma aplicacao ---------------------------------------------------- */

interface ItemProps {
  aplicacao: AplicacaoVacina
  podeAnular: boolean
  aoAnular: () => void
  aoFalhar: (problema: unknown) => void
}

function ItemAplicacao({ aplicacao, podeAnular, aoAnular, aoFalhar }: ItemProps) {
  const [anulando, setAnulando] = useState(false)
  const anulada = aplicacao.anulado_em !== null

  return (
    <article className="atendimento" data-anulado={anulada ? 'sim' : undefined}>
      <header className="atendimento-cabecalho">
        <span>
          <strong>{aplicacao.vacina_nome}</strong>
          <span className="texto-fraco">
            {' '}
            · {formatarData(aplicacao.data_aplicacao)} · {aplicacao.veterinario_nome}
          </span>
        </span>
        {anulada ? (
          <Selo tom="neutro">Anulada</Selo>
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

      {anulada ? (
        <p className="atendimento-anulacao">
          Anulada por {aplicacao.anulado_por_nome} em {formatarDataHora(aplicacao.anulado_em)}:{' '}
          {aplicacao.motivo_anulacao}
        </p>
      ) : null}

      <dl className="atendimento-corpo">
        <div>
          <dt>Próxima dose</dt>
          <dd>{aplicacao.proxima_dose ? formatarData(aplicacao.proxima_dose) : 'sem reforço'}</dd>
        </div>
        {aplicacao.lote ? (
          <div>
            <dt>Lote</dt>
            <dd>{aplicacao.lote}</dd>
          </div>
        ) : null}
        {aplicacao.observacao ? (
          <div>
            <dt>Observação</dt>
            <dd>{aplicacao.observacao}</dd>
          </div>
        ) : null}
      </dl>

      {anulando ? (
        <FormularioAnulacao
          aplicacaoId={aplicacao.id}
          aoAnular={aoAnular}
          aoFalhar={aoFalhar}
          aoCancelar={() => setAnulando(false)}
        />
      ) : null}
    </article>
  )
}

/* --- Formularios ------------------------------------------------------ */

interface FormAplicacaoProps {
  petId: number
  especie: EspeciePet
  aoSalvar: (nomeDaVacina: string) => void
  aoFalhar: (problema: unknown) => void
  aoCancelar: () => void
}

function FormularioAplicacao({
  petId,
  especie,
  aoSalvar,
  aoFalhar,
  aoCancelar,
}: FormAplicacaoProps) {
  const catalogo = useRequisicao(() => vacinas.listar(), [])
  const [vacinaId, setVacinaId] = useState('')
  const [data, setData] = useState(dataDeHoje())
  const [proximaDose, setProximaDose] = useState('')
  // Enquanto a pessoa nao mexer na proxima dose, ela acompanha a sugestao do catalogo.
  const [proximaEditada, setProximaEditada] = useState(false)
  const [lote, setLote] = useState('')
  const [observacao, setObservacao] = useState('')
  const [salvando, setSalvando] = useState(false)

  // So as vacinas que servem para este pet: da especie dele ou de qualquer especie.
  const opcoes = (catalogo.dados ?? []).filter(
    (vacina) => vacina.especie === null || vacina.especie === especie,
  )

  function sugerir(vacina: Vacina | undefined, dataAplicacao: string) {
    if (proximaEditada) return
    setProximaDose(
      vacina?.intervalo_reforco_dias && dataAplicacao
        ? somarDias(dataAplicacao, vacina.intervalo_reforco_dias)
        : '',
    )
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    const vacina = opcoes.find((item) => item.id === Number(vacinaId))
    if (!vacina) return
    setSalvando(true)
    try {
      await vacinacao.registrar(petId, {
        vacina_id: vacina.id,
        data_aplicacao: data,
        proxima_dose: proximaDose || null,
        lote: lote.trim() || null,
        observacao: observacao.trim() || null,
      })
      aoSalvar(vacina.nome)
    } catch (problema) {
      aoFalhar(problema)
      setSalvando(false)
    }
  }

  if (catalogo.carregando) return <Carregando texto="Buscando o catálogo…" />
  if (catalogo.erro) return <Aviso>{catalogo.erro}</Aviso>
  if (opcoes.length === 0) {
    return (
      <Aviso tom="atencao">
        Nenhuma vacina ativa do catálogo serve para este pet. Cadastre uma em Vacinas.
      </Aviso>
    )
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <CampoSelecao
        rotulo="Vacina"
        required
        value={vacinaId}
        onChange={(e) => {
          setVacinaId(e.target.value)
          sugerir(
            opcoes.find((item) => item.id === Number(e.target.value)),
            data,
          )
        }}
      >
        <option value="">Escolha a vacina</option>
        {opcoes.map((vacina) => (
          <option key={vacina.id} value={vacina.id}>
            {vacina.nome}
          </option>
        ))}
      </CampoSelecao>
      {/* O max e so ajuda: quem confere "hoje" no fuso de Brasilia e a API. */}
      <Campo
        rotulo="Data da aplicação"
        type="date"
        required
        max={dataDeHoje()}
        value={data}
        onChange={(e) => {
          setData(e.target.value)
          sugerir(
            opcoes.find((item) => item.id === Number(vacinaId)),
            e.target.value,
          )
        }}
      />
      <Campo
        rotulo="Próxima dose"
        type="date"
        min={data ? somarDias(data, 1) : undefined}
        value={proximaDose}
        dica="Sugerida pelo intervalo do catálogo. Pode mudar ou apagar; vazio é sem reforço."
        onChange={(e) => {
          setProximaEditada(true)
          setProximaDose(e.target.value)
        }}
      />
      <Campo rotulo="Lote" maxLength={50} value={lote} onChange={(e) => setLote(e.target.value)} />
      <Campo
        rotulo="Observação"
        maxLength={500}
        value={observacao}
        onChange={(e) => setObservacao(e.target.value)}
      />
      <div className="acoes">
        <button type="submit" className="botao" disabled={salvando}>
          {salvando ? 'Salvando…' : 'Registrar vacina'}
        </button>
        <button type="button" className="botao" data-tipo="texto" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

interface FormAnulacaoProps {
  aplicacaoId: number
  aoAnular: () => void
  aoFalhar: (problema: unknown) => void
  aoCancelar: () => void
}

function FormularioAnulacao({ aplicacaoId, aoAnular, aoFalhar, aoCancelar }: FormAnulacaoProps) {
  const [motivo, setMotivo] = useState('')
  const [erroMotivo, setErroMotivo] = useState<string | undefined>()
  const [salvando, setSalvando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (!motivo.trim()) {
      setErroMotivo('Informe por que esta aplicação está sendo anulada.')
      return
    }
    setSalvando(true)
    try {
      await vacinacao.anular(aplicacaoId, motivo.trim())
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
        dica="A aplicação não é apagada: fica no histórico, marcada como anulada, e deixa de contar na situação da vacina."
        onChange={(e) => setMotivo(e.target.value)}
      />
      <div className="acoes">
        <button type="submit" className="botao" data-tipo="perigo" disabled={salvando}>
          {salvando ? 'Anulando…' : 'Anular aplicação'}
        </button>
        <button type="button" className="botao" data-tipo="texto" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

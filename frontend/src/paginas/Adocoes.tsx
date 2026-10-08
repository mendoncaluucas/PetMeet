import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ErroApi } from '../api/cliente'
import {
  adotantes as apiAdotantes,
  pets as apiPets,
  processos as apiProcessos,
} from '../api/recursos'
import type { Adotante, Pet, ProcessoAdocao, StatusProcessoAdocao } from '../api/tipos'
import { CampoSelecao } from '../componentes/Campos'
import {
  Aviso,
  CabecalhoPagina,
  Carregando,
  EstadoVazio,
  Paginacao,
  Selo,
  Sobreposicao,
} from '../componentes/Interface'
import { PROXIMOS_STATUS, STATUS_PROCESSO, TOM_PROCESSO, formatarData } from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

const TAMANHO_PAGINA = 20

export function Adocoes() {
  const [pagina, setPagina] = useState(1)
  const [abrindo, setAbrindo] = useState(false)
  const [emEdicao, setEmEdicao] = useState<ProcessoAdocao | null>(null)
  const [mensagem, setMensagem] = useState<{ tom: 'sucesso' | 'erro'; texto: string } | null>(null)

  const { dados, carregando, erro, recarregar } = useRequisicao(
    () =>
      Promise.all([
        apiProcessos.listar({ pagina, tamanho_pagina: TAMANHO_PAGINA }),
        apiPets.listar({ tamanho_pagina: 100 }),
        apiAdotantes.listar(1, 100, true), // inclui inativos: dao nome aos processos antigos
      ]),
    [pagina],
  )

  if (carregando) return <Carregando texto="Carregando processos…" />
  if (erro) return <Aviso>{erro}</Aviso>
  if (!dados) return null

  const [lista, listaPets, listaAdotantes] = dados
  const petPorId = new Map(listaPets.itens.map((pet) => [pet.id, pet]))
  const adotantePorId = new Map(listaAdotantes.itens.map((pessoa) => [pessoa.id, pessoa]))
  const petsDisponiveis = listaPets.itens.filter((pet) => pet.situacao_adocao === 'disponivel')

  function concluir(texto: string) {
    setMensagem({ tom: 'sucesso', texto })
    setAbrindo(false)
    setEmEdicao(null)
    recarregar()
  }

  return (
    <>
      <CabecalhoPagina
        titulo="Adoções"
        descricao="Cada processo liga um pet a um adotante e caminha de análise até a finalização."
        acao={
          <button type="button" className="botao" onClick={() => setAbrindo(true)}>
            Abrir processo
          </button>
        }
      />

      {mensagem ? <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso> : null}

      {lista.itens.length === 0 ? (
        <EstadoVazio
          titulo="Nenhum processo de adoção"
          descricao="Quando um adotante escolher um pet disponível, abra o processo aqui para acompanhar cada etapa."
          acao={
            <button type="button" className="botao" onClick={() => setAbrindo(true)}>
              Abrir processo
            </button>
          }
        />
      ) : (
        <>
          <div className="tabela-envolucro">
            <table className="tabela">
              <thead>
                <tr>
                  <th>Pet</th>
                  <th>Adotante</th>
                  <th>Aberto em</th>
                  <th>Estado</th>
                  <th>
                    <span className="so-leitor-tela">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {lista.itens.map((processo) => {
                  const pet = petPorId.get(processo.pet_id)
                  const adotante = adotantePorId.get(processo.adotante_id)
                  const podeAvancar = PROXIMOS_STATUS[processo.status].length > 0

                  return (
                    <tr key={processo.id}>
                      <td className="principal">
                        {pet ? (
                          <Link to={`/pets/${pet.id}`}>{pet.nome}</Link>
                        ) : (
                          `Pet #${processo.pet_id}`
                        )}
                        {pet?.status_saude === 'em_tratamento_medico' ? (
                          <span className="texto-fraco" style={{ display: 'block' }}>
                            em tratamento médico
                          </span>
                        ) : null}
                      </td>
                      <td>{adotante?.nome ?? `Adotante #${processo.adotante_id}`}</td>
                      <td>{formatarData(processo.criado_em)}</td>
                      <td>
                        <Selo tom={TOM_PROCESSO[processo.status]}>
                          {STATUS_PROCESSO[processo.status]}
                        </Selo>
                      </td>
                      <td>
                        {podeAvancar ? (
                          <button
                            type="button"
                            className="botao"
                            data-tipo="contorno"
                            onClick={() => {
                              setMensagem(null)
                              setEmEdicao(processo)
                            }}
                          >
                            Atualizar
                          </button>
                        ) : (
                          <span className="texto-fraco">encerrado</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <Paginacao
            pagina={lista.pagina}
            tamanhoPagina={lista.tamanho_pagina}
            total={lista.total}
            aoMudar={setPagina}
          />
        </>
      )}

      {abrindo ? (
        <AbrirProcesso
          petsDisponiveis={petsDisponiveis}
          adotantes={listaAdotantes.itens.filter((pessoa) => pessoa.ativo)}
          aoFechar={() => setAbrindo(false)}
          aoCriar={() => concluir('Processo de adoção aberto.')}
        />
      ) : null}

      {emEdicao ? (
        <AtualizarProcesso
          processo={emEdicao}
          pet={petPorId.get(emEdicao.pet_id) ?? null}
          adotante={adotantePorId.get(emEdicao.adotante_id) ?? null}
          aoFechar={() => setEmEdicao(null)}
          aoSalvar={(status) =>
            concluir(
              status === 'finalizado'
                ? 'Adoção finalizada. O pet foi marcado como adotado.'
                : `Processo movido para ${STATUS_PROCESSO[status].toLowerCase()}.`,
            )
          }
        />
      ) : null}
    </>
  )
}

/* --- Abrir processo ----------------------------------------------------- */

interface AbrirProps {
  petsDisponiveis: Pet[]
  adotantes: Adotante[]
  aoFechar: () => void
  aoCriar: () => void
}

function AbrirProcesso({ petsDisponiveis, adotantes, aoFechar, aoCriar }: AbrirProps) {
  const [petId, setPetId] = useState('')
  const [adotanteId, setAdotanteId] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [salvando, setSalvando] = useState(false)

  const faltaCadastro = petsDisponiveis.length === 0 || adotantes.length === 0

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setErro(null)
    setSalvando(true)
    try {
      await apiProcessos.criar({ pet_id: Number(petId), adotante_id: Number(adotanteId) })
      aoCriar()
    } catch (problema) {
      setErro(
        problema instanceof ErroApi
          ? problema.mensagemDeTela()
          : 'Não foi possível abrir o processo.',
      )
      setSalvando(false)
    }
  }

  return (
    <Sobreposicao titulo="Abrir processo de adoção" aoFechar={aoFechar}>
      {faltaCadastro ? (
        <div className="pilha-4">
          <p>
            {petsDisponiveis.length === 0
              ? 'Nenhum pet está disponível para adoção no momento.'
              : 'Nenhum adotante ativo cadastrado.'}
          </p>
          <div className="acoes">
            <Link to={petsDisponiveis.length === 0 ? '/pets' : '/adotantes'} className="botao">
              {petsDisponiveis.length === 0 ? 'Ver os pets' : 'Cadastrar adotante'}
            </Link>
            <button type="button" className="botao" data-tipo="texto" onClick={aoFechar}>
              Fechar
            </button>
          </div>
        </div>
      ) : (
        <form className="formulario" onSubmit={enviar}>
          {erro ? <Aviso>{erro}</Aviso> : null}

          <CampoSelecao
            rotulo="Pet"
            required
            value={petId}
            dica="Só aparecem os pets com situação disponível."
            onChange={(evento) => setPetId(evento.target.value)}
          >
            <option value="">Escolha um pet</option>
            {petsDisponiveis.map((pet) => (
              <option key={pet.id} value={pet.id}>
                {pet.nome}
                {pet.status_saude === 'em_tratamento_medico' ? ' (em tratamento médico)' : ''}
              </option>
            ))}
          </CampoSelecao>

          <CampoSelecao
            rotulo="Adotante"
            required
            value={adotanteId}
            onChange={(evento) => setAdotanteId(evento.target.value)}
          >
            <option value="">Escolha um adotante</option>
            {adotantes.map((pessoa) => (
              <option key={pessoa.id} value={pessoa.id}>
                {pessoa.nome}
              </option>
            ))}
          </CampoSelecao>

          <div className="acoes">
            <button type="submit" className="botao" disabled={salvando}>
              {salvando ? 'Abrindo…' : 'Abrir processo'}
            </button>
            <button type="button" className="botao" data-tipo="texto" onClick={aoFechar}>
              Cancelar
            </button>
          </div>
        </form>
      )}
    </Sobreposicao>
  )
}

/* --- Atualizar status --------------------------------------------------- */

interface AtualizarProps {
  processo: ProcessoAdocao
  pet: Pet | null
  adotante: Adotante | null
  aoFechar: () => void
  aoSalvar: (status: StatusProcessoAdocao) => void
}

/**
 * Finalizar e a unica transicao com regra propria: pet em tratamento medico nao tem a
 * adocao finalizada, sem excecao (RN01/RF16, decisao D1). A tela avisa e bloqueia antes
 * de enviar; a API recusa do mesmo jeito (422). O conflito de concorrencia (409) e
 * explicado com o que fazer em seguida.
 */
function AtualizarProcesso({ processo, pet, adotante, aoFechar, aoSalvar }: AtualizarProps) {
  const opcoes = PROXIMOS_STATUS[processo.status]
  const [status, setStatus] = useState<StatusProcessoAdocao>(opcoes[0])
  const [erro, setErro] = useState<string | null>(null)
  const [salvando, setSalvando] = useState(false)

  const emTratamento = pet?.status_saude === 'em_tratamento_medico'
  const finalizacaoBloqueada = status === 'finalizado' && emTratamento

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setErro(null)
    setSalvando(true)
    try {
      await apiProcessos.atualizarStatus(processo.id, { status })
      aoSalvar(status)
    } catch (problema) {
      if (problema instanceof ErroApi && problema.ehConflito) {
        setErro(
          'Outro processo deste mesmo pet foi finalizado primeiro. Recarregue a lista para ver a situação atual.',
        )
      } else if (problema instanceof ErroApi) {
        setErro(problema.mensagemDeTela())
      } else {
        setErro('Não foi possível atualizar o processo.')
      }
      setSalvando(false)
    }
  }

  return (
    <Sobreposicao titulo="Atualizar processo de adoção" aoFechar={aoFechar}>
      <form className="formulario" onSubmit={enviar}>
        <p>
          <strong>{pet?.nome ?? `Pet #${processo.pet_id}`}</strong> com{' '}
          {adotante?.nome ?? `adotante #${processo.adotante_id}`}, hoje em{' '}
          {STATUS_PROCESSO[processo.status].toLowerCase()}.
        </p>

        {erro ? <Aviso>{erro}</Aviso> : null}

        <CampoSelecao
          rotulo="Novo estado"
          value={status}
          onChange={(evento) => setStatus(evento.target.value as StatusProcessoAdocao)}
        >
          {opcoes.map((valor) => (
            <option key={valor} value={valor}>
              {STATUS_PROCESSO[valor]}
            </option>
          ))}
        </CampoSelecao>

        {finalizacaoBloqueada ? (
          <Aviso tom="atencao">
            {pet?.nome} está em tratamento de <strong>{pet?.doenca_atual}</strong>. A adoção só pode
            ser finalizada depois da alta médica.
          </Aviso>
        ) : null}

        {status === 'cancelado' ? (
          <p className="texto-fraco">
            Cancelar encerra o processo. O pet volta a ficar disponível para adoção.
          </p>
        ) : null}

        <div className="acoes">
          <button
            type="submit"
            className="botao"
            data-tipo={status === 'cancelado' ? 'perigo' : undefined}
            disabled={salvando || finalizacaoBloqueada}
          >
            {salvando ? 'Salvando…' : rotuloDoBotao(status)}
          </button>
          <button type="button" className="botao" data-tipo="texto" onClick={aoFechar}>
            Cancelar
          </button>
        </div>
      </form>
    </Sobreposicao>
  )
}

/** O botao diz exatamente o que vai acontecer, com o mesmo verbo do resultado. */
function rotuloDoBotao(status: StatusProcessoAdocao): string {
  if (status === 'aprovado') return 'Aprovar adoção'
  if (status === 'finalizado') return 'Finalizar adoção'
  if (status === 'cancelado') return 'Cancelar processo'
  return 'Salvar'
}

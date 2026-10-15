/**
 * Apadrinhamentos de um padrinho (fase 3, H7): os ativos primeiro, depois os encerrados.
 * O valor combinado nao se edita -- para mudar, encerra-se e abre-se outro, e o historico
 * do que era esperado em cada mes continua certo.
 */

import { useState } from 'react'
import type { FormEvent } from 'react'
import { ErroApi } from '../api/cliente'
import { apadrinhamentos, pets as apiPets } from '../api/recursos'
import type { Apadrinhamento, Padrinho } from '../api/tipos'
import { Campo, CampoSelecao } from './Campos'
import { Aviso, Carregando, Selo, Sobreposicao } from './Interface'
import { dataDeHoje, formatarData, formatarMoeda } from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

interface Props {
  padrinho: Padrinho
  aoFechar: () => void
}

export function ApadrinhamentosDoPadrinho({ padrinho, aoFechar }: Props) {
  const [cadastrando, setCadastrando] = useState(false)
  const [mensagem, setMensagem] = useState<{ tom: 'sucesso' | 'erro'; texto: string } | null>(null)
  const { dados, carregando, erro, recarregar } = useRequisicao(
    () =>
      apadrinhamentos.listar({
        padrinho_id: padrinho.id,
        incluir_encerrados: true,
        tamanho_pagina: 100,
      }),
    [padrinho.id],
  )

  function concluir(texto: string) {
    setCadastrando(false)
    setMensagem({ tom: 'sucesso', texto })
    recarregar()
  }

  function falhar(problema: unknown, padrao: string) {
    setMensagem({
      tom: 'erro',
      texto: problema instanceof ErroApi ? problema.mensagemDeTela() : padrao,
    })
  }

  const ativos = dados?.itens.filter((item) => item.ativo) ?? []
  const totalMensal = ativos.reduce((soma, item) => soma + Number(item.valor_mensal), 0)

  return (
    <Sobreposicao titulo={`Apadrinhamentos de ${padrinho.nome}`} aoFechar={aoFechar}>
      <div className="pilha-4">
        {mensagem ? <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso> : null}
        {carregando ? <Carregando /> : null}
        {erro ? <Aviso>{erro}</Aviso> : null}

        {dados ? (
          dados.itens.length === 0 ? (
            <p className="texto-fraco">Este padrinho ainda não apadrinha nenhum pet.</p>
          ) : (
            <>
              <p>
                {ativos.length > 0 ? (
                  <>
                    Compromisso de{' '}
                    <strong className="numero-tabular">{formatarMoeda(totalMensal)}</strong> por mês
                    em {ativos.length === 1 ? '1 pet' : `${ativos.length} pets`}.
                  </>
                ) : (
                  'Nenhum apadrinhamento ativo.'
                )}
              </p>
              <div className="tabela-envolucro">
                <table className="tabela">
                  <thead>
                    <tr>
                      <th>Pet</th>
                      <th className="numero">Por mês</th>
                      <th>Período</th>
                      <th>
                        <span className="so-leitor-tela">Ações</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {dados.itens.map((item) => (
                      <LinhaApadrinhamento
                        key={item.id}
                        apadrinhamento={item}
                        aoEncerrar={() => concluir(`Apadrinhamento de ${item.pet_nome} encerrado.`)}
                        aoFalhar={(problema) => falhar(problema, 'Não foi possível encerrar.')}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )
        ) : null}

        {cadastrando ? (
          <FormularioApadrinhamento
            padrinho={padrinho}
            aoSalvar={(petNome) => concluir(`${padrinho.nome} agora apadrinha ${petNome}.`)}
            aoFalhar={(problema) => falhar(problema, 'Não foi possível registrar.')}
            aoCancelar={() => setCadastrando(false)}
          />
        ) : null}

        <div className="acoes">
          {cadastrando ? null : (
            <button type="button" className="botao" onClick={() => setCadastrando(true)}>
              Apadrinhar um pet
            </button>
          )}
          <button type="button" className="botao" data-tipo="contorno" onClick={aoFechar}>
            Fechar
          </button>
        </div>
      </div>
    </Sobreposicao>
  )
}

/* --- Uma linha -------------------------------------------------------- */

interface LinhaProps {
  apadrinhamento: Apadrinhamento
  aoEncerrar: () => void
  aoFalhar: (problema: unknown) => void
}

function LinhaApadrinhamento({ apadrinhamento, aoEncerrar, aoFalhar }: LinhaProps) {
  const [encerrando, setEncerrando] = useState(false)
  const [dataFim, setDataFim] = useState(dataDeHoje())
  const [salvando, setSalvando] = useState(false)

  async function encerrar(evento: FormEvent) {
    evento.preventDefault()
    setSalvando(true)
    try {
      await apadrinhamentos.encerrar(apadrinhamento.id, dataFim)
      aoEncerrar()
    } catch (problema) {
      aoFalhar(problema)
      setSalvando(false)
    }
  }

  return (
    <tr>
      <td className="principal">
        {apadrinhamento.pet_nome} {apadrinhamento.ativo ? null : <Selo>Encerrado</Selo>}
      </td>
      <td className="numero">{formatarMoeda(apadrinhamento.valor_mensal)}</td>
      <td>
        desde {formatarData(apadrinhamento.data_inicio)}
        {apadrinhamento.data_fim ? ` até ${formatarData(apadrinhamento.data_fim)}` : null}
      </td>
      <td>
        {!apadrinhamento.ativo ? null : encerrando ? (
          <form className="acoes" onSubmit={encerrar}>
            <Campo
              rotulo="Encerrar em"
              type="date"
              required
              min={apadrinhamento.data_inicio}
              max={dataDeHoje()}
              value={dataFim}
              onChange={(e) => setDataFim(e.target.value)}
            />
            <button type="submit" className="botao" data-tipo="perigo" disabled={salvando}>
              {salvando ? 'Encerrando…' : 'Confirmar'}
            </button>
            <button
              type="button"
              className="botao"
              data-tipo="texto"
              onClick={() => setEncerrando(false)}
            >
              Cancelar
            </button>
          </form>
        ) : (
          <button
            type="button"
            className="botao"
            data-tipo="texto"
            onClick={() => setEncerrando(true)}
          >
            Encerrar
          </button>
        )}
      </td>
    </tr>
  )
}

/* --- Cadastro --------------------------------------------------------- */

interface FormProps {
  padrinho: Padrinho
  aoSalvar: (petNome: string) => void
  aoFalhar: (problema: unknown) => void
  aoCancelar: () => void
}

function FormularioApadrinhamento({ padrinho, aoSalvar, aoFalhar, aoCancelar }: FormProps) {
  // Pet adotado nao recebe apadrinhamento (a API recusa): ficam de fora da lista.
  const listaDePets = useRequisicao(() => apiPets.listar({ tamanho_pagina: 100 }), [])
  const [petId, setPetId] = useState('')
  const [valor, setValor] = useState('')
  const [dataInicio, setDataInicio] = useState(dataDeHoje())
  const [salvando, setSalvando] = useState(false)

  const opcoes = (listaDePets.dados?.itens ?? []).filter((pet) => pet.situacao_adocao !== 'adotado')

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    const pet = opcoes.find((item) => item.id === Number(petId))
    if (!pet) return
    setSalvando(true)
    try {
      await apadrinhamentos.criar({
        padrinho_id: padrinho.id,
        pet_id: pet.id,
        valor_mensal: Number(valor.replace(',', '.')),
        data_inicio: dataInicio,
      })
      aoSalvar(pet.nome)
    } catch (problema) {
      aoFalhar(problema)
      setSalvando(false)
    }
  }

  if (listaDePets.carregando) return <Carregando texto="Buscando os pets…" />
  if (listaDePets.erro) return <Aviso>{listaDePets.erro}</Aviso>

  return (
    <form className="formulario" onSubmit={enviar}>
      <CampoSelecao rotulo="Pet" required value={petId} onChange={(e) => setPetId(e.target.value)}>
        <option value="">Escolha o pet</option>
        {opcoes.map((pet) => (
          <option key={pet.id} value={pet.id}>
            {pet.nome}
          </option>
        ))}
      </CampoSelecao>
      <div className="formulario-duplo">
        <Campo
          rotulo="Valor por mês"
          type="number"
          step="0.01"
          min="0.01"
          max={99999999.99}
          required
          inputMode="decimal"
          value={valor}
          dica="Em reais."
          onChange={(e) => setValor(e.target.value)}
        />
        <Campo
          rotulo="Início"
          type="date"
          required
          max={dataDeHoje()}
          value={dataInicio}
          onChange={(e) => setDataInicio(e.target.value)}
        />
      </div>
      <div className="acoes">
        <button type="submit" className="botao" disabled={salvando}>
          {salvando ? 'Salvando…' : 'Apadrinhar'}
        </button>
        <button type="button" className="botao" data-tipo="texto" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

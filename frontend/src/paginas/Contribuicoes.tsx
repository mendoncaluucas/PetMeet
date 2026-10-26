/**
 * Esperado x recebido dos padrinhos (fase 3, H10): quanto cada um combinou por mes e quanto
 * doou, para a equipe cobrar quem atrasou. Tudo vem calculado da API; a tela so formata.
 */

import { useState } from 'react'
import { apadrinhamentos } from '../api/recursos'
import type { MesDoPadrinho, SituacaoDoMes } from '../api/tipos'
import { CampoMarcador } from '../componentes/Campos'
import {
  Aviso,
  CabecalhoPagina,
  Carregando,
  EstadoVazio,
  Paginacao,
} from '../componentes/Interface'
import {
  SITUACOES_DO_MES,
  contagem,
  formatarMes,
  formatarMesCurto,
  formatarMoeda,
} from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

const TAMANHO_PAGINA = 20
const LEGENDA: SituacaoDoMes[] = ['em_dia', 'parcial', 'sem_doacao', 'em_andamento']

export function Contribuicoes() {
  const [pagina, setPagina] = useState(1)
  const [soPendentes, setSoPendentes] = useState(false)

  const { dados, carregando, erro } = useRequisicao(
    () =>
      apadrinhamentos.esperadoRecebido({
        so_pendentes: soPendentes,
        pagina,
        tamanho_pagina: TAMANHO_PAGINA,
      }),
    [pagina, soPendentes],
  )
  // Todos os padrinhos trazem os mesmos 12 meses: o cabecalho sai do primeiro.
  const meses = dados?.itens[0]?.meses.map((mes) => mes.mes) ?? []

  return (
    <>
      <CabecalhoPagina
        titulo="Contribuições"
        descricao="Quanto cada padrinho combinou por mês e quanto doou nos últimos 12 meses. Mês fechado parcial ou sem doação conta como pendência."
      />

      <div className="filtros">
        <CampoMarcador
          rotulo="Só quem tem pendência"
          checked={soPendentes}
          onChange={(evento) => {
            setPagina(1)
            setSoPendentes(evento.target.checked)
          }}
        />
      </div>

      <ul className="legenda-contribuicoes" aria-label="Legenda">
        {LEGENDA.map((situacao) => (
          <li key={situacao} data-situacao={situacao}>
            {SITUACOES_DO_MES[situacao]}
          </li>
        ))}
      </ul>

      {carregando ? <Carregando /> : null}
      {erro ? <Aviso>{erro}</Aviso> : null}

      {dados && !carregando ? (
        dados.itens.length === 0 ? (
          <EstadoVazio
            titulo={
              soPendentes ? 'Nenhum padrinho com pendência' : 'Nenhum apadrinhamento no período'
            }
            descricao={
              soPendentes
                ? 'Todos os meses fechados estão pagos.'
                : 'Os padrinhos aparecem aqui quando têm um apadrinhamento ativo nos últimos 12 meses.'
            }
          />
        ) : (
          <>
            <div className="tabela-envolucro">
              <table className="tabela tabela-contribuicoes">
                <thead>
                  <tr>
                    <th>Padrinho</th>
                    {meses.map((mes) => (
                      <th key={mes} className="numero" title={formatarMes(mes)}>
                        {formatarMesCurto(mes)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dados.itens.map((padrinho) => (
                    <tr key={padrinho.padrinho_id}>
                      <td className="principal">
                        {padrinho.padrinho_nome}
                        <span className="contato-linha texto-fraco">
                          {padrinho.meses_pendentes > 0
                            ? contagem(padrinho.meses_pendentes, 'mês pendente', 'meses pendentes')
                            : 'Em dia'}
                        </span>
                      </td>
                      {padrinho.meses.map((mes) => (
                        <CelulaDoMes key={mes.mes} mes={mes} />
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Paginacao
              pagina={pagina}
              tamanhoPagina={TAMANHO_PAGINA}
              total={dados.total}
              aoMudar={setPagina}
            />
          </>
        )
      ) : null}
    </>
  )
}

function CelulaDoMes({ mes }: { mes: MesDoPadrinho }) {
  if (mes.situacao === 'sem_compromisso') {
    return (
      <td className="numero texto-fraco" data-situacao={mes.situacao}>
        <span aria-hidden="true">—</span>
        <span className="so-leitor-tela">
          {formatarMes(mes.mes)}: {SITUACOES_DO_MES[mes.situacao]}
        </span>
      </td>
    )
  }
  const descricao = `${formatarMes(mes.mes)}: ${formatarMoeda(mes.recebido)} de ${formatarMoeda(
    mes.esperado,
  )}, ${SITUACOES_DO_MES[mes.situacao].toLowerCase()}`
  return (
    <td className="numero" data-situacao={mes.situacao} title={descricao}>
      <span aria-hidden="true">
        {formatarMoeda(mes.recebido)}
        <small>de {formatarMoeda(mes.esperado)}</small>
      </span>
      <span className="so-leitor-tela">{descricao}</span>
    </td>
  )
}

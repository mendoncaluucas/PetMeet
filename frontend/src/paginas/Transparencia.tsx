import { useState } from 'react'
import { Link } from 'react-router-dom'
import { transparencia } from '../api/recursos'
import type { MesDoPortal } from '../api/tipos'
import { useAuth } from '../auth/ContextoAuth'
import { Aviso, Carregando, EstadoVazio, Selo } from '../componentes/Interface'
import { CATEGORIAS_GASTO, formatarMes, formatarMoeda } from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

/**
 * Portal publico de prestacao de contas (H11). Abre sem login. Tudo vem somado de
 * GET /transparencia: a tela so formata, e nao mostra nada que identifique pessoa (D15).
 */
export function Transparencia() {
  const { autenticado } = useAuth()
  const { dados, carregando, erro } = useRequisicao(transparencia.portal, [])

  return (
    <div className="portal">
      <header className="portal-topo">
        <Link to="/transparencia" className="login-marca">
          Pet<em>Meet</em>
        </Link>
        <Link to={autenticado ? '/' : '/entrar'} className="botao" data-tipo="contorno">
          {autenticado ? 'Voltar ao painel' : 'Entrar no painel'}
        </Link>
      </header>

      <main className="portal-conteudo">
        <div className="cabecalho-pagina">
          <div>
            <h1>Prestação de contas</h1>
            <p className="descricao">
              Quanto a ONG recebeu e gastou nos últimos 12 meses, a partir das doações e dos gastos
              que a equipe registra no dia a dia.
            </p>
          </div>
        </div>

        {carregando ? <Carregando texto="Somando doações e gastos…" /> : null}
        {erro ? <Aviso>{erro}</Aviso> : null}
        {dados ? (
          <>
            <section className="destaque">
              <p>
                Saldo acumulado de{' '}
                <b className="numero-destaque">{formatarMoeda(dados.saldo_acumulado)}</b>
              </p>
              <div className="destaque-rodape">
                <span className="destaque-medida">
                  <b>{formatarMoeda(dados.arrecadado_no_periodo)}</b>
                  arrecadado em 12 meses
                </span>
                <span className="destaque-medida">
                  <b>{formatarMoeda(dados.gasto_no_periodo)}</b>
                  gasto em 12 meses
                </span>
                <span className="destaque-medida">
                  <b>
                    {formatarMes(dados.mes_inicial)} a {formatarMes(dados.mes_final)}
                  </b>
                  período
                </span>
              </div>
            </section>

            <MesAMes meses={dados.meses} />
            <GastosPorCategoria meses={dados.meses} />

            <section className="portal-secao">
              <div className="secao-titulo">
                <h2>Por pet</h2>
              </div>
              {dados.pets.length === 0 ? (
                <EstadoVazio
                  titulo="Nenhuma doação ou gasto ligado a um pet"
                  descricao="Doações e gastos sem pet indicado contam só nos totais da ONG."
                />
              ) : (
                <div className="tabela-envolucro">
                  <table className="tabela">
                    <thead>
                      <tr>
                        <th>Pet</th>
                        <th className="numero">Arrecadado para ele</th>
                        <th className="numero">Gasto com ele</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dados.pets.map((pet) => (
                        <tr key={pet.pet_id}>
                          <td className="principal">{pet.nome}</td>
                          <td className="numero">{formatarMoeda(pet.arrecadado)}</td>
                          <td className="numero">{formatarMoeda(pet.gasto)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <p className="texto-fraco portal-nota">
              O saldo acumulado soma tudo o que foi registrado desde o início, inclusive antes
              destes 12 meses. Um lançamento corrigido aparece como valor negativo no mês da
              correção, e por isso o total de um mês fechado não muda depois.
            </p>
          </>
        ) : null}
      </main>
    </div>
  )
}

function MesAMes({ meses }: { meses: MesDoPortal[] }) {
  return (
    <section className="portal-secao">
      <div className="secao-titulo">
        <h2>Mês a mês</h2>
      </div>
      <div className="tabela-envolucro">
        <table className="tabela">
          <thead>
            <tr>
              <th>Mês</th>
              <th className="numero">Arrecadado</th>
              <th className="numero">Gasto</th>
              <th className="numero">Saldo do mês</th>
              <th className="numero">Saldo acumulado</th>
            </tr>
          </thead>
          <tbody>
            {meses.map((mes) => (
              <tr key={mes.mes}>
                <td className="principal">
                  {formatarMes(mes.mes)}
                  {mes.em_andamento ? (
                    <>
                      {' '}
                      <Selo tom="ambar">em andamento</Selo>
                    </>
                  ) : null}
                </td>
                <td className="numero">{formatarMoeda(mes.arrecadado)}</td>
                <td className="numero">{formatarMoeda(mes.gasto)}</td>
                <td className="numero" data-negativo={Number(mes.saldo) < 0 ? 'sim' : undefined}>
                  {formatarMoeda(mes.saldo)}
                </td>
                <td className="numero">{formatarMoeda(mes.saldo_acumulado)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function GastosPorCategoria({ meses }: { meses: MesDoPortal[] }) {
  const [escolhido, setEscolhido] = useState(meses[0]?.mes ?? '')
  const mes = meses.find((item) => item.mes === escolhido) ?? meses[0]
  if (!mes) return null

  // A barra so desenha a proporcao; o valor exibido e o que veio da API.
  const maior = Math.max(...mes.gastos_por_categoria.map((item) => Number(item.valor)), 0)

  return (
    <section className="portal-secao">
      <div className="secao-titulo">
        <h2>Para onde foi o dinheiro</h2>
        <select
          className="portal-escolha"
          aria-label="Mês dos gastos por categoria"
          value={mes.mes}
          onChange={(evento) => setEscolhido(evento.target.value)}
        >
          {meses.map((item) => (
            <option key={item.mes} value={item.mes}>
              {formatarMes(item.mes)}
            </option>
          ))}
        </select>
      </div>

      {mes.gastos_por_categoria.length === 0 ? (
        <EstadoVazio
          titulo="Nenhum gasto neste mês"
          descricao="Quando a equipe registrar um gasto, ele aparece aqui pela categoria."
        />
      ) : (
        <ul className="barras">
          {mes.gastos_por_categoria.map((item) => {
            const valor = Number(item.valor)
            const largura = maior > 0 && valor > 0 ? (valor / maior) * 100 : 0
            return (
              <li key={item.categoria} className="barra">
                <span className="barra-rotulo">{CATEGORIAS_GASTO[item.categoria]}</span>
                <span className="barra-trilho" aria-hidden="true">
                  <span className="barra-valor" style={{ width: `${largura}%` }} />
                </span>
                <span className="barra-numero">{formatarMoeda(item.valor)}</span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

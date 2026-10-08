import { Link } from 'react-router-dom'
import { painel } from '../api/recursos'
import { Aviso, Carregando, EstadoVazio, Selo } from '../componentes/Interface'
import {
  STATUS_PROCESSO,
  STATUS_SAUDE,
  TOM_PROCESSO,
  contagem,
  formatarMoeda,
  tempoNoAbrigo,
} from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

/**
 * Tudo vem de GET /painel/resumo. O Painel baixava as primeiras 100 linhas de cada
 * listagem e contava no navegador: passando de 100, os numeros ficavam errados, e o mes
 * do "recebido este mes" era o de UTC (DEF-09, DEF-10).
 */
export function Painel() {
  const { dados, carregando, erro } = useRequisicao(painel.resumo, [])

  if (carregando) return <Carregando texto="Reunindo as pendências do dia…" />
  if (erro) return <Aviso>{erro}</Aviso>
  if (!dados) return null

  return (
    <>
      <section className="destaque">
        <p>
          {montarManchete(
            dados.pets_em_tratamento,
            dados.processos_aguardando_finalizacao,
            dados.pets_disponiveis,
          )}
        </p>
        <div className="destaque-rodape">
          <span className="destaque-medida">
            <b>{dados.pets_total}</b>
            pets no abrigo
          </span>
          <span className="destaque-medida">
            <b>{dados.pets_disponiveis}</b>
            disponíveis para adoção
          </span>
          <span className="destaque-medida">
            <b>{dados.processos_em_andamento}</b>
            adoções em andamento
          </span>
          <span className="destaque-medida">
            <b>{formatarMoeda(dados.doacoes_do_mes_total)}</b>
            recebido este mês
          </span>
        </div>
      </section>

      <div className="painel-secoes">
        <section>
          <div className="secao-titulo">
            <h2>Acompanhamento médico</h2>
            <Link to="/pets?status_saude=em_tratamento_medico" className="texto-fraco">
              Ver todos
            </Link>
          </div>

          {dados.em_tratamento.length === 0 ? (
            <EstadoVazio
              titulo="Nenhum pet em tratamento"
              descricao="Quando um animal entrar em tratamento médico, ele aparece aqui até a alta."
            />
          ) : (
            <div className="lista-atencao">
              {dados.em_tratamento.map((pet) => (
                <Link
                  key={pet.id}
                  to={`/pets/${pet.id}`}
                  className="item-atencao"
                  data-saude={pet.status_saude}
                >
                  <span>
                    <span className="item-atencao-nome">{pet.nome}</span>
                    <span className="item-atencao-detalhe">
                      {pet.doenca_atual ?? 'Tratamento sem diagnóstico registrado'}
                    </span>
                  </span>
                  <span className="item-atencao-fim item-atencao-detalhe">
                    {tempoNoAbrigo(pet.data_resgate)}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="secao-titulo">
            <h2>Adoções em andamento</h2>
            <Link to="/adocoes" className="texto-fraco">
              Ver todas
            </Link>
          </div>

          {dados.em_andamento.length === 0 ? (
            <EstadoVazio
              titulo="Nenhuma adoção em andamento"
              descricao="Abra um processo a partir da ficha de um pet disponível."
              acao={
                <Link to="/adocoes" className="botao" data-tipo="contorno">
                  Abrir processo
                </Link>
              }
            />
          ) : (
            <div className="lista-atencao">
              {dados.em_andamento.map((processo) => (
                <Link
                  key={processo.id}
                  to="/adocoes"
                  className="item-atencao"
                  data-saude={processo.pet_status_saude}
                >
                  <span>
                    <span className="item-atencao-nome">{processo.pet_nome}</span>
                    <span className="item-atencao-detalhe">
                      com {processo.adotante_nome}
                      {processo.pet_status_saude === 'em_tratamento_medico'
                        ? ` — ${STATUS_SAUDE.em_tratamento_medico.toLowerCase()}`
                        : ''}
                    </span>
                  </span>
                  <span className="item-atencao-fim">
                    <Selo tom={TOM_PROCESSO[processo.status]}>
                      {STATUS_PROCESSO[processo.status]}
                    </Selo>
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>

      {dados.esperando_ha_mais_tempo.length > 0 ? (
        <section style={{ marginTop: 'var(--e-6)' }}>
          <div className="secao-titulo">
            <h2>Esperando há mais tempo</h2>
            <Link to="/pets?situacao_adocao=disponivel" className="texto-fraco">
              Ver disponíveis
            </Link>
          </div>
          <div className="fila-espera">
            {dados.esperando_ha_mais_tempo.map((pet) => (
              <Link
                key={pet.id}
                to={`/pets/${pet.id}`}
                className="ficha item-espera"
                data-saude={pet.status_saude}
              >
                <span className="item-atencao-nome">{pet.nome}</span>
                <span className="item-atencao-detalhe">{tempoNoAbrigo(pet.data_resgate)}</span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </>
  )
}

/**
 * A manchete diz o que fazer agora, com a pendencia mais urgente na frente:
 * tratamento medico trava finalizacao de adocao (RN01), entao vem primeiro.
 */
function montarManchete(emTratamento: number, aguardando: number, disponiveis: number) {
  if (emTratamento > 0) {
    return (
      <>
        <span className="numero-destaque">{contagem(emTratamento, 'pet está', 'pets estão')}</span>{' '}
        em tratamento médico. A adoção deles só pode ser finalizada depois da alta médica.
      </>
    )
  }
  if (aguardando > 0) {
    return (
      <>
        <span className="numero-destaque">
          {contagem(aguardando, 'adoção aprovada', 'adoções aprovadas')}
        </span>{' '}
        esperando a finalização.
      </>
    )
  }
  if (disponiveis > 0) {
    return (
      <>
        Nenhuma pendência médica hoje.{' '}
        <span className="numero-destaque">
          {contagem(disponiveis, 'pet está disponível', 'pets estão disponíveis')}
        </span>{' '}
        para adoção.
      </>
    )
  }
  return <>Nenhuma pendência hoje. Cadastre os animais que chegaram ao abrigo.</>
}

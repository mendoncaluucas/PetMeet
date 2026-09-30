import { Link } from 'react-router-dom'
import { adotantes, doacoes, pets, processos } from '../api/recursos'
import type { Adotante, Doacao, Pet, ProcessoAdocao } from '../api/tipos'
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

const LIMITE = 100

interface Carga {
  pets: Pet[]
  totalPets: number
  processos: ProcessoAdocao[]
  adotantes: Adotante[]
  doacoes: Doacao[]
}

async function carregarPainel(): Promise<Carga> {
  const [listaPets, listaProcessos, listaAdotantes, listaDoacoes] = await Promise.all([
    pets.listar({ tamanho_pagina: LIMITE }),
    processos.listar({ tamanho_pagina: LIMITE }),
    adotantes.listar(1, LIMITE, true), // inclui inativos: dao nome aos processos antigos
    doacoes.listar({ tamanho_pagina: LIMITE }),
  ])
  return {
    pets: listaPets.itens,
    totalPets: listaPets.total,
    processos: listaProcessos.itens,
    adotantes: listaAdotantes.itens,
    doacoes: listaDoacoes.itens,
  }
}

export function Painel() {
  const { dados, carregando, erro } = useRequisicao(carregarPainel, [])

  if (carregando) return <Carregando texto="Reunindo as pendências do dia…" />
  if (erro) return <Aviso>{erro}</Aviso>
  if (!dados) return null

  const emTratamento = dados.pets.filter((pet) => pet.status_saude === 'em_tratamento_medico')
  const disponiveis = dados.pets.filter((pet) => pet.situacao_adocao === 'disponivel')
  const emAndamento = dados.processos.filter(
    (processo) => processo.status === 'em_analise' || processo.status === 'aprovado',
  )
  const aguardandoFinalizacao = emAndamento.filter((processo) => processo.status === 'aprovado')

  const nomeDoPet = new Map(dados.pets.map((pet) => [pet.id, pet.nome]))
  const petPorId = new Map(dados.pets.map((pet) => [pet.id, pet]))
  const nomeDoAdotante = new Map(dados.adotantes.map((pessoa) => [pessoa.id, pessoa.nome]))

  // Quem espera ha mais tempo e quem a ONG precisa divulgar primeiro.
  const esperandoHaMaisTempo = [...disponiveis]
    .sort((a, b) => a.data_resgate.localeCompare(b.data_resgate))
    .slice(0, 5)

  const mesAtual = new Date().toISOString().slice(0, 7)
  const totalDoMes = dados.doacoes
    .filter((doacao) => doacao.data.startsWith(mesAtual))
    .reduce((soma, doacao) => soma + Number(doacao.valor), 0)

  return (
    <>
      <section className="destaque">
        <p>
          {montarManchete(emTratamento.length, aguardandoFinalizacao.length, disponiveis.length)}
        </p>
        <div className="destaque-rodape">
          <span className="destaque-medida">
            <b>{dados.totalPets}</b>
            pets no abrigo
          </span>
          <span className="destaque-medida">
            <b>{disponiveis.length}</b>
            disponíveis para adoção
          </span>
          <span className="destaque-medida">
            <b>{emAndamento.length}</b>
            adoções em andamento
          </span>
          <span className="destaque-medida">
            <b>{formatarMoeda(totalDoMes)}</b>
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

          {emTratamento.length === 0 ? (
            <EstadoVazio
              titulo="Nenhum pet em tratamento"
              descricao="Quando um animal entrar em tratamento médico, ele aparece aqui até a alta."
            />
          ) : (
            <div className="lista-atencao">
              {emTratamento.map((pet) => (
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

          {emAndamento.length === 0 ? (
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
              {emAndamento.map((processo) => {
                const pet = petPorId.get(processo.pet_id)
                return (
                  <Link
                    key={processo.id}
                    to="/adocoes"
                    className="item-atencao"
                    data-saude={pet?.status_saude}
                  >
                    <span>
                      <span className="item-atencao-nome">
                        {nomeDoPet.get(processo.pet_id) ?? `Pet #${processo.pet_id}`}
                      </span>
                      <span className="item-atencao-detalhe">
                        com{' '}
                        {nomeDoAdotante.get(processo.adotante_id) ??
                          `adotante #${processo.adotante_id}`}
                        {pet?.status_saude === 'em_tratamento_medico'
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
                )
              })}
            </div>
          )}
        </section>
      </div>

      {esperandoHaMaisTempo.length > 0 ? (
        <section style={{ marginTop: 'var(--e-6)' }}>
          <div className="secao-titulo">
            <h2>Esperando há mais tempo</h2>
            <Link to="/pets?situacao_adocao=disponivel" className="texto-fraco">
              Ver disponíveis
            </Link>
          </div>
          <div className="fila-espera">
            {esperandoHaMaisTempo.map((pet) => (
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
        em tratamento médico. A adoção deles só pode ser finalizada com o acompanhamento em dia.
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

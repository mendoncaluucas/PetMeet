import { Link, useSearchParams } from 'react-router-dom'
import { pets } from '../api/recursos'
import { useAuth } from '../auth/ContextoAuth'
import type { EspeciePet, SituacaoAdocaoPet, StatusSaudePet } from '../api/tipos'
import { CampoSelecao, opcoesDe } from '../componentes/Campos'
import {
  Aviso,
  CabecalhoPagina,
  Carregando,
  EstadoVazio,
  Moldura,
  Paginacao,
  Selo,
} from '../componentes/Interface'
import {
  ESPECIES,
  SITUACOES_ADOCAO,
  STATUS_SAUDE,
  TOM_SAUDE,
  TOM_SITUACAO,
  idadeEmTexto,
  tempoNoAbrigo,
} from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

const TAMANHO_PAGINA = 12

/** Os filtros ficam na URL: a busca pode ser compartilhada e sobrevive ao F5. */
export function Pets() {
  const [parametros, setParametros] = useSearchParams()
  // Cadastrar pet e da equipe; o veterinario so consulta (POST /pets responde 403).
  const { ehEquipe } = useAuth()

  const pagina = Number(parametros.get('pagina') ?? '1') || 1
  const especie = (parametros.get('especie') ?? '') as EspeciePet | ''
  const statusSaude = (parametros.get('status_saude') ?? '') as StatusSaudePet | ''
  const situacao = (parametros.get('situacao_adocao') ?? '') as SituacaoAdocaoPet | ''

  const { dados, carregando, erro } = useRequisicao(
    () =>
      pets.listar({
        pagina,
        tamanho_pagina: TAMANHO_PAGINA,
        especie: especie || undefined,
        status_saude: statusSaude || undefined,
        situacao_adocao: situacao || undefined,
      }),
    [pagina, especie, statusSaude, situacao],
  )

  function ajustarFiltro(chave: string, valor: string) {
    const proximo = new URLSearchParams(parametros)
    if (valor) proximo.set(chave, valor)
    else proximo.delete(chave)
    proximo.delete('pagina') // trocar de filtro volta para a primeira pagina
    setParametros(proximo)
  }

  function irParaPagina(destino: number) {
    const proximo = new URLSearchParams(parametros)
    proximo.set('pagina', String(destino))
    setParametros(proximo)
    window.scrollTo({ top: 0 })
  }

  const temFiltro = Boolean(especie || statusSaude || situacao)

  return (
    <>
      <CabecalhoPagina
        titulo="Pets"
        descricao="Uma ficha por animal: estado de saúde na tarja da esquerda, situação de adoção no selo."
        acao={
          ehEquipe ? (
            <Link to="/pets/novo" className="botao">
              Cadastrar pet
            </Link>
          ) : undefined
        }
      />

      <div className="filtros">
        <CampoSelecao
          rotulo="Espécie"
          value={especie}
          onChange={(evento) => ajustarFiltro('especie', evento.target.value)}
        >
          <option value="">Todas</option>
          {opcoesDe(ESPECIES)}
        </CampoSelecao>

        <CampoSelecao
          rotulo="Estado de saúde"
          value={statusSaude}
          onChange={(evento) => ajustarFiltro('status_saude', evento.target.value)}
        >
          <option value="">Todos</option>
          {opcoesDe(STATUS_SAUDE)}
        </CampoSelecao>

        <CampoSelecao
          rotulo="Situação de adoção"
          value={situacao}
          onChange={(evento) => ajustarFiltro('situacao_adocao', evento.target.value)}
        >
          <option value="">Todas</option>
          {opcoesDe(SITUACOES_ADOCAO)}
        </CampoSelecao>

        {dados ? (
          <span className="filtros-resumo">
            {dados.total === 1 ? '1 pet encontrado' : `${dados.total} pets encontrados`}
          </span>
        ) : null}
      </div>

      {erro ? <Aviso>{erro}</Aviso> : null}
      {carregando ? <Carregando texto="Buscando fichas…" /> : null}

      {dados && !carregando ? (
        dados.itens.length === 0 ? (
          <EstadoVazio
            titulo={temFiltro ? 'Nenhum pet com esses filtros' : 'Nenhum pet cadastrado ainda'}
            descricao={
              temFiltro
                ? 'Tire um dos filtros para ver mais fichas.'
                : 'Cadastre o primeiro animal resgatado para começar o registro do abrigo.'
            }
            acao={
              temFiltro ? (
                <button
                  type="button"
                  className="botao"
                  data-tipo="contorno"
                  onClick={() => setParametros({})}
                >
                  Limpar filtros
                </button>
              ) : ehEquipe ? (
                <Link to="/pets/novo" className="botao">
                  Cadastrar pet
                </Link>
              ) : undefined
            }
          />
        ) : (
          <>
            <div className="grade-fichas">
              {dados.itens.map((pet) => (
                <Link
                  key={pet.id}
                  to={`/pets/${pet.id}`}
                  className="ficha ficha-pet"
                  data-saude={pet.status_saude}
                >
                  <Moldura url={pet.foto_url} nome={pet.nome} />
                  <div className="ficha-pet-corpo">
                    <span className="ficha-pet-nome">{pet.nome}</span>
                    <span className="ficha-pet-linha">
                      {ESPECIES[pet.especie]}, {idadeEmTexto(pet.idade)}
                    </span>
                    <span className="ficha-pet-linha">{tempoNoAbrigo(pet.data_resgate)}</span>
                    <span className="ficha-pet-selos">
                      <Selo tom={TOM_SAUDE[pet.status_saude]}>
                        {STATUS_SAUDE[pet.status_saude]}
                      </Selo>
                      <Selo tom={TOM_SITUACAO[pet.situacao_adocao]}>
                        {SITUACOES_ADOCAO[pet.situacao_adocao]}
                      </Selo>
                    </span>
                    {pet.doenca_atual ? (
                      <span className="ficha-pet-doenca">Tratando: {pet.doenca_atual}</span>
                    ) : null}
                  </div>
                </Link>
              ))}
            </div>

            <Paginacao
              pagina={dados.pagina}
              tamanhoPagina={dados.tamanho_pagina}
              total={dados.total}
              aoMudar={irParaPagina}
            />
          </>
        )
      ) : null}
    </>
  )
}

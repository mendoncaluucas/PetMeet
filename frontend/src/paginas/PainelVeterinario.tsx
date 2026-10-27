import { Link } from 'react-router-dom'
import { pets } from '../api/recursos'
import { AlertasVacina } from '../componentes/AlertasVacina'
import { Aviso, CabecalhoPagina, Carregando, EstadoVazio } from '../componentes/Interface'
import { contagem, tempoNoAbrigo } from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

const LIMITE = 100

/**
 * Pagina inicial do veterinario. Nao usa GET /painel/resumo: ele traz nomes de adotantes
 * e e so da equipe. Ao lado, os alertas de vacina (H6).
 */
export function PainelVeterinario() {
  const { dados, carregando, erro } = useRequisicao(
    () => pets.listar({ status_saude: 'em_tratamento_medico', tamanho_pagina: LIMITE }),
    [],
  )

  if (carregando) return <Carregando texto="Buscando os pets em tratamento…" />
  if (erro) return <Aviso>{erro}</Aviso>
  if (!dados) return null

  return (
    <>
      <CabecalhoPagina
        titulo="Início"
        descricao="A alta de um tratamento é sua: ela é registrada na ficha de cada pet."
      />

      <div className="painel-secoes">
        <section>
          <div className="secao-titulo">
            <h2>{contagem(dados.total, 'pet em tratamento', 'pets em tratamento')}</h2>
            <Link to="/pets?status_saude=em_tratamento_medico" className="texto-fraco">
              Ver na lista de pets
            </Link>
          </div>

          {dados.itens.length === 0 ? (
            <EstadoVazio
              titulo="Nenhum pet em tratamento"
              descricao="Quando a equipe registrar um tratamento, o pet aparece aqui até a alta."
            />
          ) : (
            <div className="lista-atencao">
              {dados.itens.map((pet) => (
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

          {dados.total > dados.itens.length ? (
            <p className="texto-fraco">
              Mostrando {dados.itens.length} de {dados.total}. Os demais estão na lista de pets.
            </p>
          ) : null}
        </section>

        <AlertasVacina limite={10} />
      </div>
    </>
  )
}

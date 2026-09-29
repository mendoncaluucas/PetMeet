import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ErroApi } from '../api/cliente'
import { adotantes as apiAdotantes, pets, processos as apiProcessos } from '../api/recursos'
import type { EspeciePet, Pet, StatusSaudePet } from '../api/tipos'
import { Campo, CampoSelecao, opcoesDe } from '../componentes/Campos'
import { Aviso, Carregando, Moldura, Selo } from '../componentes/Interface'
import {
  ESPECIES,
  SITUACOES_ADOCAO,
  STATUS_PROCESSO,
  STATUS_SAUDE,
  TOM_PROCESSO,
  TOM_SAUDE,
  TOM_SITUACAO,
  formatarData,
  formatarDataHora,
  idadeEmTexto,
  tempoNoAbrigo,
} from '../util/formato'
import { useRequisicao } from '../util/useRequisicao'

const TAMANHO_MAXIMO_FOTO = 5 * 1024 * 1024
const FORMATOS_FOTO = ['image/jpeg', 'image/png', 'image/webp']

type Secao = 'nenhuma' | 'dados' | 'saude'

export function PetDetalhe() {
  const { id } = useParams<{ id: string }>()
  const petId = Number(id)

  const { dados, carregando, erro } = useRequisicao(() => pets.obter(petId), [petId])
  const [pet, setPet] = useState<Pet | null>(null)
  const [secao, setSecao] = useState<Secao>('nenhuma')
  const [mensagem, setMensagem] = useState<{ tom: 'sucesso' | 'erro'; texto: string } | null>(null)

  useEffect(() => {
    if (dados) setPet(dados)
  }, [dados])

  function aplicar(atualizado: Pet, texto: string) {
    setPet(atualizado)
    setSecao('nenhuma')
    setMensagem({ tom: 'sucesso', texto })
  }

  function falhar(problema: unknown, padrao: string) {
    const texto = problema instanceof ErroApi ? problema.mensagemDeTela() : padrao
    setMensagem({ tom: 'erro', texto })
  }

  if (carregando) return <Carregando texto="Abrindo a ficha…" />
  if (erro) return <Aviso>{erro}</Aviso>
  if (!pet) return null

  return (
    <>
      <p style={{ marginBottom: 'var(--e-4)' }}>
        <Link to="/pets" className="botao" data-tipo="texto">
          Voltar para os pets
        </Link>
      </p>

      {/* O nome vem antes da foto: em qualquer largura, a primeira coisa a ler
          e de quem e a ficha. */}
      <header className="cabecalho-ficha">
        <h1>{pet.nome}</h1>
        <div className="ficha-pet-selos">
          <Selo tom={TOM_SAUDE[pet.status_saude]}>{STATUS_SAUDE[pet.status_saude]}</Selo>
          <Selo tom={TOM_SITUACAO[pet.situacao_adocao]}>
            {SITUACOES_ADOCAO[pet.situacao_adocao]}
          </Selo>
        </div>
      </header>

      <div className="detalhe-pet">
        <div className="detalhe-coluna-foto">
          <Moldura url={pet.foto_url} nome={pet.nome} formato="retrato" />
          <EnvioDeFoto
            petId={pet.id}
            temFoto={Boolean(pet.foto_url)}
            aoEnviar={(atualizado) => aplicar(atualizado, 'Foto enviada.')}
            aoFalhar={(texto) => setMensagem({ tom: 'erro', texto })}
          />
        </div>

        <div className="detalhe-blocos">
          {mensagem ? <Aviso tom={mensagem.tom}>{mensagem.texto}</Aviso> : null}

          {/* --- Dados do animal --- */}
          <section className="ficha">
            <div className="ficha-corpo">
              <div className="secao-titulo">
                <h2>Dados do animal</h2>
                <button
                  type="button"
                  className="botao"
                  data-tipo="texto"
                  onClick={() => setSecao(secao === 'dados' ? 'nenhuma' : 'dados')}
                >
                  {secao === 'dados' ? 'Fechar' : 'Editar'}
                </button>
              </div>

              {secao === 'dados' ? (
                <FormularioDados
                  pet={pet}
                  aoSalvar={(atualizado) => aplicar(atualizado, 'Dados atualizados.')}
                  aoFalhar={(problema) => falhar(problema, 'Não foi possível salvar os dados.')}
                  aoCancelar={() => setSecao('nenhuma')}
                />
              ) : (
                <dl className="dados">
                  <div className="dado">
                    <dt>Espécie</dt>
                    <dd>{ESPECIES[pet.especie]}</dd>
                  </div>
                  <div className="dado">
                    <dt>Idade</dt>
                    <dd>{idadeEmTexto(pet.idade)}</dd>
                  </div>
                  <div className="dado">
                    <dt>Resgatado em</dt>
                    <dd>{formatarData(pet.data_resgate)}</dd>
                  </div>
                  <div className="dado">
                    <dt>Tempo no abrigo</dt>
                    <dd>{tempoNoAbrigo(pet.data_resgate) || '—'}</dd>
                  </div>
                  <div className="dado">
                    <dt>Última alteração</dt>
                    <dd>{formatarDataHora(pet.atualizado_em)}</dd>
                  </div>
                </dl>
              )}
            </div>
          </section>

          {/* --- Ficha medica --- */}
          <section className="ficha" data-saude={pet.status_saude}>
            <div className="ficha-corpo">
              <div className="secao-titulo">
                <h2>Ficha médica</h2>
                <button
                  type="button"
                  className="botao"
                  data-tipo="texto"
                  onClick={() => setSecao(secao === 'saude' ? 'nenhuma' : 'saude')}
                >
                  {secao === 'saude' ? 'Fechar' : 'Registrar mudança'}
                </button>
              </div>

              {secao === 'saude' ? (
                <FormularioSaude
                  pet={pet}
                  aoSalvar={(atualizado) => aplicar(atualizado, 'Ficha médica atualizada.')}
                  aoFalhar={(problema) => falhar(problema, 'Não foi possível atualizar a ficha.')}
                  aoCancelar={() => setSecao('nenhuma')}
                />
              ) : (
                <div className="pilha-3">
                  <p>{STATUS_SAUDE[pet.status_saude]}</p>
                  {pet.doenca_atual ? (
                    <p>
                      Em tratamento de <strong>{pet.doenca_atual}</strong>.
                    </p>
                  ) : (
                    <p className="texto-fraco">Nenhuma doença em tratamento registrada.</p>
                  )}
                  {pet.status_saude === 'em_tratamento_medico' ? (
                    <Aviso tom="atencao">
                      Para finalizar uma adoção deste pet, a equipe precisa confirmar que o
                      acompanhamento médico está em dia.
                    </Aviso>
                  ) : null}
                </div>
              )}
            </div>
          </section>

          {/* --- Situacao de adocao: so leitura, muda pelo processo de adocao --- */}
          <section className="ficha">
            <div className="ficha-corpo">
              <div className="secao-titulo">
                <h2>Situação de adoção</h2>
              </div>
              <p>
                {pet.situacao_adocao === 'disponivel'
                  ? 'Disponível para adoção. Abra um processo quando aparecer um adotante interessado.'
                  : pet.situacao_adocao === 'em_processo_adocao'
                    ? 'Em processo de adoção. A situação muda sozinha quando o processo for finalizado ou cancelado.'
                    : 'Adotado. A ficha fica no histórico do abrigo.'}
              </p>
            </div>
          </section>

          <ProcessosDoPet petId={pet.id} />
        </div>
      </div>
    </>
  )
}

/* --- Envio da foto ------------------------------------------------------ */

interface EnvioProps {
  petId: number
  temFoto: boolean
  aoEnviar: (pet: Pet) => void
  aoFalhar: (texto: string) => void
}

function EnvioDeFoto({ petId, temFoto, aoEnviar, aoFalhar }: EnvioProps) {
  const entrada = useRef<HTMLInputElement>(null)
  const [enviando, setEnviando] = useState(false)

  async function aoEscolher(evento: ChangeEvent<HTMLInputElement>) {
    const arquivo = evento.target.files?.[0]
    evento.target.value = '' // permite reenviar o mesmo arquivo depois de um erro
    if (!arquivo) return

    // As duas checagens abaixo repetem os limites do backend (RF19/RNF09) para
    // avisar antes de gastar o upload.
    if (!FORMATOS_FOTO.includes(arquivo.type)) {
      aoFalhar('A foto precisa ser JPEG, PNG ou WebP.')
      return
    }
    if (arquivo.size > TAMANHO_MAXIMO_FOTO) {
      aoFalhar('A foto passa de 5 MB. Escolha uma imagem menor.')
      return
    }

    setEnviando(true)
    try {
      aoEnviar(await pets.enviarFoto(petId, arquivo))
    } catch (problema) {
      aoFalhar(problema instanceof ErroApi ? problema.mensagemDeTela() : 'Falha ao enviar a foto.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="pilha-3">
      <input
        ref={entrada}
        type="file"
        accept={FORMATOS_FOTO.join(',')}
        className="so-leitor-tela"
        onChange={aoEscolher}
      />
      <button
        type="button"
        className="botao"
        data-tipo="contorno"
        disabled={enviando}
        onClick={() => entrada.current?.click()}
      >
        {enviando ? 'Enviando…' : temFoto ? 'Trocar foto' : 'Enviar foto'}
      </button>
      <p className="texto-fraco">JPEG, PNG ou WebP, até 5 MB.</p>
    </div>
  )
}

/* --- Formularios de edicao ---------------------------------------------- */

interface FormProps {
  pet: Pet
  aoSalvar: (pet: Pet) => void
  aoFalhar: (problema: unknown) => void
  aoCancelar: () => void
}

function FormularioDados({ pet, aoSalvar, aoFalhar, aoCancelar }: FormProps) {
  const [nome, setNome] = useState(pet.nome)
  const [especie, setEspecie] = useState<EspeciePet>(pet.especie)
  const [idade, setIdade] = useState(String(pet.idade))
  const [dataResgate, setDataResgate] = useState(pet.data_resgate)
  const [salvando, setSalvando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setSalvando(true)
    try {
      aoSalvar(
        await pets.atualizar(pet.id, {
          nome: nome.trim(),
          especie,
          idade: Number(idade),
          data_resgate: dataResgate,
        }),
      )
    } catch (problema) {
      aoFalhar(problema)
      setSalvando(false)
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <Campo
        rotulo="Nome"
        required
        maxLength={100}
        value={nome}
        onChange={(e) => setNome(e.target.value)}
      />
      <div className="formulario-duplo">
        <CampoSelecao
          rotulo="Espécie"
          value={especie}
          onChange={(e) => setEspecie(e.target.value as EspeciePet)}
        >
          {opcoesDe(ESPECIES)}
        </CampoSelecao>
        <Campo
          rotulo="Idade"
          type="number"
          min={0}
          max={40}
          required
          value={idade}
          onChange={(e) => setIdade(e.target.value)}
        />
      </div>
      <Campo
        rotulo="Data do resgate"
        type="date"
        required
        value={dataResgate}
        onChange={(e) => setDataResgate(e.target.value)}
      />
      <div className="acoes">
        <button type="submit" className="botao" disabled={salvando}>
          {salvando ? 'Salvando…' : 'Salvar dados'}
        </button>
        <button type="button" className="botao" data-tipo="texto" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

function FormularioSaude({ pet, aoSalvar, aoFalhar, aoCancelar }: FormProps) {
  const [status, setStatus] = useState<StatusSaudePet>(pet.status_saude)
  const [doenca, setDoenca] = useState(pet.doenca_atual ?? '')
  const [erroDoenca, setErroDoenca] = useState<string | undefined>()
  const [salvando, setSalvando] = useState(false)

  const exigeDoenca = status === 'em_tratamento_medico'

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setErroDoenca(undefined)

    if (exigeDoenca && !doenca.trim()) {
      setErroDoenca('Informe qual doença está sendo tratada.')
      return
    }

    setSalvando(true)
    try {
      aoSalvar(
        await pets.atualizarStatusSaude(pet.id, {
          status_saude: status,
          doenca_atual: exigeDoenca ? doenca.trim() : null,
        }),
      )
    } catch (problema) {
      aoFalhar(problema)
      setSalvando(false)
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <CampoSelecao
        rotulo="Estado de saúde"
        value={status}
        onChange={(e) => setStatus(e.target.value as StatusSaudePet)}
      >
        {opcoesDe(STATUS_SAUDE)}
      </CampoSelecao>

      {exigeDoenca ? (
        <Campo
          rotulo="Doença em tratamento"
          required
          maxLength={255}
          value={doenca}
          erro={erroDoenca}
          onChange={(e) => setDoenca(e.target.value)}
        />
      ) : null}

      <div className="acoes">
        <button type="submit" className="botao" disabled={salvando}>
          {salvando ? 'Salvando…' : 'Salvar ficha médica'}
        </button>
        <button type="button" className="botao" data-tipo="texto" onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

/* --- Processos deste pet ------------------------------------------------ */

function ProcessosDoPet({ petId }: { petId: number }) {
  const { dados, carregando } = useRequisicao(
    () =>
      Promise.all([
        apiProcessos.listar({ pet_id: petId, tamanho_pagina: 50 }),
        apiAdotantes.listar(1, 100),
      ]),
    [petId],
  )

  if (carregando) return <Carregando texto="Buscando processos…" />
  if (!dados) return null

  const [lista, pessoas] = dados
  const nomePorId = new Map(pessoas.itens.map((pessoa) => [pessoa.id, pessoa.nome]))

  return (
    <section className="ficha">
      <div className="ficha-corpo">
        <div className="secao-titulo">
          <h2>Processos de adoção</h2>
          <Link to="/adocoes" className="texto-fraco">
            Ver todos
          </Link>
        </div>

        {lista.itens.length === 0 ? (
          <p className="texto-fraco">Este pet ainda não teve nenhum processo de adoção aberto.</p>
        ) : (
          <div className="lista-atencao">
            {lista.itens.map((processo) => (
              <div key={processo.id} className="item-atencao">
                <span>
                  <span className="item-atencao-nome">
                    {nomePorId.get(processo.adotante_id) ?? `Adotante #${processo.adotante_id}`}
                  </span>
                  <span className="item-atencao-detalhe">
                    aberto em {formatarData(processo.criado_em)}
                  </span>
                </span>
                <span className="item-atencao-fim">
                  <Selo tom={TOM_PROCESSO[processo.status]}>
                    {STATUS_PROCESSO[processo.status]}
                  </Selo>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

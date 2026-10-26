/** Moldura do painel: trilho de navegacao + area de conteudo. */

import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/ContextoAuth'
import { PERFIS } from '../util/formato'

const TRABALHO_DIARIO = [
  { para: '/', rotulo: 'Painel', fim: true },
  { para: '/pets', rotulo: 'Pets', fim: false },
  { para: '/vacinas', rotulo: 'Vacinas', fim: false },
  { para: '/adocoes', rotulo: 'Adoções', fim: false },
  { para: '/adotantes', rotulo: 'Adotantes', fim: false },
  { para: '/padrinhos', rotulo: 'Padrinhos', fim: false },
  { para: '/contribuicoes', rotulo: 'Contribuições', fim: false },
  { para: '/doacoes', rotulo: 'Doações', fim: false },
  { para: '/gastos', rotulo: 'Gastos', fim: false },
]

// O veterinario nao ve cadastros de pessoas nem adocoes: a API responde 403 a ele.
const TRABALHO_CLINICO = [
  { para: '/', rotulo: 'Início', fim: true },
  { para: '/pets', rotulo: 'Pets', fim: false },
  { para: '/vacinas', rotulo: 'Vacinas', fim: false },
]

export function Layout() {
  const { email, usuario, ehAdmin, ehVeterinario, sair } = useAuth()
  const itens = ehVeterinario ? TRABALHO_CLINICO : TRABALHO_DIARIO

  return (
    <div className="app">
      <nav className="trilho" aria-label="Navegação principal">
        <NavLink to="/" className="trilho-marca">
          Pet<em>Meet</em>
        </NavLink>
        <p className="trilho-ong">{ehVeterinario ? 'Área clínica' : 'Painel da equipe'}</p>

        <div className="trilho-nav">
          {itens.map((item) => (
            <NavLink key={item.para} to={item.para} end={item.fim} className="trilho-link">
              {item.rotulo}
            </NavLink>
          ))}
          <hr className="trilho-divisor" />
          {/* Todos os perfis: e a mesma pagina publica que qualquer visitante ve (H11). */}
          <NavLink to="/transparencia" className="trilho-link">
            Prestação de contas
          </NavLink>
          {/* A linha separa o trabalho do dia a dia da administracao da equipe, que so o
              admin faz (POST /usuarios exige perfil admin). */}
          {ehAdmin ? (
            <>
              <hr className="trilho-divisor" />
              <NavLink to="/equipe" className="trilho-link">
                Equipe
              </NavLink>
            </>
          ) : null}
        </div>

        <div className="trilho-rodape">
          <p className="trilho-usuario">
            {usuario ? `${usuario.nome} · ${PERFIS[usuario.perfil]}` : email}
          </p>
          <button type="button" className="trilho-sair" onClick={sair}>
            Sair
          </button>
        </div>
      </nav>

      <main className="conteudo">
        <div className="conteudo-largura">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

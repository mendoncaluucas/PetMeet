/** Moldura do painel: trilho de navegacao + area de conteudo. */

import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/ContextoAuth'
import { PERFIS } from '../util/formato'

const TRABALHO_DIARIO = [
  { para: '/', rotulo: 'Painel', fim: true },
  { para: '/pets', rotulo: 'Pets', fim: false },
  { para: '/adocoes', rotulo: 'Adoções', fim: false },
  { para: '/adotantes', rotulo: 'Adotantes', fim: false },
  { para: '/padrinhos', rotulo: 'Padrinhos', fim: false },
  { para: '/doacoes', rotulo: 'Doações', fim: false },
]

export function Layout() {
  const { email, usuario, ehAdmin, sair } = useAuth()

  return (
    <div className="app">
      <nav className="trilho" aria-label="Navegação principal">
        <NavLink to="/" className="trilho-marca">
          Pet<em>Meet</em>
        </NavLink>
        <p className="trilho-ong">Painel da equipe</p>

        <div className="trilho-nav">
          {TRABALHO_DIARIO.map((item) => (
            <NavLink key={item.para} to={item.para} end={item.fim} className="trilho-link">
              {item.rotulo}
            </NavLink>
          ))}
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

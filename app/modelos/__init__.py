"""Importa todos os modelos para que o Alembic (autogenerate) e o Base.metadata os enxerguem."""

from app.modelos.adotante import Adotante
from app.modelos.apadrinhamento import Apadrinhamento
from app.modelos.atendimento_clinico import AtendimentoClinico
from app.modelos.doacao import Doacao
from app.modelos.log_auditoria import LogAuditoria
from app.modelos.padrinho import Padrinho
from app.modelos.pet import Pet
from app.modelos.processo_adocao import ProcessoAdocao
from app.modelos.usuario import Usuario
from app.modelos.vacina import AplicacaoVacina, Vacina

__all__ = [
    "Adotante",
    "AplicacaoVacina",
    "AtendimentoClinico",
    "Apadrinhamento",
    "Doacao",
    "LogAuditoria",
    "Padrinho",
    "Pet",
    "ProcessoAdocao",
    "Usuario",
    "Vacina",
]

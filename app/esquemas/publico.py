"""Schemas do portal publico de prestacao de contas (fase 3, H11).

A rota e aberta, sem login. Estes schemas nao herdam dos internos de proposito: um campo
novo num schema interno nunca vaza para o portal. Fica de fora tudo o que identifica
pessoa (A-11, D15): nome e CPF de padrinho, nome de doador avulso, descricao de gasto,
id de padrinho e quem registrou. Nome de pet pode aparecer.
"""

from decimal import Decimal

from pydantic import BaseModel

from app.modelos.enums import CategoriaGasto


class GastoDaCategoria(BaseModel):
    categoria: CategoriaGasto
    valor: Decimal


class MesDoPortal(BaseModel):
    """Um mes do portal. O estorno conta no mes em que foi feito (D13)."""

    mes: str
    em_andamento: bool
    arrecadado: Decimal
    gasto: Decimal
    saldo: Decimal
    saldo_acumulado: Decimal
    gastos_por_categoria: list[GastoDaCategoria]


class PetDoPortal(BaseModel):
    """Arrecadado com destino ao pet e gasto com ele, no periodo do portal."""

    pet_id: int
    nome: str
    arrecadado: Decimal
    gasto: Decimal


class PortalTransparencia(BaseModel):
    """Ultimos 12 meses, do mais recente para o mais antigo."""

    mes_inicial: str
    mes_final: str
    arrecadado_no_periodo: Decimal
    gasto_no_periodo: Decimal
    saldo_acumulado: Decimal
    meses: list[MesDoPortal]
    pets: list[PetDoPortal]

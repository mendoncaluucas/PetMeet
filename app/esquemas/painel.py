"""Schema do resumo do Painel (DEF-09, DEF-10)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.modelos.enums import StatusProcessoAdocao, StatusSaudePet


class PetResumido(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    status_saude: StatusSaudePet
    doenca_atual: str | None
    data_resgate: date


class ProcessoResumido(BaseModel):
    id: int
    status: StatusProcessoAdocao
    pet_id: int
    pet_nome: str
    pet_status_saude: StatusSaudePet
    adotante_id: int
    adotante_nome: str


class ResumoPainel(BaseModel):
    """Contagens e total do mes vem do banco inteiro; as listas sao curtas e ja ordenadas."""

    pets_total: int
    pets_disponiveis: int
    pets_em_tratamento: int
    processos_em_andamento: int
    processos_aguardando_finalizacao: int
    mes_de_referencia: str
    doacoes_do_mes_total: Decimal
    doacoes_do_mes_quantidade: int
    em_tratamento: list[PetResumido]
    em_andamento: list[ProcessoResumido]
    esperando_ha_mais_tempo: list[PetResumido]

"""Schemas do processo de adocao (RF14-18)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modelos.enums import StatusProcessoAdocao


class ProcessoAdocaoCriar(BaseModel):
    pet_id: int
    adotante_id: int


class ProcessoAdocaoAtualizarStatus(BaseModel):
    # acompanhamento_medico_em_dia saiu daqui: pet em tratamento nao finaliza, com ou sem
    # ele (decisao D1). Quem ainda envia o campo nao recebe erro -- campo extra e ignorado.
    status: StatusProcessoAdocao


class ProcessoAdocaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    adotante_id: int
    responsavel_id: int | None
    status: StatusProcessoAdocao
    # Historico: processos finalizados antes da decisao D1 podem ter o valor True.
    acompanhamento_medico_em_dia: bool
    criado_em: datetime
    atualizado_em: datetime

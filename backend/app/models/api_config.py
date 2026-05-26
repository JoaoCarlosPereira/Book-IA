from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.models.base import Base


class ApiConfig(Base):
    __tablename__ = "api_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(String(20), nullable=False)
    modo = Column(String(10), nullable=False)
    url = Column(String(500), nullable=False)
    token = Column(String(500))
    modelo = Column(String(200))
    ativo = Column(Boolean, nullable=False, server_default="true")
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ApiConfig(id={self.id}, tipo='{self.tipo}', modo='{self.modo}', url='{self.url}')>"

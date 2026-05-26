from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.models.base import Base


class Arquivo(Base):
    __tablename__ = "arquivo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    livro_id = Column(Integer, ForeignKey("livro.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(20), nullable=False)
    caminho = Column(String(1000), nullable=False)
    tamanho_bytes = Column(BigInteger)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Arquivo(id={self.id}, tipo='{self.tipo}', caminho='{self.caminho}')>"

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.models.base import Base


class Pagina(Base):
    __tablename__ = "pagina"

    id = Column(Integer, primary_key=True, autoincrement=True)
    livro_id = Column(Integer, ForeignKey("livro.id", ondelete="CASCADE"), nullable=False)
    numero = Column(Integer, nullable=False)
    texto = Column(String, nullable=False)
    processado = Column(Boolean, nullable=False, server_default="false")
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("livro_id", "numero", name="uq_pagina_livro_numero"),
    )

    def __repr__(self):
        return f"<Pagina(id={self.id}, livro_id={self.livro_id}, numero={self.numero})>"

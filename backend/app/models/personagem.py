from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.models.base import Base


class Personagem(Base):
    __tablename__ = "personagem"

    id = Column(Integer, primary_key=True, autoincrement=True)
    livro_id = Column(Integer, ForeignKey("livro.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(200), nullable=False)
    nome_original = Column(String(200))
    genero = Column(String(20))
    idade = Column(String(20))
    is_narrador = Column(Boolean, nullable=False, server_default="false")
    voz_id = Column(Integer, ForeignKey("voz.id", ondelete="SET NULL"))
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Personagem(id={self.id}, nome='{self.nome}', genero='{self.genero}')>"

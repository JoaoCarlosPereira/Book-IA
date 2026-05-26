from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.models.base import Base


class Fala(Base):
    __tablename__ = "falas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    livro_id = Column(Integer, ForeignKey("livro.id", ondelete="CASCADE"), nullable=False)
    pagina_id = Column(Integer, ForeignKey("pagina.id", ondelete="SET NULL"))
    personagem_id = Column(Integer, ForeignKey("personagem.id", ondelete="SET NULL"))
    texto = Column(Text, nullable=False)
    processado = Column(Boolean, nullable=False, server_default="false")
    arquivo_id = Column(Integer, ForeignKey("arquivo.id", ondelete="SET NULL"))
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Fala(id={self.id}, personagem_id={self.personagem_id}, processado={self.processado})>"

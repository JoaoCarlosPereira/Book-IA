from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.models.base import Base


class Capitulo(Base):
    __tablename__ = "capitulo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    livro_id = Column(Integer, ForeignKey("livro.id", ondelete="CASCADE"), nullable=False)
    numero = Column(Integer, nullable=False)
    titulo = Column(String(500), nullable=False)
    pagina_inicio = Column(Integer)
    pagina_fim = Column(Integer)
    caminho_audio = Column(String(1000))
    duracao_estimada = Column(Integer)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return "<Capitulo(id=%s, numero=%s, titulo=%r)>" % (self.id, self.numero, self.titulo)

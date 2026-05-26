from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.models.base import Base


class BookTask(Base):
    __tablename__ = "book_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    livro_id = Column(Integer, ForeignKey("livro.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False)
    prioridade = Column(Integer, nullable=False, server_default="5")
    progresso = Column(Integer, nullable=False, server_default="0")
    etapa_atual = Column(String(100))
    celery_task_id = Column(String(255))
    erro = Column(Text)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<BookTask(id={self.id}, livro_id={self.livro_id}, status='{self.status}')>"

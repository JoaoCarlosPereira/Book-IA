from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.models.base import Base


class BookReview(Base):
    __tablename__ = "book_review"

    id = Column(Integer, primary_key=True, autoincrement=True)
    livro_id = Column(Integer, ForeignKey("livro.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"))
    personagem_id = Column(Integer, ForeignKey("personagem.id", ondelete="SET NULL"))
    acao = Column(String(20), nullable=False)
    observacao = Column(Text)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<BookReview(id={self.id}, livro_id={self.livro_id}, acao='{self.acao}')>"

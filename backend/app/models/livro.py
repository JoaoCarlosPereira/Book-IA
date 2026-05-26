from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, func
from app.models.base import Base


class Livro(Base):
    __tablename__ = "livro"

    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(500), nullable=False)
    nome_arquivo = Column(String(500), nullable=False)
    tipo_documento = Column(String(10), nullable=False)
    nivel_producao = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, server_default="pendente")
    progresso = Column(Integer, nullable=False, server_default="0")
    caminho_pdf = Column(String(1000))
    caminho_audio = Column(String(1000))
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        {"schema": None},
    )

    def __repr__(self):
        return f"<Livro(id={self.id}, titulo='{self.titulo}', status='{self.status}')>"

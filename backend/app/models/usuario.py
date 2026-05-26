from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

from app.models.base import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(String(100), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    perfil = Column(String(20), nullable=False, server_default="usuario")
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Usuario(id={self.id}, login='{self.login}', perfil='{self.perfil}')>"

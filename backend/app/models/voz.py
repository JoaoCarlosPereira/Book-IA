from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class Voz(Base):
    __tablename__ = "voz"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(200), nullable=False)
    genero = Column(String(20), nullable=False)
    idade = Column(String(20), nullable=False)

    def __repr__(self):
        return f"<Voz(id={self.id}, nome='{self.nome}', genero='{self.genero}', idade='{self.idade}')>"

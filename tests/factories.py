"""factory_boy factories for Book-IA SQLAlchemy models."""

from __future__ import annotations

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.api_config import ApiConfig
from app.models.arquivo import Arquivo
from app.models.book_review import BookReview
from app.models.book_task import BookTask
from app.models.falas import Fala
from app.models.livro import Livro
from app.models.pagina import Pagina
from app.models.personagem import Personagem
from app.models.usuario import Usuario
from app.models.voz import Voz
from app.services.auth_service import hash_password


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory; use .build() or attach sqlalchemy session for persistence."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class UsuarioFactory(BaseFactory):
    class Meta:
        model = Usuario

    login = factory.Sequence(lambda n: f"usuario{n}")
    senha_hash = factory.LazyFunction(lambda: hash_password("senha123"))
    perfil = "usuario"


class LivroFactory(BaseFactory):
    class Meta:
        model = Livro

    titulo = factory.Sequence(lambda n: f"Livro Teste {n}")
    nome_arquivo = factory.LazyAttribute(lambda o: f"{o.titulo.replace(' ', '_').lower()}.pdf")
    tipo_documento = "pdf"
    nivel_producao = "basico"
    status = "pendente"
    progresso = 0
    usuario_id = 1


class PaginaFactory(BaseFactory):
    class Meta:
        model = Pagina

    livro_id = 1
    numero = factory.Sequence(lambda n: n + 1)
    texto = factory.Faker("paragraph", locale="pt_BR")
    processado = False


class VozFactory(BaseFactory):
    class Meta:
        model = Voz

    nome = factory.Sequence(lambda n: f"Voz {n}")
    genero = "masculino"
    idade = "adulto"


class PersonagemFactory(BaseFactory):
    class Meta:
        model = Personagem

    livro_id = 1
    nome = factory.Faker("first_name", locale="pt_BR")
    genero = "neutro"
    idade = "adulto"
    is_narrador = False
    voz_id = None


class ApiConfigFactory(BaseFactory):
    class Meta:
        model = ApiConfig

    tipo = "llm"
    modo = "cloud"
    url = "https://generativelanguage.googleapis.com"
    token = "encrypted-token-placeholder"
    modelo = "gemini-2.0-flash"
    ativo = True


class BookTaskFactory(BaseFactory):
    class Meta:
        model = BookTask

    livro_id = 1
    status = "pendente"
    prioridade = 5
    progresso = 0
    etapa_atual = "extracao"


class ArquivoFactory(BaseFactory):
    class Meta:
        model = Arquivo

    livro_id = 1
    tipo = "mp3"
    caminho = factory.LazyAttribute(
        lambda o: f"/tmp/book-ia/{o.livro_id}/audio/parte_001.mp3"
    )
    tamanho_bytes = 1024


class FalaFactory(BaseFactory):
    class Meta:
        model = Fala

    livro_id = 1
    pagina_id = None
    personagem_id = None
    texto = factory.Faker("sentence", locale="pt_BR")
    processado = False


class BookReviewFactory(BaseFactory):
    class Meta:
        model = BookReview

    livro_id = 1
    usuario_id = 1
    personagem_id = None
    acao = "aprovar"
    observacao = None


async def persist(session, factory_instance: SQLAlchemyModelFactory, **kwargs):
    """Build a model instance and persist it in an async SQLAlchemy session."""
    obj = factory_instance.build(**kwargs)
    session.add(obj)
    await session.flush()
    return obj

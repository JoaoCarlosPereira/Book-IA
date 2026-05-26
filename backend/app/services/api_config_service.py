"""CRUD and connection testing for API configurations."""

import time
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.api_config import ApiConfig
from app.schemas.api_config import (
    VALID_MODOS,
    VALID_TIPOS,
    ApiConfigCreate,
    ApiConfigTestResponse,
    ApiConfigUpdate,
)

TOKEN_MASK = "***"
_TEST_TIMEOUT = 10.0


def _fernet() -> Fernet:
    return Fernet(settings.fernet_encryption_key)


def encrypt_token(plain: str) -> str:
    """Encrypt a token for storage."""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a stored token."""
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Token criptografado inválido") from exc


def mask_token(stored: str | None) -> str | None:
    """Return masked token for API responses."""
    if stored:
        return TOKEN_MASK
    return None


def _validate_tipo_modo(tipo: str, modo: str) -> None:
    if tipo not in VALID_TIPOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"tipo deve ser um de: {', '.join(sorted(VALID_TIPOS))}",
        )
    if modo not in VALID_MODOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"modo deve ser um de: {', '.join(sorted(VALID_MODOS))}",
        )


def _to_response_dict(row: ApiConfig) -> dict[str, Any]:
    return {
        "id": row.id,
        "tipo": row.tipo,
        "modo": row.modo,
        "url": row.url,
        "token": mask_token(row.token),
        "modelo": row.modelo,
        "ativo": row.ativo,
        "criado_em": row.criado_em,
        "atualizado_em": row.atualizado_em,
    }


class ApiConfigService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_configs(self, incluir_inativos: bool = False) -> list[ApiConfig]:
        stmt = select(ApiConfig).order_by(ApiConfig.id)
        if not incluir_inativos:
            stmt = stmt.where(ApiConfig.ativo.is_(True))
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, config_id: int) -> ApiConfig:
        row = await self._db.get(ApiConfig, config_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuração não encontrada")
        return row

    async def create(self, data: ApiConfigCreate) -> ApiConfig:
        _validate_tipo_modo(data.tipo, data.modo)
        encrypted = encrypt_token(data.token) if data.token else None
        row = ApiConfig(
            tipo=data.tipo,
            modo=data.modo,
            url=data.url,
            token=encrypted,
            modelo=data.modelo,
            ativo=data.ativo,
        )
        self._db.add(row)
        await self._db.flush()
        await self._db.refresh(row)
        return row

    async def update(self, config_id: int, data: ApiConfigUpdate) -> ApiConfig:
        row = await self.get_by_id(config_id)
        payload = data.model_dump(exclude_unset=True)
        token_plain = payload.pop("token", None)

        if "tipo" in payload or "modo" in payload:
            _validate_tipo_modo(
                payload.get("tipo", row.tipo),
                payload.get("modo", row.modo),
            )

        for key, value in payload.items():
            setattr(row, key, value)

        if token_plain is not None:
            row.token = encrypt_token(token_plain) if token_plain else None

        await self._db.flush()
        await self._db.refresh(row)
        return row

    async def soft_delete(self, config_id: int) -> ApiConfig:
        row = await self.get_by_id(config_id)
        row.ativo = False
        await self._db.flush()
        await self._db.refresh(row)
        return row

    async def test_connection(self, config_id: int) -> ApiConfigTestResponse:
        row = await self.get_by_id(config_id)
        return await probe_url_connection(row.url)


async def probe_url_connection(url: str) -> ApiConfigTestResponse:
    """Perform a real HTTP request to the configured URL."""
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(url)
        latencia_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code < 500:
            return ApiConfigTestResponse(conectado=True, latencia_ms=latencia_ms)
        return ApiConfigTestResponse(
            conectado=False,
            latencia_ms=latencia_ms,
            erro=f"HTTP {response.status_code}",
        )
    except httpx.RequestError as exc:
        return ApiConfigTestResponse(conectado=False, erro=str(exc))

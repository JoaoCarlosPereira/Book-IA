"""Configurações de API routes (v1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.deps import get_db, require_auth
from app.htmx import wants_html_partial
from app.schemas.api_config import (
    ApiConfigCreate,
    ApiConfigResponse,
    ApiConfigTestResponse,
    ApiConfigUpdate,
)
from app.services.api_config_service import ApiConfigService, _to_response_dict
from app.templating import templates

router = APIRouter(
    prefix="/configuracoes/apis",
    tags=["configuracoes"],
    dependencies=[Depends(require_auth)],
)


def _service(db: AsyncSession) -> ApiConfigService:
    return ApiConfigService(db)


@router.get("", response_model=list[ApiConfigResponse])
async def listar_apis(
    db: Annotated[AsyncSession, Depends(get_db)],
    incluir_inativos: bool = Query(default=False),
) -> list[ApiConfigResponse]:
    rows = await _service(db).list_configs(incluir_inativos=incluir_inativos)
    return [ApiConfigResponse(**_to_response_dict(r)) for r in rows]


@router.post("", response_model=ApiConfigResponse, status_code=status.HTTP_201_CREATED)
async def criar_api(
    body: ApiConfigCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiConfigResponse:
    row = await _service(db).create(body)
    return ApiConfigResponse(**_to_response_dict(row))


@router.put("/{config_id}", response_model=ApiConfigResponse)
async def atualizar_api(
    config_id: int,
    body: ApiConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiConfigResponse:
    row = await _service(db).update(config_id, body)
    return ApiConfigResponse(**_to_response_dict(row))


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_api(
    config_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await _service(db).soft_delete(config_id)


@router.post("/{config_id}/testar", response_model=ApiConfigTestResponse)
async def testar_api(
    request: Request,
    config_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiConfigTestResponse | Response:
    result = await _service(db).test_connection(config_id)
    if wants_html_partial(request):
        return templates.TemplateResponse(
            request=request,
            name="partials/test_result.html",
            context={
                "request": request,
                "conectado": result.conectado,
                "latencia_ms": result.latencia_ms,
                "erro": result.erro,
            },
        )
    return result

"""MusicGen soundtrack generation: atmospheric prompt via LLM and MusicGen API."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.api_config import ApiConfig
from app.models.arquivo import Arquivo
from app.services.api_config_service import decrypt_token
from app.services.ia_analyzer import IAAnalyzer, IAAnalyzerError

logger = logging.getLogger(__name__)

MUSICGEN_ENDPOINT = "generate-from-text"
MAX_RETRIES = 3
BACKOFF_SECONDS = (1.0, 2.0, 4.0)
DURACAO_LIMITE_PAGINA = 300

_NIVEIS_COM_TRILHA = frozenset({"avancado", "profissional"})


class MusicGenError(Exception):
    """Base error for MusicGen operations."""


class MusicGenAPIError(MusicGenError):
    """Raised when the MusicGen API fails after retries."""


class MusicGenPromptError(MusicGenError):
    """Raised when the atmospheric prompt cannot be generated."""


@dataclass(frozen=True)
class PaginaExcerto:
    """Page excerpt with optional timing for atmospheric prompt context."""

    numero: int
    texto: str
    tempo_inicio: int = 0
    tempo_fim: int = 0


def _sanitizar_nome(nome: str) -> str:
    limpo = re.sub(r"[^\w\-]+", "_", nome.strip(), flags=re.UNICODE)
    return limpo or "livro"


def _formatar_faixa_tempo(tempo_inicio: int, tempo_fim: int) -> str:
    from app.services.ia_analyzer import _formatar_tempo

    return f" [{_formatar_tempo(tempo_inicio)} - {_formatar_tempo(tempo_fim)}]"


def _montar_excerto_paginas(paginas: Sequence[PaginaExcerto]) -> str:
    linhas: list[str] = []
    for pagina in paginas:
        faixa = ""
        if pagina.tempo_fim > pagina.tempo_inicio:
            faixa = _formatar_faixa_tempo(pagina.tempo_inicio, pagina.tempo_fim)
        linhas.append(f"{pagina.texto.strip()}{faixa}")
    return "\n".join(linhas)


class MusicGenService:
    """Generates instrumental soundtracks via LLM prompt + MusicGen API."""

    def __init__(
        self,
        api_url: str,
        api_key: str | None = None,
        *,
        ia_analyzer: IAAnalyzer | None = None,
        timeout: float | None = None,
        audio_dir: str | Path | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.ia_analyzer = ia_analyzer
        self.timeout = float(timeout if timeout is not None else settings.musicgen_timeout)
        self.audio_dir = Path(audio_dir or settings.audio_dir)
        self._http_client = http_client
        self._owns_client = http_client is None
        self._owns_analyzer = ia_analyzer is None

    @classmethod
    async def from_db(
        cls,
        db: AsyncSession,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> MusicGenService:
        """Build service from active ``api_config`` (tipo=musicgen) and LLM analyzer."""
        stmt = (
            select(ApiConfig)
            .where(ApiConfig.tipo == "musicgen", ApiConfig.ativo.is_(True))
            .order_by(ApiConfig.id)
            .limit(1)
        )
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        api_url = settings.musicgen_api_url
        api_key: str | None = None
        if config is not None:
            api_url = config.url.rstrip("/")
            if config.token:
                api_key = decrypt_token(config.token)

        analyzer = await IAAnalyzer.from_db(db, client=http_client)
        return cls(
            api_url,
            api_key,
            ia_analyzer=analyzer,
            http_client=http_client,
        )

    async def aclose(self) -> None:
        if self._owns_analyzer and self.ia_analyzer is not None:
            await self.ia_analyzer.aclose()
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> MusicGenService:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            headers: dict[str, str] = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
                follow_redirects=True,
            )
        return self._http_client

    def _headers_auth(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    def _caminho_saida(
        self,
        nome_livro: str,
        *,
        numero_pagina: int | None = None,
    ) -> Path:
        base = self.audio_dir / _sanitizar_nome(nome_livro) / "partes"
        if numero_pagina is not None:
            return base / f"Trilha_Pag_{numero_pagina}.wav"
        return base / "Trilha.wav"

    async def _gerar_prompt_atmosferico(
        self,
        texto_excerpto: str,
        tempo_inicio: int = 0,
        tempo_fim: int = 0,
    ) -> str:
        if self.ia_analyzer is None:
            raise MusicGenPromptError("IA Analyzer não configurado")
        try:
            return await self.ia_analyzer.gerar_prompt_atmosferico(
                texto_excerpto,
                tempo_inicio,
                tempo_fim,
            )
        except IAAnalyzerError as exc:
            raise MusicGenPromptError(str(exc)) from exc

    async def _chamar_musicgen(self, prompt: str, output_path: Path) -> Path:
        """POST prompt to MusicGen API and persist WAV at *output_path*."""
        url = urljoin(f"{self.api_url}/", MUSICGEN_ENDPOINT)
        payload = {
            "prompt": prompt,
            "output": str(output_path),
        }

        last_error: Exception | None = None
        for tentativa in range(MAX_RETRIES):
            try:
                response = await self._client().post(
                    url,
                    json=payload,
                    headers=self._headers_auth(),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return await self._resolver_wav_resposta(response, output_path)
            except (httpx.HTTPError, MusicGenAPIError) as exc:
                last_error = exc
                if tentativa < MAX_RETRIES - 1:
                    await asyncio.sleep(BACKOFF_SECONDS[tentativa])
                    logger.warning(
                        "MusicGen API falhou (tentativa %d/%d): %s",
                        tentativa + 1,
                        MAX_RETRIES,
                        exc,
                    )
                else:
                    break

        raise MusicGenAPIError(
            f"MusicGen API indisponível após {MAX_RETRIES} tentativas: {last_error}"
        ) from last_error

    async def _resolver_wav_resposta(
        self,
        response: httpx.Response,
        destino: Path,
    ) -> Path:
        content_type = response.headers.get("content-type", "").lower()

        if "audio" in content_type:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(response.content)
            return destino

        try:
            data: dict[str, Any] = response.json()
        except json.JSONDecodeError as exc:
            raise MusicGenAPIError("Resposta MusicGen inválida (não é JSON nem áudio)") from exc

        status = str(data.get("status", "")).lower()
        if status and status != "success":
            raise MusicGenAPIError(f"MusicGen API retornou status: {data.get('status')}")

        if data.get("wav_bytes"):
            import base64

            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(base64.b64decode(data["wav_bytes"]))
            return destino

        download_url = (
            data.get("download_url")
            or data.get("wav_url")
            or data.get("url")
        )
        output_path = data.get("output") or data.get("wav_path")

        if download_url:
            return await self._baixar_wav(str(download_url), destino)

        if output_path:
            if str(output_path).startswith(("http://", "https://")):
                return await self._baixar_wav(str(output_path), destino)
            if Path(output_path).exists():
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(Path(output_path).read_bytes())
                return destino
            remoto = urljoin(f"{self.api_url}/", f"files/{str(output_path).lstrip('/')}")
            return await self._baixar_wav(remoto, destino)

        if destino.exists():
            return destino

        raise MusicGenAPIError("Resposta MusicGen sem arquivo de áudio")

    async def _baixar_wav(self, url: str, destino: Path) -> Path:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = urljoin(f"{self.api_url}/", url.lstrip("/"))

        response = await self._client().get(url, timeout=self.timeout)
        response.raise_for_status()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(response.content)
        return destino

    async def _registrar_arquivo(
        self,
        db: AsyncSession,
        livro_id: int,
        caminho: Path,
    ) -> Arquivo:
        tamanho = caminho.stat().st_size if caminho.exists() else None
        row = Arquivo(
            livro_id=livro_id,
            tipo="trilha",
            caminho=str(caminho.resolve()),
            tamanho_bytes=tamanho,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

    async def gerar_trilha(
        self,
        texto_excerpto: str,
        nivel_producao: str,
        tempo_inicio: int = 0,
        tempo_fim: int = 0,
        *,
        livro_id: int | None = None,
        db: AsyncSession | None = None,
        nome_livro: str = "livro",
        numero_pagina: int | None = None,
    ) -> str:
        """
        Generate one soundtrack file and return its path.

        Skips generation for ``nivel_producao="basico"`` (returns empty string).
        """
        if nivel_producao.strip().lower() == "basico":
            return ""

        if nivel_producao.strip().lower() not in _NIVEIS_COM_TRILHA:
            logger.info(
                "Nível de produção %r sem trilha — ignorando MusicGen",
                nivel_producao,
            )
            return ""

        prompt = await self._gerar_prompt_atmosferico(
            texto_excerpto,
            tempo_inicio,
            tempo_fim,
        )
        output_path = self._caminho_saida(nome_livro, numero_pagina=numero_pagina)
        final = await self._chamar_musicgen(prompt, output_path)

        if livro_id is not None and db is not None:
            await self._registrar_arquivo(db, livro_id, final)

        return str(final.resolve())

    async def gerar_trilhas_livro(
        self,
        paginas: Sequence[PaginaExcerto],
        nivel_producao: str,
        duracao_total: int,
        *,
        livro_id: int | None = None,
        db: AsyncSession | None = None,
        nome_livro: str = "livro",
    ) -> list[str]:
        """
        Generate soundtrack(s) for a book.

        When *duracao_total* > 300s, one track per page; otherwise a single track.
        """
        if nivel_producao.strip().lower() == "basico":
            return []

        if not paginas:
            return []

        caminhos: list[str] = []

        if duracao_total > DURACAO_LIMITE_PAGINA:
            for pagina in paginas:
                caminho = await self.gerar_trilha(
                    pagina.texto,
                    nivel_producao,
                    pagina.tempo_inicio,
                    pagina.tempo_fim,
                    livro_id=livro_id,
                    db=db,
                    nome_livro=nome_livro,
                    numero_pagina=pagina.numero,
                )
                if caminho:
                    caminhos.append(caminho)
        else:
            texto = _montar_excerto_paginas(paginas)
            ultima = paginas[-1]
            tempo_fim = ultima.tempo_fim if ultima.tempo_fim > 0 else duracao_total
            caminho = await self.gerar_trilha(
                texto,
                nivel_producao,
                0,
                tempo_fim,
                livro_id=livro_id,
                db=db,
                nome_livro=nome_livro,
            )
            if caminho:
                caminhos.append(caminho)

        return caminhos

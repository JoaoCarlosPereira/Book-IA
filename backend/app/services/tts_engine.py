"""Text-to-speech engine: chunking, TTS API calls, WAV→MP3 conversion, and merge."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.api_config import ApiConfig
from app.models.arquivo import Arquivo
from app.models.voz import Voz
from app.services.api_config_service import decrypt_token

logger = logging.getLogger(__name__)

TTS_ENDPOINT = "generate-from-text"
MAX_RETRIES = 3
BACKOFF_SECONDS = (1, 2, 4)
_SENTENCE_END = frozenset({".", "!", "?", ")"})


class TTSEngineError(Exception):
    """Base error for TTS operations."""


class TTSAPIError(TTSEngineError):
    """Raised when the TTS API fails after retries."""


class TTSConversionError(TTSEngineError):
    """Raised when ffmpeg conversion or merge fails."""


def _normalizar_espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def _extrair_sentencas(texto: str) -> list[str]:
    """Split text on period boundaries (Delphi ExtrairSentencas)."""
    texto = _normalizar_espacos(texto)
    if not texto:
        return []

    sentencas: list[str] = []
    inicio = 0
    for indice, caractere in enumerate(texto):
        if caractere == ".":
            pedaco = texto[inicio : indice + 1].strip()
            if pedaco:
                sentencas.append(pedaco)
            inicio = indice + 1

    resto = texto[inicio:].strip()
    if resto:
        sentencas.append(resto)

    return sentencas if sentencas else [texto]


def _dividir_por_palavras(texto: str, max_chars: int) -> list[str]:
    """Split long text at word boundaries up to max_chars per piece."""
    texto = _normalizar_espacos(texto)
    if not texto:
        return []
    if len(texto) <= max_chars:
        return [texto]

    partes: list[str] = []
    restante = texto
    while restante:
        if len(restante) <= max_chars:
            partes.append(restante)
            break

        corte = max_chars
        espaco = restante.rfind(" ", 0, corte + 1)
        if espaco > 0:
            corte = espaco

        pedaco = restante[:corte].strip()
        if pedaco:
            if partes and len(pedaco) <= 20:
                partes[-1] = f"{partes[-1]} {pedaco}".strip()
            else:
                partes.append(pedaco)

        restante = restante[corte:].strip()

    return partes


def _preparar_chunk_para_tts(chunk: str) -> str:
    """Prepare chunk for TTS API (never send lone '.', use commas for pauses)."""
    texto = _normalizar_espacos(chunk)
    if not texto:
        return texto
    if texto == ".":
        return ","
    texto = texto.replace(".", ",")
    texto = texto.replace(",", " ,")
    if texto and texto[-1] not in _SENTENCE_END and not texto.endswith(","):
        texto = f"{texto},"
    return texto


def chunkar_texto(texto: str, max_chars: int = 180) -> list[str]:
    """
    Split text into TTS-sized chunks.

    Priority: sentence boundaries → character limit → word boundaries.
    """
    texto = _normalizar_espacos(texto)
    if not texto:
        return []
    if len(texto) <= max_chars:
        return [_preparar_chunk_para_tts(texto)]

    sentencas = _extrair_sentencas(texto)
    brutos: list[str] = []
    atual = ""

    for sentenca in sentencas:
        if not atual:
            candidato = sentenca
        else:
            candidato = f"{atual} {sentenca}".strip()

        if len(candidato) <= max_chars:
            atual = candidato
            continue

        if atual:
            brutos.append(atual)

        if len(sentenca) <= max_chars:
            atual = sentenca
        else:
            brutos.extend(_dividir_por_palavras(sentenca, max_chars))
            atual = ""

    if atual:
        brutos.append(atual)

    finais: list[str] = []
    for pedaco in brutos:
        if len(pedaco) <= max_chars:
            finais.append(pedaco)
        else:
            finais.extend(_dividir_por_palavras(pedaco, max_chars))

    return [_preparar_chunk_para_tts(c) for c in finais if c.strip()]


def _sanitizar_nome(nome: str) -> str:
    limpo = re.sub(r"[^\w\-]+", "_", nome.strip(), flags=re.UNICODE)
    return limpo or "personagem"


class TTSEngine:
    """Generates unified MP3 audio from text via an external TTS API."""

    def __init__(
        self,
        api_url: str,
        api_key: str | None = None,
        *,
        timeout: float | None = None,
        audio_dir: str | Path | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = float(timeout if timeout is not None else settings.tts_timeout)
        self.audio_dir = Path(audio_dir or settings.audio_dir)
        self._http_client = http_client
        self._owns_client = http_client is None

    @classmethod
    async def from_api_config(
        cls,
        db: AsyncSession,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> TTSEngine:
        """Build engine from active ``api_config`` row with tipo=tts."""
        stmt = (
            select(ApiConfig)
            .where(ApiConfig.tipo == "tts", ApiConfig.ativo.is_(True))
            .order_by(ApiConfig.id)
            .limit(1)
        )
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        api_url = settings.tts_api_url
        api_key: str | None = None
        if config is not None:
            api_url = config.url.rstrip("/")
            if config.token:
                api_key = decrypt_token(config.token)

        return cls(api_url, api_key, http_client=http_client)

    async def aclose(self) -> None:
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> TTSEngine:
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

    def _chunkar_texto(self, texto: str, max_chars: int = 180) -> list[str]:
        return chunkar_texto(texto, max_chars=max_chars)

    def _headers_auth(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    async def _post_to_tts_api(
        self,
        texto_chunk: str,
        *,
        ref_audio: str,
        output_wav: Path,
    ) -> Path:
        """POST chunk to TTS API and persist WAV locally."""
        url = urljoin(f"{self.api_url}/", TTS_ENDPOINT)
        payload = {
            "input_text": texto_chunk,
            "output": str(output_wav),
            "ref_audio": ref_audio,
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
                return await self._resolver_wav_resposta(response, output_wav)
            except (httpx.HTTPError, TTSAPIError) as exc:
                last_error = exc
                if tentativa < MAX_RETRIES - 1:
                    await asyncio.sleep(BACKOFF_SECONDS[tentativa])
                    logger.warning(
                        "TTS API falhou (tentativa %d/%d): %s",
                        tentativa + 1,
                        MAX_RETRIES,
                        exc,
                    )
                else:
                    break

        raise TTSAPIError(
            f"TTS API indisponível após {MAX_RETRIES} tentativas: {last_error}"
        ) from last_error

    async def _resolver_wav_resposta(
        self,
        response: httpx.Response,
        destino: Path,
    ) -> Path:
        content_type = response.headers.get("content-type", "").lower()

        if "audio" in content_type or destino.suffix.lower() == ".wav":
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(response.content)
            return destino

        try:
            data: dict[str, Any] = response.json()
        except json.JSONDecodeError as exc:
            raise TTSAPIError("Resposta TTS inválida (não é JSON nem áudio)") from exc

        status = str(data.get("status", "")).lower()
        if status and status != "success":
            raise TTSAPIError(f"TTS API retornou status: {data.get('status')}")

        if data.get("wav_bytes"):
            destino.parent.mkdir(parents=True, exist_ok=True)
            import base64

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
            remoto = urljoin(f"{self.api_url}/", f"files/{output_path.lstrip('/')}")
            return await self._baixar_wav(remoto, destino)

        raise TTSAPIError("Resposta TTS sem arquivo de áudio")

    async def _baixar_wav(self, url: str, destino: Path) -> Path:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = urljoin(f"{self.api_url}/", url.lstrip("/"))

        response = await self._client().get(url, timeout=self.timeout)
        response.raise_for_status()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(response.content)
        return destino

    def _converter_wav_para_mp3(self, wav_path: Path) -> Path:
        mp3_path = wav_path.with_suffix(".mp3")
        self._executar_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(mp3_path),
            ]
        )
        return mp3_path

    def _unificar_arquivos(self, arquivos_mp3: list[Path], destino: Path) -> Path:
        if not arquivos_mp3:
            raise TTSConversionError("Nenhum arquivo MP3 para unificar")
        if len(arquivos_mp3) == 1:
            destino.parent.mkdir(parents=True, exist_ok=True)
            if arquivos_mp3[0] != destino:
                destino.write_bytes(arquivos_mp3[0].read_bytes())
            return destino

        destino.parent.mkdir(parents=True, exist_ok=True)
        lista = destino.parent / f"concat_{uuid.uuid4().hex}.txt"
        try:
            linhas = []
            for arquivo in arquivos_mp3:
                caminho = str(arquivo.resolve()).replace("'", "'\\''")
                linhas.append(f"file '{caminho}'")
            lista.write_text("\n".join(linhas) + "\n", encoding="utf-8")

            self._executar_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(lista),
                    "-c",
                    "copy",
                    str(destino),
                ]
            )
        finally:
            if lista.exists():
                lista.unlink()

        return destino

    @staticmethod
    def _executar_ffmpeg(comando: list[str]) -> None:
        try:
            resultado = subprocess.run(
                comando,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise TTSConversionError("ffmpeg não encontrado no PATH") from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or ""
            raise TTSConversionError(f"ffmpeg falhou: {stderr.strip()}") from exc
        else:
            if resultado.returncode != 0:
                raise TTSConversionError(
                    f"ffmpeg retornou código {resultado.returncode}"
                )

    async def _resolver_ref_audio(
        self,
        voz_id: int | None,
        db: AsyncSession | None,
    ) -> str:
        if voz_id is None or db is None:
            return ""
        voz = await db.get(Voz, voz_id)
        if voz is None:
            raise TTSEngineError(f"Voz id={voz_id} não encontrada")
        return voz.nome

    async def gerar_audio(
        self,
        texto: str,
        personagem: str,
        voz_id: int | None = None,
        *,
        livro_id: int | None = None,
        db: AsyncSession | None = None,
        max_chars: int = 180,
    ) -> str:
        """
        Generate unified MP3 for *texto* and return its filesystem path.

        When *livro_id* and *db* are provided, registers the file in ``arquivo``.
        """
        chunks = self._chunkar_texto(texto, max_chars=max_chars)
        if not chunks:
            raise TTSEngineError("Texto vazio — nada para sintetizar")

        ref_audio = await self._resolver_ref_audio(voz_id, db)
        trabalho = self.audio_dir / _sanitizar_nome(personagem) / uuid.uuid4().hex
        trabalho.mkdir(parents=True, exist_ok=True)

        mp3_partes: list[Path] = []
        try:
            for indice, chunk in enumerate(chunks):
                wav_path = trabalho / f"chunk_{indice:04d}.wav"
                await self._post_to_tts_api(
                    chunk,
                    ref_audio=ref_audio,
                    output_wav=wav_path,
                )
                mp3_partes.append(self._converter_wav_para_mp3(wav_path))

            saida = trabalho / f"{_sanitizar_nome(personagem)}_unificado.mp3"
            final = self._unificar_arquivos(mp3_partes, saida)

            if livro_id is not None and db is not None:
                await self._registrar_arquivo(db, livro_id, final)

            return str(final.resolve())
        except Exception:
            raise

    async def _registrar_arquivo(
        self,
        db: AsyncSession,
        livro_id: int,
        caminho: Path,
    ) -> Arquivo:
        tamanho = caminho.stat().st_size if caminho.exists() else None
        row = Arquivo(
            livro_id=livro_id,
            tipo="mp3",
            caminho=str(caminho.resolve()),
            tamanho_bytes=tamanho,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

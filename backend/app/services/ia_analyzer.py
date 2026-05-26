"""LLM client for character extraction, name normalization, and profiling."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_config import ApiConfig
from app.schemas.ia import CharacterProfile, IAProvider, LLMEndpointConfig
from app.services.api_config_service import ApiConfigService, decrypt_token

logger = logging.getLogger(__name__)

CLOUD_TIMEOUT = 60.0
LOCAL_TIMEOUT = 120.0
CLOUD_RETRIES = 3
LOCAL_RETRIES = 2
CLOUD_BACKOFF = (1.0, 2.0, 4.0)
LOCAL_BACKOFF = (1.0, 2.0)

DEFAULT_CLOUD_MODEL = "gemini-2.0-flash"
DEFAULT_LOCAL_MODEL = "gemma3:27b-it-qat"

_RATE_LIMIT_MARKERS = (
    "exceeded",
    "rate limit",
    "ratelimit",
    "quota",
    "generaterequestsperday",
    "too many requests",
)

_PROMPT_EXTRAIR_PERSONAGENS = (
    "Extract direct speech and narration from the text. Do not remove or summarize any part of the content "
    "— preserve all details.\n"
    "Output each line in the format:\n"
    "name|speech\n"
    "narrator|narration\n\n"
    "Rules:\n"
    "- Translate to Portuguese if the text is in another language.\n"
    "- Return in UTF-8 format.\n"
    "- Correct grammar and spelling (in Portuguese).\n"
    "- Convert all numerals into their full written form in Portuguese.\n"
    "- Convert all monetary values into full written form.\n"
    "- Convert all physical measures into full written form with units.\n"
    "- Remove any page numbers or markers that are not part of the narrative.\n"
    "- If multiple characters say the same thing together, join their names with '/'.\n"
    "- Everything else is narration (use the name \"narrator\").\n"
    "- Keep the original chronological order of narration and speech.\n"
    "- Adapt narration and speech to sound natural for voiceover (TTS-ready).\n"
    "- Return only the final adapted lines in the correct format — no explanations.\n\n"
    "If no valid line is found, return only:\n"
    "no characters"
)

_PROMPT_NORMALIZAR_NOMES = (
    "You will receive a list of lines with:\n"
    "ID|Name|Speech\n\n"
    "Your task:\n"
    "- Standardize names if they refer to the same character\n"
    "- Use speech content to detect if different names refer to the same speaker\n"
    "- Merge names that share similar speech tone, phrases, or context\n"
    "- Always choose the most complete and descriptive proper name\n"
    "- If the name is not a proper name of a specific person, replace it with \"narrator\"\n"
    "- Gender must be inferred from the name and the speech\n"
    "- Do not remove or change IDs\n"
    "- Do not invent new names\n\n"
    "Output format:\n"
    "ID|Standardized name|gender\n"
    "Use only \"male\" or \"female\" for gender\n"
    "Return only the list in the exact format, no comments"
)

_PROMPT_DEFINIR_PERFIL = (
    "Analyze the input and return the Character profile in this exact format: Gender|Age\n"
    "Gender must be Male or Female, based on the name.\n"
    "Age must be Child, Adult, or Elderly, based on the speech style.\n"
    "Return ONLY the profile in the required format, nothing else.\n"
    "Character name:\n\"{personagem}\"\n\n"
)

_PROMPT_ATMOSFERICO = (
    "You are a specialist in cinematic soundtrack creation for audiobooks.\n"
    "You will receive a list of book excerpts, each accompanied by a time range representing "
    "when it occurs during the audiobook playback.\n"
    "Your task is to read the excerpts (written in Portuguese), understand their emotional tone, "
    "ambiance, and narrative content, and then produce a single, coherent, descriptive text "
    "prompt in English.\n"
    "This final prompt will be used as input to generate a background instrumental soundtrack "
    "using Facebook's MusicGen model.\n"
    "The generated soundtrack should reflect the combined atmosphere of all excerpts.\n"
    "Avoid vocals, strong rhythms or abrupt transitions. Favor immersive, cinematic, and "
    "emotionally appropriate instrumental music.\n"
    "### Expected Output:\n"
    "Return only one single English prompt that describes the ideal soundtrack, like this:\n"
    '"An atmospheric, suspenseful instrumental soundtrack with slow tempo and orchestral '
    "elements like soft strings, ambient pads, and subtle percussions. Designed for a tense "
    'night scene on a cliff with wind, danger, and emotional restraint."\n'
    "\n"
    "Do not return any explanation or additional text. Return only the prompt in English "
    "between quotes."
)


class IAAnalyzerError(Exception):
    """Base error for IA analyzer operations."""


class RateLimitError(IAAnalyzerError):
    """Cloud LLM rate limit or quota exceeded."""


class LLMConnectionError(IAAnalyzerError):
    """Unable to reach the LLM endpoint."""


class LLMUnavailableError(IAAnalyzerError):
    """Both cloud and local LLM providers failed."""

    def __init__(self, cloud_error: str | None = None, local_error: str | None = None) -> None:
        self.cloud_error = cloud_error
        self.local_error = local_error
        parts: list[str] = []
        if cloud_error:
            parts.append(f"cloud: {cloud_error}")
        if local_error:
            parts.append(f"local: {local_error}")
        message = "Falha ao chamar LLM (cloud e local indisponíveis)"
        if parts:
            message = f"{message}: {'; '.join(parts)}"
        super().__init__(message)


def _config_from_row(row: ApiConfig) -> LLMEndpointConfig:
    token: str | None = None
    if row.token:
        token = decrypt_token(row.token)
    return LLMEndpointConfig(
        url=row.url.rstrip("/"),
        modo=IAProvider.CLOUD if row.modo == "cloud" else IAProvider.LOCAL,
        token=token,
        modelo=row.modelo,
    )


def _formatar_tempo(segundos: int) -> str:
    horas, resto = divmod(max(segundos, 0), 3600)
    minutos, segs = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segs:02d}"


def _extrair_prompt_ingles(resposta: str) -> str:
    texto = resposta.strip()
    if not texto:
        raise IAAnalyzerError("Prompt atmosférico vazio")
    match = re.search(r'"([^"]+)"', texto)
    if match:
        return match.group(1).strip()
    if texto.startswith('"') and texto.endswith('"'):
        return texto[1:-1].strip()
    return texto


def _normalize_genero(value: str | None) -> str:
    if not value:
        return "neutro"
    key = value.strip().lower()
    mapping = {
        "male": "masculino",
        "m": "masculino",
        "masculino": "masculino",
        "homem": "masculino",
        "female": "feminino",
        "f": "feminino",
        "feminino": "feminino",
        "mulher": "feminino",
        "neutro": "neutro",
        "neutral": "neutro",
    }
    return mapping.get(key, "neutro")


def _normalize_idade(value: str | None) -> str:
    if not value:
        return "adulto"
    key = value.strip().lower()
    mapping = {
        "child": "crianca",
        "crianca": "crianca",
        "criança": "crianca",
        "adult": "adulto",
        "adulto": "adulto",
        "elderly": "idoso",
        "idoso": "idoso",
        "idosa": "idoso",
    }
    return mapping.get(key, "adulto")


def _is_rate_limit(status_code: int, body: str) -> bool:
    if status_code == 429:
        return True
    lowered = body.lower()
    return any(marker in lowered for marker in _RATE_LIMIT_MARKERS)


def _find_text_in_json(node: Any) -> str | None:
    if isinstance(node, dict):
        if "text" in node and isinstance(node["text"], str):
            return node["text"]
        for value in node.values():
            found = _find_text_in_json(value)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_text_in_json(item)
            if found:
                return found
    return None


class IAAnalyzer:
    def __init__(
        self,
        cloud_config: LLMEndpointConfig | None = None,
        local_config: LLMEndpointConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._cloud = cloud_config
        self._local = local_config
        self._client = client
        self._owns_client = client is None

    @classmethod
    async def from_db(cls, db: AsyncSession, *, client: httpx.AsyncClient | None = None) -> IAAnalyzer:
        service = ApiConfigService(db)
        rows = await service.list_configs()
        cloud_row = next((r for r in rows if r.tipo == "llm" and r.modo == "cloud"), None)
        local_row = next((r for r in rows if r.tipo == "llm" and r.modo == "local"), None)
        if cloud_row is None and local_row is None:
            raise IAAnalyzerError("Nenhuma configuração LLM (tipo=llm) ativa encontrada")
        return cls(
            cloud_config=_config_from_row(cloud_row) if cloud_row else None,
            local_config=_config_from_row(local_row) if local_row else None,
            client=client,
        )

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> IAAnalyzer:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def extrair_personagens(self, texto: str) -> list[CharacterProfile]:
        resposta = await self._chamar_llm(_PROMPT_EXTRAIR_PERSONAGENS, texto)
        if resposta.strip().lower() in {"no characters", "[change-connection]"}:
            return []
        parsed = self._parse_resposta(resposta)
        seen: set[str] = set()
        result: list[CharacterProfile] = []
        for item in parsed:
            nome = item.nome.strip().lower()
            if not nome or nome in seen:
                continue
            seen.add(nome)
            result.append(CharacterProfile(nome=nome, genero=item.genero, idade=item.idade))
        return result

    async def normalizar_nomes(self, personagens: list[CharacterProfile]) -> list[CharacterProfile]:
        if not personagens:
            return []
        linhas = [f"{idx}|{p.nome}|" for idx, p in enumerate(personagens)]
        entrada = "\n".join(linhas)
        resposta = await self._chamar_llm(_PROMPT_NORMALIZAR_NOMES, entrada)
        return self._merge_normalizacao(personagens, resposta)

    async def gerar_prompt_atmosferico(
        self,
        texto_excerpto: str,
        tempo_inicio: int = 0,
        tempo_fim: int = 0,
    ) -> str:
        """Generate an English MusicGen prompt from a book excerpt and time range."""
        if tempo_fim > tempo_inicio:
            faixa = f" [{_formatar_tempo(tempo_inicio)} - {_formatar_tempo(tempo_fim)}]"
        else:
            faixa = ""
        conteudo = f"{texto_excerpto.strip()}{faixa}"
        resposta = await self._chamar_llm(_PROMPT_ATMOSFERICO, conteudo)
        return _extrair_prompt_ingles(resposta)

    async def definir_perfil(self, texto: str, personagem: str) -> CharacterProfile:
        prompt = _PROMPT_DEFINIR_PERFIL.format(personagem=personagem)
        resposta = await self._chamar_llm(prompt, texto)
        genero_raw, idade_raw = self._parse_genero_idade_linha(resposta)
        if genero_raw and idade_raw:
            return CharacterProfile(
                nome=personagem.strip().lower(),
                genero=_normalize_genero(genero_raw),  # type: ignore[arg-type]
                idade=_normalize_idade(idade_raw),  # type: ignore[arg-type]
            )
        parsed = self._parse_resposta(resposta)
        if parsed:
            profile = parsed[0]
            return CharacterProfile(
                nome=personagem.strip().lower(),
                genero=profile.genero,
                idade=profile.idade,
            )
        return CharacterProfile(nome=personagem.strip().lower())

    def _merge_normalizacao(
        self,
        originais: list[CharacterProfile],
        raw: str,
    ) -> list[CharacterProfile]:
        updates: dict[int, CharacterProfile] = {}
        for line in raw.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3 or not parts[0].isdigit():
                continue
            idx = int(parts[0])
            if idx >= len(originais):
                continue
            updates[idx] = CharacterProfile(
                nome=parts[1].lower(),
                genero=_normalize_genero(parts[2]),  # type: ignore[arg-type]
                idade=originais[idx].idade,
            )
        return [updates.get(idx, original) for idx, original in enumerate(originais)]

    async def _chamar_llm(self, prompt: str, conteudo: str) -> str:
        cloud_error: str | None = None

        if self._cloud is not None:
            try:
                return await self._chamar_com_retry(
                    self._chamar_llm_cloud,
                    prompt,
                    conteudo,
                    retries=CLOUD_RETRIES,
                    backoff=CLOUD_BACKOFF,
                )
            except (RateLimitError, LLMConnectionError) as exc:
                cloud_error = str(exc)
                logger.warning("Cloud LLM falhou (%s), tentando local...", exc)
            except IAAnalyzerError:
                raise
        elif self._local is None:
            raise IAAnalyzerError("Nenhuma configuração LLM disponível")

        if self._local is None:
            raise LLMUnavailableError(cloud_error=cloud_error, local_error="configuração local ausente")

        try:
            return await self._chamar_com_retry(
                self._chamar_llm_local,
                prompt,
                conteudo,
                retries=LOCAL_RETRIES,
                backoff=LOCAL_BACKOFF,
            )
        except IAAnalyzerError as exc:
            raise LLMUnavailableError(cloud_error=cloud_error, local_error=str(exc)) from exc

    async def _chamar_com_retry(
        self,
        caller: Any,
        prompt: str,
        conteudo: str,
        *,
        retries: int,
        backoff: tuple[float, ...],
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                return await caller(prompt, conteudo)
            except (RateLimitError, LLMConnectionError) as exc:
                last_error = exc
                if attempt < retries - 1:
                    delay = backoff[attempt] if attempt < len(backoff) else backoff[-1]
                    await asyncio.sleep(delay)
                else:
                    raise
            except httpx.TimeoutException as exc:
                last_error = LLMConnectionError(str(exc))
                if attempt < retries - 1:
                    delay = backoff[attempt] if attempt < len(backoff) else backoff[-1]
                    await asyncio.sleep(delay)
                else:
                    raise LLMConnectionError(str(exc)) from exc
        if last_error:
            raise last_error
        raise IAAnalyzerError("Falha inesperada ao chamar LLM")

    async def _chamar_llm_cloud(self, prompt: str, conteudo: str) -> str:
        if self._cloud is None:
            raise IAAnalyzerError("Configuração cloud ausente")
        config = self._cloud
        model = config.modelo or DEFAULT_CLOUD_MODEL
        url = self._build_cloud_url(config.url, model, config.token)
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{prompt}\n\n{conteudo}"},
                    ],
                },
            ],
        }
        headers = {"Content-Type": "application/json"}
        client = await self._get_client()
        try:
            response = await client.post(url, json=body, headers=headers, timeout=CLOUD_TIMEOUT)
        except httpx.RequestError as exc:
            raise LLMConnectionError(str(exc)) from exc

        text_body = response.text
        if _is_rate_limit(response.status_code, text_body):
            raise RateLimitError(text_body[:500])
        if response.status_code >= 500:
            raise LLMConnectionError(f"HTTP {response.status_code}")
        if response.status_code >= 400:
            raise IAAnalyzerError(f"Erro cloud LLM HTTP {response.status_code}: {text_body[:300]}")

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise IAAnalyzerError("Resposta cloud inválida (JSON)") from exc

        extracted = _find_text_in_json(payload)
        if not extracted:
            if _is_rate_limit(response.status_code, text_body):
                raise RateLimitError(text_body[:500])
            raise IAAnalyzerError("Resposta cloud sem campo text")
        return extracted.strip()

    async def _chamar_llm_local(self, prompt: str, conteudo: str) -> str:
        if self._local is None:
            raise IAAnalyzerError("Configuração local ausente")
        config = self._local
        model = config.modelo or DEFAULT_LOCAL_MODEL
        url = self._build_local_url(config.url)
        body = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": conteudo},
            ],
        }
        client = await self._get_client()
        try:
            response = await client.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=LOCAL_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise LLMConnectionError(str(exc)) from exc

        text_body = response.text
        if response.status_code == 429 or _is_rate_limit(response.status_code, text_body):
            raise RateLimitError(text_body[:500])
        if response.status_code >= 500:
            raise LLMConnectionError(f"HTTP {response.status_code}")
        if response.status_code >= 400:
            raise IAAnalyzerError(f"Erro local LLM HTTP {response.status_code}: {text_body[:300]}")

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise IAAnalyzerError("Resposta local inválida (JSON)") from exc

        message = payload.get("message") or {}
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content.strip():
            return content.strip()
        raise IAAnalyzerError("Resposta local sem conteúdo")

    @staticmethod
    def _build_cloud_url(base_url: str, model: str, token: str | None) -> str:
        base = base_url.rstrip("/")
        if "generateContent" in base:
            return base if not token else f"{base}{'&' if '?' in base else '?'}key={token}"
        path = f"v1beta/models/{model}:generateContent"
        if token:
            path = f"{path}?key={token}"
        return urljoin(f"{base}/", path)

    @staticmethod
    def _build_local_url(base_url: str) -> str:
        parsed = urlparse(base_url)
        if parsed.path and parsed.path not in {"", "/"}:
            return base_url if base_url.endswith("/api/chat") else urljoin(f"{base_url.rstrip('/')}/", "api/chat")
        return urljoin(f"{base_url.rstrip('/')}/", "api/chat")

    def _parse_resposta(self, texto: str) -> list[CharacterProfile]:
        cleaned = texto.strip()
        if not cleaned:
            return []

        json_profiles = self._parse_json_resposta(cleaned)
        if json_profiles:
            return json_profiles

        profiles: list[CharacterProfile] = []
        for line in cleaned.splitlines():
            line = line.strip()
            if not line or "|" not in line:
                continue
            profile = self._parse_linha(line)
            if profile:
                profiles.append(profile)
        return profiles

    def _parse_json_resposta(self, texto: str) -> list[CharacterProfile]:
        candidates = [texto]
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", texto, re.IGNORECASE)
        if fence:
            candidates.insert(0, fence.group(1).strip())

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            items: list[Any]
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                if "personagens" in data and isinstance(data["personagens"], list):
                    items = data["personagens"]
                elif "characters" in data and isinstance(data["characters"], list):
                    items = data["characters"]
                else:
                    items = [data]
            else:
                continue

            profiles: list[CharacterProfile] = []
            for item in items:
                if isinstance(item, dict):
                    nome = str(item.get("nome") or item.get("name") or "").strip()
                    if not nome:
                        continue
                    genero = _normalize_genero(str(item.get("genero") or item.get("gender") or ""))
                    idade = _normalize_idade(str(item.get("idade") or item.get("age") or ""))
                    profiles.append(
                        CharacterProfile(
                            nome=nome.lower(),
                            genero=genero,  # type: ignore[arg-type]
                            idade=idade,  # type: ignore[arg-type]
                        )
                    )
                elif isinstance(item, str) and "|" in item:
                    profile = self._parse_linha(item)
                    if profile:
                        profiles.append(profile)
            if profiles:
                return profiles
        return []

    def _parse_linha(self, line: str) -> CharacterProfile | None:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            return None

        if len(parts) == 2:
            nome, second = parts[0], parts[1]
            if second.lower() in {"male", "female", "masculino", "feminino", "m", "f"}:
                return CharacterProfile(
                    nome=nome.lower(),
                    genero=_normalize_genero(second),  # type: ignore[arg-type]
                    idade="adulto",
                )
            return CharacterProfile(nome=nome.lower(), genero="neutro", idade="adulto")

        if parts[0].isdigit() and len(parts) >= 3:
            return CharacterProfile(
                nome=parts[1].lower(),
                genero=_normalize_genero(parts[2]),  # type: ignore[arg-type]
                idade="adulto",
            )

        if len(parts) >= 3:
            return CharacterProfile(
                nome=parts[0].lower(),
                genero=_normalize_genero(parts[1]),  # type: ignore[arg-type]
                idade=_normalize_idade(parts[2]),  # type: ignore[arg-type]
            )
        return None

    @staticmethod
    def _parse_genero_idade_linha(texto: str) -> tuple[str | None, str | None]:
        for line in texto.splitlines():
            line = line.strip()
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|", 1)]
            if len(parts) == 2:
                return parts[0], parts[1]
        if "|" in texto:
            parts = [p.strip() for p in texto.split("|", 1)]
            if len(parts) == 2:
                return parts[0], parts[1]
        return None, None

"""Celery task: full book processing pipeline (6 stages)."""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models.api_config import ApiConfig
from app.models.arquivo import Arquivo
from app.models.book_task import BookTask
from app.models.capitulo import Capitulo
from app.models.falas import Fala
from app.models.livro import Livro
from app.models.pagina import Pagina
from app.models.personagem import Personagem
from app.models.voz import Voz
from app.schemas.ia import CharacterProfile, IAProvider, LLMEndpointConfig
from app.services.api_config_service import decrypt_token
from app.services.ia_analyzer import IAAnalyzer, _PROMPT_EXTRAIR_PERSONAGENS
from app.services.musicgen import MusicGenService, PaginaExcerto
from app.services.pdf_processor import PDFProcessor, PageExtractionResult
from app.services.tts_engine import TTSEngine

logger = logging.getLogger(__name__)

NARRADOR_NOME = "narrator"
_GENDER_TOKENS = frozenset(
    {"male", "female", "m", "f", "masculino", "feminino", "homem", "mulher"}
)
_NIVEIS_COM_TRILHA = frozenset({"avancado", "profissional"})

STAGE_CAPITULOS = "CHAPTER_DIVISION"
STAGE_PDF = "PDF_PROCESSING"
STAGE_IA = "IA_ANALYSIS"
STAGE_VOZ = "VOICE_ASSIGNMENT"
STAGE_AUDIO = "AUDIO_PRODUCTION"
STAGE_MUSIC = "MUSICGEN"
STAGE_UNIFICAR = "UNIFICAR"

PROGRESS_AFTER = {
    STAGE_CAPITULOS: 10,
    STAGE_PDF: 10,
    STAGE_IA: 40,
    STAGE_VOZ: 50,
    STAGE_AUDIO: 90,
    STAGE_MUSIC: 95,
    STAGE_UNIFICAR: 100,
}


def _run_async(coro):
    return asyncio.run(coro)


def _parse_extracao_linhas(resposta: str) -> list[tuple[str, str]]:
    """Parse LLM lines ``nome|fala`` (Delphi-compatible extraction)."""
    linhas: list[tuple[str, str]] = []
    for raw in resposta.splitlines():
        line = raw.strip()
        if not line or "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|", 1)]
        if len(parts) != 2:
            continue
        nome, fala = parts[0].lower(), parts[1]
        if not nome or not fala:
            continue
        if nome in {"no characters", "[change-connection]"}:
            continue
        if fala.lower() in _GENDER_TOKENS:
            continue
        linhas.append((nome, fala))
    return linhas


def _config_from_api_row(row: ApiConfig) -> LLMEndpointConfig:
    token: str | None = None
    if row.token:
        token = decrypt_token(row.token)
    return LLMEndpointConfig(
        url=row.url.rstrip("/"),
        modo=IAProvider.CLOUD if row.modo == "cloud" else IAProvider.LOCAL,
        token=token,
        modelo=row.modelo,
    )


def _load_ia_analyzer(db: Session) -> IAAnalyzer:
    rows = (
        db.query(ApiConfig)
        .filter(ApiConfig.tipo == "llm", ApiConfig.ativo.is_(True))
        .all()
    )
    cloud_row = next((r for r in rows if r.modo == "cloud"), None)
    local_row = next((r for r in rows if r.modo == "local"), None)
    if cloud_row is None and local_row is None:
        raise RuntimeError("Nenhuma configuração LLM ativa encontrada")
    return IAAnalyzer(
        cloud_config=_config_from_api_row(cloud_row) if cloud_row else None,
        local_config=_config_from_api_row(local_row) if local_row else None,
    )


def _load_tts_engine(db: Session) -> TTSEngine:
    row = (
        db.query(ApiConfig)
        .filter(ApiConfig.tipo == "tts", ApiConfig.ativo.is_(True))
        .order_by(ApiConfig.id)
        .first()
    )
    api_url = settings.tts_api_url
    api_key: str | None = None
    if row is not None:
        api_url = row.url.rstrip("/")
        if row.token:
            api_key = decrypt_token(row.token)
    return TTSEngine(api_url, api_key, audio_dir=settings.audio_dir)


def _load_musicgen(db: Session, analyzer: IAAnalyzer) -> MusicGenService:
    row = (
        db.query(ApiConfig)
        .filter(ApiConfig.tipo == "musicgen", ApiConfig.ativo.is_(True))
        .order_by(ApiConfig.id)
        .first()
    )
    api_url = settings.musicgen_api_url
    api_key: str | None = None
    if row is not None:
        api_url = row.url.rstrip("/")
        if row.token:
            api_key = decrypt_token(row.token)
    return MusicGenService(
        api_url,
        api_key,
        ia_analyzer=analyzer,
        audio_dir=settings.audio_dir,
    )


def _match_voz(
    vozes: list[Voz],
    genero: str | None,
    idade: str | None,
    fallback_voz_id: int | None = None,
) -> int | None:
    genero_norm = (genero or "neutro").lower()
    idade_norm = (idade or "adulto").lower()

    for voz in vozes:
        if voz.genero.lower() == genero_norm and voz.idade.lower() == idade_norm:
            return voz.id
    for voz in vozes:
        if voz.genero.lower() == genero_norm:
            return voz.id
    return fallback_voz_id


class BookPipeline:
    """Orchestrates the six pipeline stages for one livro."""

    def __init__(self, db: Session, livro_id: int, work_dir: Path) -> None:
        self.db = db
        self.livro_id = livro_id
        self.work_dir = work_dir
        self.livro = db.get(Livro, livro_id)
        if self.livro is None:
            raise ValueError(f"Livro id={livro_id} não encontrado")
        self.book_task = (
            db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        )
        if self.book_task is None:
            raise ValueError(f"book_task para livro_id={livro_id} não encontrada")

        self._audio_paths: list[Path] = []
        self._trilha_paths: list[str] = []
        self._duracao_total: int = 0

    def run(self) -> str:
        if self._is_paused():
            logger.info("Pipeline pausado antes de iniciar livro_id=%s", self.livro_id)
            return f"livro_{self.livro_id}_pausado"
        try:
            self._update_task(status="processando", progresso=0, etapa_atual=STAGE_PDF)
            self.livro.status = "processando"
            self.db.commit()

            stages = (
                self._stage_pdf_processing,
                self._stage_ia_analysis,
                self._stage_voice_assignment,
                self._stage_audio_production,
                self._stage_musicgen,
                self._stage_dividir_capitulos,
                self._stage_unificar,
            )
            for stage_fn in stages:
                if self._is_paused():
                    logger.info("Pipeline pausado livro_id=%s", self.livro_id)
                    return f"livro_{self.livro_id}_pausado"
                stage_fn()

            self._update_task(status="concluido", progresso=100, etapa_atual=STAGE_UNIFICAR)
            self.livro.status = "concluido"
            self.livro.progresso = 100
            self.db.commit()
            return f"livro_{self.livro_id}_processed"
        except Exception as exc:
            self._mark_failed(str(exc))
            raise

    def _mark_failed(self, message: str) -> None:
        self._update_task(status="falhou", erro=message[:2000])
        self.livro.status = "falhou"
        self.db.commit()

    def _is_paused(self) -> bool:
        self.db.refresh(self.book_task)
        self.db.refresh(self.livro)
        return self.book_task.status == "pausado" or self.livro.status == "pausado"

    def _update_task(
        self,
        *,
        status: str | None = None,
        progresso: int | None = None,
        etapa_atual: str | None = None,
        erro: str | None = None,
    ) -> None:
        if status is not None:
            self.book_task.status = status
        if progresso is not None:
            self.book_task.progresso = progresso
            self.livro.progresso = progresso
        if etapa_atual is not None:
            self.book_task.etapa_atual = etapa_atual
        if erro is not None:
            self.book_task.erro = erro
        self.db.commit()

    def _stage_pdf_processing(self) -> None:
        self._update_task(etapa_atual=STAGE_PDF, progresso=0)

        existing = (
            self.db.query(Pagina)
            .filter(Pagina.livro_id == self.livro_id)
            .count()
        )
        if existing == 0:
            if not self.livro.caminho_pdf:
                raise RuntimeError("caminho_pdf não definido no livro")
            processor = PDFProcessor()
            result: PageExtractionResult = processor.extract_text(self.livro.caminho_pdf)
            if not result.pages:
                raise RuntimeError("Nenhuma página extraída do documento")
            for page in result.pages:
                self.db.add(
                    Pagina(
                        livro_id=self.livro_id,
                        numero=page.numero,
                        texto=page.texto,
                        processado=False,
                    )
                )
            self.db.commit()

        self._update_task(progresso=PROGRESS_AFTER[STAGE_PDF], etapa_atual=STAGE_PDF)

    def _stage_ia_analysis(self) -> None:
        self._update_task(etapa_atual=STAGE_IA, progresso=PROGRESS_AFTER[STAGE_PDF])

        analyzer = _load_ia_analyzer(self.db)
        paginas = (
            self.db.query(Pagina)
            .filter(Pagina.livro_id == self.livro_id)
            .order_by(Pagina.numero)
            .all()
        )
        total = len(paginas)
        if total == 0:
            raise RuntimeError("Nenhuma página para análise de IA")

        async def analisar() -> list[CharacterProfile]:
            try:
                for indice, pagina in enumerate(paginas):
                    if pagina.processado:
                        continue
                    resposta = await analyzer._chamar_llm(  # noqa: SLF001
                        _PROMPT_EXTRAIR_PERSONAGENS,
                        pagina.texto,
                    )
                    if resposta.strip().lower() in {"no characters", "[change-connection]"}:
                        pagina.processado = True
                        continue

                    linhas = _parse_extracao_linhas(resposta)
                    for nome, texto_fala in linhas:
                        personagem = self._get_or_create_personagem(nome)
                        self.db.add(
                            Fala(
                                livro_id=self.livro_id,
                                pagina_id=pagina.id,
                                personagem_id=personagem.id,
                                texto=texto_fala,
                                processado=False,
                            )
                        )
                    pagina.processado = True
                    progresso = PROGRESS_AFTER[STAGE_PDF] + int(
                        (indice + 1) / total * (PROGRESS_AFTER[STAGE_IA] - PROGRESS_AFTER[STAGE_PDF])
                    )
                    self._update_task(progresso=progresso)

                self.db.commit()
                personagens = self._list_personagens()
                if not personagens:
                    raise RuntimeError("Nenhum personagem extraído pela IA")

                profiles = [
                    CharacterProfile(
                        nome=p.nome,
                        genero=p.genero or "neutro",  # type: ignore[arg-type]
                        idade=p.idade or "adulto",  # type: ignore[arg-type]
                    )
                    for p in personagens
                ]
                normalizados = await analyzer.normalizar_nomes(profiles)
                for perfil in normalizados:
                    if perfil.nome == NARRADOR_NOME:
                        continue
                    texto_pers = self._texto_personagem(perfil.nome)
                    if texto_pers:
                        atualizado = await analyzer.definir_perfil(texto_pers, perfil.nome)
                        perfil.genero = atualizado.genero
                        perfil.idade = atualizado.idade

                narrador_texto = self._texto_personagem(NARRADOR_NOME)
                if narrador_texto:
                    perfil_narrador = await analyzer.definir_perfil(
                        narrador_texto, NARRADOR_NOME
                    )
                    for perfil in normalizados:
                        if perfil.nome == NARRADOR_NOME:
                            perfil.genero = perfil_narrador.genero
                            perfil.idade = perfil_narrador.idade
                return normalizados
            finally:
                await analyzer.aclose()

        normalizados = _run_async(analisar())
        self._apply_profiles(normalizados)
        self._update_task(progresso=PROGRESS_AFTER[STAGE_IA], etapa_atual=STAGE_IA)

    def _get_or_create_personagem(self, nome: str) -> Personagem:
        nome_norm = nome.strip().lower()
        is_narrador = nome_norm == NARRADOR_NOME
        existente = (
            self.db.query(Personagem)
            .filter(
                Personagem.livro_id == self.livro_id,
                Personagem.nome == nome_norm,
            )
            .first()
        )
        if existente:
            return existente
        row = Personagem(
            livro_id=self.livro_id,
            nome=nome_norm,
            nome_original=nome,
            is_narrador=is_narrador,
            genero="neutro",
            idade="adulto",
        )
        self.db.add(row)
        self.db.flush()
        return row

    def _list_personagens(self) -> list[Personagem]:
        return (
            self.db.query(Personagem)
            .filter(Personagem.livro_id == self.livro_id)
            .order_by(Personagem.id)
            .all()
        )

    def _texto_personagem(self, nome: str) -> str:
        stmt = (
            select(Fala.texto)
            .join(Personagem, Fala.personagem_id == Personagem.id)
            .join(Pagina, Fala.pagina_id == Pagina.id)
            .where(
                Fala.livro_id == self.livro_id,
                Personagem.nome == nome,
            )
            .order_by(Pagina.numero, Fala.id)
        )
        rows = self.db.execute(stmt).scalars().all()
        return " ".join(t for t in rows if t)

    def _apply_profiles(self, profiles: list[CharacterProfile]) -> None:
        by_name = {p.nome: p for p in profiles}
        for personagem in self._list_personagens():
            perfil = by_name.get(personagem.nome)
            if perfil is None:
                continue
            personagem.genero = perfil.genero
            personagem.idade = perfil.idade
        self.db.commit()

    def _stage_voice_assignment(self) -> None:
        self._update_task(
            etapa_atual=STAGE_VOZ,
            progresso=PROGRESS_AFTER[STAGE_IA],
        )
        vozes = self.db.query(Voz).all()
        personagens = self._list_personagens()
        narrador = next((p for p in personagens if p.is_narrador), None)
        narrador_voz_id: int | None = None

        if narrador and not narrador.voz_id:
            narrador_voz_id = _match_voz(vozes, narrador.genero, narrador.idade)
            narrador.voz_id = narrador_voz_id

        for personagem in personagens:
            if personagem.voz_id:
                continue
            if personagem.is_narrador:
                continue
            voz_id = _match_voz(
                vozes,
                personagem.genero,
                personagem.idade,
                fallback_voz_id=narrador_voz_id,
            )
            if voz_id is None and narrador:
                voz_id = narrador.voz_id
            personagem.voz_id = voz_id

        self.db.commit()
        self._update_task(progresso=PROGRESS_AFTER[STAGE_VOZ], etapa_atual=STAGE_VOZ)

    def _stage_audio_production(self) -> None:
        self._update_task(
            etapa_atual=STAGE_AUDIO,
            progresso=PROGRESS_AFTER[STAGE_VOZ],
        )
        tts = _load_tts_engine(self.db)
        falas = (
            self.db.query(Fala)
            .join(Pagina, Fala.pagina_id == Pagina.id)
            .join(Personagem, Fala.personagem_id == Personagem.id)
            .filter(Fala.livro_id == self.livro_id)
            .order_by(Pagina.numero, Fala.id)
            .all()
        )
        total = len(falas)
        if total == 0:
            raise RuntimeError("Nenhuma fala para produção de áudio")

        personagem_cache: dict[int, Personagem] = {}

        async def produzir() -> None:
            try:
                for indice, fala in enumerate(falas):
                    personagem = personagem_cache.get(fala.personagem_id or 0)
                    if personagem is None and fala.personagem_id:
                        personagem = self.db.get(Personagem, fala.personagem_id)
                        if personagem:
                            personagem_cache[personagem.id] = personagem
                    if personagem is None:
                        continue

                    caminho = await tts.gerar_audio(
                        fala.texto,
                        personagem.nome,
                        voz_id=personagem.voz_id,
                    )
                    path = Path(caminho)
                    self._audio_paths.append(path)
                    arquivo = Arquivo(
                        livro_id=self.livro_id,
                        tipo="mp3",
                        caminho=str(path.resolve()),
                        tamanho_bytes=path.stat().st_size if path.exists() else None,
                    )
                    self.db.add(arquivo)
                    self.db.flush()
                    fala.arquivo_id = arquivo.id
                    fala.processado = True

                    progresso = PROGRESS_AFTER[STAGE_VOZ] + int(
                        (indice + 1)
                        / total
                        * (PROGRESS_AFTER[STAGE_AUDIO] - PROGRESS_AFTER[STAGE_VOZ])
                    )
                    self._update_task(progresso=progresso)
            finally:
                await tts.aclose()

        _run_async(produzir())
        self.db.commit()
        self._update_task(progresso=PROGRESS_AFTER[STAGE_AUDIO], etapa_atual=STAGE_AUDIO)

    def _stage_musicgen(self) -> None:
        nivel = (self.livro.nivel_producao or "").strip().lower()
        if nivel not in _NIVEIS_COM_TRILHA:
            self._update_task(progresso=PROGRESS_AFTER[STAGE_MUSIC], etapa_atual=STAGE_MUSIC)
            return

        self._update_task(
            etapa_atual=STAGE_MUSIC,
            progresso=PROGRESS_AFTER[STAGE_AUDIO],
        )
        analyzer = _load_ia_analyzer(self.db)
        musicgen = _load_musicgen(self.db, analyzer)
        paginas = (
            self.db.query(Pagina)
            .filter(Pagina.livro_id == self.livro_id)
            .order_by(Pagina.numero)
            .all()
        )
        excertos = [
            PaginaExcerto(numero=p.numero, texto=p.texto)
            for p in paginas
        ]
        duracao = max(self._duracao_total, len(self._audio_paths) * 30)

        async def gerar_trilhas() -> list[str]:
            try:
                return await musicgen.gerar_trilhas_livro(
                    excertos,
                    nivel,
                    duracao,
                    nome_livro=self.livro.titulo,
                )
            finally:
                await musicgen.aclose()

        self._trilha_paths = _run_async(gerar_trilhas())
        self._update_task(progresso=PROGRESS_AFTER[STAGE_MUSIC], etapa_atual=STAGE_MUSIC)



    def _dividir_capitulos(self):
        """Divide the book into chapters based on chapter header detection."""
        from sqlalchemy import select as _sa_select

        stmt = (
            _sa_select(Pagina)
            .where(Pagina.livro_id == self.livro_id)
            .order_by(Pagina.numero)
        )
        pages_result = self.db.execute(stmt).scalars().all()

        if not pages_result:
            cap = Capitulo(
                livro_id=self.livro_id,
                numero=1,
                titulo=self.livro.titulo or "Capítulo \xc3\x9anico",
                pagina_inicio=0,
                pagina_fim=0,
            )
            self.db.add(cap)
            self.db.commit()
            return [cap]

        # Regex: matches Capítulo 1, CAPÍTULO 2:, Chapter 3, etc.
        pat = re.compile(
            r'(?:CAP[\u00cd\u0049]TULO|Cap[\u00cd\u0049]tulo|Chapter)\s*(\d+)\s*[.:]?\s*(.+?)\s*$'
            , re.IGNORECASE | re.MULTILINE
        )

        chapters = []
        current_cap_start = None
        current_cap_num = None
        current_cap_title = None

        for page in pages_result:
            if not page.texto or len(page.texto.strip()) < 50:
                continue

            match = pat.search(page.texto[:500])
            if match:
                if current_cap_start is not None and current_cap_num is not None:
                    chapters.append(Capitulo(
                        livro_id=self.livro_id,
                        numero=current_cap_num,
                        titulo=current_cap_title,
                        pagina_inicio=current_cap_start,
                        pagina_fim=page.numero - 1,
                    ))
                current_cap_num = int(match.group(1))
                current_cap_title = "Capítulo %d - %s" % (int(match.group(1)), match.group(2).strip())
                current_cap_start = page.numero
            elif current_cap_start is None and current_cap_num is None:
                current_cap_start = page.numero
                txt = page.texto[:80].replace("\n", " ").strip() or "Introdução"
                current_cap_title = "Capítulo 1 - " + txt

        if current_cap_start is not None:
            chapters.append(Capitulo(
                livro_id=self.livro_id,
                numero=current_cap_num or 1,
                titulo=current_cap_title or "Capítulo 1",
                pagina_inicio=current_cap_start,
                pagina_fim=pages_result[-1].numero if pages_result else 0,
            ))

        if not chapters:
            chapters.append(Capitulo(
                livro_id=self.livro_id,
                numero=1,
                titulo=self.livro.titulo or "Livro Inteiro",
                pagina_inicio=pages_result[0].numero,
                pagina_fim=pages_result[-1].numero if pages_result else 0,
            ))

        for i, cap in enumerate(chapters):
            cap.numero = i + 1
            cap.titulo = cap.titulo or "Capítulo %d" % cap.numero

        self.db.query(Capitulo).filter(Capitulo.livro_id == self.livro_id).delete()
        for cap in chapters:
            self.db.add(cap)
        self.db.commit()

        return chapters



    def _stage_dividir_capitulos(self):
        """Stage: divide book into chapters."""
        self._update_task(
            etapa_atual=STAGE_CAPITULOS,
            progresso=PROGRESS_AFTER.get(STAGE_CAPITULOS, 10),
        )
        self._dividir_capitulos()
        self._update_task(
            progresso=PROGRESS_AFTER[STAGE_CAPITULOS],
            etapa_atual=STAGE_CAPITULOS,
        )

    def _stage_exportar_capitulo(self, chapters, tts, nome_seguro, saida_dir):
        """Export each chapter as a separate MP3 file."""
        from sqlalchemy import select as _sa_select

        # Get all Fala with page numbers and their audio paths
        stmt = (
            _sa_select(Fala, Pagina.numero.label("pag_num"))
            .join(Pagina, Fala.pagina_id == Pagina.id, isouter=True)
            .where(Fala.livro_id == self.livro_id, Fala.processado.is_(True))
            .order_by(Pagina.numero, Fala.id)
        )
        fala_rows = self.db.execute(stmt).all()

        # Group audio by page number
        fala_by_page = {}
        for row in fala_rows:
            fala = row[0]
            pag_num = row[1] if row[1] else 0
            if fala.arquivo_id is not None:
                arquivo = self.db.get(Arquivo, fala.arquivo_id)
                if arquivo and arquivo.caminho:
                    fpath = Path(arquivo.caminho)
                    if fpath.exists():
                        fala_by_page.setdefault(pag_num, []).append(fpath)

        for cap in chapters:
            start = cap.pagina_inicio or 0
            end = cap.pagina_fim or 999999

            chapter_files = []
            for pag_num, files in sorted(fala_by_page.items()):
                if start <= pag_num <= end:
                    chapter_files.extend(files)

            if not chapter_files:
                cap.caminho_audio = None
                cap.duracao_estimada = 0
                self.db.commit()
                continue

            cap_dir = saida_dir
            cap_dir.mkdir(parents=True, exist_ok=True)
            cap_path = cap_dir / (nome_seguro + "_capitulo_" + str(cap.numero) + ".mp3")

            try:
                tts._unificar_arquivos(chapter_files, cap_path)
                cap.caminho_audio = str(cap_path.resolve())
                cap.duracao_estimada = int(cap_path.stat().st_size / 1000) if cap_path.exists() else 0
                self.db.add(Arquivo(
                    livro_id=self.livro_id,
                    tipo="capitulo",
                    caminho=str(cap_path.resolve()),
                    tamanho_bytes=cap_path.stat().st_size if cap_path.exists() else None,
                ))
                self.db.commit()
                logger.info("Capítulo %d exportado: %s", cap.numero, cap_path)
            except Exception as exc:
                logger.error("Erro ao exportar capítulo %d: %s", cap.numero, exc)
                cap.caminho_audio = None
                self.db.commit()

    def _stage_unificar(self) -> None:
        self._update_task(
            etapa_atual=STAGE_UNIFICAR,
            progresso=PROGRESS_AFTER[STAGE_MUSIC],
        )
        if not self._audio_paths:
            raise RuntimeError("Nenhum áudio gerado para unificação")

        tts = _load_tts_engine(self.db)
        saida_dir = Path(settings.audio_dir) / str(self.livro_id)
        saida_dir.mkdir(parents=True, exist_ok=True)
        nome_seguro = re.sub(r"[^\w\-]+", "_", self.livro.titulo, flags=re.UNICODE) or "livro"
        destino = saida_dir / f"{nome_seguro}_audiobook.mp3"

        arquivos = [p for p in self._audio_paths if p.exists()]
        if not arquivos:
            raise RuntimeError("Arquivos de áudio não encontrados no disco")

        tts._unificar_arquivos(arquivos, destino)  # noqa: SLF001

        self.livro.caminho_audio = str(destino.resolve())
        self.db.add(
            Arquivo(
                livro_id=self.livro_id,
                tipo="audiobook",
                caminho=self.livro.caminho_audio,
                tamanho_bytes=destino.stat().st_size if destino.exists() else None,
            )
        )
        self._update_task(progresso=PROGRESS_AFTER[STAGE_UNIFICAR], etapa_atual=STAGE_UNIFICAR)

        # Export chapters
        try:
            from sqlalchemy import select as _sa_select
            stmt = (
                _sa_select(Capitulo)
                .where(Capitulo.livro_id == self.livro_id)
                .order_by(Capitulo.numero)
            )
            chapters = self.db.execute(stmt).scalars().all()
            if chapters:
                self._stage_exportar_capitulo(chapters, tts, nome_seguro, saida_dir)
        except Exception as exc:
            logger.warning("Falha na exportação por capítulo: %s", exc)


def run_process_book(livro_id: int, work_dir: Path) -> str:
    """Execute the pipeline synchronously (used by Celery task and tests)."""
    db = SessionLocal()
    try:
        pipeline = BookPipeline(db, livro_id, work_dir)
        return pipeline.run()
    finally:
        db.close()


def mark_book_failed(livro_id: int, message: str) -> None:
    db = SessionLocal()
    try:
        livro = db.get(Livro, livro_id)
        task = db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        if task:
            task.status = "falhou"
            task.erro = message[:2000]
        if livro:
            livro.status = "falhou"
        db.commit()
    finally:
        db.close()

"""Document text extraction for PDF, EPUB, and TXT files."""

from __future__ import annotations

import re
from enum import Enum
from html import unescape
from pathlib import Path

import ebooklib
import fitz
from ebooklib import epub
from pydantic import BaseModel, Field

from app.config import settings

PAGE_MARKER = "===PAGINA==="


class DocumentType(str, Enum):
    PDF = "pdf"
    EPUB = "epub"
    TXT = "txt"


_EXTENSION_TO_TYPE: dict[str, DocumentType] = {}


class Page(BaseModel):
    numero: int
    texto: str


class ChapterInfo(BaseModel):
    """Chapter with its page range for export-by-chapter."""
    numero: int
    titulo: str
    pagina_inicio: int
    pagina_fim: int


class PageExtractionResult(BaseModel):
    chapters: list[str] = Field(default_factory=list)
    chapter_pages: list[ChapterInfo] = Field(default_factory=list)
    pages: list[Page] = Field(default_factory=list)


class PDFProcessorError(Exception):
    """Base error for document extraction."""


class UnsupportedFormatError(PDFProcessorError):
    """Raised when the file extension is not supported."""

    def __init__(self, extension: str) -> None:
        self.extension = extension
        super().__init__(f"formato não suportado: {extension}")


class FileSizeExceededError(PDFProcessorError):
    """Raised when the file exceeds the configured maximum size."""

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        super().__init__(
            f"tamanho excedido: arquivo com {size_bytes} bytes "
            f"(máximo permitido: {max_bytes} bytes)"
        )


class CorruptedFileError(PDFProcessorError):
    """Raised when the file cannot be parsed."""

    def __init__(self, file_path: str, detail: str) -> None:
        self.file_path = file_path
        self.detail = detail
        super().__init__(f"arquivo corrompido ou ilegível: {detail}")


class EmptyFileError(PDFProcessorError):
    """Raised when the file has no content."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        super().__init__(f"arquivo vazio: {file_path}")


def _register_extensions() -> None:
    _EXTENSION_TO_TYPE.clear()
    _EXTENSION_TO_TYPE.update(
        {
            ".pdf": DocumentType.PDF,
            ".epub": DocumentType.EPUB,
            ".txt": DocumentType.TXT,
        }
    )


_register_extensions()


class PDFProcessor:
    """Extracts text from PDF, EPUB, and TXT documents."""

    def __init__(self, max_file_size_bytes: int | None = None) -> None:
        if max_file_size_bytes is None:
            max_file_size_bytes = settings.max_upload_size_mb * 1024 * 1024
        self._max_file_size_bytes = max_file_size_bytes

    def extrair(self, file_path: str) -> PageExtractionResult:
        """Detect format by extension and extract text."""
        return self.extract_text(file_path)

    def extract_text(self, file_path: str) -> PageExtractionResult:
        """Detect format by extension and extract text."""
        path = Path(file_path)
        self._validate_file(path)
        doc_type = self._detect_type(path)

        if doc_type is DocumentType.PDF:
            return self._extrair_pdf(path)
        if doc_type is DocumentType.EPUB:
            return self._extrair_epub(path)
        return self._extrair_txt(path)

    def _validate_file(self, path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"arquivo não encontrado: {path}")

        size = path.stat().st_size
        if size == 0:
            raise EmptyFileError(str(path))
        if size > self._max_file_size_bytes:
            raise FileSizeExceededError(size, self._max_file_size_bytes)

    def _detect_type(self, path: Path) -> DocumentType:
        extension = path.suffix.lower()
        doc_type = _EXTENSION_TO_TYPE.get(extension)
        if doc_type is None:
            raise UnsupportedFormatError(extension or "(sem extensão)")
        return doc_type

    def _extrair_pdf(self, path: Path) -> PageExtractionResult:
        doc: fitz.Document | None = None
        try:
            doc = fitz.open(path)
        except Exception as exc:  # noqa: BLE001 — fitz raises several types
            raise CorruptedFileError(str(path), str(exc)) from exc

        try:
            toc = self._pdf_toc(doc)
            pages: list[Page] = []
            for index in range(doc.page_count):
                page = doc[index]
                raw_text = page.get_text("text")
                cleaned = self._limpar_texto(raw_text)
                if cleaned:
                    pages.append(Page(numero=index + 1, texto=cleaned))

            chapter_pages = self._map_chapters_to_pages(toc, pages)
            chapters = [c.titulo for c in chapter_pages]

            return PageExtractionResult(
                chapters=chapters,
                chapter_pages=chapter_pages,
                pages=pages,
            )
        finally:
            if doc is not None:
                doc.close()

    def _pdf_toc(self, doc: fitz.Document) -> list[tuple]:
        """Return doc.get_toc() with page numbers (1-indexed)."""
        try:
            toc = doc.get_toc() or []
        except Exception:  # noqa: BLE001
            return []
        enriched: list[tuple] = []
        for entry in toc:
            if len(entry) >= 3:
                # [level, title, [page_number, ...]]
                page_num = int(entry[2][0]) if entry[2] else 0
                enriched.append((entry[0], entry[1], page_num))
            elif len(entry) == 2 and entry[1]:
                enriched.append((entry[0], entry[1], 0))
        return enriched

    @staticmethod
    def _map_chapters_to_pages(
        toc: list[tuple], pages: list[Page]
    ) -> list[ChapterInfo]:
        """Map TOC entries to page ranges based on page numbers."""
        if not toc:
            return []

        total_pages = len(pages)
        if total_pages == 0:
            return []

        result: list[ChapterInfo] = []
        for idx, entry in enumerate(toc):
            if len(entry) >= 3 and entry[2] and entry[1]:
                start = max(1, int(entry[2])) - 1  # 0-indexed
                if start >= total_pages:
                    continue
                if idx + 1 < len(toc):
                    next_entry = toc[idx + 1]
                    if len(next_entry) >= 3 and next_entry[2] and next_entry[2]:
                        end = max(start + 1, int(next_entry[2]) - 1)
                    else:
                        end = total_pages - 1
                else:
                    end = total_pages - 1
                end = min(end, total_pages - 1)
                result.append(ChapterInfo(
                    numero=len(result) + 1,
                    titulo=str(entry[1]).strip(),
                    pagina_inicio=start + 1,
                    pagina_fim=end + 1,
                ))
        return result

    def _extrair_epub(self, path: Path) -> PageExtractionResult:
        try:
            book = epub.read_epub(str(path))
        except Exception as exc:  # noqa: BLE001
            raise CorruptedFileError(str(path), str(exc)) from exc

        chapters = self._epub_chapter_titles(book)
        pages: list[Page] = []
        page_num = 0

        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            raw_html = item.get_content()
            if isinstance(raw_html, bytes):
                html = raw_html.decode("utf-8", errors="replace")
            else:
                html = str(raw_html)
            text = self._limpar_texto(self._html_to_text(html))
            if not text:
                continue
            page_num += 1
            pages.append(Page(numero=page_num, texto=text))

        return PageExtractionResult(chapters=chapters, pages=pages)

    def _epub_chapter_titles(self, book: epub.EpubBook) -> list[str]:
        titles: list[str] = []

        def walk_toc(toc: list) -> None:
            for entry in toc:
                if isinstance(entry, tuple):
                    link = entry[0]
                    if hasattr(link, "title") and link.title:
                        titles.append(str(link.title).strip())
                    if len(entry) > 1 and entry[1]:
                        walk_toc(entry[1])
                elif hasattr(entry, "title") and entry.title:
                    titles.append(str(entry.title).strip())

        walk_toc(book.toc or [])
        return titles

    def _extrair_txt(self, path: Path) -> PageExtractionResult:
        raw_bytes = path.read_bytes()
        text = self._decode_text(raw_bytes)
        if not text.strip():
            return PageExtractionResult(chapters=[], pages=[])

        if PAGE_MARKER in text:
            parts = text.split(PAGE_MARKER)
        else:
            parts = [text]

        pages: list[Page] = []
        for index, part in enumerate(parts, start=1):
            cleaned = self._limpar_texto(part)
            if cleaned:
                pages.append(Page(numero=index, texto=cleaned))

        return PageExtractionResult(chapters=[], pages=pages)

    def _decode_text(self, raw_bytes: bytes) -> str:
        for encoding in ("utf-8", "latin-1"):
            try:
                return raw_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw_bytes.decode("utf-8", errors="replace")

    @staticmethod
    def _html_to_text(html: str) -> str:
        without_blocks = re.sub(
            r"(?is)<(script|style)[^>]*>.*?</\1>",
            " ",
            html,
        )
        with_breaks = re.sub(
            r"(?i)</(p|div|h[1-6]|li|br|tr|section|article)>",
            "\n",
            without_blocks,
        )
        stripped = re.sub(r"<[^>]+>", " ", with_breaks)
        return unescape(stripped)

    @staticmethod
    def _limpar_texto(texto: str) -> str:
        """Normalize whitespace and drop non-Portuguese non-ASCII characters."""
        if not texto:
            return ""

        cleaned_chars: list[str] = []
        for char in texto:
            if char in "\n\r\t":
                cleaned_chars.append(" ")
                continue
            code = ord(char)
            if 32 <= code <= 126:
                cleaned_chars.append(char)
            elif 0xC0 <= code <= 0xFF:
                cleaned_chars.append(char)

        normalized = re.sub(r"\s+", " ", "".join(cleaned_chars))
        return normalized.strip()

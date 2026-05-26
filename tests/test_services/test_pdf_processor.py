"""Unit tests for PDFProcessor (PDF / EPUB / TXT extraction)."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from ebooklib import epub

from app.services.pdf_processor import (
    CorruptedFileError,
    EmptyFileError,
    FileSizeExceededError,
    PDFProcessor,
    UnsupportedFormatError,
)


@pytest.fixture()
def processor() -> PDFProcessor:
    return PDFProcessor()


@pytest.fixture()
def small_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Primeira pagina do livro.")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Segunda pagina com mais texto.")
    doc.save(path)
    doc.close()
    return path


@pytest.fixture()
def sample_epub(tmp_path: Path) -> Path:
    path = tmp_path / "sample.epub"
    book = epub.EpubBook()
    book.set_identifier("book-ia-test-epub")
    book.set_title("Livro Teste")
    book.set_language("pt")

    chapter = epub.EpubHtml(
        title="Capitulo 1",
        file_name="capitulo_1.xhtml",
        lang="pt",
    )
    chapter.content = (
        "<html><body>"
        "<h1>Capitulo 1</h1>"
        "<p>Texto do capitulo com acentuacao: acao, coracao.</p>"
        "</body></html>"
    )
    book.add_item(chapter)
    book.toc = [(chapter, [])]
    book.spine = ["nav", chapter]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)
    return path


class TestLimparTexto:
    def test_normaliza_espacos(self) -> None:
        assert PDFProcessor._limpar_texto("texto  com   espacos") == "texto com espacos"

    def test_mantem_acentuacao_portuguesa(self) -> None:
        original = "Sao Joao: acao, coracao, ninguem, voce, cafe"
        assert PDFProcessor._limpar_texto(original) == original

    def test_remove_caracteres_nao_ascii_sem_acentos_latinos(self) -> None:
        result = PDFProcessor._limpar_texto("Ola 世界 emoji 🎉 fim")
        assert "世界" not in result
        assert "🎉" not in result
        assert "Ola" in result
        assert "fim" in result


class TestExtrairPdf:
    def test_extrai_paginas_de_pdf(self, processor: PDFProcessor, small_pdf: Path) -> None:
        result = processor.extrair(str(small_pdf))

        assert len(result.pages) == 2
        assert result.pages[0].numero == 1
        assert result.pages[1].numero == 2
        assert "Primeira" in result.pages[0].texto
        assert "Segunda" in result.pages[1].texto

    def test_pdf_sem_paginas_utilizaveis_retorna_lista_vazia(
        self, processor: PDFProcessor, tmp_path: Path
    ) -> None:
        path = tmp_path / "empty_pages.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(path)
        doc.close()

        result = processor._extrair_pdf(path)

        assert result.pages == []


class TestExtrairEpub:
    def test_extrai_capitulos_e_paginas(
        self, processor: PDFProcessor, sample_epub: Path
    ) -> None:
        result = processor.extrair(str(sample_epub))

        assert len(result.chapters) >= 1
        assert "Capitulo 1" in result.chapters[0]
        assert len(result.pages) >= 1
        assert "acentuacao" in result.pages[0].texto or "acao" in result.pages[0].texto


class TestExtrairTxt:
    def test_le_utf8_com_acentos(self, processor: PDFProcessor, tmp_path: Path) -> None:
        path = tmp_path / "livro.txt"
        path.write_text(
            "Introducao com acentuacao: nao, coracao, situacao.\n",
            encoding="utf-8",
        )

        result = processor.extrair(str(path))

        assert len(result.pages) == 1
        assert "coracao" in result.pages[0].texto
        assert "nao" in result.pages[0].texto

    def test_arquivo_vazio_retorna_listas_vazias(
        self, processor: PDFProcessor, tmp_path: Path
    ) -> None:
        path = tmp_path / "vazio_conteudo.txt"
        path.write_bytes(b"   \n\t  ")

        result = processor._extrair_txt(path)

        assert result.pages == []
        assert result.chapters == []

    def test_respeita_marcador_pagina(self, processor: PDFProcessor, tmp_path: Path) -> None:
        path = tmp_path / "paginado.txt"
        path.write_text(
            "Pagina um\n===PAGINA===\nPagina dois\n",
            encoding="utf-8",
        )

        result = processor._extrair_txt(path)

        assert len(result.pages) == 2
        assert "Pagina um" in result.pages[0].texto
        assert "Pagina dois" in result.pages[1].texto


class TestExtrairErros:
    def test_arquivo_vazio_levanta_erro(
        self, processor: PDFProcessor, tmp_path: Path
    ) -> None:
        path = tmp_path / "empty.txt"
        path.write_bytes(b"")

        with pytest.raises(EmptyFileError, match="arquivo vazio"):
            processor.extrair(str(path))

    def test_arquivo_corrompido_levanta_erro(
        self, processor: PDFProcessor, tmp_path: Path
    ) -> None:
        path = tmp_path / "bad.pdf"
        path.write_bytes(b"not a real pdf content")

        with pytest.raises(CorruptedFileError, match="corrompido"):
            processor.extrair(str(path))

    def test_formato_nao_suportado(
        self, processor: PDFProcessor, tmp_path: Path
    ) -> None:
        path = tmp_path / "arquivo.zip"
        path.write_bytes(b"PK\x03\x04")

        with pytest.raises(UnsupportedFormatError, match="formato não suportado"):
            processor.extrair(str(path))

    def test_tamanho_excedido(
        self, processor: PDFProcessor, tmp_path: Path
    ) -> None:
        limit = 1024
        small_processor = PDFProcessor(max_file_size_bytes=limit)
        path = tmp_path / "grande.pdf"
        with path.open("wb") as handle:
            handle.write(b"%PDF-1.4\n")
            handle.seek(limit + 1)
            handle.write(b"\0")

        with pytest.raises(FileSizeExceededError, match="tamanho excedido"):
            small_processor.extrair(str(path))


class TestIntegracaoExtrair:
    def test_pdf_retorna_estrutura_completa(
        self, processor: PDFProcessor, small_pdf: Path
    ) -> None:
        result = processor.extract_text(str(small_pdf))

        assert isinstance(result.chapters, list)
        assert len(result.pages) >= 1

    def test_epub_retorna_capitulos_e_texto(
        self, processor: PDFProcessor, sample_epub: Path
    ) -> None:
        result = processor.extract_text(str(sample_epub))

        assert result.chapters
        assert result.pages
        assert result.pages[0].numero == 1


class TestFixtureFiles:
    def test_pdf_10_paginas_extrai_10(
        self, processor: PDFProcessor, fixture_pdf_10_pages: Path
    ) -> None:
        result = processor.extrair(str(fixture_pdf_10_pages))
        assert len(result.pages) == 10
        assert result.pages[0].numero == 1
        assert result.pages[9].numero == 10

    def test_epub_5_capitulos_extrai_5(
        self, processor: PDFProcessor, fixture_epub_5_chapters: Path
    ) -> None:
        result = processor.extrair(str(fixture_epub_5_chapters))
        assert len(result.pages) == 5
        assert len(result.chapters) >= 1

    def test_txt_fixture_utf8_com_acentos(
        self, processor: PDFProcessor, fixture_txt_utf8: Path
    ) -> None:
        result = processor.extrair(str(fixture_txt_utf8))
        assert len(result.pages) == 2
        assert "coracao" in result.pages[0].texto

    def test_txt_fixture_conteudo_vazio(
        self, processor: PDFProcessor, fixture_txt_empty_content: Path
    ) -> None:
        result = processor._extrair_txt(fixture_txt_empty_content)
        assert result.pages == []


class TestPdfGrande:
    def test_pdf_mais_de_1000_paginas_nao_estoura_memoria(
        self, processor: PDFProcessor, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mock fitz document with 1001 pages to verify iteration without OOM."""
        path = tmp_path / "huge.pdf"
        path.write_bytes(b"%PDF-mock")

        class FakePage:
            def get_text(self, mode: str) -> str:
                return "Texto da pagina simulada."

        class FakeDoc:
            page_count = 1001

            def __getitem__(self, index: int) -> FakePage:
                return FakePage()

            def get_toc(self) -> list:
                return []

            def close(self) -> None:
                pass

        def fake_open(p: Path) -> FakeDoc:
            return FakeDoc()

        monkeypatch.setattr(fitz, "open", fake_open)
        result = processor._extrair_pdf(path)
        assert len(result.pages) == 1001
        assert result.pages[0].numero == 1
        assert result.pages[-1].numero == 1001

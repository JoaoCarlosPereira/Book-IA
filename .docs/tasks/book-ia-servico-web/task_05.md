---
status: pending
title: PDF Processor com suporte multi-formato (PDF/EPUB/TXT)
type: backend
complexity: medium
dependencies:
  - task_01
---

# Tarefa 05: PDF Processor com suporte multi-formato (PDF/EPUB/TXT)

## Visão Geral
Implementar serviço de extração de texto de documentos com suporte a PDF (PyMuPDF), EPUB (ebooklib) e TXT (leitura direta). Substitui o script `extrair_pdf.py` como módulo Python integrado.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- `extract_text(file_path: str) -> PageExtractionResult` DEVE detectar formato pelo extension e extrair texto
- PDF DEVE usar PyMuPDF (`fitz`) para extração de texto página por página
- EPUB DEVE usar `ebooklib` para extração de capítulos e texto
- TXT DEVE ler o arquivo como texto puro com detecção de encoding (utf-8, latin-1)
- O resultado DEVE incluir lista de páginas com `numero` e `texto`
- O resultado DEVE incluir lista de capítulos (para PDF e EPUB)
- Texto extraído DEVE limpar caracteres especiais não-ASCII (mantendo acentuação)
- Tratamento de erro: arquivo corrompido, formato não suportado, arquivo vazio

## Subtarefas
- [ ] Criar `backend/app/services/pdf_processor.py` com classe `PDFProcessor`
- [ ] Implementar `_extrair_pdf(file_path)` — PyMuPDF página por página
- [ ] Implementar `_extrair_epub(file_path)` — ebooklib capítulo por capítulo
- [ ] Implementar `_extrair_txt(file_path)` — leitura direta com detecção de encoding
- [ ] Implementar `_limpar_texto(texto)` — remove caracteres não-ASCII, normaliza espaços
- [ ] Implementar método público `extrair(file_path) -> PageExtractionResult`
- [ ] Adicionar detecção de tipo por extensão de arquivo
- [ ] Adicionar validação de tamanho máximo (padrão: 50 MB)
- [ ] Adicionar tratamento de erros para arquivos corrompidos e formatos inválidos

## Detalhes de Implementação

### Interface baseada no TechSpec
- Ver seção "Interfaces Principais — Service de Processamento de PDF" do TechSpec
- `PageExtractionResult` com `chapters: list[str]` e `pages: list[Page]`
- `Page` com `numero: int` e `texto: str`

### Arquivos Relevantes
- `src/dpr/Win32/Debug/extrair_pdf.py` — Script existente; migrar lógica para módulo Python
- `src/pas/PDF/Rgn.Leitor.PDF.pas` — Referenciar `LerPDFPorPagina` para entender fluxo original

### Arquivos Dependentes
- `backend/app/models/pagina.py` (task_02) — Modelo para salvar resultados

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define PyMuPDF + ebooklib como bibliotecas de extração

## Entregáveis
- Serviço `pdf_processor.py` funcional com suporte a PDF/EPUB/TXT
- Limpeza de texto com remoção de caracteres não-ASCII
- Testes unitários: extração de cada formato, limpeza de texto, tratamento de erros
- Testes de integração: extração de arquivo real (fixtures)

## Testes
- Testes unitários:
  - [ ] `_extrair_pdf` extrai texto de PDF de 10 páginas corretamente
  - [ ] `_extrair_pdf` de PDF com 0 páginas retorna lista vazia
  - [ ] `_extrair_pdf` de PDF com > 1000 páginas não estoura memória
  - [ ] `_extrair_epub` extrai capítulos e texto de EPUB real
  - [ ] `_extrair_txt` lê arquivo UTF-8 com acentos corretamente
  - [ ] `_extrair_txt` de arquivo vazio retorna lista vazia
  - [ ] `_limpar_texto("texto  com   espaços")` normaliza para "texto com espaços"
  - [ ] `_limpar_texto` remove caracteres não-ASCII mas mantém acentuação (ã, ã, ç, é, í)
  - [ ] `extrair(arquivo_corrompido.pdf)` retorna erro descritivo
  - [ ] `extrair(arquivo.zip)` retorna erro "formato não suportado"
  - [ ] `extrair(arquivo_51mb.pdf)` retorna erro "tamanho excedido"
- Testes de integração:
  - [ ] `extrair(livro_teste.pdf)` retorna PageExtractionResult com páginas e capítulos
  - [ ] `extrair(livro_teste.epub)` retorna PageExtractionResult com capítulos e texto

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- Extração funcional para PDF, EPUB e TXT
- Limpeza de texto funciona corretamente
- Tratamento de erros para todos os cenários de falha

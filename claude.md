# Book-IA (Leitor) - Documentação Técnica

Este documento serve como referência técnica para o projeto **Book-IA**, um sistema automatizado para processamento de livros em PDF e geração de audiobooks enriquecidos com IA.

## Índice
- [Objetivo do Projeto](#objetivo-do-projeto)
- [Funcionalidades Principais](#funcionalidades-principais)
- [Arquitetura e Tecnologias](#arquitetura-e-tecnologias)
- [Estrutura de Pastas](#estrutura-de-pastas)
- [Fluxo de Execução](#fluxo-de-execução)
- [Integrações e APIs](#integrações-e-apis)
- [Banco de Dados](#banco-de-dados)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Scripts e Comandos Úteis](#scripts-e-comandos-úteis)
- [Melhorias e Riscos](#melhorias-e-riscos)

---

## Objetivo do Projeto
O **Book-IA** (executável `Leitor.exe`) é um serviço de console desenvolvido em Delphi que monitora um diretório de entrada para livros em PDF. O sistema extrai o conteúdo textual, utiliza Inteligência Artificial para identificar personagens, narradores e tons emocionais, e gera um audiobook completo com vozes distintas e trilha sonora contextual.

---

## Funcionalidades Principais
1.  **Extração de Texto:** Processamento de PDFs preservando a estrutura de páginas.
2.  **Análise de Conteúdo via IA:**
    - Separação entre narração e falas de personagens.
    - Normalização de nomes de personagens (agrupamento de apelidos/referências).
    - Perfilamento de personagens (Gênero e Idade aparente).
3.  **Geração de Áudio (TTS):**
    - Atribuição automática de vozes baseada no perfil do personagem.
    - Quebra de texto em chunks otimizados para APIs de TTS.
    - Produção de arquivos de áudio individuais por trecho.
4.  **Trilha Sonora (MusicGen):**
    - Geração de prompts em inglês baseados na atmosfera do capítulo/livro.
    - Criação de trilhas instrumentais cinematográficas para fundo musical.
5.  **Persistência:** Histórico completo de processamento em banco de dados PostgreSQL.

---

## Arquitetura e Tecnologias
-   **Linguagem Principal:** Delphi (Object Pascal) - RAD Studio.
-   **Scripting:** Python 3.13 (utilizado para extração de PDFs via PyMuPDF/fitz).
-   **Banco de Dados:** PostgreSQL.
-   **Processamento Paralelo:** OmniThreadLibrary (OTL).
-   **IA Generativa (LLM):**
    -   **Online:** Google Gemini 2.0 Flash API.
    -   **Local:** Ollama (modelo Gemma 3 ou similar).
-   **Audio/TTS:** Integração customizada com APIs locais de TTS e MusicGen.
-   **Tratamento de Erros:** madExcept.

---

## Estrutura de Pastas
-   `src/dpr/`: Arquivos de projeto Delphi (`.dpr`, `.dproj`).
-   `src/pas/`: Código-fonte principal.
    -   `Book/`: Lógica de negócio relacionada ao livro (Personagens, Narrador, Vozes).
    -   `PDF/`: Integração com scripts de extração de PDF.
    -   `Shared/`: Utilitários, Singletons, Fábricas de Threads e classes de comunicação REST.
-   `src/Win32/Debug/` / `Release/`: Binários e scripts auxiliares (`extrair_pdf.py`).
-   `sql/`: Scripts de estrutura do banco de dados PostgreSQL.
-   `unittest/`: Testes unitários e ambiente de testes.

---

## Fluxo de Execução
O programa opera em um loop contínuo (`Monitorar`):

1.  **Monitoramento:** Verifica a pasta `S:\dsv\NLP\pdfs\processar`.
2.  **Ingestão:**
    - Chama `extrair_pdf.py` para converter PDF em TXT com marcadores `===PAGINA===`.
    - Salva as páginas brutas na tabela `TB_LIVROPAGINA`.
3.  **Análise de Personagens (`ObterPersonagens`):**
    - Envia trechos de texto para IA com prompt especializado para extrair `nome|fala`.
    - **Normalização:** IA agrupa variações de nomes e define o gênero.
    - **Perfilamento:** IA define idade (Criança, Adulto, Idoso) baseada no vocabulário.
4.  **Análise de Narrador (`ObterNarrador`):** Define o perfil de voz do narrador.
5.  **Produção de Áudio (`ObterVozes`):**
    - Associa vozes disponíveis (`TB_LIVROPERSONAGENS`) aos perfis identificados.
    - Envia chunks de texto para a API de TTS.
    - Gera prompt atmosférico e solicita criação de trilha sonora via MusicGen.
6.  **Finalização:** Move o PDF original para a pasta `processado` e reinicia o ciclo.

---

## Integrações e APIs
-   **LLM API (Online):** Gemini 2.0 Flash (`https://generativelanguage.googleapis.com`).
-   **LLM API (Local):** Ollama no IP `192.168.2.183:11434`.
-   **TTS API:** Serviço local no IP `192.168.2.184:8001` (endpoint `/generate-from-text`).
-   **MusicGen API:** Serviço local no IP `192.168.2.184:8002` (endpoint `/generate-from-text`).

---

## Banco de Dados
A estrutura principal consiste em:
-   `TB_LIVROCABECALHO`: Metadados do livro e status de processamento.
-   `TB_LIVROPAGINA`: Conteúdo textual dividido por páginas.
-   `TB_LIVROPERSONAGENS`: Lista de personagens únicos identificados, perfis e vozes atribuídas.
-   `TB_LIVROFALAS`: Mapeamento de cada fala ao seu personagem, página e arquivo de áudio resultante.
-   `TB_LIVROAPIS`: Gerenciamento de chaves de API.

---

## Configuração do Ambiente
-   **Python:** Necessário Python 3.13 instalado com a biblioteca `pymupdf`.
-   **Paths:**
    -   Entrada: `S:\dsv\NLP\pdfs\processar`
    -   Saída de Áudio: `S:\dsv\TTS\out\[Nome_do_Livro]\partes\`
-   **Banco de Dados:** Configuração de conexão no `dbxconnections.ini`.

---

## Scripts e Comandos Úteis
-   **Extração Manual:** `python extrair_pdf.py caminho_do_livro.pdf`
-   **Limpeza de Logs:** O sistema gera `LogErro.log` em caso de falhas críticas.
-   **Reinicialização:** O programa possui uma rotina `RestartSelf` que o reinicia automaticamente para limpar memória ou recuperar-se de erros de conexão.

---

## Melhorias e Riscos
-   **Risco Técnico:** Dependência de caminhos hardcoded (ex: `S:\dsv\`, `C:\Users\s293\...`). Recomenda-se mover para arquivo de configuração (`.ini` ou `.env`).
-   **Melhoria:** Implementar um dashboard web para acompanhar o progresso das filas de processamento.
-   **Gargalo:** O tempo de processamento de áudio (TTS) é o maior limitador; a implementação atual utiliza envio sequencial de chunks.
-   **Conexão:** A IA alterna automaticamente entre modo Online e Local caso atinja limites de quota (Rate Limit).

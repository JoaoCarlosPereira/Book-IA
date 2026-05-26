---
status: pending
title: TTSEngine — chunking de texto, chamada TTS API, conversão WAV→MP3
type: backend
complexity: high
dependencies:
  - task_02, task_04, task_06
---

# Tarefa 08: TTSEngine — chunking de texto, chamada TTS API, conversão WAV→MP3

## Visão Geral
Implementar o motor de TTS que chunka texto, envia para API de TTS, baixa WAV e converte para MP3. Substitui `Rgn.Leitor.Book.Vozes.pas` e `Rgn.Leitor.Book.VozesHttp.pas`.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- `TTSEngine` DEVE chunkar texto em blocos de ~180 caracteres (ajustável)
- Chunking DEVE ser feito em limites de sentença (pontos finais) quando possível
- Se um chunk não tem limite natural, dividir no espaço mais próximo
- Nunca enviar "." isolado para TTS (substituir por "," para pausa natural)
- `gerar_audio(texto, personagem) -> str` DEVE retornar caminho do arquivo MP3 unificado
- Cada chunk DEVE ser enviado para TTS API via HTTP POST
- Resposta da TTS API (WAV) DEVE ser baixada e convertida para MP3 via ffmpeg
- Trechos DEVE ser unificados em um único arquivo por personagem
- Retry com backoff exponencial: 3 tentativas para TTS API
- Timeout configurável: 120s por chunk
- Salvar caminhos dos arquivos no modelo `arquivo`

## Subtarefas
- [ ] Criar `backend/app/services/tts_engine.py` com classe `TTSEngine`
- [ ] Implementar `_chunkar_texto(texto, max_chars=180) -> list[str]` — divisão inteligente
- [ ] Implementar `_post_to_tts_api(texto_chunk) -> str` — envia para TTS, recebe WAV
- [ ] Implementar `_converter_wav_para_mp3(wav_path) -> str` — ffmpeg
- [ ] Implementar `_unificar_arquivos(arquivos_mp3) -> str` — ffmpeg concat
- [ ] Implementar `gerar_audio(texto, personagem) -> str` — pipeline completo
- [ ] Implementar retry com backoff exponencial para chamadas TTS API
- [ ] Configurar timeout de 120s por chamada
- [ ] Tratar erros: TTS API indisponível, timeout, resposta inválida

## Detalhes de Implementação

### Interface baseada no TechSpec
- Ver seção "Interfaces Principais — Engine de TTS" do TechSpec
- TTSEngine com `api_url`, `api_key` opcional
- `gerar_audio(texto, personagem)` retorna caminho do arquivo

### Pipeline TTS original (referência)
- `src/pas/Book/Vozes/Rgn.Leitor.Book.VozesHttp.pas` — Endpoints TTS original (porta 8001)
- `src/pas/Book/Vozes/Rgn.Leitor.Book.Vozes.pas` — Lógica de chunking original (50-100 chars)
- `src/pas/Book/Vozes/Rgn.Leitor.Book.Vozes.pas` — Método `Unificar` com `unir.bat`

### Arquivos Relevantes
- `src/pas/Book/Vozes/Rgn.Leitor.Book.VozesHttp.pas` — Endpoints TTS original: `localhost:8001/generate-from-text`, `localhost:8001/merge-wavs`
- `src/pas/Book/Vozes/Rgn.Leitor.Book.Vozes.pas` — Lógica de chunking e unificação

### Arquivos Dependentes
- `backend/app/models/arquivo.py` (task_02) — Para salvar caminhos de arquivos de áudio
- `backend/app/services/api_config_service.py` (task_04) — Para ler URL da TTS API

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define httpx + ffmpeg como ferramentas de TTS

## Entregáveis
- `tts_engine.py` com TTSEngine completo
- Chunking inteligente de texto (sentença > limite de caracteres > espaço)
- Chamada TTS API com retry e timeout
- Conversão WAV→MP3 via ffmpeg
- Unificação de trechos em arquivo único
- Testes unitários: chunking, mock TTS API, ffmpeg
- Testes de integração: pipeline completo com TTS API mockada

## Testes
- Testes unitários:
  - [ ] `_chunkar_texto("texto com várias sentenças.", max_chars=180)` divide em chunks por sentença
  - [ ] `_chunkar_texto` de texto longo (> 500 chars) gera múltiplos chunks
  - [ ] `_chunkar_texto` de texto sem "." (ponto) divide em limites de palavra
  - [ ] `_chunkar_texto` não envia "." isolado para TTS (substitui por ",")
  - [ ] `_chunkar_texto` de 180 chars exatos retorna um chunk
  - [ ] `_chunkar_texto` de 179 chars retorna um chunk (não quebra)
- Testes de integração:
  - [ ] `gerar_audio("texto teste", "personagem")` retorna caminho de arquivo MP3 válido
  - [ ] `gerar_audio` com TTS API indisponível retry 3x e retorna erro
  - [ ] `gerar_audio` com timeout retorna erro descritivo

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- Chunking funciona corretamente (sentença → caracteres → espaço)
- TTS API é chamada com retry e timeout
- Conversão WAV→MP3 funciona
- Arquivo final unificado é criado corretamente

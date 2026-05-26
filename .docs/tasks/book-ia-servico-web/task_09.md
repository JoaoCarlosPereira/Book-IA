---
status: pending
title: MusicGen — geração de prompt, chamada API, salvamento de trilha
type: backend
complexity: high
dependencies:
  - task_02, task_04, task_06
---

# Tarefa 09: MusicGen — geração de prompt, chamada API, salvamento de trilha

## Visão Geral
Implementar o serviço de geração de trilha sonora usando MusicGen. Inclui geração de prompt atmosférico por IA (com fallback cloud/local via IA Analyzer) e chamada à API MusicGen para gerar áudio instrumental.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- `MusicGenService` DEVE gerar prompt atmosférico usando IA Analyzer (reutiliza task_07)
- Prompt DEVE ser gerado em inglês baseado na atmosfera/emotional tone do texto
- `gerar_trilha(texto_excerpto, nivel_producao) -> str` DEVE retornar caminho do arquivo de trilha
- Livros com duração > 300 segundos DEVE gerar trilha por página
- Livros com duração <= 300 segundos DEVE gerar trilha única para todo o livro
- Chamada MusicGen DEVE usar endpoint configurável (cloud ou local)
- Retry com backoff exponencial: 3 tentativas
- Timeout configurável: 180s por geração
- Salvar caminho da trilha no modelo `arquivo` com tipo "trilha"

## Subtarefas
- [ ] Criar `backend/app/services/musicgen.py` com classe `MusicGenService`
- [ ] Implementar `_gerar_prompt_atmosferico(texto_excerpto, tempo_inicio, tempo_fim) -> str`
- [ ] Implementar `_chamar_musicgen(prompt) -> str` — HTTP POST para MusicGen API
- [ ] Implementar `gerar_trilha(texto_excerpto, nivel_producao, tempo_inicio=0, tempo_fim=0) -> str`
- [ ] Implementar lógica de trilha por página vs. trilha única (baseado em duração)
- [ ] Implementar retry com backoff exponencial
- [ ] Configurar timeout de 180s por chamada
- [ ] Salvar caminho no modelo `arquivo` (tipo "trilha")

## Detalhes de Implementação

### Prompt atmosférico
- Enviar ao LLM: trecho de texto do livro + timestamp (tempo_inicio, tempo_fim)
- Receber: descrição em inglês para MusicGen (ex: "cinematic orchestral, tense atmosphere, minor key, slow tempo")
- Reutilizar IA Analyzer (task_07) para geração do prompt

### Interface baseada no TechSpec
- Ver seção "Pontos de Integração — Integração com Serviços de IA" do TechSpec
- MusicGen endpoint configurável (padrão: localhost:8002/generate-from-text)

### Arquivos Relevantes
- `src/pas/Book/Vozes/Rgn.Leitor.Book.Vozes.pas` — Método `CriarTrilha()` original; referencia lógica de per-page vs. única
- `src/pas/Book/Vozes/Rgn.Leitor.Book.VozesHttp.pas` — Endpoint MusicGen original (porta 8002)

### Arquivos Dependentes
- `backend/app/models/arquivo.py` (task_02) — Para salvar caminho de trilha
- `backend/app/services/ia_analyzer.py` (task_07) — Para gerar prompt atmosférico
- `backend/app/services/api_config_service.py` (task_04) — Para ler URL MusicGen API

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define MusicGen como serviço configurável

## Entregáveis
- `musicgen.py` com MusicGenService completo
- Prompt atmosférico gerado por IA
- Chamada MusicGen API com retry e timeout
- Lógica por-página vs. trilha única (baseado em duração)
- Salvamento de caminho no modelo `arquivo`
- Testes unitários: geração de prompt, mock MusicGen API
- Testes de integração: pipeline completo com MusicGen API mockada

## Testes
- Testes unitários:
  - [ ] `_gerar_prompt_atmosferico("trecho triste", 0, 300)` retorna string em inglês
  - [ ] `_gerar_prompt_atmosferico` gera prompt diferente para texto alegre vs. triste
  - [ ] `_chamar_musicgen` com API mockada retorna caminho de arquivo
  - [ ] `_chamar_musicgen` com API indisponível retry 3x e retorna erro
  - [ ] `gerar_trilha` com duração > 300s gera trilha por página
  - [ ] `gerar_trilha` com duração <= 300s gera trilha única
- Testes de integração:
  - [ ] `MusicGenService` com API MusicGen mockada gera trilha sonora
  - [ ] `MusicGenService` com IA Analyzer indisponível retorna erro (não consegue gerar prompt)

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- Prompt atmosférico gerado corretamente por IA
- MusicGen API é chamada com retry e timeout
- Lógica por-página vs. única funciona corretamente
- Caminho da trilha é salvo no banco

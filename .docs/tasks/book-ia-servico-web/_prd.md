# PRD — Book-IA: Serviço Web de Conversão de PDF em Audiobook com IA

> **Versão:** 1.0
> **Data:** 2026-05-25
> **Status:** Rascunho para revisão

---

## Visão Geral

O **Book-IA** é um serviço web para conversão automática de livros em PDF em audiobooks produzidos com inteligência artificial. O sistema extrai o texto do PDF, identifica personagens e narradores, atribui vozes distintas a cada um e gera um audiobook completo com trilha sonora contextual.

**Problema que resolve:** Produzir um audiobook profissional custa entre US$ 2.000 e US$ 50.000 e leva semanas ou meses. O Book-IA reduz esse custo para uma assinatura acessível e o tempo de produção para minutos.

**Para quem é:** Editoras e produtoras que processam livros em volume, e usuários individuais que desejam transformar seus próprios livros em audiobook.

**Por que é valioso:** Democratiza a produção de audiobooks — o formato está em crescimento de 22% ao ano, com plataformas como Spotify registrando 1 milhão de assinantes Audiobook+ e 60% de aumento no consumo ano a ano.

---

## Objetivos

- **Reduzir o tempo de produção de um audiobook de semanas para menos de 30 minutos** para livros até 400 páginas.
- **Alcançar 90% de precisão na identificação automática de personagens** e falas, sem intervenção humana.
- **Suportar processamento de múltiplos livros simultaneamente** em uma fila configurável por prioridade.
- **Permitir configuração individual de cada serviço de IA** (LLM, TTS, MusicGen) como cloud ou local.

---

## Histórias de Usuário

### Produtor de Audiobooks (Editora/Produtora)

- Como **produtor de audiobooks**, quero **enviar múltiplos livros para processamento em uma fila**, para **otimizar o tempo de produção em lote**.
- Como **produtor de audiobooks**, quero **revisar e ajustar os personagens identificados antes da produção de áudio**, para **garantir qualidade editorial**.
- Como **produtor de audiobooks**, quero **configurar cada serviço de IA (LLM, TTS, trilha) separadamente como cloud ou local**, para **controlar custos e privacidade**.
- Como **produtor de audiobooks**, quero **pausar, retomar ou cancelar um livro na fila**, para **adaptar a produção a prioridades changeantes**.
- Como **produtor de audiobooks**, quero **convidar outros membros da equipe para revisar a distribuição de vozes**, para **validar escolhas antes da entrega**.

### Usuário Pessoal (Autor / Leitor)

- Como **autor independente**, quero **enviar meu livro em PDF e receber um audiobook pronto**, para **distribuir minha obra em áudio sem contratar locutores**.
- Como **usuário pessoal**, quero **escolher o nível de qualidade do audiobook (básico, avançado ou profissional)** ao enviar o livro, para **equilibrar velocidade e acabamento**.
- Como **usuário pessoal**, quero **acompanhar o progresso do processamento do meu livro pelo navegador**, para **saber quando meu audiobook estará pronto**.
- Como **usuário pessoal**, quero **baixar o audiobook pronto em um clique**, para **ouvir no meu dispositivo favorito**.

### Administrador do Sistema

- Como **administrador**, quero **configurar o servidor (pastas, banco de dados, serviços de IA) uma vez e esquecer**, para **manter o serviço rodando com mínimo esforço**.
- Como **administrador**, quero **acessar logs detalhados de cada etapa do processamento**, para **diagnosticar problemas rapidamente**.
- Como **administrador**, quero **definir credenciais de login (usuário e senha) para acessar o dashboard**, para **impedir acesso não autorizado ao sistema**.
- Como **usuário logado**, quero **fazer logout e trocar de conta**, para **compartilhar o servidor com segurança**.

---

## Funcionalidades Principais

### Fase 1 — MVP (Pipeline Essencial)

#### Upload e ingestão de PDF
- Envio de PDF pelo web dashboard.
- Extração automática de texto preservando estrutura de páginas e capítulos.
- Suporte a PDFs textuais (exclusivamente no MVP).
- Validação de formato e tamanho do arquivo.
- Indicador de progresso de ingestão.

#### Análise de conteúdo com IA
- Identificação automática de personagens e falas.
- Separação entre narração e diálogos.
- Normalização de nomes (agrupamento de variações/apelidos).
- Perfilamento de personagens (gênero e faixa etária aparente).
- Análise de perfil do narrador.
- Funciona para ficção literária no MVP.

#### Configuração de serviços de IA
- Interface para configurar cada serviço separadamente: LLM, TTS e MusicGen.
- Cada serviço aceita modo cloud (URL + token) ou local (endereço na rede).
- Validação de conexão ao salvar configuração.
- Armazenamento seguro de tokens e credenciais.

#### Produção de áudio (TTS)
- Atribuição automática de vozes com base no perfil do personagem.
- Quebra de texto em chunks otimizados para APIs de TTS.
- Produção de áudio individual por trecho.
- Unificação dos trechos em um único arquivo por personagem.

#### Fila de processamento
- Lista de livros na fila com status individual (pendente, em análise, em produção, concluído, falhou).
- Reordenação por prioridade (drag and drop ou botões).
- Botões de pausar, retomar e cancelar por livro.
- Indicador visual de progresso por etapa.

#### Autenticação e sessão
- Tela de login com usuário e senha.
- Configuração inicial de credenciais de administrador no primeiro acesso.
- Sessão com tempo de expiração configurável (idle timeout).
- Botão de logout em todas as páginas.
- No MVP: autenticação local (usuário e senha definidos pelo admin).

#### Dashboard web
- Página inicial com visão da fila de processamento.
- Página de detalhes do livro com status de cada etapa.
- Página de configurações do sistema.
- Upload de PDF integrado ao dashboard.
- Download do audiobook concluído.

### Fase 2 — Áudio Completo

#### Trilha sonora contextual
- Geração de trilha musical baseada na atmosfera do conteúdo.
- Trilha separada por capítulo ou contínua (dependendo do nível escolhido).
- Prompt atmosférico gerado automaticamente por IA.

#### Nível de produção configurável
- O usuário escolhe ao iniciar o processamento:
  - **Básico:** áudio simples, uma voz, sem trilha.
  - **Avançado:** multi-voz, trilha sonora simples.
  - **Profissional:** multi-voz, trilha contextual, separação por capítulos.

#### Revisão guiada de personagens
- Painel para o usuário revisar, editar e confirmar a lista de personagens.
- Edição de nome, gênero, faixa etária e voz atribuída.
- Visualização de trechos de fala de cada personagem para validação.
- Botão de "aprovar e iniciar produção de áudio".

#### Exportação por capítulos
- Audiobook dividido em arquivos por capítulo.
- Navegação por capítulo no player.

### Fase 3 — Colaboração e Escala

#### Modo colaborativo
- Convite de membros da equipe por e-mail.
- Perfis: administrador, revisor, espectador.
- Revisor pode aprovar/rejeitar personagens e distribuição de vozes.
- Histórico de alterações e aprovações.

#### Múltiplos formatos de conteúdo
- Adaptação automática do método de análise para não-ficção, acadêmico e técnico.
- Para não-ficção: identificação de seções e tópicos em vez de personagens.
- Para acadêmico: preservação de referências, fórmulas e notas de rodapé.

#### Filas com prioridade avançada
- Agrupamento de livros por projeto/campanha.
- Limites de concorrência configuráveis (quantos livros processar em paralelo).
- Notificação quando um livro concluído ou quando há falha.

#### Métricas e analytics
- Tempo médio de produção por livro.
- Taxa de sucesso de processamento.
- Consumo de créditos/API.
- Gráficos de uso do sistema.

---

## Experiência do Usuário

### Fluxo principal — Usuário pessoal enviando um livro

1. O usuário acessa o dashboard pelo navegador.
2. Clica em "Novo livro" e seleciona o arquivo PDF.
3. Escolhe o nível de produção: básico, avançado ou profissional.
4. Aguarda a análise automática (personagens, narrador, vozes).
5. Revisa os resultados na tela (na Fase 2).
6. Confirma e o áudio é produzido.
7. Recebe notificação e baixa o audiobook concluído.

### Fluxo principal — Produtor enviando múltiplos livros

1. O produtor acessa o dashboard e vê a fila de processamento.
2. Arrasta múltiplos PDFs para a fila.
3. Define a prioridade de cada livro (arrastando na lista).
4. Acompanha o progresso de cada um individualmente.
5. Revisa e aprova os personagens no painel de revisão (Fase 2).
6. Convida colegas para revisar (Fase 3).
7. Baixa os audiobooks concluídos.

### Considerações de UX

- **Feedback constante:** cada etapa do processamento tem indicador visual claro.
- **Transparência:** o usuário sabe exatamente em que etapa o livro está e quanto falta.
- **Controle:** pausar, retomar, cancelar, reordenar — tudo ao alcance de um clique.
- **Onboarding:** primeiro acesso inclui um tutorial rápido de 3 passos (upload → configuração → processamento).
- **Design System:** interface segue o padrão Pac-Man Tech Theme (Bootstrap 5.2.3, paleta escura com gradientes ciano/amarelo, fundo animado com Pac-Man, cards com glassmorphism).

### Design System — Pac-Man Tech Theme

A interface web utiliza o design system existente na pasta `design/`, com as seguintes características aplicadas:

- **Framework:** Bootstrap 5.2.3 + Bootstrap Icons 1.8.1.
- **Fonte:** Plus Jakarta Sans (pesos 100–900) via Google Fonts.
- **Paleta escura:** fundo principal `#08101c`, texto principal `#d8e7ff`, primária `#34d3ff` (ciano), secundária `#ffd166` (amarelo Pac-Man).
- **Gradientes:** botões e badges com gradiente ciano → amarelo; títulos com texto gradiente.
- **Cards:** `border-0`, `rounded-4`, `shadow` com `backdrop-filter: blur(14px)` (glassmorphism) para sobrepor o canvas animado.
- **Navbar:** fundo `rgba(7, 15, 28, 0.78)`, links brancos, brand em cor primária.
- **Canvas animado:** Pac-Man Tech Theme com grid, lanes, pellets, fantasmas, code symbols (`</>`, `{ }`, `SQL`, etc.) e score no canto.
- **Botões:** `.btn-primary` (gradiente ciano, texto escuro), `.btn-outline-dark` (borda ciana, hover amarelo).
- **Badges:** fundo gradiente para status e categorias.
- **Feature icons:** ícones Bootstrap em quadrados arredondados com fundo gradiente.
- **Responsividade:** breakpoints Bootstrap padrão (sm/md/lg/xl/xxl) + correções em `responsive-fixes.css`.
- **Acessibilidade:** respeita `prefers-reduced-motion` (canvas estático em vez de animado).
- **Reutilização:** copiar pasta `design/` e personalizar cores nos `:root` do CSS, nome da marca, links de navegação e conteúdo HTML.

---

## Fora de Escopo (Non-Goals)

- **Formatos diferentes de PDF no MVP:** apenas PDFs textuais. PDFs escaneados (OCR) na Fase 2 ou posterior.
- **Distribuição automática para plataformas:** o sistema gera o arquivo, mas não faz upload para Spotify, Audible, Apple Books etc.
- **Player de áudio embutido:** o audiobook é baixado e ouvido no dispositivo do usuário. Não há player integrado.
- **Tradução automática de conteúdo:** o sistema processa o PDF no idioma original.
- **Aplicativo mobile:** acesso via navegador. Sem app nativo.

---

## Plano de Entrega por Fases

### MVP (Fase 1) — Valor mínimo verificável

**Inclui:**
- Upload de PDF pelo dashboard.
- Extração de texto e análise de personagens/narrador.
- Configuração de APIs (cloud ou local).
- Produção de áudio TTS multi-voz.
- Fila de processamento com pausar/retomar/cancelar.
- Download do audiobook concluído.

**Critério de sucesso para Fase 2:**
- Pipeline funcional de ponta a ponta em pelo menos 3 livros de testes.
- Usuário consegue enviar um PDF e baixar o audiobook sem intervenção manual.
- Configuração de serviços de IA validada em ambos os modos (cloud e local).

### Fase 2 — Áudio completo

**Inclui:**
- Trilha sonora contextual (MusicGen).
- Nível de produção configurável.
- Revisão guiada de personagens.
- Exportação por capítulos.

**Critério de sucesso para Fase 3:**
- Audiobook profissional (multi-voz + trilha) produzido com sucesso.
- Revisor externo consegue revisar e aprovar personagens via dashboard.
- Tempo de produção de audiobook de 300 páginas ≤ 45 minutos.

### Fase 3 — Colaboração e escala

**Inclui:**
- Modo colaborativo com perfis.
- Múltiplos formatos de conteúdo.
- Filas com prioridade avançada e limites de concorrência.
- Métricas e analytics.

**Critério de sucesso:**
- Múltiplos usuários revisam simultaneamente sem conflitos.
- Sistema processa pelo menos 5 livros simultaneamente sem degradação.
- Painel de métricas fornece insights acionáveis sobre produção.

---

## Métricas de Sucesso

### Engajamento
- Tempo médio do upload ao audiobook concluído ≤ 30 minutos (livros ≤ 400 páginas).
- Taxa de conclusão de pipeline ≥ 95% dos livros enviados.
- Retorno de usuários na semana seguinte ≥ 40%.

### Qualidade
- Precisão de identificação de personagens ≥ 90% (validada por revisão humana).
- Satisfação com qualidade de voz ≥ 4.0 em escala de 1 a 5.

### Negócio
- Número de livros processados por mês (crescimento de 20% ao mês).
- Tempo de inatividade do serviço < 5% ao mês.

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Serviço de IA cloud fica indisponível ou excede quota | Produções travadas | Fallback automático para serviço local configurado; notificação proativa ao usuário |
| Qualidade da análise de personagens para gêneros não-ficção | Personagens incorretos ou inexistentes | Filtro de tipo de conteúdo no upload; análise adaptativa por tipo na Fase 3 |
| Tempo de processamento de áudio (TTS) é o gargalo principal | Filas longas, usuários frustrados | Processamento paralelo configurável; fila com prioridade e estimativas de tempo visíveis |
| Dependência de serviços externos de IA (TTS, LLM, MusicGen) | Risco de mudança de preço ou descontinuação | Cada serviço é substituíível e configurável; suporte a alternatives locais |
| Resistência de usuários à voz artificial em ficção | Insatisfação com resultado | Nível de produção configurável; usuário escolhe qualidade; revisão de vozes permite ajustes |

---

## Registros de Decisão de Arquitetura

- [ADR-001: Estratégia de Entrega Faseada com MVP Vertical](adrs/adr-001.md) — Entregar o sistema em 3 fases, cada uma com valor próprio, começando pelo pipeline essencial.

---

## Perguntas em Aberto

- **Formatos de entrada além de PDF:** EPUB e TXT são relevantes para o MVP ou podem ser adiados?
- **Idiomas:** o sistema deve suportar PDFs em múltiplos idiomas no MVP ou focar em português/inglês inicialmente?
- **Armazenamento de áudio:** há limite de espaço disponível no servidor para os audiobooks gerados? Os arquivos antigos devem ser arquivados ou excluídos automaticamente?
- **Autenticação:** no MVP, a autenticação será local (usuário/senha definidos pelo admin) ou deve suportar integração com diretório ativo (LDAP/Active Directory) a partir da Fase 1?
- **Licenciamento de vozes:** há restrições de uso comercial das vozes TTS configuradas?

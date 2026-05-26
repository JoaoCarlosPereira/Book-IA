---
status: pending
title: Frontend HTMX — dashboard, login, upload, detalhes, configurações
type: frontend
complexity: medium
dependencies:
  - task_03, task_04, task_10
---

# Tarefa 12: Frontend HTMX — dashboard, login, upload, detalhes, configurações

## Visão Geral
Implementar todos os templates Jinja2 + HTMX para o dashboard do Book-IA, integrando com o design system Pac-Man Tech Theme existente na pasta `design/`. Esta tarefa cobre todas as páginas do dashboard: login, dashboard principal, detalhes do livro e configurações.

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- Todos os templates DEVE usar o design system Pac-Man Tech Theme (Bootstrap 5.2.3, paleta escura, gradientes ciano/amarelo)
- Assets do design system DEVE ser copiados e referenciados corretamente: `design/css/styles.css`, `design/css/responsive-fixes.css`, `design/js/scripts.js`
- Template `base.html` DEVE incluir navbar, canvas Pac-Man, footer e blocos de conteúdo
- Template `login.html` DEVE ter card central com glassmorphism e formulário de login
- Template `dashboard.html` DEVE ter hero section, grid de cards de livros, botão de upload
- HTMX DEVE usar `hx-trigger="every 3s"` para polling de progresso
- Template `livro/detail.html` DEVE ter tabs Bootstrap (informações, personagens, áudio)
- Template `livro/configuracoes.html` DEVE ter formulário para cada API + botão de teste de conexão
- Todos os botões DEVE usar classes do design system: `.btn-primary`, `.btn-outline-dark`
- Badges de status DEVE usar `.bg-gradient-primary-to-secondary`
- Progress bars DEVE usar gradiente ciano→amarelo

## Subtarefas
- [ ] Criar `backend/templates/base.html` — layout principal com navbar, canvas, footer
- [ ] Criar `backend/templates/login.html` — card com glassmorphism e formulário
- [ ] Criar `backend/templates/dashboard.html` — hero, grid de livros, botão de upload
- [ ] Copiar assets do design system (`css/`, `js/`, `responsive-fixes.css`)
- [ ] Configurar `static/` com CSS e JS do design system
- [ ] Criar `backend/templates/partials/livro_list.html` — lista de livros (HTMX partial)
- [ ] Criar `backend/templates/partials/livro_card.html` — card individual de livro
- [ ] Criar `backend/templates/partials/progresso.html` — barra de progresso (HTMX partial)
- [ ] Criar `backend/templates/partials/status_badge.html` — badge de status
- [ ] Criar `backend/templates/livro/upload.html` — formulário de upload
- [ ] Criar `backend/templates/livro/detail.html` — tabs com informações, personagens, áudio
- [ ] Criar `backend/templates/livro/configuracoes.html` — painel de configurações de API
- [ ] Implementar fluxos HTMX: polling, upload, pausar, cancelar, reordenar, testar conexão

## Detalhes de Implementação

### Template structure baseada no TechSpec
- Ver seção "Design da Interface" do TechSpec para estrutura de templates e fluxos HTMX
- Ver seção "Componentes Customizados" do TechSpec para HTML de status badge, feature icon, progress bar
- Ver seção "Cores Semânticas para Status" do TechSpec para paleta de status

### Integração com design system
- Copiar `design/css/styles.css` → `backend/static/css/styles.css`
- Copiar `design/css/responsive-fixes.css` → `backend/static/css/responsive-fixes.css`
- Copiar `design/js/scripts.js` → `backend/static/js/scripts.js`
- Copiar Bootstrap 5.2.3 e Bootstrap Icons via CDN no `<head>`
- Copiar Google Fonts (Plus Jakarta Sans) via CDN no `<head>`
- Aplicar classe `pacman-tech-theme` no `<body>`

### Fluxos HTMX baseados no TechSpec
- Ver seção "Fluxos HTMX" do TechSpec para 6 interações com attributes e endpoints

### Arquivos Relevantes
- `design/` — Design system Pac-Man Tech Theme completo; copiar CSS/JS para static
- `design/design.md` — Especificações do design system para referência

### Arquivos Dependentes
- `backend/app/templates/` — Templates Jinja2
- `backend/app/static/` — CSS, JS, assets do design system
- `backend/app/api/v1/livros.py` (task_10) — Endpoints da API que os templates consomem
- `backend/app/api/v1/configuracoes.py` (task_04) — Endpoints de configuração

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define HTMX + Jinja2 para frontend
- [ADR-004: Arquitetura do Sistema](adrs/adr-004.md) — Define estrutura de templates

## Entregáveis
- 12 templates Jinja2 completos (base, login, dashboard, partials, livro/*, configuracoes)
- Design system Pac-Man Tech Theme integrado (CSS, JS, canvas animado)
- Fluxos HTMX configurados (polling, upload, controle de livro, configurações)
- Responsividade funcional (mobile/tablet/desktop)
- Testes visuais: todas as páginas renderizam corretamente com design system
- Testes de integração: HTMX calls funcionam com endpoints da API

## Testes
- Testes visuais/manual:
  - [ ] `login.html` renderiza com card glassmorphism e botão gradiente ciano
  - [ ] `dashboard.html` renderiza com navbar, hero, grid de cards
  - [ ] `livro/detail.html` renderiza com tabs Bootstrap e barras de progresso
  - [ ] `livro/configuracoes.html` renderiza com formulário de API e botão de teste
  - [ ] Canvas Pac-Man animado aparece no fundo (exceto prefers-reduced-motion)
  - [ ] Cards usam backdrop-filter: blur(14px) (glassmorphism)
  - [ ] Badges de status usam cores corretas (pendente=cinza, processando=ciano, concluído=verde, falhou=vermelho, pausado=amarelo)
  - [ ] Design responsivo funciona em mobile (< 576px), tablet (768px) e desktop (1200px+)
- Testes de integração:
  - [ ] HTMX polling (`hx-trigger="every 3s"`) atualiza lista de livros
  - [ ] HTMX upload (`hx-post` com `hx-encoding="multipart"`) faz upload de arquivo
  - [ ] HTMX pausa (`hx-post`) atualiza status do livro
  - [ ] HTMX testar conexão (`hx-post`) mostra badge verde/vermelho

## Critérios de Sucesso
- Todos os testes passando
- Todas as páginas renderizam corretamente
- Design system Pac-Man Tech Theme integrado
- HTMX calls funcionam com endpoints da API
- Responsividade funcional em todos os breakpoints
- Canvas animado aparece no fundo (respeita prefers-reduced-motion)

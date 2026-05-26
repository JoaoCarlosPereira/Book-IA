---
status: pending
title: Autenticação e sessão com cookies HTTP-only
type: backend
complexity: medium
dependencies:
  - task_02
---

# Tarefa 03: Autenticação e sessão com cookies HTTP-only

## Visão Geral
Implementar sistema de autenticação com login, logout, setup inicial (primeiro acesso) e middleware de sessão baseado em cookies HTTP-only. A autenticação usa bcrypt para hashes de senha e sessões armazenadas em memória (ou Redis para produção).

<critical>
- SEMPRE LEIA o PRD e o TechSpec antes de começar
- CONSULTE O TECHSPEC para detalhes de implementação — não duplique aqui
- FOQUE NO "O QUÊ" — descreva o que precisa ser feito, não como
- MINIMIZE CÓDIO — mostre código só para ilustrar estrutura atual ou áreas problemáticas
- TESTES OBRIGATÓRIOS — toda tarefa DEVE incluir testes nos entregáveis
</critical>

<requirements>
- Endpoint POST `/api/v1/auth/setup` DEVE criar primeiro admin se não houver usuários no banco (primeiro acesso)
- Endpoint POST `/api/v1/auth/login` DEVE validar credenciais, criar sessão, definir cookie HTTP-only
- Endpoint POST `/api/v1/auth/logout` DEVE destruir sessão e limpar cookie
- Senhas DEVE ser hasheadas com bcrypt (fazer 12 rounds)
- Sessão DEVE ter idle timeout configurável (padrão: 30 minutos)
- Middleware DEVE proteger rotas com decorator `require_auth`
- GET `/api/v1/auth/login` DEVE retornar template HTML de login (Jinja2)
- Redirecionamento: login com sucesso → `/dashboard`; com falha → `/login?error=1`

## Subtarefas
- [ ] Criar `backend/app/deps.py` com dependência `get_current_user` (extrai user do cookie/sessão)
- [ ] Criar `backend/app/middlewares/session.py` com middleware de sessão
- [ ] Criar `backend/app/deps.py` com decorator `require_auth` e `require_role`
- [ ] Criar `backend/app/api/v1/auth.py` com endpoints setup, login, logout
- [ ] Criar `backend/app/services/auth_service.py` com lógica de hash, sessão, validação
- [ ] Criar `backend/templates/login.html` com formulário de login (design Pac-Man)
- [ ] Configurar sessão com cookie HTTP-only, Secure (se HTTPS), SameSite=Lax
- [ ] Configurar idle timeout configurável via环境变量

## Detalhes de Implementação

### Endpoints definidos no TechSpec
- Ver seção "Endpoints de API — Autenticação" do TechSpec
- `GET /api/v1/auth/login` — retorna template HTML
- `POST /api/v1/auth/login` — valida credenciais, redireciona
- `POST /api/v1/auth/logout` — destrói sessão
- `POST /api/v1/auth/setup` — cria admin inicial

### Arquivos Relevantes
- `src/pas/Book/Leitor.Book.pas` — Referenciar `TB_LIVROAPIS` para entender como credenciais eram armazenadas
- `design/login.html` — Referenciar design do template (se existir no design system)

### Arquivos Dependentes
- `backend/app/models/usuario.py` (task_02) — Modelo Usuario para查询 e criação
- `backend/app/templates/` (task_12) — Templates Jinja2 que usam autenticação

### ADRs Relacionados
- [ADR-002: Stack Tecnológica](adrs/adr-002.md) — Define session-based auth com cookies HTTP-only

## Entregáveis
- Serviço de autenticação com setup, login, logout
- Middleware de sessão com cookie HTTP-only
- Decorator `require_auth` para proteger rotas
- Template HTML de login estilizado com Pac-Man Tech Theme
- Testes unitários: hash de senha, validação de credenciais, criação de sessão
- Testes de integração: fluxo completo de setup → login → acesso protegido → logout

## Testes
- Testes unitários:
  - [ ] `bcrypt.hashpw("senha123", bcrypt.gensalt(12))` gera hash válido
  - [ ] `bcrypt.checkpw("senha123", hash)` retorna True para senha correta
  - [ ] `bcrypt.checkpw("senha_errada", hash)` retorna False
  - [ ] Primeiro acesso (sem usuários) retorna 201 ao criar admin
  - [ ] Segundo acesso (já existe admin) retorna 403
- Testes de integração:
  - [ ] POST /api/v1/auth/setup cria admin e redireciona para /dashboard
  - [ ] POST /api/v1/auth/login com credenciais válidas define cookie e redireciona
  - [ ] POST /api/v1/auth/login com credenciais inválidas retorna 401
  - [ ] POST /api/v1/auth/logout destrói sessão e redireciona para /login
  - [ ] Acesso a rota protegida sem sessão retorna 302 para /login

## Critérios de Sucesso
- Todos os testes passando
- Cobertura de testes >= 80%
- Setup cria admin no primeiro acesso
- Login autentica e define cookie HTTP-only
- Rota protegida é bloqueada sem sessão válida
- Logout destrói sessão e limpa cookie

-- Book-IA seed data: 9 default voices + admin placeholder
-- Run after migrations: psql -U bookia -d bookia -f scripts/seed_data.sql

INSERT INTO voz (nome, genero, idade) VALUES
  ('Voz Masculina Criança', 'masculino', 'crianca'),
  ('Voz Masculina Adulto', 'masculino', 'adulto'),
  ('Voz Masculina Idoso', 'masculino', 'idoso'),
  ('Voz Feminina Criança', 'feminino', 'crianca'),
  ('Voz Feminina Adulto', 'feminino', 'adulto'),
  ('Voz Feminina Idoso', 'feminino', 'idoso'),
  ('Voz Neutra Criança', 'neutro', 'crianca'),
  ('Voz Neutra Adulto', 'neutro', 'adulto'),
  ('Voz Neutra Idoso', 'neutro', 'idoso')
ON CONFLICT DO NOTHING;

-- Placeholder admin — replace hash via POST /api/v1/auth/setup on first access
INSERT INTO usuario (login, senha_hash, perfil)
VALUES (
  'admin',
  '$2b$12$PLACEHOLDER_REPLACE_ON_SETUP',
  'admin'
)
ON CONFLICT (login) DO NOTHING;

-- book_task rows are created on livro upload (status 'pendente', prioridade 5).
-- Example (after a livro exists):
-- INSERT INTO book_task (livro_id, status, prioridade, progresso)
-- VALUES (1, 'pendente', 5, 0);

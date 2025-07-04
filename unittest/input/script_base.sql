-- SCRIPT GERADO EM: 2025-05-26 20:25:49
-- PostgreSQL - Estrutura completa de tabelas do sistema de livros, falas e personagens

-- Tabela de Livros
CREATE TABLE TB_LIVROCABECALHO (
    CD_SEQUENCIAL      BIGSERIAL PRIMARY KEY,
    TX_TITULO          TEXT UNIQUE,
    FL_LIDO            TEXT,
    FL_NORMALIZADO     TEXT,
    FL_NARRADOR        TEXT,
    FL_PRODUZIDO       TEXT,
    DT_MANUTECAO       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Páginas dos Livros
CREATE TABLE TB_LIVROPAGINA (
    CD_SEQUENCIAL           BIGSERIAL PRIMARY KEY,
    CD_SEQUENCIALLIVRO      BIGINT NOT NULL REFERENCES TB_LIVROCABECALHO(CD_SEQUENCIAL),
    NR_PAGINA               BIGINT,
    TX_PAGINA               TEXT,
    FL_PROCESSADO           TEXT,
    DT_MANUTECAO            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Personagens
CREATE TABLE TB_LIVROPERSONAGENS (
    CD_SEQUENCIAL          BIGSERIAL PRIMARY KEY,
    CD_SEQUENCIALLIVRO     BIGINT NOT NULL REFERENCES TB_LIVROCABECALHO(CD_SEQUENCIAL),
    TX_PERSONAGEM          TEXT,
    TX_GENERO              TEXT,
    TX_IDADE               TEXT,
    CD_VOZ                 BIGINT,
    DT_MANUTECAO           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Falas
CREATE TABLE TB_LIVROFALAS (
    CD_SEQUENCIAL             BIGSERIAL PRIMARY KEY,
    CD_SEQUENCIALLIVRO        BIGINT NOT NULL REFERENCES TB_LIVROCABECALHO(CD_SEQUENCIAL),
    CD_SEQUENCIALPAGINA       BIGINT NOT NULL REFERENCES TB_LIVROPAGINA(CD_SEQUENCIAL),
    CD_SEQUENCIALPERSONAGEM   BIGINT NOT NULL REFERENCES TB_LIVROPERSONAGENS(CD_SEQUENCIAL),
    TX_FALA                   TEXT,
    FL_PROCESSADO             TEXT,
    DT_MANUTECAO              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para armazenar chaves de APIs externas
CREATE TABLE TB_LIVROAPIS (
    CD_SEQUENCIAL   BIGSERIAL PRIMARY KEY,
    TX_KEY          TEXT UNIQUE,
    DT_EXPIRACAO    TIMESTAMP
);

CREATE TABLE TB_LIVROVOZES (
    CD_SEQUENCIAL   BIGSERIAL PRIMARY KEY,
    TX_NOME          TEXT UNIQUE,
    TX_GENERO              TEXT,
    TX_IDADE               TEXT
);

-- Índices adicionais recomendados
CREATE INDEX idx_livropagina_livro ON TB_LIVROPAGINA(CD_SEQUENCIALLIVRO);
CREATE INDEX idx_personagens_livro ON TB_LIVROPERSONAGENS(CD_SEQUENCIALLIVRO);
CREATE INDEX idx_falas_livro_pagina ON TB_LIVROFALAS(CD_SEQUENCIALLIVRO, CD_SEQUENCIALPAGINA);
CREATE INDEX idx_falas_personagem ON TB_LIVROFALAS(CD_SEQUENCIALPERSONAGEM);

delete from TB_LIVROAPIS;
insert into TB_LIVROAPIS(TX_KEY) values ('AIzaSyDTRrwio8jO_9v4QS_ouF7HjyO_N36KZnE');
insert into TB_LIVROAPIS(TX_KEY) values ('AIzaSyB1rNQIFargUbdVYDUBTPPk1vy2uSZbF68');
insert into TB_LIVROAPIS(TX_KEY) values ('AIzaSyBs1sd5ocP5J56QPJ-W6Ly5SPFPyI0uZ2w');
insert into TB_LIVROAPIS(TX_KEY) values ('AIzaSyB2RTjEi0L7n30kQsmBq1HM_t7lxQodFTs');
insert into TB_LIVROAPIS(TX_KEY) values ('AIzaSyC2Kt99Sb5IY_RNUO9ZqnFrDWpXxex_o-E');
insert into TB_LIVROAPIS(TX_KEY) values ('AIzaSyDeB1vs-udoPPUEWs6nOpvQ0h12TgK4Xgs');
insert into TB_LIVROAPIS(TX_KEY) values ('AIzaSyDSIcMZlMrVeV_9StdMnxdsOxJJqaPp3q4');
insert into TB_LIVROAPIS(TX_KEY) values ('AIzaSyBxwanOk70H4nstHnqlEO_s1x_QwDpWj-4');
insert into TB_LIVROAPIS(TX_KEY) values ('AIzaSyCdF3aqoPASms0nW2R9LF74MfQOs16DFTs');
insert into TB_LIVROAPIS(TX_KEY) values ('AIzaSyCwQchUI6Z3Orgg7o9LrytINIbgh_rzpKc');

delete from TB_LIVROVOZES;
INSERT INTO TB_LIVROVOZES (TX_NOME, TX_GENERO, TX_IDADE) VALUES
('kris', 'Male', 'adult'),
('pereira', 'Male', 'adult'),
('bresolin', 'Male', 'adult'),
('sergio', 'Male', 'adult'),
('ana', 'Female', 'adult'),
('alex', 'Male', 'adult'),
('weslay', 'Male', 'adult'),
('eleandro', 'Male', 'adult'),
('eletro', 'Male', 'adult'),
('elvira', 'Female', 'Elderly'),
('henrique', 'Male', 'adult'),
('leo', 'Male', 'adult'),
('maninho', 'Male', 'adult'),
('mauricio', 'Male', 'adult'),
('michelli', 'Female', 'adult'),
('nicolas', 'Male', 'adult'),
('nik', 'Male', 'adult'),
('ode', 'Female', 'adult'),
('olia', 'Female', 'adult'),
('pai', 'Male', 'Elderly'),
('rafael', 'Male', 'adult'),
('rosa', 'Female', 'adult'),
('sogra', 'Female', 'Elderly'),
('stasia', 'Female', 'adult'),
('valdemar', 'Male', 'Elderly'),
('vetrana', 'Male', 'adult'),
('william', 'Male', 'adult'),
('luis', 'Male', 'adult'),
('pedro', 'Male', 'adult'),
('jose', 'Male', 'adult'),
('marques', 'Male', 'adult'),
('maria', 'Female', 'adult'),
('polaca', 'Female', 'adult'),
('paulo', 'Male', 'adult'),
('cana', 'Female', 'adult'),
('camila', 'Female', 'adult'),
('raul', 'Male', 'adult'),
('flavia', 'Female', 'adult'),
('anna', 'Female', 'adult'),
('yvar', 'Male', 'adult');
unit Rgn.Leitor.Book.Personagens;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, OtlTask,
  Leitor.Book, Rgn.Leitor.IA.Http;

type
  IRgnLeitorBookPersonagens = interface
    ['{2740652E-A163-4B81-9FF5-E8E9E3430FC1}']
    procedure ObterPersonagens(const ALivro: TLivro);
  end;

  TRgnLeitorBookPersonagens = class(TInterfacedPersistent, IRgnLeitorBookPersonagens)
  private
    oIRgnLeitorIAHttp: IRgnLeitorIAHttp;
    procedure NormalizarNomes(const ALivro: TLivro);
    procedure DefinirPerfilPersonagem(const ALivro: TLivro);
  public
    procedure ObterPersonagens(const ALivro: TLivro);
  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, Helper.HNumeric;



procedure TRgnLeitorBookPersonagens.ObterPersonagens(const ALivro: TLivro);
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
  iTentativas: Integer;
  iRequisicoes: Integer;
  dTime: TTime;
  oRequestIA: TRequestIA;
  oResponse: TResponse;
  oPersonagens: TStringList;

  function GetPrompt: string;
  begin
    Result :=
      '[INSTRUÇÃO DE SISTEMA]\n' +
      'Você é um classificador de personagens de livros de ficção. Sua tarefa é extrair apenas os personagens que falam na narrativa de um trecho de livro fornecido.\n' +
      '\n' +
      '[SUA FUNÇÃO]\n' +
      'Identifique os personagens que têm **fala direta**, ou seja, frases que começam com **travessão no início da linha** (—, –), ou estão entre aspas (""). Para cada personagem com fala identificada, extraia:\n' +
      '# REGRAS PARA IDENTIFICAÇÃO DE FALAS EM TEXTOS NARRATIVOS (PORTUGUÊS)\n' +
      '\n' +
      '## 1. SINAIS GRÁFICOS\n' +
      '- Se o texto estiver ENTRE ASPAS (“ ” ou '''' '''') → É uma fala.\n' +
      '  Exemplo: "Ele disse: '''' Vamos agora.''''"\n' +
      '- Se começar com TRAVESSÃO (— ou -) → É uma fala.\n' +
      '  Exemplo: — Onde você estava?\n' +
      '\n' +
      '## 2. VERBOS DECLARATIVOS (PALAVRAS-CHAVE)\n' +
      '- Verbos comuns que introduzem falas:\n' +
      '  dizer, falar, perguntar, responder, gritar, sussurrar, exclamar, murmurar, ordenar, comentar, declarar, indagar, replicar, retrucar, berrar, chorar, gemer, balbuciar, afirmar, garantir, sugerir, pedir, avisar.\n' +
      '- Padrão típico:\n' +
      '  "[Verbo declarativo] + '''': '''' + Aspas"\n' +
      '  Exemplo: "Ele gritou: '''' Cuidado ! ''''"\n' +
      '\n' +
      '## 3. PONTUAÇÃO EXPRESSIVA\n' +
      '- Se contém !, ? ou … (reticências) dentro de aspas/travessão → Provavelmente é fala.\n' +
      '  Exemplo: "Você está louco?"\n' +
      '\n' +
      '## 4. ESTRUTURA DE DIÁLOGO\n' +
      '- Mudança de linha + travessão/aspas → Novo personagem falando.\n' +
      '  Exemplo:\n' +
      '  — Você vai?\n' +
      '  — Não, estou cansado.\n' +
      '\n' +
      '## 5. CONTEXTOS QUE NÃO SÃO FALAS\n' +
      '- Se o texto entre aspas é uma citação (sem verbo declarativo):\n' +
      '  Exemplo: A placa dizia "Pare". → Não é diálogo.\n' +
      '- Pensamentos (geralmente em itálico ou com verbos como "pensar"):\n' +
      '  Exemplo: *Será que ela vem?, ele pensou.* → Não é fala.\n' +
      '\n' +
      '## 6. REGRAS ADICIONAIS PARA EVITAR FALSOS POSITIVOS\n' +
      '- Se o texto entre aspas é um título, nome de obra ou expressão idiomática → Ignorar.\n' +
      '  Exemplo: Ele leu "Dom Casmurro".\n' +
      '- Se o verbo declarativo está no passado indireto (sem aspas):\n' +
      '  Exemplo: Ele disse que iria embora. → Não é fala direta.\n' +
      '\n' +
      '## EXEMPLOS PRÁTICOS PARA TREINAMENTO\n' +
      '1. Fala detectada:\n' +
      '   Maria suspirou: "Estou exausta."\n' +
      '   → (Possui verbo declarativo + aspas)\n' +
      '\n' +
      '2. Não é fala:\n' +
      '   O livro "1984" é famoso.\n' +
      '   → (Aspas sem verbo declarativo)\n' +
      '\n' +
      '3. Diálogo com travessão:\n' +
      '   — Que horas são? — perguntou João.\n' +
      '   → (Travessão + verbo declarativo)\n' +
      '\n' +
      '1. Nome (mesmo que genérico, como "Pai", "Menina", "Homem")\n' +
      '2. Fala (fala do personagem no trecho, fiel ao texto fornecido)\n' +
      '\n' +
      '[REGRAS IMPORTANTES]\n' +
      '- Cada linha de fala no texto original deve gerar uma nova linha de saída.\n' +
      '- Mesmo que o mesmo personagem fale duas vezes, cada fala deve ser separada.\n' +
      '- Quando a fala for interrompida por narração, cada parte da fala deve ser extraída separadamente.\n' +
      '- Se houver narração entre partes de uma fala (por exemplo: “— Não sei — disse ela. — Aqui em casa não está.”), trate como duas falas distintas, mas do mesmo personagem.\n' +
      '- NUNCA junte falas diferentes em uma única linha de saída.\n' +
      '- Preserve a ordem das falas exatamente como aparecem no texto.\n' +
      '- NÃO inclua personagens que NÃO falam diretamente.\n' +
      '- NÃO invente nomes nem falas. Use apenas o que está explicitamente no texto.\n' +
      '- Ignore números de página, títulos, notas, prefácios, sumário, etc.\n' +
      '\n' +
      '[FORMATO DE SAÍDA]\n' +
      'Retorne apenas os dados, um personagem por linha, seguindo este formato exato (sem ponto final):\n' +
      '\n' +
      'Nome|fala\n' +
      '\n' +
      'Se não houver nenhum personagem com fala direta no trecho, retorne apenas:\n' +
      '\n' +
      'sem personagens\n' +
      '\n' +
      '[EXEMPLOS DE SAÍDA CORRETA]\n' +
      'João|Meu pastel é mais barato!\n' +
      'Menina|Mentira garato.\n' +
      'Vó|Não briguem crianças\n' +
      '\n' +
      '[EXEMPLO DE NARRAÇÃO INTERCALADA CORRETAMENTE TRATADA]\n' +
      'Texto:\n' +
      '— Onde está ele? — perguntou João, olhando em volta. — Ninguém viu?\n' +
      '\n' +
      'Deve retornar:\n' +
      'João|Onde está ele?\n' +
      'João|Ninguém viu?\n' +
      '\n' +
      '[TEXTO A SER ANALISADO]\n' +
      '"' + oPagina.Texto + '"';
  end;

  procedure Generate;
  var
    sPersonagem: string;
  begin
    try
      oResponse := oIRgnLeitorIAHttp.Generate(oRequestIA);
      oPagina.ListaPersonagens.Clear;
      if (oResponse.Response <> '') and (not(oResponse.Response.Contains('sem personagens'))) then
      begin
        oPersonagens.Text := oResponse.Response.Replace(' — ', #13#10).Replace(' – ', #13#10);
        for sPersonagem in oPersonagens do
        begin
          if (sPersonagem.Contains('|')) and (Length(sPersonagem.Split(['|'])) >= 2) then
          begin
            if (sPersonagem.Split(['|'])[0].Trim <> 'nome') and (StrToInt64Def(sPersonagem.Split(['|'])[1].Trim.Replace('\n', '').Replace(' ', ''), -1) = -1) then
            begin
              oPagina.ListaPersonagens.Add(TPersonagemFala.Create);
              oPagina.ListaPersonagens.Last.nome := sPersonagem.Split(['|'])[0].Trim;
              oPagina.ListaPersonagens.Last.fala := sPersonagem.Split(['|'])[1].Trim.Replace('\n', '').Replace('  ', ' ');
            end;
          end
          else
          begin
            if (iTentativas > 0) then
            begin
              Inc(iTentativas, -1);
              Generate;
              Break;
            end;
          end;
        end;
      end;
    except
      on E: Exception do
      begin
        if (iTentativas > 0) or (E.Message.Contains('timed out')) then
        begin
          Inc(iTentativas, -1);
          oIRgnLeitorIAHttp.DescarregarModelo;
          Sleep(5000);
          Generate;
        end
        else
          Raise;
      end;
    end;
  end;



begin
  dTime             := Now;
  oIRgnLeitorIAHttp := TRgnLeitorIAHttp.Create.Ref;
  oRequestIA        := TRequestIA.Create;
  oPersonagens      := TStringList.Create;

  try
    iRequisicoes := 100;
    for oPagina in ALivro do
    begin
      if (iRequisicoes = 0) then
      begin
        oIRgnLeitorIAHttp.DescarregarModelo;
        iRequisicoes := 100;
      end;

      iTentativas := 5;
      Inc(iRequisicoes, -1);
      oRequestIA.prompt := GetPrompt;
      Generate;
    end;
  finally
    oPersonagens.Free;
    oRequestIA.Free;
  end;

  with TStringList.Create do
  begin
    Add(TimeToStr(Now - dTime));
    for oPagina in ALivro do
    begin
      for oPersonagem in oPagina.ListaPersonagens do
      begin
        Add(oPersonagem.nome + '|' + oPersonagem.fala);
      end;
    end;
    SaveToFile('Personagens.txt');
    Free;
  end;

  NormalizarNomes(ALivro);
  DefinirPerfilPersonagem(ALivro);
end;



procedure TRgnLeitorBookPersonagens.NormalizarNomes(const ALivro: TLivro);
var
  oPagina: TPagina;
  oRequestIA: TRequestIA;
  oResponse: TResponse;
  iTentativas: Integer;
  oListaPersonagens: TListaPersonagensFalas;
  oPersonagem: TPersonagemFala;
  dTime: TTime;

  function GetPrompt: string;
  begin
    Result :=
      'Você receberá uma lista contendo linhas no seguinte formato:\n' +
      '\n' +
      'ID|Nome\n' +
      '\n' +
      'Sua tarefa é processar cada linha da lista seguindo as instruções abaixo:\n' +
      '\n' +
      '[INSTRUÇÕES]\n' +
      '\n' +
      '1. Padronização de nomes repetidos:\n' +
      '   Se um personagem aparecer com variações no nome (ex: “Eddye Murphy”, “Eddye”, “Murphy”), unifique todas essas ocorrências para uma versão padronizada e consistente (ex: “Eddye Murphy”).\n' +
      '\n' +
      '2. Identificação de gênero:\n' +
      '   Determine o gênero do personagem com base no nome padronizado:\n' +
      '   - masculino\n' +
      '   - feminino\n' +
      '\n' +
      '3. Preservação do ID:\n' +
      '   Não modifique o ID original. Ele deve ser mantido exatamente como foi recebido para que a correspondência continue válida.\n' +
      '\n' +
      '4. Não remova nenhuma linha da entrada.\n' +
      '   Cada entrada recebida deve produzir uma linha correspondente na saída.\n' +
      '\n' +
      '[FORMATO DE SAÍDA]\n' +
      '\n' +
      'A saída deve conter uma linha para cada entrada, neste formato exato:\n' +
      '\n' +
      'ID|Nome padronizado|gênero\n' +
      '\n' +
      'Exemplo:\n' +
      '\n' +
      'Entrada:\n' +
      '123|Eddye\n' +
      '124|Murphy\n' +
      '125|Joana\n' +
      '127|Eddye Murphy\n' +
      '\n' +
      'Saída esperada:\n' +
      '123|Eddye Murphy|masculino\n' +
      '124|Eddye Murphy|masculino\n' +
      '125|Joana|feminino\n' +
      '127|Eddye Murphy|masculino\n' +
      '\n' +
      'IMPORTANTE:\n' +
      'Use apenas masculino ou feminino no campo de gênero.\n' +
      'Não invente nomes que não estejam presentes na entrada.\n' +
      'Se dois nomes forem provavelmente da mesma pessoa, padronize para a forma mais completa e clara.\n' +
      '\n' +
      '[LISTA PARA PROCESSAR ABAIXO]' +
      '\n\n' +
      oListaPersonagens.GetPersonagens;
  end;

  procedure Generate;
  var
    sPersonagem: string;
    oPersonagens: TStringList;
  begin
    try
      oPersonagens      := TStringList.Create;
      oResponse         := oIRgnLeitorIAHttp.Generate(oRequestIA);
      oPersonagens.Text := oResponse.Response;

      for sPersonagem in oPersonagens do
      begin
        if (sPersonagem.Contains('|')) and (Length(sPersonagem.Split(['|'])) >= 2) and (StrToIntDef(sPersonagem.Split(['|'])[0], -1) >= 0) then
        begin
          oPersonagem        := oListaPersonagens[sPersonagem.Split(['|'])[0].ToInteger];
          oPersonagem.nome   := sPersonagem.Split(['|'])[1];
          oPersonagem.genero := sPersonagem.Split(['|'])[2];
        end
      end;
    except
      on E: Exception do
      begin
        if (iTentativas > 0) or (E.Message.Contains('timed out')) then
        begin
          Inc(iTentativas, -1);
          oIRgnLeitorIAHttp.DescarregarModelo;
          Sleep(5000);
          Generate;
        end
        else
          Raise;
      end;
    end;
  end;



begin
  iTentativas       := 3;
  dTime             := Now;
  oRequestIA        := TRequestIA.Create;
  oListaPersonagens := TListaPersonagensFalas.Create(False);

  try

    for oPagina in ALivro do
    begin
      for oPersonagem in oPagina.ListaPersonagens do
      begin
        oListaPersonagens.Add(oPersonagem);
      end;
    end;

    oRequestIA.prompt := GetPrompt;
    Generate;

    for oPagina in ALivro do
    begin
      for oPersonagem in oPagina.ListaPersonagens do
      begin
        oListaPersonagens.Add(oPersonagem);
      end;
    end;

    with TStringList.Create do
    begin
      Add(TimeToStr(Now - dTime));
      for oPagina in ALivro do
      begin
        for oPersonagem in oPagina.ListaPersonagens do
        begin
          Add(oPersonagem.nome + '|' + oPersonagem.genero + '|' + oPersonagem.fala);
        end;
      end;
      SaveToFile('PersonagensNormalizado.txt');
      Free;
    end;
  finally
    oRequestIA.Free;
    oListaPersonagens.Free;
  end;
end;



procedure TRgnLeitorBookPersonagens.DefinirPerfilPersonagem(const ALivro: TLivro);
var
  oRequestIA: TRequestIA;
  oResponse: TResponse;
  iTentativas: Integer;
  sPersonagem: string;
  dTime: TTime;

  function GetPrompt: string;
  begin
    Result :=
      '[INSTRUÇÃO DE SISTEMA]\n' +
      'Você é um classificador de personagens em livros de ficção. Sua tarefa é analisar um trecho das falas de um personagem de uma história e, com base na linguagem, vocabulário, temas e estilo,' + ' identificar qual seria o perfil mais compatível com o personagem.\n' +
      '\n\n' +
      '[SUA FUNÇÃO]\n' +
      'Avalie o trecho de falas e indique, com base no tom e estilo das falas:\n' +
      '1. Gênero que mais se aproxima da voz do personagem: **Masculino** ou **Feminino**\n' +
      '2. Faixa etária que mais combina com o personagem: **Criança**, **Adulto** ou **Idoso**\n' +
      '\n\n' +
      '[COMO DECIDIR]\n' +
      '- Leve em consideração o vocabulário utilizado, complexidade das frases, sentimentos expressos, ritmo e maturidade das ideias.\n' +
      '- Evite conclusões óbvias apenas com base em personagens ou contexto externo. Baseie-se apenas no **estilo da fala**.\n' +
      '\n\n' +
      '[CASO DE INCERTEZA]\n' +
      'Se não for possível determinar com segurança o perfil do personagem, **sorteie uma combinação plausível de gênero e idade**, que seja **coerente com o tom geral do texto**.\n' +
      '\n\n' +
      '[FORMATO DE RESPOSTA]\n' +
      'Responda com uma única linha, exatamente no formato abaixo (sem ponto final):\n' +
      '\n' +
      'Gênero|Idade\n' +
      '\n' +
      'Exemplos válidos:\n' +
      'Masculino|Adulto\n' +
      'Feminino|Idoso\n' +
      '\n\n' +
      '[NOME DO PERSONGEM]\n' +
      '"' + sPersonagem + '"' +
      '\n\n' +
      '[TEXTO A SER ANALISADO]\n' +
      '"' + ALivro.GetTrechoPorPersonagem(sPersonagem) + '"';
  end;

  procedure Generate;
  var
    oPersonagem: TPersonagemFala;
  begin
    try
      oResponse := oIRgnLeitorIAHttp.Generate(oRequestIA);

      if (oResponse.Response.Contains('|')) and (Length(oResponse.Response.Split(['|'])) >= 2) then
      begin
        for oPersonagem in ALivro.GetPersonagem(sPersonagem) do
        begin
          oPersonagem.genero         := oResponse.Response.Split(['|'])[0].Trim;
          oPersonagem.idade_aparente := oResponse.Response.Split(['|'])[1].Trim;
        end;
      end
      else
      begin
        if (iTentativas > 0) then
        begin
          Inc(iTentativas, -1);
          Generate;
        end;
      end;
    except
      on E: Exception do
      begin
        if (iTentativas > 0) or (E.Message.Contains('timed out')) then
        begin
          Inc(iTentativas, -1);
          oIRgnLeitorIAHttp.DescarregarModelo;
          Sleep(5000);
          Generate;
        end
        else
          Raise;
      end;
    end;
  end;



begin
  iTentativas := 3;
  dTime       := Now;
  oRequestIA  := TRequestIA.Create;

  try
    for sPersonagem in ALivro.GetPersonagens do
    begin
      oRequestIA.prompt := GetPrompt;
      Generate;
    end;
  finally
    oIRgnLeitorIAHttp.DescarregarModelo;
    oRequestIA.Free;
  end;
end;

end.

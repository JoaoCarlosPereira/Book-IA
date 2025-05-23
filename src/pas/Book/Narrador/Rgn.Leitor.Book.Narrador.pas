unit Rgn.Leitor.Book.Narrador;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, OtlTask,
  Leitor.Book, Rgn.Leitor.IA.Http;

type
  IRgnLeitorBookNarrador = interface
    ['{BA32DA37-B936-4228-823E-BB58A1FF91E4}']
    procedure ObterNarrador(const ALivro: TLivro);
  end;

  TRgnLeitorBookNarrador = class(TInterfacedPersistent, IRgnLeitorBookNarrador)
  private
    oIRgnLeitorIAHttp: IRgnLeitorIAHttp;
    procedure DefinirPerfilNarrador(const ALivro: TLivro);
    procedure ExtrairNarracoes(const ALivro: TLivro);
  public
    procedure ObterNarrador(const ALivro: TLivro);
  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, Helper.HNumeric;



procedure TRgnLeitorBookNarrador.ObterNarrador(const ALivro: TLivro);
begin
  ExtrairNarracoes(ALivro);
  DefinirPerfilNarrador(ALivro);
end;



procedure TRgnLeitorBookNarrador.ExtrairNarracoes(const ALivro: TLivro);
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
  iTentativas: Integer;
  iRequisicoes: Integer;
  dTime: TTime;
  oRequestIA: TRequestIA;
  oResponse: TResponse;
  oNarrador: TStringList;

  function GetPrompt: string;
  begin
    Result :=
      '[INSTRUÇÃO DE SISTEMA]\n' +
      'Você é um classificador de narrações em livros de ficção. Sua tarefa é extrair apenas as falas atribuídas ao **narrador** em um trecho de livro fornecido.\n' +
      '\n\n' +
      '[SUA FUNÇÃO]\n' +
      'Identifique as falas que são **narrações do narrador**, ou seja, todo o texto **que não estiver entre travessões (—, –)** nem **entre aspas ("")**, e que **não seja fala direta de personagens**. Para cada trecho narrado, extraia:\n' +
      '\n\n' +
      '1. narração: texto narrado fiel ao trecho fornecido, mantendo pontuação e quebras de linha, se houver\n' +
      '\n\n' +
      '[EXEMPLO]\n' +
      'No trecho: "' +
      'A luz começava a declinar, e Eddie Willers não conseguiu distinguir o rosto do vagabundo, que tinha\n' +
      'falado de modo simples, sem expressão. Mas, do crepúsculo lá longe, no fim da rua, lampejos amarelos\n' +
      'alcançaram seus olhos, que, galhofeiros e parados, fitavam Willers diretamente – como se a pergunta se\n' +
      'referisse àquele mal-estar inexplicável que ele sentia.\n' +
      '– Por que você disse isso? – perguntou Willers, tenso.\n' +
      'O vagabundo se encostou no batente da porta. Uma vidraça partida por trás dele refletia o amarelo\n' +
      'metálico do céu.\n' +
      '– Por que isso o incomoda? – perguntou.\n' +
      '– Não me incomoda – rosnou Willers."\n' +
      '\n\n' +
      '[DEVE RETORNAR]\n' +
      'A luz começava a declinar, e Eddie Willers não conseguiu distinguir o rosto do vagabundo, que tinha|' +
      'falado de modo simples, sem expressão. Mas, do crepúsculo lá longe, no fim da rua, lampejos amarelos|' +
      'alcançaram seus olhos, que, galhofeiros e parados, fitavam Willers diretamente – como se a pergunta se|' +
      'referisse àquele mal-estar inexplicável que ele sentia.|' +
      'O vagabundo se encostou no batente da porta. Uma vidraça partida por trás dele refletia o amarelo|' +
      'metálico do céu.|' +
      '\n\n' +
      '[REGRAS]\n' +
      '- NÃO inclua falas entre travessões ou aspas (falas diretas dos personagens)\n' +
      '- NÃO invente conteúdo. Use apenas o que está **explicitamente** narrado no trecho\n' +
      '- NÃO quebre uma narração contínua em várias falas, a não ser que ela esteja separada por trechos de fala direta\n' +
      '- IGNORE número da página, notas de rodapé e etc, qualquer elemento que não pertença a história.\n' +
      '\n\n' +
      '[FORMATO DE RESPOSTA]\n' +
      'Retorne apenas os dados, um por linha, seguindo este formato exato (sem ponto final):\n' +
      '\n\n' +
      'narração|\n' +
      '\n\n' +
      'Se não houver nenhum trecho narrado (somente diálogos), retorne apenas:\n' +
      '\n\n' +
      'sem narrador\n' +
      '\n\n' +
      '[EXEMPLO DE SAÍDA]\n' +
      'O sol nascia sobre os telhados molhados da cidade, iluminando os becos silenciosos.|\n' +
      'Ela caminhava devagar, como se temesse que o tempo passasse rápido demais.|\n' +
      '\n\n' +
      '[TEXTO A SER ANALISADO]\n' +
      '"' + oPagina.Texto + '"';

  end;

  procedure Generate;
  var
    sNarracao: string;
  begin
    try
      oResponse := oIRgnLeitorIAHttp.Generate(oRequestIA);
      if (oResponse.Response <> '') and (not(oResponse.Response.Contains('sem narrador'))) then
      begin
        oNarrador.Text := oResponse.Response.Replace('|', #13#10);
        for sNarracao in oNarrador do
        begin
          if (sNarracao <> '') then
          begin
            oPagina.ListaPersonagens.Add(TPersonagemFala.Create);
            oPagina.ListaPersonagens.Last.nome := 'Narrador';
            oPagina.ListaPersonagens.Last.fala := sNarracao.Trim.Replace('\n', '').Replace('  ', ' ');
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
  oNarrador         := TStringList.Create;

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
    oNarrador.Free;
    oRequestIA.Free;
  end;

  with TStringList.Create do
  begin
    Add(TimeToStr(Now - dTime));
    for oPersonagem in ALivro.GetPersonagem('Narrador') do
    begin
      Add(oPersonagem.nome + '|' + oPersonagem.fala);
    end;
    SaveToFile('Narrador.txt');
    Free;
  end;
end;



procedure TRgnLeitorBookNarrador.DefinirPerfilNarrador(const ALivro: TLivro);
var
  oRequestIA: TRequestIA;
  oResponse: TResponse;
  iTentativas: Integer;
  oPersonagem: TPersonagemFala;
  dTime: TTime;

  function GetPrompt: string;
  begin
    Result :=
      '[INSTRUÇÃO DE SISTEMA]\n' +
      'Você é um classificador de estilo narrativo em livros de ficção. Sua tarefa é analisar um trecho narrado de uma história e, com base na linguagem, vocabulário, temas e estilo,' + ' identificar qual seria o perfil mais compatível com o narrador que está contando essa história.\n' +
      '\n\n' +
      '[SUA FUNÇÃO]\n' +
      'Avalie o trecho narrado e indique, com base no tom e estilo da escrita:\n' +
      '1. Gênero que mais se aproxima da voz do narrador: **Masculino** ou **Feminino**\n' +
      '2. Faixa etária que mais combina com o narrador: **Criança**, **Adulto** ou **Idoso**\n' +
      '\n\n' +
      '[COMO DECIDIR]\n' +
      '- Leve em consideração o vocabulário utilizado, complexidade das frases, sentimentos expressos, ritmo e maturidade das ideias.\n' +
      '- Evite conclusões óbvias apenas com base em personagens ou contexto externo. Baseie-se apenas no **estilo da narração**.\n' +
      '\n\n' +
      '[CASO DE INCERTEZA]\n' +
      'Se não for possível determinar com segurança o perfil do narrador, **sorteie uma combinação plausível de gênero e idade**, que seja **coerente com o tom geral do texto**.\n' +
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
      '[TEXTO A SER ANALISADO]\n' +
      '"' + ALivro.GetTrechoPorPersonagem('Narrador') + '"';
  end;

  procedure Generate;
  var
    oPersonagem: TPersonagemFala;
  begin
    try
      oResponse := oIRgnLeitorIAHttp.Generate(oRequestIA);

      if (oResponse.Response.Contains('|')) and (Length(oResponse.Response.Split(['|'])) >= 2) then
      begin
        for oPersonagem in ALivro.GetPersonagem('Narrador') do
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
    oRequestIA.prompt := GetPrompt;
    Generate;

    with TStringList.Create do
    begin
      Add(TimeToStr(Now - dTime));
      for oPersonagem in ALivro.GetPersonagem('Narrador') do
      begin
        Add(oPersonagem.nome + '|' + oPersonagem.genero + '|' + oPersonagem.fala);
      end;
      SaveToFile('NarradorNormalizado.txt');
      Free;
    end;
  finally
    oIRgnLeitorIAHttp.DescarregarModelo;
    oRequestIA.Free;
  end;
end;

end.

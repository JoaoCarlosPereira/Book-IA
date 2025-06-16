unit Rgn.Leitor.Book.Personagens;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, OtlTask,
  Leitor.Book, Rgn.Leitor.IA.Http, System.SyncObjs, Rgn.Leitor.Book.Abstract;

type
  IRgnLeitorBookPersonagens = interface
    ['{2740652E-A163-4B81-9FF5-E8E9E3430FC1}']
    procedure ObterPersonagens(const ALivro: TLivro);
  end;

  TRgnLeitorBookPersonagens = class(TRgnLeitorBookAbstract, IRgnLeitorBookPersonagens)
  private
    procedure NormalizarNomes(const ALivro: TLivro);
    procedure ExtrairPersonagem(const ALivro: TLivro);
    procedure Imprimir(const ATexto: string);
    procedure DefinirPerfilPersonagem(const ALivro: TLivro);
  public
    procedure ObterPersonagens(const ALivro: TLivro);
  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, Helper.HNumeric, StrUtils, System.DateUtils,
  DAO.Leitor.Book, Helper.HString, System.Generics.Defaults, Helper.HComparer,
  System.RegularExpressions;



procedure TRgnLeitorBookPersonagens.ObterPersonagens(const ALivro: TLivro);
begin
  while ALivro.HaPaginasPendentes do
  begin
    ExtrairPersonagem(ALivro);
  end;

  if (not(ALivro.normalizado)) then
  begin
    Imprimir('Normalizando nomes de personagens...');
    ALivro.Clear;
    oIDAOLeitorBook.LocalizarPaginas(ALivro);
    NormalizarNomes(ALivro);
    DefinirPerfilPersonagem(ALivro);
  end;
end;



procedure TRgnLeitorBookPersonagens.Imprimir(const ATexto: string);
begin
  Writeln(ATexto);
end;



procedure TRgnLeitorBookPersonagens.ExtrairPersonagem(const ALivro: TLivro);
var
  oPagina: TPagina;
  oRequestIA: TRequestIA;
  oPersonagens: TStringList;
  oIRgnLeitorIAHttp: IRgnLeitorIAHttp;

const
  PROMPT = 'Extract direct speech and narration from the text. Do not remove or summarize any part of the content — preserve all details.\n' +
    'Output each line in the format:\n' +
    'name|speech\n' +
    'narrator|narration\n\n' +
    'Rules:\n' +
    '- Translate to Portuguese if the text is in another language.\n' +
    '- Correct grammar and spelling (in Portuguese).\n' +
    '- Convert all numerals (e.g., 1, 25, 2025) into their full written form in Portuguese (e.g., um, vinte e cinco, dois mil e vinte e cinco).\n' +
    '- Convert all monetary values (e.g., R$12,50) into full written form (e.g., doze reais e cinquenta centavos).\n' +
    '- Convert all physical measures (e.g., 3 km, 5kg, 1,75m) into full written form with units (e.g., três quilômetros, cinco quilogramas, um metro e setenta e cinco centímetros).\n' +
    '- Remove any page numbers or markers that are not part of the narrative (e.g., "Página 12", "12", "Capítulo 1 - Página 5").\n' +
    '- If multiple characters say the same thing together, join their names with "/" (e.g., João/Maria|Let’s go!).\n' +
    '- Speech usually starts with “—” or is between quotes, but may also be inferred from context.\n' +
    '- Everything else is narration (use the name "narrator").\n' +
    '- Keep the original chronological order of narration and speech.\n' +
    '- Adapt narration and speech to sound natural for voiceover (TTS-ready), but do NOT omit, shorten, or simplify any information or dialogue.\n' +
    '- You may rephrase narration or speech for fluency, but must fully preserve the original meaning and all included details.\n' +
    '- Replace vague or expressive-only lines (e.g. "...", sighs) with narration (e.g., narrator|Ele permaneceu em silêncio).\n' +
    '- Ignore any content not part of the story (such as summaries, author info, dedications, titles, or footnotes).\n' +
    '- Return only the final adapted lines in the correct format — no explanations or additional output.\n\n' +
    'If no valid line is found, return only:\n' +
    'no characters';

  procedure Generate;
  var
    sPersonagem, sResponse: string;
  begin
    if (not(oPagina.Processado)) then
    begin
      oPagina.ListaPersonagens.Clear;
      oIRgnLeitorIAHttp := GetAPI;
      try
        oRequestIA.SetPrompt(PROMPT, oPagina.Texto);
        sResponse := oIRgnLeitorIAHttp.Generate(oRequestIA);

        case AnsiIndexStr(THlpString.RemoverQuebrasDeLinha(sResponse.Trim), ['[change-connection]', 'no characters']) of
          0:
            begin
              Imprimir('Falha de conexão na página ' + oPagina.Numero.ToString + '/' + ALivro.Count.ToString + ' modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local') + '. Reconectando...');
              Generate;
              Exit;
            end;
          1:
            begin
              oPagina.Processado := True;
              oIDAOLeitorBook.SalvarPagina(ALivro, oPagina);
            end

        else
          oPersonagens.Text := sResponse;
          for sPersonagem in oPersonagens do
          begin
            if (sPersonagem.Contains('|')) then
            begin
              oPagina.ListaPersonagens.Add(TPersonagemFala.Create);
              oPagina.ListaPersonagens.Last.nome := TRegEx.Replace(THlpString.RemoverCaracteresEspeciaisNaoASCII(sPersonagem.Split(['|'])[0].Trim), '[^a-zA-ZÀ-ÿ\s!?,\.]', '');
              oPagina.ListaPersonagens.Last.fala := TRegEx.Replace(THlpString.RemoverCaracteresEspeciaisNaoASCII(sPersonagem.Split(['|'])[1].Trim), '[^a-zA-ZÀ-ÿ\s!?,\.]', '');
            end;
          end;

          if (oPagina.ListaPersonagens.Count > 0) then
          begin
            oPagina.Processado := True;
            oIDAOLeitorBook.SalvarPagina(ALivro, oPagina);
            oIDAOLeitorBook.SalvarFala(ALivro, oPagina);
          end;
        end;

        Imprimir('Processada página ' + oPagina.Numero.ToString + '/' + ALivro.Count.ToString + ' modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local'));
      except
        on E: Exception do
        begin
          Imprimir('Falha ' + E.ClassName + ': ' + E.Message + ' na página ' + oPagina.Numero.ToString + '/' + ALivro.Count.ToString + ' modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local') + '. Reconectando...');
          Generate;
        end;
      end;
    end;
  end;



begin
  Imprimir('Preparando para extrair personagens e narrações via IA...');
  oRequestIA   := TRequestIA.Create;
  oPersonagens := TStringList.Create;
  try
    for oPagina in ALivro do
    begin
      Generate;
    end;
  finally
    oRequestIA.Free;
    oPersonagens.Free;
  end;
end;



procedure TRgnLeitorBookPersonagens.NormalizarNomes(const ALivro: TLivro);
var
  oPagina: TPagina;
  oRequestIA: TRequestIA;
  iTentativas: Integer;
  oListaPersonagens: TListaPersonagensFalas;
  oPersonagem, oPersonagemAux: TPersonagemFala;
  oIRgnLeitorIAHttp: IRgnLeitorIAHttp;
  sPersonagens: String;

  function GetPrompt: string;
  begin
    Result :=
      'You will receive a list of lines with:\n' +
      'ID|Name|Speech\n\n' +
      'Your task:\n' +
      '- Standardize names if they refer to the same character\n' +
      '- Use speech content to detect if different names refer to the same speaker\n' +
      '- Merge names that share similar speech tone, phrases, or context\n' +
      '- Always choose the most complete and descriptive proper name for similar cases\n' +
      '- If the name is not a proper name of a specific person (e.g., if it is generic, descriptive, or vague — like "bruxa", "velha", "homem", "mulher", "Unknown", "voz",' + ' "criatura", "alguém", "figura", "pessoa", "sombra", "eles", "ela", "ele", "multidão", etc.), replace it with "narrator"\n' +
      '- Only use "narrator" if there is no specific person’s name\n' +
      '- Gender must be inferred from the name and the speech\n' +
      '- Do not remove or change IDs\n' +
      '- Do not invent new names\n\n' +
      'Output format:\n' +
      'ID|Standardized name|gender\n' +
      'Use only "male" or "female" for gender\n' +
      'Return only the list in the exact format, no comments'
  end;

  procedure Generate;
  var
    sPersonagem, sResponse: string;
    oPersonagens: TStringList;
  begin
    try
      oIRgnLeitorIAHttp := GetAPI(ttaOnline);
      oPersonagens      := TStringList.Create;
      sResponse         := oIRgnLeitorIAHttp.Generate(oRequestIA);
      oPersonagens.Text := sResponse;

      if (sResponse = '[change-connection]') then
      begin
        Imprimir('Falha de conexão - modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local') + '. Reconectando...');

        if (oIRgnLeitorIAHttp.Expirada) then
        begin
          oIDAOLeitorBook.AtualizarAPI(oIRgnLeitorIAHttp.GetKey);
        end;

        oIRgnLeitorIAHttp := GetAPI;
        Generate;
        Exit;
      end;

      for sPersonagem in oPersonagens do
      begin
        if (sPersonagem.Contains('|')) and (Length(sPersonagem.Split(['|'])) >= 2) and (StrToIntDef(sPersonagem.Split(['|'])[0], -1) >= 0) then
        begin
          oPersonagem        := oListaPersonagens[sPersonagem.Split(['|'])[0].ToInteger];
          oPersonagem.nome   := THlpString.RemoveSymbolAndPontuation(sPersonagem.Split(['|'])[1]).toLower;
          oPersonagem.genero := sPersonagem.Split(['|'])[2];
        end
      end;
    except
      on E: Exception do
      begin
        if (iTentativas > 0) or (E.Message.Contains('timed out')) then
        begin
          Inc(iTentativas, -1);
          Sleep(UM_SEGUNDO);
          Generate;
        end
        else
          Raise;
      end;
    end;
  end;



begin
  iTentativas       := 3;
  oRequestIA        := TRequestIA.Create;
  oListaPersonagens := TListaPersonagensFalas.Create(False);

  try
    for sPersonagens in ALivro.GetPersonagens do
    begin
      oPersonagem          := ALivro.GetPersonagem(sPersonagens)[0];
      oPersonagem.auxiliar := sPersonagens;
      oListaPersonagens.Add(oPersonagem);
    end;

    oListaPersonagens.Sort(
      TComparer<TPersonagemFala>.Construct(
      function(const Item1, Item2: TPersonagemFala): Integer
      begin
        Result := 0;

        if (Item1.nome < Item2.nome) then
          Result := Succ(0)
        else if (Item1.nome > Item2.nome) then
          Result := Pred(0)
      end)
      );

    if (oListaPersonagens.Count > 0) then
    begin
      oRequestIA.SetPrompt(GetPrompt, oListaPersonagens.GetPersonagens);
      Generate;

      for oPersonagem in oListaPersonagens do
      begin
        if (oPersonagem.nome <> oPersonagem.auxiliar) then
        begin
          for oPersonagemAux in ALivro.GetPersonagem(oPersonagem.auxiliar) do
          begin
            oPersonagemAux.nome       := oPersonagem.nome;
            oPersonagemAux.genero     := oPersonagem.genero;
            oPersonagemAux.sequencial := oPersonagem.sequencial;
          end;
        end;
      end;

      oListaPersonagens.Clear;
    end;

    ALivro.normalizado := True;
    oIDAOLeitorBook.SalvarPersonagens(ALivro);
    oIDAOLeitorBook.SalvarFalas(ALivro);
    oIDAOLeitorBook.SalvarCabecalho(ALivro);
    oIDAOLeitorBook.RemoverPersonagensSemFala(ALivro);
  finally
    oRequestIA.Free;
    oListaPersonagens.Free;
  end;
end;



procedure TRgnLeitorBookPersonagens.DefinirPerfilPersonagem(const ALivro: TLivro);
var
  oRequestIA: TRequestIA;
  iTentativas, iNumero: Integer;
  sPersonagem: string;

  function GetPrompt: string;
  begin
    Result :=
      'Analyze the input and return the Character profile in this exact format: Gender|Age\n' +
      'Gender must be Male or Female, based on the name.\n' +
      'Age must be Child, Adult, or Elderly, based on the speech style.\n' +
      'Return ONLY the profile in the required format, nothing else.' +
      'Character name:\n"' + sPersonagem + '"\n\n';
  end;

  procedure Generate;
  var
    oPersonagem: TPersonagemFala;
    sResponse: string;
  begin
    try
      sResponse := GetAPI.Generate(oRequestIA);

      if (sResponse.Contains('|')) and (Length(sResponse.Split(['|'])) >= 2) then
      begin
        for oPersonagem in ALivro.GetPersonagem(sPersonagem) do
        begin
          oPersonagem.genero         := sResponse.Split(['|'])[0].Trim;
          oPersonagem.idade_aparente := sResponse.Split(['|'])[1].Trim;
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
          Sleep(UM_SEGUNDO);
          Generate;
        end
        else
          Raise;
      end;
    end;
  end;



begin
  iTentativas := 3;
  iNumero     := 0;
  oRequestIA  := TRequestIA.Create;

  try
    for sPersonagem in ALivro.GetPersonagens do
    begin
      if (sPersonagem <> 'narrator') then
      begin
        Inc(iNumero);
        oRequestIA.SetPrompt(GetPrompt, ALivro.GetTrechoPorPersonagem(sPersonagem));
        Imprimir('Processando personagem "' + sPersonagem + '" Quantidade: ' + iNumero.ToString + '/' + Length(ALivro.GetPersonagens).ToString);
        Generate;
      end;
    end;

    oIDAOLeitorBook.SalvarPersonagens(ALivro);
  finally
    oRequestIA.Free;
  end;
end;

end.

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
  public
    procedure ObterPersonagens(const ALivro: TLivro);
  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, Helper.HNumeric, StrUtils, System.DateUtils,
  DAO.Leitor.Book;



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
  end;
end;



procedure TRgnLeitorBookPersonagens.Imprimir(const ATexto: string);
begin
  Writeln(ATexto);
end;



procedure TRgnLeitorBookPersonagens.ExtrairPersonagem(const ALivro: TLivro);
var
  iNumeroPagina: Integer;
  oPagina: TPagina;
  oRequestIA: TRequestIA;
  oPersonagens: TStringList;
  oIRgnLeitorIAHttp: IRgnLeitorIAHttp;

const
  PROMPT = 'Extract direct speech and narration from the Portuguese text.\n' +
    'Output each line in the format:\n' +
    'name|speech\n' +
    'narrator|narration\n\n' +
    'Rules:\n' +
    '- If multiple characters say the same thing together, join their names with "/" (e.g., João/Maria|Let''s go!).\n' +
    '- Speech usually starts with “—” or is between quotes, but may also be inferred from context.\n' +
    '- Everything else is narration (use the name "narrator").\n' +
    '- Maintain the original chronological order of narration and speech.\n' +
    '- Correct grammar and spelling (in Portuguese).\n' +
    '- Adapt narration and speech to be natural for voiceover (TTS-ready).\n' +
    '- You may rephrase narration or speech, but do not change the core meaning or story outcome.\n' +
    '- Replace silent, vague or expressive-only lines like "..." or sighs with a narration (e.g. narrator|Mat remains silent).\n' +
    '- Translate to Portuguese if the text is in English.\n' +
    '- Ignore any content that is not part of the story, such as notes, summaries, author info, dedications, or titles.\n' +
    '- Do not return any explanations, only the final adapted lines in the correct format.\n\n' +
    'If no valid line is found, return only:\n' +
    'no characters';

  procedure Generate;
  var
    sPersonagem, sResponse: string;
  begin
    oIRgnLeitorIAHttp := GetAPI;
    try
      oRequestIA.SetPrompt(PROMPT, oPagina.Texto);
      sResponse := oIRgnLeitorIAHttp.Generate(oRequestIA);

      case AnsiIndexStr(sResponse, ['[change-connection]', 'no characters']) of
        0:
          begin
            Imprimir('Falha de conexão na página ' + oPagina.Numero.ToString + '/' + ALivro.Count.ToString + ' modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local') + '. Reconectando...');
            Generate;
          end;
        1:
          begin
            Exit;
          end

      else
        oPersonagens.Text := sResponse;
        for sPersonagem in oPersonagens do
        begin
          if (sPersonagem.Contains('|')) then
          begin
            oPagina.ListaPersonagens.Add(TPersonagemFala.Create);
            oPagina.ListaPersonagens.Last.nome := sPersonagem.Split(['|'])[0].Trim;
            oPagina.ListaPersonagens.Last.fala := sPersonagem.Split(['|'])[1].Replace('—', '').Trim;
          end;
        end;

        if (oPagina.ListaPersonagens.Count > 0) then
        begin
          oPagina.Processado := True;
          oIDAOLeitorBook.SalvarPagina(ALivro, oPagina);
          oIDAOLeitorBook.SalvarFala(ALivro, oPagina);
        end;

        Inc(iNumeroPagina);
        Imprimir('Processada página ' + oPagina.Numero.ToString + ' - Total Geral: ' + iNumeroPagina.ToString + '/' + ALivro.Count.ToString + ' modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local'));
      end;

    except
      on E: Exception do
      begin
        Imprimir('Falha ' + E.ClassName + ': ' + E.Message + ' na página ' + oPagina.Numero.ToString + '/' + ALivro.Count.ToString + ' modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local') + '. Reconectando...');
        Generate;
      end;
    end;
  end;



begin
  iNumeroPagina := 0;
  Imprimir('Preparando para extrair personagens e narrações via IA...');
  oRequestIA   := TRequestIA.Create;
  oPersonagens := TStringList.Create;
  try
    for oPagina in ALivro do
    begin
      if (not(oPagina.Processado)) then
      begin
        Generate;
      end;
    end;
  finally
    oRequestIA.Free;
    oPersonagens.Free;
  end;

  // TRgnSistemaThreadFactory.CriarLoopTasks(oListaAPIs.Count, ALivro,
  // procedure(const ATask: IOmniTask; const AObjeto: TObject)
  // var
  // oPagina: TPagina;
  // oRequestIA: TRequestIA;
  // oPersonagens: TStringList;
  // oIRgnLeitorIAHttp: IRgnLeitorIAHttp;
  //
  // function GetPrompt: string;
  // begin
  // Result :=
  // 'Extract direct speech and narration from the Portuguese text.\n' +
  // 'Output each line in the format:\n' +
  // 'name|speech\n' +
  // 'narrator|narration\n\n' +
  // 'Rules:\n' +
  // '- If multiple characters say the same thing together, join their names with "/" (e.g., João/Maria|Let''s go!).\n' +
  // '- Speech usually starts with “—” or is between quotes, but may also be inferred from context.\n' +
  // '- Everything else is narration (use the name "narrator").\n' +
  // '- Maintain the original chronological order of narration and speech.\n' +
  // '- Correct grammar and spelling (in Portuguese).\n' +
  // '- Adapt narration and speech to be natural for voiceover (TTS-ready).\n' +
  // '- You may rephrase narration or speech, but do not change the core meaning or story outcome.\n' +
  // '- Replace silent, vague or expressive-only lines like "..." or sighs with a narration (e.g. narrator|Mat remains silent).\n' +
  // '- Translate to Portuguese if the text is in English.\n' +
  // '- Ignore any content that is not part of the story, such as notes, summaries, author info, dedications, or titles.\n' +
  // '- Do not return any explanations, only the final adapted lines in the correct format.\n\n' +
  // 'If no valid line is found, return only:\n' +
  // 'no characters';
  // end;
  //
  // procedure Generate;
  // var
  // sPersonagem, sResponse: string;
  // begin
  // try
  // try
  // if (oIRgnLeitorIAHttp.GetTipo = ttaLocal) then
  // oCriticalSection.Enter;
  //
  // sResponse := oIRgnLeitorIAHttp.Generate(oRequestIA);
  //
  // if (oIRgnLeitorIAHttp.GetTipo = ttaLocal) then
  // oCriticalSection.Release;
  //
  // oPagina.Response := sResponse;
  // oPagina.ListaPersonagens.Clear;
  //
  // if (sResponse = '[change-connection]') then
  // begin
  // Imprimir('Falha de conexão na página ' + oPagina.Numero.ToString + '/' + ALivro.Count.ToString + ' modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local') + '. Reconectando...');
  //
  // if (oIRgnLeitorIAHttp.Expirada) then
  // begin
  // oCriticalSection.Enter;
  // oIDAOLeitorBook.AtualizarAPI(oIRgnLeitorIAHttp.GetKey);
  // oCriticalSection.Release;
  // end;
  //
  // oIRgnLeitorIAHttp.SetUso(False);
  // oIRgnLeitorIAHttp := GetAPI(ttaLocal);
  // Generate;
  // Exit;
  // end;
  //
  // if (not(sResponse.Contains('no characters'))) then
  // begin
  // if (sResponse.Contains('|')) then
  // begin
  // oPersonagens.Text := sResponse;
  // for sPersonagem in oPersonagens do
  // begin
  // if (sPersonagem.Contains('|')) then
  // begin
  // oPagina.Processado := True;
  // oPagina.ListaPersonagens.Add(TPersonagemFala.Create);
  // oPagina.ListaPersonagens.Last.nome := sPersonagem.Split(['|'])[0].Trim;
  // oPagina.ListaPersonagens.Last.fala := sPersonagem.Split(['|'])[1].Replace('—', '').Trim;
  // end;
  // end;
  //
  // if (oPagina.ListaPersonagens.Count > 0) then
  // begin
  // oCriticalSection.Enter;
  // oPagina.Processado := True;
  // oIDAOLeitorBook.SalvarPagina(ALivro, oPagina);
  // oIDAOLeitorBook.SalvarFala(ALivro, oPagina);
  // oCriticalSection.Release;
  // end;
  // end
  // else
  // begin
  // Imprimir('Falha de conexão na página ' + oPagina.Numero.ToString + '/' + ALivro.Count.ToString + ' modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local') + '. Reconectando...');
  // oIRgnLeitorIAHttp.SetUso(False);
  // oIRgnLeitorIAHttp := GetAPI(ttaLocal);
  // Generate;
  // Exit;
  // end;
  // end;
  //
  // oCriticalSection.Enter;
  // Inc(iNumeroPagina);
  // oCriticalSection.Release;
  //
  // Imprimir('Processada página ' + oPagina.Numero.ToString + ' - Total Geral: ' + iNumeroPagina.ToString + '/' + ALivro.Count.ToString + ' modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local'));
  // except
  // on E: Exception do
  // begin
  // Imprimir('Falha ' + E.ClassName + ': ' + E.Message + ' na página ' + oPagina.Numero.ToString + '/' + ALivro.Count.ToString + ' modo: ' + IfThen(oIRgnLeitorIAHttp.GetTipo = ttaOnline, 'Online', 'Local') + '. Reconectando...');
  // oIRgnLeitorIAHttp.SetUso(False);
  // oIRgnLeitorIAHttp := GetAPI(ttaLocal);
  // Generate;
  // end;
  // end;
  // finally
  //
  // Sleep(UM_SEGUNDO);
  // end;
  // end;
  //
  //
  //
  // begin
  // oPagina := TPagina(AObjeto);
  // if (not(oPagina.Processado)) then
  // begin
  // oIRgnLeitorIAHttp := GetAPI;
  // oRequestIA := TRequestIA.Create;
  // oPersonagens := TStringList.Create;
  // try
  //
  // oRequestIA.SetPrompt(GetPrompt, oPagina.Texto);
  // oPagina.PROMPT := oRequestIA.ToJson;
  // Generate;
  //
  // finally
  // oPersonagens.Free;
  // oRequestIA.Free;
  // oIRgnLeitorIAHttp.SetUso(False);
  // end;
  // end;
  // end);
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
      '- Use speech content to detect if different names (like "bruxa", "velha", "Unknown") are actually the same speaker\n' +
      '- Merge names that share similar speech tone, phrases, or context\n' +
      '- Always choose the most complete and descriptive name for all similar cases\n' +
      '- If the name is generic or not a proper name (e.g., "bruxa", "velha", "homem", "mulher", "pessoa", "Unknown", "ele", "ela", "voz", "multidão", "criatura"...), replace it with "narrator"\n' +
      '- Gender must be inferred using name and speech\n' +
      '- Do not remove or change IDs\n' +
      '- Do not invent any new names\n\n' +
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
      oPersonagens.SaveToFile(ALivro.nome + '.txt');

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

end.

unit Rgn.Leitor.Book.Vozes;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, OtlTask,
  Leitor.Book, Rgn.Leitor.IA.Http, Rgn.Leitor.Book.Abstract;

type
  IRgnLeitorBookVozes = interface
    ['{6E325157-C547-4254-B77B-0E55BB4FA240}']
    procedure ObterVozes(const ALivro: TLivro);
  end;

  TRgnLeitorBookVozes = class(TRgnLeitorBookAbstract, IRgnLeitorBookVozes)
  private
    oListaVozes: TListaVozes;
    procedure DefinirVozes(const ALivro: TLivro);
    procedure Gravar(const ALivro: TLivro);
    procedure Unificar(const ALivro: TLivro);
    procedure CriarTrilha(const ALivro: TLivro);
  public
    constructor Create;
    destructor Destroy; override;
    procedure ObterVozes(const ALivro: TLivro);
  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, Helper.HNumeric, Rgn.Leitor.Book.VozesHttp,
  DAO.Leitor.Book, Helper.HString, Windows, MMSystem,
  System.RegularExpressions, Winapi.ShellAPI, Vcl.MPlayer, DateUtils;



constructor TRgnLeitorBookVozes.Create;
begin
  inherited;
  oListaVozes := TListaVozes.Create;
end;



destructor TRgnLeitorBookVozes.Destroy;
begin
  oListaVozes.Free;
  inherited;
end;



procedure TRgnLeitorBookVozes.Gravar(const ALivro: TLivro);
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
  sPersonagem: string;
  oVozTTS: TTTSVoice;
  sTrecho: string;
  oTextoFala, oArquivosSaida: TStringList;
  iIndice: Integer;
begin
  Writeln('Gravando Falas...');

  oVozTTS        := TTTSVoice.Create;
  oTextoFala     := TStringList.Create;
  oArquivosSaida := TStringList.Create;
  try
    for oPagina in ALivro do
    begin
      Writeln('Gravando Página ' + oPagina.Numero.ToString + ' de ' + ALivro.Count.ToString + '.');
      for oPersonagem in oPagina.ListaPersonagens do
      begin
        if (not(oPersonagem.processado)) and (not(oPersonagem.fala.contains('@@'))) then
        begin
          sTrecho         := TRegEx.Replace(oPersonagem.fala, '[^a-zA-ZÀ-ÿ\s!?:,\.]', '');
          sTrecho         := StringReplace(sTrecho, '.', #13#10, [rfReplaceAll]);
          sTrecho         := StringReplace(sTrecho, '?', '?' + #13#10, [rfReplaceAll]);
          sTrecho         := StringReplace(sTrecho, '!', '!' + #13#10, [rfReplaceAll]);
          sTrecho         := StringReplace(sTrecho, ':', ':' + #13#10, [rfReplaceAll]);
          oTextoFala.Text := sTrecho;

          with TStringList.Create do
          begin
            Text        := sTrecho;
            for iIndice := 0 to Pred(Count) do
            begin
              if (Strings[iIndice].trim.Length >= 200) then
              begin
                oTextoFala[iIndice] := StringReplace(oTextoFala[iIndice], ',', ',' + #13#10, [rfReplaceAll]);
              end;
            end;
          end;

          if (THlpString.RemoverQuebrasDeLinha(oTextoFala.Text).trim <> EmptyStr) then
          begin
            for iIndice := 0 to Pred(oTextoFala.Count) do
            begin
              oVozTTS.input_text := oTextoFala[iIndice].trim;
              oVozTTS.output     := '/dsv/TTS/out/' + ALivro.nome + '/partes/Pagina_' + oPagina.Numero.ToString + '_Trecho_' + oPersonagem.sequencialFala.ToString + '-' + iIndice.ToString + '.wav';
              oArquivosSaida.Add('file ' + QuotedStr('S:\' + oVozTTS.output.Replace('/', '\').Replace('.wav', '.mp3')));
              oVozTTS.ref_audio := oPersonagem.Voz.nome;
              if (TRgnLeitorBookVozesHttp.Create.Ref.Gravar(oVozTTS)) then
              begin
                oPersonagem.processado := True;
                oPersonagem.ArquivosAudio.Add('S:\' + oVozTTS.output.Replace('/', '\').Replace('.wav', '.mp3'));
              end;
            end;
          end
          else
            oPersonagem.processado := True;
        end;
      end;
      oIDAOLeitorBook.SalvarFala(ALivro, oPagina);
    end;
    oArquivosSaida.SaveToFile('S:\dsv\TTS\out\' + ALivro.nome + '\partes\lista.txt');

    if (not(ALivro.HaPaginasPendentes)) then
    begin
      Unificar(ALivro);
      ALivro.produzido := True;
      oIDAOLeitorBook.SalvarCabecalho(ALivro);
    end;
  finally
    oVozTTS.Free;
    oTextoFala.Free;
    oArquivosSaida.Free;
  end;
end;



procedure TRgnLeitorBookVozes.ObterVozes(const ALivro: TLivro);
begin
  if (not(ALivro.produzido)) then
  begin
    Writeln('Definindo Vozes...');
    ALivro.Clear;
    oIDAOLeitorBook.LocalizarPaginas(ALivro);
    DefinirVozes(ALivro);
    Gravar(ALivro);
  end;
end;



procedure TRgnLeitorBookVozes.Unificar(const ALivro: TLivro);
var
  oComandoUnir: TStringList;
begin
  oComandoUnir := TStringList.Create;
  try
    oComandoUnir.LoadFromFile('S:\dsv\TTS\out\unir.bat');
    oComandoUnir.Text := StringReplace(oComandoUnir.Text, 'lista.txt', 'S:\dsv\TTS\out\' + ALivro.nome + '\partes\lista.txt', [rfReplaceAll]);
    oComandoUnir.Text := StringReplace(oComandoUnir.Text, 'output.mp3', 'S:\dsv\TTS\out\' + ALivro.nome + '\Saida.mp3', [rfReplaceAll]);
    oComandoUnir.SaveToFile('S:\dsv\TTS\out\unir.bat');
    WinExec(PAnsiChar(AnsiString('cmd.exe /c "S:\dsv\TTS\out\unir.bat"')), SW_HIDE);
  finally
    oComandoUnir.Free;
  end;
end;



procedure TRgnLeitorBookVozes.CriarTrilha(const ALivro: TLivro);
var
  oPlayer: TMediaPlayer;
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
  iDuracao: Integer;
  sArquivo, sTrecho, sResponse: String;
  tDuracao: TTime;
  oRequestIA: TRequestIA;
  oIRgnLeitorIAHttp: IRgnLeitorIAHttp;
  oTrilha: TTrilha;

  function GetPrompt: string;
  begin
    Result := 'You are a specialist in cinematic soundtrack creation for audiobooks.\n' +
      'You will receive a list of book excerpts, each accompanied by a time range representing when it occurs during the audiobook playback.\n' +
      'Your task is to read the excerpts (written in Portuguese), understand their emotional tone, ambiance, and narrative content, and then produce a single, coherent, descriptive text prompt in English.\n' +
      'This final prompt will be used as input to generate a background instrumental soundtrack using Facebook''s MusicGen model.\n' +
      'The generated soundtrack should reflect the combined atmosphere of all excerpts.\n' +
      'Avoid vocals, strong rhythms or abrupt transitions. Favor immersive, cinematic, and emotionally appropriate instrumental music.\n' +
      '### Expected Output:\n' +
      'Return only one single English prompt that describes the ideal soundtrack, like this:\n' +
      '"An atmospheric, suspenseful instrumental soundtrack with slow tempo and orchestral elements like soft strings, ambient pads, and subtle percussions. Designed for a tense night scene on a cliff with wind, danger, and emotional restraint."\n' +
      '\n' +
      'Do not return any explanation or additional text. Return only the prompt in English between quotes.';
  end;



begin
  oPlayer    := TMediaPlayer.Create(nil);
  oRequestIA := TRequestIA.Create;
  oTrilha    := TTrilha.Create;
  try
    for oPagina in ALivro do
    begin
      for oPersonagem in oPagina.ListaPersonagens do
      begin
        if (oPersonagem.processado) then
        begin
          for sArquivo in oPersonagem.ArquivosAudio do
          begin
            oPlayer.FileName := sArquivo;
            oPlayer.Open;
            oPersonagem.Duracao := oPersonagem.Duracao + oPlayer.Length div 1000; // Milissegundos para segundos
            oPagina.Duracao     := oPagina.Duracao + oPersonagem.Duracao;
            oPlayer.Close;
          end;
        end;
      end;
    end;

    if (ALivro.DuracaoTotal > 300) then
    begin
      for oPagina in ALivro do
      begin
        tDuracao := 0;
        for oPersonagem in oPagina.ListaPersonagens do
        begin
          sTrecho  := sTrecho + oPersonagem.fala + ' [' + TimeToStr(tDuracao) + ' - ' + TimeToStr(IncSecond(tDuracao, oPersonagem.Duracao)) + ' \n';
          tDuracao := IncSecond(tDuracao, oPersonagem.Duracao);
        end;
        oRequestIA.SetPrompt(GetPrompt, sTrecho);
        oIRgnLeitorIAHttp := GetAPI;

        oTrilha.prompt := oIRgnLeitorIAHttp.Generate(oRequestIA);
        oTrilha.output := '/dsv/TTS/out/' + ALivro.nome + '/partes/Trilha_Pag_' + oPagina.Numero.ToString + '.wav';
        TRgnLeitorBookVozesHttp.Create.Ref.GerarTrilha(oTrilha)
      end;
    end
    else
    begin
      tDuracao := 0;
      for oPagina in ALivro do
      begin
        for oPersonagem in oPagina.ListaPersonagens do
        begin
          sTrecho  := sTrecho + oPersonagem.fala + ' [' + TimeToStr(tDuracao) + ' - ' + TimeToStr(IncSecond(tDuracao, oPersonagem.Duracao)) + ' \n';
          tDuracao := IncSecond(tDuracao, oPersonagem.Duracao);
        end;
      end;

      oRequestIA.SetPrompt(GetPrompt, sTrecho);
      oIRgnLeitorIAHttp := GetAPI;

      oTrilha.prompt := oIRgnLeitorIAHttp.Generate(oRequestIA);
      oTrilha.output := '/dsv/TTS/out/' + ALivro.nome + '/partes/Trilha.wav';
      TRgnLeitorBookVozesHttp.Create.Ref.GerarTrilha(oTrilha)
    end;
  finally
    oPlayer.Free;
    oRequestIA.Free;
    oTrilha.Free;
  end;
end;



procedure TRgnLeitorBookVozes.DefinirVozes(const ALivro: TLivro);
var
  oPersonagem, oPersonagemAux: TPersonagemFala;
  sPersonagem: string;
  oVoz: TVoz;
begin
  oIDAOLeitorBook.LocalizarVozes(oListaVozes);

  oPersonagem := ALivro.GetPersonagem('narrator')[0];
  if (oPersonagem.Voz.Sequencial = 0) then
  begin
    oVoz := oListaVozes.GetVoz(oPersonagem.genero, oPersonagem.idade_aparente);
    if (Assigned(oVoz)) then
    begin
      for oPersonagemAux in ALivro.GetPersonagem('narrator') do
      begin
        oPersonagemAux.Voz.Sequencial := oVoz.Sequencial;
        oPersonagemAux.Voz.nome       := oVoz.nome;
      end;
    end;
  end;

  for sPersonagem in ALivro.GetPersonagens do
  begin
    if (sPersonagem = 'narrator') then
      Continue;

    oPersonagem := ALivro.GetPersonagem(sPersonagem)[0];
    if (oPersonagem.Voz.Sequencial = 0) then
    begin
      oVoz := oListaVozes.GetVoz(oPersonagem.genero, oPersonagem.idade_aparente);
      if (not(Assigned(oVoz))) then
        oVoz := oListaVozes.GetVoz(oPersonagem.genero, '');

      if (not(Assigned(oVoz))) then
        oVoz := ALivro.GetPersonagem('narrator')[0].Voz;

      if (Assigned(oVoz)) then
      begin
        for oPersonagemAux in ALivro.GetPersonagem(sPersonagem) do
        begin
          oPersonagemAux.Voz.Sequencial := oVoz.Sequencial;
          oPersonagemAux.Voz.nome       := oVoz.nome;
        end;
      end;
    end;
  end;

  oIDAOLeitorBook.SalvarPersonagens(ALivro);
end;

end.

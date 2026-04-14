unit Rgn.Leitor.PDF;

interface

uses
  System.SysUtils, System.Classes;

type
  IRgnLeitorPDF = interface
    ['{71DC33FB-2F05-4980-99E2-0F0191C10B21}']
    function LerPDFPorPagina(const ACaminhoPDF: string): TStringList;
  end;

  TRgnLeitorPDF = class(TInterfacedPersistent, IRgnLeitorPDF)
  public
    function LerPDFPorPagina(const ACaminhoPDF: string): TStringList;
  end;

implementation

uses
  Winapi.ShellAPI, Winapi.Windows, System.IOUtils, Helper.HNumeric,
  Rgn.Leitor.IA.Http;



function ExecutarComando(const Executavel, Parametros: string): Boolean;
var
  SEInfo: TShellExecuteInfo;
begin
  ZeroMemory(@SEInfo, SizeOf(SEInfo));
  SEInfo.cbSize       := SizeOf(TShellExecuteInfo);
  SEInfo.fMask        := SEE_MASK_NOCLOSEPROCESS;
  SEInfo.Wnd          := 0;
  SEInfo.lpVerb       := 'open';
  SEInfo.lpFile       := PChar(Executavel);
  SEInfo.lpParameters := PChar(Parametros);
  SEInfo.nShow        := SW_HIDE;

  if ShellExecuteEx(@SEInfo) then
  begin
    WaitForSingleObject(SEInfo.hProcess, INFINITE);
    CloseHandle(SEInfo.hProcess);
    Result := True;
  end
  else
    Result := False;
end;



function TRgnLeitorPDF.LerPDFPorPagina(const ACaminhoPDF: string): TStringList;
var
  OutputPath, Cmd, TempText: string;
  SL: TStringList;

  procedure CortarTextoPorTokens(const Texto: string; MaxTokens: Integer);
  var
    Sentencas: TArray<string>;
    Sentenca, BlocoAtual, sSentencaManipucao: string;
    TokenCount, TotalTokens: Integer;
    Palavras: TArray<string>;
  begin
    // Corta apenas por pontos finais (não por ! ou ?)
    Sentencas   := Texto.Split(['.'], TStringSplitOptions.ExcludeEmpty);
    BlocoAtual  := '';
    TotalTokens := 0;

    for Sentenca in Sentencas do
    begin
      sSentencaManipucao := Sentenca.Trim;
      if sSentencaManipucao.Trim = '' then
        Continue;

      sSentencaManipucao := sSentencaManipucao + '.'; // reanexa o ponto final

      Palavras   := sSentencaManipucao.Split([' '], TStringSplitOptions.ExcludeEmpty);
      TokenCount := Length(Palavras);

      if TotalTokens + TokenCount > MaxTokens then
      begin
        Result.Add(Trim(BlocoAtual));
        BlocoAtual  := sSentencaManipucao + ' ';
        TotalTokens := TokenCount;
      end
      else
      begin
        BlocoAtual := BlocoAtual + sSentencaManipucao + ' ';
        Inc(TotalTokens, TokenCount);
      end;
    end;

    if BlocoAtual.Trim <> '' then
      Result.Add(Trim(BlocoAtual));
  end;



begin
  OutputPath := ACaminhoPDF.Replace(ExtractFileName(ACaminhoPDF), ExtractFileName(ACaminhoPDF).Replace(' ', '_'));
  RenameFile(ACaminhoPDF, OutputPath);

  if (DirectoryExists('C:\Users\s293\AppData\Local\Programs\Python\Python313')) then
    Cmd := Format('%s %s %s', ['C:\Users\s293\AppData\Local\Programs\Python\Python313\python.exe', 'extrair_pdf.py', OutputPath])
  else
    Cmd := Format('%s %s %s', ['C:\Users\Windows\AppData\Local\Programs\Python\Python313\python.exe', 'extrair_pdf.py', OutputPath]);
  WinExec(PAnsiChar(AnsiString(Cmd)), SW_HIDE);
  OutputPath := OutputPath.Replace('.pdf', '.txt');

  while (not FileExists(OutputPath)) do
  begin
    Sleep(UM_SEGUNDO);
  end;

  Sleep(UM_MINUTO);

  if not FileExists(OutputPath) then
    raise Exception.Create('Falha ao gerar o arquivo de saída .txt');

  // 5. Carregar o texto dividido por páginas
  SL     := TStringList.Create;
  Result := TStringList.Create;
  try
    SL.LoadFromFile(OutputPath, TEncoding.UTF8);
    TempText    := StringReplace(SL.Text, sLineBreak, ' ', [rfReplaceAll]);;
    Result.Text := StringReplace(TempText, '===PAGINA===', #13#10, [rfReplaceAll]);
  finally
    SL.Free;
  end;
end;

end.

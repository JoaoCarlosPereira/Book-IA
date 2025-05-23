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
  Winapi.ShellAPI, Winapi.Windows, System.IOUtils, Helper.HNumeric;



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
  PythonPath: string;
  ProcHandle: THandle;
begin
  Cmd        := Format('%s %s %s', ['C:\Users\s293\AppData\Local\Programs\Python\Python313\python.exe', 'extrair_pdf.py', ACaminhoPDF]);
  ProcHandle := WinExec(PAnsiChar(AnsiString(Cmd)), SW_HIDE);
  OutputPath := ACaminhoPDF.Replace('.pdf', '.txt');

  while (not FileExists(OutputPath)) do
  begin
    Sleep(1000);
  end;

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
    TFile.Delete(OutputPath);
  end;
end;

end.

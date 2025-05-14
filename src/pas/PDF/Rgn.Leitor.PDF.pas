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
  sPastaTemporaria, sNomeBase, sArquivoPagina, sTextoPagina: string;
  oPaginas: TStringList;
  iContador, iCasas: Integer;
begin
  Result := TStringList.Create;
  try
    sPastaTemporaria := IncludeTrailingPathDelimiter(GetEnvironmentVariable('TEMP') + '\pdfsplit_' + FormatDateTime('dd_mm_yyyy_hh_nn_ss_zzz', Now) + '_' + GetNumeroRandomico);
    ForceDirectories(sPastaTemporaria);

    // Passo 1 - Dividir o PDF por páginas
    if (not(ExecutarComando('C:\Program Files\qpdf\bin\qpdf.exe', Format('--split-pages "%s" "%spag_%%d.pdf"', [ACaminhoPDF, sPastaTemporaria])))) then
      raise Exception.Create('Erro ao dividir PDF com QPDF.');

    // Passo 2 - Ler os arquivos gerados e extrair texto
    iContador := 1;
    iCasas    := 2;
    while True do
    begin
      sArquivoPagina := Format('%spag_%s.pdf', [sPastaTemporaria, Format('%.' + iCasas.ToString + 'd', [iContador])]);
      if (not(FileExists(sArquivoPagina))) then
      begin
        if (iCasas <= 5) then
        begin
          Inc(iCasas);
          Continue
        end
        else
          Break;
      end;

      sTextoPagina := sArquivoPagina.Replace('.pdf', '.txt');

      if (not(ExecutarComando('pdftotext.exe', Format('"%s" "%s"', [sArquivoPagina, sTextoPagina])))) then
        raise Exception.CreateFmt('Erro ao extrair texto da página %d.', [iContador]);

      if (FileExists(sTextoPagina)) then
      begin
        oPaginas := TStringList.Create;
        try
          oPaginas.LoadFromFile(sTextoPagina, TEncoding.UTF8);
          Result.Add(oPaginas.Text.Trim);
        finally
          oPaginas.Free;
        end;
      end;

      Inc(iContador);
    end;
  finally
    TDirectory.Delete(sPastaTemporaria, True); // descomente se quiser remover os arquivos
  end;

  // Limpeza opcional dos arquivos temporários

end;

end.

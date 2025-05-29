unit Rgn.Leitor.Book;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, OtlTask,
  Leitor.Book, Rgn.Leitor.PDF, Rgn.Leitor.Book.Personagens,
  Rgn.Leitor.Book.Narrador, System.Generics.Defaults, DAO.Leitor.Book;

type
  IRgnLeitorBook = interface
    ['{7CE41228-2682-49C9-A436-209B66DFB41B}']
    procedure ProcessarBook(const ALivroPDF: String);
    procedure MonitorarNovosBooks;
  end;

  TRgnLeitorBook = class(TInterfacedPersistent, IRgnLeitorBook)
  private
    oLivro: TLivro;
    oIRgnLeitorPDF: IRgnLeitorPDF;
    oIRgnLeitorBookPersonagens: IRgnLeitorBookPersonagens;
    oIRgnLeitorBookNarrador: IRgnLeitorBookNarrador;
    oIDAOLeitorBook: IDAOLeitorBook;

    procedure MonitorarArquivos(const ATask: IOmniTask);
  public
    constructor Create;
    function Ref: IRgnLeitorBook;
    destructor Destroy; override;
    procedure ProcessarBook(const ALivroPDF: String);
    procedure MonitorarNovosBooks;
  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, Rgn.Leitor.IA.Http, Winapi.Windows;



constructor TRgnLeitorBook.Create;
begin
  oLivro                     := TLivro.Create;
  oIRgnLeitorPDF             := TRgnLeitorPDF.Create;
  oIRgnLeitorBookPersonagens := TRgnLeitorBookPersonagens.Create;
  oIRgnLeitorBookNarrador    := TRgnLeitorBookNarrador.Create;
  oIDAOLeitorBook            := TDAOLeitorBook.Create;
end;



procedure TRgnLeitorBook.ProcessarBook(const ALivroPDF: String);
var
  oPaginas: TStringList;
  sTexto: string;
  iNumero: Integer;
begin
  oLivro.Nome := ExtractFileName(ALivroPDF).Replace('.pdf', '').Replace(' ', '_');
  oIDAOLeitorBook.LocalizarCabecalho(oLivro);

  if (oLivro.lido) then
  begin
    Writeln('Baixando Livro do banco de dados...');
    oIDAOLeitorBook.LocalizarPaginas(oLivro);
  end
  else
  begin
    oLivro.Clear;
    Writeln('Lendo PDF...');
    oPaginas := oIRgnLeitorPDF.LerPDFPorPagina(ALivroPDF);
    iNumero  := 1;
    for sTexto in oPaginas do
    begin
      if (sTexto.Trim <> EmptyStr) then
      begin
        oLivro.Add(TPagina.Create);
        oLivro.Last.Numero := iNumero;
        oLivro.Last.Texto  := sTexto.Trim;

        inc(iNumero);
      end;
    end;

    Writeln('Salvando páginas no banco de dados...');
    oLivro.lido := True;
    oIDAOLeitorBook.SalvarCabecalho(oLivro);
    oIDAOLeitorBook.SalvarPaginas(oLivro);
    oPaginas.Free;
  end;

  if (oLivro.Count > 0) then
  begin
    oIRgnLeitorBookPersonagens.ObterPersonagens(oLivro);
    oIRgnLeitorBookNarrador.ObterNarrador(oLivro);
  end;
end;



function TRgnLeitorBook.Ref: IRgnLeitorBook;
begin
  Result := Self;
end;



destructor TRgnLeitorBook.Destroy;
begin
  oLivro.Free;
  inherited;
end;



procedure TRgnLeitorBook.MonitorarNovosBooks;
var
  oArquivos: TStringDynArray;
  sArquivo: string;
  dTempo: TTime;
  iTempo: Integer;

const
  DiretorioPDFS = 'S:\dsv\NLP\pdfs\processar';
begin
  if (DirectoryExists(DiretorioPDFS)) then
  begin
    try
      oArquivos := TDirectory.GetFiles(DiretorioPDFS);
      Writeln('Procurando PDFs...');
      for sArquivo in oArquivos do
      begin
        if (not(sArquivo.ToLower.Contains('.pdf'))) then
          Continue;

        dTempo := Now;
        Writeln('Processando livro: ' + ExtractFileName(sArquivo));
        for iTempo := 60 downto 0 do
        begin
          Writeln('Resetando APIs, por favor aguarde ' + iTempo.ToString + 's.');
          Sleep(UM_SEGUNDO);
        end;

        ProcessarBook(sArquivo);
        TFile.Copy(sArquivo, sArquivo.Replace('processar', 'processado'));
        TFile.Delete(sArquivo);
        Writeln('Finalizado, Tempo de processamento: ' + TimeToStr(Now - dTempo));
      end;
      MonitorarNovosBooks;
    except
      on E: Exception do
      begin
        Writeln(E.ClassName, ': ', E.Message);
        with TStringList.Create do
        begin
          Add(E.Message + '|' + E.ClassName + '|' + E.StackTrace);
          SaveToFile('LogErro.log');
          Free;
        end;
      end;
    end;
  end
  else
  begin
    Writeln('Diretório: \\192.168.2.162\Dados\dsv\NLP\pdfs Não existe');
  end;
end;



procedure TRgnLeitorBook.MonitorarArquivos(const ATask: IOmniTask);
var
  oArquivos: TStringDynArray;
  sArquivo: string;
  dTempo: TTime;
  iTempo: Integer;
begin
  try
    oArquivos := TDirectory.GetFiles('D:\dsv\NLP\pdfs\processar');
    Writeln('Procurando PDFs...');
    for sArquivo in oArquivos do
    begin
      if (not(sArquivo.ToLower.Contains('.pdf'))) then
        Continue;

      dTempo := Now;
      Writeln('Processando livro: ' + ExtractFileName(sArquivo));
      for iTempo := 60 downto 0 do
      begin
        Writeln('Resetando APIs, por favor aguarde ' + iTempo.ToString + 's.');
        Sleep(UM_SEGUNDO);
      end;
      ProcessarBook(sArquivo);
      TFile.Copy(sArquivo, sArquivo.Replace('processar', 'processado'));
      TFile.Delete(sArquivo);
      Writeln('Finalizado, Tempo de processamento: ' + TimeToStr(Now - dTempo));
    end;
    MonitorarArquivos(ATask);
  except
    on E: Exception do
    begin
      Writeln(E.ClassName, ': ', E.Message);
      with TStringList.Create do
      begin
        Add(E.Message + '|' + E.ClassName + '|' + E.StackTrace);
        SaveToFile('LogErro.log');
        Free;
      end;
    end;
  end;
end;

end.

unit Rgn.Leitor.Book;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, OtlTask,
  Leitor.Book, Rgn.Leitor.PDF, Rgn.Leitor.Book.Personagens,
  Rgn.Leitor.Book.Narrador, System.Generics.Defaults, DAO.Leitor.Book,
  Rgn.Leitor.Book.Vozes;

type
  IRgnLeitorBook = interface
    ['{7CE41228-2682-49C9-A436-209B66DFB41B}']
    procedure ProcessarBook(const ALivroPDF: String);
  end;

  TRgnLeitorBook = class(TInterfacedPersistent, IRgnLeitorBook)
  private
    oLivro: TLivro;
    oIRgnLeitorPDF: IRgnLeitorPDF;
    oIRgnLeitorBookPersonagens: IRgnLeitorBookPersonagens;
    oIRgnLeitorBookNarrador: IRgnLeitorBookNarrador;
    oIRgnLeitorBookVozes: IRgnLeitorBookVozes;
    oIDAOLeitorBook: IDAOLeitorBook;
  public
    constructor Create;
    function Ref: IRgnLeitorBook;
    destructor Destroy; override;
    procedure ProcessarBook(const ALivroPDF: String);
  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, Rgn.Leitor.IA.Http, Winapi.Windows, Helper.HString;



constructor TRgnLeitorBook.Create;
begin
  oLivro                     := TLivro.Create;
  oIRgnLeitorPDF             := TRgnLeitorPDF.Create;
  oIRgnLeitorBookPersonagens := TRgnLeitorBookPersonagens.Create;
  oIRgnLeitorBookNarrador    := TRgnLeitorBookNarrador.Create;
  oIRgnLeitorBookVozes       := TRgnLeitorBookVozes.Create;
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
      if (THlpString.RemoverCaracteresEspeciaisNaoASCII(sTexto.Trim) <> EmptyStr) and (not(THlpString.SomenteNumeros(THlpString.RemoverCaracteresEspeciaisNaoASCII(sTexto.Trim)))) then
      begin
        oLivro.Add(TPagina.Create);
        oLivro.Last.Numero := iNumero;
        oLivro.Last.Texto  := THlpString.RemoverCaracteresEspeciaisNaoASCII(sTexto.Trim);

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
    oIRgnLeitorBookVozes.ObterVozes(oLivro);
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

end.

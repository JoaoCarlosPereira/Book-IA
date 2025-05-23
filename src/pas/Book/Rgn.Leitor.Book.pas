unit Rgn.Leitor.Book;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, OtlTask,
  Leitor.Book, Rgn.Leitor.PDF, Rgn.Leitor.Book.Personagens,
  Rgn.Leitor.Book.Narrador, System.Generics.Defaults;

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

    procedure OrdenarConteudo(const ALivro: TLivro);
    procedure ExportarLivro(const ALivro: TLivro);
  public
    constructor Create;
    destructor Destroy; override;
    procedure ProcessarBook(const ALivroPDF: String);
  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, Rgn.Leitor.IA.Http, SynCommons;



constructor TRgnLeitorBook.Create;
begin
  oLivro                     := TLivro.Create;
  oIRgnLeitorPDF             := TRgnLeitorPDF.Create;
  oIRgnLeitorBookPersonagens := TRgnLeitorBookPersonagens.Create;
  oIRgnLeitorBookNarrador    := TRgnLeitorBookNarrador.Create;
end;



procedure TRgnLeitorBook.ProcessarBook(const ALivroPDF: String);
var
  oPaginas: TStringList;
  sTexto: string;
begin
  oPaginas := oIRgnLeitorPDF.LerPDFPorPagina(ALivroPDF);
  try
    oLivro.Clear;
    for sTexto in oPaginas do
    begin
      if (sTexto.Trim <> EmptyStr) then
      begin
        oLivro.Add(TPagina.Create);
        oLivro.Last.Texto := sTexto.Trim;
      end;
    end;
    oIRgnLeitorBookPersonagens.ObterPersonagens(oLivro);
    oIRgnLeitorBookNarrador.ObterNarrador(oLivro);

    OrdenarConteudo(oLivro);
    ExportarLivro(oLivro);
  finally
    oPaginas.Free;
    TRgnLeitorIAHttp.Create.Ref.DescarregarModelo;
  end;
end;



destructor TRgnLeitorBook.Destroy;
begin
  oLivro.Free;
  inherited;
end;



procedure TRgnLeitorBook.ExportarLivro(const ALivro: TLivro);
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
  oListaPersonagensExportacao: TListaPersonagensFalas;
begin
  oListaPersonagensExportacao := TListaPersonagensFalas.Create(False);
  try
    for oPagina in ALivro do
    begin
      for oPersonagem in oPagina.ListaPersonagens do
      begin
        oListaPersonagensExportacao.Add(oPersonagem);
      end;
    end;

    with TStringList.Create do
    begin
      for oPagina in ALivro do
      begin
        for oPersonagem in oPagina.ListaPersonagens do
        begin
          Add(oPersonagem.nome + '|' + oPersonagem.genero + '|' + oPersonagem.fala);
        end;
      end;

      SaveToFile('../output/SequenciaLivro.txt', TEncoding.UTF8);
      Clear;
      Text := oListaPersonagensExportacao.ToJson;
      SaveToFile('../output/SequenciaLivro.json', TEncoding.UTF8);
      Free;
    end;
  finally
    oListaPersonagensExportacao.Free;
  end;
end;



procedure TRgnLeitorBook.OrdenarConteudo(const ALivro: TLivro);
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
  iPosBusca, iPosEncontrado: Integer;
begin
  iPosBusca := 1;

  for oPagina in ALivro do
  begin
    for oPersonagem in oPagina.ListaPersonagens do
    begin
      if oPersonagem.fala.Trim = '' then
      begin
        oPersonagem.Posicao := MaxInt;
        Continue;
      end;

      iPosEncontrado := PosEx(oPersonagem.fala, oPagina.Texto.Replace('\n', '').Replace('  ', ' '), 0);

      if (iPosEncontrado > 0) then
      begin
        oPersonagem.Posicao := iPosEncontrado;
      end
      else
        oPersonagem.Posicao := MaxInt;
    end;

    oPagina.ListaPersonagens.Sort(
      TComparer<TPersonagemFala>.Construct(
      function(const L, R: TPersonagemFala): Integer
      begin
        Result := 0;

        if (L.Posicao > R.Posicao) then
          Result := Succ(0)
        else if (L.Posicao < R.Posicao) then
          Result := Pred(0)
      end));
  end;

  // Tratar falas repetidas.

end;

end.

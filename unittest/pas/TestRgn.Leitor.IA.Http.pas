unit TestRgn.Leitor.IA.Http;

interface

uses
  TestFramework, Rgn.Leitor.IA.Http, Leitor.IA.Request;

type
  TestRgnLeitorIAHttp = class(TTestCase)
  private
    oRequestIA: TRequestIA;
  public
    procedure SetUp; override;
    procedure TearDown; override;
  published
    procedure TestConexaoComIA;
    procedure TestExtrairPersonagens;
  end;

implementation

uses
  System.SysUtils, Leitor.IA.Response, Rgn.Leitor.Book;



procedure TestRgnLeitorIAHttp.SetUp;
begin

  oRequestIA := TRequestIA.Create;
end;



procedure TestRgnLeitorIAHttp.TearDown;
begin
  oRequestIA.Free;
end;



procedure TestRgnLeitorIAHttp.TestConexaoComIA;
var
  sResponse: string;
  oIRgnLeitorIAHttp: IRgnLeitorIAHttp;
begin
  oIRgnLeitorIAHttp := TRgnLeitorIAHttp.Create(ttaLocal);
  sResponse         := oIRgnLeitorIAHttp.Generate(oRequestIA);
  CheckTrue(sResponse.ToLower.Contains('sim'), 'IA offline');
end;



procedure TestRgnLeitorIAHttp.TestExtrairPersonagens;
var
  oRgnLeitorBook: IRgnLeitorBook;
begin
  oRgnLeitorBook := TRgnLeitorBook.Create;
  oRgnLeitorBook.ProcessarBook('D:\dsv-git\dsv-delphi\Book-IA\unittest\input\O_Olho_do_Mundo_-_A_Roda_do_Tempo_-_Vol.__1__-_Robert_Jordan.pdf');
end;

initialization

RegisterTest('IA', TestRgnLeitorIAHttp.Suite);

end.

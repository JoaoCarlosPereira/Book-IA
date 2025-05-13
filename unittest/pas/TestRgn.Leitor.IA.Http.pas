unit TestRgn.Leitor.IA.Http;

interface

uses
  TestFramework, Rgn.Leitor.IA.Http, Leitor.IA.Request;

type
  TestRgnLeitorIAHttp = class(TTestCase)
  private
    oIRgnLeitorIAHttp: IRgnLeitorIAHttp;
    oRequestIA: TRequestIA;
  public
    procedure SetUp; override;
    procedure TearDown; override;
  published
    procedure TestConexaoComIA;
  end;

implementation

uses
  System.SysUtils, Leitor.IA.Response;



procedure TestRgnLeitorIAHttp.SetUp;
begin
  oIRgnLeitorIAHttp := TRgnLeitorIAHttp.Create;
  oRequestIA        := TRequestIA.Create;
end;



procedure TestRgnLeitorIAHttp.TearDown;
begin
  oRequestIA.Free;
end;



procedure TestRgnLeitorIAHttp.TestConexaoComIA;
var
  oRespostaIA: TResponse;
begin
  oRequestIA.model  := 'gemma3:27b';
  oRequestIA.prompt := 'IA está na escuta?';

  oRespostaIA := oIRgnLeitorIAHttp.Generate(oRequestIA);

  CheckTrue(oRespostaIA.Response.ToLower.Contains('sim'), 'IA Fora do ar.');
end;

initialization

RegisterTest('IA', TestRgnLeitorIAHttp.Suite);

end.

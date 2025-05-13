unit Rgn.Leitor.IA.Http;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, Rgn.Sistema.WebService.Rest,
  Leitor.IA.Request, Leitor.IA.Response;

type
  IRgnLeitorIAHttp = interface
    ['{A912C374-4F2E-4307-8215-8FB53D407551}']
    function Generate(const ARequestIA: TRequestIA): TResponse;
  end;

  TRgnLeitorIAHttp = class(TInterfacedPersistent, IRgnLeitorIAHttp)
  private
    oIWebService: IRgnSistemaWebServiceRest;
  public
    function Generate(const ARequestIA: TRequestIA): TResponse;
    constructor Create;
  end;

const
  URL_API = 'https://joaocarlosdev.duckdns.org';
  METODO_API = 'ollama/api/generate';
  PORTA_PADRAO = 443;
  BOLETO_TIMEOUT = 120000;
  TIPO_ENVIO_RETORNO = 'application/json';
  API_KEY = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImJmNTU0NjFlLThlM2QtNGYxNS1hYmY5LWM1OTNlODRiNzY2OSJ9.m-iD7Y6ceGG7xfL2FqvI77UYkDtU356B5_xkw-gSWYg';

implementation

uses
  Lib.RC.RestClient.Exception.Factory, Lib.Serialize.Enumerator;

{ TRgnLeitorIAHttp }



constructor TRgnLeitorIAHttp.Create;
begin
  oIWebService := TRgnSistemaWebServiceRest.Create.Ref;
  oIWebService.InicializarConexao(
    URL_API,
    PORTA_PADRAO,
    tNenhum,
    EmptyStr,
    EmptyStr,
    exAtualizacaoTributaria,
    BOLETO_TIMEOUT,
    EmptyStr,
    'application/x-www-form-urlencoded',
    TIPO_ENVIO_RETORNO,
    JSONSuperObject,
    False);

  oIWebService.AddHeadersToSend('Content-Type', TIPO_ENVIO_RETORNO);
  oIWebService.AddHeadersToSend('Authorization', API_KEY);
end;



function TRgnLeitorIAHttp.Generate(const ARequestIA: TRequestIA): TResponse;
begin
  Result := TResponse.Create;
  oIWebService.Post(METODO_API, ARequestIA.ToJson, Result, TResponse);
end;

end.

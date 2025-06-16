unit Rgn.Leitor.Book.VozesHttp;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, Rgn.Sistema.WebService.Rest,
  Leitor.IA.Request, Leitor.IA.Response, System.SyncObjs, Vcl.Forms,
  OtlTaskControl, OtlTask, Vcl.ExtCtrls;

type
  TTipoAPI = (
    ttaNenhum = 0,
    ttaOnline = 1,
    ttaLocal = 2);

  IRgnLeitorBookVozesHttp = interface
    ['{E94673D4-643D-49B5-8FA2-89D5EB966904}']
    function Gravar(const AVoz: TTTSVoice): Boolean;
    function Unificar(const AVoz: TTTSVoice): Boolean;
    function GerarTrilha(const ATrilha: TTrilha): Boolean;
  end;

  TRgnLeitorBookVozesHttp = class(TInterfacedPersistent, IRgnLeitorBookVozesHttp)
  private
    oIRgnSistemaWebServiceRest: IRgnSistemaWebServiceRest;
  public
    function Gravar(const AVoz: TTTSVoice): Boolean;
    function Unificar(const AVoz: TTTSVoice): Boolean;
    function GerarTrilha(const ATrilha: TTrilha): Boolean;
    function Ref: IRgnLeitorBookVozesHttp;
    constructor Create;
  end;

const
  URL_API_LOCAL = 'http://192.168.2.162';
  PORTA_PADRAO = 8001;
  QUINZE_MINUTOS = 900000;
  TIPO_ENVIO_RETORNO = 'application/json';

implementation

uses
  Lib.RC.RestClient.Exception.Factory, Lib.Serialize.Enumerator,
  Lib.RC.RestClient.HTTPClient.Enumerator, System.DateUtils,
  Rgn.Sistema.ThreadFactory;

{ TRgnLeitorIAHttp }



constructor TRgnLeitorBookVozesHttp.Create;
begin
  oIRgnSistemaWebServiceRest := TRgnSistemaWebServiceRest.Create(ctUseWinHTTP).Ref;
  oIRgnSistemaWebServiceRest.InicializarConexao(
    URL_API_LOCAL,
    PORTA_PADRAO,
    tNenhum,
    EmptyStr,
    EmptyStr,
    exAtualizacaoTributaria,
    QUINZE_MINUTOS,
    EmptyStr,
    TIPO_ENVIO_RETORNO,
    TIPO_ENVIO_RETORNO,
    JSONSuperObject,
    False);

end;



function TRgnLeitorBookVozesHttp.GerarTrilha(const ATrilha: TTrilha): Boolean;
var
  oVozResponse: TTTSVoiceRet;
begin
  oIRgnSistemaWebServiceRest.InicializarConexao(
    URL_API_LOCAL,
    8002,
    tNenhum,
    EmptyStr,
    EmptyStr,
    exAtualizacaoTributaria,
    QUINZE_MINUTOS,
    EmptyStr,
    TIPO_ENVIO_RETORNO,
    TIPO_ENVIO_RETORNO,
    JSONSuperObject,
    False);

  oVozResponse := TTTSVoiceRet.Create;
  Result       := False;
  try
    oIRgnSistemaWebServiceRest.Post('generate-from-text', ATrilha.ToJson, oVozResponse, TTTSVoiceRet);
    Result := oVozResponse.status.Equals('success');
  finally
    oVozResponse.Free;
  end;
end;



function TRgnLeitorBookVozesHttp.Gravar(const AVoz: TTTSVoice): Boolean;
var
  oVozResponse: TTTSVoiceRet;
begin
  oVozResponse := TTTSVoiceRet.Create;
  Result       := False;
  try
    oIRgnSistemaWebServiceRest.Post('generate-from-text', AVoz.ToJson, oVozResponse, TTTSVoiceRet);
    Result := oVozResponse.status.Equals('success');
  finally
    oVozResponse.Free;
  end;
end;



function TRgnLeitorBookVozesHttp.Ref: IRgnLeitorBookVozesHttp;
begin
  Result := Self;
end;



function TRgnLeitorBookVozesHttp.Unificar(const AVoz: TTTSVoice): Boolean;
var
  oVozResponse: TTTSVoiceRet;
begin
  oVozResponse := TTTSVoiceRet.Create;
  Result       := False;
  try
    oIRgnSistemaWebServiceRest.Post('merge-wavs', AVoz.ToJson, oVozResponse, TTTSVoiceRet);
    Result := oVozResponse.status.Equals('success');
  finally
    oVozResponse.Free;
  end;
end;

end.

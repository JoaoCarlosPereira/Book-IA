unit Rgn.Leitor.IA.Http;

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

  IRgnLeitorIAHttp = interface
    ['{A912C374-4F2E-4307-8215-8FB53D407551}']
    function Generate(const ARequestIA: TRequestIA): string;
    function Disponivel: Boolean;
    function GetTipo: TTipoAPI;
    function Expirada: Boolean;
    function GetKey: String;
  end;

  TRgnLeitorIAHttp = class(TInterfacedPersistent, IRgnLeitorIAHttp)
  private
    TimeOut: IOmniTaskControl;
    oTipoAPI: TTipoAPI;
    MetodoAPI: String;
    APIKey: String;
    Expirado: Boolean;
    FRequisicoes: Integer;
    oIRgnSistemaWebServiceRest: IRgnSistemaWebServiceRest;
    procedure DescarregarModelo;
    procedure Resetar(const ATask: IOmniTask);
  public
    constructor Create(const ATipoAPI: TTipoAPI; const AKeyAPI: String = '');
    destructor Destroy; override;

    function Generate(const ARequestIA: TRequestIA): string;
    function Ref: IRgnLeitorIAHttp;
    function Disponivel: Boolean;
    function GetTipo: TTipoAPI;
    function Expirada: Boolean;
    function GetKey: String;
  end;

  TListaAPI = TList<IRgnLeitorIAHttp>;

const
  URL_API_LOCAL = 'http://192.168.2.162';
  URL_API_ONLINE = 'https://generativelanguage.googleapis.com';
  PORTA_PADRAO = 11434;
  QUINZE_MINUTOS = 900000;
  TIPO_ENVIO_RETORNO = 'application/json';
  UM_MINUTO = 60000;
  UM_DIA = 90000000;
  UM_SEGUNDO = 1000;
  DEZ_SEGUNDOS = 10000;

implementation

uses
  Lib.RC.RestClient.Exception.Factory, Lib.Serialize.Enumerator,
  Lib.RC.RestClient.HTTPClient.Enumerator, System.DateUtils,
  Rgn.Sistema.ThreadFactory;

{ TRgnLeitorIAHttp }



constructor TRgnLeitorIAHttp.Create(const ATipoAPI: TTipoAPI; const AKeyAPI: String = '');
var
  oResponse: TResponseLocal;
begin
  oTipoAPI                   := ATipoAPI;
  APIKey                     := AKeyAPI;
  Expirado                   := False;
  oIRgnSistemaWebServiceRest := TRgnSistemaWebServiceRest.Create(ctUseWinHTTP).Ref;
  TimeOut                    := TRgnSistemaThreadFactory.CriarTarefaParalela(Resetar, nil, nil, nil, False);

  case oTipoAPI of
    ttaLocal:
      begin
        MetodoAPI := 'api/chat';
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

        oResponse := TResponseLocal.Create;
        try
          oIRgnSistemaWebServiceRest.Post(MetodoAPI, '{"model":"gemma3:27b", "keep_alive": -1,"messages":[{"content":"Acorde.","role":"user"}]}', oResponse, TResponseLocal);
        finally
          oResponse.Free;
        end;
      end;

    ttaOnline:
      begin
        MetodoAPI := 'v1beta/models/gemini-2.0-flash:generateContent?key=' + APIKey;;
        oIRgnSistemaWebServiceRest.InicializarConexao(
          URL_API_ONLINE,
          443,
          tNenhum,
          EmptyStr,
          EmptyStr,
          exAtualizacaoTributaria,
          UM_MINUTO,
          EmptyStr,
          TIPO_ENVIO_RETORNO,
          TIPO_ENVIO_RETORNO,
          JSONSuperObject,
          False);
      end;
  end;
end;



procedure TRgnLeitorIAHttp.Resetar(const ATask: IOmniTask);
var
  oTimeOut: TThread;
begin
  Sleep(UM_MINUTO);
  TimeOut      := nil;
  TimeOut      := TRgnSistemaThreadFactory.CriarTarefaParalela(Resetar, nil, nil, nil, False);
  FRequisicoes := 0;
end;



function TRgnLeitorIAHttp.GetKey: String;
begin
  Result := APIKey;
end;



function TRgnLeitorIAHttp.GetTipo: TTipoAPI;
begin
  Result := oTipoAPI;
end;



function TRgnLeitorIAHttp.Generate(const ARequestIA: TRequestIA): string;
var
  oRequestOnline: TContentsWrapper;
  oResponseLocal: TResponseLocal;
  oResponseOnline: TResponseOnline;



begin
  Result := '';
  case oTipoAPI of
    ttaOnline:
      begin
        oRequestOnline  := TContentsWrapper.Create;
        oResponseOnline := TResponseOnline.Create;
        try
          oRequestOnline.contents.Add(TContentRequest.Create);
          oRequestOnline.contents.Last.parts.Add(TPartRequest.Create);
          oRequestOnline.contents.Last.parts.Last.text := ARequestIA.messages.First.content + '\n\n' + ARequestIA.messages.Last.content;

          oIRgnSistemaWebServiceRest.Post(MetodoAPI, oRequestOnline.ToJson, oResponseOnline, TResponseOnline);

          if (oResponseOnline.Response <> '') then
            Result := oResponseOnline.Response
          else if (oIRgnSistemaWebServiceRest.getRetorno.Contains('GenerateRequestsPerDayPerProjectPerModel-FreeTie')) then
          begin
            Expirado := True;
            Result   := '[change-connection]';
          end
          else
            Result := '[change-connection]';
        finally
          oRequestOnline.Free;
          oResponseOnline.Free;
        end;
      end;

    ttaLocal:
      begin
        oResponseLocal := TResponseLocal.Create;
        try
          oIRgnSistemaWebServiceRest.Post(MetodoAPI, ARequestIA.ToJson, oResponseLocal, TResponseLocal);
          Result := oResponseLocal.Response;
        finally
          oResponseLocal.Free;
        end;
      end;
  end;

end;



procedure TRgnLeitorIAHttp.DescarregarModelo;
var
  oResponse: TResponseLocal;
begin
  oResponse := TResponseLocal.Create;
  try
    case oTipoAPI of
      ttaLocal:
        begin
          oIRgnSistemaWebServiceRest.Post(MetodoAPI, '{"model": "gemma3:27b", "keep_alive": 0}', oResponse, TResponseLocal);
        end;
    end;
  finally
    oResponse.Free;
  end;
end;



destructor TRgnLeitorIAHttp.Destroy;
begin
  case oTipoAPI of
    ttaLocal:
      begin
        DescarregarModelo;
      end;
  end;

  TimeOut := nil;
  inherited;
end;



function TRgnLeitorIAHttp.Disponivel: Boolean;
begin
  Result := False;

  if (oTipoAPI = ttaLocal) then
    Exit(True);

  if (FRequisicoes <= 14) then
  begin
    Inc(FRequisicoes);
    Exit(True);
  end
  else if (Assigned(TimeOut)) and (not(TimeOut.CancellationToken.IsSignalled)) then
  begin
    TimeOut.CancellationToken.Signal;
    TimeOut.Run
  end;
end;



function TRgnLeitorIAHttp.Expirada: Boolean;
begin
  Result := Expirado;
end;



function TRgnLeitorIAHttp.Ref: IRgnLeitorIAHttp;
begin
  Result := Self;
end;

end.

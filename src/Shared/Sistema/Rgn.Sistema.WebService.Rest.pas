unit Rgn.Sistema.WebService.Rest;

interface

uses
  SynCommons, Lib.RC.RestClient.Base, Lib.RC.IRestClient, Lib.RC.RestClient.IAuthorize,
  OtlTaskControl, OtlSync, SynCrtSock, Lib.Serialize.Enumerator, Lib.RC.RestClient.Exception.Factory;

type
  /// <summary>
  /// Assinatura da função de autenticação
  /// </summary>
  TFunctionAuth = reference to function(const ARestClient: IRestClient; out AOutputStr: RawByteString): Boolean;

  TAuthorizationType = (tNenhum, tToken, tBasic);

  /// <summary>
  /// Assinatura da função de atualização do ticket de acesso
  /// </summary>
  TFunctionKeepAliveTicket = reference to function(const ARestClient: IRestClient;
    out AOutputStr: RawByteString): Boolean;

  IRgnSistemaWebServiceRest = interface(IRestClient)
    ['{485DE95B-9415-4764-AA03-B72D62565B5F}']
    /// <summary>
    /// Método para criar uma conexão com o servidor  e utiliza-la
    /// Caso o tipo de autenticação for token, simplesmente passa-lo como String
    /// Se for basic Concatenar Usuario:Senha em Base 64
    /// </summary>
    function InicializarConexao(
      const AServidor: String;
      const APorta: integer;
      const ATipoAutenticacao: TAuthorizationType;
      const AAuthorization: string = '';
      const ASalvarJsonEm: String = '';
      const ATipoExcecao: TRCExceptionFactory.TExceptionType = exSysmoS1Server;
      const ATimeOut: integer = 10000;
      const ARootURI: string = '';
      const ATipoEnvio: string = 'application/json';
      const ATipoRetorno: string = 'application/xml';
      const ATipoSerializacao: TSerializeType = JSONSuperObject;
      const AInicializarImediatamente: Boolean = True
      ): IRestClient;
    function getSerializado: String;
    function getRetorno: String;

    function Post(const AAction: RawUTF8; const ARequestDto: TObject; out AResponseDto; const AClassNameResponseDto: TClass = nil; const AAditionalHeaders: RawUTF8 = ''): Boolean; overload;
    function Post(const AAction: RawUTF8; const ARequestDto: String; out AResponseDto; const AClassNameResponseDto: TClass = nil; const AAditionalHeaders: RawUTF8 = ''): Boolean; overload;
    procedure AddHeadersToSend(const AKey: String; const AValue: String = ''); overload;
    procedure ClientInitialize;
  end;

  TRgnSistemaWebServiceRest = class(TRestClientBase, IRgnSistemaWebServiceRest, IRestClient)
  private
    FWakeUpTicket: IOmniTaskControl;

    FAuthorized: Boolean;
    FAuth: TFunctionAuth;
    FAuthIsDefined: Boolean;
    FStatus: integer;

    /// <summary>
    /// Códigos de erros conhecidos de autenticação, esses códigos informados
    /// resultarão em uma nova chamada para autenticação e um novo request para o
    /// serviço, algo como um " Tentar Novamente "
    /// </summary>
    FRecognizedErrorAuth: array of String;

    FKeepAliveTicket: TFunctionKeepAliveTicket;
    FKeepAliveTicketIsDefined: Boolean;
    FAliveTicketTimeout: integer;
    SalvarJsons: string;
    sObjetoSerializado: string;
    sRetorno: string;
  private
    procedure SetAuth(const AValue: TFunctionAuth);
    procedure SetKeepAliveTicket(const AValue: TFunctionKeepAliveTicket);
    procedure DoKeepAliveTicket();
    procedure DoAuth();
  public
    function Ref: IRgnSistemaWebServiceRest;
    /// <summary>
    /// Método para criar uma conexão com o servidor  e utiliza-la
    /// Caso o tipo de autenticação for token, simplesmente passa-lo como String
    /// Se for basic Concatenar Usuario:Senha em Base 64
    /// </summary>
    function InicializarConexao(
      const AServidor: String;
      const APorta: integer;
      const ATipoAutenticacao: TAuthorizationType;
      const AAuthorization: string = '';
      const ASalvarJsonEm: String = '';
      const ATipoExcecao: TRCExceptionFactory.TExceptionType = exSysmoS1Server;
      const ATimeOut: integer = 10000;
      const ARootURI: string = '';
      const ATipoEnvio: string = 'application/json';
      const ATipoRetorno: string = 'application/xml';
      const ATipoSerializacao: TSerializeType = JSONSuperObject;
      const AInicializarImediatamente: Boolean = True
      ): IRestClient;
    function getSerializado: String;
    function getRetorno: String;
    /// <summary>
    /// Método para autenticação de acesso
    /// </summary>
    property Auth: TFunctionAuth read FAuth write SetAuth;

    /// <summary>
    /// A cada quanto tempo o ticket será reativado
    /// </summary>
    property AliveTicketTimeout: integer read FAliveTicketTimeout write FAliveTicketTimeout;

    /// <summary>
    /// Método para atualização do ticket de acesso
    /// </summary>
    property KeepAliveTicket: TFunctionKeepAliveTicket read FKeepAliveTicket write SetKeepAliveTicket;

    /// <summary>
    /// Status do request
    /// </summary>
    property Status: integer read FStatus write FStatus;
  public
    /// <summary>
    /// Códigos de erros conhecidos de autenticação, esses códigos informados
    /// resultarão em uma nova chamada para autenticação e um novo request para o
    /// serviço, algo como um " Tentar Novamente "
    /// </summary
    function SetRecognizedErrorAuth(const ARecognizedError: array of String): integer;
  public
    destructor Destroy; override;

    /// <summary>
    /// Inicializa os objetos necessários para a comunicação.
    /// Este método deve ser chamado antes de um POST, GET, PUT ou DELETE
    /// </summary>
    procedure ClientInitialize; override;

    /// <summary>
    /// Realiza a chamada de uma url utilizando metodo GET
    /// </summary>
    /// <param name="AAction">
    /// Action que será requisitada
    /// </param>
    /// <param name="ARequestDto">
    /// Objeto DTO que será enviado para o serviço
    /// </param>
    /// <param name="AResponseDto">
    /// Objeto DTO que será populado com os valores retornados do serviço
    /// </param>
    /// <param name="AClassName">
    /// Tipo da classe de AResponseDto
    /// </param>
    /// <param name="AAditionalHeaders">
    /// Cabeçalhos adicionais que podem ser enviados a cada requisição
    /// </param>
    function Get(const AAction: RawUTF8; const ARequestDto: TObject; out AResponseDto;
      const AClassNameResponseDto: TClass = nil; const AAditionalHeaders: RawUTF8 = ''): Boolean;

    /// <summary>
    /// Realiza a chamada de uma url utilizando metodo POST
    /// </summary>
    /// <param name="AAction">
    /// Action que será requisitada
    /// </param>
    /// <param name="ARequestDto">
    /// Objeto DTO que será enviado para o serviço
    /// </param>
    /// <param name="AResponseDto">
    /// Objeto DTO que será populado com os valores retornados do serviço
    /// </param>
    /// <param name="AClassName">
    /// Tipo da classe de AResponseDto
    /// </param>
    /// <param name="AAditionalHeaders">
    /// Cabeçalhos adicionais que podem ser enviados a cada requisição
    /// </param>
    function Post(const AAction: RawUTF8; const ARequestDto: TObject; out AResponseDto;
      const AClassNameResponseDto: TClass = nil; const AAditionalHeaders: RawUTF8 = ''): Boolean; overload;

    function Post(const AAction: RawUTF8; const ARequestDto: String; out AResponseDto;
      const AClassNameResponseDto: TClass = nil; const AAditionalHeaders: RawUTF8 = ''): Boolean; overload;

    /// <summary>
    /// Realiza a chamada de uma url utilizando metodo PUT
    /// </summary>
    /// <param name="AAction">
    /// Action que será requisitada
    /// </param>
    /// <param name="ARequestDto">
    /// Objeto DTO que será enviado para o serviço
    /// </param>
    /// <param name="AResponseDto">
    /// Objeto DTO que será populado com os valores retornados do serviço
    /// </param>
    /// <param name="AClassName">
    /// Tipo da classe de AResponseDto
    /// </param>
    /// <param name="AAditionalHeaders">
    /// Cabeçalhos adicionais que podem ser enviados a cada requisição
    /// </param>
    function Put(const AAction: RawUTF8; const ARequestDto: TObject; out AResponseDto;
      const AClassNameResponseDto: TClass = nil; const AAditionalHeaders: RawUTF8 = ''): Boolean;

    /// <summary>
    /// Realiza a chamada de uma url utilizando metodo PATCH
    /// </summary>
    /// <param name="AAction">
    /// Action que será requisitada
    /// </param>
    /// <param name="ARequestDto">
    /// Objeto DTO que será enviado para o serviço
    /// </param>
    /// <param name="AResponseDto">
    /// Objeto DTO que será populado com os valores retornados do serviço
    /// </param>
    /// <param name="AClassName">
    /// Tipo da classe de AResponseDto
    /// </param>
    /// <param name="AAditionalHeaders">
    /// Cabeçalhos adicionais que podem ser enviados a cada requisição
    /// </param>
    function Patch(const AAction: RawUTF8; const ARequestDto: TObject; out AResponseDto;
      const AClassNameResponseDto: TClass = nil; const AAditionalHeaders: RawUTF8 = ''): Boolean;

    /// <summary>
    /// Realiza a chamada de uma url utilizando metodo DELETE
    /// </summary>
    /// <param name="AAction">
    /// Action que será requisitada
    /// </param>
    /// <param name="ARequestDto">
    /// Objeto DTO que será enviado para o serviço
    /// </param>
    /// <param name="AResponseDto">
    /// Objeto DTO que será populado com os valores retornados do serviço
    /// </param>
    /// <param name="AClassName">
    /// Tipo da classe de AResponseDto
    /// </param>
    /// <param name="AAditionalHeaders">
    /// Cabeçalhos adicionais que podem ser enviados a cada requisição
    /// </param>
    function Delete(const AAction: RawUTF8; const ARequestDto: TObject; out AResponseDto;
      const AClassNameResponseDto: TClass = nil; const AAditionalHeaders: RawUTF8 = ''): Boolean;
  end;

implementation

uses
  System.SysUtils,
  System.StrUtils,
  Lib.RC.RestClient.Response,
  Lib.Serialize.Factory,
  Lib.RC.RestClient.Exception.Base,
  System.Variants,
  OtlTask,
  Vcl.Dialogs,
  OtlComm,
  Helper.HMediaType,
  SynZip,
  Lib.RC.RestClient.Exception.SysmoS1Server,
  System.Classes,
  Log4D, Helper.HNumeric;

const
  LOG4D_CATEGORY = 'RestClientSysmoS1Server';

  { TRCSysmoS1Server }



procedure TRgnSistemaWebServiceRest.DoAuth;
var
  sSendHeader: RawByteString;
begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.DoAuth');

  if not(FAuthIsDefined) then
  begin
    FAuthorized := True;
    exit;
  end;

  FAuthorized := Auth(Self, sSendHeader);

  if (FAuthorized) then
    Self.AddHeadersToSend(sSendHeader);
  // else
  // raise EExceptionSysmoS1Server.Create('Erro de autenticação. ' + #10 + Self.ExceptionObj.mensagem);

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.DoAuth');
end;



procedure TRgnSistemaWebServiceRest.ClientInitialize;
begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.ClientInitialize');

  inherited ClientInitialize;

  if (FKeepAliveTicketIsDefined) then
    DoKeepAliveTicket;

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.ClientInitialize');
end;



function TRgnSistemaWebServiceRest.Delete(const AAction: RawUTF8; const ARequestDto: TObject; out AResponseDto; const AClassNameResponseDto: TClass;
  const AAditionalHeaders: RawUTF8): Boolean;

  procedure DoDelete(const ARequestDto: TObject; var AResponseDto; const AAditionalHeaders: RawUTF8; var Result: Boolean; const AAction: RawUTF8);
  var
    sObjSerialized: RawByteString;
    oResponse: TRCResponse;
    sResponse: RawByteString;
  begin
    Result := False;

    oResponse := TRCResponse.Create(Self.SerializeType);
    try
      if Assigned(ARequestDto) then
        Result := TSerializeFactory.GetInstance(Self.SerializeType).Serialize(ARequestDto, sObjSerialized)
      else
        Result := True;

      if Result then
      begin
        Status := Self.request(methodDelete, AAction, sObjSerialized, AAditionalHeaders, sResponse);

        if (TObject(AResponseDto) <> nil) then
          Result := oResponse.GetResponse(AResponseDto, Self.ExceptionObj, Status, sResponse)
        else
        begin
          Result                      := Status = 200;
          RawByteString(AResponseDto) := sResponse;
        end;
      end;
    finally
      FreeAndNil(oResponse);
    end;
  end;



begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.Delete');

  Result := False;
  Status := 0;

  DoDelete(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);

  if (not(Result)) then
  begin
    if (MatchStr(Self.ExceptionObj.codigo, FRecognizedErrorAuth)) then
    begin
      DoAuth;
      DoDelete(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);
    end;
  end;

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.Delete');
end;



destructor TRgnSistemaWebServiceRest.Destroy;
begin
  { TODO : o tempo definido para atualização do ticket será o tempo que irá levar para terminar a tarefa ao fechar a aplicação }
  // oLoginDTO := nil; // nao dar freeandnil pois não é criado nessa classe.
  if (FWakeUpTicket <> nil) then
    FWakeUpTicket.Terminate(2000);

  inherited;
end;



function TRgnSistemaWebServiceRest.Put(const AAction: RawUTF8; const ARequestDto: TObject; out AResponseDto; const AClassNameResponseDto: TClass;
  const AAditionalHeaders: RawUTF8): Boolean;

  procedure DoPut(const ARequestDto: TObject; var AResponseDto; const AAditionalHeaders: RawUTF8; var Result: Boolean; const AAction: RawUTF8);
  var
    sObjSerialized: RawByteString;
    oResponse: TRCResponse;
    sResponse: RawByteString;
  begin
    Result := False;

    oResponse := TRCResponse.Create(Self.SerializeType);
    try
      if Assigned(ARequestDto) then
        Result := TSerializeFactory.GetInstance(Self.SerializeType).Serialize(ARequestDto, sObjSerialized)
      else
        Result := True;

      if Result then
      begin
        Status := Self.request(methodPut, AAction, sObjSerialized, AAditionalHeaders, sResponse);

        if (TObject(AResponseDto) <> nil) then
          Result := oResponse.GetResponse(AResponseDto, Self.ExceptionObj, Status, sResponse)
        else
        begin
          Result                      := Status = 200;
          RawByteString(AResponseDto) := sResponse;
        end;
      end;
    finally
      FreeAndNil(oResponse);
    end;
  end;



begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.Put');

  Result := False;
  Status := 0;

  DoPut(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);

  if (not(Result)) then
  begin
    if (MatchStr(Self.ExceptionObj.codigo, FRecognizedErrorAuth)) then
    begin
      DoAuth;
      DoPut(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);
    end;
  end;

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.Put');
end;



function TRgnSistemaWebServiceRest.Ref: IRgnSistemaWebServiceRest;
begin
  Result := Self;
end;



function TRgnSistemaWebServiceRest.Patch(const AAction: RawUTF8; const ARequestDto: TObject; out AResponseDto; const AClassNameResponseDto: TClass;
  const AAditionalHeaders: RawUTF8): Boolean;

  procedure DoPatch(const ARequestDto: TObject; var AResponseDto; const AAditionalHeaders: RawUTF8; var Result: Boolean; const AAction: RawUTF8);
  var
    sObjSerialized: RawByteString;
    oResponse: TRCResponse;
    sResponse: RawByteString;
  begin
    Result := False;

    oResponse := TRCResponse.Create(Self.SerializeType);
    try
      if Assigned(ARequestDto) then
        Result := TSerializeFactory.GetInstance(Self.SerializeType).Serialize(ARequestDto, sObjSerialized)
      else
        Result := True;

      if Result then
      begin
        Status := Self.request(methodPatch, AAction, sObjSerialized, AAditionalHeaders, sResponse);

        if (TObject(AResponseDto) <> nil) then
          Result := oResponse.GetResponse(AResponseDto, Self.ExceptionObj, Status, sResponse)
        else
        begin
          Result                      := Status = 200;
          RawByteString(AResponseDto) := sResponse;
        end;
      end;
    finally
      FreeAndNil(oResponse);
    end;
  end;



begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.Path');

  Result := False;
  Status := 0;

  DoPatch(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);

  if (not(Result)) then
  begin
    if (MatchStr(Self.ExceptionObj.codigo, FRecognizedErrorAuth)) then
    begin
      DoAuth;
      DoPatch(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);
    end;
  end;

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.Path');
end;



procedure TRgnSistemaWebServiceRest.DoKeepAliveTicket;
begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.DoKeepAliveTicket');

  // para executar esse método o keepAlive deve ser maior que 1segundo
  if (Self.FAliveTicketTimeout < 1000) then
    exit;

  FWakeUpTicket := CreateTask(
    procedure(const task: IOmniTask)
    var
      sOutoutStr: RawByteString;
    begin
      while not(task.Terminated) do
      begin
        sleep(Self.FAliveTicketTimeout);
        Self.KeepAliveTicket(Self, sOutoutStr);
      end;
    end)
    .Run;

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.DoKeepAliveTicket');
end;



procedure TRgnSistemaWebServiceRest.SetAuth(const AValue: TFunctionAuth);
begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.SetAuth');

  FAuth          := AValue;
  FAuthIsDefined := True;

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.SetAuth');
end;



procedure TRgnSistemaWebServiceRest.SetKeepAliveTicket(const AValue: TFunctionKeepAliveTicket);
begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.SetKeepAliveTicket');

  FKeepAliveTicket          := AValue;
  FKeepAliveTicketIsDefined := True;

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.SetKeepAliveTicket');
end;



function TRgnSistemaWebServiceRest.SetRecognizedErrorAuth(const ARecognizedError: array of String): integer;
var
  iCont: integer;
begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.SetRecognizedErrorAuth');

  Result := Length(ARecognizedError);
  SetLength(FRecognizedErrorAuth, Result);

  for iCont                     := 0 to Result - 1 do
    FRecognizedErrorAuth[iCont] := ARecognizedError[iCont];

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.SetRecognizedErrorAuth');
end;



function TRgnSistemaWebServiceRest.Get(const AAction: RawUTF8; const ARequestDto: TObject;
out AResponseDto; const AClassNameResponseDto: TClass; const AAditionalHeaders: RawUTF8): Boolean;

  procedure DoGet(const ARequestDto: TObject; var AResponseDto; const AAditionalHeaders: RawUTF8; var Result: Boolean;
  const AAction: RawUTF8);
  var
    sObjSerialized: RawByteString;
    oResponse: TRCResponse;
    sResponse: RawByteString;
  begin
    Result := False;

    oResponse := TRCResponse.Create(Self.SerializeType);
    try
      Result := TSerializeFactory.GetInstance(Self.SerializeType).Serialize(ARequestDto, sObjSerialized);
      if Result then
      begin
        Status := Self.request(methodGet, AAction, sObjSerialized, AAditionalHeaders, sResponse);
        if (TObject(AResponseDto) <> nil) then
          Result := oResponse.GetResponse(AResponseDto, Self.ExceptionObj, Status, sResponse)
        else
        begin
          Result                      := Status = 200;
          RawByteString(AResponseDto) := sResponse;
        end;
      end;
    finally
      FreeAndNil(oResponse);
    end;
  end;



begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.Get');

  Result := False;
  Status := 0;

  DoGet(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);

  if (not(Result)) then
  begin
    if (MatchStr(Self.ExceptionObj.codigo, FRecognizedErrorAuth)) then
    begin
      DoAuth;
      DoGet(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);
    end;
  end;

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.Get');
end;



function TRgnSistemaWebServiceRest.InicializarConexao(const AServidor: String; const APorta: integer; const ATipoAutenticacao: TAuthorizationType; const AAuthorization: string; const ASalvarJsonEm: String; const ATipoExcecao: TRCExceptionFactory.TExceptionType;
const ATimeOut: integer; const ARootURI, ATipoEnvio, ATipoRetorno: string; const ATipoSerializacao: TSerializeType; const AInicializarImediatamente: Boolean): IRestClient;

  function GetAuthorizationLine: String;
  begin
    case (ATipoAutenticacao) of
      tToken:
        begin
          Result := 'Bearer ' + AAuthorization;
        end;

      tBasic:
        begin
          Result := 'Basic ' + AAuthorization;
        end;
    end;
  end;



begin
  Result                := Self;
  Self.Server           := AServidor;
  Self.Port             := APorta;
  Self.RootURI          := ARootURI;
  Self.Compression      := CompressDeflate;
  Self.SendMediaType    := ATipoEnvio;
  Self.ReceiveMediaType := ATipoRetorno;
  Self.TimeOut          := ATimeOut;
  Self.SerializeType    := ATipoSerializacao;
  Self.ExceptionObj     := TRCExceptionFactory.GetInstance(ATipoExcecao);
  if (ATipoAutenticacao <> tNenhum) then
    Self.AddHeadersToSend('Authorization', GetAuthorizationLine);

  if (AInicializarImediatamente) then
    Self.ClientInitialize();

  SalvarJsons := ASalvarJsonEm;
end;



function TRgnSistemaWebServiceRest.getRetorno: String;
begin
  Result := sRetorno;
end;



function TRgnSistemaWebServiceRest.getSerializado: String;
begin
  Result := sObjetoSerializado;
end;



function TRgnSistemaWebServiceRest.Post(const AAction: RawUTF8; const ARequestDto: TObject; out AResponseDto;
const AClassNameResponseDto: TClass; const AAditionalHeaders: RawUTF8): Boolean;

  procedure DoPost(const ARequestDto: TObject; var AResponseDto; const AAditionalHeaders: RawUTF8; var Result: Boolean;
  const AAction: RawUTF8);
  var
    sObjSerialized: RawByteString;
    oResponse: TRCResponse;
    sResponse: RawByteString;
    oJson: TStringList;
  begin
    Result := False;

    oResponse := TRCResponse.Create(Self.SerializeType);
    try
      if Assigned(ARequestDto) then
        Result := TSerializeFactory.GetInstance(Self.SerializeType).Serialize(ARequestDto, sObjSerialized)
      else
        Result := True;

      sObjetoSerializado := UTF8ToString(sObjSerialized);

      if (SalvarJsons <> '') and (sObjSerialized <> '') then
      begin
        oJson := TStringList.Create;
        try
          oJson.Text := UTF8ToString(sObjSerialized);
          if (SalvarJsons.Contains('%s')) then
            oJson.SaveToFile(Format(SalvarJsons, [FormatDateTime('dd_mm_yyyy_hh_nn_ss_zzz', Now) + '_' + GetNumeroRandomico]))
          else
            oJson.SaveToFile(SalvarJsons);
        finally
          FreeAndNil(oJson);
        end;
      end;

      if Result then
      begin
        Status := Self.request(methodPost, AAction, sObjSerialized, AAditionalHeaders, sResponse);

        sRetorno := UTF8ToString(sResponse);

        if (TObject(AResponseDto) <> nil) then
        begin
          Result   := oResponse.GetResponse(AResponseDto, Self.ExceptionObj, Status, sResponse);
          sRetorno := UTF8ToString(sResponse);
          if (sResponse = '') then
            sRetorno := Self.ExceptionObj.codigo + ' - ' + Self.ExceptionObj.mensagem;
        end
        else
        begin
          Result := Status = 200;
        end;
      end;
    finally
      FreeAndNil(oResponse);
    end;
  end;



begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.Post');

  Result := False;
  Status := 0;

  DoPost(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);

  if (not(Result)) then
  begin
    if (MatchStr(Self.ExceptionObj.codigo, FRecognizedErrorAuth)) then
    begin
      DoAuth;
      DoPost(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);
    end;
  end;

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.Post');
end;



function TRgnSistemaWebServiceRest.Post(const AAction: RawUTF8; const ARequestDto: String; out AResponseDto; const AClassNameResponseDto: TClass; const AAditionalHeaders: RawUTF8): Boolean;

  procedure DoPost(const ARequestDto: String; var AResponseDto; const AAditionalHeaders: RawUTF8; var Result: Boolean; const AAction: RawUTF8);
  var
    oResponse: TRCResponse;
    sResponse: RawByteString;
    oJson: TStringList;
  begin
    Result    := True;
    oResponse := TRCResponse.Create(Self.SerializeType);
    try
      Status := Self.request(methodPost, AAction, StringToUTF8(ARequestDto), AAditionalHeaders, sResponse);

      if (sResponse <> '') then
        TSerializeFactory.GetInstance(Self.SerializeType).Unserialize(sResponse, AResponseDto, TObject(AResponseDto).ClassType);

      if (SalvarJsons <> '') and (ARequestDto <> '') then
      begin
        oJson := TStringList.Create;
        try
          oJson.Text := ARequestDto;
          if (SalvarJsons.Contains('%s')) then
            oJson.SaveToFile(Format(SalvarJsons, [FormatDateTime('dd_mm_yyyy_hh_nn_ss_zzz', Now) + '_' + GetNumeroRandomico]))
          else
            oJson.SaveToFile(SalvarJsons);
        finally
          FreeAndNil(oJson);
        end;
      end;

      if (TObject(AResponseDto) <> nil) then
      begin
        Result   := oResponse.GetResponse(AResponseDto, Self.ExceptionObj, Status, sResponse);
        sRetorno := UTF8ToString(sResponse);
        if (sResponse = '') then
          sRetorno := Self.ExceptionObj.codigo + ' - ' + Self.ExceptionObj.mensagem;
      end
      else
      begin
        Result := Status = 200;
      end;
    finally
      FreeAndNil(oResponse);
    end;
  end;



begin
  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Enter: ' + Self.ClassName + '.Post');

  Result := False;
  Status := 0;

  DoPost(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);

  if (not(Result)) then
  begin
    if (MatchStr(Self.ExceptionObj.codigo, FRecognizedErrorAuth)) then
    begin
      DoAuth;
      DoPost(ARequestDto, AResponseDto, AAditionalHeaders, Result, AAction);
    end;
  end;

  TLogLogger.GetLogger(LOG4D_CATEGORY).Trace('Leave: ' + Self.ClassName + '.Post');
end;

end.

unit Rgn.Sistema.ThreadUtils;

interface

uses
  System.Classes, Math, SysmoSQL, System.Generics.Collections,
  System.SyncObjs, OtlTask, OtlCommon;

type
  TRgnSistemaThreadUtils = class
  strict protected
    class function QuantidadeTasks(const AQuantidadeSolicitada: integer): integer;
  public
    class procedure MostrarSplash(const AOwner: TObject; const AMensagem: String = ''; const AMetodoCancelarProcessoThread: TNotifyEvent = nil);
    class procedure EsconderSplash(const AOwner: TObject);
    class function CriarNovaConexao(const ACriarComFetchAllAtivo: Boolean = False): TPSQLConnection;

    class procedure IniciarPacoteConexoes(const AQuantiadeConexoes, AIdentificadorProcesso: integer);
    class function ObterConexaoLivre(const AIdentificadorProcesso: integer): TPSQLConnection;
    class procedure LiberarConexaoParaUso(const AConexao: TPSQLConnection);
    class procedure DestruirPacoteConexoes(const AIdentificadorProcesso: integer);
    class function GetNumeroThreadAtual(const ATask: IOmniTask): integer;
    class function GetQuantidadeThreads(const ATask: IOmniTask): integer;
  end;

  TPSQLConnectionThread = class(TPSQLConnection)
  public
    EmUso: Boolean;
  end;

const
  INDICE_THREAD = 'INDICE_THREAD';
  TOTAL_THREAD = 'TOTAL_THREAD';

var
  oDicionarioConexoes: TObjectDictionary<integer, TObjectList<TPSQLConnectionThread>>;
  oCriticalSection: TCriticalSection;

implementation

uses
  System.SysUtils, Helper.HSQL;



class function TRgnSistemaThreadUtils.CriarNovaConexao(const ACriarComFetchAllAtivo: Boolean): TPSQLConnection;
begin
  if (ACriarComFetchAllAtivo) then
    CriarConexao(Result, Self.ClassName).Conectar(True)
  else
    CriarConexao(Result, Self.ClassName, [coFetchAllFalse]).Conectar(True);
end;



class procedure TRgnSistemaThreadUtils.EsconderSplash(const AOwner: TObject);
begin
  //
end;



class function TRgnSistemaThreadUtils.GetNumeroThreadAtual(const ATask: IOmniTask): integer;
begin
  Result := 0;
  if (ATask.Param.Exists(INDICE_THREAD)) then
    Result := TList<Int64>(ATask.Param.ByName(INDICE_THREAD).AsObject).Count;
end;



class function TRgnSistemaThreadUtils.GetQuantidadeThreads(const ATask: IOmniTask): integer;
begin
  Result := 0;
  if (ATask.Param.Exists(TOTAL_THREAD)) then
    Result := ATask.Param.ByName(TOTAL_THREAD).AsInteger
end;



class procedure TRgnSistemaThreadUtils.MostrarSplash(const AOwner: TObject; const AMensagem: String; const AMetodoCancelarProcessoThread: TNotifyEvent);
begin
  //
end;



class function TRgnSistemaThreadUtils.QuantidadeTasks(const AQuantidadeSolicitada: integer): integer;
begin
  Result := AQuantidadeSolicitada;
end;



class procedure TRgnSistemaThreadUtils.IniciarPacoteConexoes(const AQuantiadeConexoes, AIdentificadorProcesso: integer);
var
  iIndice: integer;
begin
  if (not(oDicionarioConexoes.ContainsKey(AIdentificadorProcesso))) then
    oDicionarioConexoes.Add(AIdentificadorProcesso, TObjectList<TPSQLConnectionThread>.Create);

  oDicionarioConexoes.Items[AIdentificadorProcesso].Clear;
  for iIndice := 1 to AQuantiadeConexoes do
  begin
    oDicionarioConexoes.Items[AIdentificadorProcesso].Add(TPSQLConnectionThread.Create(nil));
    oDicionarioConexoes.Items[AIdentificadorProcesso].Last.Conectar;
    oDicionarioConexoes.Items[AIdentificadorProcesso].Last.EmUso := False;
  end;
end;



class function TRgnSistemaThreadUtils.ObterConexaoLivre(const AIdentificadorProcesso: integer): TPSQLConnection;

  function GetConexaoLivre: TPSQLConnection;
  var
    oConexao: TPSQLConnectionThread;
  begin
    Result := nil;

    for oConexao in oDicionarioConexoes.Items[AIdentificadorProcesso] do
    begin
      if (not(oConexao.EmUso)) then
      begin
        oConexao.EmUso := True;
        Result := oConexao;
        Break;
      end;
    end;

    if (not(Assigned(Result))) then
      Result := GetConexaoLivre;
  end;


begin
  if (not(oDicionarioConexoes.ContainsKey(AIdentificadorProcesso))) then
    raise Exception.Create('Pacote de conexões não inicalizado para este identificador: ' + AIdentificadorProcesso.ToString);

  oCriticalSection.Enter;
  try
    Result := GetConexaoLivre;
  finally
    oCriticalSection.Release;
  end;
end;



class procedure TRgnSistemaThreadUtils.LiberarConexaoParaUso(const AConexao: TPSQLConnection);
begin
  if (AConexao is TPSQLConnectionThread) then
    TPSQLConnectionThread(AConexao).EmUso := False;
end;



class procedure TRgnSistemaThreadUtils.DestruirPacoteConexoes(const AIdentificadorProcesso: integer);
var
  oConexao: TPSQLConnectionThread;
begin
  if (not(oDicionarioConexoes.ContainsKey(AIdentificadorProcesso))) then
    raise Exception.Create('Pacote de conexões não inicalizado para este identificador: ' + AIdentificadorProcesso.ToString);

  for oConexao in oDicionarioConexoes.Items[AIdentificadorProcesso] do
  begin
    oConexao.Close;
  end;
  oDicionarioConexoes.Remove(AIdentificadorProcesso);
end;

initialization

oDicionarioConexoes := TObjectDictionary < integer, TObjectList < TPSQLConnectionThread >>.Create([doOwnsValues]);
oCriticalSection := TCriticalSection.Create;

finalization

oDicionarioConexoes.Free;
oCriticalSection.Free;

end.

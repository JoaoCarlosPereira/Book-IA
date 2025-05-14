unit Rgn.Sistema.ThreadFactory;

interface

uses
  OtlTaskControl, OtlTask, OtlComm, OtlSync, System.Generics.Collections, OtlCommon, System.Rtti,
  System.Classes, System.SysUtils, Winapi.Windows, otlparallel, Rgn.Sistema.ThreadUtils;

type
  TExceptionReturn = record
    EMessage: String;
    EStackTrace: String;
    EClassName: String;
    Return: String;
  end;

  TMetodoExecutarTask = reference to procedure(const ATask: IOmniTask);
  TMetodoExecutarLoopTask = reference to procedure(const ATask: IOmniTask; const AObjeto: TObject);
  TMetodoExibirMensagemTask = reference to procedure(const ATask: IOmniTaskControl; const Msg: TOmniMessage);
  TMetodoFinalizarTask = reference to procedure(const ATask: IOmniTaskControl);

  TMetodoExecutarThread = reference to procedure;
  TMetodoExecutarFinalizarThread = reference to procedure;
  TMetodoExecutarException = reference to procedure(AException: TExceptionReturn);

  TDadosThread = class
  public
    oITaskControl: IOmniTaskControl;
    oListaObjetos: TObjectList<TObject>;

    constructor Create;
    destructor Destroy; override;
  end;

  TDicionarioThread = class(TObjectDictionary<String, TDadosThread>)
  strict private
    oListaIndices: TList<String>;
  public
    procedure Add(const Key: String; const Value: TDadosThread);
    procedure Remove(const Key: String);
    procedure Clear;
    function GetIndex(const AKey: String): Integer;

    constructor Create(Ownerships: TDictionaryOwnerships); reintroduce;
    destructor Destroy; override;
  end;

  TRgnSistemaThreadFactory = class(TRgnSistemaThreadUtils)
  strict private
    class function GerarNomeThread: String;
    class function GetTokenCancelamentoThread(const ACancellationToken: IOmniCancellationToken): IOmniCancellationToken;
  public
    class function CriarTarefaParalela(
      AExecutarThread: TMetodoExecutarTask;
      AExibirMensagem: TMetodoExibirMensagemTask = nil;
      ACancelarThread: IOmniCancellationToken = nil;
      AFinalizarThread: TMetodoFinalizarTask = nil;
      const AIniciarImediatamente: Boolean = True): IOmniTaskControl;

    class function CriarTarefaParalelaComRaiseExcept(
      AExecutarThread: TMetodoExecutarTask;
      ACancelarThread: IOmniCancellationToken = nil;
      AFinalizarThread: TMetodoFinalizarTask = nil;
      const AIniciarImediatamente: Boolean = True): IOmniTaskControl;

    class procedure CriarThread(
      var AThread: TThread;
      const IniciarImediatamente: Boolean;
      const APermitirThreadsSimultaneas: Boolean;
      const AExecutarThread: TMetodoExecutarThread;
      AFinalizarThread: TMetodoExecutarFinalizarThread = nil;
      AException: TMetodoExecutarException = nil);

    class procedure CriarThreadNativa(
      var AThread: TThread;
      const IniciarImediatamente: Boolean;
      const APermitirThreadsSimultaneas: Boolean;
      const AExecutarThread: TMetodoExecutarThread;
      AFinalizarThread: TMetodoExecutarFinalizarThread = nil);

    class procedure CriarLoopTarefasParalelas(const AQuantidadeTasksSimultaneas: Integer; const AListaObjetos: TValue; const AMetodoExecutar: TMetodoExecutarLoopTask);

    { TODO: Metodos abaixam criam leak }
    class procedure CriarLoopTasksSimultaneas(const AQuantidadeTasksSimultaneas: Integer; const AListaObjetos: TValue; const AMetodoExecutar: TMetodoExecutarLoopTask; const ADispararExcecao: Boolean = False);
    class function CriarLoopTasks(const AQuantidadeTasksSimultaneas: Integer; const AListaObjetos: TValue; const AMetodoExecutar: TMetodoExecutarLoopTask): IOmniParallelLoop<Integer>;
  end;

const
  WM_MENSAGEMERRO = 0;
  WM_MENSAGEMPROCESS = 1;
  WM_MENSAGEMSUCESS = 2;
  WM_MENSAGEMWARNING = 3;
  WM_MENSAGEMREPORT = 4;
  WM_MENSAGEMDIALOG = 5;

  ERRO_DE_CONEXAO_TERMINADA: array of String = ['terminating connection due to administrator command', 'canceling statement due to user request'];
  OBJECTOPARAMETRO = 'ObjectoParametroThread';

implementation

uses
  Helper.HString, Math, Helper.HNumeric;



class procedure TRgnSistemaThreadFactory.CriarLoopTarefasParalelas(const AQuantidadeTasksSimultaneas: Integer; const AListaObjetos: TValue; const AMetodoExecutar: TMetodoExecutarLoopTask);
var
  oListaObjetosParametro: TValue;
  iQuantidadeTasksSimultaneas: Integer;
  oObjecto: TObject;
  oIOmniTaskControl: IOmniTaskControl;
  oListaTasks: TObjectDictionary<String, TObject>;
  oIOmniCancellationToken: IOmniCancellationToken;

  function PodeIniciarNovaThread: Boolean;
  begin
    Result := (not(oIOmniCancellationToken.IsSignalled));
    if (Result) then
    begin
      while oListaTasks.Count >= iQuantidadeTasksSimultaneas do
        Sleep(5);
    end;
  end;



var
  sException: String;
  oListaIndices: TList<Int64>;
begin
  oListaObjetosParametro := AListaObjetos;

  if (TObjectList<TObject>(oListaObjetosParametro.AsObject).Count = 0) then
    Exit;

  iQuantidadeTasksSimultaneas := QuantidadeTasks(AQuantidadeTasksSimultaneas);

  if (iQuantidadeTasksSimultaneas = 0) then
    iQuantidadeTasksSimultaneas := 1;

  sException              := EmptyStr;
  oListaTasks             := TObjectDictionary<String, TObject>.Create;
  oListaIndices           := TList<Int64>.Create;
  oIOmniCancellationToken := CreateOmniCancellationToken;
  try
    for oObjecto in TObjectList<TObject>(oListaObjetosParametro.AsObject) do
    begin
      if (PodeIniciarNovaThread) then
      begin
        oIOmniTaskControl := TRgnSistemaThreadFactory.CriarTarefaParalelaComRaiseExcept(
          procedure(const ATask: IOmniTask)
          begin
            try
              try
                if (not(sException.IsEmpty)) then
                  Exit;

                AMetodoExecutar(ATask, oListaTasks[ATask.Name]);
              except
                on E: Exception do
                begin
                  if (sException.IsEmpty) then
                    sException := E.Message + '|' + E.ClassName + '|' + E.StackTrace;
                  ATask.CancellationToken.Signal;
                end;
              end;
            finally
              oListaTasks.Remove(ATask.Name);
              oListaIndices.Add(ATask.UniqueID);
            end;
          end, oIOmniCancellationToken, nil, False);

        oListaTasks.Add(oIOmniTaskControl.Name, oObjecto);
        oIOmniTaskControl.Param.Add(oListaIndices, INDICE_THREAD);
        oIOmniTaskControl.Param.Add(TObjectList<TObject>(oListaObjetosParametro.AsObject).Count, TOTAL_THREAD);
        oIOmniTaskControl.Run;
      end;
    end;

    while oListaTasks.Count > 0 do
    begin
      Sleep(5);
    end;

  finally
    oListaTasks.Free;
    oListaIndices.Free;

    if (not(sException.IsEmpty)) then
      raise Exception.Create(sException);
  end;
end;



class function TRgnSistemaThreadFactory.CriarLoopTasks(const AQuantidadeTasksSimultaneas: Integer; const AListaObjetos: TValue; const AMetodoExecutar: TMetodoExecutarLoopTask): IOmniParallelLoop<Integer>;
var
  oListaObjetosParametro: TValue;
  oException: Exception;
  iQuantidadeTasksSimultaneas: Integer;
begin
  oListaObjetosParametro := AListaObjetos;

  if (TObjectList<TObject>(oListaObjetosParametro.AsObject).Count = 0) then
    Exit(nil);

  iQuantidadeTasksSimultaneas := QuantidadeTasks(AQuantidadeTasksSimultaneas);

  if (iQuantidadeTasksSimultaneas = 0) then
    iQuantidadeTasksSimultaneas := 1;

  Result := Parallel.ForEach(0, Pred(TObjectList<TObject>(oListaObjetosParametro.AsObject).Count))
    .TaskConfig(Parallel.TaskConfig.OnMessage(nil))
    .NumTasks(ifthen(iQuantidadeTasksSimultaneas > TObjectList<TObject>(oListaObjetosParametro.AsObject).Count, TObjectList<TObject>(oListaObjetosParametro.AsObject).Count, iQuantidadeTasksSimultaneas));

  oException := nil;
  Result.Execute(
    procedure(const ATask: IOmniTask; const AIndex: Integer)
    var
      oListaObjetos: TObjectList<TObject>;
    begin
      try
        if (Assigned(oException)) then
          Exit;

        oListaObjetos := TObjectList<TObject>(oListaObjetosParametro.AsObject);
        AMetodoExecutar(ATask, oListaObjetos[AIndex]);
      except
        on E: Exception do
        begin
          if (oException = nil) then
            oException := Exception.Create(E.Message + '|' + E.ClassName + '|' + E.StackTrace);
        end;
      end;
    end);

  if (Assigned(oException)) then
    raise oException;
end;



class procedure TRgnSistemaThreadFactory.CriarLoopTasksSimultaneas(const AQuantidadeTasksSimultaneas: Integer; const AListaObjetos: TValue; const AMetodoExecutar: TMetodoExecutarLoopTask; const ADispararExcecao: Boolean);

  procedure CarregarDicionarioDaThread(const AQuantidadeTasks: Integer; const ADicionarioThread: TDicionarioThread);
  var
    iNumeroInstancia: Integer;
    oDadosThread: TDadosThread;
  begin
    for iNumeroInstancia := 1 to AQuantidadeTasks do
    begin
      oDadosThread               := TDadosThread.Create;
      oDadosThread.oITaskControl := CriarTarefaParalela(
        procedure(const ATask: IOmniTask)
        var
          oDadosThread: TDadosThread;
        begin
          if (ADicionarioThread.TryGetValue(ATask.Name, oDadosThread)) then
          begin
            AMetodoExecutar(ATask, oDadosThread.oListaObjetos);
          end;
        end,
        nil, nil, nil, False);
      ADicionarioThread.Add(oDadosThread.oITaskControl.Name, oDadosThread);
    end;
  end;

  procedure DistribuirItensEntreThreads(const ADicionarioThread: TDicionarioThread);
  var
    oDadosThread: TDadosThread;
    iIndexThread, iIndexItens: Integer;
  begin
    for oDadosThread in ADicionarioThread.Values do
    begin
      iIndexThread := ADicionarioThread.GetIndex(oDadosThread.oITaskControl.Name);

      for iIndexItens := 0 to Pred(TObjectList<TObject>(AListaObjetos.AsObject).Count) do
      begin
        if ((iIndexItens mod ADicionarioThread.Count) = iIndexThread) then
          oDadosThread.oListaObjetos.Add(TObjectList<TObject>(AListaObjetos.AsObject).Items[iIndexItens]);
      end;
    end;
  end;

  procedure IniciarThreads(const ADicionarioDadosThread: TDicionarioThread);
  var
    oDadosThread: TDadosThread;
  begin
    for oDadosThread in ADicionarioDadosThread.Values do
      oDadosThread.oITaskControl.Run;
  end;

  procedure AguardarConclusaoProcessamento(const ADicionarioDadosThread: TDicionarioThread);
  var
    oDadosThread: TDadosThread;
    oException: Exception;
  begin
    oException := nil;

    for oDadosThread in ADicionarioDadosThread.Values do
    begin
      oDadosThread.oITaskControl.WaitFor(INFINITE);

      if ((ADispararExcecao) and (not(Assigned(oException))) and (Assigned(oDadosThread.oITaskControl.FatalException))) then
      begin
        oException := oDadosThread.oITaskControl.FatalException;
        oDadosThread.oITaskControl.DetachException;
      end;
    end;

    if (Assigned(oException)) then
      raise oException;
  end;

  function GetQuantidadeDeTasks(const AQuantidadeItens, AQuantidadeThreadsPreDefinido: Integer): Integer;
  var
    iQntThreads: Integer;
  begin
    Result := 1;

    for iQntThreads := AQuantidadeThreadsPreDefinido downto 1 do
    begin
      if (Trunc(AQuantidadeItens / iQntThreads) >= 1) then
        Exit(iQntThreads);
    end;
  end;



var
  oDicionarioThread: TDicionarioThread;
  iQuantidadeTasks: Integer;
begin
  if (TObjectList<TObject>(AListaObjetos.AsObject).Count = 0) then
    Exit;

  oDicionarioThread := TDicionarioThread.Create([doOwnsValues]);
  try
    iQuantidadeTasks := GetQuantidadeDeTasks(TObjectList<TObject>(AListaObjetos.AsObject).Count, AQuantidadeTasksSimultaneas);

    CarregarDicionarioDaThread(iQuantidadeTasks, oDicionarioThread);

    DistribuirItensEntreThreads(oDicionarioThread);

    IniciarThreads(oDicionarioThread);

    AguardarConclusaoProcessamento(oDicionarioThread);
  finally
    oDicionarioThread.Free;
  end;
end;



class function TRgnSistemaThreadFactory.CriarTarefaParalela(AExecutarThread: TMetodoExecutarTask; AExibirMensagem: TMetodoExibirMensagemTask = nil; ACancelarThread: IOmniCancellationToken = nil; AFinalizarThread: TMetodoFinalizarTask = nil; const AIniciarImediatamente: Boolean = True): IOmniTaskControl;
begin
  Result := CreateTask(
    procedure(const ATask: IOmniTask)
    begin
      try
        AExecutarThread(ATask);
      except
        on E: Exception do
        begin
          ATask.Comm.Send(WM_MENSAGEMERRO, E.ClassName + '| ' + E.Message + '| StackLog: ' + E.StackTrace);
        end;
      end;
    end, GerarNomeThread).CancelWith(GetTokenCancelamentoThread(ACancelarThread)).OnMessage(
    procedure(const ATask: IOmniTaskControl; const AMsg: TOmniMessage)
    begin
      try
        if (Assigned(AExibirMensagem)) then
          AExibirMensagem(ATask, AMsg);

        case (AMsg.MsgID) of
          WM_MENSAGEMERRO:
            begin
              raise Exception.Create(AMsg.MsgData.AsString);
            end;
        end;
      except
        ATask.CancellationToken.Signal;
        ATask.WaitFor(3000);
        Raise;
      end;

    end).OnTerminated(
    procedure(const ATask: IOmniTaskControl)
    begin
      if (Assigned(AFinalizarThread)) then
        AFinalizarThread(ATask);
    end);

  if (AIniciarImediatamente) then
    Result.Run;
end;



class function TRgnSistemaThreadFactory.CriarTarefaParalelaComRaiseExcept(AExecutarThread: TMetodoExecutarTask; ACancelarThread: IOmniCancellationToken; AFinalizarThread: TMetodoFinalizarTask; const AIniciarImediatamente: Boolean): IOmniTaskControl;
begin
  Result := CreateTask(
    procedure(const ATask: IOmniTask)
    begin
      AExecutarThread(ATask);
    end, GerarNomeThread)
    .CancelWith(GetTokenCancelamentoThread(ACancelarThread))
    .OnTerminated(
    procedure(const ATask: IOmniTaskControl)
    begin
      if (Assigned(ATask.FatalException)) then
      begin
        ATask.CancellationToken.Signal;
        ATask.WaitFor(3000);
      end;

      if (Assigned(AFinalizarThread)) then
        AFinalizarThread(ATask);

      if (Assigned(ATask.FatalException)) then
        raise ATask.DetachException;
    end);

  if (AIniciarImediatamente) then
    Result.Run;
end;



class procedure TRgnSistemaThreadFactory.CriarThread(var AThread: TThread; const IniciarImediatamente: Boolean; const APermitirThreadsSimultaneas: Boolean; const AExecutarThread: TMetodoExecutarThread; AFinalizarThread: TMetodoExecutarFinalizarThread; AException: TMetodoExecutarException);
var
  oThread: TThread;
begin
  if (not(APermitirThreadsSimultaneas)) then
  begin
    if (Assigned(AThread)) then
    begin
      AThread.WaitFor;
    end;
  end;

  AThread := TThread.CreateAnonymousThread(
    procedure
    var
      Handle: THandle;
      rException: TExceptionReturn;
    begin
      Handle := oThread.Handle;
      try
        AExecutarThread;

        if (Assigned(AFinalizarThread)) then
        begin
          AFinalizarThread;
        end;
        TerminateThread(Handle, 0);
      except
        on E: Exception do
        begin
          if (Assigned(AException)) then
          begin
            rException.EMessage := E.Message;
            rException.EStackTrace := E.StackTrace;
            rException.EClassName := E.ClassName;
            rException.Return := E.ClassName + '| ' + E.Message + '| StackLog: ' + E.StackTrace;
            AException(rException);
          end;
          TerminateThread(Handle, 0);
        end;
      end;
    end);

  oThread := AThread;
  if (IniciarImediatamente) then
    oThread.Start;
end;



class procedure TRgnSistemaThreadFactory.CriarThreadNativa(var AThread: TThread; const IniciarImediatamente, APermitirThreadsSimultaneas: Boolean; const AExecutarThread: TMetodoExecutarThread; AFinalizarThread: TMetodoExecutarFinalizarThread);
begin
  CriarThread(AThread, IniciarImediatamente, APermitirThreadsSimultaneas, AExecutarThread, AFinalizarThread,
    procedure(AException: TExceptionReturn)
    begin
      raise Exception.Create(AException.Return);
    end);
end;



class function TRgnSistemaThreadFactory.GerarNomeThread: String;
begin
  Result := 'Thread_Sistema_' + FormatDateTime('dd_mm_yyyy_hh_nn_ss_zzz', Now) + '_' + GetNumeroRandomico;
end;



class function TRgnSistemaThreadFactory.GetTokenCancelamentoThread(const ACancellationToken: IOmniCancellationToken): IOmniCancellationToken;
begin
  if (Assigned(ACancellationToken)) then
    Result := ACancellationToken
  else
    Result := CreateOmniCancellationToken;
end;

{ TDadosThread }



constructor TDadosThread.Create;
begin
  oListaObjetos := TObjectList<TObject>.Create(False);
end;



destructor TDadosThread.Destroy;
begin
  oListaObjetos.Free;
  inherited;
end;

{ TDicionarioThread }



procedure TDicionarioThread.Add(const Key: String; const Value: TDadosThread);
begin
  inherited Add(Key, Value);
  oListaIndices.Add(Key);
end;



procedure TDicionarioThread.Clear;
begin
  inherited Clear;
  oListaIndices.Clear;
end;



constructor TDicionarioThread.Create(Ownerships: TDictionaryOwnerships);
begin
  inherited Create(Ownerships);
  oListaIndices := TList<String>.Create;
end;



destructor TDicionarioThread.Destroy;
begin
  oListaIndices.Free;
  inherited;
end;



function TDicionarioThread.GetIndex(const AKey: String): Integer;
begin
  Result := oListaIndices.IndexOf(AKey);
end;



procedure TDicionarioThread.Remove(const Key: String);
begin
  inherited Remove(Key);
  oListaIndices.Remove(Key);
end;

end.

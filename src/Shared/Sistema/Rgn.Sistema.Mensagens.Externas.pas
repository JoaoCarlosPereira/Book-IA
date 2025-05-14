unit Rgn.Sistema.Mensagens.Externas;

interface

uses
  SysmoSQL, otlTask,
  OtlTaskControl, OtlComm, Rgn.Sistema.ThreadFactory, OtlCommon,
  System.SyncObjs,
  OtlSync;

type
  TMetodoExibirMensagem = reference to function(const ATipo: Integer; const AMensagem: string): Boolean;

{$M+}

  IRgnSistemaMensagensExternas = interface
    ['{0FEBC2FE-E31B-4792-8319-B1B9ABF79816}']
    procedure IncluirMensagem(const ATipoMensagem: Integer; const AMensagem: string);
  end;
{$M-}

  TRgnSistemaMensagensExternas = class(TInterfacedObject, IRgnSistemaMensagensExternas)
  strict private
    CriticalSection: TCriticalSection;
    oControladorThread: IOmniTask;
  public
    constructor Create(const AControladorThread: IOmniTask); overload;
    destructor Destroy; override;
    function Ref: IRgnSistemaMensagensExternas;
    procedure IncluirMensagem(const ATipoMensagem: Integer; const AMensagem: string);
  end;

implementation

uses
  Winapi.Windows, Rgn.Sistema.ThreadUtils, RecordHelper.HArray, SysUtils;

{ TRgnSistemaMensagensExternas }



constructor TRgnSistemaMensagensExternas.Create(const AControladorThread: IOmniTask);
begin
  oControladorThread := AControladorThread;
  CriticalSection   := TCriticalSection.Create;
end;



destructor TRgnSistemaMensagensExternas.Destroy;
begin
  CriticalSection.Free;
  inherited;
end;



procedure TRgnSistemaMensagensExternas.IncluirMensagem(const ATipoMensagem: Integer; const AMensagem: string);
begin
  CriticalSection.Enter;
  try
    oControladorThread.Comm.Send(ATipoMensagem, AMensagem);
  finally
    CriticalSection.Release;
  end;
end;



function TRgnSistemaMensagensExternas.Ref: IRgnSistemaMensagensExternas;
begin
  Result := Self;
end;

end.

unit Sistema.Singleton;

interface

uses
  Helper.HRecords;

type
  TSistemaSingleton = class
  private
    rSistemaSingleton: TSistema;

  public
    function Obter: TSistema; overload;
    procedure Postar(ASistema: TSistema); overload;
  end;

var
  oSistemaSingleton: TSistemaSingleton;

implementation

uses
  SysUtils, StrUtils;

{ TSistemaSingleton }



function TSistemaSingleton.Obter: TSistema;
begin
  Result := rSistemaSingleton;
end;



procedure TSistemaSingleton.Postar(ASistema: TSistema);
begin
  rSistemaSingleton := ASistema;
end;

initialization

oSistemaSingleton := TSistemaSingleton.Create;

finalization

FreeAndNil(oSistemaSingleton);

end.

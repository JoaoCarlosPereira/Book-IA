unit Leitor.IA.Request;

interface

uses
  System.SysUtils,
  System.Classes;

type
  TRequestIA = class
  private
    FModel: string;
    FPrompt: string;
    FStream: Boolean;
  public
    function ToJson: String;
    constructor Create;

    property model: string read FModel write FModel;
    property prompt: string read FPrompt write FPrompt;
    property stream: Boolean read FStream write FStream;
  end;

implementation

uses
  Lib.Serialize.Factory, Lib.Serialize.Enumerator, IdURI, IdGlobal;

{ TRequest }



constructor TRequestIA.Create;
begin
  stream := False;
end;



function TRequestIA.ToJson: String;
var
  sJson: RawByteString;

  function UnescapeUnicode(const AStr: string): string;
  var
    I: Integer;
  begin
    Result := '';
    I      := 1;
    while I <= Length(AStr) do
    begin
      if (AStr[I] = '\') and (I < Length(AStr) - 5) and (AStr[I + 1] = 'u') then
      begin
        Result := Result + WideChar(StrToInt('$' + Copy(AStr, I + 2, 4)));
        Inc(I, 6);
      end
      else
      begin
        Result := Result + AStr[I];
        Inc(I);
      end;
    end;
  end;



begin
  TSerializeFactory.GetInstance(JSONSuperObject).Serialize(Self, sJson);
  Result := UTF8ToString(sJson);
  Result := TIdURI.URLDecode(Result, IndyTextEncoding_UTF8);
  Result := UnescapeUnicode(Result);
end;

end.

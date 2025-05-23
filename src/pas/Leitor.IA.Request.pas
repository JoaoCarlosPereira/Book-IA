unit Leitor.IA.Request;

interface

uses
  System.SysUtils,
  System.Classes;

type
  TOptions = class
  private
    Ftemperature: Currency;
    Ftop_p: Currency;
  public
    property temperature: Currency read Ftemperature write Ftemperature;
    property top_p: Currency read Ftop_p write Ftop_p;
  end;

  TRequestIA = class
  private
    FModel: string;
    Fkeep_alive: Integer;
    FPrompt: string;
    FStream: Boolean;
    Fstop: TArray<String>;
    Foptions: TOptions;
  public
    function ToJson: String;
    constructor Create;
    destructor Destroy; override;

    property model: string read FModel write FModel;
    property keep_alive: Integer read Fkeep_alive write Fkeep_alive;
    property prompt: string read FPrompt write FPrompt;
    property stream: Boolean read FStream write FStream;
    property stop: TArray<String> read Fstop write Fstop;
    property options: TOptions read Foptions write Foptions;
  end;

implementation

uses
  Lib.Serialize.Factory, Lib.Serialize.Enumerator, IdURI, IdGlobal;

{ TRequest }



constructor TRequestIA.Create;
begin
  FModel                := 'gemma3:27b-it-qat';
  FPrompt               := '';
  FStream               := False;
  Fstop                 := ['\n\n'];
  Fkeep_alive           := -1;
  Foptions              := TOptions.Create;
  Foptions.Ftemperature := 0.1;
  Foptions.Ftop_p       := 0.5;
end;



destructor TRequestIA.Destroy;
begin
  Foptions.Free;
  inherited;
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

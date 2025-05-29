unit Leitor.IA.Request;

interface

uses
  System.SysUtils,
  System.Classes, System.Generics.Collections;

type
  TMessage = class
  private
    Frole: string;
    Fcontent: string;
  public
    property role: string read Frole write Frole;
    property content: string read Fcontent write Fcontent;
  end;

  TRequestIA = class
  private
    Fmodel: string;
    Fstream: Boolean;
    Fmessages: TList<TMessage>;
    Ftop_p: Double;
    Ftemperature: Double;
  public
    constructor Create;
    destructor Destroy; override;

    procedure SetPrompt(const APrompt, AContent: string);
    function ToJson: String;

    property model: string read Fmodel write Fmodel;
    property stream: Boolean read Fstream write Fstream;
    property messages: TList<TMessage> read Fmessages write Fmessages;
//    property top_p: Double read Ftop_p write Ftop_p;
//    property temperature: Double read Ftemperature write Ftemperature;
  end;

  // Google
  TPartRequest = class
  private
    Ftext: string;
  public
    constructor Create;
    destructor Destroy; override;
    property text: string read Ftext write Ftext;
  end;

  TContentRequest = class
  private
    Fparts: TList<TPartRequest>;
  public
    constructor Create;
    destructor Destroy; override;
    property parts: TList<TPartRequest> read Fparts write Fparts;
  end;

  TContentsWrapper = class
  private
    Fcontents: TList<TContentRequest>;
  public
    constructor Create;
    destructor Destroy; override;
    function ToJson: String;
    property contents: TList<TContentRequest> read Fcontents write Fcontents;
  end;

implementation

uses
  Lib.Serialize.Factory, Lib.Serialize.Enumerator, IdURI, IdGlobal;

{ TRequest }



constructor TRequestIA.Create;
begin
  Fmodel    := 'gemma3:27b';
  Fstream   := false;
  Fmessages := TList<TMessage>.Create;
  Fmessages.Add(TMessage.Create);
  Fmessages.Last.Frole   := 'system';
  Fmessages.Last.content := '';
  Fmessages.Add(TMessage.Create);
  Fmessages.Last.Frole   := 'user';
  Fmessages.Last.content := '';
  Ftemperature           := 0.4;
  Ftop_p                 := 0.9;
end;



destructor TRequestIA.Destroy;
begin
  Fmessages.Free;
  inherited;
end;



procedure TRequestIA.SetPrompt(const APrompt, AContent: string);
begin
  Fmessages.First.content := APrompt;
  Fmessages.Last.content  := AContent;
end;



function TRequestIA.ToJson: String;
var
  sJson: RawByteString;

  function UnescapeUnicode(const AStr: string): string;
  var
    I: integer;
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

{ TContentsWrapper }



constructor TPartRequest.Create;
begin
  inherited;
end;



destructor TPartRequest.Destroy;
begin
  inherited;
end;

{ TContent }



constructor TContentRequest.Create;
begin
  inherited;
  Fparts := TList<TPartRequest>.Create;
end;



destructor TContentRequest.Destroy;
begin
  Fparts.Free;
  inherited;
end;

{ TContentsWrapper }



constructor TContentsWrapper.Create;
begin
  inherited;
  Fcontents := TList<TContentRequest>.Create;
end;



destructor TContentsWrapper.Destroy;
begin
  Fcontents.Free;
  inherited;
end;



function TContentsWrapper.ToJson: String;
var
  sJson: RawByteString;

  function UnescapeUnicode(const AStr: string): string;
  var
    I: integer;
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

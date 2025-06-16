unit Leitor.IA.Response;

interface

uses
  System.SysUtils,
  System.JSON, System.Classes, System.Generics.Collections;

type
  // Offline
  TMessageSimple = class
  private
    Frole: string;
    Fcontent: string;
  public
    constructor Create;
    destructor Destroy; override;
    property role: string read Frole write Frole;
    property content: string read Fcontent write Fcontent;
  end;

  TResponseLocal = class
  private
    Fmodel: string;
    Fcreated_at: string;
    Fmessage: TMessageSimple;
    Fdone_reason: string;
    Fdone: Boolean;
    Ftotal_duration: Int64;
    Fload_duration: Int64;
    Fprompt_eval_count: Integer;
    Fprompt_eval_duration: Int64;
    Feval_count: Integer;
    Feval_duration: Int64;
  private
    function GetResponse: string;
  public
    constructor Create;
    destructor Destroy; override;

    function QuantidadePersoangens: Integer;

    property model: string read Fmodel write Fmodel;
    property created_at: string read Fcreated_at write Fcreated_at;
    property message: TMessageSimple read Fmessage write Fmessage;
    property done_reason: string read Fdone_reason write Fdone_reason;
    property done: Boolean read Fdone write Fdone;
    property total_duration: Int64 read Ftotal_duration write Ftotal_duration;
    property load_duration: Int64 read Fload_duration write Fload_duration;
    property prompt_eval_count: Integer read Fprompt_eval_count write Fprompt_eval_count;
    property prompt_eval_duration: Int64 read Fprompt_eval_duration write Fprompt_eval_duration;
    property eval_count: Integer read Feval_count write Feval_count;
    property eval_duration: Int64 read Feval_duration write Feval_duration;
    property Response: string read GetResponse;
  end;

  // Online:
  TPart = class
  private
    Ftext: string;
  public
    constructor Create;
    destructor Destroy; override;
    property text: string read Ftext write Ftext;
  end;

  TContent = class
  private
    Frole: string;
    Fparts: TList<TPart>;
  public
    constructor Create;
    destructor Destroy; override;
    property role: string read Frole write Frole;
    property parts: TList<TPart> read Fparts write Fparts;
  end;

  TCandidate = class
  private
    Fcontent: TContent;
    FfinishReason: string;
    FavgLogprobs: Double;
  public
    constructor Create;
    destructor Destroy; override;
    property content: TContent read Fcontent write Fcontent;
    property finishReason: string read FfinishReason write FfinishReason;
    property avgLogprobs: Double read FavgLogprobs write FavgLogprobs;
  end;

  TTokenDetail = class
  private
    Fmodality: string;
    FtokenCount: Integer;
  public
    constructor Create;
    destructor Destroy; override;
    property modality: string read Fmodality write Fmodality;
    property tokenCount: Integer read FtokenCount write FtokenCount;
  end;

  TUsageMetadata = class
  private
    FpromptTokenCount: Integer;
    FcandidatesTokenCount: Integer;
    FtotalTokenCount: Integer;
    FpromptTokensDetails: TList<TTokenDetail>;
    FcandidatesTokensDetails: TList<TTokenDetail>;
  public
    constructor Create;
    destructor Destroy; override;
    property promptTokenCount: Integer read FpromptTokenCount write FpromptTokenCount;
    property candidatesTokenCount: Integer read FcandidatesTokenCount write FcandidatesTokenCount;
    property totalTokenCount: Integer read FtotalTokenCount write FtotalTokenCount;
    property promptTokensDetails: TList<TTokenDetail> read FpromptTokensDetails write FpromptTokensDetails;
    property candidatesTokensDetails: TList<TTokenDetail> read FcandidatesTokensDetails write FcandidatesTokensDetails;
  end;

  TResponseOnline = class
  private
    FmodelVersion: string;
    FresponseId: string;
    Fcandidates: TList<TCandidate>;
    FusageMetadata: TUsageMetadata;
    function GetResponse: string;
  public
    constructor Create;
    destructor Destroy; override;
    function QuantidadePersoangens: Integer;

    property modelVersion: string read FmodelVersion write FmodelVersion;
    property responseId: string read FresponseId write FresponseId;
    property candidates: TList<TCandidate> read Fcandidates write Fcandidates;
    property usageMetadata: TUsageMetadata read FusageMetadata write FusageMetadata;

    property Response: string read GetResponse;
  end;

implementation

uses
  SynCommons, IdURI, IdGlobal;

{ TMessageSimple }



constructor TMessageSimple.Create;
begin
  inherited;
end;



destructor TMessageSimple.Destroy;
begin
  inherited;
end;

{ TGemmaResponse }



constructor TResponseLocal.Create;
begin
  inherited;
  Fmessage := TMessageSimple.Create;
end;



destructor TResponseLocal.Destroy;
begin
  Fmessage.Free;
  inherited;
end;



function TResponseLocal.QuantidadePersoangens: Integer;

  function CountCharManual(const Texto: string; const C: Char): Integer;
  var
    I: Integer;
  begin
    Result := 0;
    for I  := 1 to Length(Texto) do
      if Texto[I] = C then
        Inc(Result);
  end;



begin
  Result := CountCharManual(GetResponse, '|');
end;



function TResponseLocal.GetResponse: string;
begin
  Result := Self.message.content;
end;



constructor TPart.Create;
begin
  inherited;
end;



destructor TPart.Destroy;
begin
  inherited;
end;

{ TContent }



constructor TContent.Create;
begin
  inherited;
  Fparts := TList<TPart>.Create;
end;



destructor TContent.Destroy;
begin
  Fparts.Free;
  inherited;
end;

{ TCandidate }



constructor TCandidate.Create;
begin
  inherited;
  Fcontent := TContent.Create;
end;



destructor TCandidate.Destroy;
begin
  Fcontent.Free;
  inherited;
end;

{ TTokenDetail }



constructor TTokenDetail.Create;
begin
  inherited;
end;



destructor TTokenDetail.Destroy;
begin
  inherited;
end;

{ TUsageMetadata }



constructor TUsageMetadata.Create;
begin
  inherited;
  FpromptTokensDetails     := TList<TTokenDetail>.Create;
  FcandidatesTokensDetails := TList<TTokenDetail>.Create;
end;



destructor TUsageMetadata.Destroy;
begin
  FpromptTokensDetails.Free;
  FcandidatesTokensDetails.Free;
  inherited;
end;

{ TGeminiResponse }



constructor TResponseOnline.Create;
begin
  inherited;
  Fcandidates    := TList<TCandidate>.Create;
  FusageMetadata := TUsageMetadata.Create;
end;



destructor TResponseOnline.Destroy;
begin
  Fcandidates.Free;
  FusageMetadata.Free;
  inherited;
end;



function TResponseOnline.GetResponse: string;

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
  if (Self.candidates.Count > 0) and (Self.candidates.Last.content.parts.Count > 0) then
  begin
    Result := UTF8ToString(Self.candidates.Last.content.parts.Last.text);
    Result := TIdURI.URLDecode(Result, IndyTextEncoding_UTF8);
    Result := UnescapeUnicode(Result);
  end;
end;



function TResponseOnline.QuantidadePersoangens: Integer;

  function CountCharManual(const Texto: string; const C: Char): Integer;
  var
    I: Integer;
  begin
    Result := 0;
    for I  := 1 to Length(Texto) do
      if Texto[I] = C then
        Inc(Result);
  end;



begin
  Result := CountCharManual(GetResponse, '|');
end;

end.

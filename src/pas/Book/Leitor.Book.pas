unit Leitor.Book;

interface

uses
  System.SysUtils,
  System.Classes,
  System.Generics.Collections, RecordHelper.HArray, Helper.HBoolean;

type
  TVoz = class
  public
    Sequencial: Int64;
    nome: string;
    genero: string;
    idade: string;
    EmUso: Boolean;
  end;

  TListaVozes = class(TObjectList<TVoz>)
  public
    function GetVoz(const AGenero, AIdade: string): TVoz;
  end;

  TPersonagemFala = class
  private
    FNome: string;
    FGenero: string;
    FIdadeAparente: string;
    FFala: string;
  public
    Sequencial: Int64;
    sequencialFala: Int64;
    Voz: TVoz;
    processado: Boolean;
    auxiliar: string;
    ArquivosAudio: TArrayString;
    Duracao: Integer;
    constructor Create;
    destructor Destroy; override;
    property nome: string read FNome write FNome;
    property genero: string read FGenero write FGenero;
    property idade_aparente: string read FIdadeAparente write FIdadeAparente;
    property fala: string read FFala write FFala;
  end;

  TListaPersonagensFalas = class(TObjectList<TPersonagemFala>)
  public
    function ToJson: String;
    function GetPersonagens: String;
    function GetTrechoPorPersonagem(const APersonagem: string): String;
    procedure RemoverDuplicados;
  end;

  TPagina = class
  public
    Sequencial: Int64;
    Texto: string;
    ListaPersonagens: TListaPersonagensFalas;
    Prompt: String;
    processado: Boolean;
    Response: String;
    Numero: Integer;
    Duracao: Currency;
    constructor Create;
    destructor Destroy; override;
  end;

  TLivro = class(TObjectList<TPagina>)
  public
    Sequencial: Int64;
    nome: string;
    lido: Boolean;
    normalizado: Boolean;
    narradorObtido: Boolean;
    produzido: Boolean;
    function GetTrechoPorPersonagem(const APersonagem: string): String;
    function GetPersonagem(const ANome: string): TArray<TPersonagemFala>;
    function GetPersonagens: TArrayString;
    function HaPaginasPendentes: Boolean;
    function HaFalasPendentes: Boolean;
    function DuracaoTotal: Currency;
  end;

implementation

uses
  Lib.Serialize.Factory, Lib.Serialize.Enumerator, IdURI,
  IdGlobal;



constructor TPagina.Create;
begin
  ListaPersonagens := TListaPersonagensFalas.Create;
  processado       := False;
  Prompt           := '';
end;



destructor TPagina.Destroy;
begin
  ListaPersonagens.Free;
  inherited;
end;

{ TListaPersonagensFalas }



function TListaPersonagensFalas.GetPersonagens: String;
var
  iIndice: Integer;
  oPersonagem: TPersonagemFala;
begin
  Result      := '';
  for iIndice := 0 to Pred(Self.Count) do
  begin
    oPersonagem := Self[iIndice];
    Result      := Result + iIndice.ToString + '|' + oPersonagem.nome + '|' + GetTrechoPorPersonagem(oPersonagem.nome) + ' \n ';
  end;
end;



function TListaPersonagensFalas.GetTrechoPorPersonagem(const APersonagem: string): String;
var
  oPersonagem: TPersonagemFala;
begin
  Result := '';
  for oPersonagem in Self do
  begin
    if (oPersonagem.nome = APersonagem) then
    begin
      Result := Result + oPersonagem.fala + ' ';
    end;

    if (Result.Replace(' ', '').Length >= 1000) then
      Break;
  end;

end;



procedure TListaPersonagensFalas.RemoverDuplicados;
var
  oArrayNomes: TArrayString;
  iIndice: Integer;
  oPersonagem: TPersonagemFala;
begin
  oArrayNomes := [];
  for iIndice := Pred(Self.Count) downto 0 do
  begin
    oPersonagem := Self[iIndice];
    if (oArrayNomes.Find(oPersonagem.nome)) then
    begin
      Self.Delete(iIndice);
    end
    else
      oArrayNomes.Add(oPersonagem.nome);

  end;
end;



function TListaPersonagensFalas.ToJson: String;
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

{ TLivro }



function TLivro.DuracaoTotal: Currency;
var
  oPagina: TPagina;
begin
  Result := 0;
  for oPagina in Self do
  begin
    Result := Result + oPagina.Duracao;
  end;
end;



function TLivro.GetPersonagem(const ANome: string): TArray<TPersonagemFala>;
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
begin
  Result := [];
  for oPagina in Self do
  begin
    for oPersonagem in oPagina.ListaPersonagens do
    begin
      if (oPersonagem.nome = ANome) then
      begin
        Result := Result + [oPersonagem];
      end;
    end;
  end;
end;



function TLivro.GetPersonagens: TArrayString;
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
begin
  Result := [];
  for oPagina in Self do
  begin
    for oPersonagem in oPagina.ListaPersonagens do
    begin
      Result.Add(oPersonagem.nome, False);
    end;
  end;
end;



function TLivro.GetTrechoPorPersonagem(const APersonagem: string): String;
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
begin
  Result := '';
  for oPagina in Self do
  begin
    for oPersonagem in oPagina.ListaPersonagens do
    begin
      if (oPersonagem.nome = APersonagem) then
      begin
        Result := Result + oPersonagem.fala + ' ';
      end;
    end;

    if (Result.Replace(' ', '').Length >= 800) then
      Break;
  end;
end;



function TLivro.HaFalasPendentes: Boolean;
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
begin
  Result := False;
  for oPagina in Self do
  begin
    for oPersonagem in oPagina.ListaPersonagens do
    begin
      if (not(oPersonagem.processado)) then
        Exit(True);
    end;
  end;
end;



function TLivro.HaPaginasPendentes: Boolean;
var
  oPagina: TPagina;
begin
  Result := False;
  for oPagina in Self do
  begin
    if (not(oPagina.processado)) and (not(oPagina.Response.Contains('no characters'))) then
    begin
      Exit(True);
    end;
  end;
end;

{ TPersonagemFala }



constructor TPersonagemFala.Create;
begin
  Voz := TVoz.Create;
end;



destructor TPersonagemFala.Destroy;
begin
  Voz.Free;
  inherited;
end;

{ TListaVozes }



function TListaVozes.GetVoz(const AGenero, AIdade: string): TVoz;
var
  oVoz: TVoz;
begin
  Result := nil;
  for oVoz in Self do
  begin
    if (not(oVoz.EmUso)) and (oVoz.genero.ToUpper.Equals(AGenero.ToUpper)) and ((oVoz.idade.ToUpper.Equals(AIdade.ToUpper)) or (AIdade.IsEmpty)) then
    begin
      oVoz.EmUso := True;
      Exit(oVoz);
    end;
  end;
end;

end.

unit Rgn.Leitor.Book.Narrador;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, OtlTask,
  Leitor.Book, Rgn.Leitor.IA.Http, Rgn.Leitor.Book.Abstract;

type
  IRgnLeitorBookNarrador = interface
    ['{BA32DA37-B936-4228-823E-BB58A1FF91E4}']
    procedure ObterNarrador(const ALivro: TLivro);
  end;

  TRgnLeitorBookNarrador = class(TRgnLeitorBookAbstract, IRgnLeitorBookNarrador)
  private
    procedure DefinirPerfilNarrador(const ALivro: TLivro);
  public
    procedure ObterNarrador(const ALivro: TLivro);
  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, Helper.HNumeric;



procedure TRgnLeitorBookNarrador.ObterNarrador(const ALivro: TLivro);
begin
  if (not(ALivro.narradorObtido)) then
  begin
    Writeln('Definindo perfil de narrador...');
    DefinirPerfilNarrador(ALivro);
  end;
end;



procedure TRgnLeitorBookNarrador.DefinirPerfilNarrador(const ALivro: TLivro);
var
  oRequestIA: TRequestIA;
  iTentativas: Integer;

  function GetPrompt: string;
  begin
    Result :=
      'Analyze the input and return the narrator profile in this exact format: Gender|Age\n' +
      'Gender must be Male or Female, based on the narration.\n' +
      'Age must be Child, Adult, or Elderly, based on the narration style.\n' +
      'Return ONLY the profile in the required format, nothing else.'
  end;

  procedure Generate;
  var
    oPersonagem: TPersonagemFala;
    sResponse: String;
  begin
    try
      sResponse := GetAPI.Generate(oRequestIA);

      if (sResponse.Contains('|')) and (Length(sResponse.Split(['|'])) >= 2) then
      begin
        for oPersonagem in ALivro.GetPersonagem('narrator') do
        begin
          oPersonagem.genero         := sResponse.Split(['|'])[0].Trim;
          oPersonagem.idade_aparente := sResponse.Split(['|'])[1].Trim;
        end;
      end
      else
      begin
        if (iTentativas > 0) then
        begin
          Inc(iTentativas, -1);
          Generate;
        end;
      end;
    except
      on E: Exception do
      begin
        if (iTentativas > 0) or (E.Message.Contains('timed out')) then
        begin
          Inc(iTentativas, -1);
          Sleep(UM_SEGUNDO);
          Generate;
        end
        else
          Raise;
      end;
    end;
  end;



begin
  iTentativas := 3;
  oRequestIA  := TRequestIA.Create;

  try
    oRequestIA.SetPrompt(GetPrompt, ALivro.GetTrechoPorPersonagem('narrator'));
    Generate;

    ALivro.narradorObtido := True;
    oIDAOLeitorBook.SalvarCabecalho(ALivro);
    oIDAOLeitorBook.SalvarPersonagens(ALivro);
  finally
    oRequestIA.Free;
  end;
end;

end.

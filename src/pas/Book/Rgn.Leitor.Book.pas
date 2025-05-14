unit Rgn.Leitor.Book;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, OtlTask,
  Leitor.Book, Rgn.Leitor.PDF;

type
  IRgnLeitorBook = interface
    ['{7CE41228-2682-49C9-A436-209B66DFB41B}']
    procedure ProcessarBook(const ALivroPDF: String);
  end;

  TRgnLeitorBook = class(TInterfacedPersistent, IRgnLeitorBook)
  private
    oLivro: TLivro;
    oIRgnLeitorPDF: IRgnLeitorPDF;
    procedure ProcessarBook(const ALivroPDF: String);
    procedure ObterPersonagens;
  public
    constructor Create;
    destructor Destroy; override;

  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, Rgn.Leitor.IA.Http;



constructor TRgnLeitorBook.Create;
begin
  oLivro         := TLivro.Create;
  oIRgnLeitorPDF := TRgnLeitorPDF.Create;
end;



procedure TRgnLeitorBook.ProcessarBook(const ALivroPDF: String);
var
  oPaginas: TStringList;
  sTexto: string;
begin
  oPaginas := oIRgnLeitorPDF.LerPDFPorPagina(ALivroPDF);
  try
    oLivro.Clear;
    for sTexto in oPaginas do
    begin
      oLivro.Add(TPagina.Create);
      oLivro.Last.Texto := sTexto;
    end;
    ObterPersonagens;

  finally
    oPaginas.Free;
  end;

end;



procedure TRgnLeitorBook.ObterPersonagens;
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
begin
  TRgnSistemaThreadFactory.CriarLoopTasks(15, oLivro,
    procedure(const ATask: IOmniTask; const AObjeto: TObject)
    var
      oPagina: TPagina;
      oRequestIA: TRequestIA;
      oResponse: TResponse;
      oPersonagens: TStringList;
      sPersonagem: string;

      function GetPrompt: string;
      begin
        Result := 'Abaixo est� um trecho de um livro. Seu objetivo � identificar apenas os personagens que t�m fala expl�cita dentro da narrativa da hist�ria.' + sLineBreak +
            '' + sLineBreak +
            'Ignore completamente qualquer conte�do que n�o fa�a parte da narrativa, como:' + sLineBreak +
            '- Nome do autor ou autora' + sLineBreak +
            '- Cr�ditos editoriais' + sLineBreak +
            '- Pref�cio, sum�rio, ep�grafe ou dedicat�ria' + sLineBreak +
            '- Instru��es, t�tulos ou notas que n�o fa�am parte da hist�ria em si' + sLineBreak +
            '' + sLineBreak +
            'Considere como fala apenas as frases que come�am com travess�o no in�cio da linha.' + sLineBreak +
            'Ignore travess�es que aparecem no meio de palavras (como em "busc�-los").' + sLineBreak +
            '' + sLineBreak +
            'Para cada personagem com fala identific�vel, informe:' + sLineBreak +
            '- Nome' + sLineBreak +
            '- G�nero: masculino ou feminino' + sLineBreak +
            '- Idade aparente: crian�a, adulto ou idoso' + sLineBreak +
            '' + sLineBreak +
            'Formato da resposta, sem t�tulo ou cabe�alho:' + sLineBreak +
            'Nome|g�nero|idade aparente' + sLineBreak +
            '' + sLineBreak +
            'Instru��es importantes:' + sLineBreak +
            '- N�o inclua linhas como "Nome|g�nero|idade_aparente".' + sLineBreak +
            '- N�o repita personagens. Escolha a idade mais compat�vel com o trecho.' + sLineBreak +
            '- Inferir o g�nero e a idade a partir do nome e do contexto da fala, mesmo que n�o estejam explicitamente escritos.' + sLineBreak +
            '- Ignore personagens sem nome claro ou com nomes gen�ricos como "mo�o", "senhora", "menino", exceto se forem usados como nomes pr�prios.' + sLineBreak +
            '- Se nenhum personagem com fala for identificado, responda apenas com: sem personagens' + sLineBreak +
            '' + sLineBreak +
            'Trecho:' + sLineBreak +
          'Trecho:' + sLineBreak + '"""' + sLineBreak + oPagina.Texto + sLineBreak + '"""';
      end;



    begin
      oPagina := TPagina(AObjeto);
      oRequestIA := TRequestIA.Create;
      oPersonagens := TStringList.Create;
      try
        try
          oRequestIA.model := 'gemma3:27b';
          oRequestIA.prompt := GetPrompt;

          oResponse := TRgnLeitorIAHttp.Create.Ref.Generate(oRequestIA);

          if (oResponse.Response <> '') and (not(oResponse.Response.Contains('sem personagens'))) then
          begin
            oPersonagens.Text := oResponse.Response;
            for sPersonagem in oPersonagens do
            begin
              if (sPersonagem.Contains('|')) and (Length(sPersonagem.Split(['|'])) >= 3) then
              begin
                oPagina.ListaPersonagens.Add(TPersonagemFala.Create);
                oPagina.ListaPersonagens.Last.nome := sPersonagem.Split(['|'])[0];
                oPagina.ListaPersonagens.Last.genero := sPersonagem.Split(['|'])[1];
                oPagina.ListaPersonagens.Last.idade_aparente := sPersonagem.Split(['|'])[2];
              end;
            end;
          end;
        except
          on E: Exception do
          begin
            with TStringList.Create do
            begin
              Add(oResponse.Response);
              Add(E.Message + '|' + E.ClassName + '|' + E.StackTrace);
              SaveToFile('Outputerror.txt');
              Free;
            end;
          end;
        end;;
      finally
        oPersonagens.Free;
        oRequestIA.Free;
      end;
    end);

  with TStringList.Create do
  begin
    for oPagina in oLivro do
    begin
      for oPersonagem in oPagina.ListaPersonagens do
      begin
        Add(oPersonagem.nome + '|' + oPersonagem.genero + '|' + oPersonagem.idade_aparente);
      end;
    end;
    SaveToFile('Outputteste.txt');
    Free;
  end;

end;



destructor TRgnLeitorBook.Destroy;
begin
  oLivro.Free;
  inherited;
end;

end.

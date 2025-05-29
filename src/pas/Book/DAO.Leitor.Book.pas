unit DAO.Leitor.Book;

interface

uses
  Padrao.DAO, System.Generics.Collections, System.SysUtils, System.Classes, OtlTask,
  Leitor.Book, SysmoSQL, Helper.HBoolean, Rgn.Leitor.IA.Http;

type
  IDAOLeitorBook = interface
    ['{54991F2D-7449-4F8E-BF25-189CBD439D82}']
    procedure SalvarCabecalho(const ALivro: TLivro);
    procedure SalvarPaginas(const ALivro: TLivro);
    procedure SalvarPagina(const ALivro: TLivro; const APagina: TPagina);
    procedure SalvarPersonagens(const ALivro: TLivro);
    procedure SalvarFalas(const ALivro: TLivro; const ALimpar: Boolean = true);
    procedure SalvarFala(const ALivro: TLivro; const APagina: TPagina);

    function LocalizarCabecalho(const ALivro: TLivro): Boolean;
    function LocalizarPaginas(const ALivro: TLivro): Boolean;
    function LocalizarFalas(const ALivro: TLivro): Boolean;
    function LocalizarAPIS(const AListaAPI: TListaAPI): Boolean;
    procedure AtualizarAPI(const AKey: string);
    procedure RemoverPersonagensSemFala(const ALivro: TLivro);
  end;

  TDAOLeitorBook = class(TPadraoDAO, IDAOLeitorBook)
  public
    procedure SalvarCabecalho(const ALivro: TLivro);
    procedure SalvarPaginas(const ALivro: TLivro);
    procedure SalvarPagina(const ALivro: TLivro; const APagina: TPagina);
    procedure SalvarPersonagens(const ALivro: TLivro);
    procedure SalvarFalas(const ALivro: TLivro; const ALimpar: Boolean = true);
    procedure SalvarFala(const ALivro: TLivro; const APagina: TPagina);

    function LocalizarCabecalho(const ALivro: TLivro): Boolean;
    function LocalizarPaginas(const ALivro: TLivro): Boolean;
    function LocalizarFalas(const ALivro: TLivro): Boolean;
    function LocalizarAPIS(const AListaAPI: TListaAPI): Boolean;
    procedure AtualizarAPI(const AKey: string);
    procedure RemoverPersonagensSemFala(const ALivro: TLivro);
    function Ref: IDAOLeitorBook;

    constructor Create; reintroduce;
    destructor Destroy; override;

  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, SynCommons, Helper.HSQLBuilder, Helper.HSQL, System.DateUtils;



procedure TDAOLeitorBook.AtualizarAPI(const AKey: string);
begin
  oUpdate1.Limpar;
  oUpdate1.Add('DT_EXPIRACAO', IncDay(Now));
  oUpdate1.AddWhere('TX_KEY', AKey);
  oUpdate1.SetTabela('TB_LIVROAPIS');
  oConexao1.Execute(oUpdate1.SQL(), oUpdate1.Params());
end;



constructor TDAOLeitorBook.Create;
begin
  CriarConexao(oConexao1, Self.ClassName).Conectar(true);
  inherited Create(oConexao1);
end;



destructor TDAOLeitorBook.Destroy;
begin
  inherited;
  oConexao1.Free;
end;



function TDAOLeitorBook.LocalizarAPIS(const AListaAPI: TListaAPI): Boolean;

  function GetSQL: string;
  begin
    Result := 'SELECT TX_KEY, DT_EXPIRACAO FROM TB_LIVROAPIS WHERE DT_EXPIRACAO <= :AData or DT_EXPIRACAO is null order by CD_SEQUENCIAL';
  end;



begin
  PrepararSQL(oSQLDataSet1, GetSQL);
  oSQLDataSet1.ParamByName('AData').AsDateTime := Now;
  oSQLDataSet1.Open;

  oSQLDataSet1.First;
  AListaAPI.Clear;
  while (not(oSQLDataSet1.Eof)) do
  begin
    if (oSQLDataSet1.FieldByName('TX_KEY').AsString = 'local') then
      AListaAPI.Add(TRgnLeitorIAHttp.Create(ttaLocal))
    else
      AListaAPI.Add(TRgnLeitorIAHttp.Create(ttaOnline, oSQLDataSet1.FieldByName('TX_KEY').AsString));

    oSQLDataSet1.Next;
  end;
  oSQLDataSet1.Close;
end;



function TDAOLeitorBook.LocalizarCabecalho(const ALivro: TLivro): Boolean;

  function GetSQL: string;
  begin
    Result := 'SELECT * FROM TB_LIVROCABECALHO WHERE TX_TITULO = :ATitulo;';
  end;



begin
  PrepararSQL(oSQLDataSet1, GetSQL);
  oSQLDataSet1.ParamByName('ATitulo').AsString := ALivro.nome;
  oSQLDataSet1.Open;

  oSQLDataSet1.First;
  ALivro.Clear;
  while (not(oSQLDataSet1.Eof)) do
  begin
    ALivro.sequencial     := oSQLDataSet1.FieldByName('CD_SEQUENCIAL').AsLargeInt;
    ALivro.nome           := oSQLDataSet1.FieldByName('TX_TITULO').AsString;
    ALivro.lido           := oSQLDataSet1.FieldByName('FL_LIDO').AsString = 'S';
    ALivro.normalizado    := oSQLDataSet1.FieldByName('FL_NORMALIZADO').AsString = 'S';
    ALivro.narradorObtido := oSQLDataSet1.FieldByName('FL_NARRADOR').AsString = 'S';
    ALivro.produzido      := oSQLDataSet1.FieldByName('FL_PRODUZIDO').AsString = 'S';
    oSQLDataSet1.Next;
  end;
  oSQLDataSet1.Close;
end;



function TDAOLeitorBook.LocalizarPaginas(const ALivro: TLivro): Boolean;

  function GetSQL: string;
  begin
    Result :=
      'SELECT * FROM TB_LIVROPAGINA  ' +
      'WHERE CD_SEQUENCIALLIVRO = :ATitulo order by NR_PAGINA';
  end;



begin
  PrepararSQL(oSQLDataSet1, GetSQL);
  oSQLDataSet1.ParamByName('ATitulo').AsLargeInt := ALivro.sequencial;
  oSQLDataSet1.Open;

  oSQLDataSet1.First;
  while (not(oSQLDataSet1.Eof)) do
  begin
    ALivro.Add(TPagina.Create);

    ALivro.Last.sequencial := oSQLDataSet1.FieldByName('CD_SEQUENCIAL').AsLargeInt;
    ALivro.Last.Numero     := oSQLDataSet1.FieldByName('NR_PAGINA').AsLargeInt;
    ALivro.Last.Texto      := oSQLDataSet1.FieldByName('TX_PAGINA').AsString;
    ALivro.Last.Processado := oSQLDataSet1.FieldByName('FL_PROCESSADO').AsString = 'S';
    ALivro.Last.Numero     := oSQLDataSet1.FieldByName('NR_PAGINA').AsInteger;
    oSQLDataSet1.Next;
  end;
  oSQLDataSet1.Close;

  if (ALivro.Count > 0) then
    LocalizarFalas(ALivro);
end;



function TDAOLeitorBook.Ref: IDAOLeitorBook;
begin
  Result := Self;
end;



procedure TDAOLeitorBook.RemoverPersonagensSemFala(const ALivro: TLivro);
begin
  PrepararSQL(oSQLDataSet1, 'delete from TB_LIVROPERSONAGENS where CD_SEQUENCIALLIVRO = :ALivro and CD_SEQUENCIAL not in (select CD_SEQUENCIALPERSONAGEM from TB_LIVROFALAS where CD_SEQUENCIALLIVRO = :ALivro)');
  oSQLDataSet1.ParamByName('ALivro').AsLargeInt := ALivro.sequencial;
  oSQLDataSet1.ExecSQL();
end;



function TDAOLeitorBook.LocalizarFalas(const ALivro: TLivro): Boolean;

  function GetSQL: string;
  begin
    Result :=
      'SELECT ' +
      '  F.CD_SEQUENCIAL, ' +
      '  F.CD_SEQUENCIALLIVRO, ' +
      '  F.CD_SEQUENCIALPAGINA, ' +
      '  F.CD_SEQUENCIALPERSONAGEM, ' +
      '  F.TX_FALA, ' +
      '  P.TX_PERSONAGEM, ' +
      '  P.TX_GENERO, ' +
      '  P.TX_IDADE, ' +
      '  P.CD_VOZ, ' +
      '  F.FL_PROCESSADO ' +
      'FROM TB_LIVROFALAS F ' +
      'JOIN TB_LIVROPERSONAGENS P ON P.CD_SEQUENCIAL = F.CD_SEQUENCIALPERSONAGEM ' +
      'WHERE F.CD_SEQUENCIALLIVRO = :ATitulo';
  end;



var
  oDicionarioPaginas: TObjectDictionary<Int64, TPagina>;
  oPagina: TPagina;
begin
  PrepararSQL(oSQLDataSet1, GetSQL);
  oSQLDataSet1.ParamByName('ATitulo').AsLargeInt := ALivro.sequencial;
  oSQLDataSet1.Open;

  oDicionarioPaginas := TObjectDictionary<Int64, TPagina>.Create;
  try
    for oPagina in ALivro do
    begin
      oPagina.ListaPersonagens.Clear;
      oDicionarioPaginas.Add(oPagina.sequencial, oPagina);
    end;

    oSQLDataSet1.First;
    while (not(oSQLDataSet1.Eof)) do
    begin
      if (oDicionarioPaginas.TryGetValue(oSQLDataSet1.FieldByName('CD_SEQUENCIALPAGINA').AsLargeInt, oPagina)) then
      begin
        oPagina.ListaPersonagens.Add(TPersonagemFala.Create);
        oPagina.ListaPersonagens.Last.sequencial     := oSQLDataSet1.FieldByName('CD_SEQUENCIAL').AsLargeInt;
        oPagina.ListaPersonagens.Last.nome           := oSQLDataSet1.FieldByName('TX_PERSONAGEM').AsString;
        oPagina.ListaPersonagens.Last.genero         := oSQLDataSet1.FieldByName('TX_GENERO').AsString;
        oPagina.ListaPersonagens.Last.idade_aparente := oSQLDataSet1.FieldByName('TX_IDADE').AsString;
        oPagina.ListaPersonagens.Last.fala           := oSQLDataSet1.FieldByName('TX_FALA').AsString;
        oPagina.ListaPersonagens.Last.Voz            := oSQLDataSet1.FieldByName('CD_VOZ').AsLargeInt;
        oPagina.ListaPersonagens.Last.Processado     := oSQLDataSet1.FieldByName('FL_PROCESSADO').AsString = 'S';
      end;

      oSQLDataSet1.Next;
    end;
    oSQLDataSet1.Close;
  finally
    oDicionarioPaginas.Free;
  end;
end;



procedure TDAOLeitorBook.SalvarCabecalho(const ALivro: TLivro);

  function GetSQL: String;
  begin
    Result := oInsert1.SQLWithValues.Replace(';', ' returning CD_SEQUENCIAL;')
  end;



begin
  oInsert1.Limpar(tsbUpSert);

  oInsert1.Add('TX_TITULO', ALivro.nome);
  oInsert1.Add('FL_LIDO', ALivro.lido.ToSN, [tsoConflict]);
  oInsert1.Add('FL_NORMALIZADO', ALivro.normalizado.ToSN, [tsoConflict]);
  oInsert1.Add('FL_NARRADOR', ALivro.narradorObtido.ToSN, [tsoConflict]);
  oInsert1.Add('FL_PRODUZIDO', ALivro.produzido.ToSN, [tsoConflict]);
  oInsert1.Add('DT_MANUTECAO', Now, [tsoConflict]);

  oInsert1.SetConflict(['TX_TITULO']);

  oInsert1.SetTabela('TB_LIVROCABECALHO');
  PrepararSQL(oSQLDataSet1, GetSQL);
  oSQLDataSet1.Open;
  while (not(oSQLDataSet1.Eof)) do
  begin
    ALivro.sequencial := oSQLDataSet1.FieldByName('CD_SEQUENCIAL').AsLargeInt;
    oSQLDataSet1.Next;
  end;

  oSQLDataSet1.Close;
end;



procedure TDAOLeitorBook.SalvarPagina(const ALivro: TLivro; const APagina: TPagina);
var
  oLivro: TLivro;
  oPersonagem, oPersonagemAux: TPersonagemFala;
  sPersonagens: string;
begin
  oLivro            := TLivro.Create(False);
  oLivro.sequencial := ALivro.sequencial;
  oLivro.Add(APagina);
  SalvarPaginas(oLivro);
  oLivro.Free;

end;



procedure TDAOLeitorBook.SalvarPaginas(const ALivro: TLivro);
var
  oPagina: TPagina;

  function GetSQL: String;
  begin
    Result := oInsert1.SQLWithValues.Replace(';', ' returning CD_SEQUENCIAL;')
  end;



begin
  for oPagina in ALivro do
  begin
    oInsert1.Limpar(tsbUpSert);
    if (oPagina.sequencial > 0) then
      oInsert1.Add('CD_SEQUENCIAL', oPagina.sequencial);

    oInsert1.Add('CD_SEQUENCIALLIVRO', ALivro.sequencial, [tsoConflict]);
    oInsert1.Add('NR_PAGINA', oPagina.Numero, [tsoConflict]);
    oInsert1.Add('TX_PAGINA', oPagina.Texto, [tsoConflict]);
    oInsert1.Add('FL_PROCESSADO', oPagina.Processado.ToSN, [tsoConflict]);
    oInsert1.Add('DT_MANUTECAO', Now, [tsoConflict]);
    oInsert1.SetConflict(['CD_SEQUENCIAL']);
    oInsert1.SetTabela('TB_LIVROPAGINA');
    PrepararSQL(oSQLDataSet1, GetSQL);
    oSQLDataSet1.Open;
    while (not(oSQLDataSet1.Eof)) do
    begin
      oPagina.sequencial := oSQLDataSet1.FieldByName('CD_SEQUENCIAL').AsLargeInt;
      oSQLDataSet1.Next;
    end;
    oSQLDataSet1.Close;
  end;
end;



procedure TDAOLeitorBook.SalvarPersonagens(const ALivro: TLivro);
var
  sPersonagens: string;
  oPersonagem: TPersonagemFala;

  function GetSQL: String;
  begin
    Result := oInsert1.SQLWithValues.Replace(';', ' returning CD_SEQUENCIAL;')
  end;



begin
  for sPersonagens in ALivro.GetPersonagens do
  begin
    oPersonagem := ALivro.GetPersonagem(sPersonagens)[0];

    oInsert1.Limpar(tsbUpSert);
    if (oPersonagem.sequencial > 0) then
      oInsert1.Add('CD_SEQUENCIAL', oPersonagem.sequencial);

    oInsert1.Add('CD_SEQUENCIALLIVRO', ALivro.sequencial, [tsoConflict]);
    oInsert1.Add('TX_PERSONAGEM', sPersonagens, [tsoConflict]);
    oInsert1.Add('TX_GENERO', oPersonagem.genero, [tsoConflict]);
    oInsert1.Add('TX_IDADE', oPersonagem.idade_aparente, [tsoConflict]);
    oInsert1.Add('CD_VOZ', oPersonagem.Voz, [tsoConflict]);
    oInsert1.Add('DT_MANUTECAO', Now, [tsoConflict]);
    oInsert1.SetConflict(['CD_SEQUENCIAL']);
    oInsert1.SetTabela('TB_LIVROPERSONAGENS');
    PrepararSQL(oSQLDataSet1, GetSQL);
    oSQLDataSet1.Open;
    while (not(oSQLDataSet1.Eof)) do
    begin
      for oPersonagem in ALivro.GetPersonagem(sPersonagens) do
        oPersonagem.sequencial := oSQLDataSet1.FieldByName('CD_SEQUENCIAL').AsLargeInt;
      oSQLDataSet1.Next;
    end;
    oSQLDataSet1.Close;
  end;
end;



procedure TDAOLeitorBook.SalvarFala(const ALivro: TLivro; const APagina: TPagina);
var
  oLivro: TLivro;
  oPersonagem, oPersonagemAux: TPersonagemFala;
  sPersonagens: string;
begin
  oLivro            := TLivro.Create(False);
  oLivro.sequencial := ALivro.sequencial;
  oLivro.Add(APagina);

  for sPersonagens in oLivro.GetPersonagens do
  begin
    oPersonagem := ALivro.GetPersonagem(sPersonagens)[0];
    for oPersonagemAux in ALivro.GetPersonagem(sPersonagens) do
    begin
      oPersonagemAux.sequencial := oPersonagem.sequencial;
    end;
  end;

  SalvarCabecalho(ALivro);
  SalvarPersonagens(oLivro);
  SalvarFalas(oLivro, False);

  oLivro.Free;
end;



procedure TDAOLeitorBook.SalvarFalas(const ALivro: TLivro; const ALimpar: Boolean = true);
var
  oPagina: TPagina;
  oPersonagem: TPersonagemFala;
begin
  if (ALimpar) then
  begin
    oDelete1.Limpar;
    oDelete1.AddWhere('CD_SEQUENCIALLIVRO', ALivro.sequencial);
    oDelete1.SetTabela('TB_LIVROFALAS');
    oConexao1.Execute(oDelete1.SQL(), oDelete1.Params());
  end;

  for oPagina in ALivro do
  begin
    for oPersonagem in oPagina.ListaPersonagens do
    begin
      oInsert1.Limpar;
      oInsert1.Add('CD_SEQUENCIALLIVRO', ALivro.sequencial);
      oInsert1.Add('CD_SEQUENCIALPAGINA', oPagina.sequencial);
      oInsert1.Add('CD_SEQUENCIALPERSONAGEM', oPersonagem.sequencial);
      oInsert1.Add('TX_FALA', oPersonagem.fala);
      oInsert1.Add('DT_MANUTECAO', Now);
      oInsert1.SetTabela('TB_LIVROFALAS');
      oConexao1.Execute(oInsert1.SQL(), oInsert1.Params());
    end;
  end;
end;

end.

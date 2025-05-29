unit Rgn.Leitor.Book.Abstract;

interface

uses
  System.Generics.Collections, Rgn.Leitor.IA.Http, System.Classes,
  DAO.Leitor.Book;

type
  TRgnLeitorBookAbstract = class(TInterfacedPersistent)
  protected
    oListaAPIs: TListaAPI;
    oIDAOLeitorBook: IDAOLeitorBook;
    function GetAPI(const ATipoAPI: TTipoAPI = ttaNenhum): IRgnLeitorIAHttp;
  public
    constructor Create;
    destructor Destroy; override;
  end;

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils, Leitor.IA.Response,
  Leitor.IA.Request, SynCommons, Winapi.Windows;



constructor TRgnLeitorBookAbstract.Create;
begin
  oIDAOLeitorBook := TDAOLeitorBook.Create;

  oListaAPIs := TListaAPI.Create;

  oIDAOLeitorBook.LocalizarAPIS(oListaAPIs);
end;



destructor TRgnLeitorBookAbstract.Destroy;
begin
  oListaAPIs.Free;
  inherited;
end;



function TRgnLeitorBookAbstract.GetAPI(const ATipoAPI: TTipoAPI): IRgnLeitorIAHttp;
var
  oIAPI: IRgnLeitorIAHttp;
  iIndice: Integer;
begin
  Result      := nil;
  for iIndice := Pred(oListaAPIs.Count) downto 0 do
  begin
    if (oListaAPIs[iIndice].Expirada) then
    begin
      oIDAOLeitorBook.AtualizarAPI(oListaAPIs[iIndice].GetKey);
      oListaAPIs.Delete(iIndice);
    end;
  end;

  if (oListaAPIs.Count = 0) then
  begin
    oIDAOLeitorBook.LocalizarAPIS(oListaAPIs);
  end;

  for oIAPI in oListaAPIs do
  begin
    if (oIAPI.Disponivel) then
    begin
      Exit(oIAPI);
    end;
  end;

  if ((ATipoAPI = ttaLocal) or (oListaAPIs.Count = 0)) and (ATipoAPI <> ttaOnline) then
  begin
    Result := TRgnLeitorIAHttp.Create(ATipoAPI);
    Exit;
  end;

  if (not(Assigned(Result))) then
  begin
    Writeln('Nenhuma API disponível. Aguardando reset...');
    Sleep(DEZ_SEGUNDOS);
    Result := GetAPI;
  end;
end;

end.

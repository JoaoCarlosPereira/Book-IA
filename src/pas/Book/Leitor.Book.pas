unit Leitor.Book;

interface

uses
  System.SysUtils,
  System.Classes,
  System.Generics.Collections;

type
  TPersonagemFala = class
  private
    FNome: string;
    FGenero: string;
    FIdadeAparente: string;
    FFala: string;
  public
    property nome: string read FNome write FNome;
    property genero: string read FGenero write FGenero;
    property idade_aparente: string read FIdadeAparente write FIdadeAparente;
    property fala: string read FFala write FFala;
  end;

  TListaPersonagensFalas = TObjectList<TPersonagemFala>;

  TPagina = class
  public
    Texto: string;
    ListaPersonagens: TListaPersonagensFalas;
    constructor Create;
    destructor Destroy; override;
  end;

  TLivro = TObjectList<TPagina>;

implementation




constructor TPagina.Create;
begin
  ListaPersonagens := TListaPersonagensFalas.Create;
end;



destructor TPagina.Destroy;
begin
  ListaPersonagens.Free;
  inherited;
end;

end.

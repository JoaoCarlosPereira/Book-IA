unit Rgn.Leitor.IA;

interface

uses
  System.Generics.Collections, System.SysUtils, System.Classes, OtlTask;

type
  IRgnLeitorIA = interface
    ['{AEE05A01-557E-4190-94CC-4CAE851A9ABE}']
  end;

  TRgnLeitorIA = class(TInterfacedPersistent, IRgnLeitorIA)
  private
    procedure ProcessarBooks(const ATask: IOmniTask);
  public
    constructor Create;
  end;

const
  ESPERA = 5000;
  DIRETORIO = '\\192.168.2.162\Dados\dsv\NLP\pdfs';

implementation

uses
  Rgn.Sistema.ThreadFactory, System.Types, System.IOUtils;



constructor TRgnLeitorIA.Create;
begin
  TRgnSistemaThreadFactory.CriarTarefaParalela(ProcessarBooks);
end;



procedure TRgnLeitorIA.ProcessarBooks(const ATask: IOmniTask);
var
  oLivrosPDF: TStringDynArray;
  sLivro: string;
begin
  oLivrosPDF := TDirectory.GetFiles(DIRETORIO + '\processar');
  for sLivro in oLivrosPDF do
  begin


    TFile.Move(sLivro, sLivro.Replace('processar', 'processado'));
  end;

  Sleep(ESPERA);
  if (not(ATask.CancellationToken.IsSignalled)) then
    ProcessarBooks(ATask);
end;

end.

program Leitor;

{$APPTYPE CONSOLE}

{$R *.res}

uses
  System.SysUtils,
  Rgn.Leitor.IA.Http in '..\pas\Rgn.Leitor.IA.Http.pas',
  Rgn.Sistema.WebService.Rest in 'D:\dsv-git\dsv-delphi\shared\Sistema\WebService\Rgn.Sistema.WebService.Rest.pas',
  Leitor.IA.Request in '..\pas\Leitor.IA.Request.pas',
  Leitor.IA.Response in '..\pas\Leitor.IA.Response.pas';

begin
  try
    { TODO -oUser -cConsole Main : Insert code here }
  except
    on E: Exception do
      Writeln(E.ClassName, ': ', E.Message);
  end;
end.

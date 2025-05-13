program LeitorTests;
{

  Delphi DUnit Test Project
  -------------------------
  This project contains the DUnit test framework and the GUI/Console test runners.
  Add "CONSOLE_TESTRUNNER" to the conditional defines entry in the project options
  to use the console test runner.  Otherwise the GUI test runner will be used by
  default.

}

{$IFDEF CONSOLE_TESTRUNNER}
{$APPTYPE CONSOLE}
{$ENDIF}




uses
  DBXDevartPostgreSQL,
  Forms,
  I.Lib.ExportaArquivo,
  TestFramework,
  GUITestRunner,
  TextTestRunner,
  SysmoSQL,
  OtlSync,
  Lib.ExportaArquivoTextFile,
  Lib.ExportaArquivoFactory,
  Lib.Serialize.Factory,
  Lib.Serialize.Enumerator,
  DateUtils,
  OtlTaskControl,
  OtlTask,
  OtlComm,
  Winapi.Windows,
  Winapi.Messages,
  Vcl.Controls,
  SynSQLite3Static,
  TestRgn.Leitor.IA.Http in '..\pas\TestRgn.Leitor.IA.Http.pas',
  Leitor.IA.Request in '..\..\src\pas\Leitor.IA.Request.pas',
  Leitor.IA.Response in '..\..\src\pas\Leitor.IA.Response.pas',
  Rgn.Leitor.IA.Http in '..\..\src\pas\Rgn.Leitor.IA.Http.pas',
  Rgn.Sistema.WebService.Rest in 'D:\dsv-git\dsv-delphi\shared\Sistema\WebService\Rgn.Sistema.WebService.Rest.pas';

{$R *.RES}




begin
  Application.Initialize;
  if IsConsole then
    TextTestRunner.RunRegisteredTests
  else
    GUITestRunner.RunRegisteredTests;
end.

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
  Rgn.Leitor.IA in '..\..\src\pas\Rgn.Leitor.IA.pas',
  Rgn.Sistema.ThreadUtils in '..\..\src\Shared\Sistema\Rgn.Sistema.ThreadUtils.pas',
  Rgn.Sistema.WebService.Rest in '..\..\src\Shared\Sistema\Rgn.Sistema.WebService.Rest.pas',
  Rgn.Sistema.ThreadFactory in '..\..\src\Shared\Sistema\Rgn.Sistema.ThreadFactory.pas',
  Rgn.Leitor.Book in '..\..\src\pas\Book\Rgn.Leitor.Book.pas',
  Leitor.Book in '..\..\src\pas\Book\Leitor.Book.pas',
  Rgn.Leitor.PDF in '..\..\src\pas\PDF\Rgn.Leitor.PDF.pas',
  Rgn.Leitor.IA.Http in '..\..\src\pas\Rgn.Leitor.IA.Http.pas',
  Rgn.Leitor.Book.Personagens in '..\..\src\pas\Book\Personagens\Rgn.Leitor.Book.Personagens.pas',
  Rgn.Leitor.Book.Narrador in '..\..\src\pas\Book\Narrador\Rgn.Leitor.Book.Narrador.pas',
  Rgn.Leitor.Book.Abstract in '..\..\src\pas\Book\Rgn.Leitor.Book.Abstract.pas',
  DAO.Leitor.Book in '..\..\src\pas\Book\DAO.Leitor.Book.pas',
  Padrao.DAO in '..\..\..\shared\Padrao\DAO\Padrao.DAO.pas',
  Sistema.Retorno in '..\..\..\shared\shared\Sistema\Sistema.Retorno.pas',
  I.Sistema.Retorno in '..\..\..\shared\shared\Sistema\I.Sistema.Retorno.pas',
  Rgn.Leitor.Book.Vozes in '..\..\src\pas\Book\Vozes\Rgn.Leitor.Book.Vozes.pas',
  Rgn.Leitor.Book.VozesHttp in '..\..\src\pas\Book\Vozes\Rgn.Leitor.Book.VozesHttp.pas';

{$R *.RES}




begin
  Application.Initialize;
  if IsConsole then
    TextTestRunner.RunRegisteredTests
  else
    GUITestRunner.RunRegisteredTests;
end.

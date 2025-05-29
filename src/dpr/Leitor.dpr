program Leitor;

{$APPTYPE CONSOLE}

{$R *.res}


uses
  DBXDevartPostgreSQL,
  System.SysUtils,
  Rgn.Leitor.Book.Personagens in '..\pas\Book\Personagens\Rgn.Leitor.Book.Personagens.pas',
  Rgn.Leitor.Book in '..\pas\Book\Rgn.Leitor.Book.pas',
  Rgn.Leitor.Book.Abstract in '..\pas\Book\Rgn.Leitor.Book.Abstract.pas',
  DAO.Leitor.Book in '..\pas\Book\DAO.Leitor.Book.pas',
  Rgn.Leitor.Book.Narrador in '..\pas\Book\Narrador\Rgn.Leitor.Book.Narrador.pas',
  Rgn.Leitor.PDF in '..\pas\PDF\Rgn.Leitor.PDF.pas',
  Leitor.Book in '..\pas\Book\Leitor.Book.pas',
  Rgn.Leitor.IA.Http in '..\pas\Rgn.Leitor.IA.Http.pas',
  Leitor.IA.Request in '..\pas\Leitor.IA.Request.pas',
  Rgn.Sistema.WebService.Rest in '..\Shared\Sistema\Rgn.Sistema.WebService.Rest.pas',
  Leitor.IA.Response in '..\pas\Leitor.IA.Response.pas',
  Rgn.Sistema.ThreadUtils in '..\Shared\Sistema\Rgn.Sistema.ThreadUtils.pas',
  Rgn.Sistema.Mensagens.Externas in '..\Shared\Sistema\Rgn.Sistema.Mensagens.Externas.pas',
  Sistema.Singleton in '..\Shared\Sistema\Sistema.Singleton.pas',
  Rgn.Sistema.ThreadFactory in '..\Shared\Sistema\Rgn.Sistema.ThreadFactory.pas',
  Padrao.DAO in '..\..\..\shared\Padrao\DAO\Padrao.DAO.pas',
  Sistema.Retorno in '..\..\..\shared\shared\Sistema\Sistema.Retorno.pas',
  I.Sistema.Retorno in '..\..\..\shared\shared\Sistema\I.Sistema.Retorno.pas',
  EnumeradorTipoDeCliente in '..\..\..\shared\Enumerador\EnumeradorTipoDeCliente.pas',
  System.Classes;

begin
  try
    TRgnLeitorBook.Create.Ref.MonitorarNovosBooks;
  except
    on E: Exception do
    begin
      Writeln(E.ClassName, ': ', E.Message);
      with TStringList.Create do
      begin
        Add(E.Message + '|' + E.ClassName + '|' + E.StackTrace);
        SaveToFile('LogErro.log');
        Free;
      end;
    end;
  end;

end.

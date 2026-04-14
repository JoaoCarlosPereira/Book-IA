program Leitor;

{$APPTYPE CONSOLE}

{$R *.res}


uses
  madExcept,
  madLinkDisAsm,
  madListHardware,
  madListProcesses,
  madListModules,
  DBXDevartPostgreSQL,
  System.SysUtils,
  System.IOUtils,
  System.Classes,
  Winapi.Windows,
  Winapi.ShellAPI,
  System.Types,
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
  Sistema.Retorno in '..\..\..\shared\Sistema\Sistema.Retorno.pas',
  I.Sistema.Retorno in '..\..\..\shared\Sistema\I.Sistema.Retorno.pas',
  EnumeradorTipoDeCliente in '..\..\..\shared\Enumerador\EnumeradorTipoDeCliente.pas',
  Rgn.Leitor.Book.Vozes in '..\pas\Book\Vozes\Rgn.Leitor.Book.Vozes.pas',
  Rgn.Leitor.Book.VozesHttp in '..\pas\Book\Vozes\Rgn.Leitor.Book.VozesHttp.pas';



procedure RestartSelf;
var
  Params: string;
begin
  // Reconstroi a linha de comando com os parâmetros originais
  Params := '';
  if ParamCount > 0 then
    Params := GetCommandLine;

  // Executa uma nova instância do programa
  ShellExecute(0, nil, PChar('C:\Leitor\Leitor.exe'), nil, nil, SW_SHOWNORMAL);

  // Fecha a instância atual
  Halt(0);
end;



procedure Monitorar;
var
  oArquivos: TStringDynArray;
  sArquivo: string;
  dTempo: TTime;
const
  DiretorioPDFS = 'S:\dsv\NLP\pdfs\processar';
begin
  if (DirectoryExists(DiretorioPDFS)) then
  begin
    try
      oArquivos := [];
      if (not(TDAOLeitorBook.Create.Ref.LocalizarLivrosPendentes(oArquivos))) then
      begin
        Writeln('Procurando PDFs no diretório: ' + DiretorioPDFS);
        oArquivos := TDirectory.GetFiles(DiretorioPDFS);
        for sArquivo in oArquivos do
        begin
          if (not(sArquivo.ToLower.Contains('.pdf'))) then
          begin
            TFile.Delete(sArquivo);
          end;
        end;
        oArquivos := TDirectory.GetFiles(DiretorioPDFS);
      end;

      if (Length(oArquivos) = 0) then
      begin
        Writeln('Nenhum livro para a processar. Aguardando 1m...');
        Sleep(UM_MINUTO);
        Monitorar;
        Exit;
      end;

      for sArquivo in oArquivos do
      begin
        if (not(sArquivo.ToLower.Contains('.pdf'))) then
        begin
          Continue;
        end;

        dTempo := Now;
        Writeln('Processando livro: ' + ExtractFileName(sArquivo));

        TRgnLeitorBook.Create.Ref.ProcessarBook(sArquivo);

        if (FileExists(sArquivo)) then
        begin
          if (not(FileExists(sArquivo.Replace('processar', 'processado')))) then
            TFile.Copy(sArquivo, sArquivo.Replace('processar', 'processado'));
        end;

        if (FileExists(sArquivo.ToLower.Replace('pdf', 'txt'))) then
          TFile.Delete(sArquivo.ToLower.Replace('pdf', 'txt'));

        if (FileExists(sArquivo)) then
          TFile.Delete(sArquivo);

        Writeln('Finalizado, Tempo de processamento: ' + TimeToStr(Now - dTempo));
        Writeln('Reiniciando a busca em 10s.');
        Sleep(DEZ_SEGUNDOS);
        Exit;
      end;
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
  end
  else
  begin
    Writeln('Diretório: "' + DiretorioPDFS + '" Não existe');
  end;
end;



begin
  try
    try
      Monitorar;
    finally
      RestartSelf;
    end;
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

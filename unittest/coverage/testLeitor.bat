@echo off
C:\dsv-git\dsv-delphi\sysmos1-modular\Fiscal\DRCST\unittests\coverage\CodeCoverage_win32_1.0_RC11\CodeCoverage.exe -e C:\dsv-git\dsv-delphi\sysmos1-modular\Fiscal\DRCST\unittests\exe\DRCSTTests.exe -m C:\dsv-git\dsv-delphi\sysmos1-modular\Fiscal\DRCST\unittests\exe\DRCSTTests.map -uf C:\dsv-git\dsv-delphi\sysmos1-modular\Fiscal\DRCST\unittests\coverage\list_units.txt -spf C:\dsv-git\dsv-delphi\sysmos1-modular\Fiscal\DRCST\unittests\coverage\list_paths.txt -od emma -emma -meta -xml -html
if "%1" == "" (
pause
cd emma
call start CodeCoverage_summary.html
)
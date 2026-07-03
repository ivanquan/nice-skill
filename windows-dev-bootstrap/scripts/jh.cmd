@echo off
%1 mshta vbscript:CreateObject("Shell.Application").ShellExecute("cmd.exe","/c %~s0 ::","","runas",1)(window.close)&&exit
ping /n 1 127.0.0.1 >nul
chcp 936
For /f "tokens=2,*" %%i in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v "Desktop"') do Set dt=%%j
mshta vbscript:msgbox("你好 请先关闭需要激活的软件 然后点击“确定”继续",6,"兔桔科技")(window.close)
ping /n 2 127.0.0.1 >nul
ECHO 开始放置激活所需文件...
echo f|xcopy /r /c /h /q /s /e /i /y "%~dp0"micool_config\_auto  %windir%
ping /n 2 127.0.0.1 >nul 
ECHO 开始逐个激活...
ping /n 2 127.0.0.1 >nul
ECHO 正在激活所有2017版本...
ping /n 2 127.0.0.1 >nul
ECHO 正在激活所有2018版本...
ping /n 2 127.0.0.1 >nul
ECHO 正在激活所有2019版本...
call echo d|xcopy /r /c /h /q /s /e /y "%~dp0"micool_config\JetBrainsold %HOMEPATH% 2>nul
ping /n 2 127.0.0.1 >nul
ECHO 正在激活所有2020版本...
ping /n 2 127.0.0.1 >nul
ECHO 正在激活所有2021版本...
ping /n 2 127.0.0.1 >nul
ECHO 正在激活所有2022版本...
call echo d|xcopy /r /c /h /q /s /e /y "%~dp0"micool_config\JetBrains %appdata%\JetBrains 2>nul
ping /n 3 127.0.0.1 >nul
@echo off
echo "请注意你的杀毒软件提示，一定要允许"
@echo  ########################################
@xcopy C:\Windows\system32\drivers\etc\hosts C:\Windows\system32\drivers\etc\hosts.bak\ /d /c /i /y 
@echo  ########################################
ECHO 激活成功！
set msg="恭喜已经成功激活！\n打开软件生效\n如果未激活成功的话\n请看教程里的备用方案"
mshta vbscript:msgbox(Replace(%msg%,"\n",vbCrLf),6,"兔桔科技")(window.close)
pauses
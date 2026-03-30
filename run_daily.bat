@echo off
REM SENTINEL2 Daily Pipeline — Scheduled for 0600 GMT
cd /d "C:\Users\Preston\Desktop\Sentinal2"

REM Log start
echo [%date% %time%] Pipeline starting >> logs\scheduler.log

REM Run pipeline
"C:\Users\Preston\AppData\Local\Programs\Python\Python312\python.exe" -m src.pipeline -v >> logs\pipeline_%date:~-4%%date:~4,2%%date:~7,2%.log 2>&1

REM Log completion
echo [%date% %time%] Pipeline finished (exit code %ERRORLEVEL%) >> logs\scheduler.log

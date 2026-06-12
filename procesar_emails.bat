@echo off
:loop
cd /d C:\Users\ingdi\Downloads\correspondencia\07-04
call venv\Scripts\activate
python manage.py procesar_emails_seguro
deactivate
timeout /t 300 /nobreak
goto loop 
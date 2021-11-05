@echo off
REM python must be present in the system's path; python 3.9 @64 bit is recommended
echo Setting up the venv...
python -m venv venv
echo Copying the requirements.txt into the venv
copy requirements.txt venv\\Scripts\\requirements.txt
echo venv setup completed, Now installing the required libs ...
cd venv\\Scripts
activate & pip install -r requirements.txt & echo venv installation COMPLETED & timeout /t -1 & exit
pause
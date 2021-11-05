@echo off
cd venv\\Scripts
activate & cd ../../ & python willow.py %* & timeout /t -1 & exit
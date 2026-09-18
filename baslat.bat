@echo off
chcp 65001 > nul
title İş Arama Asistanı

echo ======================================================
echo          📋 İŞ ARAMA ASİSTANI BAŞLATILIYOR
echo ======================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Sanal ortam (.venv) oluşturuluyor...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo HATA: Python bulunamadı! Lütfen Python 3.10+ kurulu olduğundan emin olun.
        pause
        exit /b %errorlevel%
    )
    echo [2/2] Gerekli paketler yükleniyor...
    .venv\Scripts\pip install -r requirements.txt
)

echo.
echo Uygulama açılıyor: http://localhost:8501
echo Kapatmak için bu pencerede Ctrl+C tuşlarına basabilirsiniz.
echo.

.venv\Scripts\python.exe -m streamlit run streamlit_app.py

pause

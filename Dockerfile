FROM python:3.11-slim

WORKDIR /app

# jobspy/pandas için derleme araçları gerektiren bazı bağımlılıklar olabilir
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Kişisel veriler (profil, iş veritabanı) konteyner dışında (volume) kalıcı olsun
VOLUME ["/app/data"]

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]

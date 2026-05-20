FROM python:3.11-slim

# ffmpeg pour faster-whisper, gcc/cmake pour pymeshfix/fast-simplification
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    g++ \
    cmake \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances d'abord (layer cachée si requirements.txt ne change pas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY . .

# Créer les dossiers persistants s'ils n'existent pas
RUN mkdir -p mission_logs stl_output research_logs session_logs

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

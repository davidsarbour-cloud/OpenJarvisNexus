FROM python:3.11-slim

# System deps: ffmpeg (whisper), gcc/cmake (meshfix), Playwright browser deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    g++ \
    cmake \
    libgl1 \
    libglib2.0-0 \
    curl \
    git \
    # Playwright / Chromium headless deps
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxfont2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (layer cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's Chromium browser binary
RUN python -m playwright install chromium

# blogwatcher-cli (Go binary — skill dependency)
RUN curl -sL https://github.com/JulienTant/blogwatcher-cli/releases/latest/download/blogwatcher-cli_linux_amd64.tar.gz \
    | tar xz -C /usr/local/bin blogwatcher-cli \
    && chmod +x /usr/local/bin/blogwatcher-cli

# Application source
COPY . .

# Persistent runtime dirs
RUN mkdir -p mission_logs stl_output research_logs session_logs

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Shared image for every Mining service — the command differs per service
# (see docker-compose.mining.yml). One image keeps the shared strategy code
# byte-identical across market-data / workers / risk-manager / backtester.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.mining.txt .
RUN pip install --no-cache-dir -r requirements.mining.txt

COPY . .

# Default: orchestrator. Overridden by `command:` in compose for other services.
CMD ["uvicorn", "services.orchestrator.main:app", "--host", "0.0.0.0", "--port", "8090"]

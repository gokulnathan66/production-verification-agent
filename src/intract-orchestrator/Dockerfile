FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY src/intract-orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/intract-orchestrator/ .

# Copy frontend files
COPY frontend /frontend

EXPOSE 8006

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8006"]

FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY src/app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/app/ .

# Copy frontend files
COPY frontend /frontend

EXPOSE 8006

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8006"]

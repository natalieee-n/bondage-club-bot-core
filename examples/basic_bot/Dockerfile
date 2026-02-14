FROM python:3.11.9-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir . \
    && pip install --no-cache-dir -r examples/basic_bot/requirements.txt

CMD ["python", "examples/basic_bot/main.py"]

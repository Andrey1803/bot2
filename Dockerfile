FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала копируем зависимости, чтобы они кэшировались
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Затем копируем весь проект
COPY . .

CMD ["python", "main.py"]

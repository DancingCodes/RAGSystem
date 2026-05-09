FROM python:3.12-slim

WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10005

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10005", "--workers", "1"]

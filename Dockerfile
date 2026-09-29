FROM python:3.14-slim
LABEL authors="Loup Letac, ing - 3E ing"

WORKDIR /intern-app
ENV PYTHONPATH=/intern-app/apps \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=debug

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "gunicorn>=23,<24"

COPY . .

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--error-logfile", "-", "main:intern_app"]

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

RUN adduser --disabled-password --no-create-home appuser
RUN mkdir -p /app/staticfiles /app/media && chown -R appuser:appuser /app/staticfiles /app/media
USER appuser

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "barberia.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]

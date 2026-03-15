# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml .
COPY packages packages
COPY apps apps
COPY services services
COPY samples samples
RUN pip install --no-cache-dir .

FROM python:3.11-slim AS runtime
RUN adduser --disabled-password --gecos "" appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY packages packages
COPY apps apps
COPY services services
COPY samples samples
USER appuser
EXPOSE 8080
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8080"]

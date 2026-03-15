# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

FROM python:3.11-slim AS runtime
RUN adduser --disabled-password --gecos "" appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY packages packages
COPY services services
USER appuser
EXPOSE 8093
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "uvicorn", "services.a2a_cmdb_agent.server:app", "--host", "0.0.0.0", "--port", "8093"]

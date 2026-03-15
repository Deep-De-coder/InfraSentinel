# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY packages packages
COPY apps apps
COPY services services
COPY samples samples
ENV PYTHONUNBUFFERED=1
# Run as root so we can create /app/.data/evidence when volume mounts (dev mode)
CMD ["python", "-m", "apps.worker.main"]

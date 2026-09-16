# syntax=docker/dockerfile:1.7
FROM python:3.15.0rc2-alpine3.24 AS builder
WORKDIR /app
RUN apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev
COPY requirements.txt .
RUN python -m venv /opt/venv
RUN --mount=type=cache,target=/root/.cache/pip \
    /opt/venv/bin/pip install --disable-pip-version-check -r requirements.txt

FROM python:3.15.0rc2-alpine3.24
WORKDIR /app
RUN apk add --no-cache libstdc++
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY app.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

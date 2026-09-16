FROM python:3.12-alpine
WORKDIR /app
RUN apk add --no-cache libstdc++ \
    && apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps
COPY app.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

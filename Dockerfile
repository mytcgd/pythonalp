FROM python:3.10-alpine

WORKDIR /app

COPY app.py requirements.txt /app/

ARG PORT=${PORT:-'3000'}
EXPOSE $PORT

RUN apk update && apk add --no-cache bash wget curl procps &&\
    chmod +x app.py &&\
    pip install -r requirements.txt

HEALTHCHECK --interval=2m --timeout=30s CMD curl --fail http://localhost/healthcheck || exit 1

CMD ["python3", "/app/app.py"]

FROM python:3.10-alpine

WORKDIR /app

COPY requirements.txt /app
RUN apk update && \
    apk add --no-cache bash wget curl procps && \
    pip install --no-cache-dir -r requirements.txt

COPY app.py ./

EXPOSE 3000

ENTRYPOINT [ "python3", "app.py" ]

FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN mkdir -p data/sst

EXPOSE 6379

ENV KV_HOST=0.0.0.0

CMD ["python", "-m", "kvstore.server"]

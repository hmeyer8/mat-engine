git FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal32 libgdal-dev build-essential curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    numpy shapely rasterio pystac-client planetary-computer psycopg2-binary

COPY ingest_s2.py /app/ingest_s2.py
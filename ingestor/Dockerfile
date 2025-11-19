FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Minimal system deps; rely on manylinux wheels for rasterio/shapely/pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates libexpat1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    numpy shapely rasterio pillow pystac-client planetary-computer

COPY ingest_s2.py /app/ingest_s2.py

ENTRYPOINT ["python", "-u", "/app/ingest_s2.py"]

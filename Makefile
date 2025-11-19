PYTHON ?= python
FIELD ?= demo-field
ZIP ?= 68430
START ?= 2022-01-01
END ?= 2023-01-01

.PHONY: setup ingest preprocess svd overlay pipeline api ui lint test clean

setup:
	$(PYTHON) -m venv .venv
	. .\.venv\Scripts\activate && pip install --upgrade pip && pip install -r requirements.txt

ingest:
	$(PYTHON) -m src.ingest.run_ingest $(FIELD) $(ZIP) $(START) $(END)

preprocess:
	$(PYTHON) -m src.preprocessing.run_preprocessing $(FIELD)

svd:
	$(PYTHON) -m src.temporal_svd.run_svd $(FIELD)

overlay:
	$(PYTHON) -m src.analysis.build_overlay $(FIELD)

pipeline: ingest preprocess svd overlay

api:
	uvicorn src.api.main:app --reload --host $${MAT_API_HOST:-0.0.0.0} --port $${MAT_API_PORT:-8080}

ui:
	cd ui && npm install && npm run dev

lint:
	$(PYTHON) -m pytest --collect-only

test:
	$(PYTHON) -m pytest -q

clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache .venv data/raw/* data/processed/*

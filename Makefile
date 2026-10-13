# One-command workflows. On Windows, run these from Git Bash, or run the
# commands under each target by hand (use .venv/Scripts/ instead of .venv/bin/).
PY ?= python3
VENV := .venv
BIN := $(VENV)/bin
ifeq ($(OS),Windows_NT)
  BIN := $(VENV)/Scripts
endif

.PHONY: setup data test lint format index agent serve site clean

setup:            ## create the venv and install runtime + dev dependencies
	$(PY) -m venv $(VENV)
	$(BIN)/python -m pip install -r requirements-dev.txt

data:             ## regenerate data/processed from the seed table
	$(BIN)/python data/scripts/data_pipeline.py

test:             ## run the test suite
	$(BIN)/python -m pytest

lint:             ## lint and check formatting
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

format:           ## auto-fix lint issues and format
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

index:            ## create the Elasticsearch indices and load the data (needs .env)
	$(BIN)/python data/scripts/create_indices.py --recreate
	$(BIN)/python data/scripts/bulk_index.py

agent:            ## run the ADK chat UI at http://localhost:8000 (needs .env + indexed data)
	$(BIN)/adk web agents/

site:             ## build the static demo site into _site/
	rm -rf _site && mkdir -p _site/data
	cp -r frontend/. _site/
	cp data/processed/*.json _site/data/

serve: site       ## preview the static demo at http://localhost:8080
	$(BIN)/python -m http.server 8080 --directory _site

clean:
	rm -rf _site .pytest_cache .ruff_cache

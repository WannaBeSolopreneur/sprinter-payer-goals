.PHONY: all venv generate dbt export

PYTHON := .venv/bin/python
export PAYER_DB_PATH := $(CURDIR)/data/payer.duckdb
export DBT_PROFILES_DIR := $(CURDIR)/dbt
export DBT_SEND_ANONYMOUS_USAGE_STATS := false

all: export

.venv/bin/python: requirements.txt
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.txt

venv: .venv/bin/python

generate: venv
	$(PYTHON) -m payer_model.generate

dbt: generate
	cd dbt && ../.venv/bin/dbt build --profiles-dir .

export: dbt
	$(PYTHON) -m payer_model.export_site

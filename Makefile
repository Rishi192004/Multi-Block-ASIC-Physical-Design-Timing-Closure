# EDA-Genius Makefile
# Requires WSL Ubuntu-22.04 with Yosys, OpenROAD and sky130A PDK installed.

WSL       := wsl.exe -d Ubuntu-22.04 --
PROJ_WSL  := /opt/cad_ai
PYTHON    := python3
PYTEST    := python3 -m pytest
YOSYS     := /usr/bin/yosys
OR_BIN    := /opt/eda_env/bin/openroad
PDK       := sky130hd

.PHONY: help setup symlink test test-unit test-integration lint \
        run-all run-pd clean-artifacts clean-runs

help:
	@echo "EDA-Genius — Available targets:"
	@echo "  make setup          Install Python deps in WSL"
	@echo "  make symlink        (Re)create /opt/cad_ai -> project symlink in WSL"
	@echo "  make test           Run full test suite (unit + integration)"
	@echo "  make test-unit      Run unit tests only"
	@echo "  make test-integration  Run integration tests (needs tools)"
	@echo "  make lint           Run ruff linter"
	@echo "  make run-all        Synthesize all 5 benchmarks (generic PDK)"
	@echo "  make run-pd         Synthesize + place all 5 benchmarks (sky130hd)"
	@echo "  make clean-runs     Remove all run artifacts"
	@echo "  make clean-artifacts Remove all reports and run artifacts"

## ── Environment setup ────────────────────────────────────────────────────────

symlink:
	$(WSL) bash -c "sudo ln -sfn '/mnt/c/Users/Lenovo/Desktop/CAD_AI PROJEC' /opt/cad_ai && echo 'Symlink OK'"

setup:
	$(WSL) bash -c "cd $(PROJ_WSL) && pip3 install pytest pydantic pyyaml sqlalchemy 2>&1 | tail -5"

## ── Tests ────────────────────────────────────────────────────────────────────

test:
	$(WSL) bash -c "cd $(PROJ_WSL) && $(PYTEST) tests/ -v --tb=short 2>&1"

test-unit:
	$(WSL) bash -c "cd $(PROJ_WSL) && $(PYTEST) tests/unit/ -v --tb=short 2>&1"

test-integration:
	$(WSL) bash -c "cd $(PROJ_WSL) && $(PYTEST) tests/integration/ -v --tb=short 2>&1"

test-sky130:
	$(WSL) bash -c "cd $(PROJ_WSL) && $(PYTEST) tests/integration/test_yosys_sky130.py -v --tb=short 2>&1"

test-pd:
	$(WSL) bash -c "cd $(PROJ_WSL) && $(PYTEST) tests/integration/test_openroad_placement.py -v --tb=short 2>&1"

## ── Lint ─────────────────────────────────────────────────────────────────────

lint:
	$(WSL) bash -c "cd $(PROJ_WSL) && python3 -m ruff check src/ tests/ --fix 2>&1 || true"

## ── EDA runs ─────────────────────────────────────────────────────────────────

run-all:
	$(WSL) bash -c "cd $(PROJ_WSL) && $(PYTHON) scripts/run_flow.py --all-benchmarks --pdk generic 2>&1"

run-pd:
	$(WSL) bash -c "cd $(PROJ_WSL) && $(PYTHON) scripts/run_flow.py --all-benchmarks --pdk sky130hd --run-pd 2>&1"

run-alu:
	$(WSL) bash -c "cd $(PROJ_WSL) && $(PYTHON) scripts/run_flow.py --design alu --pdk sky130hd --run-pd 2>&1"

run-uart:
	$(WSL) bash -c "cd $(PROJ_WSL) && $(PYTHON) scripts/run_flow.py --design uart_tx --pdk sky130hd --run-pd 2>&1"

## ── Cleanup ──────────────────────────────────────────────────────────────────

clean-runs:
	$(WSL) bash -c "rm -rf $(PROJ_WSL)/artifacts/runs/run_* && echo 'Runs cleaned'"

clean-artifacts:
	$(WSL) bash -c "rm -rf $(PROJ_WSL)/artifacts/runs/run_* $(PROJ_WSL)/artifacts/reports/*.csv $(PROJ_WSL)/artifacts/reports/*.json && echo 'Artifacts cleaned'"

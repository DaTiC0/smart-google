.PHONY: run test health check-paths install-hooks

PYTHON ?= python3

ifeq ($(wildcard .venv/bin/python),.venv/bin/python)
PYTHON := .venv/bin/python
endif

run:
	$(PYTHON) app.py

test:
	@if $(PYTHON) -m pytest --version >/dev/null 2>&1; then \
		$(PYTHON) -m pytest -q; \
		code=$$?; \
		if [ $$code -eq 5 ]; then echo "No tests discovered"; exit 0; fi; \
		exit $$code; \
	else \
		$(PYTHON) -m unittest discover -s tests -v; \
		code=$$?; \
		if [ $$code -eq 5 ]; then echo "No tests discovered"; exit 0; fi; \
		exit $$code; \
	fi

health:
	bash scripts/health_check.sh

check-paths:
	bash scripts/check_absolute_paths.sh

install-hooks:
	bash scripts/install_git_hooks.sh

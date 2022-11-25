.PHONY: setup
setup:
	python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

.PHONY: lint
lint:
	flake8

.PHONY: runserver
runserver:
	uvicorn tips.main:app --reload

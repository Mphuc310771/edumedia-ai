.PHONY: help install run stop test api deploy lint clean

help:
	@echo AgentSys commands: install, run, stop, test, api, deploy, lint, clean

install:
	pip install -r requirements.txt
	cd gallery_web && npm install

run:
	docker compose up --build

stop:
	docker compose down

api:
	python -m uvicorn apps.api.main:app --reload --port 8000

test:
	pytest tests/ -v --cov=apps --cov=pipeline --cov-fail-under=80 --cov-report=term-missing

lint:
	python -m py_compile apps/api/main.py
	python -m py_compile apps/lambda_handlers/ingest.py
	python -m py_compile pipeline/aggregator_lambda.py

clean:
	@echo Cleaning build artifacts...
	rm -rf .pytest_cache __pycache__ .coverage .htmlcov
	rm -rf apps/__pycache__ apps/**/__pycache__
	rm -rf config/__pycache__ pipeline/__pycache__ tests/__pycache__
	rm -rf gallery_web/dist pack/
	rm -rf report/public/ report/.hugo_build.lock

deploy:
	python scripts/deploy_stack.py

.PHONY: help install run stop test api deploy

help:
	@echo AgentSys commands: install, run, stop, test, api, deploy

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
	pytest tests/ -v --cov=apps --cov-fail-under=60 --cov-report=term-missing

deploy:
	sam deploy --template-file infra/template.yaml --guided --capabilities CAPABILITY_IAM

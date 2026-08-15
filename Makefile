.PHONY: backend-install frontend-install dev-backend dev-frontend build-frontend copy-frontend test-backend test-frontend migrate seed-demo sam-build sam-deploy

backend-install:
	python -m pip install -r backend/requirements.txt

frontend-install:
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev -- --host 127.0.0.1

build-frontend:
	cd frontend && npm run build

copy-frontend:
	python backend/scripts/copy_frontend.py

test-backend:
	cd backend && python -m pytest

test-frontend:
	cd frontend && npm run test

migrate:
	python backend/scripts/migrate.py

seed-demo:
	python backend/scripts/seed_demo.py

sam-build: build-frontend copy-frontend
	sam build

sam-deploy:
	sam deploy --guided

up:
	docker compose up -d
build:
	docker compose build
logs:
	docker compose logs --tail=100
ps:
	docker compose ps
test:
	cd backend && pytest -q
lint:
	cd backend && ruff check app tests

.PHONY: up down build logs shell migrate makemigrations

up:
	docker-compose up

down:
	docker-compose down

build:
	docker-compose up --build

logs:
	docker-compose logs -f web

shell:
	docker-compose exec web python manage.py shell

migrate:
	docker-compose exec web python manage.py migrate

makemigrations:
	docker-compose exec web python manage.py makemigrations

PYTHON=python3.8
DJANGO_MANAGE=api/manage.py
ENV_DIR=.$(PYTHON)_env
IN_ENV=. $(ENV_DIR)/bin/activate

env-dev:
	$(eval include env/.env.dev)
	$(eval export $(shell sed 's/=.*//' env/.env.dev))

env-prod:
	$(eval include env/.env.prod)
	$(eval export $(shell sed 's/=.*//' env/.env.prod))

env-sub: env-prod
	envsubst < "docker-compose.prod.yml" > "docker-compose.yml"

celery: env-dev
	$(IN_ENV) && cd api && celery -A config worker --beat -l info -S django

deploy-prod: env-prod env-sub
	echo "Building ${ENVIRONMENT} Environment"
	docker-compose up --build -d

build-python:
	virtualenv -p $(PYTHON) $(ENV_DIR)
	$(IN_ENV) && pip3 install -r api/requirements.txt

backend-serve: env-dev migrations
	$(IN_ENV) && python $(DJANGO_MANAGE) runserver

run-django-scripts: env-dev
	@$(IN_ENV) && python $(DJANGO_MANAGE) runscript initialize_stations
	@$(IN_ENV) && python $(DJANGO_MANAGE) runscript query_madis

migrations: env-dev
	$(IN_ENV) && python $(DJANGO_MANAGE) makemigrations --noinput
	$(IN_ENV) && python $(DJANGO_MANAGE) migrate --noinput

flush-the-database-yes-really: env-dev
	$(IN_ENV) && python $(DJANGO_MANAGE) flush

encrypt-dotenv:
	tar -c env/ | gpg --symmetric -c -o env.tar.gpg

# decrypt-dotenv:
# 	gpg --quiet --batch --yes --decrypt --passphrase=foo env.tar.gpg | tar -x
# 	rm env.tar.gpg

env-clean:
	@rm -rf $(ENV_DIR)
	@rm -rf .pytest_cache
	@echo "Environment cleaned."

# /!\ /!\ /!\ /!\ /!\ /!\ /!\ DISCLAIMER /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\
#
# This Makefile is only meant to be used for DEVELOPMENT purpose as we are
# changing the user id that will run in the container.
#
# PLEASE DO NOT USE IT FOR YOUR CI/PRODUCTION/WHATEVER...
#
# /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\ /!\
#
# Note to developers:
#
# While editing this file, please respect the following statements:
#
# 1. Every variable should be defined in the ad hoc VARIABLES section with a
#    relevant subsection
# 2. Every new rule should be defined in the ad hoc RULES section with a
#    relevant subsection depending on the targeted service
# 3. Rules should be sorted alphabetically within their section
# 4. When a rule has multiple dependencies, you should:
#    - duplicate the rule name to add the help string (if required)
#    - write one dependency per line to increase readability and diffs
# 5. .PHONY rule statement should be written after the corresponding rule
# ==============================================================================
# VARIABLES

include env.d/development/localtunnel

BOLD := \033[1m
RESET := \033[0m
GREEN := \033[1;32m


# -- Database

DB_HOST            = postgresql
DB_PORT            = 5432

# -- Docker
# Get the current user ID to use for docker run and docker exec commands
DOCKER_UID          = $(shell id -u)
DOCKER_GID          = $(shell id -g)
DOCKER_USER         = $(DOCKER_UID):$(DOCKER_GID)
COMPOSE             = DOCKER_USER=$(DOCKER_USER) docker compose
COMPOSE_EXEC        = $(COMPOSE) exec
COMPOSE_EXEC_APP    = $(COMPOSE_EXEC) app-dev
COMPOSE_RUN         = $(COMPOSE) run --rm
COMPOSE_RUN_APP     = $(COMPOSE_RUN) app-dev
COMPOSE_RUN_ADMIN   = $(COMPOSE_RUN) admin-dev
COMPOSE_RUN_MAIL    = $(COMPOSE_RUN) mail-generator
COMPOSE_RUN_CROWDIN = $(COMPOSE_RUN) crowdin crowdin
WAIT_DB             = @$(COMPOSE_RUN) dockerize -wait tcp://$(DB_HOST):$(DB_PORT) -timeout 60s

# -- Backend
MANAGE                 = $(COMPOSE_RUN_APP) python manage.py

# -- Frontend
MAIL_YARN = $(COMPOSE_RUN_MAIL) yarn
ADMIN_YARN = $(COMPOSE_RUN_ADMIN) yarn

# ==============================================================================
# RULES

default: help

data/media:
	@mkdir -p data/media

data/static:
	@mkdir -p data/static

data/contracts:
	@mkdir -p data/contracts


# -- Project

bootstrap: ## Prepare Docker images for the project
bootstrap: \
	data/media \
	data/static \
	data/contracts \
	env.d/development/common \
	env.d/development/crowdin \
	env.d/development/localtunnel \
	src/frontend/admin/.env \
	build \
	admin-install \
	admin-build \
	run \
	migrate \
	i18n-compile \
	mails-install \
	mails-build
.PHONY: bootstrap

# -- Docker/compose
build: ## build the app-dev container
	@$(COMPOSE) build app-dev
.PHONY: build

down: ## stop and remove containers, networks, images, and volumes
	@$(COMPOSE) down
.PHONY: down

logs: ## display app-dev logs (follow mode)
	@$(COMPOSE) logs -f app-dev
.PHONY: logs

logs-celery: ## display celery-dev logs (follow mode)
	@$(COMPOSE) logs -f celery-dev
.PHONY: logs-celery

purge-celery: ## purge celery tasks
	@$(COMPOSE_EXEC) celery-dev celery -A joanie.celery_app purge
.PHONY: purge-celery

flower: ## run flower
	@$(COMPOSE_EXEC) celery-dev celery -A joanie.celery_app flower
.PHONY: flower

run: ## start the wsgi (production) and development server
	@$(COMPOSE) up --force-recreate -d nginx
	@$(COMPOSE) up --force-recreate -d app-dev
	@$(COMPOSE) up --force-recreate -d admin-dev
	@$(COMPOSE) up --force-recreate -d celery-dev
	@echo "Wait for postgresql to be up..."
	@$(WAIT_DB)
.PHONY: run

status: ## an alias for "docker compose ps"
	@$(COMPOSE) ps
.PHONY: status

stop: ## stop the development server using Docker
	@$(COMPOSE) stop
.PHONY: stop

# -- Backend

demo: ## flush db then create a demo for load testing purpose
	@$(MAKE) resetdb
	@$(MANAGE) create_demo
.PHONY: demo

demo-dev: ## flush db then create a dataset for dev purpose
	@${MAKE} resetdb
	@$(MANAGE) create_dev_demo
	@$(MANAGE) generate_jwt_tokens
.PHONY: demo-dev

dev-data: ## flush db then create a simpler dataset for dev purpose
	@echo "$(BOLD)Flush database$(RESET)"
	@$(MANAGE) flush --no-input
	@${MAKE} superuser
	@$(MANAGE) set_default_site --domain=$(LOCALTUNNEL_DOMAIN) --name=$(LOCALTUNNEL_DOMAIN)
	@$(MANAGE) create_dev_data
	@$(MANAGE) generate_jwt_tokens
.PHONY: dev-data

generate-jwt-tokens: ## generate JWT tokens for all users
	@$(MANAGE) generate_jwt_tokens
.PHONY: generate-jwt-tokens

# Nota bene: Black should come after isort just in case they don't agree...
lint: ## lint back-end python sources
lint: \
  lint-ruff-format \
  lint-ruff-check \
  lint-pylint
.PHONY: lint

lint-ruff-format: ## format back-end python sources with ruff
	@echo 'lint:ruff-format started…'
	@$(COMPOSE_RUN_APP) ruff format .
.PHONY: lint-ruff-format

lint-ruff-check: ## lint back-end python sources with ruff
	@echo 'lint:ruff-check started…'
	@$(COMPOSE_RUN_APP) ruff check . --fix
.PHONY: lint-ruff-check

lint-pylint: ## lint back-end python sources with pylint only on changed files from main
	@echo 'lint:pylint started…'
	bin/pylint --diff-only=origin/main
.PHONY: lint-pylint

lint-pylint-todo: ## lint back-end python sources with pylint only on changed files from main without fixme warnings
	@echo 'lint:pylint started…'
	bin/pylint --diff-only=origin/main --disable=fixme
.PHONY: lint-pylint-todo

lint-pylint-all: ## lint back-end python sources with pylint
	@echo 'lint:pylint-all started…'
	bin/pylint joanie
.PHONY: lint-pylint-all

lint-pylint-all-todo: ## lint back-end python sources with pylint without fixme warnings
	@echo 'lint:pylint-all started…'
	bin/pylint joanie --disable=fixme
.PHONY: lint-pylint-all-todo

test: ## run project tests
	@$(MAKE) test-back-parallel
	@$(MAKE) admin-test
.PHONY: test

test-back: ## run back-end tests
	@args="$(filter-out $@,$(MAKECMDGOALS))" && \
	bin/pytest $${args:-${1}}
.PHONY: test-back

test-back-parallel: ## run all back-end tests in parallel
	@args="$(filter-out $@,$(MAKECMDGOALS))" && \
	bin/pytest -n auto $${args:-${1}}
.PHONY: test-back-parallel


makemigrations:  ## run django makemigrations for the joanie project.
	@echo "$(BOLD)Running makemigrations$(RESET)"
	@$(COMPOSE) up -d postgresql
	@$(WAIT_DB)
	@$(MANAGE) makemigrations
.PHONY: makemigrations

migrate:  ## run django migrations for the joanie project.
	@echo "$(BOLD)Running migrations$(RESET)"
	@$(COMPOSE) up -d postgresql
	@$(WAIT_DB)
	@$(MANAGE) migrate
.PHONY: migrate

superuser: ## Create an admin superuser with password "admin"
	@echo "$(BOLD)Creating a Django superuser$(RESET)"
	@$(MANAGE) createsuperuser --username admin --email admin@example.com --no-input
.PHONY: superuser

back-i18n-compile: ## compile the gettext files
	@$(MANAGE) compilemessages --ignore="venv/**/*"
.PHONY: back-i18n-compile

back-i18n-generate: ## create the .pot files used for i18n
	@$(MANAGE) makemessages -a --keep-pot
.PHONY: back-i18n-generate

shell: ## connect to database shell
	@$(MANAGE) shell_plus
.PHONY: dbshell

check: ## run django system check framework
	@echo "$(BOLD)System Check Framework"
	@$(MANAGE) check
.PHONY: check

# -- Database

dbshell: ## connect to database shell
	${COMPOSE_EXEC_APP} python manage.py dbshell
.PHONY: dbshell

resetdb: ## flush database and create a superuser "admin"
	@echo "$(BOLD)Flush database$(RESET)"
	@$(MANAGE) flush
	@${MAKE} superuser
	@$(MANAGE) set_default_site --domain=$(LOCALTUNNEL_DOMAIN) --name=$(LOCALTUNNEL_DOMAIN)
.PHONY: resetdb

# -- Frontend admin
src/frontend/admin/.env:
	cp -n src/frontend/admin/.env.example src/frontend/admin/.env

admin-install: ## Install node_modules
	@${ADMIN_YARN} install
.PHONY: admin-install

admin-lint: ## Lint frontend admin app
	@${ADMIN_YARN} lint
.PHONY: admin-lint

admin-test: ## Test frontend admin app
	@${ADMIN_YARN} test
.PHONY: admin-test

admin-build: ## Build frontend admin app
	@${ADMIN_YARN} build
.PHONY: admin-build

admin-i18n-extract: ## Extract translations of frontend admin app
	@${ADMIN_YARN} i18n:extract
.PHONY: admin-i18n-extract

admin-i18n-compile: ## Compile translations of frontend admin app
	@${ADMIN_YARN} i18n:compile
.PHONY: admin-i18n-compile

env.d/development/common:
	cp -n env.d/development/common.dist env.d/development/common

# -- Internationalization

env.d/development/crowdin:
	cp -n env.d/development/crowdin.dist env.d/development/crowdin

env.d/development/localtunnel:
	cp -n env.d/development/localtunnel.dist env.d/development/localtunnel

crowdin-download: ## Download translated message from crowdin
	@$(COMPOSE_RUN_CROWDIN) download -c crowdin/config.yml
.PHONY: crowdin-download

crowdin-upload: ## Upload source translations to crowdin
	@$(COMPOSE_RUN_CROWDIN) upload sources -c crowdin/config.yml
.PHONY: crowdin-upload

i18n-compile: ## compile all translations
i18n-compile: \
	back-i18n-compile \
	admin-i18n-compile
.PHONY: i18n-compile

i18n-generate: ## create the .pot files and extract frontend messages
i18n-generate: \
	back-i18n-generate \
	admin-i18n-extract
.PHONY: i18n-generate

i18n-download-and-compile: ## download all translated messages and compile them to be used by all applications
i18n-download-and-compile: \
  crowdin-download \
  i18n-compile
.PHONY: i18n-download-and-compile

i18n-generate-and-upload: ## generate source translations for all applications and upload them to crowdin
i18n-generate-and-upload: \
  i18n-generate \
  crowdin-upload
.PHONY: i18n-generate-and-upload


# -- Mail generator

mails-build: ## Convert mjml files to html and text
	@$(MAIL_YARN) build
.PHONY: mails-build

mails-build-html-to-plain-text: ## Convert html files to text
	@$(MAIL_YARN) build-html-to-plain-text
.PHONY: mails-build-html-to-plain-text

mails-build-mjml-to-html:	## Convert mjml files to html and text
	@$(MAIL_YARN) build-mjml-to-html
.PHONY: mails-build-mjml-to-html

mails-install: ## mail-generator yarn install
	@$(MAIL_YARN) install
.PHONY: mails-install


# -- Misc
clean: ## restore repository state as it was freshly cloned
	git clean -idx
.PHONY: clean

tunnel: ## Run a proxy through localtunnel
	@echo
	npx localtunnel -s $(LOCALTUNNEL_SUBDOMAIN) -h $(LOCALTUNNEL_HOST) --port $(LOCALTUNNEL_PORT) --print-requests
.PHONY: tunnel

help:
	@echo "$(BOLD)Joanie Makefile"
	@echo "Please use 'make $(BOLD)target$(RESET)' where $(BOLD)target$(RESET) is one of:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-30s$(RESET) %s\n", $$1, $$2}'
.PHONY: help

lint-front: ## run all front-end "linters"
lint-front: \
  lint-front-eslint \
  lint-front-prettier
.PHONY: lint-front

lint-front-prettier: ## run prettier over js/jsx/json/ts/tsx files -- beware! overwrites files
	@$(ADMIN_YARN) prettier-write
.PHONY: lint-front-prettier

lint-front-eslint: ## lint TypeScript sources
	@$(ADMIN_YARN) lint
.PHONY: lint-front-eslint

test-front: ## run front-end tests, or specific test like `make test-front js/components/CourseRunEnrollment`
	@args="$(filter-out $@,$(MAKECMDGOALS))" && \
	$(ADMIN_YARN) test $${args:-${1}}
.PHONY: test-front

test-e2e-front: ## run front-end tests, or specific test like `make test-e2e-front js/components/CourseRunEnrollment`
	npx playwright install --with-deps chromium
	NEXT_PUBLIC_API_SOURCE=test $(ADMIN_YARN) build
	@args="$(filter-out $@,$(MAKECMDGOALS))" && \
	$(ADMIN_YARN) test:e2e $${args:-${1}}
.PHONY: test-front

install-front: ## install front-end dependencies
	@$(ADMIN_YARN) install
.PHONY: install-front
.PHONY:
all: help

.PHONY:
help:
	@grep --no-filename -E '^[a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY:
quality:  ## Perform quality checks
	poetry run mypy ./src/*.py

.PHONY:
fmt:  ## Format code
	poetry run black src/*.py

.PHONY:
gui:  ## Run the app
	poetry run gui

.PHONY:
server: ## Run backend server without GUI in DEBUG mode
	FLASK_APP=src/server.py FLASK_DEBUG=1 poetry run flask run

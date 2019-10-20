.PHONY: \
	fmt \
	lint \
	test \
	build

all:
	@echo "fmt                 Format code."
	@echo "lint                Lint code."
	@echo "test                Test code."
	@echo "build               Build Docker image."

FILES = tg_odesli_bot tests
IMAGE_NAME = 9dogs/tg-odesli-bot:latest

fmt:
	pipenv run black $(FILES)
	pipenv run isort --recursive $(FILES)

lint:
	@if ! pipenv run black --check $(FILES); then \
		echo "Run 'make fmt' to fix"; \
		false; \
	fi
	@if ! pipenv run isort --check-only --recursive $(FILES); then \
		echo "Run 'make fmt' to fix"; \
		false; \
	fi
	pipenv run flake8 $(FILES)
	pipenv run pydocstyle $(FILES)
	pipenv run mypy $(FILES)

build:
	docker build -t $(IMAGE_NAME) .

TEST_OPTS ?= tests -r R --timeout=10
TEST_OUTPUT ?= .
test:
	pipenv run py.test \
        --cov tg_odesli_bot \
        --cov-report term-missing \
        --cov-report html:$(TEST_OUTPUT)/htmlcov \
        --cov-report xml:$(TEST_OUTPUT)/coverage.xml \
        --junit-xml $(TEST_OUTPUT)/junit.xml \
        $(TEST_OPTS)

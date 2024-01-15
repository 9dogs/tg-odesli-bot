.PHONY: \
	fmt \
	lint \
	test \
	build-dev \
	build

all:
	@echo "fmt                 Format code."
	@echo "lint                Lint code."
	@echo "test                Test code."
	@echo "build-dev           Build Docker dev image."
	@echo "build               Build Docker image."

FILES = tg_odesli_bot tests
IMAGE_NAME = 9dogs/tg-odesli-bot:latest

fmt:
	poetry run ruff format $(FILES)
	poetry run ruff check --fix-only -e $(FILES)

lint:
	@if ! poetry run ruff format --check $(FILES); then \
		echo "Run 'make fmt' to fix"; \
		false; \
	fi
	poetry run ruff check $(FILES)
	poetry run mypy $(FILES)

build-dev:
	docker build -t $(IMAGE_NAME) --target=builder --build-arg poetry_args="--with main,dev" .
build:
	docker build -t $(IMAGE_NAME) .

TEST_OPTS ?= tests -r R --timeout=10
TEST_OUTPUT ?= .
test:
	poetry run py.test \
        --cov tg_odesli_bot \
        --cov-report term-missing \
        --cov-report html:$(TEST_OUTPUT)/htmlcov \
        --cov-report xml:$(TEST_OUTPUT)/coverage.xml \
        --junit-xml $(TEST_OUTPUT)/junit.xml \
        $(TEST_OPTS)

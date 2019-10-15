.PHONY: \
	fmt \
	lint \
	mypy \
	test \
	build \
	push

all:
	@echo "fmt                 Format code."
	@echo "lint                Lint code."
	@echo "mypy                Check types."
	@echo "test                Test code."
	@echo "build               Build Docker image."
	@echo "push                Push Docker image to DockerHub."

FILES = tg_odesli_bot tests
IMAGE_NAME = 9dogs/tg_odesli_bot:latest

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

mypy:
	pipenv run mypy $(FILES)

build:
	docker build -t $(IMAGE_NAME) .

push:
	docker push $(IMAGE_NAME)

TEST_OPTS ?= tests -r R
TEST_OUTPUT ?= .
test:
	pipenv run py.test \
        --cov tg_odesli_bot \
        --cov-report term-missing \
        --cov-report html:$(TEST_OUTPUT)/htmlcov \
        --cov-report xml:$(TEST_OUTPUT)/coverage.xml \
        --html=$(TEST_OUTPUT)/report.html \
        --self-contained-html \
        --junit-xml $(TEST_OUTPUT)/junit.xml \
        $(TEST_OPTS)

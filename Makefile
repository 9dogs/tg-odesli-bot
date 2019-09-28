.PHONY: \
	fmt \
	lint \
	test

all:
	@echo "fmt                 Format code."
	@echo "lint                Lint code."
	@echo "test                Test code."

FILES = group_songlink_bot tests

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

TEST_OPTS ?= tests -r R
TEST_OUTPUT ?= .
test:
	pipenv run py.test \
        --cov group_songlink_bot \
        --cov-report term-missing \
        --cov-report html:$(TEST_OUTPUT)/htmlcov \
        --cov-report xml:$(TEST_OUTPUT)/coverage.xml \
        --html=$(TEST_OUTPUT)/report.html \
        --self-contained-html \
        --junit-xml $(TEST_OUTPUT)/junit.xml \
        $(TEST_OPTS)

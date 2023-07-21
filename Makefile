VENV ?= ENV

.PHONY: all tests

all: tests

$(VENV):
	virtualenv --python=python3 $(VENV)
	. $(VENV)/bin/activate && pip install -r requirements.txt

tests: $(VENV)
	. $(VENV)/bin/activate && python -m unittest --buffer --verbose

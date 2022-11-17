.PHONY: default cm2350_tests

.PHONY: all virtualenv venv tests

all: tests

virtualenv venv: $(VENV)

$(VENV):
	virtualenv --python=python3 $(VENV)
	. $(VENV)/bin/activate && pip install -r requirements.txt

tests: $(VENV)
	. $(VENV)/bin/activate && python -m unittest --buffer --verbose

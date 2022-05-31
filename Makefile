VENV ?= ENV

.PHONY: all virtualenv venv tests clean

all: tests

virtualenv venv: $(VENV)

$(VENV):
	virtualenv --python=python3 $(VENV)
	. $(VENV)/bin/activate && pip install -r requirements.txt

tests: $(VENV)
	. $(VENV)/bin/activate && python3 -m unittest --buffer --verbose

clean:
ifneq ($(wildcard VENV),)
	rm -rf $(VENV)
endif

VENV ?= ENV
MPC5674_TESTS := $(patsubst cm2350/tests/test_mpc5674_%.py,%,$(wildcard cm2350/tests/test_mpc5674_*.py))
CM2350_TESTS := $(patsubst cm2350/tests/test_cm2350_%.py,%,$(wildcard cm2350/tests/test_cm2350_*.py))

.PHONY: all virtualenv venv clean $(MPC5674_TESTS) $(CM2350_TESTS)

all: $(MPC5674_TESTS) $(CM2350_TESTS)

virtualenv venv: $(VENV)

$(VENV):
	virtualenv --python=python3 $(VENV)
	. $(VENV)/bin/activate && pip install -r requirements.txt

$(MPC5674_TESTS):
	echo "Running MPC5674 $@ unit tests"
	python3 -m unittest cm2350.tests.test_mpc5674_$@ --buffer --verbose

$(CM2350_TESTS):
	echo "Running CM2350 $@ unit tests"
	python3 -m unittest cm2350.tests.test_cm2350_$@ --buffer --verbose

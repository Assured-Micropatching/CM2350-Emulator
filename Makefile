VENV ?= ENV

.PHONY: default all unittests cm2350_tests vivisect_tests vivisect_ppc_vle_tests vle virtualenv venv clean

default: vivisect_ppc_tests cm2350_tests

all: vivisect_tests cm2350_tests

virtualenv venv: ${VENV}

${VENV}:
	virtualenv --python=python3 ${VENV}
	. ${VENV}/bin/activate && pip install -r requirements.txt

vle: vivisect_ppc_vle_tests

embedded: vivisect_ppc_embedded_tests

cm2350_tests:
	echo "Running CM2350 unit tests"
	python3 -m unittest cm2350.tests.test_mpc5674_fmpll --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_siu --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_swt --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_mmu --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_timebase --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_bam --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_flash --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_flexcan --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_dspi --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_sim --buffer --verbose
	python3 -m unittest cm2350.tests.test_cm2350_cli --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_decfilt --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_eqadc --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_xbar --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_pbridge --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_ecsm --buffer --verbose
	python3 -m unittest cm2350.tests.test_mpc5674_ebi --buffer --verbose

vivisect_ppc_tests:
	echo "Vivisect PPC unit tests"
	cd cm2350/internal && python3 -m unittest envi.tests.test_ppc_by_cat --buffer --verbose
	cd cm2350/internal && python3 -m unittest envi.tests.test_arch_ppc --buffer --verbose

vivisect_ppc_vle_tests:
	echo "Vivisect PPC VLE unit tests"
	cd cm2350/internal && \
		python3 -m unittest envi.tests.test_arch_ppc.PpcInstructionSet.test_envi_ppcvle_disasm \
		                    envi.tests.test_arch_ppc.PpcInstructionSet.test_envi_ppcvle_emu \
				--buffer --verbose

vivisect_ppc_embedded_tests:
	echo "Vivisect PPC embedded unit tests"
	cd cm2350/internal && \
		python3 -m unittest envi.tests.test_arch_ppc.PpcInstructionSet.test_envi_ppc_embedded_disasm \
		                    envi.tests.test_arch_ppc.PpcInstructionSet.test_envi_ppc_embedded_emu \
				--buffer --verbose

vivisect_tests:
	echo "Vivisect unit tests"
	cd cm2350/internal && python3 -m unittest --buffer --verbose

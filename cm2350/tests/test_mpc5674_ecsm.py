import random

from cm2350 import intc_exc

from .helpers import MPC5674_Test


# Offset and access size for each ECSM register
ECSM_PCT                = (0xFFF40000, 2)
ECSM_REV                = (0xFFF40002, 2)
ECSM_IMC                = (0xFFF40008, 4)
ECSM_MRSR               = (0xFFF4000F, 1)
ECSM_ECR                = (0xFFF40043, 1)
ECSM_ESR                = (0xFFF40047, 1)
ECSM_EEGR               = (0xFFF4004A, 2)
ECSM_FEAR               = (0xFFF40050, 4)
ECSM_FEMR               = (0xFFF40056, 1)
ECSM_FEAT               = (0xFFF40057, 1)
ECSM_FEDRH              = (0xFFF40058, 4)
ECSM_FEDRL              = (0xFFF4005C, 4)
ECSM_REAR               = (0xFFF40060, 4)
ECSM_RESR               = (0xFFF40065, 1)
ECSM_REMR               = (0xFFF40066, 1)
ECSM_REAT               = (0xFFF40067, 1)
ECSM_REDRH              = (0xFFF40068, 4)
ECSM_REDRL              = (0xFFF4006C, 4)

# These values were read from a MPC5674F
ECSM_PCT_DEFAULT_VALUE  = 0xE760
ECSM_PCT_DEFAULT_BYTES  = b'\xE7\x60'
ECSM_REV_DEFAULT_VALUE  = 0x0000
ECSM_REV_DEFAULT_BYTES  = b'\x00\x00'
ECSM_IMC_DEFAULT_VALUE  = 0xC803E400
ECSM_IMC_DEFAULT_BYTES  = b'\xC8\x03\xE4\x00'

# The MRSR should have the POR flag set, all other registers have a default of 0
ECSM_MRSR_DEFAULT_VALUE  = 0x80
ECSM_MRSR_DEFAULT_BYTES  = b'\x80'

# Constants used to test error generation
ECSM_EEGR_FRC1BI_MASK           = 0x2000
ECSM_EEGR_FR11BI_MASK           = 0x1000
ECSM_EEGR_FRCNCI_MASK           = 0x0200
ECSM_EEGR_FR1NCI_MASK           = 0x0100

# The ESR and ECR masks are the same
ECSM_EXR_R1BC_MASK              = 0x20
ECSM_EXR_F1BC_MASK              = 0x10
ECSM_EXR_RNCE_MASK              = 0x02
ECSM_EXR_FNCE_MASK              = 0x00

# The EEGR[ERRBIT] field indicates the type of error that will be generated, and
# each error has a weird value that gets stored in the RESR register, we only
# use a few values for testing:
ECSM_EEGR_ERRBIT_DATA_0_MASK    = 0x0000
ECSM_EEGR_ERRBIT_DATA_31_MASK   = 0x001F
ECSM_EEGR_ERRBIT_ECC_0_MASK     = 0x0040
ECSM_EEGR_ERRBIT_ECC_7_MASK     = 0x0047

ECSM_RESR_DATA_0_ERROR          = 0xCE
ECSM_RESR_DATA_31_ERROR         = 0xF4
ECSM_RESR_ECC_0_ERROR           = 0x01
ECSM_RESR_ECC_7_ERROR           = 0x80

ECSM_RAM_ERROR_TESTS = (
    (ECSM_EEGR_ERRBIT_DATA_0_MASK,  ECSM_RESR_DATA_0_ERROR),
    (ECSM_EEGR_ERRBIT_DATA_31_MASK, ECSM_RESR_DATA_31_ERROR),
    (ECSM_EEGR_ERRBIT_ECC_0_MASK,   ECSM_RESR_ECC_0_ERROR),
    (ECSM_EEGR_ERRBIT_ECC_7_MASK,   ECSM_RESR_ECC_7_ERROR),
)

# All forced RAM error tests will come from bus master of CORE0, which has a
# value of 0 so REMR will be 0.  Not much to verify
ECSM_REMR_CORE0_VALUE           = 0x00

# All forced RAM error tests done here are done with the default MMU entries so
# they will not be cached or buffered, will be in supervisor mode and will
# happen during a data write, so the WRITE and PROTECTION fields are known for
# the REAT values generated in this file
ECSM_REAT_BASE_VALUE            = 0b10000011
ECSM_REAT_SIZE_VALUES = {
    1: 0b0000000,
    2: 0b0010000,
    4: 0b0100000,
    8: 0b0110000,
}


def get_int_src(event):
    """
    Calculate the correct external interrupt source for a ECSM device and event
    values are from
    "Table 9-8. Interrupt Request Sources" (MPC5674FRM.pdf page 325-341)

      ECSM = 9     # ECSM_ESR[RNCE], ECSM_ESR[FNCE]

    Parameters:
        event (str): the event to return the interrupt source for

    Return:
        interrupt source value (int)
    """
    # Single-bit errors have no corresponding interrupt event
    return {'r1br': None, 'rncr': 9, 'f1br': None, 'fncr': 9}[event]


def get_int(event):
    """
    Returns an ExternalException object that corresponds to a queued exception
    associated with a specific DSPI device and event.

    Parameters:
        event (str): the event to return the interrupt source for

    Return:
        interrupt source value (int)
    """
    src = get_int_src(event)
    if src is None:
        return None
    else:
        return intc_exc.ExternalException(intc_exc.INTC_SRC(src))


class MPC5674_ECSM_Test(MPC5674_Test):

    ##################################################
    # Tests
    ##################################################

    def test_ecsm_regs(self):
        # First 3 registers are read-only with fixed values
        addr, size = ECSM_PCT
        self.assertEqual(self.emu.readMemValue(addr, size), ECSM_PCT_DEFAULT_VALUE)
        self.assertEqual(self.emu.readMemory(addr, size), ECSM_PCT_DEFAULT_BYTES)
        addr, size = ECSM_REV
        self.assertEqual(self.emu.readMemValue(addr, size), ECSM_REV_DEFAULT_VALUE)
        self.assertEqual(self.emu.readMemory(addr, size), ECSM_REV_DEFAULT_BYTES)
        addr, size = ECSM_IMC
        self.assertEqual(self.emu.readMemValue(addr, size), ECSM_IMC_DEFAULT_VALUE)
        self.assertEqual(self.emu.readMemory(addr, size), ECSM_IMC_DEFAULT_BYTES)

        # The reset-related features of the MRSR register are tested in the SWT
        # unit tests
        addr, size = ECSM_MRSR
        self.assertEqual(self.emu.readMemValue(addr, size), ECSM_MRSR_DEFAULT_VALUE)
        self.assertEqual(self.emu.readMemory(addr, size), ECSM_MRSR_DEFAULT_BYTES)

        # The rest of the registers have default values of 0
        addr, size = ECSM_ECR
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_ESR
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_EEGR
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_FEAR
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_FEMR
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_FEAT
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_FEDRH
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_FEDRL
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_REAR
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_RESR
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_REMR
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_REAT
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_REDRH
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

        addr, size = ECSM_REDRL
        self.assertEqual(self.emu.readMemValue(addr, size), 0)
        self.assertEqual(self.emu.readMemory(addr, size), b'\x00'*size)

    def test_ecsm_reset_reason(self):
        # Verify RSR[SERF] default. The RSR register has WKPCFG and BOOTCFG
        # read-only values
        # For this configuration WKPCFG is 1 and BOOTCFG is 0 so the default RSR
        # value is:
        #   0xx00008000
        addr, size = ECSM_MRSR

        # By default the POR flag should be set
        self.assertEqual(self.emu.readMemValue(addr, size), ECSM_MRSR_DEFAULT_VALUE)
        self.assertEqual(self.emu.ecsm.registers.mrsr.por, 1)
        self.assertEqual(self.emu.ecsm.registers.mrsr.dir, 0)
        self.assertEqual(self.emu.ecsm.registers.mrsr.swtr, 0)

        # Trigger some resets and ensure the correct reset source is set (also 
        # the weak pullup flag is set)
        source_tests = [
            (intc_exc.ResetSource.POWER_ON,          'por',  0x80),
            (intc_exc.ResetSource.EXTERNAL,          'dir',  0x40),
            (intc_exc.ResetSource.LOSS_OF_LOCK,      'dir',  0x40),
            (intc_exc.ResetSource.LOSS_OF_CLOCK,     'dir',  0x40),
            (intc_exc.ResetSource.CORE_WATCHDOG,     'dir',  0x40),
            (intc_exc.ResetSource.DEBUG,             'dir',  0x40),
            (intc_exc.ResetSource.WATCHDOG,          'swtr', 0x20),
            (intc_exc.ResetSource.SOFTWARE_SYSTEM,   'dir',  0x40),
            (intc_exc.ResetSource.SOFTWARE_EXTERNAL, 'dir',  0x40),
        ]

        for source, test_field, test_value in source_tests:
            # Queue a reset exception with the desired reset reason and step to 
            # reset the emulator
            self.emu.queueException(intc_exc.ResetException(source))
            self.emu.stepi()

            # Verify that the reset reason is now set correctly
            self.assertEqual(self.emu.readMemValue(addr, size), test_value, msg=test_field)

            for field, value in self.emu.ecsm.registers.mrsr.vsGetFields():
                msg = '%s (%s)' % (field, test_field)
                if field == test_field:
                    self.assertEqual(value, 1, msg=msg)
                else:
                    self.assertEqual(value, 0, msg=msg)

            # Writing 0 to all fields should not change anything
            self.emu.writeMemory(addr, b'\x00' * size)

            for field, value in self.emu.ecsm.registers.mrsr.vsGetFields():
                msg = '%s (%s)' % (field, test_field)
                if field == test_field:
                    self.assertEqual(value, 1, msg=msg)
                else:
                    self.assertEqual(value, 0, msg=msg)

            # Writing 1 to all fields should not change anything
            self.emu.writeMemory(addr, b'\xFF' * size)

            for field, value in self.emu.ecsm.registers.mrsr.vsGetFields():
                msg = '%s (%s)' % (field, test_field)
                if field == test_field:
                    self.assertEqual(value, 1, msg=msg)
                else:
                    self.assertEqual(value, 0, msg=msg)

    def test_ecsm_fr11b_error(self):
        # The EEGR register can be used to force RAM write errors, 1-bit errors
        # should result in the REAR, RESR, REMR, REAT, REDRH, and REDRL
        # registers being updated but no exception will be generated.  Only
        # non-correctable errors can generate ECSM exceptions.

        ecr_addr, ecr_size = ECSM_ECR
        esr_addr, esr_size = ECSM_ESR
        eegr_addr, eegr_size = ECSM_EEGR
        rear_addr, rear_size = ECSM_REAR
        resr_addr, resr_size = ECSM_RESR
        remr_addr, remr_size = ECSM_REMR
        reat_addr, reat_size = ECSM_REAT
        redrh_addr, redrh_size = ECSM_REDRH
        redrl_addr, redrl_size = ECSM_REDRL

        # No errors configured and no errors detected yet
        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), 0)

        # First test single-write error generation
        errbit, resr_value = random.choice(ECSM_RAM_ERROR_TESTS)
        eegr_value = ECSM_EEGR_FR11BI_MASK | errbit
        self.emu.writeMemValue(eegr_addr, eegr_value, eegr_size)

        err1_pc = self.set_random_pc()
        err1_addr, err1_value, err1_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err1_addr, err1_value, err1_size)

        # R1BC (field is named as 'r1br' in the emulator register) is set
        # because the event has occurred.
        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)

        # Because nothing in ECR is set, the ESR bit should show up but the ECSM
        # RAM ECC registers will still be 0
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), 0)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), 0)
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), 0)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), 0)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), 0)

        # Clear the status flag
        self.emu.writeMemValue(esr_addr, ECSM_EXR_R1BC_MASK, esr_size)

        # Try to write again and nothing happens because this was just a 1-time
        # error.
        err2_pc = self.set_random_pc()
        err2_addr, err2_value, err2_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err2_addr, err2_value, err2_size)

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), 0)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), 0)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), 0)
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), 0)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), 0)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), 0)

        # Clear the EEGR and re-write the value to get the ESR event flag set
        # again
        self.emu.writeMemValue(eegr_addr, 0, eegr_size)
        self.emu.writeMemValue(eegr_addr, eegr_value, eegr_size)

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), 0)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)

        self.emu.writeMemValue(err2_addr, err2_value, err2_size)

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), 0)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), 0)
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), 0)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), 0)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), 0)

        # Clear the ESR flag and EEGR value, then enable ECR and make sure the
        # REAR, RESR, REMR, REAT, REDRH, and REDRL registers are set correctly,
        # but no exception is generated.
        self.emu.writeMemValue(esr_addr, ECSM_EXR_R1BC_MASK, esr_size)
        self.emu.writeMemValue(eegr_addr, 0, eegr_size)
        self.emu.writeMemValue(ecr_addr, ECSM_EXR_R1BC_MASK, ecr_size)
        self.emu.writeMemValue(eegr_addr, eegr_value, eegr_size)

        err3_pc = self.set_random_pc()
        err3_addr, err3_value, err3_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err3_addr, err3_value, err3_size)

        err3_reat_value = ECSM_REAT_BASE_VALUE | ECSM_REAT_SIZE_VALUES[err3_size]

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), err3_addr)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), resr_value )
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), ECSM_REMR_CORE0_VALUE)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), err3_reat_value)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), err3_value)

        self.assertEqual(self._getPendingExceptions(), [])

    def test_ecsm_frc1b_error(self):
        # The EEGR register can be used to force RAM write errors, 1-bit errors
        # should result in the REAR, RESR, REMR, REAT, REDRH, and REDRL
        # registers being updated but no exception will be generated.  Only
        # non-correctable errors can generate ECSM exceptions.

        ecr_addr, ecr_size = ECSM_ECR
        esr_addr, esr_size = ECSM_ESR
        eegr_addr, eegr_size = ECSM_EEGR
        rear_addr, rear_size = ECSM_REAR
        resr_addr, resr_size = ECSM_RESR
        remr_addr, remr_size = ECSM_REMR
        reat_addr, reat_size = ECSM_REAT
        redrh_addr, redrh_size = ECSM_REDRH
        redrl_addr, redrl_size = ECSM_REDRL

        # No errors configured and no errors detected yet
        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), 0)

        errbit, resr_value = random.choice(ECSM_RAM_ERROR_TESTS)
        eegr_value = ECSM_EEGR_FRC1BI_MASK | errbit
        self.emu.writeMemValue(eegr_addr, eegr_value, eegr_size)

        err1_pc = self.set_random_pc()
        err1_addr, err1_value, err1_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err1_addr, err1_value, err1_size)

        # R1BC (field is named as 'r1br' in the emulator register) is set
        # because the event has occurred.
        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)

        # Because nothing in ECR is set, the ESR bit should show up but the ECSM
        # RAM ECC registers will still be 0
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), 0)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), 0)
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), 0)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), 0)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), 0)

        # Clear the status flag
        self.emu.writeMemValue(esr_addr, ECSM_EXR_R1BC_MASK, esr_size)

        # Try to write again and the error should be detected because the
        # continuous 1-bit error flag was set.
        err2_pc = self.set_random_pc()
        err2_addr, err2_value, err2_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err2_addr, err2_value, err2_size)

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), 0)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), 0)
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), 0)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), 0)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), 0)

        # If the ECR flag is enabled now the error information will start being
        # populated, but because the ESR flag is already set a new interrupt
        # would not be generated, but the 1-bit errors don't generate an
        # exception anyway.
        self.emu.writeMemValue(ecr_addr, ECSM_EXR_R1BC_MASK, ecr_size)

        err3_pc = self.set_random_pc()
        err3_addr, err3_value, err3_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err3_addr, err3_value, err3_size)

        err3_reat_value = ECSM_REAT_BASE_VALUE | ECSM_REAT_SIZE_VALUES[err3_size]

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), err3_addr)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), resr_value )
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), ECSM_REMR_CORE0_VALUE)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), err3_reat_value)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), err3_value)

        self.assertEqual(self._getPendingExceptions(), [])

        # Confirm the error information is updated on the next write.
        err4_pc = self.set_random_pc()
        err4_addr, err4_value, err4_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err4_addr, err4_value, err4_size)

        err4_reat_value = ECSM_REAT_BASE_VALUE | ECSM_REAT_SIZE_VALUES[err4_size]

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), err4_addr)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), resr_value )
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), ECSM_REMR_CORE0_VALUE)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), err4_reat_value)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), err4_value)

        self.assertEqual(self._getPendingExceptions(), [])

        # Clear the ESR and EEGR flags, then re-enable the EEGR flag to ensure
        # that no unexpected exceptions occur when a 1-bit RAM ECC error is
        # generated
        self.emu.writeMemValue(esr_addr, ECSM_EXR_R1BC_MASK, esr_size)
        self.emu.writeMemValue(eegr_addr, 0, eegr_size)
        self.emu.writeMemValue(eegr_addr, eegr_value, eegr_size)

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), 0)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)

        err5_pc = self.set_random_pc()
        err5_addr, err5_value, err5_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err5_addr, err5_value, err5_size)

        err5_reat_value = ECSM_REAT_BASE_VALUE | ECSM_REAT_SIZE_VALUES[err5_size]

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_R1BC_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), err5_addr)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), resr_value )
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), ECSM_REMR_CORE0_VALUE)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), err5_reat_value)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), err5_value)

        self.assertEqual(self._getPendingExceptions(), [])

    def test_ecsm_fr1nc_error(self):
        # The EEGR register can be used to force RAM write errors,
        # non-correctable errors should result in the REAR, RESR, REMR, REAT,
        # REDRH, and REDRL registers being updated and an external exception
        # will be generated.

        ecr_addr, ecr_size = ECSM_ECR
        esr_addr, esr_size = ECSM_ESR
        eegr_addr, eegr_size = ECSM_EEGR
        rear_addr, rear_size = ECSM_REAR
        resr_addr, resr_size = ECSM_RESR
        remr_addr, remr_size = ECSM_REMR
        reat_addr, reat_size = ECSM_REAT
        redrh_addr, redrh_size = ECSM_REDRH
        redrl_addr, redrl_size = ECSM_REDRL

        # No errors configured and no errors detected yet
        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), 0)

        # First test single-write error generation
        errbit, resr_value = random.choice(ECSM_RAM_ERROR_TESTS)
        eegr_value = ECSM_EEGR_FR1NCI_MASK | errbit
        self.emu.writeMemValue(eegr_addr, eegr_value, eegr_size)

        err1_pc = self.set_random_pc()
        err1_addr, err1_value, err1_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err1_addr, err1_value, err1_size)

        # RNCE (field is named as 'rncr' in the emulator register) is set
        # because the event has occurred.
        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)

        # Because nothing in ECR is set, the ESR bit should show up but the ECSM
        # RAM ECC registers will still be 0
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), 0)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), 0)
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), 0)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), 0)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), 0)

        # Clear the status flag
        self.emu.writeMemValue(esr_addr, ECSM_EXR_RNCE_MASK, esr_size)

        # Try to write again and nothing happens because this was just a 1-time
        # error.
        err2_pc = self.set_random_pc()
        err2_addr, err2_value, err2_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err2_addr, err2_value, err2_size)

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), 0)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), 0)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), 0)
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), 0)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), 0)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), 0)

        # Clear the EEGR and re-write the value to get the ESR event flag set
        # again
        self.emu.writeMemValue(eegr_addr, 0, eegr_size)
        self.emu.writeMemValue(eegr_addr, eegr_value, eegr_size)

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), 0)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)

        self.emu.writeMemValue(err2_addr, err2_value, err2_size)

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), 0)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), 0)
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), 0)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), 0)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), 0)

        # Clear the ESR flag and EEGR value, then enable ECR and make sure the
        # REAR, RESR, REMR, REAT, REDRH, and REDRL registers are set correctly,
        # but no exception is generated.
        self.emu.writeMemValue(esr_addr, ECSM_EXR_RNCE_MASK, esr_size)
        self.emu.writeMemValue(eegr_addr, 0, eegr_size)
        self.emu.writeMemValue(ecr_addr, ECSM_EXR_RNCE_MASK, ecr_size)
        self.emu.writeMemValue(eegr_addr, eegr_value, eegr_size)

        err3_pc = self.set_random_pc()
        err3_addr, err3_value, err3_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err3_addr, err3_value, err3_size)

        err3_reat_value = ECSM_REAT_BASE_VALUE | ECSM_REAT_SIZE_VALUES[err3_size]

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), err3_addr)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), resr_value )
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), ECSM_REMR_CORE0_VALUE)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), err3_reat_value)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), err3_value)

        self.assertEqual(self._getPendingExceptions(), [get_int('rncr')])

    def test_ecsm_frcnc_error(self):
        # The EEGR register can be used to force RAM write errors,
        # non-correctable errors should result in the REAR, RESR, REMR, REAT,
        # REDRH, and REDRL registers being updated and an external exception
        # will be generated.

        ecr_addr, ecr_size = ECSM_ECR
        esr_addr, esr_size = ECSM_ESR
        eegr_addr, eegr_size = ECSM_EEGR
        rear_addr, rear_size = ECSM_REAR
        resr_addr, resr_size = ECSM_RESR
        remr_addr, remr_size = ECSM_REMR
        reat_addr, reat_size = ECSM_REAT
        redrh_addr, redrh_size = ECSM_REDRH
        redrl_addr, redrl_size = ECSM_REDRL

        # No errors configured and no errors detected yet
        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), 0)

        errbit, resr_value = random.choice(ECSM_RAM_ERROR_TESTS)
        eegr_value = ECSM_EEGR_FRCNCI_MASK | errbit
        self.emu.writeMemValue(eegr_addr, eegr_value, eegr_size)

        err1_pc = self.set_random_pc()
        err1_addr, err1_value, err1_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err1_addr, err1_value, err1_size)

        # RNCE (field is named as 'rncr' in the emulator register) is set
        # because the event has occurred.
        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)

        # Because nothing in ECR is set, the ESR bit should show up but the ECSM
        # RAM ECC registers will still be 0
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), 0)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), 0)
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), 0)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), 0)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), 0)

        # Clear the status flag
        self.emu.writeMemValue(esr_addr, ECSM_EXR_RNCE_MASK, esr_size)

        # Try to write again and the error should be detected because the
        # continuous 1-bit error flag was set.
        err2_pc = self.set_random_pc()
        err2_addr, err2_value, err2_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err2_addr, err2_value, err2_size)

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), 0)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), 0)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), 0)
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), 0)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), 0)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), 0)

        # If the ECR flag is enabled now the error information will start being
        # populated, but because the ESR flag is already set a new interrupt
        # will not be generated
        self.emu.writeMemValue(ecr_addr, ECSM_EXR_RNCE_MASK, ecr_size)

        err3_pc = self.set_random_pc()
        err3_addr, err3_value, err3_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err3_addr, err3_value, err3_size)

        err3_reat_value = ECSM_REAT_BASE_VALUE | ECSM_REAT_SIZE_VALUES[err3_size]

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), err3_addr)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), resr_value )
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), ECSM_REMR_CORE0_VALUE)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), err3_reat_value)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), err3_value)

        self.assertEqual(self._getPendingExceptions(), [])

        # Confirm the error information is updated on the next write.
        err4_pc = self.set_random_pc()
        err4_addr, err4_value, err4_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err4_addr, err4_value, err4_size)

        err4_reat_value = ECSM_REAT_BASE_VALUE | ECSM_REAT_SIZE_VALUES[err4_size]

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), err4_addr)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), resr_value )
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), ECSM_REMR_CORE0_VALUE)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), err4_reat_value)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), err4_value)

        self.assertEqual(self._getPendingExceptions(), [])

        # Clear the ESR and EEGR flags, then re-enable the EEGR flag to ensure
        # that no unexpected exceptions occur when a 1-bit RAM ECC error is
        # generated
        self.emu.writeMemValue(esr_addr, ECSM_EXR_RNCE_MASK, esr_size)
        self.emu.writeMemValue(eegr_addr, 0, eegr_size)
        self.emu.writeMemValue(eegr_addr, eegr_value, eegr_size)

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), 0)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)

        err5_pc = self.set_random_pc()
        err5_addr, err5_value, err5_size = self.get_random_ram_addr_and_data()
        self.emu.writeMemValue(err5_addr, err5_value, err5_size)

        err5_reat_value = ECSM_REAT_BASE_VALUE | ECSM_REAT_SIZE_VALUES[err5_size]

        self.assertEqual(self.emu.readMemValue(ecr_addr, ecr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(esr_addr, esr_size), ECSM_EXR_RNCE_MASK)
        self.assertEqual(self.emu.readMemValue(eegr_addr, eegr_size), eegr_value)
        self.assertEqual(self.emu.readMemValue(rear_addr, rear_size), err5_addr)
        self.assertEqual(self.emu.readMemValue(resr_addr, resr_size), resr_value )
        self.assertEqual(self.emu.readMemValue(remr_addr, remr_size), ECSM_REMR_CORE0_VALUE)
        self.assertEqual(self.emu.readMemValue(reat_addr, reat_size), err5_reat_value)
        self.assertEqual(self.emu.readMemValue(redrh_addr, redrh_size), 0)
        self.assertEqual(self.emu.readMemValue(redrl_addr, redrl_size), err5_value)

        self.assertEqual(self._getPendingExceptions(), [get_int('rncr')])

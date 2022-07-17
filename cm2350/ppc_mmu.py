import enum

import envi
from envi.archs.ppc.regs import *
from envi.archs.ppc.const import *

from .ppc_vstructs import BitFieldSPR, v_const

import logging
logger = logging.getLogger(__name__)


__all__ = [
    'PpcMMU',
]


class PpcTlbFlags(enum.IntFlag):
    # The flag bits are arranged as:
    #   VLE | W | I | M | G | E
    VLE    = 0b100000
    W      = 0b010000
    I      = 0b001000
    M      = 0b000100
    G      = 0b000010
    E      = 0b000001

    # Some common flag combinations
    WG     = W | G
    IG     = I | G
    WIG    = W | I | G


class PpcTlbPerm(enum.IntFlag):
    # The permission bits are arranged as:
    #   SX | UX | SW | UW | SR | UR
    S_R    = 0b000010
    S_W    = 0b001000
    S_X    = 0b100000
    S_RW   = 0b001010
    S_RX   = 0b100010
    S_RWX  = 0b101010
    U_R    = 0b000001
    U_W    = 0b000100
    U_X    = 0b010000
    U_RW   = 0b000101
    U_RX   = 0b010001
    U_RWX  = 0b010101
    SU_R   = S_R | U_R
    SU_RW  = S_RW | U_RW
    SU_RX  = S_RX | U_RX
    SU_RWX = S_RWX | U_RWX


# PPC TLB Entry Page Sizes
class PpcTlbPageSize(enum.IntEnum):
    SIZE_1KB   = 0
    SIZE_2KB   = 1
    SIZE_4KB   = 2
    SIZE_8KB   = 3
    SIZE_16KB  = 4
    SIZE_32KB  = 5
    SIZE_64KB  = 6
    SIZE_128KB = 7
    SIZE_256KB = 8
    SIZE_512KB = 9
    SIZE_1MB   = 10
    SIZE_2MB   = 11
    SIZE_4MB   = 12
    SIZE_8MB   = 13
    SIZE_16MB  = 14
    SIZE_32MB  = 15
    SIZE_64MB  = 16
    SIZE_128MB = 17
    SIZE_256MB = 18
    SIZE_512MB = 19
    SIZE_1GB   = 20
    SIZE_2GB   = 21
    SIZE_4GB   = 22


# TLB address comparison masks (based on the TLB entry page size)
_tlb_address_mask = (
    0xFFFFFC00,  # [ 0]   1KB Pages
    0xFFFFF800,  # [ 1]   2KB Pages
    0xFFFFF000,  # [ 2]   4KB Pages
    0xFFFFE000,  # [ 3]   8KB Pages
    0xFFFFC000,  # [ 4]  16KB Pages
    0xFFFF8000,  # [ 5]  32KB Pages
    0xFFFF0000,  # [ 6]  64KB Pages
    0xFFFE0000,  # [ 7] 128KB Pages
    0xFFFC0000,  # [ 8] 256KB Pages
    0xFFF80000,  # [ 9] 512KB Pages
    0xFFF00000,  # [10]   1MB Pages
    0xFFE00000,  # [11]   2MB Pages
    0xFFC00000,  # [12]   4MB Pages
    0xFF800000,  # [13]   8MB Pages
    0xFF000000,  # [14]  16MB Pages
    0xFE000000,  # [15]  32MB Pages
    0xFC000000,  # [16]  64MB Pages
    0xF8000000,  # [17] 128MB Pages
    0xF0000000,  # [18] 256MB Pages
    0xE0000000,  # [19] 512MB Pages
    0xC0000000,  # [20]   1GB Pages
    0x80000000,  # [21]   2GB Pages
    0x00000000,  # [22]   4GB Pages
)

# TLB entry size debug msg strings
_tlb_size_str = (
    '1kB',
    '2kB',
    '4kB',
    '8kB',
    '16kB',
    '32kB',
    '64kB',
    '128kB',
    '256kB',
    '512kB',
    '1MB',
    '2MB',
    '4MB',
    '8MB',
    '16MB',
    '32MB',
    '64MB',
    '128MB',
    '256MB',
    '512MB',
    '1GB',
    '2GB',
    '4GB',
)


# Read-only SPRs that report information about the MMU/TLB configuration

class MMUCFG(BitFieldSPR):
    def __init__(self, emu):
        super().__init__(REG_MMUCFG, emu)
        self._pad0 = v_const(8)
        self.rasize = v_const(7, 0b0100000)
        self._pad1 = v_const(2)
        self.npids = v_const(4, 0b0001)
        self.pidsize = v_const(5, 0b00111)
        self._pad2 = v_const(2)
        self.ntlbs = v_const(2, 0b01)
        self.mavn = v_const(2, 0b00)


class TLB0CFG(BitFieldSPR):
    def __init__(self, emu):
        super().__init__(REG_TLB0CFG, emu)
        self.assoc = v_const(8)
        self.minsize = v_const(4)
        self.maxsize = v_const(4)
        self.iprot = v_const(1)
        self.avail = v_const(1)
        self.p2psa = v_const(1)
        self._pad0 = v_const(1)
        self.nentry = v_const(12)


class TLB1CFG(BitFieldSPR):
    def __init__(self, emu):
        super().__init__(REG_TLB1CFG, emu)
        self.assoc = v_const(8, 0x20)
        self.minsize = v_const(4, 0x0) # minimum page size is 1KB
        self.maxsize = v_const(4, 0xB) # maximum page size is 4GB
        self.iprot = v_const(1, 1)
        self.avail = v_const(1, 1)
        self.p2psa = v_const(1, 1)
        self._pad0 = v_const(1)
        self.nentry = v_const(12, 0x20)

# For MAS0-MAS6 SPRs there is nothing that needs to happen when values are read
# or written so the normal SPR storage is used and instead these masks are used
# to efficiently read/write values in those registers

MAS0_TBSEL_MASK    = 0x30000000
MAS0_ESEL_MASK     = 0x001F0000
MAS0_NV_MASK       = 0x0000001F

MAS0_TBSEL_SHIFT   = 28
MAS0_ESEL_SHIFT    = 16
MAS0_NV_SHIFT      = 0

MAS1_VALID_MASK    = 0x80000000
MAS1_IPROT_MASK    = 0x40000000
MAS1_TID_MASK      = 0x007F0000
MAS1_TS_MASK       = 0x00001000
MAS1_TSIZ_MASK     = 0x00000F80

MAS1_VALID_SHIFT   = 31
MAS1_IPROT_SHIFT   = 30
MAS1_TID_SHIFT     = 16
MAS1_TS_SHIFT      = 12
MAS1_TSIZ_SHIFT    = 7

# The EPN and RPN fields are extracted using the same mask and without any
# shifting.  This mask is used in some other operations as well to extract the
# maximum allowed MASK bits from a value (such as in tlbivax)
EPN_MASK           = 0xFFFFFC00

#MAS2_EPN_MASK      = 0xFFFFFC00
MAS2_FLAGS_MASK    = 0x0000003F

#MAS2_EPN_SHIFT     = 10
MAS2_FLAGS_SHIFT   = 0

#MAS3_RPN_MASK      = 0xFFFFFC00
MAS3_USER_MASK     = 0x000003C0
MAS3_PERM_MASK     = 0x0000003F

#MAS3_RPN_SHIFT     = 10
MAS3_USER_SHIFT    = 6
MAS3_PERM_SHIFT    = 0

# TODO: MAS4 is used only during the TLB Miss exception handler. This module
# does not currently implement any special handling related to MAS4 and in
# theory it won't need to.
MAS4_TLBSELD_MASK  = 0x30000000
MAS4_TIDSELD_MASK  = 0x00030000
MAS4_TSIZED_MASK   = 0x00000F80
MAS4_FLAGSD_MASK   = 0x0000003F

MAS4_TLBSELD_SHIFT = 28
MAS4_TIDSELD_SHIFT = 16
MAS4_TSIZED_SHIFT  = 7
MAS4_FLAGSD_SHIFT  = 0

MAS6_SPID_MASK     = 0x001F0000
MAS6_SAS_MASK      = 0x00000001

MAS6_SPID_SHIFT    = 16
MAS6_SAS_SHIFT     = 0


class PpcTLBEntry:
    # Define the attributes for this class in slots to improve performance
    #__slots__ = ['esel', 'valid', 'iprot', 'tid', 'ts', 'tsiz', 'epn', 'flags',
    #        'rpn', 'user', 'perm', 'mask', 'vle']

    def __init__(self, esel, valid=0, iprot=0, tid=0, ts=0, tsiz=0, epn=0, flags=0, rpn=0, user=0, perm=0):
        # the entry selector (index) can't be changed
        self.esel = esel
        self.config(valid, iprot, tid, ts, tsiz, epn, flags, rpn, user, perm)

    def config(self, valid=0, iprot=0, tid=0, ts=0, tsiz=0, epn=0, flags=0, rpn=0, user=0, perm=0):
        self.valid = valid
        self.iprot = iprot
        self.tid = tid
        self.ts = ts
        self.tsiz = PpcTlbPageSize(tsiz)
        self.epn = epn
        self.flags = PpcTlbFlags(flags)
        self.rpn = rpn
        self.user = user
        self.perm = PpcTlbPerm(perm)

        # Calculate the mask now
        self.mask = _tlb_address_mask[self.tsiz]

        self.vle = bool(self.flags & PpcTlbFlags.VLE)

    def size(self):
        # Used in debug messages
        return _tlb_size_str[self.tsiz]

    def read(self):
        '''
        Return MAS1, MAS2, and MAS3 values that represent this TLB entry
        '''
        mas1 = (self.valid << MAS1_VALID_SHIFT) | \
                (self.iprot << MAS1_IPROT_SHIFT) | \
                (self.tid << MAS1_TID_SHIFT) | \
                (self.ts << MAS1_TS_SHIFT) | \
                (self.tsiz << MAS1_TSIZ_SHIFT)

        mas2 = self.epn | \
                (self.flags << MAS2_FLAGS_SHIFT)

        mas3 = self.rpn | \
                (self.user << MAS3_USER_SHIFT) | \
                (self.perm << MAS3_PERM_SHIFT)

        return (mas1, mas2, mas3)

    def write(self, mas1, mas2, mas3):
        '''
        Update this TLB entry using the supplied MAS1, MAS2, and MAS3 SPR values
        '''

        # The IPROT bit does not protect a TLB entry from being overwritten,
        # just from being invalidated by the tlbivax instruction or by setting
        # the MMUCSR0[TLB1_FI] bit.

        self.config(valid=(mas1 & MAS1_VALID_MASK) >> MAS1_VALID_SHIFT,
                    iprot=(mas1 & MAS1_IPROT_MASK) >> MAS1_IPROT_SHIFT,
                    tid=(mas1 & MAS1_TID_MASK) >> MAS1_TID_SHIFT,
                    ts=(mas1 & MAS1_TS_MASK) >> MAS1_TS_SHIFT,
                    tsiz=(mas1 & MAS1_TSIZ_MASK) >> MAS1_TSIZ_SHIFT,
                    epn=mas2 & EPN_MASK,
                    flags=(mas2 & MAS2_FLAGS_MASK) >> MAS2_FLAGS_SHIFT,
                    rpn=mas3 & EPN_MASK,
                    user=(mas3 & MAS3_USER_MASK) >> MAS3_USER_SHIFT,
                    perm=(mas3 & MAS3_PERM_MASK) >> MAS3_PERM_SHIFT)

    def invalidate(self):
        '''
        Invalidate this TLB entry (unless IPROT is set)
        '''
        if self.iprot == 0:
            self.valid = 0


class PpcMMU:
    def __init__(self, emu):
        emu.modules['MMU'] = self

        # SPRs to related to the PPC/e200z7 MMU
        self.mmucfg = MMUCFG(emu)
        self.tlb0cfg = TLB0CFG(emu)
        self.tlb1cfg = TLB1CFG(emu)

        # The e200z7 ("zen" processor) always assumes TLB 1 is selected
        # regardless of the value actually used in MAS0[TBSEL]. To maintain
        # compatibility with how the e200z7 processor works don't attempt to
        # emulate having two TLBs.
        self._tlb = tuple(PpcTLBEntry(i) for i in range(32))

    def init(self, emu):
        self.emu = emu

        # The TLB entries can be invalidated selectively with the tlbivax
        # instruction, or all TLB entries can be invalidated by writing 1 to the
        # MMUCSR0[TLB1_FI] bit.
        self.emu.addSprWriteHandler(REG_MMUCSR0, self._mmucsr0WriteHandler)

        # Handle writes to the cache status and control SPRs
        self.emu.addSprWriteHandler(REG_L1CSR0, self._l1csr0WriteHandler)
        self.emu.addSprWriteHandler(REG_L1CSR1, self._l1csr1WriteHandler)

        # Set TLB1 entry 0 to the correct default values.
        #   (from "10.6.7 TLB load on reset" e200z759CRM.pdf page 570)
        #
        # It is not clear from the e200z7 documentation if the EPN/RPN page
        # should be the BAM memory range, but for now we assume it is
        self.tlbConfig(0, tsiz=PpcTlbPageSize.SIZE_4KB, epn=0xFFFFF000, rpn=0xFFFFF000)

    def i_tlbre(self, op):
        '''
        Update MAS1, MAS2, and MAS3 based on the TLB entry identified by
        MAS0(TLBSEL, ESEL)
        '''
        # Identify TLB entry
        mas0 = self.emu.getRegister(REG_MAS0)
        esel = (mas0 & MAS0_ESEL_MASK) >> MAS0_ESEL_SHIFT

        logger.debug('MMU: read mapping %d: 0x%08x -> 0x%08x (%s %s %s)',
                esel, self._tlb[esel].rpn, self._tlb[esel].epn,
                self._tlb[esel].size(),
                'VLE' if self._tlb[esel].vle else 'BookE',
                self._tlb[esel].perm.name)

        mas1, mas2, mas3 = self._tlb[esel].read()

        self.emu.setRegister(REG_MAS1, mas1)
        self.emu.setRegister(REG_MAS2, mas2)
        self.emu.setRegister(REG_MAS3, mas3)

    def i_tlbwe(self, op):
        '''
        Update the TLB entry identified by MAS0(TLBSEL, ESEL) with the values
        of MAS1, MAS2, and MAS3
        '''
        mas0 = self.emu.getRegister(REG_MAS0)
        esel = (mas0 & MAS0_ESEL_MASK) >> MAS0_ESEL_SHIFT

        mas1 = self.emu.getRegister(REG_MAS1)
        mas2 = self.emu.getRegister(REG_MAS2)
        mas3 = self.emu.getRegister(REG_MAS3)

        self._tlb[esel].write(mas1, mas2, mas3)

        logger.debug('MMU: write mapping %d: 0x%08x -> 0x%08x (%s %s %s)',
                esel, self._tlb[esel].rpn, self._tlb[esel].epn,
                self._tlb[esel].size(),
                'VLE' if self._tlb[esel].vle else 'BookE',
                self._tlb[esel].perm.name)

    def i_tlbsx(self, op):
        '''
        TLB search indexed
        '''
        ea = op.opers[0].getOperAddr(op, self.emu)

        # The tlbsx instruction will search using EPN[0:21] from the GPR
        # selected by the instruction, SAS (search AS bit) in MAS6, and SPID in
        # MAS6. If the search is successful, the given TLB entry information
        # will be loaded into MAS0-MAS3.
        #   (from "10.6.4 Searching the TLB" e200z759CRM.pdf page 569)
        #
        # MAS6[SAS] is used as the TS value
        # MAS6[SPID] is used as the TID value

        mas6 = self.emu.getRegister(REG_MAS6)
        spid = (mas6 & MAS6_SPID_MASK) >> MAS6_SPID_SHIFT
        sas = (mas6 & MAS6_SAS_MASK) >> MAS6_SAS_SHIFT

        entry = self.tlbFindEntry(ea, ts=sas, tid=spid)
        if entry is not None:
            mas1, mas2, mas3 = entry.read()

            logger.debug('MMU: search found mapping %d: 0x%08x -> 0x%08x (%s %s %s)',
                    esel, entry.rpn, entry.epn, entry.size(),
                    'VLE' if entry.vle else 'BookE', entry.perm.name)

            # Update MAS0 to indicate which entry this is
            mas0 = (1 << MAS0_TBSEL_SHIFT) | (entry.esel << MAS0_ESEL_SHIFT)
            self.emu.setRegister(REG_MAS0, mas0)

            # the VALID bit in MAS1 does not need to be explicitly set because
            # an entry cannot be found if it is not marked as valid.
            self.emu.setRegister(REG_MAS1, mas1)
            self.emu.setRegister(REG_MAS2, mas2)
            self.emu.setRegister(REG_MAS3, mas3)
        else:
            # If an entry was not found MAS0-MAS3 should be filled out with a
            # "potential next" TLB entry (similar to what happens during a TLB
            # miss)
            self.tlbMiss(ea, ts=sas, tid=spid)

    def i_tlbivax(self, op):
        '''
        Invalidate all TLB entries, indexed
        '''
        ea = op.opers[0].getOperAddr(op, self.emu)

        # From "10.5.4 TLB Invalidate (tlbivax) Instruction" (e200z759CRM.pdf
        # page 567), bit 29 of the EA is the INV_ALL flag. If set all TLB
        # entries should be invalidated, otherwise only the TLB ientries
        # identified by the most significant 22 bits of EA (the EPN) should be
        # invalidated.

        if ea & 0x00000004:
            matching_entries = self._tlb

        else:
            # Per the same section the TS and PID values are not used to
            # identify the TLB entry to invalidate, so all entries that match
            # should be invalidated.
            #
            # TODO: Best as I can tell the epn should be masked by the entry's
            # page-size determiend mask
            matching_entries = [e for e in self._tlb if ea & e.mask == e.epn & e.mask]

        for entry in matching_entries:
            logger.debug('MMU: invalidating mapping %d: 0x%08x -> 0x%08x (%s %s %s)',
                    entry.esel, entry.rpn, entry.epn, entry.size(),
                    'VLE' if entry.vle else 'BookE', entry.perm.name)

            entry.invalidate()

    def i_tlbsync(self, op):
        '''
        TLB syncronize (nothing to emulate)
        '''
        pass

    def _mmucsr0WriteHandler(self, emu, op):
        '''
        Only bit 30 (MMUCSR0[TLB1_FI]) can be written
        '''
        # If the TLB1_FI bit is set, invalidate all TLB entries
        if emu.getOperValue(op, 1) & 0x00000002:
            for entry in self._tlb:
                entry.invalidate()

        return 0

    def _l1csr0WriteHandler(self, emu, op):
        '''
        Ensure the data cache invalidate (L1CSR0[DCINV]) bit is always 0
        '''
        val = emu.getOperValue(op, 1) & 0XFFFFFFFFD
        return val

    def _l1csr1WriteHandler(self, emu, op):
        '''
        Ensure the instruction cache invalidate (L1CSR1[ICINV]) bit is always 0
        '''
        val = emu.getOperValue(op, 1) & 0XFFFFFFFFD
        return val

    def tlbFindEntry(self, va, ts=0, tid=0):
        '''
        Return a translated address if there is a valid TLB entry for the
        supplied virtual address.
        '''
        for entry in self._tlb:
            # Only check TLB entries that are:
            #   - valid
            #   - have a matching TS
            #   - have a TID that matches the current PID, or is 0 (global)
            if entry.valid and ts == entry.ts and entry.tid in (0, tid):
                # Not sure if this is necessary, but mask the EPN value as well
                # to ensure that only the bits that should be compared are
                # checked.
                if va & entry.mask == entry.epn & entry.mask:
                    return entry
        return None

    def tlbConfig(self, esel, valid=1, iprot=1, tid=0, ts=0, tsiz=0, epn=0,
                 flags=0, rpn=0, user=0, perm=PpcTlbPerm.SU_RWX):
        '''
        Utility to allow easier programmatic configuration of a TLB entry
        (such as during emulator initialization).

        The default values here are the default values (except for size, epn,
        and rpn) as defined by the e200z7 manual for the default TLB entry 0
        values.
        '''
        self._tlb[esel].config(valid, iprot, tid, ts, tsiz, epn, flags, rpn, user, perm)

        logger.debug('MMU: configured mapping %d: 0x%08x -> 0x%08x (%s %s %s)',
                esel, self._tlb[esel].rpn, self._tlb[esel].epn,
                self._tlb[esel].size(),
                'VLE' if self._tlb[esel].vle else 'BookE',
                self._tlb[esel].perm.name)

    def tlbMiss(self, va, ts, tid):
        # Per "10.6.5 TLB miss exception update" (e200z759CRM.pdf page 570):
        #   - Set MAS0[ESEL] with the value of MAS0[NV]
        #   - Populate MAS1 and MAS2 with the default values in MAS4
        #   - Zero out MAS3
        mas0 = self.emu.getRegister(REG_MAS0)
        mas4 = self.emu.getRegister(REG_MAS4)

        nv = (mas0 & MAS0_NV_MASK) >> MAS0_NV_SHIFT

        # No need to shift the default TLBSEL value to get it in the right
        # bit position to write to MAS0.
        new_mas0 = (mas4 & MAS4_TLBSELD_MASK) | (nv << MAS0_ESEL_SHIFT) | nv
        self.emu.setRegister(REG_MAS0, new_mas0)

        # New value of MAS1, leave the VALID and IPROT bits as 0

        # NOTE: It appears that older PPC implementations used a
        # MAS4[TIDSELD] field that could be used to pull a process ID from
        # one or more PIDx SPRs. However the e200z7 only appears to have a
        # PID0 SPR, and # the MAS4 documentation states that values other
        # than 0 should not be used.
        #
        # Newer versions of the PowerPC ISA/EREF no longer have this field.
        #
        # Either way just use the PID value in PID0 for the MAS1[TID] value
        # to set.  PID0 is used during address lookup so the cur_pid value
        # supplied to this function is the correct value to place in the
        # MAS1[TID] field

        # The TSIZD field does not need to be shifted to be written to
        # MAS1[TSIZ]
        new_mas1 = (tid << MAS1_TID_SHIFT) | (ts << MAS1_TS_SHIFT) | (mas4 & MAS4_TSIZED_MASK)
        self.emu.setRegister(REG_MAS1, new_mas1)

        # MAS4 has the correct default flag values at the right bit
        # positions to be written to MAS2
        new_mas2 = (va & EPN_MASK) | (mas4 & MAS4_FLAGSD_MASK)
        self.emu.setRegister(REG_MAS2, new_mas2)

        # Clear MAS3
        self.emu.setRegister(REG_MAS3, 0)

    def translateDataAddr(self, va):
        '''
        Return the physical address that matches the supplied virtual address
        based on the current PID and MSR[DS] flag.
        '''
        entry = self.getDataEntry(va)
        if entry is not None:
            return entry.rpn | (va & ~entry.mask)

        else:
            # TODO: replace standard envi SegmentationViolation with the correct
            # PowerPC-specific exception type.

            # Set the DEAR SPR to the address that caused the TLB miss
            #self.emu.setRegister(REG_DEAR, va)
            #self.tlbMiss(va, ts, pid)
            raise envi.SegmentationViolation(va)

    def translateInstrAddr(self, va):
        '''
        Return the physical address and VLE mode that matches the supplied
        virtual address based on the current PID and MSR[IS] flag.
        '''
        entry = self.getInstrEntry(va)
        if entry is not None:
            ea = entry.rpn | (va & ~entry.mask)
            return (ea, entry.vle)

        else:
            # TODO: replace standard envi SegmentationViolation with the correct
            # PowerPC-specific exception type.

            # Set the DEAR SPR to the address that caused the TLB miss
            #self.emu.setRegister(REG_DEAR, va)
            #self.tlbMiss(va, ts, pid)
            raise envi.SegmentationViolation(va)

    def getDataEntry(self, va):
        '''
        Return a matching TLB entry for the specified data fetch address
        '''
        ts = (self.emu.getRegister(REG_MSR) & MSR_DS_MASK) >> MSR_DS_SHIFT
        pid = self.emu.getRegister(REG_PID)
        entry = self.tlbFindEntry(va, ts=ts, tid=pid)
        return entry

    def getInstrEntry(self, va):
        '''
        Return a matching TLB entry for the specified instruction fetch address
        '''
        ts = (self.emu.getRegister(REG_MSR) & MSR_IS_MASK) >> MSR_IS_SHIFT
        pid = self.emu.getRegister(REG_PID)
        entry = self.tlbFindEntry(va, ts=ts, tid=pid)
        return entry

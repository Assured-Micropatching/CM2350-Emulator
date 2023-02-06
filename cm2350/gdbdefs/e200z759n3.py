import collections


reg_fmt = collections.OrderedDict([
    ('r0', (32, 0)),
    ('r1', (32, 1)),
    ('r2', (32, 2)),
    ('r3', (32, 3)),
    ('r4', (32, 4)),
    ('r5', (32, 5)),
    ('r6', (32, 6)),
    ('r7', (32, 7)),
    ('r8', (32, 8)),
    ('r9', (32, 9)),
    ('r10', (32, 10)),
    ('r11', (32, 11)),
    ('r12', (32, 12)),
    ('r13', (32, 13)),
    ('r14', (32, 14)),
    ('r15', (32, 15)),
    ('r16', (32, 16)),
    ('r17', (32, 17)),
    ('r18', (32, 18)),
    ('r19', (32, 19)),
    ('r20', (32, 20)),
    ('r21', (32, 21)),
    ('r22', (32, 22)),
    ('r23', (32, 23)),
    ('r24', (32, 24)),
    ('r25', (32, 25)),
    ('r26', (32, 26)),
    ('r27', (32, 27)),
    ('r28', (32, 28)),
    ('r29', (32, 29)),
    ('r30', (32, 30)),
    ('r31', (32, 31)),
    ('pc', (32, 32)),
    ('msr', (32, 33)),
    ('cr', (32, 34)),
    ('lr', (32, 35)),
    ('ctr', (32, 36)),
    ('xer', (32, 37)),
    ('ev0h', (32, 38)),
    ('ev1h', (32, 39)),
    ('ev2h', (32, 40)),
    ('ev3h', (32, 41)),
    ('ev4h', (32, 42)),
    ('ev5h', (32, 43)),
    ('ev6h', (32, 44)),
    ('ev7h', (32, 45)),
    ('ev8h', (32, 46)),
    ('ev9h', (32, 47)),
    ('ev10h', (32, 48)),
    ('ev11h', (32, 49)),
    ('ev12h', (32, 50)),
    ('ev13h', (32, 51)),
    ('ev14h', (32, 52)),
    ('ev15h', (32, 53)),
    ('ev16h', (32, 54)),
    ('ev17h', (32, 55)),
    ('ev18h', (32, 56)),
    ('ev19h', (32, 57)),
    ('ev20h', (32, 58)),
    ('ev21h', (32, 59)),
    ('ev22h', (32, 60)),
    ('ev23h', (32, 61)),
    ('ev24h', (32, 62)),
    ('ev25h', (32, 63)),
    ('ev26h', (32, 64)),
    ('ev27h', (32, 65)),
    ('ev28h', (32, 66)),
    ('ev29h', (32, 67)),
    ('ev30h', (32, 68)),
    ('ev31h', (32, 69)),
    ('acc', (64, 70)),
    ('spefscr', (32, 71)),
    ('DEC', (32, 72)),
    ('SRR0', (32, 73)),
    ('SRR1', (32, 74)),
    ('PID', (32, 75)),
    ('DECAR', (32, 76)),
    ('LPER', (32, 77)),
    ('LPERU', (32, 78)),
    ('CSRR0', (32, 79)),
    ('CSRR1', (32, 80)),
    ('DEAR', (32, 81)),
    ('ESR', (32, 82)),
    ('IVPR', (32, 83)),
    ('TBL', (32, 84)),
    ('TBU', (32, 85)),
    ('PIR', (32, 86)),
    ('PVR', (32, 87)),
    ('DBSR', (32, 88)),
    ('DBSRWR', (32, 89)),
    ('EPCR', (32, 90)),
    ('DBCR0', (32, 91)),
    ('DBCR1', (32, 92)),
    ('DBCR2', (32, 93)),
    ('MSRP', (32, 94)),
    ('IAC1', (32, 95)),
    ('IAC2', (32, 96)),
    ('IAC3', (32, 97)),
    ('IAC4', (32, 98)),
    ('DAC1', (32, 99)),
    ('DAC2', (32, 100)),
    ('DVC1', (32, 101)),
    ('DVC2', (32, 102)),
    ('TSR', (32, 103)),
    ('LPIDR', (32, 104)),
    ('TCR', (32, 105)),
    ('IVOR0', (32, 106)),
    ('IVOR1', (32, 107)),
    ('IVOR2', (32, 108)),
    ('IVOR3', (32, 109)),
    ('IVOR4', (32, 110)),
    ('IVOR5', (32, 111)),
    ('IVOR6', (32, 112)),
    ('IVOR7', (32, 113)),
    ('IVOR8', (32, 114)),
    ('IVOR9', (32, 115)),
    ('IVOR10', (32, 116)),
    ('IVOR11', (32, 117)),
    ('IVOR12', (32, 118)),
    ('IVOR13', (32, 119)),
    ('IVOR14', (32, 120)),
    ('IVOR15', (32, 121)),
    ('IVOR38', (32, 122)),
    ('IVOR39', (32, 123)),
    ('IVOR40', (32, 124)),
    ('IVOR41', (32, 125)),
    ('IVOR42', (32, 126)),
    ('TENSR', (32, 127)),
    ('TENS', (32, 128)),
    ('TENC', (32, 129)),
    ('TIR', (32, 130)),
    ('L1CFG0', (32, 131)),
    ('L1CFG1', (32, 132)),
    ('NPIDR5', (32, 133)),
    ('L2CFG0', (32, 134)),
    ('IVOR32', (32, 135)),
    ('IVOR33', (32, 136)),
    ('IVOR34', (32, 137)),
    ('IVOR35', (32, 138)),
    ('IVOR36', (32, 139)),
    ('IVOR37', (32, 140)),
    ('DBCR3', (32, 141)),
    ('DBCNT', (32, 142)),
    ('DBCR4', (32, 143)),
    ('DBCR5', (32, 144)),
    ('MCARU', (32, 145)),
    ('MCSRR0', (32, 146)),
    ('MCSRR1', (32, 147)),
    ('MCSR', (32, 148)),
    ('MCAR', (32, 149)),
    ('DSRR0', (32, 150)),
    ('DSRR1', (32, 151)),
    ('DDAM', (32, 152)),
    ('L1CSR2', (32, 153)),
    ('L1CSR3', (32, 154)),
    ('MAS0', (32, 155)),
    ('MAS1', (32, 156)),
    ('MAS2', (32, 157)),
    ('MAS3', (32, 158)),
    ('MAS4', (32, 159)),
    ('MAS6', (32, 160)),
    ('PID1', (32, 161)),
    ('PID2', (32, 162)),
    ('EDBRAC0', (32, 163)),
    ('TLB0CFG', (32, 164)),
    ('TLB1CFG', (32, 165)),
    ('TLB2CFG', (32, 166)),
    ('TLB3CFG', (32, 167)),
    ('DBRR0', (32, 168)),
    ('EPR', (32, 169)),
    ('L2ERRINTEN', (32, 170)),
    ('L2ERRATTR', (32, 171)),
    ('L2ERRADDR', (32, 172)),
    ('L2ERREADDR', (32, 173)),
    ('L2ERRCTL', (32, 174)),
    ('L2ERRDIS', (32, 175)),
    ('L1FINV1', (32, 176)),
    ('DEVENT', (32, 177)),
    ('NSPD', (32, 178)),
    ('NSPC', (32, 179)),
    ('L2ERRINJHI', (32, 180)),
    ('L2ERRINJLO', (32, 181)),
    ('L2ERRINJCTL', (32, 182)),
    ('L2CAPTDATAHI', (32, 183)),
    ('L2CAPTDATALO', (32, 184)),
    ('L2CAPTECC', (32, 185)),
    ('L2ERRDET', (32, 186)),
    ('HID0', (32, 187)),
    ('HID1', (32, 188)),
    ('L1CSR0', (32, 189)),
    ('L1CSR1', (32, 190)),
    ('MMUCSR0', (32, 191)),
    ('BUCSR', (32, 192)),
    ('MMUCFG', (32, 193)),
    ('L1FINV0', (32, 194)),
    ('L2CSR0', (32, 195)),
    ('L2CSR1', (32, 196)),
    ('PWRMGTCR0', (32, 197)),
    ('SCCSRBAR', (32, 198)),
    ('SVR', (32, 199)),
])

# r0 through xer, but the size is the size of the asciified GDB formatted 
# packet.
# 32 GPRs, 6 system registers = 38 registers
# All registers for this interface are 32bits wide, 4 bytes = 8 characters
reg_pkt_size = (38 * 8, 38)

target_xml = b'''<?xml version="1.0"?>
<!DOCTYPE target SYSTEM "gdb-target.dtd">
<target>
  <architecture>powerpc:vle</architecture>
  <feature name="org.gnu.gdb.power.core">
    <reg bitsize="32" name="r0" regnum="0" />
    <reg bitsize="32" name="r1" regnum="1" />
    <reg bitsize="32" name="r2" regnum="2" />
    <reg bitsize="32" name="r3" regnum="3" />
    <reg bitsize="32" name="r4" regnum="4" />
    <reg bitsize="32" name="r5" regnum="5" />
    <reg bitsize="32" name="r6" regnum="6" />
    <reg bitsize="32" name="r7" regnum="7" />
    <reg bitsize="32" name="r8" regnum="8" />
    <reg bitsize="32" name="r9" regnum="9" />
    <reg bitsize="32" name="r10" regnum="10" />
    <reg bitsize="32" name="r11" regnum="11" />
    <reg bitsize="32" name="r12" regnum="12" />
    <reg bitsize="32" name="r13" regnum="13" />
    <reg bitsize="32" name="r14" regnum="14" />
    <reg bitsize="32" name="r15" regnum="15" />
    <reg bitsize="32" name="r16" regnum="16" />
    <reg bitsize="32" name="r17" regnum="17" />
    <reg bitsize="32" name="r18" regnum="18" />
    <reg bitsize="32" name="r19" regnum="19" />
    <reg bitsize="32" name="r20" regnum="20" />
    <reg bitsize="32" name="r21" regnum="21" />
    <reg bitsize="32" name="r22" regnum="22" />
    <reg bitsize="32" name="r23" regnum="23" />
    <reg bitsize="32" name="r24" regnum="24" />
    <reg bitsize="32" name="r25" regnum="25" />
    <reg bitsize="32" name="r26" regnum="26" />
    <reg bitsize="32" name="r27" regnum="27" />
    <reg bitsize="32" name="r28" regnum="28" />
    <reg bitsize="32" name="r29" regnum="29" />
    <reg bitsize="32" name="r30" regnum="30" />
    <reg bitsize="32" name="r31" regnum="31" />
    <reg bitsize="32" name="pc" regnum="32" type="code_ptr" />
    <reg bitsize="32" name="msr" regnum="33" />
    <reg bitsize="32" name="cr" regnum="34" />
    <reg bitsize="32" name="lr" regnum="35" />
    <reg bitsize="32" name="ctr" regnum="36" />
    <reg bitsize="32" name="xer" regnum="37" />
  </feature>
  <feature name="org.gnu.gdb.power.spe">
    <reg bitsize="32" name="ev0h" regnum="38" />
    <reg bitsize="32" name="ev1h" regnum="39" />
    <reg bitsize="32" name="ev2h" regnum="40" />
    <reg bitsize="32" name="ev3h" regnum="41" />
    <reg bitsize="32" name="ev4h" regnum="42" />
    <reg bitsize="32" name="ev5h" regnum="43" />
    <reg bitsize="32" name="ev6h" regnum="44" />
    <reg bitsize="32" name="ev7h" regnum="45" />
    <reg bitsize="32" name="ev8h" regnum="46" />
    <reg bitsize="32" name="ev9h" regnum="47" />
    <reg bitsize="32" name="ev10h" regnum="48" />
    <reg bitsize="32" name="ev11h" regnum="49" />
    <reg bitsize="32" name="ev12h" regnum="50" />
    <reg bitsize="32" name="ev13h" regnum="51" />
    <reg bitsize="32" name="ev14h" regnum="52" />
    <reg bitsize="32" name="ev15h" regnum="53" />
    <reg bitsize="32" name="ev16h" regnum="54" />
    <reg bitsize="32" name="ev17h" regnum="55" />
    <reg bitsize="32" name="ev18h" regnum="56" />
    <reg bitsize="32" name="ev19h" regnum="57" />
    <reg bitsize="32" name="ev20h" regnum="58" />
    <reg bitsize="32" name="ev21h" regnum="59" />
    <reg bitsize="32" name="ev22h" regnum="60" />
    <reg bitsize="32" name="ev23h" regnum="61" />
    <reg bitsize="32" name="ev24h" regnum="62" />
    <reg bitsize="32" name="ev25h" regnum="63" />
    <reg bitsize="32" name="ev26h" regnum="64" />
    <reg bitsize="32" name="ev27h" regnum="65" />
    <reg bitsize="32" name="ev28h" regnum="66" />
    <reg bitsize="32" name="ev29h" regnum="67" />
    <reg bitsize="32" name="ev30h" regnum="68" />
    <reg bitsize="32" name="ev31h" regnum="69" />
    <reg bitsize="64" name="acc" regnum="70" />
    <reg bitsize="32" name="spefscr" regnum="71" />
  </feature>
  <feature name="org.gnu.gdb.power.spr">
    <reg bitsize="32" name="DEC" regnum="72" />
    <reg bitsize="32" name="SRR0" regnum="73" />
    <reg bitsize="32" name="SRR1" regnum="74" />
    <reg bitsize="32" name="PID" regnum="75" />
    <reg bitsize="32" name="DECAR" regnum="76" />
    <reg bitsize="32" name="LPER" regnum="77" />
    <reg bitsize="32" name="LPERU" regnum="78" />
    <reg bitsize="32" name="CSRR0" regnum="79" />
    <reg bitsize="32" name="CSRR1" regnum="80" />
    <reg bitsize="32" name="DEAR" regnum="81" />
    <reg bitsize="32" name="ESR" regnum="82" />
    <reg bitsize="32" name="IVPR" regnum="83" />
    <reg bitsize="32" name="TBL" regnum="84" />
    <reg bitsize="32" name="TBU" regnum="85" />
    <reg bitsize="32" name="PIR" regnum="86" />
    <reg bitsize="32" name="PVR" regnum="87" />
    <reg bitsize="32" name="DBSR" regnum="88" />
    <reg bitsize="32" name="DBSRWR" regnum="89" />
    <reg bitsize="32" name="EPCR" regnum="90" />
    <reg bitsize="32" name="DBCR0" regnum="91" />
    <reg bitsize="32" name="DBCR1" regnum="92" />
    <reg bitsize="32" name="DBCR2" regnum="93" />
    <reg bitsize="32" name="MSRP" regnum="94" />
    <reg bitsize="32" name="IAC1" regnum="95" />
    <reg bitsize="32" name="IAC2" regnum="96" />
    <reg bitsize="32" name="IAC3" regnum="97" />
    <reg bitsize="32" name="IAC4" regnum="98" />
    <reg bitsize="32" name="DAC1" regnum="99" />
    <reg bitsize="32" name="DAC2" regnum="100" />
    <reg bitsize="32" name="DVC1" regnum="101" />
    <reg bitsize="32" name="DVC2" regnum="102" />
    <reg bitsize="32" name="TSR" regnum="103" />
    <reg bitsize="32" name="LPIDR" regnum="104" />
    <reg bitsize="32" name="TCR" regnum="105" />
    <reg bitsize="32" name="IVOR0" regnum="106" />
    <reg bitsize="32" name="IVOR1" regnum="107" />
    <reg bitsize="32" name="IVOR2" regnum="108" />
    <reg bitsize="32" name="IVOR3" regnum="109" />
    <reg bitsize="32" name="IVOR4" regnum="110" />
    <reg bitsize="32" name="IVOR5" regnum="111" />
    <reg bitsize="32" name="IVOR6" regnum="112" />
    <reg bitsize="32" name="IVOR7" regnum="113" />
    <reg bitsize="32" name="IVOR8" regnum="114" />
    <reg bitsize="32" name="IVOR9" regnum="115" />
    <reg bitsize="32" name="IVOR10" regnum="116" />
    <reg bitsize="32" name="IVOR11" regnum="117" />
    <reg bitsize="32" name="IVOR12" regnum="118" />
    <reg bitsize="32" name="IVOR13" regnum="119" />
    <reg bitsize="32" name="IVOR14" regnum="120" />
    <reg bitsize="32" name="IVOR15" regnum="121" />
    <reg bitsize="32" name="IVOR38" regnum="122" />
    <reg bitsize="32" name="IVOR39" regnum="123" />
    <reg bitsize="32" name="IVOR40" regnum="124" />
    <reg bitsize="32" name="IVOR41" regnum="125" />
    <reg bitsize="32" name="IVOR42" regnum="126" />
    <reg bitsize="32" name="TENSR" regnum="127" />
    <reg bitsize="32" name="TENS" regnum="128" />
    <reg bitsize="32" name="TENC" regnum="129" />
    <reg bitsize="32" name="TIR" regnum="130" />
    <reg bitsize="32" name="L1CFG0" regnum="131" />
    <reg bitsize="32" name="L1CFG1" regnum="132" />
    <reg bitsize="32" name="NPIDR5" regnum="133" />
    <reg bitsize="32" name="L2CFG0" regnum="134" />
    <reg bitsize="32" name="IVOR32" regnum="135" />
    <reg bitsize="32" name="IVOR33" regnum="136" />
    <reg bitsize="32" name="IVOR34" regnum="137" />
    <reg bitsize="32" name="IVOR35" regnum="138" />
    <reg bitsize="32" name="IVOR36" regnum="139" />
    <reg bitsize="32" name="IVOR37" regnum="140" />
    <reg bitsize="32" name="DBCR3" regnum="141" />
    <reg bitsize="32" name="DBCNT" regnum="142" />
    <reg bitsize="32" name="DBCR4" regnum="143" />
    <reg bitsize="32" name="DBCR5" regnum="144" />
    <reg bitsize="32" name="MCARU" regnum="145" />
    <reg bitsize="32" name="MCSRR0" regnum="146" />
    <reg bitsize="32" name="MCSRR1" regnum="147" />
    <reg bitsize="32" name="MCSR" regnum="148" />
    <reg bitsize="32" name="MCAR" regnum="149" />
    <reg bitsize="32" name="DSRR0" regnum="150" />
    <reg bitsize="32" name="DSRR1" regnum="151" />
    <reg bitsize="32" name="DDAM" regnum="152" />
    <reg bitsize="32" name="L1CSR2" regnum="153" />
    <reg bitsize="32" name="L1CSR3" regnum="154" />
    <reg bitsize="32" name="MAS0" regnum="155" />
    <reg bitsize="32" name="MAS1" regnum="156" />
    <reg bitsize="32" name="MAS2" regnum="157" />
    <reg bitsize="32" name="MAS3" regnum="158" />
    <reg bitsize="32" name="MAS4" regnum="159" />
    <reg bitsize="32" name="MAS6" regnum="160" />
    <reg bitsize="32" name="PID1" regnum="161" />
    <reg bitsize="32" name="PID2" regnum="162" />
    <reg bitsize="32" name="EDBRAC0" regnum="163" />
    <reg bitsize="32" name="TLB0CFG" regnum="164" />
    <reg bitsize="32" name="TLB1CFG" regnum="165" />
    <reg bitsize="32" name="TLB2CFG" regnum="166" />
    <reg bitsize="32" name="TLB3CFG" regnum="167" />
    <reg bitsize="32" name="DBRR0" regnum="168" />
    <reg bitsize="32" name="EPR" regnum="169" />
    <reg bitsize="32" name="L2ERRINTEN" regnum="170" />
    <reg bitsize="32" name="L2ERRATTR" regnum="171" />
    <reg bitsize="32" name="L2ERRADDR" regnum="172" />
    <reg bitsize="32" name="L2ERREADDR" regnum="173" />
    <reg bitsize="32" name="L2ERRCTL" regnum="174" />
    <reg bitsize="32" name="L2ERRDIS" regnum="175" />
    <reg bitsize="32" name="L1FINV1" regnum="176" />
    <reg bitsize="32" name="DEVENT" regnum="177" />
    <reg bitsize="32" name="NSPD" regnum="178" />
    <reg bitsize="32" name="NSPC" regnum="179" />
    <reg bitsize="32" name="L2ERRINJHI" regnum="180" />
    <reg bitsize="32" name="L2ERRINJLO" regnum="181" />
    <reg bitsize="32" name="L2ERRINJCTL" regnum="182" />
    <reg bitsize="32" name="L2CAPTDATAHI" regnum="183" />
    <reg bitsize="32" name="L2CAPTDATALO" regnum="184" />
    <reg bitsize="32" name="L2CAPTECC" regnum="185" />
    <reg bitsize="32" name="L2ERRDET" regnum="186" />
    <reg bitsize="32" name="HID0" regnum="187" />
    <reg bitsize="32" name="HID1" regnum="188" />
    <reg bitsize="32" name="L1CSR0" regnum="189" />
    <reg bitsize="32" name="L1CSR1" regnum="190" />
    <reg bitsize="32" name="MMUCSR0" regnum="191" />
    <reg bitsize="32" name="BUCSR" regnum="192" />
    <reg bitsize="32" name="MMUCFG" regnum="193" />
    <reg bitsize="32" name="L1FINV0" regnum="194" />
    <reg bitsize="32" name="L2CSR0" regnum="195" />
    <reg bitsize="32" name="L2CSR1" regnum="196" />
    <reg bitsize="32" name="PWRMGTCR0" regnum="197" />
    <reg bitsize="32" name="SCCSRBAR" regnum="198" />
    <reg bitsize="32" name="SVR" regnum="199" />
  </feature>
</target>'''

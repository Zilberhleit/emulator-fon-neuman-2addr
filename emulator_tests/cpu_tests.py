import unittest

from emulator_src.cpu import CPU

NOP, MOV, LOAD, STORE, ADD, SUB, MUL, DIV = 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07
AND_, OR_, XOR, NOT, SHL, SHR, CMP, JMP = 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F
JZ, JNZ, JC, JNC, JS, JNS, JO, JNO = 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17
HLT = 0x18

IMM, DIR, REG, IND = 0, 1, 2, 3


def enc(opcode, am1=0, op1=0, am2=0, op2=0):
    return (opcode << 26) | (am1 << 24) | (am2 << 22) | ((op1 & 0x7FF) << 11) | (op2 & 0x7FF)


def MOV_ri(reg, imm): return enc(MOV, REG, reg, IMM, imm & 0x7FF)
def MOV_rr(dst, src): return enc(MOV, REG, dst, REG, src)
def ADD_rr(dst, src): return enc(ADD,  REG, dst, REG, src)
def ADD_ri(dst, imm): return enc(ADD,  REG, dst, IMM, imm & 0x7FF)
def SUB_rr(dst, src): return enc(SUB,  REG, dst, REG, src)
def SUB_ri(dst, imm): return enc(SUB,  REG, dst, IMM, imm & 0x7FF)
def CMP_ri(r, imm): return enc(CMP,  REG, r,   IMM, imm & 0x7FF)
def CMP_rr(a, b): return enc(CMP,  REG, a,   REG, b)
def MUL_rr(dst, src): return enc(MUL,  REG, dst, REG, src)
def LOAD_dir(reg, a): return enc(LOAD, REG, reg, DIR, a)
def LOAD_ind(reg, r): return enc(LOAD, REG, reg, IND, r)
def STORE_dir(a, r): return enc(STORE,DIR, a,   REG, r)
def JMP_abs(addr): return enc(JMP, DIR, addr)
def JZ_abs(addr): return enc(JZ,  DIR, addr)
def JNZ_abs(addr): return enc(JNZ, DIR, addr)
def HLT_(): return enc(HLT)


def run(cpu, limit=10_000):
    steps = 0
    while not cpu.halted and steps < limit:
        cpu.step()
        steps += 1
    assert cpu.halted, "Eternal Cycle"
    return steps


class testMOV(unittest.TestCase):
    def setUp(self):
        self.cpu = CPU()

    def test_mov_immediate(self):
        self.cpu.load_program([MOV_ri(0, 42), HLT_()])
        run(self.cpu)
        self.assertEqual(self.cpu.registers[0], 42)

    def test_mov_neg_immediate(self):
        self.cpu.load_program([MOV_ri(0, -5), HLT_()])
        run(self.cpu)
        self.assertEqual(self.cpu.registers[0], -5)

    def test_mov_reg_to_reg(self):
        self.cpu.load_program([MOV_ri(1, 42), MOV_rr(0, 1), HLT_()])
        run(self.cpu)
        self.assertEqual(self.cpu.registers[0], 42)
        self.assertEqual(self.cpu.registers[1], 42)


class TestArithmetic(unittest.TestCase):
    def setUp(self):
        self.cpu = CPU()

    def test_add_basic(self):
        self.cpu.load_program([MOV_ri(0, 5), MOV_ri(1, 3), ADD_rr(0, 1), HLT_()])
        run(self.cpu)
        self.assertEqual(self.cpu.registers[0], 8)

    def test_add_zero_flag(self):
        self.cpu.load_program([MOV_ri(0,5), MOV_ri(1, -5), ADD_rr(0,1), HLT_()])
        run(self.cpu)
        self.assertEqual(self.cpu.flags['Z'], 1)

    def test_add_overflow(self):
        self.cpu.registers[0] = 0x7FFFFFFF
        self.cpu.load_program([ADD_ri(0,1), HLT_()])
        run(self.cpu)
        self.assertEqual(self.cpu.flags['O'], 1)
        self.assertEqual(self.cpu.flags['S'], 1)


class TestCMP(unittest.TestCase):
    def setUp(self):
        self.cpu = CPU()

    def test_cmp_does_not_modify_op(self):
        self.cpu.load_program([MOV_ri(0,5), MOV_ri(1,3), CMP_rr(0, 1), HLT_()])
        run(self.cpu)
        self.assertEqual(self.cpu.registers[0], 5)
        self.assertEqual(self.cpu.registers[1], 3)

    def test_cmp_equal(self):
        self.cpu.load_program([MOV_ri(0, 7), CMP_ri(0, 7), HLT_()])
        run(self.cpu)
        self.assertEqual(self.cpu.flags['Z'], 1)


class TestJumps(unittest.TestCase):
    def setUp(self):
        self.cpu = CPU()

    def test_jz_taken(self):
        prog = [MOV_ri(0,0), CMP_ri(0,0), JZ_abs(10),
                HLT_(), HLT_(), HLT_(), HLT_(), HLT_(), HLT_(), HLT_(), HLT_()]
        self.cpu.load_program(prog)
        self.cpu.step(); self.cpu.step(); self.cpu.step()
        self.assertEqual(self.cpu.pc, 10)


if __name__ == '__main__':
    unittest.main()
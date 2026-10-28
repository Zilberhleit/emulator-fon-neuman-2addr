import unittest
from emulator_src.assembler import Assembler
from emulator_src.cpu import CPU


class TestParseOperands(unittest.TestCase):
    def setUp(self):
        self.assem = Assembler()

    def test_reg(self):
        self.assertEqual(self.assem._parse_operand("R3"), (2,3))

    def test_imm_positive(self):
        self.assertEqual(self.assem._parse_operand("#42"), (0, 42))

    def test_imm_negative(self):
        self.assertEqual(self.assem._parse_operand("#-1"), (0,0x7FF))

    def test_direct(self):
        self.assertEqual(self.assem._parse_operand("[100]"), (1,100))

    def test_indirect_reg(self):
        self.assertEqual(self.assem._parse_operand("[R3]"), (3,3))

    def test_unknown_ref(self):
        with self.assertRaises(ValueError):
            self.assem._parse_operand("R9")


class TestAssembleBasic(unittest.TestCase):
    def test_nop_hlt(self):
        prog = Assembler().assemble("NOP\nHLT")
        self.assertEqual(prog, [0x00 << 26, 0x18 << 26])

    def test_mov_immediate(self):
        prog = Assembler().assemble("MOV R0, #42")
        expected = (0x01 << 26) | (2 << 24) | (0 << 22) | (0 << 11) | 42
        self.assertEqual(prog[0], expected)

    def test_comment_ignored(self):
        prog = Assembler().assemble("MOV R0, #1 ; note\n//header \nHLT")
        self.assertEqual(len(prog), 2)

    def test_empty_input(self):
        self.assertEqual(Assembler().assemble(""), [])
        self.assertEqual(Assembler().assemble("\n\n\n"), [])

    def test_unknown_mnemonic(self):
        with self.assertRaises(ValueError):
            Assembler().assemble("FOO R0, R1")


class TestAssembleLabels(unittest.TestCase):
    def test_forward_label(self):
        text = "JMP end\nHLT\nend:\nHLT"
        prog = Assembler().assemble(text)
        self.assertEqual(prog[0], (0x0F << 26) | (1 << 24) | (2 << 11))

    def test_backward_label(self):
        text = "loop:\nHLT\nJMP loop"
        prog = Assembler().assemble(text)
        self.assertEqual(prog[1], (0x0F << 26) | (1 << 24) | 0)

    def test_duplicate_label(self):
        with self.assertRaises(ValueError):
            Assembler().assemble("loop:\nloop:\nHLT")

    def test_undefined_label(self):
        with self.assertRaises(ValueError):
            Assembler().assemble('JMP nowhere')

    def test_label_on_same_line(self):
        text = "loop: HLT\nJMP loop"
        prog = Assembler().assemble(text)
        self.assertEqual(len(prog), 2)
        self.assertEqual(prog[1], (0x0F << 26) | (1 << 24) | 0)


class TestAssemblerCpuSymmetry(unittest.TestCase):
    def test_all_opcodes_known_by_cpu(self):
        a = Assembler()
        for name, code in a.opcodes.items():
            text = f"{name} R0, #1"
            try:
                prog = a.assemble(text)
            except ValueError:
                continue
            cpu = CPU()
            cpu.load_program(prog)
            cpu.step()
            if name != 'HLT':
                self.assertFalse(cpu.halted, f"CPU не знает {name}={hex(code)}")

    def test_pack_decode_symmetry(self):
        a = Assembler()
        c = CPU()
        for opcode, am1, am2, op1, op2 in [
            (0x01, 2, 0, 3, 42),
            (0x04, 2, 2, 0, 1),
            (0x0F, 1, 0, 100, 0)
        ]:
            instr = a._pack(opcode, am1, op1, am2, op2)
            decoded = c.decode(instr)
            self.assertEqual(decoded, (opcode, am1, am2, op1, op2))


class TestEndToEnd(unittest.TestCase):
    def test_simple_loop(self):
        text = """
            MOV R0, #0
            MOV R1, #5
        loop:
            CMP R1, #0
            JZ done
            ADD R0, R1
            SUB R1, #1
            JMP loop
        done:
            HLT
        """
        prog = Assembler().assemble(text)
        cpu = CPU()
        cpu.load_program(prog)
        while not cpu.halted:
            cpu.step()
        self.assertEqual(cpu.registers[0], 15)
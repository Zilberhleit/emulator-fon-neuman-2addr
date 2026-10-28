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

    def test_sum_10_elements(self):
        """Тест сценариев из варианта"""
        text = """
            MOV R2, #0
            LOAD R1, [501]
            MOV R0, #502
        loop:
            CMP R1, #0
            JZ end
            LOAD R3, [R0]
            ADD R2, R3
            ADD R0, #1
            SUB R1, #1
            JMP loop
        end:
            STORE [600], R2
            HLT
        """
        prog = Assembler().assemble(text)
        cpu = CPU()
        cpu.load_program(prog)

        cpu.memory[500] = 1
        cpu.memory[501] = 10
        for i in range(10):
            cpu.memory[502 + i] = (i + 1) * 3

        while not cpu.halted:
            cpu.step()

        self.assertEqual(cpu.memory[600], 165)

    def test_sum_single_element(self):
        text = """
            MOV R2, #0
            LOAD R1, [501]
            MOV R0, #502
        loop:
            CMP R1, #0
            JZ end
            LOAD R3, [R0]
            ADD R2, R3
            ADD R0, #1
            SUB R1, #1
            JMP loop
        end:
            STORE [600], R2
            HLT
        """
        prog = Assembler().assemble(text)
        cpu = CPU()
        cpu.load_program(prog)
        cpu.memory[500] = 1
        cpu.memory[501] = 1
        cpu.memory[502] = 42

        while not cpu.halted:
            cpu.step()
        self.assertEqual(cpu.memory[600], 42)

    def _run_convolution(self, arr_a, arr_b):
        text = """
            MOV R2, #0
            MOV R6, #701
            MOV R7, #721
            MOV R4, #10
        loop:
            CMP R4, #0
            JZ end
            LOAD R0, [R6]
            LOAD R1, [R7]
            MUL R0, R1
            ADD R2, R0
            ADD R6, #1
            ADD R7, #1
            SUB R4, #1
            JMP loop
        end:
            STORE [800], R2
            HLT
        """
        prog = Assembler().assemble(text)
        cpu = CPU()
        cpu.load_program(prog)

        cpu.memory[700] = 1

        for i, v in enumerate(arr_a):
            cpu.memory[701 + i] = v
        cpu.memory[720] = 2
        for i, v in enumerate(arr_b):
            cpu.memory[721 + i] = v

        while not cpu.halted:
            cpu.step()
        return cpu.memory[800]

    def test_positive_arrays(self):
        arr_a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        arr_b = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
        self.assertEqual(self._run_convolution(arr_a, arr_b), 770)

    def test_zeros_arrays(self):
        a = [0] * 10
        b = [0] * 10
        self.assertEqual(self._run_convolution(a,b), 0)

    def test_negative_arrays(self):
        arr_a = [-1, -2, -3, -4, -5, -6, -7, -8, -9, -10]
        arr_b = [-2, -4, -6, -8, -10, -12, -14, -16, -18, -20]
        self.assertEqual(self._run_convolution(arr_a,arr_b), 770)


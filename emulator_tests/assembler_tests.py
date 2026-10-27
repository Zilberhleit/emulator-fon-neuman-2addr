import unittest
from emulator_src.assembler import Assembler


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


class TestAssembleLabels(unittest.TestCase):
    def test_forward_label(self):
        text = "JMP end\nHLT\nend:\nHLT"
        prog = Assembler().assemble(text)
        self.assertEqual(prog[0], (0x0F << 26) | (1 << 24) | (2 << 11))
class Assembler:
    def __init__(self):
        self.opcodes = {
            'NOP': 0x00, 'MOV': 0x01, 'LOAD': 0x02, 'STORE': 0x03,
            'ADD': 0x04, 'SUB': 0x05, 'MUL': 0x06, 'DIV': 0x07,
            'AND_': 0x08, 'OR_': 0x09, 'XOR': 0x0A, 'NOT': 0x0B,
            'SHL': 0x0C, 'SHR': 0x0D, 'CMP': 0x0E, 'JMP': 0x0F,
            'JZ': 0x10, 'JNZ': 0x11, 'JC': 0x12, 'JNC': 0x13,
            'JS': 0x14, 'JNS': 0x15, 'JO': 0x16, 'JNO': 0x17,
            'HLT': 0x18
        }
        self.regs = {f'R{i}': i for i in range(8)}

    def _strip_comment(self, line):
        for marker in (';', '//'):
            if marker in line:
                line = line.split(marker, 1)[0]
        return line

    def _split_label(self, line):
        if ':' in line:
            label, rest = line.split(':', 1)
            return label.strip(), rest.strip()
        return None, line.strip()

    def _parse_operand(self, op_str):
        op_str = op_str.strip()
        if not op_str:
            return (0, 0)
        # Регистр R0..R7
        if op_str in self.regs:
            return (2, self.regs[op_str])
        if (op_str[0] in 'Rr') and op_str[1:].isdigit():
            raise ValueError(f"Неизвестный регистр {op_str}")
        # Непосредственное значение #5, #-5
        if op_str.startswith('#'):
            try:
                val = int(op_str[1:], 0)
            except ValueError:
                raise ValueError(f'Некорректное непосредственное значение, {op_str}')
            val = val & 0x7FF
            return (0, val)
        # Косвенное-регистровая [R3]
        if op_str.startswith('[') and op_str.endswith(']'):
            inner = op_str[1:-1].strip()
            if inner in self.regs:
                return (3, self.regs[inner])
            try:
                addr = int(inner, 0)
            except ValueError:
                raise ValueError(f'Некорректный адрес в скобках [{inner}]')
            return (1, addr & 0x7FF)
        # Прямое число 100, 0x64
        try:
            addr = int(op_str, 0)
        except ValueError:
            pass

        return (1, op_str)

    def _parse_operands(self, op_str):
        if not op_str.strip():
            return []
        parts = [s.strip() for s in op_str.split(',')]
        return [self._parse_operand(p) for p in parts]

    def _resolve_operand(self, am, val, labels):
        if isinstance(val, str):
            if val not in labels:
                raise ValueError(f'Неопределённая метка {val}')
            return (1, labels[val])
        return (am, val)

    def _pack(self, opcode, am1, op1, am2, op2):
        return (opcode << 26) | (am1 << 24) | (am2 << 22) | ((op1 & 0x7FF) << 11) | (op2 & 0x7FF)

    def assemble(self, code):
        lines = code.split('\n')
        labels = {}

        addr = 0
        for raw in lines:
            line = self._strip_comment(raw)
            if not line.strip():
                continue
            label, rest = self._split_label(line)
            if label:
                if label in labels:
                    raise ValueError(f'Метка {label} уже опрделена')
                labels[label] = addr
            if rest:
                addr += 1

        program = []
        for raw in lines:
            line = self._strip_comment(raw)
            label, rest = self._split_label(line)
            if not rest:
                continue
            parts = rest.split(None, 1)
            mnemonic = parts[0].upper()
            if mnemonic not in self.opcodes:
                raise ValueError(f'Неизвестная инструкция {mnemonic}')
            opcode = self.opcodes[mnemonic]

            op_str = parts[1] if len(parts) > 1 else ""
            operands = self._parse_operands(op_str)

            if len(operands) > 2:
                raise ValueError(f'Слишком много операндов в {rest}')

            am1, op1 = operands[0] if len(operands) >= 1 else (0,0)
            am2, op2 = operands[1] if len(operands) >= 2 else (0,0)

            am1, op1 = self._resolve_operand(am1, op1, labels)
            am2, op2 = self._resolve_operand(am2, op2, labels)

            program.append(self._pack(opcode, am1, op1, am2, op2))

        return program

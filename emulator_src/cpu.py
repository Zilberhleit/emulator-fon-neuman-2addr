class CPU:
    def __init__(self):
        self.memory = [0] * 2048
        self.registers = [0] * 8
        self.pc = 0 # счётчик команд
        self.ir = 0 # регистр команд
        self.flags = {'Z':0, 'C':0, 'S':0, 'O':0}
        self.halted = False # остановка

    def reset(self):
        self.memory = [0] * 2048
        self.registers = [0] * 8
        self.pc = 0 # счётчик команд
        self.ir = 0 # регистр команд
        self.flags = {'Z':0, 'C':0, 'S':0, 'O':0} #Zero, Carry, Sign, Overflow
        self.halted = False # остановка

    def load_program(self, program, start=0):
        for i, command in enumerate(program):
            self.memory[start+i] = command

    def to_signed32(self, val): # Обрез до 32 бит
        val &= 0xFFFFFFFF
        if val > 0x7FFFFFFF:
            val -= 0x100000000
        return val

    def fetch(self):
        self.ir = self.memory[self.pc]
        return self.ir

    def decode(self, command):
        opcode = (command >> 26) & 0x3F # Код операции
        am1 = (command >> 24) & 0x3 # Тип адресации операнда 1
        am2 = (command >> 22) & 0x3 # Для операнда 2
        op1 = (command >> 11) & 0x7FF # адрес регистра 1
        op2 = command & 0x7FF # регистра 2
        return opcode, am1, am2, op1, op2

    def get_operand(self, am, op):
        if am == 0: # Непосредственная
            return op - 0x800 if op & 0x400 else op
        elif am == 1: # Прямая
            return self.memory[op]
        elif am == 2: # Регистровая
            return self.registers[op]
        elif am == 3: # Косвенно-регистровая
            return self.memory[self.registers[op]]

    def set_operand(self, am, op, value):
        if am == 1: self.memory[op] = self.to_signed32(value)
        elif am == 2: self.registers[op] = self.to_signed32(value)
        elif am == 3: self.memory[self.registers[op]] = self.to_signed32(value)

    def get_address(self, am, op):
        if am == 1: return op
        elif am == 3: return self.registers[op]
        return op

    def update_flags(self, result, carry=0, overflow=0):
        self.flags['Z'] = 1 if result == 0 else 0
        self.flags['S'] = 1 if result < 0 else 0
        self.flags['C'] = carry
        self.flags['O'] = overflow

    def step(self):
        if self.halted:
            return False
        instr = self.fetch()
        opcode, am1, am2, op1, op2 = self.decode(instr)
        self.pc += 1
        if opcode == 0x00: #NOP
            pass
        elif opcode == 0x01: #MOV
            val = self.get_operand(am2, op2)
            self.set_operand(am1, op1, val)
        elif opcode == 0x02: #LOAD
            addr = self.get_address(am2, op2)
            val = self.memory[addr]
            self.set_operand(am1, op1, val)
        elif opcode == 0x03: #STORE
            addr = self.get_address(am1, op1)
            val = self.get_operand(am2, op2)
            self.memory[addr] = self.to_signed32(val)
        elif opcode == 0x04: #ADD
            a = self.get_operand(am1, op1)
            b = self.get_operand(am2, op2)
            res = self.to_signed32(a + b)
            carry = 1 if (a + b) > 0x7FFFFFFF or (a + b) < -0x80000000 else 0
            overflow = 1 if (a > 0 and b > 0 and res < 0) or (a < 0 and b < 0 and res > 0) else 0
            self.set_operand(am1, op1, res)
            self.update_flags(res, carry, overflow)
        elif opcode == 0x05: #SUB
            a = self.get_operand(am1, op1)
            b = self.get_operand(am2, op2)
            res = self.to_signed32(a - b)
            carry = 1 if (a - b) < -0x8000000 else 0
            overflow = 1 if (a > 0 and b < 0 and res < 0) or (a > 0 and b < 0 and res > 0) else 0
            self.set_operand(am1, op1, res)
            self.update_flags(res, carry, overflow)
        elif opcode == 0x06: #MUL
            a = self.get_operand(am1, op1)
            b = self.get_operand(am2, op2)
            res = self.to_signed32(a * b)
            self.set_operand(am1, op1, res)
            self.update_flags(res)
        elif opcode == 0x07: #DIV
            a = self.get_operand(am1, op1)
            b = self.get_operand(am2, op2)
            if b == 0:
                self.halted = True
                return False
            res = self.to_signed32(int(a / b))
            self.set_operand(am1, op1, res)
            self.update_flags(res)
        elif opcode == 0x08: #AND
            a = self.get_operand(am1, op1)
            b = self.get_operand(am2, op2)
            res = self.to_signed32(a & b)
            self.set_operand(am1, op1, res)
            self.update_flags(res)
        elif opcode == 0x09: #OR
            a = self.get_operand(am1, op1)
            b = self.get_operand(am2, op2)
            res = self.to_signed32(a & b)
            self.set_operand(am1, op1, res)
        elif opcode == 0x0A: #XOR
            a = self.get_operand(am1, op1)
            b = self.get_operand(am2, op2)
            res = self.to_signed32(a ^ b)
            self.set_operand(am1, op1, res)
            self.update_flags(res)
        elif opcode == 0x0B: #NOT
            a = self.get_operand(am1, op1)
            res = self.to_signed32(~a)
            self.set_operand(am1, op1, res)
            self.update_flags(res)
        elif opcode == 0x0C:  # SHL
            a = self.get_operand(am1, op1)
            b = self.get_operand(am2, op2)
            res = self.to_signed32(a << b)
            self.set_operand(am1, op1, res)
            self.update_flags(res)
        elif opcode == 0x0D: #SHR
            a = self.get_operand(am1, op1)
            b = self.get_operand(am2, op2)
            res = self.to_signed32(a >> b)
            self.set_operand(am1, op1, res)
            self.update_flags(res)
        elif opcode == 0x0E: #CMP
            a = self.get_operand(am1, op1)
            b = self.get_operand(am2, op2)
            res = self.to_signed32(a - b)
            carry = 1 if a < b else 0
            overflow = 1 if (a > 0 and b < 0 and res < 0) or (a < 0 and b > 0 and res > 0) else 0
            self.update_flags(res, carry, overflow)
        elif opcode == 0x0F:  #JMP
            addr = self.get_address(am1, op1)
            if am1 == 0:
                self.pc += addr
            else:
                self.pc = addr
        elif opcode == 0x10:  #JZ
            if self.flags['Z']:
                addr = self.get_address(am1, op1)
                if am1 == 0:
                    self.pc += addr
                else:
                    self.pc = addr
        elif opcode == 0x11:  #JNZ
            if self.flags['Z']:
                addr = self.get_address(am1, op1)
                if am1 == 0:
                    self.pc += addr
                else:
                    self.pc = addr
        elif opcode == 0x12:  #JC
            if self.flags['C']:
                addr = self.get_address(am1, op1)
                if am1 == 0:
                    self.pc += addr
                else:
                    self.pc = addr
        elif opcode == 0x13:  #JNC
            if self.flags['C']:
                addr = self.get_address(am1, op1)
                if am1 == 0:
                    self.pc += addr
                else:
                    self.pc = addr
        elif opcode == 0x14:  #JS
            if self.flags['S']:
                addr = self.get_address(am1, op1)
                if am1 == 0:
                    self.pc += addr
                else:
                    self.pc = addr
        elif opcode == 0x15:  #JNS
            if self.flags['S']:
                addr = self.get_address(am1, op1)
                if am1 == 0:
                    self.pc += addr
                else:
                    self.pc = addr
        elif opcode == 0x16:  #JO
            if self.flags['O']:
                addr = self.get_address(am1, op1)
                if am1 == 0:
                    self.pc += addr
                else:
                    self.pc = addr
        elif opcode == 0x17:  #JNO
            if self.flags['O']:
                addr = self.get_address(am1, op1)
                if am1 == 0:
                    self.pc += addr
                else:
                    self.pc = addr
        elif opcode == 0x18:  #HLT
            self.halted = True
        else:
            self.halted = True
        return True
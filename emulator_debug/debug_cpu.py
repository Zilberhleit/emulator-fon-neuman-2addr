from emulator_src.cpu import CPU

IMM, DIR, REG, IND = 0,1,2,3

def enc(opcode, am1=0, op1=0, am2=0, op2=0):
    return (opcode << 26) | (am1 << 24) | (am2 << 22) | ((op1 & 0x7FF) << 11) | (op2 & 0x7FF)

MOV_ri = lambda r, i: enc(0x01, REG, r, IMM, i & 0x7FF)
HLT_ = lambda : enc(0x18)

cpu = CPU()
print(f'CPU init: pc={cpu.pc}, halted={cpu.halted}, mem_size={len(cpu.memory)}')

prog = [MOV_ri(0, 42), HLT_()]
print(f'Program: MOV_ri={hex(prog[0])}, HLT={hex(prog[1])}')

cpu.load_program(prog)
print(f"memory[0]={hex(cpu.memory[0])}")
print(f"memory[1]={hex(cpu.memory[1])}")
print(f"memory[2]={hex(cpu.memory[2])}")
print()

for i in range(10):
    if cpu.halted:
        print(f"[step {i}] already halted")
        break
    old_pc = cpu.pc
    cpu.step()
    print(f"[step {i}] pc {old_pc}->{cpu.pc}, ir={hex(cpu.ir)}, halted={cpu.halted}, R0={cpu.registers[0]}")

print(f"\nFinal: pc={cpu.pc}, halted={cpu.halted}, regs[:4]={cpu.registers[:4]}")
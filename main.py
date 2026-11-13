import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from emulator_src.cpu import CPU
from emulator_src.assembler import Assembler

# ТЕКСТЫ ПРОГРАММ ПО ЗАДАНИЮ

EXAMPLE1_TEXT = """
; Сумма массива (10 элементов)
; [500] - номер массива (1), [501] - длина,
; [502..511] - элементы массива. Результат [600]

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

EXAMPLE2_TEXT = """
; Свёртка массивов по 10 элементов
; S = sum(A[i] * B[i]
; [700] - Номер А, [701..710] - A
; [720] - Номер B, [721..730] - B, Результат [800]

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

OPCODE_TO_NAME = {
    0x00: 'NOP',  0x01: 'MOV',  0x02: 'LOAD', 0x03: 'STORE',
    0x04: 'ADD',  0x05: 'SUB',  0x06: 'MUL',  0x07: 'DIV',
    0x08: 'AND',  0x09: 'OR',   0x0A: 'XOR',  0x0B: 'NOT',
    0x0C: 'SHL',  0x0D: 'SHR',  0x0E: 'CMP',  0x0F: 'JMP',
    0x10: 'JZ',   0x11: 'JNZ',  0x12: 'JC',   0x13: 'JNC',
    0x14: 'JS',   0x15: 'JNS',  0x16: 'JO',   0x17: 'JNO',
    0x18: 'HLT',
}


class EmulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Эмулятор процессора - двухадрессная архитектура фон Неймана")
        self.root.geometry("1200x720")

        self.cpu = CPU()
        self.assembler = Assembler()

        self._build_ui()
        self.update_display()

    def _build_ui(self):
        left = tk.Frame(self.root)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        right = tk.Frame(self.root)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(left, text="Программа на ассемблере:").pack(anchor='w')
        self.code_editor = scrolledtext.ScrolledText(left, width=60, height=30, font=('Courier New', 10))
        self.code_editor.pack(fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(left)
        btn_row.pack(fill=tk.X, pady=5)
        tk.Button(btn_row, text="Загрузить", width=12, command=self.on_load).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="Шаг", width=12, command=self.on_step).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="Выполнить", width=12, command=self.on_run).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="Сброс", width=12, command=self.on_reset).pack(side=tk.LEFT, padx=2)

        ex_row = tk.Frame(left)
        ex_row.pack(fill=tk.X, pady=(0,5))
        tk.Button(btn_row, text="Пример 1: сумма массива", width=12, command=self.on_example1).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="Пример 2: свёртка массивов", width=12, command=self.on_example2).pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="Готово к работе")
        tk.Label(left, textvariable=self.status_var, fg='darkblue', anchor='w', justify='left').pack(fill=tk.X)

        reg_frame = tk.LabelFrame(right, text="Регистры общего назначения")
        reg_frame.pack(fill=tk.X, padx=5, pady=5)
        self.reg_labels = []
        for i in range(8):
            lbl = tk.Label(reg_frame, text=f"R{i}: 0", width=14, anchor='w', font=('Courier New', 10))
            lbl.grid(row=i // 4, column=i % 4, sticky='w', padx=1, pady=2)
            self.reg_labels.append(lbl)

        sp_frame = tk.LabelFrame(right, text="Счётчик команд, регистр команд, флаги")
        sp_frame.pack(fill=tk.X, padx=5, pady=5)

        self.pc_label = tk.Label(sp_frame, text="PC = 0", anchor='w', font=('Courier New', 10))
        self.pc_label.pack(fill=tk.X, padx=4)

        self.ir_label = tk.Label(sp_frame, text="Флаги: Z (ноль) = 0, C (перенос) = 0, S (знак) = 0, O (Переполнение) = 0", anchor='w', font=("Courier New", 10))
        self.ir_label.pack(fill=tk.X, padx=4)

        self.flags_label = tk.Label(sp_frame, text="IR = 0x00000000", anchor='w', font=('Courier New', 10))
        self.flags_label.pack(fill=tk.X, padx=4)

        instr_frame = tk.LabelFrame(right, text="Текущая команда")
        instr_frame.pack(fill=tk.X, padx=5, pady=5)

        self.instr_asm = tk.Label(instr_frame, text="Ассемблер: ", anchor='w', font=('Courier New', 10))
        self.instr_asm.pack(fill=tk.X, padx=4)

        self.instr_fields = tk.Label(instr_frame, text="Поля: ", anchor='w', font=('Courier New', 10))
        self.instr_fields.pack(fill=tk.X, padx=4)

        mem_frame = tk.LabelFrame(right, text="ОЗУ (первые 100 ячеек)")
        mem_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.mem_text = scrolledtext.ScrolledText(mem_frame, width=55, height=16, font=('Courier New', 10))
        self.mem_text.pack(fill=tk.BOTH, expand=True)
        self.mem_text.config(state=tk.DISABLED)

    def on_load(self):
        text = self.code_editor.get('1.0', tk.END)
        if not text.strip():
            messagebox.showinfo("Программа пустая", "Введите код программы")
            return
        try:
            program = self.assembler.assemble(text)
        except ValueError as e:
            messagebox.showerror("Ошибка ассемблера", str(e))
            return
        if not program:
            messagebox.showinfo("Программа пустая", "В программе ни одной команды")
            return

        self.cpu.reset()
        self.cpu.load_program(program)
        self.status_var.set(f"Программа загружена: {len(program)} команд")
        self.update_display()

    def on_step(self):
        if self.cpu.halted:
            self.status_var.set("Программа остановлена (HLT)")
            return
        self.cpu.step()
        if self.cpu.halted:
            self.status_var.set("Программа завершена (HLT)")
        self.update_display()

    def on_run(self):
        if self.cpu.halted:
            self.status_var.set("Программа остановлена")
            return
        limit = 10000
        for _ in range(limit):
            if self.cpu.halted:
                break
            self.cpu.step()
        if not self.cpu.halted:
            self.status_var.set(f"Программа остановлена: предел {limit} достигнут")
        else:
            self.status_var.set(f"Программа завершена (HLT)")
        self.update_display()

    def on_reset(self):
        self.cpu.reset()
        self.status_var.set("Программа очищена")
        self.update_display()

    def on_example1(self):
        self.code_editor.delete('1.0', tk.END)
        self.code_editor.insert('1.0', EXAMPLE1_TEXT)
        self.cpu.reset()
        self.cpu.memory[500] = 1
        self.cpu.memory[501] = 10
        for i in range(10):
            self.cpu.memory[502+i] = (i+1)*3
        try:
            program = self.assembler.assemble(EXAMPLE1_TEXT)
            self.cpu.load_program(program)
        except ValueError as e:
            messagebox.showerror("Ошибка загрузки примера 1", str(e))
        self.status_var.set("Пример 1: 3, 6, 9, ..., 30, Ожидаемый ответ: 165")
        self.update_display()

    def on_example2(self):
        self.code_editor.delete('1.0', tk.END)
        self.code_editor.insert('1.0', EXAMPLE2_TEXT)
        self.cpu.reset()
        self.cpu.memory[700] = 1
        for i in range(10):
            self.cpu.memory[701+i] = i + 1
        self.cpu.memory[720] = 2
        for i in range(10):
            self.cpu.memory[721 + i] = (i + 1) * 2
        self.status_var.set("Пример 2: два списка [1, 2, 3, ..., 10] и [2, 4, 6, ..., 20]"
                            "Свёртка = 770 ")
        try:
            program = self.assembler.assemble(EXAMPLE2_TEXT)
            self.cpu.load_program(program)
        except ValueError as e:
            messagebox.showerror("Ошибка загрузки примера 2", str(e))
        self.update_display()

    def update_display(self):
        for i in range(8):
            self.reg_labels[i].config(text=f"R{i}: {self.cpu.registers[i]}")

        self.pc_label.config(text=f"PC = {self.cpu.pc}")
        self.ir_label.config(text=f"IR = 0x{self.cpu.ir:08X}")
        f = self.cpu.flags
        self.flags_label.config(
            text=(f"Z = {f['Z']}, "
                  f"C = {f['C']}, "
                  f"S = {f['S']}, "
                  f"O = {f['O']}, ")
        )

        self._update_current_instruction()

        self._update_memory()

    def _update_current_instruction(self):
        if self.cpu.ir == 0 and self.cpu.pc == 0:
            self.instr_asm.config(text="Ассемблер")
            self.instr_fields.config(text="Поля")
            return

        opcode, am1, am2, op1, op2 = self.cpu.decode(self.cpu.ir)
        mnemonic = OPCODE_TO_NAME.get(opcode, f"?{opcode:02X}")

        def fmt(am, o):
            if am == 0:
                v = 0 - 0x800 if (o & 0x400) else o
                return f"#{v}"
            if am == 1: return f"[{o}]"
            if am == 2: return f"R{o}"
            if am == 3: return f"[R{o}]"
            return f"f{o}"

        asm_text = f"{mnemonic} {fmt(am1, op1)}"
        self.instr_asm.config(text=f"Ассемблер: {asm_text}")
        self.instr_fields.config(
            text=(f"Поля: opcodes=0x{opcode:02X} ({mnemonic}) "
                  f"am1={am1}, am2={am2}, op1={op1}, op2={op2}")
        )

    def _update_memory(self):
        self.mem_text.config(state=tk.NORMAL)
        self.mem_text.delete('1.0', tk.END)

        for start in range(0, 1000, 5):
            cells = "".join(f"[{start+j}]={self.cpu.memory[start+j]:1d}; " for j in range(5))
            self.mem_text.insert(tk.END, cells + "\n")
        self.mem_text.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = EmulatorApp(root)
    root.mainloop()
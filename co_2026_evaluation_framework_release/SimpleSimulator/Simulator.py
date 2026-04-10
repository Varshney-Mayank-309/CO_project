import sys


def to_bin32(val):
    return format(val & 0xFFFFFFFF, '032b')


def to_signed32(val):
    if val >= 0x80000000:
        return val - 0x100000000
    return val


def u32(val):
    return val & 0xFFFFFFFF


def sext(bits, val):
    if val & (1 << (bits - 1)):
        return val - (1 << bits)
    return val


class Simulator:

    def __init__(self):
        self.regs = [0] * 32
        self.regs[2] = 0x0000017C
        self.pc = 0

        self.data_mem = {}
        for i in range(32):
            self.data_mem[0x00010000 + i * 4] = 0

        self.stack_mem = {}
        for i in range(32):
            self.stack_mem[0x00000100 + i * 4] = 0

        self.instr_mem = {}

    def load_program(self, filename):
        addr = 0
        f = open(filename, 'r')
        for line in f:
            line = line.strip()
            if line == '':
                continue
            if len(line) != 32:
                sys.exit(1)
            self.instr_mem[addr] = line
            addr += 4
        f.close()

    def read_mem(self, addr):
        if addr % 4 != 0:
            raise Exception("Invalid Memory Access")
        a = addr & ~3
        if a in self.data_mem:
            return self.data_mem[a]
        if a in self.stack_mem:
            return self.stack_mem[a]
        raise Exception("Invalid Memory Access")

    def write_mem(self, addr, val):
        if addr % 4 != 0:
            raise Exception("Invalid Memory Access")
        a = addr & ~3
        val = u32(val)
        if a in self.data_mem:
            self.data_mem[a] = val
        elif a in self.stack_mem:
            self.stack_mem[a] = val
        else:
            raise Exception("Invalid Memory Access")

    def get_imm_i(self, instr):
        return sext(12, int(instr[0:12], 2))

    def get_imm_s(self, instr):
        raw = int(instr[0:7] + instr[20:25], 2)
        return sext(12, raw)

    def get_imm_b(self, instr):
        bits = instr[0] + instr[24] + instr[1:7] + instr[20:24] + "0"
        return sext(13, int(bits, 2))

    def get_imm_j(self, instr):
        bits = instr[0] + instr[12:20] + instr[11] + instr[1:11] + "0"
        return sext(21, int(bits, 2))

    def get_imm_u(self, instr):
        return sext(20, int(instr[0:20], 2)) << 12

    def run_r_type(self, instr):
        funct7 = instr[0:7]
        rs2 = int(instr[7:12], 2)
        rs1 = int(instr[12:17], 2)
        funct3 = instr[17:20]
        rd = int(instr[20:25], 2)

        v1 = self.regs[rs1]
        v2 = self.regs[rs2]
        result = 0

        if funct3 == "000" and funct7 == "0000000":
            result = u32(v1 + v2)
        elif funct3 == "000" and funct7 == "0100000":
            result = u32(v1 - v2)
        elif funct3 == "001" and funct7 == "0000000":
            result = u32(v1 << (v2 & 0x1F))
        elif funct3 == "010" and funct7 == "0000000":
            if to_signed32(v1) < to_signed32(v2):
                result = 1
            else:
                result = 0
        elif funct3 == "011" and funct7 == "0000000":
            if u32(v1) < u32(v2):
                result = 1
            else:
                result = 0
        elif funct3 == "100" and funct7 == "0000000":
            result = u32(v1 ^ v2)
        elif funct3 == "101" and funct7 == "0000000":
            result = u32(v1) >> (v2 & 0x1F)
        elif funct3 == "110" and funct7 == "0000000":
            result = u32(v1 | v2)
        elif funct3 == "111" and funct7 == "0000000":
            result = u32(v1 & v2)
        elif funct7 == "0000001" and funct3 == "000":
            result = u32(to_signed32(v1) * to_signed32(v2))
        elif funct7 == "0000001" and funct3 == "001":
            b = to_bin32(v1)[::-1]
            result = int(b, 2)

        if rd != 0:
            self.regs[rd] = result

    def run_i_type(self, instr):
        opcode = instr[25:32]
        rd = int(instr[20:25], 2)
        funct3 = instr[17:20]
        rs1 = int(instr[12:17], 2)
        imm = self.get_imm_i(instr)

        jumped = False

        if opcode == "0000011" and funct3 == "010":
            addr = u32(self.regs[rs1] + imm)
            if rd != 0:
                self.regs[rd] = self.read_mem(addr)

        elif opcode == "0010011":
            v1 = self.regs[rs1]
            if funct3 == "000":
                if rd != 0:
                    self.regs[rd] = u32(v1 + imm)
            elif funct3 == "011":
                if rd != 0:
                    if u32(v1) < u32(imm):
                        self.regs[rd] = 1
                    else:
                        self.regs[rd] = 0

        elif opcode == "1100111" and funct3 == "000":
            target = u32(self.regs[rs1] + imm)
            target = target & ~1
            if rd != 0:
                self.regs[rd] = u32(self.pc + 4)
            self.pc = target
            jumped = True

        return jumped

    def run_s_type(self, instr):
        rs2 = int(instr[7:12], 2)
        rs1 = int(instr[12:17], 2)
        funct3 = instr[17:20]
        imm = self.get_imm_s(instr)

        if funct3 == "010":
            addr = u32(self.regs[rs1] + imm)
            self.write_mem(addr, self.regs[rs2])

    def run_b_type(self, instr):
        rs1 = int(instr[12:17], 2)
        rs2 = int(instr[7:12], 2)
        funct3 = instr[17:20]
        imm = self.get_imm_b(instr)

        v1s = to_signed32(self.regs[rs1])
        v2s = to_signed32(self.regs[rs2])
        v1u = u32(self.regs[rs1])
        v2u = u32(self.regs[rs2])

        take = False
        if funct3 == "000":
            take = (v1u == v2u)
        elif funct3 == "001":
            take = (v1u != v2u)
        elif funct3 == "100":
            take = (v1s < v2s)
        elif funct3 == "101":
            take = (v1s >= v2s)
        elif funct3 == "110":
            take = (v1u < v2u)
        elif funct3 == "111":
            take = (v1u >= v2u)

        if take:
            self.pc = (self.pc + imm) & 0xFFFFFFFF
            return True
        return False

    def run_u_type(self, instr):
        opcode = instr[25:32]
        rd = int(instr[20:25], 2)
        imm = self.get_imm_u(instr)

        if opcode == "0110111" and rd != 0:
            self.regs[rd] = u32(imm)
        elif opcode == "0010111" and rd != 0:
            self.regs[rd] = u32(self.pc + imm)

    def run_j_type(self, instr):
        rd = int(instr[20:25], 2)
        imm = self.get_imm_j(instr)

        if rd != 0:
            self.regs[rd] = u32(self.pc + 4)
        self.pc = (self.pc + imm) & 0xFFFFFFFF
        return True

    def dump_regs(self):
        parts = ["0b" + to_bin32(self.pc)]
        for i in range(32):
            parts.append("0b" + to_bin32(self.regs[i]))
        return " ".join(parts)

    def dump_mem(self):
        lines = []
        for i in range(32):
            addr = 0x00010000 + i * 4
            val = self.data_mem[addr]
            lines.append("0x" + format(addr, '08X') + ":0b" + to_bin32(val))
        return "\n".join(lines)

    def run(self, input_file, output_file):
        self.load_program(input_file)
        trace = []
        error_flag = False
        halt = "00000000000000000000000001100011"

        try:
            while self.pc in self.instr_mem:
                instr = self.instr_mem[self.pc]

                if instr == halt:
                    trace.append(self.dump_regs())
                    break

                jumped = False
                opcode = instr[25:32]

                if opcode == "0110011":
                    self.run_r_type(instr)
                    self.pc = (self.pc + 4) & 0xFFFFFFFF

                elif opcode == "1101111":
                    jumped = self.run_j_type(instr)

                elif opcode == "1100011":
                    jumped = self.run_b_type(instr)
                    if not jumped:
                        self.pc = (self.pc + 4) & 0xFFFFFFFF

                elif opcode == "0100011":
                    self.run_s_type(instr)
                    self.pc = (self.pc + 4) & 0xFFFFFFFF

                elif opcode == "0000011" or opcode == "0010011" or opcode == "1100111":
                    jumped = self.run_i_type(instr)
                    if not jumped:
                        self.pc = (self.pc + 4) & 0xFFFFFFFF

                elif opcode == "0110111" or opcode == "0010111":
                    self.run_u_type(instr)
                    self.pc = (self.pc + 4) & 0xFFFFFFFF

                else:
                    self.pc = (self.pc + 4) & 0xFFFFFFFF

                self.regs[0] = 0
                trace.append(self.dump_regs())

        except Exception:
            error_flag = True

        out = open(output_file, 'w')
        for line in trace:
            out.write(line + "\n")
        if not error_flag:
            out.write(self.dump_mem() + "\n")
        out.close()


if len(sys.argv) < 3:
    sys.exit(1)

sim = Simulator()
sim.run(sys.argv[1], sys.argv[2])
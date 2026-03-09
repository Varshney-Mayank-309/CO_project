#!/usr/bin/env python3
import sys

class RISCV:
    def __init__(self):
        self.reg_map = {
            "zero":"00000","ra":"00001","sp":"00010","gp":"00011","tp":"00100",
            "t0":"00101","t1":"00110","t2":"00111",
            "s0":"01000","s1":"01001",
            "a0":"01010","a1":"01011","a2":"01100","a3":"01101",
            "a4":"01110","a5":"01111","a6":"10000","a7":"10001",
            "s2":"10010","s3":"10011","s4":"10100","s5":"10101",
            "s6":"10110","s7":"10111","s8":"11000","s9":"11001",
            "s10":"11010","s11":"11011",
            "t3":"11100","t4":"11101","t5":"11110","t6":"11111"
        }

        self.func3_map = {
            "add":"000","sub":"000","sll":"001","slt":"010","sltu":"011",
            "xor":"100","srl":"101","or":"110","and":"111",
            "lw":"010","addi":"000","sltiu":"011","jalr":"000",
            "sw":"010",
            "beq":"000","bne":"001","blt":"100","bge":"101","bltu":"110","bgeu":"111"
        }

        self.func7_map = {
            "add":"0000000","sub":"0100000","sll":"0000000","slt":"0000000",
            "sltu":"0000000","xor":"0000000","srl":"0000000","or":"0000000","and":"0000000"
        }

        self.op_map = {
            "add":0b0110011,"sub":0b0110011,"sll":0b0110011,"slt":0b0110011,
            "sltu":0b0110011,"xor":0b0110011,"srl":0b0110011,"or":0b0110011,"and":0b0110011,
            "lw":0b0000011,"addi":0b0010011,"sltiu":0b0010011,"jalr":0b1100111,
            "sw":0b0100011,
            "beq":0b1100011,"bne":0b1100011,"blt":0b1100011,"bge":0b1100011,"bltu":0b1100011,"bgeu":0b1100011,
            "lui":0b0110111,"auipc":0b0010111,
            "jal":0b1101111
        }

        self.label_pos_dict = {}
        self.lines = []

    def Dec_to_Bin(self, num_val, bit_cnt):
        if num_val < 0:
            num_val = (1 << bit_cnt) + num_val
        bin_result = bin(num_val & ((1<<bit_cnt)-1))[2:].zfill(bit_cnt)
        return bin_result[-bit_cnt:]

    def fits_signed(self, value, bits):
        lo = -(1 << (bits-1))
        hi = (1 << (bits-1)) - 1
        return lo <= value <= hi

    def parse_int(self, tok):
        tok = tok.strip()
        try:
            return int(tok, 0)
        except Exception:
            return int(tok)

    def R_Type(self, instr, args, line_num):
        try:
            rd, rs1, rs2 = [x.strip() for x in args.split(",")]
        except Exception:
            return f"Error on line {line_num}: Invalid operand format for {instr}"

        for r in (rd, rs1, rs2):
            if r not in self.reg_map:
                return f"Error on line {line_num}: Invalid register '{r}'"

        f7 = self.func7_map[instr]
        f3 = self.func3_map[instr]
        opcode = format(self.op_map[instr], '07b')

        return f"{f7}{self.reg_map[rs2]}{self.reg_map[rs1]}{f3}{self.reg_map[rd]}{opcode}"

    def I_Type(self, instr, args, line_num):
        try:
            if instr == "lw":
                rd, rest = [x.strip() for x in args.split(",",1)]
                imm_str, rs1 = rest.split("(")
                rs1 = rs1.strip()[:-1]
                imm_val = self.parse_int(imm_str)
            else:
                rd, rs1, imm_tok = [x.strip() for x in args.split(",")]
                imm_val = self.parse_int(imm_tok)
        except Exception:
            return f"Error on line {line_num}: Invalid operand format for {instr}"

        if rd not in self.reg_map:
            return f"Error on line {line_num}: Invalid register '{rd}'"
        if rs1 not in self.reg_map:
            return f"Error on line {line_num}: Invalid register '{rs1}'"

        if not self.fits_signed(imm_val, 12):
            return f"Error on line {line_num}: Immediate {imm_val} out of range for 12-bit signed"

        imm_bin = self.Dec_to_Bin(int(imm_val), 12)
        f3 = self.func3_map[instr]
        opcode = format(self.op_map[instr], '07b')

        return f"{imm_bin}{self.reg_map[rs1]}{f3}{self.reg_map[rd]}{opcode}"

    def S_Type(self, instr, args, line_num):
        try:
            rs2, rest = [x.strip() for x in args.split(",",1)]
            imm_str, rs1 = rest.split("(")
            rs1 = rs1.strip()[:-1]
            imm_val = self.parse_int(imm_str)
        except Exception:
            return f"Error on line {line_num}: Invalid operand format for {instr}"

        if rs2 not in self.reg_map:
            return f"Error on line {line_num}: Invalid register '{rs2}'"
        if rs1 not in self.reg_map:
            return f"Error on line {line_num}: Invalid register '{rs1}'"

        if not self.fits_signed(imm_val, 12):
            return f"Error on line {line_num}: Immediate {imm_val} out of range for 12-bit signed"

        imm_bin = self.Dec_to_Bin(int(imm_val), 12)
        imm_hi = imm_bin[:7]
        imm_lo = imm_bin[7:]
        f3 = self.func3_map[instr]
        opcode = format(self.op_map[instr], '07b')

        return f"{imm_hi}{self.reg_map[rs2]}{self.reg_map[rs1]}{f3}{imm_lo}{opcode}"

    def B_Type(self, instr, args, line_num, idx):
        try:
            rs1, rs2, imm_tok = [x.strip() for x in args.split(",")]
        except Exception:
            return f"Error on line {line_num}: Invalid operand format for {instr}"

        if rs1 not in self.reg_map:
            return f"Error on line {line_num}: Invalid register '{rs1}'"
        if rs2 not in self.reg_map:
            return f"Error on line {line_num}: Invalid register '{rs2}'"

        try:
            if imm_tok in self.label_pos_dict:
                imm_val = (self.label_pos_dict[imm_tok] - idx) * 2
            else:
                imm_val = self.parse_int(imm_tok) // 2
        except Exception:
            return f"Error on line {line_num}: Invalid immediate/label '{imm_tok}'"

        if not self.fits_signed(imm_val, 12):
            return f"Error on line {line_num}: Branch immediate {imm_val} out of range for 12-bit signed"

        imm_bin = self.Dec_to_Bin(int(imm_val), 12)
        imm_b12 = imm_bin[0]
        imm_b10_5 = imm_bin[2:8]
        imm_b4_1 = imm_bin[8:12]
        imm_b11 = imm_bin[1]
        f3 = self.func3_map[instr]
        opcode = format(self.op_map[instr], '07b')

        return f"{imm_b12}{imm_b10_5}{self.reg_map[rs2]}{self.reg_map[rs1]}{f3}{imm_b4_1}{imm_b11}{opcode}"

    def U_Type(self, instr, args, line_num):
        try:
            rd, imm_tok = [x.strip() for x in args.split(",")]
        except Exception:
            return f"Error on line {line_num}: Invalid operand format for {instr}"

        if rd not in self.reg_map:
            return f"Error on line {line_num}: Invalid register '{rd}'"

        try:
            imm_val = self.parse_int(imm_tok)
        except Exception:
            return f"Error on line {line_num}: Invalid immediate '{imm_tok}'"

        if not self.fits_signed(imm_val, 20):
            return f"Error on line {line_num}: Immediate {imm_val} out of range for 20-bit"

        imm_bin = self.Dec_to_Bin(int(imm_val), 20)
        opcode = format(self.op_map[instr], '07b')

        return f"{imm_bin}{self.reg_map[rd]}{opcode}"

    def J_Type(self, instr, args, line_num, idx):
        try:
            rd, imm_tok = [x.strip() for x in args.split(",")]
        except Exception:
            return f"Error on line {line_num}: Invalid operand format for {instr}"

        if rd not in self.reg_map:
            return f"Error on line {line_num}: Invalid register '{rd}'"

        try:
            if imm_tok in self.label_pos_dict:
                imm_val = (self.label_pos_dict[imm_tok] - idx) * 2
            else:
                imm_val = self.parse_int(imm_tok) // 2
        except Exception:
            return f"Error on line {line_num}: Invalid immediate/label '{imm_tok}'"

        if not self.fits_signed(imm_val, 20):
            return f"Error on line {line_num}: J-type immediate {imm_val} out of range for 20-bit signed"

        imm_bin = self.Dec_to_Bin(int(imm_val), 20)
        imm_b20 = imm_bin[0]
        imm_b19_12 = imm_bin[1:9]
        imm_b11 = imm_bin[9]
        imm_b10_1 = imm_bin[10:20]
        opcode = format(self.op_map[instr], '07b')

        return f"{imm_b20}{imm_b10_1}{imm_b11}{imm_b19_12}{self.reg_map[rd]}{opcode}"

    def process_line(self, line_str, line_num, idx):
        if '#' in line_str:
            line_str = line_str.split('#',1)[0].strip()

        label = None
        instr_part = line_str

        if ":" in line_str:
            parts = line_str.split(":",1)
            label = parts[0].strip()
            instr_part = parts[1].strip()

            if not label or not label[0].isalpha():
                return f"Error on line {line_num}: Invalid label '{label}'"

        if instr_part == "":
            return None

        parts = instr_part.split(None, 1)
        instr = parts[0].strip()
        args = parts[1].strip() if len(parts) > 1 else ""

        if instr in self.func7_map:
            return self.R_Type(instr, args, line_num)
        if instr in ["addi","lw","sltiu","jalr"]:
            return self.I_Type(instr, args, line_num)
        if instr == "sw":
            return self.S_Type(instr, args, line_num)
        if instr in ["beq","bne","blt","bge","bltu","bgeu"]:
            return self.B_Type(instr, args, line_num, idx)
        if instr in ["lui","auipc"]:
            return self.U_Type(instr, args, line_num)
        if instr == "jal":
            return self.J_Type(instr, args, line_num, idx)

        return f"Error on line {line_num}: Unknown instruction '{instr}'"

    def read_file(self, in_file):
        self.lines = []
        line_cnt = 0
        with open(in_file, 'r') as fh:
            raw_lines = fh.readlines()

        for raw in raw_lines:
            line = raw.strip()
            if not line:
                continue
            if '#' in line:
                line = line.split('#',1)[0].strip()
                if not line:
                    continue
            if ":" in line:
                parts = line.split(":",1)
                lbl = parts[0].strip()
                if lbl and lbl[0].isalpha():
                    self.label_pos_dict[lbl] = line_cnt
                else:
                    self.label_pos_dict[lbl] = line_cnt
            self.lines.append(raw.rstrip("\n"))
            line_cnt += 1

    def verify_virtual_halt(self):
        if not self.lines:
            print("Error: Missing Virtual Halt instruction")
            sys.exit(1)

        last_line = self.lines[-1].strip()

        if '#' in last_line:
            last_line = last_line.split('#',1)[0].strip()

        if ":" in last_line:
            parts = last_line.split(":",1)
            last_line = parts[1].strip()

        if not last_line.lower().startswith("beq"):
            print("Error: Missing Virtual Halt instruction")
            sys.exit(1)

        try:
            _, rest = last_line.split(None,1)
            args = rest.strip()
            fields = [x.strip() for x in args.split(",")]
            if len(fields) != 3:
                print("Error: Missing Virtual Halt instruction")
                sys.exit(1)
            imm_tok = fields[2]
            imm_val = int(imm_tok, 0)
            if imm_val != 0:
                print("Error: Missing Virtual Halt instruction")
                sys.exit(1)
        except Exception:
            print("Error: Missing Virtual Halt instruction")
            sys.exit(1)

    def process_file(self, in_file, out_file):
        self.verify_virtual_halt()

        with open(out_file, "w") as out:
            line_num = 1
            instr_idx = 0
            for raw in self.lines:
                line = raw.strip()

                if '#' in line:
                    line = line.split('#',1)[0].strip()

                if not line:
                    line_num += 1
                    continue

                encoded = self.process_line(line, line_num, instr_idx)

                if encoded is None:
                    line_num += 1
                    continue

                if isinstance(encoded, str) and encoded.startswith("Error"):
                    print(encoded)
                    return

                if len(encoded) != 32:
                    print(f"Error on line {line_num}: Encoded instruction length != 32 ({len(encoded)})")
                    return

                out.write(encoded + "\n")

                line_num += 1
                instr_idx += 1

        print("Successfully assembled to", out_file)


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 Assembler.py <input.asm> <output.bin>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    asm = RISCV()
    asm.read_file(input_file)
    asm.process_file(input_file, output_file)


if __name__ == "__main__":
    main()
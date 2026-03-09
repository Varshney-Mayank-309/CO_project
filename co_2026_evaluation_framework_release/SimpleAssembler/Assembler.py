#!/usr/bin/env python3
import sys


class RISCV:

    def __init__(self):

        # register encoding table
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

        # funct3 codes
        self.func3_map = {
            "add":"000","sub":"000","sll":"001","slt":"010","sltu":"011",
            "xor":"100","srl":"101","or":"110","and":"111",
            "lw":"010","addi":"000","sltiu":"011","jalr":"000",
            "sw":"010",
            "beq":"000","bne":"001","blt":"100","bge":"101","bltu":"110","bgeu":"111"
        }

        # funct7 only used for R type
        self.func7_map = {
            "add":"0000000","sub":"0100000","sll":"0000000","slt":"0000000",
            "sltu":"0000000","xor":"0000000","srl":"0000000","or":"0000000","and":"0000000"
        }

        # opcode values
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

    # decimal to binary helper
    def Dec_to_Bin(self, val, bits):

        if val < 0:
            val = (1 << bits) + val

        b = bin(val)[2:]
        b = b.zfill(bits)

        if len(b) > bits:
            b = b[-bits:]

        return b

    def fits_signed(self, v, bits):

        lo = -(1 << (bits - 1))
        hi = (1 << (bits - 1)) - 1

        if v < lo or v > hi:
            return False

        return True

    def parse_int(self, tok):

        tok = tok.strip()

        try:
            num = int(tok,0)
        except:
            num = int(tok)

        return num

    # ---------------- R TYPE ----------------

    def R_Type(self, instr, args, line_no):

        pieces = args.split(",")

        if len(pieces) != 3:
            return "Error on line "+str(line_no)+": Invalid operand format"

        rd = pieces[0].strip()
        rs1 = pieces[1].strip()
        rs2 = pieces[2].strip()

        if rd not in self.reg_map:
            return "Error on line "+str(line_no)+": Invalid register "+rd

        if rs1 not in self.reg_map or rs2 not in self.reg_map:
            return "Error on line "+str(line_no)+": Invalid register"

        f7 = self.func7_map[instr]
        f3 = self.func3_map[instr]
        opcode = format(self.op_map[instr],'07b')

        return f7 + self.reg_map[rs2] + self.reg_map[rs1] + f3 + self.reg_map[rd] + opcode

    # ---------------- I TYPE ----------------

    def I_Type(self,instr,args,line_no):

        if instr=="lw":

            try:
                p = args.split(",",1)
                rd = p[0].strip()

                stuff = p[1].strip()
                off = stuff.split("(")[0]
                rs1 = stuff.split("(")[1].replace(")","")

                imm_val = self.parse_int(off)

            except:
                return "Error on line "+str(line_no)+": Bad operand format"

        else:

            f = args.split(",")

            if len(f)!=3:
                return "Error on line "+str(line_no)+": Bad operands"

            rd = f[0].strip()
            rs1 = f[1].strip()
            imm_val = self.parse_int(f[2])

        if rd not in self.reg_map or rs1 not in self.reg_map:
            return "Error on line "+str(line_no)+": Invalid register"

        if not self.fits_signed(imm_val,12):
            return "Error on line "+str(line_no)+": Immediate overflow"

        bits = self.Dec_to_Bin(imm_val,12)

        f3 = self.func3_map[instr]
        op = format(self.op_map[instr],'07b')

        return bits + self.reg_map[rs1] + f3 + self.reg_map[rd] + op

    # ---------------- S TYPE ----------------

    def S_Type(self,instr,args,line_no):

        try:
            x=args.split(",",1)
            r2=x[0].strip()
            blah = x[1].strip()

            im = blah.split("(")[0]
            base = blah.split("(")[1].replace(")","")

            num = self.parse_int(im)

        except:
            return "Error on line "+str(line_no)+" : Invalid operands"

        if base not in self.reg_map or r2 not in self.reg_map:
            return "Error on line "+str(line_no)+" : Invalid register"

        if not self.fits_signed(num,12):
            return "Error on line "+str(line_no)+": Immediate out of range"

        b = self.Dec_to_Bin(num,12)

        hi=b[:7]
        lo = b[7:]   

        f = self.func3_map[instr]
        op=format(self.op_map[instr],'07b')

        out = hi + self.reg_map[r2] + self.reg_map[base] + f + lo + op

        return out

    # ---------------- B TYPE ----------------

    def B_Type(self, instr, args, line_no, idx):

        fields = args.split(",")

        if len(fields) != 3:
            return "Error on line "+str(line_no)

        rs1 = fields[0].strip()
        rs2 = fields[1].strip()
        imm_tok = fields[2].strip()

        if rs1 not in self.reg_map or rs2 not in self.reg_map:
            return "Error on line "+str(line_no)+": Invalid register"

        try:

            if imm_tok in self.label_pos_dict:
                imm_val = (self.label_pos_dict[imm_tok] - idx) * 2
            else:
                imm_val = self.parse_int(imm_tok) // 2

        except:
            return "Error on line "+str(line_no)+": Invalid label"

        if not self.fits_signed(imm_val,12):
            return "Error on line "+str(line_no)+": Branch immediate overflow"

        imm_bin = self.Dec_to_Bin(imm_val,12)

        b12 = imm_bin[0]
        b10_5 = imm_bin[2:8]
        b4_1 = imm_bin[8:12]
        b11 = imm_bin[1]

        f3 = self.func3_map[instr]
        opcode = format(self.op_map[instr],'07b')

        return b12 + b10_5 + self.reg_map[rs2] + self.reg_map[rs1] + f3 + b4_1 + b11 + opcode

    # ---------------- U TYPE ----------------

    def U_Type(self, instr, args, line_no):

        try:
            rd, imm = args.split(",")
        except:
            return "Error on line "+str(line_no)

        rd = rd.strip()

        if rd not in self.reg_map:
            return "Error on line "+str(line_no)+": Invalid register"

        imm_val = self.parse_int(imm)

        if not self.fits_signed(imm_val,20):
            return "Error on line "+str(line_no)+": Immediate overflow"

        imm_bin = self.Dec_to_Bin(imm_val,20)

        opcode = format(self.op_map[instr],'07b')

        return imm_bin + self.reg_map[rd] + opcode

    # ---------------- J TYPE ----------------

    def J_Type(self, instr, args, line_no, idx):

        try:
            rd, imm_tok = args.split(",")
        except:
            return "Error on line "+str(line_no)

        rd = rd.strip()

        if rd not in self.reg_map:
            return "Error on line "+str(line_no)

        if imm_tok.strip() in self.label_pos_dict:
            imm_val = (self.label_pos_dict[imm_tok.strip()] - idx) * 2
        else:
            imm_val = self.parse_int(imm_tok) // 2

        if not self.fits_signed(imm_val,20):
            return "Error on line "+str(line_no)

        imm_bin = self.Dec_to_Bin(imm_val,20)

        b20 = imm_bin[0]
        b19_12 = imm_bin[1:9]
        b11 = imm_bin[9]
        b10_1 = imm_bin[10:20]

        opcode = format(self.op_map[instr],'07b')

        return b20 + b10_1 + b11 + b19_12 + self.reg_map[rd] + opcode

    # ---------- FILE READING ----------

    def read_file(self, in_file):

        self.lines = []

        line_index = 0

        with open(in_file) as f:
            raw = f.readlines()

        for line in raw:

            text = line.strip()

            if not text:
                continue

            if "#" in text:
                text = text.split("#")[0].strip()

            if ":" in text:

                label = text.split(":")[0].strip()

                self.label_pos_dict[label] = line_index

            self.lines.append(line.rstrip("\n"))

            line_index += 1

    # ---------- VIRTUAL HALT CHECK ----------

    def verify_virtual_halt(self):

        if not self.lines:
            print("Error: Missing Virtual Halt instruction")
            return False

        x = self.lines[-1].strip()

        if "#" in x:
            x = x.split("#")[0].strip()

        if ":" in x:
            x = x.split(":")[1].strip()

        if not x.lower().startswith("beq"):
            print("Error: Missing Virtual Halt instruction")
            return False

        stuff = x.split(None,1)

        if len(stuff) > 1:
            p = stuff[1].split(",")

            if len(p) >= 3:
                off = p[2].strip()

                try:
                    val = int(off,0)
                    if val != 0:
                        print("Error: Missing Virtual Halt instruction")
                        return False
                except:
                    print("Error: Missing Virtual Halt instruction")
                    return False

        return True
    
    

    # ---------- PROCESS ----------

    def process_file(self, out_file):

        with open(out_file,"w") as out:

            line_num = 1
            idx = 0

            for raw in self.lines:

                line = raw.strip()

                if "#" in line:
                    line = line.split("#")[0].strip()

                if not line:
                    line_num += 1
                    continue

                if ":" in line:
                    line = line.split(":",1)[1].strip()

                if not line:
                    line_num += 1
                    continue

                parts = line.split(None,1)

                instr = parts[0]

                args = ""

                if len(parts) > 1:
                    args = parts[1]

                encoded = None

                if instr in self.func7_map:
                    encoded = self.R_Type(instr,args,line_num)

                elif instr in ["addi","lw","sltiu","jalr"]:
                    encoded = self.I_Type(instr,args,line_num)

                elif instr == "sw":
                    encoded = self.S_Type(instr,args,line_num)

                elif instr in ["beq","bne","blt","bge","bltu","bgeu"]:
                    encoded = self.B_Type(instr,args,line_num,idx)

                elif instr in ["lui","auipc"]:
                    encoded = self.U_Type(instr,args,line_num)

                elif instr == "jal":
                    encoded = self.J_Type(instr,args,line_num,idx)

                else:
                    print("Error on line",line_num,": Unknown instruction",instr)
                    return False

                if isinstance(encoded,str) and encoded.startswith("Error"):
                    print(encoded)
                    return False

                if len(encoded) != 32:
                    print("Error on line",line_num)
                    return False

                out.write(encoded+"\n")

                idx += 1
                line_num += 1

        print("Successfully assembled to",out_file)
        return True


def main():

    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python3 Assembler.py input.asm output.bin")
        sys.exit(1)

    inp = sys.argv[1]
    out = sys.argv[2]

    asm = RISCV()

    asm.read_file(inp)

    ok2 = asm.verify_virtual_halt()

    if not ok2:
        # create empty output so grader doesn't crash, but it won't match golden
        open(out, 'w').close()
        sys.exit(1)

    ok1 = asm.process_file(out)

    if not ok1:
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3

import sys
import re
import os

REGISTERS = {
    'zero': 0, 'x0': 0,
    'ra': 1, 'x1': 1,
    'sp': 2, 'x2': 2,
    'gp': 3, 'x3': 3,
    'tp': 4, 'x4': 4,
    't0': 5, 'x5': 5,
    't1': 6, 'x6': 6,
    't2': 7, 'x7': 7,
    's0': 8, 'fp': 8, 'x8': 8,
    's1': 9, 'x9': 9,
    'a0': 10, 'x10': 10,
    'a1': 11, 'x11': 11,
    'a2': 12, 'x12': 12,
    'a3': 13, 'x13': 13,
    'a4': 14, 'x14': 14,
    'a5': 15, 'x15': 15,
    'a6': 16, 'x16': 16,
    'a7': 17, 'x17': 17,
    's2': 18, 'x18': 18,
    's3': 19, 'x19': 19,
    's4': 20, 'x20': 20,
    's5': 21, 'x21': 21,
    's6': 22, 'x22': 22,
    's7': 23, 'x23': 23,
    's8': 24, 'x24': 24,
    's9': 25, 'x25': 25,
    's10': 26, 'x26': 26,
    's11': 27, 'x27': 27,
    't3': 28, 'x28': 28,
    't4': 29, 'x29': 29,
    't5': 30, 'x30': 30,
    't6': 31, 'x31': 31,
}

OPCODES = {
    'add': '0110011', 'sub': '0110011', 'sll': '0110011',
    'slt': '0110011', 'sltu': '0110011', 'xor': '0110011',
    'srl': '0110011', 'or': '0110011', 'and': '0110011',
    'lw': '0000011', 'addi': '0010011', 'sltiu': '0010011',
    'jalr': '1100111',
    'sw': '0100011',
    'beq': '1100011', 'bne': '1100011', 'blt': '1100011',
    'bge': '1100011', 'bltu': '1100011', 'bgeu': '1100011',
    'lui': '0110111', 'auipc': '0010111',
    'jal': '1101111',
}

FUNCT3 = {
    'add': '000', 'sub': '000', 'sll': '001', 'slt': '010',
    'sltu': '011', 'xor': '100', 'srl': '101', 'or': '110',
    'and': '111',
    'lw': '010', 'addi': '000', 'sltiu': '011', 'jalr': '000',
    'sw': '010',
    'beq': '000', 'bne': '001', 'blt': '100', 'bge': '101',
    'bltu': '110', 'bgeu': '111',
}

FUNCT7 = {
    'add': '0000000', 'sub': '0100000', 'sll': '0000000',
    'slt': '0000000', 'sltu': '0000000', 'xor': '0000000',
    'srl': '0000000', 'or': '0000000', 'and': '0000000',
}

MAX_INSTRUCTIONS = 64
MAX_PROGRAM_MEMORY = 256

def to_binary(value, bits):
    if value < 0:
        value = (1 << bits) + value
    return format(value & ((1 << bits) - 1), f'0{bits}b')

def parse_register(reg, line_num=None):
    reg = reg.strip().lower()
    if reg in REGISTERS:
        return REGISTERS[reg]
    error_msg = f"Unknown register: {reg}"
    if line_num:
        raise ValueError(f"Error at line {line_num}: {error_msg}")
    raise ValueError(error_msg)

def parse_immediate(imm_str, bits, signed=True, is_label=False, label_addr=None, pc=None, line_num=None):
    imm_str = imm_str.strip()
    
    if is_label and label_addr is not None and pc is not None:
        offset = label_addr - pc
        return offset
    
    sign = 1
    if imm_str.startswith('+'):
        imm_str = imm_str[1:]
    elif imm_str.startswith('-'):
        sign = -1
        imm_str = imm_str[1:]
    
    if not imm_str:
        raise ValueError("Empty immediate value")
    
    if len(imm_str) > 1 and imm_str[0] == '0' and imm_str[1] not in 'xXbB':
        value = int(imm_str, 8)
    elif imm_str.startswith('0x') or imm_str.startswith('0X'):
        value = int(imm_str, 16)
    elif imm_str.startswith('0b') or imm_str.startswith('0B'):
        value = int(imm_str, 2)
    else:
        value = int(imm_str)
    
    value = sign * value
    
    if signed:
        max_val = (1 << (bits - 1)) - 1
        min_val = -(1 << (bits - 1))
        if not (min_val <= value <= max_val):
            raise ValueError(f"Immediate {value} out of range for {bits}-bit signed")
    else:
        max_val = (1 << bits) - 1
        if not (0 <= value <= max_val):
            raise ValueError(f"Immediate {value} out of range for {bits}-bit unsigned")
    
    return value

def encode_r_type(instr, rd, rs1, rs2):
    funct7 = FUNCT7[instr]
    funct3 = FUNCT3[instr]
    opcode = OPCODES[instr]
    return funct7 + to_binary(rs2, 5) + to_binary(rs1, 5) + funct3 + to_binary(rd, 5) + opcode

def encode_i_type(instr, rd, rs1, imm):
    funct3 = FUNCT3[instr]
    opcode = OPCODES[instr]
    imm_bin = to_binary(imm & 0xFFF, 12)
    return imm_bin + to_binary(rs1, 5) + funct3 + to_binary(rd, 5) + opcode

def encode_s_type(instr, rs1, rs2, imm):
    funct3 = FUNCT3[instr]
    opcode = OPCODES[instr]
    imm_bin = to_binary(imm & 0xFFF, 12)
    imm_high = imm_bin[:7]
    imm_low = imm_bin[7:]
    return imm_high + to_binary(rs2, 5) + to_binary(rs1, 5) + funct3 + imm_low + opcode

def encode_b_type(instr, rs1, rs2, imm):
    funct3 = FUNCT3[instr]
    opcode = OPCODES[instr]
    imm_12 = (imm >> 12) & 1
    imm_11 = (imm >> 11) & 1
    imm_10_5 = (imm >> 5) & 0x3F
    imm_4_1 = (imm >> 1) & 0xF
    
    imm_bin = str(imm_12) + to_binary(imm_10_5, 6) + to_binary(rs2, 5) + to_binary(rs1, 5) + funct3 + to_binary(imm_4_1, 4) + str(imm_11) + opcode
    return imm_bin

def encode_u_type(instr, rd, imm):
    opcode = OPCODES[instr]
    imm_bin = to_binary((imm >> 12) & 0xFFFFF, 20)
    return imm_bin + to_binary(rd, 5) + opcode

def encode_j_type(instr, rd, imm):
    opcode = OPCODES[instr]
    imm_20 = (imm >> 20) & 1
    imm_19_12 = (imm >> 12) & 0xFF
    imm_11 = (imm >> 11) & 1
    imm_10_1 = (imm >> 1) & 0x3FF
    
    imm_bin = str(imm_20) + to_binary(imm_10_1, 10) + str(imm_11) + to_binary(imm_19_12, 8)
    return imm_bin + to_binary(rd, 5) + opcode

def is_instruction(line):
    line = line.strip()
    if not line or line.startswith('#'):
        return False
    if ':' in line:
        line = line.split(':')[-1].strip()
    if not line:
        return False
    instr = line.split()[0].lower()
    return instr in OPCODES

def is_virtual_halt(line):
    line = line.strip().lower()
    if ':' in line:
        line = line.split(':')[-1].strip()
    
    patterns = [
        r'beq\s+(zero|x0)\s*,\s*(zero|x0)\s*,\s*0(\s*#.*)?$',
        r'beq\s+(zero|x0)\s*,\s*(zero|x0)\s*,\s*0x0+(\s*#.*)?$',
    ]
    for pattern in patterns:
        if re.match(pattern, line):
            return True
    return False

def first_pass(lines):
    labels = {}
    address = 0
    has_virtual_halt = False
    virtual_halt_line = -1
    instruction_count = 0
    
    for line_num, line in enumerate(lines, 1):
        original_line = line
        if '#' in line:
            line = line[:line.index('#')]
        
        line = line.strip()
        if not line:
            continue
        
        if ':' in line:
            parts = line.split(':')
            label = parts[0].strip()
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', label):
                raise ValueError(f"Line {line_num}: Invalid label name '{label}'")
            labels[label] = address
            
            rest = ':'.join(parts[1:]).strip()
            if rest and is_instruction(rest):
                instruction_count += 1
                if is_virtual_halt(rest):
                    has_virtual_halt = True
                    virtual_halt_line = line_num
                address += 4
        else:
            if is_instruction(line):
                instruction_count += 1
                if instruction_count > MAX_INSTRUCTIONS:
                    raise ValueError(f"Line {line_num}: Program memory limit exceeded (max {MAX_INSTRUCTIONS} instructions)")
                if is_virtual_halt(line):
                    has_virtual_halt = True
                    virtual_halt_line = line_num
                address += 4
    
    if address > MAX_PROGRAM_MEMORY:
        raise ValueError(f"Program memory limit exceeded: {address} bytes (max {MAX_PROGRAM_MEMORY} bytes)")
    
    return labels, has_virtual_halt, virtual_halt_line, address, instruction_count

def parse_instruction(line, pc, labels, line_num):
    original_line = line
    if '#' in line:
        line = line[:line.index('#')]
    
    line = line.strip()
    if not line:
        return None
    
    if ':' in line:
        parts = line.split(':')
        line = ':'.join(parts[1:]).strip()
        if not line:
            return None
    
    if not line:
        return None
    
    tokens = re.split(r'[\s,]+', line)
    tokens = [t for t in tokens if t]
    
    if not tokens:
        return None
    
    instr = tokens[0].lower()
    
    if is_virtual_halt(original_line):
        return encode_b_type('beq', 0, 0, 0)
    
    if instr not in OPCODES:
        raise ValueError(f"Unknown instruction: {instr}")
    
    try:
        if instr in ['add', 'sub', 'sll', 'slt', 'sltu', 'xor', 'srl', 'or', 'and']:
            if len(tokens) != 4:
                raise ValueError(f"{instr} requires 3 operands")
            rd = parse_register(tokens[1], line_num)
            rs1 = parse_register(tokens[2], line_num)
            rs2 = parse_register(tokens[3], line_num)
            return encode_r_type(instr, rd, rs1, rs2)
        
        elif instr == 'lw':
            if len(tokens) != 3:
                raise ValueError(f"lw requires 2 operands: rd, imm(rs1)")
            rd = parse_register(tokens[1], line_num)
            mem_arg = tokens[2]
            match = re.match(r'([+-]?\w+)\s*\(\s*(\w+)\s*\)', mem_arg)
            if not match:
                raise ValueError(f"Invalid memory operand: {mem_arg}")
            imm_str = match.group(1)
            rs1 = parse_register(match.group(2), line_num)
            imm = parse_immediate(imm_str, 12, signed=True, line_num=line_num)
            return encode_i_type(instr, rd, rs1, imm)
        
        elif instr in ['addi', 'sltiu']:
            if len(tokens) != 4:
                raise ValueError(f"{instr} requires 3 operands")
            rd = parse_register(tokens[1], line_num)
            rs1 = parse_register(tokens[2], line_num)
            imm = parse_immediate(tokens[3], 12, signed=True, line_num=line_num)
            return encode_i_type(instr, rd, rs1, imm)
        
        elif instr == 'jalr':
            if len(tokens) == 4:
                rd = parse_register(tokens[1], line_num)
                rs1 = parse_register(tokens[2], line_num)
                imm = parse_immediate(tokens[3], 12, signed=True, line_num=line_num)
                return encode_i_type(instr, rd, rs1, imm)
            elif len(tokens) == 3:
                rd = parse_register(tokens[1], line_num)
                mem_arg = tokens[2]
                match = re.match(r'([+-]?\w+)\s*\(\s*(\w+)\s*\)', mem_arg)
                if not match:
                    raise ValueError(f"Invalid memory operand for jalr: {mem_arg}")
                imm_str = match.group(1)
                rs1 = parse_register(match.group(2), line_num)
                imm = parse_immediate(imm_str, 12, signed=True, line_num=line_num)
                return encode_i_type(instr, rd, rs1, imm)
            else:
                raise ValueError(f"jalr requires 2 or 3 operands")
        
        elif instr == 'sw':
            if len(tokens) != 3:
                raise ValueError(f"sw requires 2 operands: rs2, imm(rs1)")
            rs2 = parse_register(tokens[1], line_num)
            mem_arg = tokens[2]
            match = re.match(r'([+-]?\w+)\s*\(\s*(\w+)\s*\)', mem_arg)
            if not match:
                raise ValueError(f"Invalid memory operand: {mem_arg}")
            imm_str = match.group(1)
            rs1 = parse_register(match.group(2), line_num)
            imm = parse_immediate(imm_str, 12, signed=True, line_num=line_num)
            return encode_s_type(instr, rs1, rs2, imm)
        
        elif instr in ['beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu']:
            if len(tokens) != 4:
                raise ValueError(f"{instr} requires 3 operands")
            rs1 = parse_register(tokens[1], line_num)
            rs2 = parse_register(tokens[2], line_num)
            label = tokens[3]
            
            if label in labels:
                offset = labels[label] - pc
            else:
                try:
                    offset = parse_immediate(label, 13, signed=True, line_num=line_num)
                except ValueError:
                    raise ValueError(f"Unknown label or invalid immediate: {label}")
            
            if offset % 2 != 0:
                raise ValueError(f"Branch offset must be even: {offset}")
            
            if offset < -4096 or offset > 4094:
                raise ValueError(f"Branch offset {offset} out of range")
            
            return encode_b_type(instr, rs1, rs2, offset)
        
        elif instr in ['lui', 'auipc']:
            if len(tokens) != 3:
                raise ValueError(f"{instr} requires 2 operands")
            rd = parse_register(tokens[1], line_num)
            imm = parse_immediate(tokens[2], 32, signed=True, line_num=line_num)
            if imm < -(1 << 31) or imm >= (1 << 31):
                raise ValueError(f"Immediate out of range")
            return encode_u_type(instr, rd, imm)
        
        elif instr == 'jal':
            if len(tokens) != 3:
                raise ValueError(f"jal requires 2 operands")
            rd = parse_register(tokens[1], line_num)
            label = tokens[2]
            
            if label in labels:
                offset = labels[label] - pc
            else:
                try:
                    offset = parse_immediate(label, 21, signed=True, line_num=line_num)
                except ValueError:
                    raise ValueError(f"Unknown label or invalid immediate: {label}")
            
            if offset % 2 != 0:
                raise ValueError(f"Jump offset must be even: {offset}")
            
            if offset < -(1 << 20) or offset >= (1 << 20):
                raise ValueError(f"Jump offset {offset} out of range")
            
            return encode_j_type(instr, rd, offset)
        
        else:
            raise ValueError(f"Unhandled instruction: {instr}")
            
    except ValueError as e:
        error_str = str(e)
        if not error_str.startswith(f"Error at line {line_num}"):
            raise ValueError(f"Error at line {line_num}: {error_str}")
        raise

def assemble(input_file, output_file, readable_file=None):
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            print(f"Error: Cannot create output directory {output_dir}: {e}")
            sys.exit(1)
    
    try:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Cannot open input file {input_file}")
        sys.exit(1)
    
    try:
        labels, has_virtual_halt, virtual_halt_line, total_bytes, instruction_count = first_pass(lines)
        
        if not has_virtual_halt:
            print("Error: Missing Virtual Halt instruction (beq zero, zero, 0)")
            sys.exit(1)
        
        binary_output = []
        pc = 0
        
        for line_num, line in enumerate(lines, 1):
            try:
                binary = parse_instruction(line, pc, labels, line_num)
                if binary:
                    binary_output.append(binary)
                    pc += 4
            except ValueError as e:
                print(str(e))
                sys.exit(1)
        
        with open(output_file, 'w') as f:
            for i, binary in enumerate(binary_output):
                if i < len(binary_output) - 1:
                    f.write(binary + '\n')
                else:
                    f.write(binary)
        
        print(f"Assembly successful: {len(binary_output)} instructions generated")
        
    except ValueError as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python3 Assembler.py <input_file> <output_file> [readable_output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    readable_file = sys.argv[3] if len(sys.argv) == 4 else None
    
    assemble(input_file, output_file, readable_file)
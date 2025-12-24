#!/bin/bash

if [ $# -eq 0 ]; then
	echo "Usage: $0 <input_file.s>"
	exit 1
fi

input_file=$1
output_file="${input_file%.s}"

# Assemble the input file
arm-none-eabi-as -o "${output_file}.o" "$input_file"

# Link the object file
arm-none-eabi-ld -o "$output_file" "${output_file}.o"

# Run the executable using QEMU
# qemu-arm -d in_asm,exec,cpu -singlestep "./$output_file"
# qemu-arm -d in_asm,exec,cpu -singlestep "./$output_file" #2>/dev/null
qemu-arm -d in_asm,exec,cpu -one-insn-per-tb "./$output_file"

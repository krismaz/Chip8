import os
import time
from font import font
import random
import math
import sys
from msvcrt import getch
import keymap

memory = [0] * 4096
registers = [0] * 16
IDX, PC, opcode = 0, 0x200, 0
screen = [[0] * 64 for i in range(32)]
delay_timer, sound_timer = 0, 0
stack, SP = [], 0
keys = [False] * 16
draw, last_draw = True, 0


def getKeys():
    global keys
    keys = [False] * 16
    keys[getKeyPress()] = True


def getKeyPress():
    key = None
    while key is None:
        char = getch().decode('utf-8')
        if char == 'c':
            raise Exception('C for exit')
        key = keymap.keymap.get(char, None)
    return key


def cycle():
    global PC, IDX, opcode, registers, memory, screen, draw, delay_timer, sound_timer, stack
    opcode = (memory[PC] << 8) + memory[PC + 1]
    first, second, third, fourth = (opcode & 0xF000) >> 12, (
        opcode & 0x0F00) >> 8, (opcode & 0x00F0) >> 4, opcode & 0x000F
    if opcode & 0xFFFF != opcode:
        raise Exception("BAD OPCODE" + hex(opcode))
    PC = (PC + 2) & 0x0FFF
    if first == 0:
        if opcode == 0x00E0:
            screen = [[0] * 64 for i in range(32)]
        elif opcode == 0x00EE:
            PC = stack.pop()
    elif first == 1:
        PC = opcode & 0x0FFF
    elif first == 2:
        stack.append(PC)
        PC = opcode & 0x0FFF
        if len(stack) > 16:
            raise Exception('STACK OVERFLOW!')
    elif first == 3:
        if registers[second] == opcode & 0x00FF:
            PC += 2
    elif first == 4:
        if registers[second] != opcode & 0x00FF:
            PC += 2
    elif first == 5:
        if registers[second] == registers[third]:
            PC += 2
    elif first == 6:
        registers[second] = opcode & 0x00FF
    elif first == 7:
        registers[second] = (
            registers[second] + (opcode & 0x00FF)) % 0x100
    elif first == 8:
        if fourth == 0:
            registers[second] = registers[
                third]
        elif fourth == 1:
            registers[second] |= registers[
                third]
        elif fourth == 2:
            registers[second] &= registers[
                third]
        elif fourth == 3:
            registers[second] ^= registers[
                third]
        elif fourth == 4:
            registers[0xF] = 0
            registers[second] += registers[
                third]
            if registers[second] > 0xFF:
                registers[0xF] = 1
                registers[second] %= 0x100
        elif fourth == 5:
            registers[0xF] = 1
            registers[second] -= registers[
                third]
            if registers[second] < 0:
                registers[0xF] = 0
                registers[second] %= 0x100
        elif fourth == 6:
            registers[0xF] = registers[second] & 0x01
            registers[second] >>= 1
        elif fourth == 7:
            registers[0xF] = 1
            registers[second] = registers[
                third] - registers[second]
            if registers[second] < 0:
                registers[0xF] = 0
                registers[second] %= 0x100
        elif fourth == 0xE:
            registers[0xF] = registers[second] & 0x80 >> 7
            registers[second] = (registers[second] << 1) % 0x100
        else:
            raise Exception('Unknown opcode: ' + hex(opcode))
    elif first == 9:
        if registers[second] != registers[third]:
            PC += 2
    elif first == 0xA:
        IDX = opcode & 0x0FFF
    elif first == 0xB:
        PC = ((opcode & 0x0FFF) + registers[0]) & 0x0FFF
    elif first == 0xC:
        registers[second] = random.randrange(
            0xFF) & opcode
    elif first == 0xD:
        vx, vy, n = registers[second] & 0x3F, registers[
            third] & 0x1F, fourth
        if not n:
            raise Exception('16 BIT Sprite')
        registers[0xF] = 0
        for line in range(n):
            pixels = memory[IDX + line]
            for bit in range(8):
                if vx + bit >= 64 or vy + line >= 31:
                    continue
                if screen[vy + line][vx + bit] & (pixels & (0x80 >> bit)):
                    registers[0xF] = 1
                screen[vy + line][vx + bit] ^= pixels & (0x80 >> bit)
        draw = True
    elif first == 0xE:
        if opcode & 0x00FF == 0x9E:
            getKeys()
            if keys[registers[second]]:
                PC += 2
        elif opcode & 0x00FF == 0xA1:
            getKeys()
            if not keys[registers[second]]:
                PC += 2
        else:
            raise Exception('Unknown opcode: ' + hex(opcode))
    elif first == 0xF:
        if opcode & 0x00FF == 0x07:
            registers[second] = math.ceil((delay_timer - time.time()) / 60.0) % 0xFF
        elif opcode & 0x00FF == 0x0A:
            registers[second] = getKeyPress()
        elif opcode & 0x00FF == 0x15:
            delay_timer = time.time() + registers[second] / 60.0
        elif opcode & 0x00FF == 0x18:
            sound_timer = time.time() + registers[second] / 60.0
        elif opcode & 0x00FF == 0x1E:
            IDX = (IDX + registers[second]) % 0xFFFF
        elif opcode & 0x00FF == 0x29:
            IDX = registers[second] * 5
        elif opcode & 0x00FF == 0x33:
            memory[IDX] = registers[second] // 100
            memory[IDX + 1] = (registers[second] % 100) // 10
            memory[IDX + 2] = registers[second] % 10
        elif opcode & 0x00FF == 0x55:
            memory[IDX:IDX + second + 1] = registers[:second + 1]
            IDX += second + 1
        elif opcode & 0x00FF == 0x65:
            registers[:second + 1] = memory[IDX:IDX + second + 1]
            IDX += second + 1
        else:
            raise Exception('Unknown opcode: ' + hex(opcode))
    else:
        raise Exception('Unknown opcode: ' + hex(opcode))


def draw_screen():
    global draw, last_draw
    os.system('cls')
    for line in screen:
        print(''.join('#' if v else ' ' for v in line))
        draw = False
        last_draw = time.time()


print('V: ', [hex(v) for v in registers],
          'IDX: ', hex(IDX), 'OP: ', hex(opcode), 'STK: ', [hex(v) for v in stack], len(memory), file=sys.stderr)

memory[0:len(font)] = font


if len(sys.argv) < 2:
    raise Exception('Provide ROM path')

with open(sys.argv[1], 'rb') as file:
    program = file.read()

memory[0x200:0x200 + len(program)] = program

while True:
    print('V: ', [hex(v) for v in registers],
          'IDX: ', hex(IDX), 'OP: ', hex(opcode), 'STK: ', [hex(v) for v in stack], len(memory), file=sys.stderr)
    cycle()
    if draw:
        draw_screen()
        #time.sleep(0.01)

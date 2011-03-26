#! /usr/bin/python3
# Detach the Verizon LG-VL600 modem connected on /dev/ttyACM0 from network
#
# Author: Andrew Zaborowski <balrogg@gmail.com>
#
# The contents of this file are AGPLv3
#
import os, sys, select
from termios import *

out_serial = 0
in_serial = -1
in_data = b''

def cdc_pack(data):
	global out_serial
	l = len(data)
	ret = bytes([
		0x5a, 0x48, 0x12, 0xa5, # Header
		(out_serial >> 0) & 255, (out_serial >> 8) & 255,
		(out_serial >> 16) & 255, (out_serial >> 24) & 255,
		(l >> 0) & 255, (l >> 8) & 255,
		(l >> 16) & 255, (l >> 24) & 255,
		0x11, 0xf0 ]) + data + \
		b'\0' * [ 2, 1, 0, 3 ][l & 3] # Padding
	out_serial += 1
	return ret

def cdc_unpack(data):
	global in_serial, in_data
	data = in_data + data
	in_data = b''
	while len(data) and data[0] == 0:
		data = data[1:]
	if len(data) < 14:
		in_data = data
		return None
	if data[0] != 0x5a or data[1] != 0x48 or \
			data[2] != 0x12 or data[3] != 0xa5 or \
			data[12] != 0x11 or data[13] != 0xf0:
		raise Exception("Bad magic: " + repr(data))
	serial = (data[4] << 0) | (data[5] << 8) | \
			(data[6] << 16) | (data[7] << 24)
	l = (data[8] << 0) | (data[9] << 8) | \
			(data[10] << 16) | (data[11] << 24)
	if len(data) < l + 14:
		#raise "Packet incomplete"
		in_data = data
		return None
	in_data = data[14 + l:]
	if serial == in_serial:
		return None
	in_serial = serial
	return data[14:14 + l]

modem = os.open('/dev/ttyACM0', os.O_RDWR)

IFLAG = 0
OFLAG = 1
CFLAG = 2
LFLAG = 3
ISPEED = 4
OSPEED = 5
CC = 6

mode = tcgetattr(modem)
mode[IFLAG] = mode[IFLAG] & ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON)
mode[OFLAG] = mode[OFLAG] & ~(OPOST)
mode[CFLAG] = mode[CFLAG] & ~(CSIZE | PARENB)
mode[CFLAG] = mode[CFLAG] | CS8
mode[LFLAG] = mode[LFLAG] & ~(ECHO | ICANON | IEXTEN | ISIG)
mode[ISPEED] = B115200
mode[OSPEED] = B115200
mode[CC][VMIN] = 1
mode[CC][VTIME] = 0
tcsetattr(modem, TCSAFLUSH, mode)

try:
	# Flush the IN endpoint
	while 1:
		rfd, wfd, xfd = select.select([ modem ], [], [], 0)
		if not modem in rfd:
			break
		os.read(modem, 2048)

	os.write(modem, cdc_pack(b'ATCGATT=0\n'))
	while 1:
		rfd, wfd, xfd = select.select([ modem ], [], [], 1)
		if not modem in rfd:
			break

		line = cdc_unpack(os.read(modem, 2048))
		if line:
			try:
				sys.stdout.write(line.decode("ascii"))
			except:
				sys.stdout.write(repr(line))
except Exception as e:
	os.close(modem)
	raise e

os.close(modem)

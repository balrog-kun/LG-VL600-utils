#! /usr/bin/python3
# Attach the Verizon LG-VL600 modem connected on /dev/ttyACM0 to network
#
# Author: Andrew Zaborowski <balrogg@gmail.com>
#
# The contents of this file are AGPLv3
#
import os, sys, select
from termios import *

out_serial = 5
in_serial = -1
in_data = b''

def cdc_pack_binary(data, checksum):
	global out_serial
	l = len(data)
	plen = 1891
	ret = bytes([
		0x5a, 0x48, 0x12, 0xa5, # Header
		(out_serial >> 0) & 255, (out_serial >> 8) & 255,
		(out_serial >> 16) & 255, (out_serial >> 24) & 255,
		(plen >> 0) & 255, (plen >> 8) & 255,
		(plen >> 16) & 255, (plen >> 24) & 255,
		0x21, 0xf0 ]) + data + \
		b'\0' * (plen - 3 - l) + \
		checksum + b'\x7e\0\0\0' # Padding
	out_serial += 1
	return ret

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

	os.write(modem, cdc_pack_binary(b'\xf1\x4a', b'\xb1\xf3'))
	while 1:
		rfd, wfd, xfd = select.select([ modem ], [], [], 0.5)
		if not modem in rfd:
			break

		line = os.read(modem, 2048)
		if line:
			sys.stdout.write(repr(line))
except Exception as e:
	os.close(modem)
	raise e

os.close(modem)

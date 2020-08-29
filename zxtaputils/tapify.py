#!/usr/bin/env python3

import struct
from .util import BT_PROGRAM, BT_NUM_ARRAY, BT_CHAR_ARRAY, BT_BINARY, compute_checksum
from .tapinfo import ZXHeader, ZXData

"""
tapify.py - Put the specified file into a TAP file
"""


def type_byte(objtype):
    if objtype == 'program':
        return BT_PROGRAM
    elif objtype == 'code':
        return BT_BINARY
    elif objtype == 'nums':
        return BT_NUM_ARRAY
    elif objtype == 'chars':
        return BT_CHAR_ARRAY
    return None


def make_block_parameters(args, data_bytes):
    if args.objtype in ["nums", "chars"]:  # array data
        return [args.varname[0], 0x8000]
    elif args.objtype == "program":
        return [args.autostart_line, len(data_bytes)]
    elif args.objtype == 'code':
        return [args.startaddr, 0x8000]


def tapify(args):
    with open(args.infile, "rb") as infile:
        data_bytes = infile.read()
    filename = args.filename
    data_size = len(data_bytes)
    parameters = make_block_parameters(args, data_bytes)
    zxheader = ZXHeader(type_byte(args.objtype), args.filename, data_size, parameters)
    zxdata = ZXData(data_bytes)
    header_bytes = zxheader.bytes()
    dblock_bytes = zxdata.bytes()

    with open(args.outfile, "wb") as outfile:

        # write header (2 + 19 bytes)
        outfile.write(struct.pack('<H', len(header_bytes)))  # size word
        outfile.write(header_bytes)

        # write the data block (2 + |data_bytes| | + 2 bytes)
        outfile.write(struct.pack('<H', len(dblock_bytes)))  # size word
        outfile.write(dblock_bytes)

    print("done")

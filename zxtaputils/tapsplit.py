#!/usr/bin/env python3

import struct
import os

"""
tapsplit.py - Split tap file into individual blocks
"""

DESCRIPTION = "tapsplit - TAP file splitter"


def read_tap_block(infile, block_num):
    # 2 bytes data length
    data_len = struct.unpack("<H", infile.read(2))[0]
    return infile.read(data_len)


def tapsplit(args):
    block_num = 0
    basename = os.path.basename(args.tapfile).replace('.tap', '')
    with open(args.tapfile, "rb") as infile:
        try:
            while True:
                data_bytes = read_tap_block(infile, block_num)
                if len(data_bytes) == 0:
                    break

                filepath = '%s-%03d.tap' % (basename, block_num)
                if args.outdir is not None:
                    filepath = os.path.join(args.outdir, filepath)
                    if not os.path.exists(args.outdir):
                        os.makedirs(args.outdir)
                print("Writing '%s'" % filepath)
                with open(filepath, 'wb') as outfile:
                    outfile.write(struct.pack("<H", len(data_bytes)))
                    outfile.write(data_bytes)
                    data_bytes = read_tap_block(infile, block_num)
                    outfile.write(struct.pack("<H", len(data_bytes)))
                    outfile.write(data_bytes)
                block_num = block_num + 1
        except:
            pass
    print("done")

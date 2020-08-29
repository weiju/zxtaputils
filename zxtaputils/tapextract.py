import struct
import traceback
from .util import compute_checksum

"""
tapextract.py - Extract the binary data from a TAP file
"""

def read_headerless_data(data_bytes):
    """only check the checksum and length here"""
    computed_checksum = compute_checksum(data_bytes[:-1])
    checksum = struct.unpack_from('<B', data_bytes, len(data_bytes) - 1)[0]
    return data_bytes[1:-1]  # strip the flags and checksum


def read_tap_block(infile):
    # 2 bytes data length
    data_bytes = infile.read(2)
    if len(data_bytes) == 0:
        return None
    data_len = struct.unpack("<H", data_bytes)[0]
    return infile.read(data_len)

def tapextract(args):
    blocknum = 0
    with open(args.tapfile, "rb") as infile:
        try:
            while True:
                data_bytes = read_tap_block(infile)  # header
                if data_bytes is None:
                    print("Error: block %d not found" % args.blocknum)
                    break
                data_bytes = read_tap_block(infile)  # data
                if data_bytes is None:
                    print("Error: block %d not found" % args.blocknum)
                    break
                out_bytes = read_headerless_data(data_bytes)
                if blocknum == args.blocknum:
                    print("Extracting block %d" % blocknum)
                    with open(args.outfile, 'wb') as outfile:
                        outfile.write(out_bytes)
                    break
                blocknum = blocknum + 1
        except:
            traceback.print_exc()
    print("Done.")


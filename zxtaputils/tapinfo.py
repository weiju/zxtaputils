#!/usr/bin/env python3

import struct
import traceback
from .util import BT_PROGRAM, BT_NUM_ARRAY, BT_CHAR_ARRAY, BT_BINARY, BLOCK_TYPES, compute_checksum

"""
tapinfo.py - Print the block information of a TAP file for Sinclair ZX Spectrum.

I wrote this, so the Spartan cross assembler will be able to directly generate
executables that can be loaded into the machine.

This was based on the information found in the cited sources.

Source:

[1] https://faqwiki.zxnet.co.uk/wiki/TAP_format
[2] https://formats.kaitai.io/zx_spectrum_tap/index.html
[3] https://faqwiki.zxnet.co.uk/wiki/Spectrum_tape_interface

      |------ Spectrum-generated data -------|       |---------|

13 00 00 03 52 4f 4d 7x20 02 00 00 00 00 80 f1 04 00 ff f3 af a3

^^^^^...... first block is 19 bytes (17 bytes+flag+checksum)
      ^^... flag byte (A reg, 00 for headers, ff for data blocks)
         ^^ first byte of header, indicating a code block

file name ..^^^^^^^^^^^^^
header info ..............^^^^^^^^^^^^^^^^^
checksum of header .........................^^
length of second block ........................^^^^^
flag byte ...........................................^^
first two bytes of rom .................................^^^^^
checksum (checkbittoggle would be a better name!).............^^
"""

DESCRIPTION = "tapinfo - TAP file viewer"


def read_block_params(block_type, data_bytes):
    if block_type in {BT_NUM_ARRAY, BT_CHAR_ARRAY}:
        return read_array_params(data_bytes)
    else:
        return read_std_params(data_bytes)


def read_array_params(data_bytes):
    reserved = struct.unpack_from("<B", data_bytes, 14)[0]
    varname = struct.unpack_from("<B", data_bytes, 15)[0]
    reserved1 = struct.unpack_from("<H", data_bytes, 16)[0]
    return reserved, varname, reserved1


def read_std_params(data_bytes):
    param1 = struct.unpack_from("<H", data_bytes, 14)[0]
    param2 = struct.unpack_from("<H", data_bytes, 16)[0]
    return param1, param2


def zxheader_from_bytes(data_bytes):
    """Make a ZXHeader object from the specified bytes object"""
    # 1 byte flag byte
    flag1 = struct.unpack_from("<B", data_bytes, 0)[0]

    # 1 byte block type
    block_type = struct.unpack_from("<B", data_bytes, 1)[0]

    # 10 bytes name
    name_bytes = data_bytes[2:12]
    file_name = name_bytes.decode('ascii')

    # 2 bytes data length
    data_len = struct.unpack_from("<H", data_bytes, 12)[0]

    # 4 bytes block parameters
    params = read_block_params(block_type, data_bytes)

    # 1 byte checksum
    checksum = struct.unpack_from("<B", data_bytes, 18)[0]
    return ZXHeader(block_type, file_name, data_len, params, checksum)


class ZXHeader:
    """Representation of a ZX Spectrum header block in a TAP file"""
    def __init__(self, block_type, file_name, data_len, params, checksum=None):
        self.block_type = block_type
        self.file_name = file_name
        self.data_len = data_len
        self.params = params
        # only used as a control
        self.file_checksum = checksum

    def block_params_tostr(self):
        if self.block_type in {BT_NUM_ARRAY, BT_CHAR_ARRAY}:
            return self.array_params_tostr()
        elif self.block_type == BT_PROGRAM:
            return self.prog_params_tostr()
        elif self.block_type == BT_BINARY:
            return self.binary_params_tostr()

    def array_params_tostr(self):
        out = 'Reserved1     : "%02x"\n' % self.params[0]
        out += 'Variable Name : "%c"\n' % self.params[1]
        out += 'Reserved2     : "%04x"\n' % self.params[2]  # always $0080
        return out

    def prog_params_tostr(self):
        out = 'Autostart line: %d\n' % self.params[0]
        out += 'Program Length: %d\n' % self.params[1]
        return out

    def binary_params_tostr(self):
        out = 'Start address : $%04x\n' % self.params[0]
        out += 'Reserved      : $%04x\n' % self.params[1]  # always $8000
        return out

    def make_block_parameters(self):
        if self.block_type in [BT_NUM_ARRAY, BT_CHAR_ARRAY]:  # array data
            return bytes([0x00, str.encode(self.params[1]), 0x00, 0x80])
        elif self.block_type == BT_PROGRAM:
            asl_data = struct.pack("<H", self.params[0])
            lp_data = struct.pack("<H", self.params[1])
            return asl_data + lp_data
        elif self.block_type == BT_BINARY:
            sa_data = struct.pack("<H", self.params[0])
            return sa_data + struct.pack("<H", self.params[1])


    def write(self, outfile):
        """Write this header into the specified output file"""
        outfile.write(self.bytes())

    def prebytes(self):
        result = bytes([0, self.block_type])  # flag and type bytes

        # filename, space padded (10 bytes)
        if len(self.file_name) > 10:
            self.file_name = self.file_name[:10]
        elif len(self.file_name) < 10:
            num_spaces = 10 - len(self.file_name)
            self.file_name += (' ' * num_spaces)
        result += str.encode(self.file_name)

        # encode data length in little endian (2 bytes)
        dsize_w = struct.pack("<H", self.data_len)
        result += dsize_w

        # encode 4 bytes of block parameters
        result += self.make_block_parameters()
        return result

    def bytes(self):
        return self.prebytes() + bytes([self.checksum()])

    def checksum(self):
        return compute_checksum(self.prebytes())

    def __str__(self):
        out = "Flag Byte     : %d\n" % 0
        out += "Block type    : %d (%s)\n" % (self.block_type, BLOCK_TYPES[self.block_type])
        out += 'Filename      : "%s"\n' % self.file_name
        out += "Data Length   : %d\n" % self.data_len
        # TODO: Parameters
        out += self.block_params_tostr()
        out += "Checksum      : $%02x" % self.checksum()
        if self.file_checksum is not None:
            out += " (in file: $%02x)" % self.file_checksum
        return out

def zxdata_from_bytes(data_bytes):
    return ZXData(data_bytes[1:-1])

class ZXData:
    """Representation of a ZX Spectrum data block in a TAP file"""
    def __init__(self, data_bytes):
        """data_bytes is just the pure data, no flags and checksum"""
        self.data_bytes = data_bytes

    def prebytes(self):
        """returns the data bytes with the flag byte prefixed"""
        return bytes([0xff]) + self.data_bytes

    def bytes(self):
        return self.prebytes() + bytes([self.checksum()])

    def write(self, outfile):
        outfile.write(self.bytes())

    def checksum(self):
        return compute_checksum(self.prebytes())

    def __str__(self):
        out = "# data bytes  : %d\n" % (len(self.data_bytes) + 2)
        out += "Checksum      : $%02x" % self.checksum()
        return out


def read_zxtap_block(data_bytes):
    flags = struct.unpack_from("<B", data_bytes, 0)[0]
    if flags == 0:  # Data with header
        print("(HEADER)")
        print(zxheader_from_bytes(data_bytes))
    elif flags == 0xff:
        print("(DATA)")
        print(zxdata_from_bytes(data_bytes))
    else:
        print("flags: %d (DATA ?)" % flags)
        print(zxdata_from_bytes(data_bytes))


def read_tap_block(infile, block_num):
    # 2 bytes data length
    data_bytes = infile.read(2)
    if len(data_bytes) == 0:
        return None
    data_len = struct.unpack("<H", data_bytes)[0]
    print("----------------------------------------------------------")
    print("TAP Block %02d, length: %d" % (block_num, data_len), end=" ")
    return infile.read(data_len)


def next_zxtap_block(data_bytes):
    flags = struct.unpack_from("<B", data_bytes, 0)[0]
    if flags == 0:  # Data with header
        return zxheader_from_bytes(data_bytes)
    elif flags == 0xff:
        return ZXData(data_bytes)
    else:
        return ZXData(data_bytes)

def next_tap_block(infile):
    # 2 bytes data length
    data_bytes = infile.read(2)
    if len(data_bytes) == 0:
        return None
    data_len = struct.unpack("<H", data_bytes)[0]
    data_bytes = infile.read(data_len)
    return next_zxtap_block(data_bytes)


def tapinfo(args):
    block_num = 0
    with open(args.tapfile, "rb") as infile:
        try:
            while True:
                data_bytes = read_tap_block(infile, block_num)
                if data_bytes is None:
                    break
                read_zxtap_block(data_bytes)
                block_num += 1
        except:
            traceback.print_exc()
        print("Done.")

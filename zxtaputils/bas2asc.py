#!/usr/bin/env python3

import struct
import traceback
from .basic_tokens import REV_TOKENS
from .util import BLOCK_TYPES, BT_PROGRAM, BT_NUM_ARRAY, BT_CHAR_ARRAY, BT_BINARY, compute_checksum

"""
bas2asc.py - Turn tokenized ZX Spectrum BASIC file into an ASCII source

http://fileformats.archiveteam.org/wiki/Sinclair_BASIC_tokenized_file

A BASIC file consists of a series of lines, where each line:

  - 2 Bytes line number
  - 2 Bytes line length (n)
  - n Bytes tokenized text

Additional rules:

  - numbers are encoded in a funny format:
    - first the characters of the number, followed by code 0x0e, the "number marker",
      followed by 5 bytes float representation (we can skip that)

  - for longer files, there will be additional code appended to the program
"""

def is_token(b):
    return b in REV_TOKENS

def is_number(b):
    return b == 0x0e

def detokenize_statement(line_bytes, pos, outline):
    while pos < len(line_bytes):
        b = line_bytes[pos]
        if is_token(b):
            outline = outline + ' ' + REV_TOKENS[b] + ' '
            pos = pos + 1
        elif is_number(b):
            pos = pos + 6  # skip the float representation
        else:
            c = chr(b)

            if c == '\r':  # carriage return -> LF
                c = '\n'
            outline = outline + c
            pos = pos + 1
    return pos, outline


def detokenize_line(line_bytes, line_number):
    # read the token, it's one byte
    outline = '%d' % line_number
    end_pos = len(line_bytes)

    pos = 0
    while pos < end_pos:
        pos, outline = detokenize_statement(line_bytes, pos, outline)
    return outline


def next_line(infile, autostart, progoffset):
    """file based next_line(), if progoffset is not None, we have a +3DOS header"""
    if progoffset is not None:
        file_pos = infile.tell() - 128  # - size of +3DOS header
        if file_pos >= progoffset:
            return None

    lnbytes = infile.read(2)
    if len(lnbytes) == 0:
        return None
    line_number = struct.unpack(">H", lnbytes)[0]  # Big endian ????
    num_line_bytes = struct.unpack("<H", infile.read(2))[0]
    data_bytes = infile.read(num_line_bytes)
    outline = detokenize_line(data_bytes, line_number)
    return outline


PLUS3DOS_ISSUE   = 0x01
PLUS3DOS_VERSION = 0x00


def compute_checksum2(bytearr):
    """checksum computed differently than on TAP files"""
    csum = 0
    for b in bytearr:
        csum += b
    return csum % 256


class Plus3DOSHeader:
    """Representation of a +3DOS header"""

    def __init__(self, file_len, block_type, inner_file_len, params):
        self.file_len = file_len
        self.block_type = block_type
        self.inner_file_len = inner_file_len  # file_len - 128 - <size of post program code>
        self.params = params

    def param_bytes(self):
        if self.block_type == BT_PROGRAM:
            result = struct.pack('<H', self.params[0])
            result += struct.pack('<H', self.params[1])
        return result

    def write(self, outfile):
        # 1. Write 'PLUS3DOS'
        outbytes = str.encode('PLUS3DOS')
        outbytes += bytes([0x1a, PLUS3DOS_ISSUE, PLUS3DOS_VERSION])
        outbytes += struct.pack('<L', self.file_len)

        # now compile the BASIC header
        outbytes += bytes([self.block_type])
        outbytes += struct.pack('<H', self.inner_file_len)

        outbytes += self.param_bytes()
        outbytes += bytearray(105)  # actually one more
        checksum = compute_checksum2(outbytes)
        outbytes += bytes([checksum])
        outfile.write(outbytes)

    def __str__(self):
        out = '+3DOS file\n'
        out += '----------\n'
        out += '3DOS file length: %d\n' % self.file_len
        out += "Block type: %s\n" % BLOCK_TYPES[self.block_type]
        out += 'BASIC file length: %d\n' % self.inner_file_len
        if self.block_type == BT_PROGRAM:
            out += "BASIC autostart: %d\n" % self.params[0]
            out += "BASIC prog offset: %d\n" % self.params[1]
        return out


def plus3dos_info(infile):
    """
    Bytes 0...7 - +3DOS signature - 'PLUS3DOS'
    Byte 8      - 1Ah (26) Soft-EOF (end of file)
    Byte 9      - Issue number
    Byte 10     - Version number
    Bytes 11...14   - Length of the file in bytes, 32 bit number,
            least significant byte in lowest address
    Bytes 15...22   - +3 BASIC header data
    Bytes 23...126  - Reserved (set to 0)
    Byte 127    - Checksum (sum of bytes 0...126 modulo 256)

    The BASIC header data field has this format:

    |----------------|-----|-----|-----|-----|-----|-----|-----|
    |   Byte         |  0  |  1  |  2  |  3  |  4  |  5  |  6  |
    |----------------|-----|-----|-----|-----|-----|-----|-----|
    |Program         |  0  |File length|8000h/LINE |prog offset|
    |Numeric array   |  1  |File length| xxx |name | xxx | xxx |
    |Character Array |  2  |File length| xxx |name | xxx | xxx |
    |Code            |  3  |File length| load addy | xxx | xxx |

    prog offset actually points to the address right after the program's last line,
    sometimes that area contains more data e.g. for variables, machine code etc. that
    was created outside of the program or as a result of execution
    """
    infile.seek(11)
    filelen = struct.unpack('<L', infile.read(4))[0]
    basic_header_data = infile.read(8)
    block_type = basic_header_data[0]
    bas_filelen = struct.unpack_from('<H', basic_header_data, 1)
    if block_type == BT_PROGRAM:
        autostart = struct.unpack_from('<H', basic_header_data, 3)[0]
        progoffset = struct.unpack_from('<H', basic_header_data, 5)[0]
        params = [autostart, progoffset]

    header = Plus3DOSHeader(filelen, block_type, bas_filelen, params)
    print(header)
    return autostart, progoffset


def detokenize_file(infile, autostart, progoffset, outfile=None):
    outline = ''
    try:
        while outline is not None:
            outline = next_line(infile, autostart, progoffset)
            if outline is not None:
                if outfile is None:
                    print(outline, end="")
                else:
                    outfile.write(outline)
    except:
        traceback.print_exc()


def detokenize_bytes(data_bytes, outfile=None):
    offset = 0
    while offset < len(data_bytes):
        line_number = struct.unpack_from(">H", data_bytes, offset)[0]  # Big endian
        num_line_bytes = struct.unpack_from("<H", data_bytes, offset + 2)[0]
        start = offset + 4
        line_bytes = data_bytes[start:start+num_line_bytes]
        outline = detokenize_line(line_bytes, line_number)
        if outfile is None:
            print(outline, end="")
        else:
            outfile.write(outline)
        offset += num_line_bytes + 4


def bas2asc(args):
    with open(args.infile, 'rb') as infile:
        # first see if we have an PLUS3DOS header
        try:
            tag = infile.read(8).decode('utf-8')
        except:
            tag = None
        if tag == 'PLUS3DOS':
            autostart, progoffset = plus3dos_info(infile)
            infile.seek(128)  # skip the 128 byte header
        else:
            autostart, progoffset = None, None
            infile.seek(0)  # assume, we just have plain tokenized Spectrum BASIC

        if args.outformat == 'source':
            if args.outfile is not None:
                with open(args.outfile, 'w') as outfile:
                    detokenize_file(infile, autostart, progoffset, outfile)
            else:
                print("\nBASIC source code:")
                print("-------------------")
                detokenize_file(infile, autostart, progoffset)
        else:
            # output tokens
            outbytes = infile.read()
            if args.outfile is not None:
                with open(args.outfile, 'wb') as outfile:
                    outfile.write(outbytes)
            else:
                print("you need to specify an output file for writing tokens")
        print('\nDone')

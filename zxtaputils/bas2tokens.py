#!/usr/bin/env python3

import struct
import traceback
from .basic_tokens import TOKENS, REV_TOKENS
from .tapinfo import ZXHeader, ZXData
from .bas2asc import Plus3DOSHeader
from .util import BT_PROGRAM
from math import log2
import sys

"""
bas2tokens.py - Tokenize a BASIC text file in ASCII format

look at:

https://worldofspectrum.org/ZXBasicManual/zxmanchap24.html


----------------- SOURCE 1 FOR NUMBERS --------------
Any number (except 0) can be written uniquely as
 m x 2e where
 is the sign,
m is the mantissa, and lies between 0.5 and 1 (it cannot be 1),
and e is the exponent, a whole number (possibly negative).

Suppose you write m in the binary scale. Because it is a fraction, it will have a binary point (like the decimal point in the scale of ten) and then a binary fraction (like a decimal fraction); so in binary:
a half is written .1
a quarter is written .01
three quarters is written .11
a tenth is written .000110011001100110011 ... and so on.

With our number m, because it is less than 1, there are no bits before the binary point, and because it is at least 0.5, the bit immediately after the binary point is a 1.

To store the number in the computer, we use five bytes, as follows:

write the first eight bits of the mantissa in the second byte (we know that the first bit is 1), the second eight bits in the third byte, the third eight bits in the fourth byte and the fourth eight bits in the fifth byte;
replace the first bit in the second byte which we know is 1 by the sign: 0 for plus, 1 for minus;
write the exponent +128 in the first byte. For instance, suppose our number is 1/10
1/10 =4/5x2-3
Thus the mantissa m is .11001100110011001100110011001100 in binary (since the 33rd bit is 1, we shall round the 32nd up from 0 to 1), and the exponent e is 3.

Applying our three rules gives the five bytes

There is an alternative way of storing whole numbers between 65535 and +65535:

the first byte is 0.
the second byte is 0 for a positive number, FFh for a negative one,
the third and fourth bytes are the less and more significant bytes of the number (or the number +131072 if it is negative),
the fifth byte is 0.
"""

class BasicToken:
    """super class for BASIC tokens"""

    def write(self, outfile):
        """default write function: write the result of bytes()"""
        outfile.write(self.bytes())


class BasicLineNumber(BasicToken):
    """An line number token, this class helps in rendering the correct byte sequence"""
    def __init__(self, value):
        self.value = value

    def num_bytes(self):
        return 2

    def bytes(self):
        """returns the representation as a bytes object"""
        return struct.pack('>H', self.value)  # line number is big endian

    def __repr__(self):
        return str(self.value)


class BasicInt(BasicToken):
    """An integer token, this class helps in rendering the correct byte sequence"""
    def __init__(self, value):
        self.value = value
        self.strvalue = str(value)

    def num_bytes(self):
        # Length of the string presentation + 5 + 0x0e marker
        return len(self.strvalue) + 5 + 1

    def bytes(self):
        strbytes = self.strvalue.encode('ascii')  # the original string representation
        nbytes = struct.pack("<H", self.value)
        intbytes = bytes([0x0e, 0x00, 0x00 if self.value >= 0 else 0xff,
                          nbytes[0], nbytes[1], 0x00])
        return strbytes + intbytes

    def __repr__(self):
        return str(self.value)


class BasicFloat(BasicToken):
    """A floating point number token, this class helps in rendering the correct byte sequence"""
    def __init__(self, value, strvalue):
        self.value = value
        self.strvalue = strvalue

    def num_bytes(self):
        return len(self.strvalue) + 5 + 1

    def bytes(self):
        outbytes = self.strvalue.encode('ascii') # the original string representation
        # Write the 5 byte floating point representation:
        # 1 byte exponent, 4 bytes mantissa
        m, e = make_float(self.value)
        outbytes += struct.pack('<B', 0x0e)  # write the number marker
        outbytes += struct.pack('<B', e)     # write the exponent
        outbytes += struct.pack('>L', m)     # write the 4 byte mantissa, big endian format
        return outbytes

    def __repr__(self):
        return str(self.value)

class BasicString(BasicToken):
    """A string token"""
    def __init__(self, value):
        self.value = value

    def num_bytes(self):
        return len(self.value) + 2  # the double quotes are included

    def bytes(self):
        outstr = '"%s"' % self.value
        return outstr.encode('ascii')

    def __repr__(self):
        return '"' + self.value + '"'

class BasicSyntaxChars(BasicToken):
    """syntactic characters that don't have any particular things"""
    def __init__(self, value):
        self.value = value

    def num_bytes(self):
        return len(self.value)

    def bytes(self):
        """write the string"""
        return self.value.encode('ascii')

    def __repr__(self):
        return str(self.value)

class BasicKeyword(BasicToken):
    """BASIC keyword"""
    def __init__(self, value):
        self.value = value

    def num_bytes(self):
        return 1

    def bytes(self):
        """write the line number to the output file in big endian (!) format"""
        return struct.pack('<B', self.value)

    def __repr__(self):
        return REV_TOKENS[self.value]


def convert_token(token, current_tokens):
    """convert the token into the appropriate representation"""
    if token in TOKENS:
        return BasicKeyword(TOKENS[token])

    # is it a string ?
    if token.startswith('"'):
        return BasicString(token.strip('"'))
    # is it an integer ?
    try:
        value = int(token)
        if len(current_tokens) == 0:  # line numbers are treated differently
            return BasicLineNumber(value)
        return BasicInt(value)  # this is just a regular integer
    except:
        pass
    # is it a floating point number ?
    try:
        value = float(token)
        return BasicFloat(value, token)
    except:
        pass

    # fallback: just return the characters
    return BasicSyntaxChars(token)


def next_token(line, current_tokens):
    """retrieve the next token from the given line. Returns the token and the rest of the line
    as the result
    Known issues:
    - does not preserve white space
    """
    token = ""
    i = 0
    in_string = False

    line = line.lstrip()  # remove leading space
    while i < len(line):
        c = line[i]

        # handle strings
        if c in ['"', '(', ')', ',', '='] and i > 0 and not in_string:  # handle as separate tokens
            break
        elif c == '"' and i == 0:
            in_string = True
        elif c == '"' and in_string:  # end the string
            in_string = False
        elif c in ['(', ')', ',', '='] and i == 0:
            i = i + 1
            token = c
            break
        elif not in_string and c.isspace():
            break

        token = token + c
        i = i + 1

    # process the token
    if len(token) == 0:
        token = None
    else:
        token = convert_token(token, current_tokens)
    return token, line[i:]

def tokenize_line(line):
    result = []
    while len(line) > 0:  # ignore empty lines
        token, line = next_token(line, result)
        if token is not None:
            result.append(token)
    return result


def render_line(tokenized):
    # the line number does not contribute to the number of bytes
    num_bytes = 1  # add the 0x0d at the end of each line
    for token in tokenized[1:]:
        num_bytes += token.num_bytes()

    outbytes = tokenized[0].bytes()  # line number
    outbytes += struct.pack("<H", num_bytes)
    for token in tokenized[1:]:
        outbytes += token.bytes()
    outbytes += struct.pack('<B', 0x0d)
    return outbytes


def bas2token_bytes(infile):
    """Reads the BASIC source code from the specified input file and
    returns a bytes object that contains the entire program"""
    result = None
    while True:
        line = infile.readline()
        if not line or len(line) == 0:
            break
        tokenized = tokenize_line(line)
        if len(tokenized) > 0:
            outbytes = render_line(tokenized)
            if result is None:
                result = outbytes
            else:
                result += outbytes
    return result


def mantissa_int_part(n):
    """convert the integral part of a decimal number to mantissa digits"""
    result = []
    n = int(n)
    while n > 0:
        q = n / 2
        rem = n % 2
        if rem == 0:
            result.append('0')
        else:
            result.append('1')
        n = int(q)
    result.reverse()
    return result

def make_float(n, num_bits=32, bias=128):
    """
    for a float, compute the mantissa
    TODO: this function fails for very large numbers, because we don't really process the
    integral part of the mantissa correctly.
    It also currently fails for n = 0.1
    """
    m = []
    exponent = 0
    leading_zero = True
    negative = n < 0
    n = abs(n)

    # if we have a number before the decimal
    m = mantissa_int_part(n)
    if len(m) > 0:
        n = n - int(n)
        exponent = len(m)
        leading_zero = False

    #print("m = %s, n = %f" % (m, n))
    while len(m) <= num_bits:
        n = n * 2
        #print(n)
        if int(n) > 0:
            m.append('1')
            n = n - int(n)
            leading_zero = False
        else:
            if leading_zero:
                exponent = exponent - 1
            else:
                m.append('0')

    #print('mantissa: %s, exp: %d (base2)' % (m, exponent))
    if not negative:  # handle sign
        m[0] = '0'

    # round up the last digit of the mantissa if the 33rd digit is a 1 and chop off
    # digit 33 after that
    if m[-2] == '0' and m[-1] == '1':
        m[-2] = '1'
    m = ''.join(m[:-1])
    #print('mantissa: %s, exp: %d (base2)' % (m, exponent))

    exponent = exponent + bias
    m = int(m, 2)
    return m, exponent


def bas2tap(args):
    with open(args.infile) as infile:
        outbytes = bas2token_bytes(infile)

    if args.format == 'tap':
        zxheader = ZXHeader(BT_PROGRAM, "", len(outbytes), [args.autostart, len(outbytes)])
        zxdata = ZXData(outbytes)
        header_bytes = zxheader.bytes()
        dblock_bytes = zxdata.bytes()
        with open(args.outfile, "wb") as outfile:
            # write header (2 + 19 bytes)
            outfile.write(struct.pack('<H', len(header_bytes)))  # size word
            outfile.write(header_bytes)

            # write the data block (2 + |data_bytes| | + 2 bytes)
            outfile.write(struct.pack('<H', len(dblock_bytes)))  # size word
            outfile.write(dblock_bytes)
    elif args.format == 'plain':
        with open(args.outfile, "wb") as outfile:
            outfile.write(outbytes)
    elif args.format == '+3dos':
        # Write a +3DOS Header as a prefix
        with open(args.outfile, "wb") as outfile:
            inner_file_len = len(outbytes)
            file_len = len(outbytes) + 128
            header = Plus3DOSHeader(file_len, BT_PROGRAM, inner_file_len, [args.autostart, inner_file_len])
            header.write(outfile)
            outfile.write(outbytes)

"""
I just leave this here for debugging the float conversion easier
"""
if __name__ == '__main__':
    if len(sys.argv) >= 2:
        n = float(sys.argv[1])
        print("n is: %f" % n)
        m, e = make_float(n)
        print("m: $%04x, e: $%02x" % (m, e))
        #m  = mantissa_int_part(n)
        print(m)
    else:
        print("usage: bas2tokens.py <number>")

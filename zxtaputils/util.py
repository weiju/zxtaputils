"""
General TAP related functions
"""

BT_PROGRAM    = 0
BT_NUM_ARRAY  = 1
BT_CHAR_ARRAY = 2
BT_BINARY     = 3
BLOCK_TYPES = ['Program', 'Number array', 'Character array', 'Code']


def compute_checksum(in_bytes, start_value=0):
    csum = start_value
    for i, b in enumerate(in_bytes):
        csum = csum^(b&0xff)
    return csum


from .bas2asc import detokenize_bytes
from .tapinfo import next_tap_block

"""
tap2basic.py - Extracts the BASIC code from the specified block in the TAP file
"""

def tap2basic(args):
    blocknum = 0
    with open(args.infile, "rb") as infile:
        while True:
            header_block = next_tap_block(infile)
            if header_block is None:
                print("Could not find block %d" % args.blocknum)
                break
            data_block = next_tap_block(infile)
            if data_block is None:
                print("Could not find block %d" % args.blocknum)
                break
            if blocknum == args.blocknum:
                break
            blocknum += 1

        if blocknum == args.blocknum:
            if args.outformat == "tokens":
                if args.outfile is None:
                    print("Please provide an output file to write tokenized BASIC program to")
                else:
                    with open(args.outfile, "wb") as outfile:
                        outfile.write(data_block.data_bytes[1:-1])
            else:
                # block found, now parse the BASIC data, remember the block still has flag and checksum,
                if args.outfile is not None:
                    with open(args.outfile, "w") as outfile:
                        detokenize_bytes(data_block.data_bytes[1:-1], outfile)
                else:
                    detokenize_bytes(data_block.data_bytes[1:-1])

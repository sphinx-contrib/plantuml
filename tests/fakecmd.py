#!/usr/bin/env python
import sys


def dump(fout, fin):
    # embed as PostScript comment
    fout.write('% ' + ' '.join(sys.argv) + '\n')
    for line in fin:
        fout.write('% ' + line)


if '-pipe' in sys.argv:
    dump(sys.stdout, sys.stdin)
else:
    for fname in sys.argv[1:]:
        if not fname.endswith('.puml'):
            continue
        with open(fname[:-5] + '.png', 'w') as fout:
            with open(fname, 'r') as fin:
                dump(fout, fin)

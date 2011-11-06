#!/usr/bin/env python
import sys
assert len(sys.argv) > 1
f = open(sys.argv[-1][:-4] + '.pdf', 'w')
try:
    f.write(' '.join(sys.argv[1:]))
finally:
    f.close()

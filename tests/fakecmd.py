#!/usr/bin/env python
import sys

# embed as PostScript comment
sys.stdout.write('% ' + ' '.join(sys.argv) + '\n')
for line in sys.stdin:
    sys.stdout.write('% ' + line)

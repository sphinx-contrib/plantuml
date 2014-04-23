#!/usr/bin/env python
import sys

# embed as PostScript comment
print '%', ' '.join(sys.argv)
for line in sys.stdin:
    sys.stdout.write('% ' + line)

#!/usr/bin/env python
import sys
print '%', ' '.join(sys.argv)
for line in sys.stdin:
    sys.stdout.write(line)

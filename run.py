#!/usr/bin/env python

import time
import cm2350


def main():
    ECU = cm2350.CM2350()

    start = time.time()
    ECU.emu.run()
    runtime = time.time() - start
    ticks = ECU.emu.systicks()

    print("since start: %d instructions in %.3f secs: %.3f ops/sec" % \
                (ticks, runtime, ticks/runtime))


if __name__ == '__main__':
    main()

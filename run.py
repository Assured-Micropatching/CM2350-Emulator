#!/usr/bin/env python

import cm2350


def main():
    ECU = cm2350.CM2350()
    ECU.emu.run()


if __name__ == '__main__':
    main()

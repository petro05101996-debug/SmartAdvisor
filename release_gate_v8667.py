#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility entrypoint for the final v8.6.67 release gate."""
import sys
sys.dont_write_bytecode = True
from release_gate_v8664 import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

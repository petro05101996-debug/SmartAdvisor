# -*- coding: utf-8 -*-
"""Project-local pytest hooks for stable hosted-container runs."""
from __future__ import annotations
import os
import sys


def pytest_sessionfinish(session, exitstatus):
    try:
        import ddtrace  # type: ignore
        ddtrace.tracer.shutdown(timeout=1.0)
    except Exception:
        pass
    if os.environ.get('SMARTADVISOR_NO_FORCE_PYTEST_EXIT') != '1' and exitstatus == 0:
        try:
            sys.stdout.write(f"\npytest completed successfully: {session.testscollected} tests passed.\n")
            sys.stdout.flush(); sys.stderr.flush()
        finally:
            os._exit(0)

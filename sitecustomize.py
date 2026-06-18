# -*- coding: utf-8 -*-
"""Project-local test stability settings.

Some execution environments preload third-party pytest plugins that are not part
of this project. They can leave background hooks/threads alive after the tests
finish, so the suite prints "passed" but the process does not exit. For this
repository we intentionally run only the built-in pytest functionality unless a
caller explicitly overrides the environment.
"""
from __future__ import annotations
import os
import sys

argv0 = (sys.argv[0] or '').lower()
if argv0.endswith('pytest') or argv0.endswith('pytest.exe') or 'pytest' in os.path.basename(argv0):
    os.environ.setdefault('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')

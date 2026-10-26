"""Fail if tests are missing, rather than accepting an empty test run."""
import unittest
suite = unittest.defaultTestLoader.discover('app_tests')
if suite.countTestCases() == 0:
    raise SystemExit('No application tests discovered')
raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())

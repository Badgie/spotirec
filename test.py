import unittest
import sys
from tests.lib import compare, runner

# set comparison function
unittest.defaultTestLoader.sortTestMethodsUsing = compare

# load tests
suite = unittest.defaultTestLoader.discover(start_dir='tests')

# run
if __name__ == '__main__':
    print('\033[33m' + f'{" " * 19}Running test suite for Spotirec' + '\033[0m')
    print('----------------------------------------------------------------------\n')
    result = runner.run(suite)
    print(f'-> {result.testsRun - len(result.errors) - len(result.failures)} passed')
    if result.unexpectedSuccesses:
        print(f'\t{len(result.unexpectedSuccesses)} unexpected')
    if result.skipped:
        print(f'-> {len(result.skipped)} skipped')
    if result.errors:
        print(f'-> {len(result.errors)} errors')
    if result.failures:
        print(f'-> {len(result.failures)} failed')
        if result.expectedFailures:
            print(f'\t{len(result.expectedFailures)} expected')
    if not result.wasSuccessful():
        sys.exit(1)

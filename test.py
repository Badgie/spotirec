import unittest
from tests.lib import compare, runner

# set comparison function
unittest.defaultTestLoader.sortTestMethodsUsing = compare

# load tests
suite = unittest.defaultTestLoader.discover(start_dir='tests')

# run
if __name__ == '__main__':
    print('\033[33m' + f'{" " * 19}Running test suite for Spotirec' + '\033[0m')
    print('----------------------------------------------------------------------\n')
    runner.run(suite)

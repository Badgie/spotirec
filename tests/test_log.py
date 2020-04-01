from tests.lib import ordered, SpotirecTestCase, runner
from spotirec import log
import os
import sys


class TestLog(SpotirecTestCase):
    """
    Running tests for log.py
    """

    @classmethod
    def setUpClass(cls) -> None:
        """
        Setup any necessary data or states before any tests in this class is run
        """
        if runner.verbosity > 0:
            super(TestLog, cls).setUpClass()
            print(f'file:/{__file__}\n')
        cls.logger = log.Log()
        cls.stdout_preserve = sys.__stdout__

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Clear or resolve any necessary data or states after all tests in this class are run
        """
        if runner.verbosity > 0:
            super(TestLog, cls).tearDownClass()

    def setUp(self):
        """
        Setup any necessary data or states before each test is run
        """
        self.logger.LOG_PATH = 'fixtures/logs'
        self.logger.set_level(50)
        sys.stdout = open('fixtures/log-test', 'w')

    def tearDown(self):
        """
        Clear or resolve any necessary data or states after each test is run
        """
        os.remove('fixtures/log-test')
        sys.stdout = self.stdout_preserve

    @ordered
    def test_set_level(self):
        """
        Testing set_level()
        """
        self.logger.set_level(log.INFO)
        self.assertEqual(self.logger.LEVEL, 30)

    @ordered
    def test_suppress_warnings(self):
        """
        Testing suppress_warnings()
        """
        self.logger.suppress_warnings(True)
        self.assertTrue(self.logger.SUPPRESS_WARNINGS)
        self.logger.suppress_warnings(False)
        self.assertFalse(self.logger.SUPPRESS_WARNINGS)

    @ordered
    def test_log_file_log(self):
        """
        Testing log_file() log arg
        """
        self.logger.info('test_log')
        self.logger.log_file()
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open('fixtures/log-test', 'r') as f:
            file = f.read().split('/')[2].strip('\n')
            with open(f'{self.logger.LOG_PATH}/{file}') as f1:
                stdout = f1.read()
                self.assertIn('test_log', stdout)
        os.remove(f'{self.logger.LOG_PATH}/{file}')
        os.rmdir(self.logger.LOG_PATH)

    @ordered
    def test_log_file_crash(self):
        """
        Testing log_file() on crash
        """
        self.logger.info('test_log')
        self.logger.log_file(crash=True)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open('fixtures/log-test', 'r') as f:
            file = f.read().split('/')[2].strip('\n')
            with open(f'{self.logger.LOG_PATH}/{file}') as f1:
                stdout = f1.read()
                self.assertIn('test_log', stdout)
        os.remove(f'{self.logger.LOG_PATH}/{file}')
        os.rmdir(self.logger.LOG_PATH)

    @ordered
    def test_error(self):
        """
        Testing error()
        """
        s = 'test_error'
        self.logger.error(s)
        self.assertIn(s, self.logger.LOG)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open('fixtures/log-test', 'r') as f:
            stdout = f.read()
            self.assertIn('ERROR', stdout)
            self.assertIn('test_error', stdout)

    @ordered
    def test_warning(self):
        """
        Testing warning()
        """
        s = 'test_warning'
        self.logger.warning(s)
        self.assertIn(s, self.logger.LOG)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open('fixtures/log-test', 'r') as f:
            stdout = f.read()
            self.assertIn('WARNING', stdout)
            self.assertIn('test_warning', stdout)

    @ordered
    def test_info(self):
        """
        Testing info()
        """
        s = 'test_info'
        self.logger.info(s)
        self.assertIn(s, self.logger.LOG)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open('fixtures/log-test', 'r') as f:
            stdout = f.read()
            self.assertIn('INFO', stdout)
            self.assertIn('test_info', stdout)

    @ordered
    def test_verbose(self):
        """
        Testing verbose()
        """
        s = 'test_verbose'
        self.logger.verbose(s)
        self.assertIn(s, self.logger.LOG)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open('fixtures/log-test', 'r') as f:
            stdout = f.read()
            self.assertIn('INFO', stdout)
            self.assertIn('test_verbose', stdout)

    @ordered
    def test_debug(self):
        """
        Testing debug()
        """
        s = 'test_debug'
        self.logger.debug(s)
        self.assertIn(s, self.logger.LOG)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open('fixtures/log-test', 'r') as f:
            stdout = f.read()
            self.assertIn('DEBUG', stdout)
            self.assertIn('test_debug', stdout)

    @ordered
    def test_append_log(self):
        """
        Testing append_log()
        """
        self.logger.append_log('TEST', 'test_message')
        self.assertIn('test_message', self.logger.LOG)

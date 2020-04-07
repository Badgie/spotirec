from pathlib import Path
import os
import time

NOTSET = 0
ERROR = 10
WARNING = 20
INFO = 30
VERBOSE = 40
DEBUG = 50
LOG_LEVELS = {0: 'NOTSET', 10: 'ERROR', 20: 'WARNING', 30: 'INFO', 40: 'VERBOSE', 50: 'DEBUG'}


class Log:
    LEVEL = INFO
    SUPPRESS_WARNINGS = False
    LOG_PATH = f'{Path.home()}/.config/spotirec/logs'
    LOG = ''

    def set_level(self, level: int):
        self.LEVEL = level

    def suppress_warnings(self, suppress: bool):
        self.SUPPRESS_WARNINGS = suppress

    def log_file(self, crash=False):
        if not os.path.isdir(self.LOG_PATH):
            os.makedirs(self.LOG_PATH)
        t = time.localtime()
        file_name = f'spotirec_{t.tm_mday}-{t.tm_mon}-{t.tm_year}.{"crash." if crash else ""}log'
        with open(f'{self.LOG_PATH}/{file_name}', 'w') as file:
            file.write(self.LOG)
        self.info(f'saved{" crash" if crash else ""} log to {self.LOG_PATH}/{file_name}')

    def error(self, msg):
        if self.LEVEL >= ERROR:
            print('\033[91m' + 'ERROR: ' + '\033[0m' + str(msg))
        self.append_log('ERROR', msg)

    def warning(self, msg):
        if self.LEVEL >= WARNING and not self.SUPPRESS_WARNINGS:
            print('\033[93m' + 'WARNING: ' + '\033[0m' + str(msg))
        self.append_log('WARNING', msg)

    def info(self, msg):
        if self.LEVEL >= INFO:
            print('\033[96m' + 'INFO: ' + '\033[0m' + str(msg))
        self.append_log('INFO', msg)

    def verbose(self, msg):
        if self.LEVEL >= VERBOSE:
            print('\033[96m' + 'INFO: ' + '\033[0m' + str(msg))
        self.append_log('INFO', msg)

    def debug(self, msg):
        if self.LEVEL >= DEBUG:
            print('\033[94m' + 'DEBUG: ' + '\033[0m' + str(msg))
        self.append_log('DEBUG', msg)

    def append_log(self, level_name, msg):
        self.LOG += f'[{time.ctime(time.time())}][{level_name}]: {str(msg)}\n'

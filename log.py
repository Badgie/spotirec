from pathlib import Path
import os
import time

ERROR = 0
WARNING = 10
INFO = 20
VERBOSE = 30
DEBUG = 40
LOG_FILE = f'{Path.home()}/.config/spotirec/spotirec.log'

if not os.path.isfile(LOG_FILE):
    f = open(LOG_FILE, 'w')
    f.close()


class Log:
    LEVEL = INFO

    def log_file(self, level_name, msg):
        with open(LOG_FILE, 'a') as file:
            file.write(f'[{time.ctime(time.time())}][{level_name}]: {msg}')

    def error(self, msg):
        if self.LEVEL >= ERROR:
            print('\033[91m' + 'ERROR: ' + '\033[0m' + msg)
        self.log_file('ERROR', msg)

    def warning(self, msg):
        if self.LEVEL >= WARNING:
            print('\033[93m' + 'WARNING: ' + '\033[0m' + msg)
        self.log_file('WARNING', msg)

    def info(self, msg):
        if self.LEVEL >= INFO:
            print('\033[96m' + 'INFO: ' + '\033[0m' + msg)
        self.log_file('INFO', msg)

    def verbose(self, msg):
        if self.LEVEL >= VERBOSE:
            print('\033[96m' + 'INFO: ' + '\033[0m' + msg)
        self.log_file('INFO', msg)

    def debug(self, msg):
        if self.LEVEL >= DEBUG:
            print('\033[94m' + 'DEBUG: ' + '\033[0m' + msg)
        self.log_file('DEBUG', msg)

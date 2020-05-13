from . import lib
from .ut_ext import SpotirecTestResults, SpotirecTestRunner

ordered, compare = lib.order_handler()

# setup runner with low verbosity, and no variable printing on fail/error, and custom results class
# for verbose output and variable printing, set verbosity=5 and tb_locals=True
runner = SpotirecTestRunner(verbosity=5, tb_locals=True, resultclass=SpotirecTestResults)

from . import spotirec
from .spotirec import init, recommend


def run():
    parser = spotirec.create_parser()
    spotirec.args = parser.parse_args()
    init()
    recommend()
    if spotirec.args.log:
        spotirec.logger.log_file()

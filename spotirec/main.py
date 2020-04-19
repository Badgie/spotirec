from spotirec import spotirec
from .spotirec import setup_config_dir, init, recommend


def run():
    parser = spotirec.create_parser()
    spotirec.args = parser.parse_args()
    setup_config_dir()
    init()
    recommend()
    if spotirec.args.log:
        spotirec.logger.log_file()

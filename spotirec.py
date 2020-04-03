from spotirec import spotirec
from spotirec.spotirec import setup_config_dir, init, recommend

parser = spotirec.create_parser()

spotirec.args = parser.parse_args()

if __name__ == '__main__':
    setup_config_dir()
    init()
    recommend()
    if spotirec.args.log:
        spotirec.logger.log_file()

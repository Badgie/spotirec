from . import spotirec
from .spotirec import setup_config_dir, init, add_tracks_to_playlist

def run():
    parser = spotirec.create_parser()
    spotirec.args = parser.parse_args()
    setup_config_dir()
    init()
    add_tracks_to_playlist()

    if spotirec.args.log:
        spotirec.logger.log_file()

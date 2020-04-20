#!/usr/bin/env python
import webbrowser
import json
import argparse
import hashlib
import re
import math
import base64
from . import oauth2, api as sp_api, conf as sp_conf, log, recommendation
import sys
from io import BytesIO
from PIL import Image
from bottle import route, run, request
from pathlib import Path

__version__ = '1.3.1'

PORTS = [8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009]
CONFIG_PATH = f'{Path.home()}/.config/spotirec'
TUNING_FILE = f'{Path.home()}/.config/spotirec/tuning-opts'

TUNE_PREFIX = ['max', 'min', 'target']
TUNE_ATTR = {'int': {'duration_ms': {'min': 0, 'max': sys.maxsize * 2 + 1, 'rec_min': 0,
                                     'rec_max': 3600000},
                     'key': {'min': 0, 'max': 11, 'rec_min': 0, 'rec_max': 11},
                     'mode': {'min': 0, 'max': 1, 'rec_min': 0, 'rec_max': 1},
                     'time_signature': {'min': 0, 'max': 500, 'rec_min': 0, 'rec_max': 500},
                     'popularity': {'min': 0, 'max': 100, 'rec_min': 0, 'rec_max': 100}},
             'float': {'acousticness': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 1.0},
                       'danceability': {'min': 0.0, 'max': 1.0, 'rec_min': 0.1, 'rec_max': 0.9},
                       'energy': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 1.0},
                       'instrumentalness': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 1.0},
                       'liveness': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 0.4},
                       'loudness': {'min': -60, 'max': 0, 'rec_min': -20, 'rec_max': 0},
                       'speechiness': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 0.3},
                       'valence': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 1.0},
                       'tempo': {'min': 0.0, 'max': 220.0, 'rec_min': 60.0, 'rec_max': 210.0}}}
URI_RE = r'spotify:(artist|track):[a-zA-Z0-9]+'
PLAYLIST_URI_RE = r'spotify:playlist:[a-zA-Z0-9]+'
TRACK_URI_RE = r'spotify:track:[a-zA-Z0-9]+'
TUNE_RE = r'\w+_\w+=\d+(.\d+)?'
SHOW_EPI_RE = r'spotify:(show|episode):[a-zA-Z0-9]+'

logger = log.Log()
conf = sp_conf.Config()
api = sp_api.API()
sp_oauth = oauth2.SpotifyOAuth()
rec = recommendation.Recommendation()
headers = {}
args = None


def create_parser() -> argparse.ArgumentParser:
    # Argument parser
    arg_parser = \
        argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog='spotirec',
                                epilog="""
passing no recommendation scheme defaults to basing recommendations off your top 5 valid seed genres
spotirec is released under GPL-3.0 and comes with ABSOLUTELY NO WARRANTY, for details read LICENSE
""")
    arg_parser.add_argument('n', nargs='?', type=int, const=5, default=5,
                            help='amount of seeds to use on no-arg recommendations as an integer - '
                                 'note that this must appear as the first argument if used and can '
                                 'only be used with no-arg')

    # Verbosity
    verbosity_group = arg_parser.add_argument_group(title='Verbosity switches')
    mutex_verbosity = verbosity_group.add_mutually_exclusive_group()
    mutex_verbosity.add_argument('-v', '--verbose', action='store_true', help='verbose printing')
    mutex_verbosity.add_argument('-q', '--quiet', action='store_true', help='quiet printing')
    mutex_verbosity.add_argument('--debug', action='store_true',
                                 help='print for debugging purposes')
    verbosity_group.add_argument('--suppress-warnings', action='store_true',
                                 help='suppress warning messages')
    verbosity_group.add_argument('--log', action='store_true',
                                 help='log all output, including those above logging level, to '
                                      'file')

    # Recommendation schemes
    rec_scheme_group = arg_parser.add_argument_group(title='Recommendation schemes')
    # Create mutually exclusive group for recommendation types to ensure only one is given
    mutex_group = rec_scheme_group.add_mutually_exclusive_group()
    mutex_group.add_argument('-a', metavar='SEED_SIZE', nargs='?', type=int, const=5,
                             choices=range(1, 6), help='base recommendations on your top artists')
    mutex_group.add_argument('-t', metavar='SEED_SIZE', nargs='?', type=int, const=5,
                             choices=range(1, 6), help='base recommendations on your top tracks')
    mutex_group.add_argument('-st', metavar='SEED_SIZE', nargs='?', type=int, const=5,
                             help='base recommendations on top saved tracks')
    mutex_group.add_argument('-ac', action='store_true',
                             help='base recommendations on custom top artists')
    mutex_group.add_argument('-tc', action='store_true',
                             help='base recommendations on custom top tracks')
    mutex_group.add_argument('-gc', action='store_true',
                             help='base recommendations on custom top valid seed genres')
    mutex_group.add_argument('-stc', action='store_true',
                             help='base recommendations on custom top saved tracks')
    mutex_group.add_argument('-gcs', action='store_true',
                             help='base recommendations on custom seed genres')
    mutex_group.add_argument('-c', action='store_true',
                             help='base recommendations on a custom seed')
    rec_scheme_group.add_argument('--preserve', action='store_true',
                                  help='preserve previous playlist and create new')

    # Saving arguments
    save_group = arg_parser.add_argument_group(title='Saving arguments')
    # You should only be able to save or remove the current track at once, not both
    save_mutex_group = save_group.add_mutually_exclusive_group()
    add_mutex_group = save_group.add_mutually_exclusive_group()
    save_mutex_group.add_argument('-s', action='store_true', help='like currently playing track')
    save_mutex_group.add_argument('-sr', action='store_true',
                                  help='remove currently playing track from liked tracks')
    add_mutex_group.add_argument('--add-to', metavar='[PLAYLIST | URI]', nargs=1, type=str,
                                 help='add currently playing track to input playlist')
    add_mutex_group.add_argument('--remove-from', metavar='[PLAYLIST | URI]', nargs=1, type=str,
                                 help='remove currently playing track from input playlist')
    save_group.add_argument('--save-playlist', action='store_true', help='save a playlist')
    save_group.add_argument('--remove-playlists', metavar='ID', nargs='+', type=str,
                            help='remove playlist(s)')
    save_group.add_argument('--save-device', action='store_true', help='save a playback device')
    save_group.add_argument('--remove-devices', metavar='ID', nargs='+', type=str,
                            help='remove playback device(s)')
    save_group.add_argument('--remove-presets', metavar='ID', nargs='+', type=str,
                            help='remove preset(s)')

    # Recommendation modifications
    rec_options_group = arg_parser.add_argument_group(
        title='Recommendation options',
        description='These may only appear when creating a playlist')
    rec_options_group.add_argument('-l', metavar='LIMIT', nargs=1, type=int, choices=range(1, 101),
                                   help='amount of tracks to add (default: 100, max: 100)')
    rec_options_group.add_argument('--tune', metavar='ATTR', nargs='+', type=str,
                                   help='specify tunable attribute(s)')
    rec_options_group.add_argument('--play', metavar='DEVICE', nargs=1,
                                   help='select playback device to start playing on')
    rec_options_group.add_argument('--load-preset', metavar='ID', nargs=1, type=str,
                                   help='load and use preset')
    rec_options_group.add_argument('--save-preset', metavar='ID', nargs=1, type=str,
                                   help='save options as preset')

    # Blacklisting
    blacklist_group = arg_parser.add_argument_group(title='Blacklisting')
    blacklist_group.add_argument('-b', '--blacklist-add', metavar='URI', nargs='+', type=str,
                                 help='blacklist track(s) and/or artist(s)')
    blacklist_group.add_argument('-br', '--blacklist-remove', metavar='URI', nargs='+', type=str,
                                 help='remove track(s) and/or artists(s) from blacklist')

    # Playback
    playback_group = arg_parser.add_argument_group(title='Playback')
    playback_group.add_argument('--transfer-playback', metavar='ID', nargs=1, type=str,
                                help='transfer playback to input device ID')

    # Printing
    print_group = arg_parser.add_argument_group(title='Printing')
    print_group.add_argument('--print', metavar='TYPE', nargs='+', type=str,
                             choices=['artists', 'tracks', 'genres', 'genre-seeds',
                                      'devices', 'blacklist', 'presets', 'playlists', 'tuning'],
                             help='print a list of genre seeds, or your top artists, tracks, or '
                                  'genres, where TYPE=[artists|tracks|genres|genre-seeds|devices|'
                                  'blacklist|presets|playlists|tuning]')
    print_group.add_argument('--version', action='version', version=f'%(prog)s v{__version__}')
    print_group.add_argument('--track-features', metavar='[URI | current]', nargs=1, type=str,
                             help='print track features of URI or currently playing track')

    # Misc
    misc_group = arg_parser.add_argument_group(title='Misc')
    misc_group.add_argument('--auth', action='store_true',
                            help='force re-authorization of OAuth token')

    return arg_parser


def check_scope_permissions():
    oauth = conf.get_oauth()
    if len(oauth.keys()) != 6:
        logger.error('missing oauth config, authorizing...')
        authorize()
        sys.exit(0)
    scopes = oauth.get('scope')
    if any(scope not in scopes for scope in sp_oauth.scopes):
        logger.error('new functionality that needs new permissions has been added, please '
                     'navigate to your browser and authorize again')
        authorize()
        sys.exit(0)


def authorize(port=PORTS[0]):
    """
    Open redirect URL in browser, and host http server on localhost.
    Function index() will be routed on said http server.
    """
    logger.verbose('hosting localhost server')
    sp_oauth.PORT = port
    webbrowser.open(f'{sp_oauth.redirect}:{port}')
    try:
        logger.info(f'running authorization on {sp_oauth.redirect}:{port}')
        run(host='', port=port, quiet=True)
    except OSError as ex:
        if ex.errno == 98:
            next_port = PORTS.index(port) + 1
            if next_port > len(PORTS) - 1:
                logger.error(f'tried all ports ({",".join(str(x) for x in PORTS)}), all are in use')
                logger.error(f'please ensure one of them is available and try again')
                sys.exit(1)
            logger.warning(f'port {port} is already in use, trying {PORTS[next_port]}')
            authorize(port=PORTS[next_port])


@route('/')
def index() -> str:
    """
    This function is routed to http server hosted on localhost.
    Retrieve code from redirect URL once authorization is complete and retrieve token from API.
    :return: success confirmation if access token is found
    :return: link to authorization if access token wasn't found
    """
    access_token = ""
    code = sp_oauth.parse_response_code(request.url)
    if code:
        logger.verbose('code found, retrieving oauth token')
        logger.debug(f'code: {code}')
        access_token = sp_oauth.retrieve_access_token(code)['access_token']
    if access_token:
        logger.verbose('successfully retrieved oauth token')
        logger.debug(f'token: {access_token}')
        return "<span>Successfully retrieved OAuth token. You may close this tab and start " \
               "using Spotirec.</span>"
    else:
        logger.verbose('code not found, requesting permissions')
        return f"<a href='{sp_oauth.get_authorize_url()}'>Login to Spotify</a>"


def get_token() -> str:
    """
    Retrieve access token from OAuth handler. Try to authorize and exit if credentials don't exist.
    :return: access token, if present
    """
    logger.verbose('getting token')
    creds = sp_oauth.get_credentials()
    if creds:
        logger.verbose('token found')
        return creds.get('access_token')
    else:
        logger.verbose('token not found, authorising')
        authorize()
        sys.exit(0)


def check_if_show_or_episode(uri: str) -> bool:
    """
    Checks whether URI is a show or episode
    :param uri:
    """
    uri_type = uri.split(":")[1] if ':' in uri else uri
    uri_name = uri if ':' in uri else 'currently playing'
    if re.match(SHOW_EPI_RE, uri) or uri == 'episode' or uri == 'show':
        logger.warning(f'{uri_type}s can not exist in a playlists ({uri_name})')
        return True
    return False


def format_identifier(identifier: str) -> str:
    return identifier.translate({ord(c): '_' for c in '½§"¾¤£€±`^*µ!@#$%^&*()[]{};:,./<>?\\|`~=+ '})


def get_user_top_genres() -> dict:
    """
    Extract genres from user's top 50 artists and map them to their amount of occurrences
    :return: dict of genres and their count of occurrences
    """
    logger.verbose('getting top genres')
    data = api.get_top_list('artists', 50, headers)
    logger.debug(f'got {len(data["items"])} artists for genres')
    genre_seeds = api.get_genre_seeds(headers)
    # Get all genres of each artist
    artist_genres = [genre.replace(' ', '-') for x in data['items']
                     for genre in x['genres'] if genre.replace(' ', '-') in genre_seeds['genres']]
    # Map each genre to its count
    genres = {genre: artist_genres.count(genre) for genre in artist_genres}
    logger.debug(f'extracted {len(genres)} genre seeds from artists')
    logger.debug(f'genre seeds: {genres}')
    return genres


def add_top_genres_seed(seed_count: int):
    """
    Add top 5 genres to recommendation object seed info.
    """
    logger.verbose(f'adding top {seed_count} genres to seeds')
    sort = sorted(get_user_top_genres().items(), key=lambda kv: kv[1], reverse=True)
    if seed_count > len(sort):
        seed_count = len(sort)
    parse_seed_info([sort[x][0] for x in range(0, seed_count)])


def print_choices(data=None, prompt=True, sort=False) -> str:
    """
    Used for custom seed creation. All valid choices are printed to terminal and user is prompted
    to select. If the seed type is genres, seeds are simply added to the recommendations object.
    :param data: valid choices as a list of names
    :param prompt: whether or not to prompt user for input
    :param sort: whether or not printed data should be sorted
    :return: user input, if seed type is artists or tracks
    """

    def _index(i: str, r: list) -> int:
        """
        Calculates absolute index of item in matrix with respect to rows
        :param i: item
        :param r: row
        :return: index
        """
        return r.index(i) + (matrix.index(r) * 3)

    def _strip(i: str) -> str:
        """
        Ensures string is a certain length
        :param i: item
        :return: formatted string
        """
        return i if len(i) < 34 else f'{i[0:34]}..'

    def _jump(i: str, r: list) -> str:
        """
        Create a whitespace jump if needed, based on item index
        No jump if item is the last element in its row
        :param i: item
        :param r: row
        :return: whitespace jump
        """
        ind = _index(i, r)
        return '' if r.index(i) == len(r) - 1 else ' ' * (40 - len(_strip(i)) - len(str(ind)))

    if sort:
        sorted_data = sorted(data.items(), key=lambda kv: kv[1], reverse=True)
        data = [sorted_data[x][0] for x in range(0, len(sorted_data))]
    # Convert data to matrix
    matrix = [data[x:x + 3] for x in range(0, len(data), 3)]
    # Format output lines, three seeds per line
    line = '\n'.join([''.join(f'{_index(x, row)}: {_strip(x)}{_jump(x, row)}'
                              for x in row) for row in matrix])
    print(line.strip('\n'))
    if prompt:

        def prompt_selection() -> str:
            try:
                inp = input('Enter integer identifiers for 1-5 whitespace separated selections'
                            ' that you wish to include [default: top 5]:\n') or '0 1 2 3 4'
            except KeyboardInterrupt:
                sys.exit(0)
            if not inp:
                logger.error(f'input \"{inp}\" is malformed.')
                logger.info('please ensure that your input valid, i.e. n0 [ ... n5 ], where '
                            'n is a valid index.')
                return prompt_selection()
            return inp

        input_string = prompt_selection()

        # If seed type is genres, simply parse the seed, else return the input for
        # further processing
        if 'genres' in rec.seed_type:
            parse_seed_info([data[int(x)] for x in input_string.strip(' ').split(' ')])
        else:
            return input_string.strip(' ')


def print_artists_or_tracks(data: json, prompt=True):
    """
    Construct dict only containing artist or track names and IDs and prompt for selection.
    Seeds are added to recommendation object. If prompt is False, choices will simply be printed.
    :param data: valid choices as json object
    :param prompt: whether or not to prompt for input
    """
    choices = {}
    for x in data['items']:
        choices[x['name']] = x['id']
    selection = print_choices(data=list(choices.keys()), prompt=prompt)
    if prompt:
        parse_seed_info([data['items'][int(x)] for x in selection.split(' ')])


def check_if_valid_genre(genre: str) -> bool:
    """
    Checks if input genre is in user's top genres or available genre seeds.
    :param genre: user input genre
    :return: True if genre exists, False if not
    """
    if any(g == genre for g in api.get_genre_seeds(headers)['genres']):
        return True
    logger.debug(f'genre {genre} is invalid')
    return False


def check_tune_validity(tune: str):
    """
    Check validity of tune input - exit program if not valid
    :param tune: tune input as string
    """
    logger.verbose('checking tune validity')
    if not re.match(TUNE_RE, tune):
        logger.error(f'tune {tune} does not match the proper format')
        logger.verbose(tune)
        logger.log_file(crash=True)
        sys.exit(1)
    prefix = tune.split('_', 1)[0]
    key = tune.split('=')[0].split('_', 1)[1]
    value = tune.split('=')[1]
    logger.debug(f'prefix: {prefix}, attribute: {key}, value: {value}')
    # Check prefix validity
    if prefix not in TUNE_PREFIX:
        logger.error(f'tune prefix \"{tune.split("_", 1)[0]}\" is malformed')
        logger.verbose(TUNE_PREFIX)
        logger.log_file(crash=True)
        sys.exit(1)
    # Check attribute validity
    if key not in list(TUNE_ATTR['int'].keys()) + list(TUNE_ATTR['float'].keys()):
        logger.error(f'tune attribute \"{tune.split("=")[0].split("_", 1)[1]}\" is malformed')
        logger.verbose(list(TUNE_ATTR['int'].keys()) + list(TUNE_ATTR['float'].keys()))
        logger.log_file(crash=True)
        sys.exit(1)
    # Try parsing value to number
    try:
        # Try parsing value to number
        value = int(float(value)) if key in TUNE_ATTR['int'].keys() else float(value)
        value_type = 'int' if key in TUNE_ATTR['int'].keys() else 'float'
        # Ensure value is within accepted range
        if not TUNE_ATTR[value_type][key]['max'] >= value >= TUNE_ATTR[value_type][key]['min']:
            logger.error(f'value {value} for attribute {key} is outside the accepted range (min: '
                         f'{TUNE_ATTR[value_type][key]["min"]}, max: '
                         f'{TUNE_ATTR[value_type][key]["max"]})')
            logger.log_file(crash=True)
            sys.exit(1)
        # Warn if value is outside recommended range
        if not TUNE_ATTR[value_type][key]['rec_max'] >= value >= \
                TUNE_ATTR[value_type][key]['rec_min']:
            logger.warning(f'value {value} for attribute {key} is outside the recommended range '
                           f'(min: {TUNE_ATTR[value_type][key]["rec_min"]}, max: '
                           f'{TUNE_ATTR[value_type][key]["rec_max"]}), recommendations may be '
                           f'scarce')
        logger.debug(f'tune attribute {key} with prefix {prefix} and value {value} is valid')
    except ValueError:
        logger.error(f'tune value {value} does not match attribute {key} data type requirements')
        logger.log_file(crash=True)
        sys.exit(1)


def filter_list_duplicates(li: list) -> list:
    """
    Removes duplicates from a list
    :param li: original list of strings or dicts
    :return: list without duplicates
    """
    # extract uris if elements are dicts
    new_li = [x['uri'] if type(x) is dict else x for x in li]
    # filter duplicates
    new_li = sorted(list(set(new_li)), key=new_li.index)
    for x in li:
        if type(x) is dict and x['uri'] in new_li:
            new_li[new_li.index(x['uri'])] = x
        elif x in new_li:
            new_li[new_li.index(x)] = x
    return new_li


def parse_seed_info(seeds):
    """
    Adds seed data to recommendation object
    :param seeds: seed data as a string or a list
    """
    logger.verbose('processing seeds')
    seeds = filter_list_duplicates(seeds.split() if type(seeds) is str else seeds)
    if len(seeds) > 5:
        logger.error('please enter at most 5 seeds')
        logger.log_file(crash=True)
        sys.exit(1)
    # Parse each seed in input and add to seed string depending on type
    for x in seeds:
        logger.debug(f'seed: {x}')
        if rec.seed_type == 'genres':
            rec.add_seed_info(data_string=x)
        elif rec.seed_type == 'custom':
            if check_if_valid_genre(x):
                rec.add_seed_info(data_string=x)
            elif re.match(URI_RE, x):
                rec.add_seed_info(data_dict=api.request_data(x, f'{x.split(":")[1]}s', headers))
            else:
                logger.warning(f'input \"{x}\" does not match a genre or a valid URI syntax, '
                               f'skipping...')
        else:
            rec.add_seed_info(data_dict=x)


def set_blacklist_current(entries: list) -> list:
    if 'current-track' in entries:
        logger.verbose('getting current track')
        entries.remove('current-track')
        entries.append(api.get_current_track(headers))
    elif 'current-artists' in entries:
        logger.verbose('getting current artists')
        entries.remove('current-artists')
        entries += [x for x in api.get_current_artists(headers)]
    else:
        logger.warning('your argument for current does not match proper syntax, try '
                       '"current-track" or "current-artists"')
    return entries


def add_to_blacklist(entries: list):
    """
    Add input uris to blacklist and exit
    :param entries: list of input uris
    """
    logger.verbose('adding blacklist entries')
    for x in entries:
        if check_if_show_or_episode(x):
            continue
        logger.debug(f'entry: {x}')
        if not conf.check_item_in_blacklist(x):
            uri_data = api.request_data(x, f'{x.split(":")[1]}s', headers)
            conf.add_to_blacklist(uri_data, x)


def remove_from_blacklist(entries: list):
    """
    Remove track(s) and/or artist(s) from blacklist.
    :param entries: list of uris
    """
    logger.verbose('removing blacklist entries')
    for x in entries:
        if check_if_show_or_episode(x):
            continue
        logger.debug(f'entry: {x}')
        conf.remove_from_blacklist(x)


def print_blacklist():
    """
    Format and print blacklist entries
    """
    blacklist = conf.get_blacklist()
    print('\033[1m' + 'Tracks' + '\033[0m')
    for x in blacklist.get('tracks').values():
        print(f'{x["name"]} by {", ".join(x["artists"])} - {x["uri"]}')
    print('\n' + '\033[1m' + 'Artists' + '\033[0m')
    for x in blacklist.get('artists').values():
        print(f'{x["name"]} - {x["uri"]}')


def generate_img(tracks: list) -> Image:
    """
    Generate personalized cover image for a playlist. Track uris are hashed. The hash is both mapped
    to an image and converted to a color.
    :param tracks: list of track uris
    :return: a 320x320 image generated from playlist hash
    """
    logger.verbose('generating image')
    # Hash tracks to a playlist-unique string
    track_hash = hashlib.sha256(''.join(str(x) for x in tracks).encode('utf-8')).hexdigest()
    logger.debug(f'hash: {track_hash}')
    # Use the first six chars of the hash to generate a color
    # The hex value of three pairs of chars are converted to integers, yielding a list on the
    # form [r, g, b]
    color = [int(track_hash[i:i + 2], 16) for i in (0, 2, 4)]
    logger.debug(f'color: {color}')
    # Create an image object the size of the squared square root of the hash string - always 8x8
    img = Image.new('RGB', (int(math.sqrt(len(track_hash))), int(math.sqrt(len(track_hash)))))
    logger.debug(f'image: {img}')
    # Iterate over hash string and assign to pixel map each digit to the generated color,
    # each letter to light gray
    pixel_map = [color if re.match(r'[0-9]', x) else [200, 200, 200] for x in track_hash]
    # Add the pixel map to the image object and return as a size suited for the Spotify API
    logger.debug(f'pixel map: {pixel_map}')
    img.putdata([tuple(x) for x in pixel_map])
    return img.resize((320, 320), Image.AFFINE)


def add_image_to_playlist(tracks: list):
    """
    base64 encode image data and upload to playlist.
    :param tracks: list of track uris
    """
    logger.info('Generating and uploading playlist cover image')
    img_headers = {'Content-Type': 'image/jpeg',
                   'Authorization': f'Bearer {get_token()}'}
    img_buffer = BytesIO()
    generate_img(tracks).save(img_buffer, format='JPEG')
    img_str = base64.b64encode(img_buffer.getvalue())
    logger.verbose('uploading image')
    api.upload_image(rec.playlist_id, img_str, img_headers)


def save_preset(name: str):
    """
    Save recommendation object as preset
    :param name: name of preset
    """
    name = format_identifier(name)
    logger.verbose('saving preset')
    preset = {'limit': rec.limit_original,
              'based_on': rec.based_on,
              'seed': rec.seed,
              'seed_type': rec.seed_type,
              'seed_info': rec.seed_info,
              'rec_params': rec.rec_params,
              'auto_play': rec.auto_play,
              'playback_device': rec.playback_device}
    logger.debug(f'preset: {preset}')
    conf.save_preset(preset, name)


def load_preset(name: str) -> recommendation.Recommendation:
    """
    Load preset recommendation object from config
    :param name: name of preset
    :return: recommendation object with settings from preset
    """
    logger.info(f'using preset \"{name}\"')
    presets = conf.get_presets()
    try:
        logger.verbose('getting preset')
        contents = presets[name]
    except KeyError:
        logger.error(f'could not find preset \"{name}\", check spelling and try again')
        logger.log_file(crash=True)
        sys.exit(1)
    preset = recommendation.Recommendation(preset=contents)
    logger.debug(f'preset: {preset}')
    return preset


def remove_presets(presets: list):
    """
    Remove preset(s) from user config
    :param presets: list of devices
    """
    logger.verbose('removing presets')
    for x in presets:
        logger.debug(f'preset: {x}')
        conf.remove_preset(x)


def print_presets():
    """
    Format and print preset entries
    """

    def _bool(b: bool) -> str:
        return 'Yes' if b else 'No'

    presets = conf.get_presets()
    print('\033[1m' + f'Name{" " * 16}Type{" " * 21}Auto play{" " * 6}Params'
                      f'{" " * 44}Seeds' + '\033[0m')
    for x in presets.items():
        params = ",".join(f"{y[0]}={y[1]}" if "seed" not in y[0] else "" for y in
                          x[1]["rec_params"].items()).strip(',')
        print(
            f'{x[0]}{" " * (20 - len(x[0]))}{x[1]["based_on"]}'
            f'{" " * (25 - len(x[1]["based_on"]))}{_bool(x[1]["auto_play"])}'
            f'{" " * (15 - len(_bool(x[1]["auto_play"])))}{params}{" " * (50 - len(params))}'
            f'{",".join(str(y["name"]) for y in x[1]["seed_info"].values())}')


def get_device(device_name: str) -> dict:
    """
    Get device from config
    :param device_name: name of playback device
    """
    devices = conf.get_devices()
    try:
        return devices[device_name]
    except KeyError:
        logger.error(f'device {device_name} does not exist in config')
        logger.log_file(crash=True)
        sys.exit(1)


def save_device():
    """
    Prompt user for an identifier for device and save to config
    """

    def prompt_device_index() -> int:
        try:
            ind = input('Select a device by index[0]: ') or 0
        except KeyboardInterrupt:
            sys.exit(0)
        try:
            assert devices[int(ind)] is not None
            return int(ind)
        except (ValueError, AssertionError, IndexError):
            logger.error(f'input \"{ind}\" is malformed.')
            logger.info('please ensure that your input is an integer and is a valid index.')
            return prompt_device_index()

    def prompt_name() -> str:
        try:
            inp = input('Enter an identifier for your device: ')
        except KeyboardInterrupt:
            sys.exit(0)
        if inp:
            return format_identifier(inp)
        else:
            logger.error(f'device identifier \"{inp}\" is malformed.')
            logger.info('please ensure that the identifier contains at least one character')
            return prompt_name()

    # Get available devices from API and print
    devices = api.get_available_devices(headers)['devices']
    print('Available devices:')
    print('\033[1m' + f'Name{" " * 19}Type' + '\033[0m')
    for x in devices:
        print(f'{devices.index(x)}. {x["name"]}{" " * (20 - len(x["name"]))}{x["type"]}')
    logger.info('please note that a player needs to be active to be shown in the above list, i.e. '
                'if you want to save your phone as a device, the app needs to be launched on '
                'your phone')
    # Prompt device selection and identifier, and save to config
    device = devices[prompt_device_index()]
    device_dict = {'id': device['id'], 'name': device['name'], 'type': device['type']}
    name = prompt_name()
    logger.verbose('saving device')
    logger.debug(f'device: {device_dict}')
    conf.save_device(device_dict, name)


def remove_devices(devices: list):
    """
    Remove device(s) from user config
    :param devices: list of device(s)
    """
    logger.verbose('removing devices')
    for x in devices:
        logger.debug(f'device: {x}')
        conf.remove_device(x)


def print_saved_devices():
    """
    Print all saved devices
    """
    devices = conf.get_devices()
    print('\033[1m' + f'ID{" " * 18}Name{" " * 16}Type' + '\033[0m')
    for x in devices.items():
        print(f'{x[0]}{" " * (20 - len(x[0]))}{x[1]["name"]}'
              f'{" " * (20 - len(x[1]["name"]))}{x[1]["type"]}')


def print_playlists():
    """
    Print all saved playlists
    """
    playlists = conf.get_playlists()
    print('\033[1m' + f'ID{" " * 18}Name{" " * 26}URI' + '\033[0m')
    for x in playlists.items():
        print(f'{x[0]}{" " * (20 - len(x[0]))}{x[1]["name"]}'
              f'{" " * (30 - len(x[1]["name"]))}{x[1]["uri"]}')


def save_playlist():
    """
    Prompt user for an identifier and URI for playlist and save to config
    """

    def input_id() -> str:
        try:
            iden = input('Please input an identifier for your playlist: ')
        except KeyboardInterrupt:
            sys.exit(0)
        if iden:
            return format_identifier(iden)
        else:
            logger.error(f'playlist identifier \"{iden}\" is malformed.')
            logger.info('please ensure that the identifier contains at least one character')
            return input_id()

    def input_uri() -> str:
        try:
            uri = input('Please input the URI for your playlist: ')
        except KeyboardInterrupt:
            sys.exit(0)
        try:
            assert uri
            assert re.match(PLAYLIST_URI_RE, uri)
            return uri
        except AssertionError:
            logger.error(f'playlist uri \"{uri}\" is malformed.')
            return input_uri()

    # Prompt device identifier and URI, and save to config
    playlist_id = input_id()
    playlist_uri = input_uri()
    playlist = {'name': api.get_playlist(headers, playlist_uri.split(':')[2])["name"],
                'uri': playlist_uri}
    logger.verbose(f'saving playlist')
    logger.debug(f'playlist: {playlist}')
    conf.save_playlist(playlist, playlist_id)


def remove_playlists(playlists: list):
    """
    Remove playlist(s) from user config
    :param playlists: list of playlist(s)
    """
    logger.verbose('removing playlists')
    for x in playlists:
        logger.debug(f'playlist: {x}')
        conf.remove_playlist(x)


def add_current_track(playlist: str):
    """
    Add currently playing track to input playlist
    :param playlist: identifier or URI for playlist
    """
    # Check whether input is URI or identifier
    if re.match(PLAYLIST_URI_RE, playlist):
        playlist_id = playlist.split(':')[2]
    else:
        playlists = conf.get_playlists()
        try:
            playlist_id = playlists[playlist]['uri'].split(':')[2]
        except KeyError:
            logger.error(f'playlist {playlist} does not exist in config')
            logger.log_file(crash=True)
            sys.exit(1)
    logger.info(f'adding currently playing track to playlist')

    current_track = api.get_current_track(headers)
    if check_if_show_or_episode(current_track):
        return
    playlist_tracks = [x['track']['uri']
                       for x in api.get_playlist(headers, playlist_id)['tracks']['items']]
    if current_track in playlist_tracks:
        logger.warning(f'track {current_track} already exists in playlist, skipping...')
        return
    api.add_to_playlist([current_track], playlist_id, headers)


def remove_current_track(playlist: str):
    """
    Remove currently playing track from input playlist
    :param playlist: identifier or URI for playlist
    """
    # Check whether input is URI or identifier
    if re.match(PLAYLIST_URI_RE, playlist):
        playlist_id = playlist.split(':')[2]
    else:
        playlists = conf.get_playlists()
        try:
            playlist_id = playlists[playlist]['uri'].split(':')[2]
        except KeyError:
            logger.error(f'playlist {playlist} does not exist in config')
            logger.log_file(crash=True)
            sys.exit(1)
    logger.info(f'removing currently playing track to playlist')
    current_track = api.get_current_track(headers)
    if check_if_show_or_episode(current_track):
        return
    playlist_tracks = [x['track']['uri']
                       for x in api.get_playlist(headers, playlist_id)['tracks']['items']]
    if current_track not in playlist_tracks:
        logger.warning(f'track {current_track} doesnt exist in playlist, skipping...')
        return
    api.remove_from_playlist([current_track], playlist_id, headers)


def print_track_features(uri: str):
    """
    Prints various information about a track
    :param uri: URI of track
    """
    if not re.match(TRACK_URI_RE, uri):
        logger.error(f'{uri} is not a valid track URI')
        logger.log_file(crash=True)
        sys.exit(1)
    audio_features = api.get_audio_features(uri.split(':')[2], headers)
    track_info = api.request_data(uri, 'tracks', headers)
    print('\t' + '\033[1m' + f'{track_info["name"]} - '
                             f'{", ".join(x["name"] for x in track_info["artists"])}' + '\033[0m')
    print(f'Track URI{" " * 21}{track_info["uri"]}')
    print(f'Artist URI(s){" " * 17}'
          f'{", ".join(x["name"] + ": " + x["uri"] for x in track_info["artists"])}')
    print(f'Album URI{" " * 21}{track_info["album"]["uri"]}')
    print(f'Release date{" " * 18}{track_info["album"]["release_date"]}')
    print(f'Duration{" " * 22}{audio_features["duration_ms"]}ms '
          f'({millis_to_stamp(audio_features["duration_ms"])})')
    print(f'Key{" " * 27}{audio_features["key"]}')
    print(f'Mode{" " * 26}{audio_features["mode"]} '
          f'({"minor" if audio_features["mode"] == 0 else "major"})')
    print(f'Time signature{" " * 16}{audio_features["time_signature"]}')
    print(f'Popularity{" " * 20}{track_info["popularity"]}')
    print(f'Acousticness{" " * 18}{audio_features["acousticness"]}')
    print(f'Danceability{" " * 18}{audio_features["danceability"]}')
    print(f'Energy{" " * 24}{audio_features["energy"]}')
    print(f'Instrumentalness{" " * 14}{audio_features["instrumentalness"]}')
    print(f'Liveness{" " * 22}{audio_features["liveness"]}')
    print(f'Loudness{" " * 22}{audio_features["loudness"]} dB')
    print(f'Speechiness{" " * 19}{audio_features["speechiness"]}')
    print(f'Valence{" " * 23}{audio_features["valence"]}')
    print(f'Tempo{" " * 25}{audio_features["tempo"]} bpm')


def millis_to_stamp(x: int):
    """
    Convert milliseconds to a timestamp on the form "{hours}h {minutes}m {seconds}s".
    Hours and minutes are only included if they are present.
    :param x: milliseconds
    :return: formatted timestamp
    """
    sec_total = int(x / 1000)
    sec = sec_total % 60
    mins_total = math.floor(sec_total / 60)
    mins = mins_total % 60
    hours = int(mins_total / 60)
    return f'{f"{hours}h " if hours != 0 else ""}{f"{mins}m " if mins != 0 else ""}{sec}s'


def transfer_playback(device_id):
    """
    Transfers playback to different device
    :param device_id: device to transfer playback to
    """
    try:
        device = conf.get_devices()[device_id]['id']
    except KeyError:
        logger.error(f'device {device_id} does not exist in config')
        logger.log_file(crash=True)
        sys.exit(1)
    logger.info(f'transferring playback to device {device_id}')
    logger.debug(f'device: {device}')
    api.transfer_playback(device, headers)


def filter_recommendations(data: json) -> list:
    """
    Filter blacklisted artists and tracks from recommendations.
    :param data: recommendations as json object.
    :return: list of eligible track URIs
    """
    logger.verbose('filtering tracks')
    valid_tracks = []
    blacklist = conf.get_blacklist()
    for x in data['tracks']:
        # If the URI of the current track is blacklisted or there is an intersection between
        # the set of blacklisted artists and the set of artists of the current track,
        # then skip - otherwise add to valid tracks
        if any(x['uri'] == s for s in blacklist['tracks'].keys()) or len(
                set(blacklist['artists'].keys()) & set(y['uri'] for y in x['artists'])) > 0:
            continue
        else:
            valid_tracks.append(x['uri'])
    logger.debug(f'tracks filtered: {len(data["tracks"]) - len(valid_tracks)}')
    logger.debug(f'tracks left after filter: {len(valid_tracks)}')
    return valid_tracks


def print_tuning_options():
    """
    Prints available tuning options
    """
    try:
        with open(TUNING_FILE, 'r') as file:
            tuning_opts = file.readlines()
    except FileNotFoundError:
        logger.error('could not find tuning options file')
        logger.log_file(crash=True)
        sys.exit(1)
    if len(tuning_opts) == 0:
        logger.error('tuning options file is empty')
        logger.log_file(crash=True)
        sys.exit(1)
    for x in tuning_opts:
        if tuning_opts.index(x) == 0:
            print('\033[1m' + x.strip('\n') + '\033[0m')
        else:
            print(x.strip('\n'))
    print('note that recommendations may be scarce outside the recommended ranges. If the '
          'recommended range is not available, they may only be scarce at extreme values.')


def recommend():
    """
    Main function for recommendations. Retrieves recommendations and tops up list if any tracks
    were removed by the blacklist filter. Playlist is created and tracks are added. Seed info
    is printed to terminal.
    """
    logger.info('getting recommendations')
    # Create seed from user preferences
    rec.create_seed()
    # Save as preset if requested
    if args.save_preset:
        save_preset(args.save_preset[0])
    # Filter blacklisted artists and tracks from recommendations
    tracks = filter_recommendations(api.get_recommendations(rec.rec_params, headers))
    # If no tracks are left, notify an error and exit
    if len(tracks) == 0:
        logger.error('received zero tracks with your options - adjust and try again')
        logger.log_file(crash=True)
        sys.exit(1)
    if len(tracks) <= rec.limit_original / 2:
        logger.warning(f'only received {len(tracks)} different recommendations, you may receive '
                       f'duplicates of these (this might take a few seconds)')
    # Filter recommendations until length of track list matches limit preference
    while len(tracks) < rec.limit_original:
        rec.update_limit(rec.limit_original - len(tracks))
        tracks += filter_recommendations(api.get_recommendations(rec.rec_params, headers))

    def create_new_playlist():
        rec.playlist_id = api.create_playlist(rec.playlist_name, rec.playlist_description(),
                                              headers, cache_id=True)
        api.add_to_playlist(tracks, rec.playlist_id, headers=headers)

    # Create playlist and add tracks
    if args.preserve:
        logger.info('preserving playlist and creating new default')
        create_new_playlist()
    else:
        try:
            rec.playlist_id = conf.get_playlists()['spotirec-default']['uri'].split(':')[2]
            assert api.check_if_playlist_exists(rec.playlist_id, headers) is True
            api.replace_playlist_tracks(rec.playlist_id, tracks, headers=headers)
            api.update_playlist_details(rec.playlist_name, rec.playlist_description(),
                                        rec.playlist_id, headers=headers)
        except (KeyError, AssertionError):
            logger.info('playlist has either been deleted, or made private, creating new '
                        'default...')
            create_new_playlist()
    # Generate and upload dank-ass image
    add_image_to_playlist(tracks)
    # Print seed selection
    rec.print_selection()
    # Start playing on input device if auto-play is present
    if rec.auto_play:
        api.play(rec.playback_device['id'], f'spotify:playlist:{rec.playlist_id}', headers)


def parse():
    """
    Parse arguments
    """
    logger.verbose('parsing args')
    if args.auth:
        authorize()
        sys.exit(0)
    if args.blacklist_add:
        if any('current' in x for x in args.blacklist_add):
            args.blacklist_add = set_blacklist_current(args.blacklist_add)
        add_to_blacklist(args.blacklist_add)
        sys.exit(0)
    if args.blacklist_remove:
        if any('current' in x for x in args.blacklist_remove):
            args.blacklist_remove = set_blacklist_current(args.blacklist_remove)
        remove_from_blacklist(args.blacklist_remove)
        sys.exit(0)

    if args.transfer_playback:
        transfer_playback(args.transfer_playback[0])
        sys.exit(0)

    if args.s:
        logger.info('liking current track')
        api.like_track(headers, check_if_show_or_episode)
        sys.exit(0)
    elif args.sr:
        logger.info('unliking current track')
        api.unlike_track(headers, check_if_show_or_episode)
        sys.exit(0)
    if args.save_playlist:
        save_playlist()
        sys.exit(0)
    if args.remove_playlists:
        remove_playlists(args.remove_playlists)
        sys.exit(0)
    if args.save_device:
        save_device()
        sys.exit(0)
    if args.remove_devices:
        remove_devices(args.remove_devices)
        sys.exit(0)
    if args.remove_presets:
        remove_presets(args.remove_presets)
        sys.exit(0)
    if args.add_to:
        add_current_track(args.add_to[0])
        sys.exit(0)
    elif args.remove_from:
        remove_current_track(args.remove_from[0])
        sys.exit(0)

    if args.print:
        if 'artists' in args.print:
            print('\033[4m\033[1m' + 'Top artists' + '\033[0m')
            print_artists_or_tracks(data=api.get_top_list('artists', 50, headers), prompt=False)
        if 'tracks' in args.print:
            print('\033[4m\033[1m' + 'Top tracks' + '\033[0m')
            print_artists_or_tracks(data=api.get_top_list('tracks', 50, headers), prompt=False)
        if 'genres' in args.print:
            print('\033[4m\033[1m' + 'Top genres' + '\033[0m')
            print_choices(data=get_user_top_genres(), sort=True, prompt=False)
        if 'genre-seeds' in args.print:
            print('\033[4m\033[1m' + 'Genre seeds' + '\033[0m')
            print_choices(data=api.get_genre_seeds(headers)['genres'], prompt=False)
        if 'blacklist' in args.print:
            print('\033[4m\033[1m' + 'Blacklist' + '\033[0m')
            print_blacklist()
        if 'devices' in args.print:
            print('\033[4m\033[1m' + 'Devices' + '\033[0m')
            print_saved_devices()
        if 'presets' in args.print:
            print('\033[4m\033[1m' + 'Presets' + '\033[0m')
            print_presets()
        if 'playlists' in args.print:
            print('\033[4m\033[1m' + 'Playlists' + '\033[0m')
            print_playlists()
        if 'tuning' in args.print:
            print('\033[4m\033[1m' + 'Tuning options' + '\033[0m')
            print_tuning_options()
        sys.exit(0)
    if args.track_features:
        print_track_features(api.get_current_track(headers) if
                             args.track_features[0] == 'current' else args.track_features[0])
        sys.exit(0)

    if args.play:
        rec.auto_play = True
        rec.playback_device = get_device(args.play[0])

    if args.a:
        logger.info(f'basing recommendations off your top {args.a} artist(s)')
        rec.based_on = 'top artists'
        rec.seed_type = 'artists'
        parse_seed_info([x for x in api.get_top_list('artists', args.a, headers)['items']])
    elif args.t:
        logger.info(f'basing recommendations off your top {args.t} track(s)')
        rec.based_on = 'top tracks'
        rec.seed_type = 'tracks'
        parse_seed_info([x for x in api.get_top_list('tracks', args.t, headers)['items']])
    elif args.st:
        logger.info(f'basing recommendations off your top {args.st} saved track(s)')
        rec.based_on = 'recent saved tracks'
        rec.seed_type = 'tracks'
        parse_seed_info([x['track'] for x in api.get_saved_tracks(headers, limit=args.st)['items']])
    elif args.gcs:
        rec.based_on = 'custom seed genres'
        print_choices(data=api.get_genre_seeds(headers)['genres'])
    elif args.ac:
        rec.based_on = 'custom artists'
        rec.seed_type = 'artists'
        print_artists_or_tracks(api.get_top_list('artists', 50, headers))
    elif args.tc:
        rec.based_on = 'custom tracks'
        rec.seed_type = 'tracks'
        print_artists_or_tracks(api.get_top_list('tracks', 50, headers))
    elif args.stc:
        rec.based_on = 'custom saved tracks'
        rec.seed_type = 'tracks'
        print_artists_or_tracks({'items': [x['track']
                                           for x in api.get_saved_tracks(headers)['items']]})
    elif args.gc:
        rec.based_on = 'custom top genres'
        print_choices(data=get_user_top_genres(), sort=True)
    elif args.c:
        rec.based_on = 'custom mix'
        rec.seed_type = 'custom'
        print_choices(data=get_user_top_genres(), prompt=False, sort=True)
        try:
            user_input = input('Enter a combination of 1-5 whitespace separated genre names, '
                               'track uris, and artist uris. \nGenres with several words should '
                               'be connected with dashes, e.g.; vapor-death-pop.\n')
        except KeyboardInterrupt:
            sys.exit(0)
        if not user_input:
            logger.error('please enter 1-5 seeds')
            logger.log_file(crash=True)
            sys.exit(1)
        seeds = [x for x in user_input.strip(' ').split() if not check_if_show_or_episode(x)]
        parse_seed_info(seeds)
    else:
        logger.info(f'basing recommendations off your top {args.n} genres')
        add_top_genres_seed(args.n)

    if args.l:
        rec.update_limit(args.l[0], init=True)
    logger.info(f'the playlist will contain {rec.limit} tracks')

    if args.tune:
        for x in args.tune:
            check_tune_validity(x)
            rec.rec_params[x.split('=')[0]] = x.split('=')[1]


def init():
    global rec, headers

    # Logging handler
    if args.verbose:
        logger.set_level(log.VERBOSE)
    elif args.quiet:
        logger.set_level(log.WARNING)
    elif args.debug:
        logger.set_level(log.DEBUG)

    if args.suppress_warnings:
        logger.suppress_warnings(True)

    logger.verbose('initialising')
    logger.debug(f'log level: {logger.LEVEL} ({log.LOG_LEVELS[logger.LEVEL]})')
    logger.debug(f'suppress warnings: {logger.SUPPRESS_WARNINGS}')

    # Config handler
    conf.set_logger(logger)

    # API handler
    api.set_logger(logger)
    api.set_conf(conf)

    # OAuth handler
    sp_oauth.set_logger(logger)
    sp_oauth.set_conf(conf)
    sp_oauth.set_api(api)

    check_scope_permissions()

    headers = {'Content-Type': 'application/json',
               'Authorization': f'Bearer {get_token()}'}

    # Recommendation object
    if args.load_preset:
        rec = load_preset(args.load_preset[0])
        rec.set_logger(logger)
    else:
        rec = recommendation.Recommendation()
        rec.set_logger(logger)
        parse()

    logger.debug(f'args: {args}')

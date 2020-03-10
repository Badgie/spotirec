#!/usr/bin/env python
import webbrowser
import json
import argparse
import shlex
import os
import hashlib
import re
import math
import base64
import oauth2
import recommendation
import api
import conf
import sys
from io import BytesIO
from PIL import Image
from bottle import route, run, request
from pathlib import Path


VERSION = '1.2'

PORT = 8080
CONFIG_PATH = f'{Path.home()}/.config/spotirec'

TUNE_PREFIX = ['max', 'min', 'target']
TUNE_ATTR = {'int': {'duration_ms': {'min': 0, 'max': sys.maxsize * 2 + 1, 'rec_min': 0, 'rec_max': 3600000},
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

# OAuth handler
sp_oauth = oauth2.SpotifyOAuth()

# Argument parser
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, prog='spotirec',
                                 epilog="""
passing no recommendation scheme argument defaults to basing recommendations off your top 5 valid seed genres
spotirec is released under GPL-3.0 and comes with ABSOLUTELY NO WARRANTY, for details read LICENSE""")
parser.add_argument('n', nargs='?', type=int, const=5, default=5,
                    help='amount of seeds to use on no-arg recommendations as an integer - note that this must appear '
                         'as the first argument if used and can only be used with no-arg')

# Recommendation schemes
rec_scheme_group = parser.add_argument_group(title='Recommendation schemes')
# Create mutually exclusive group for recommendation types to ensure only one is given
mutex_group = rec_scheme_group.add_mutually_exclusive_group()
mutex_group.add_argument('-a', metavar='SEED_SIZE', nargs='?', type=int, const=5, choices=range(1, 6),
                         help='base recommendations on your top artists')
mutex_group.add_argument('-t', metavar='SEED_SIZE', nargs='?', type=int, const=5, choices=range(1, 6),
                         help='base recommendations on your top tracks')
mutex_group.add_argument('-ac', action='store_true', help='base recommendations on custom top artists')
mutex_group.add_argument('-tc', action='store_true', help='base recommendations on custom top tracks')
mutex_group.add_argument('-gc', action='store_true', help='base recommendations on custom top valid seed genres')
mutex_group.add_argument('-gcs', action='store_true', help='base recommendations on custom seed genres')
mutex_group.add_argument('-c', action='store_true', help='base recommendations on a custom seed')
rec_scheme_group.add_argument('--preserve', action='store_true', help='preserve previous playlist and create new')

# Saving arguments
save_group = parser.add_argument_group(title='Saving arguments')
# You should only be able to save or remove the current track at once, not both
save_mutex_group = save_group.add_mutually_exclusive_group()
add_mutex_group = save_group.add_mutually_exclusive_group()
save_mutex_group.add_argument('-s', action='store_true', help='like currently playing track')
save_mutex_group.add_argument('-sr', action='store_true', help='remove currently playing track from liked tracks')
add_mutex_group.add_argument('--add-to', metavar='[PLAYLIST | URI]', nargs=1, type=str,
                             help='add currently playing track to input playlist')
add_mutex_group.add_argument('--remove-from', metavar='[PLAYLIST | URI]', nargs=1, type=str,
                             help='remove currently playing track from input playlist')
save_group.add_argument('--save-playlist', action='store_true', help='save a playlist')
save_group.add_argument('--remove-playlists', metavar='ID', nargs='+', type=str, help='remove playlist(s)')
save_group.add_argument('--save-device', action='store_true', help='save a playback device')
save_group.add_argument('--remove-devices', metavar='ID', nargs='+', type=str, help='remove playback device(s)')
save_group.add_argument('--load-preset', metavar='ID', nargs=1, type=str, help='load and use preset')
save_group.add_argument('--save-preset', metavar='ID', nargs=1, type=str, help='save options as preset')
save_group.add_argument('--remove-presets', metavar='ID', nargs='+', type=str, help='remove preset(s)')

# Recommendation modifications
rec_options_group = parser.add_argument_group(title='Recommendation options',
                                              description='These may only appear when creating a playlist')
rec_options_group.add_argument('-l', metavar='LIMIT', nargs=1, type=int, choices=range(1, 101),
                               help='amount of tracks to add (default: 20, max: 100)')
rec_options_group.add_argument('--tune', metavar='ATTR', nargs='+', type=str, help='specify tunable attribute(s)')
rec_options_group.add_argument('--play', metavar='DEVICE', nargs=1, help='select playback device to start playing on')

# Blacklisting
blacklist_group = parser.add_argument_group(title='Blacklisting')
blacklist_group.add_argument('-b', metavar='URI', nargs='+', type=str, help='blacklist track(s) and/or artist(s)')
blacklist_group.add_argument('-br', metavar='URI', nargs='+', type=str,
                             help='remove track(s) and/or artists(s) from blacklist')
blacklist_group.add_argument('-bc', metavar='artist | track', nargs=1, choices=['artist', 'track'],
                             help='blacklist currently playing artist(s) or track')

# Printing
print_group = parser.add_argument_group(title='Printing')
print_group.add_argument('--print', metavar='TYPE', nargs=1, type=str,
                         choices=['artists', 'tracks', 'genres', 'genre-seeds', 'devices', 'blacklist', 'presets',
                                  'playlists', 'tuning'],
                         help='print a list of genre seeds, or your top artists, tracks, or genres, where '
                              'TYPE=[artists|tracks|genres|genre-seeds|devices|blacklist]')
print_group.add_argument('--version', action='version', version=f'%(prog)s v{VERSION}')
print_group.add_argument('--track-features', metavar='[URI | current]', nargs=1, type=str,
                         help='print track features of URI or currently playing track')

# Ensure config dir exists
if not os.path.isdir(CONFIG_PATH):
    os.makedirs(CONFIG_PATH)


def authorize():
    """
    Open redirect URL in browser, and host http server on localhost.
    Function index() will be routed on said http server.
    """
    webbrowser.open(sp_oauth.redirect)
    run(host='', port=PORT)


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
        access_token = sp_oauth.retrieve_access_token(code)['access_token']
    if access_token:
        return "<span>Successfully retrieved OAuth token. You may close this tab and start using Spotirec.</span>"
    else:
        return f"<a href='{sp_oauth.get_authorize_url()}'>Login to Spotify</a>"


def get_token() -> str:
    """
    Retrieve access token from OAuth handler. Try to authorize and exit if credentials don't exist.
    :return: access token, if present
    """
    creds = sp_oauth.get_credentials()
    if creds:
        return creds.get('access_token')
    else:
        authorize()
        exit(1)


def get_user_top_genres() -> dict:
    """
    Extract genres from user's top 50 artists and map them to their amount of occurrences
    :return: dict of genres and their count of occurrences
    """
    data = api.get_top_list('artists', 50, headers)
    genres = {}
    genre_seeds = api.get_genre_seeds(headers)
    # Loop through each genre of each artist
    for x in data['items']:
        for genre in x['genres']:
            genre = genre.replace(' ', '-')
            # Check if genre is a valid seed
            if any(g == genre for g in genre_seeds['genres']):
                try:
                    genres[genre] += 1
                except KeyError:
                    genres[genre] = 1
    return genres


def add_top_genres_seed(seed_count: int):
    """
    Add top 5 genres to recommendation object seed info.
    """
    sort = sorted(get_user_top_genres().items(), key=lambda kv: kv[1], reverse=True)
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
    if sort:
        sorted_data = sorted(data.items(), key=lambda kv: kv[1], reverse=True)
        data = [sorted_data[x][0] for x in range(0, len(sorted_data))]
    line = ""
    # Format output lines, three seeds per line
    for x in range(0, round(len(data)), 3):
        try:
            line += f'{x}: {data[x]}'
            if data[x + 1]:
                line += f'{" " * (40 - len(data[x]))}{x + 1}: ' \
                        f'{data[x + 1] if len(data[x + 1]) < 40 else f"{data[x + 1][0:37]}.. "}'
                if data[x + 2]:
                    line += f'{" " * (40 - len(data[x + 1]))}{x + 2}: ' \
                            f'{data[x + 2] if len(data[x + 2]) < 40 else f"{data[x + 2][0:37]}.. "}\n'
        except IndexError:
            continue
    print(line.strip('\n'))
    if prompt:
        try:
            input_string = input('Enter integer identifiers for 1-5 whitespace separated selections that you wish to '
                                 'include [default: top 5]:\n') or '0 1 2 3 4'
        except KeyboardInterrupt:
            exit(0)
        # If seed type is genres, simply parse the seed, else return the input for further processing
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
    if any(g == genre for g in get_user_top_genres()) or any(
            g == genre for g in api.get_genre_seeds(headers)['genres']):
        return True
    return False


def check_tune_validity(tune: str):
    """
    Check validity of tune input - exit program if not valid
    :param tune: tune input as string
    """
    prefix = tune.split('_', 1)[0]
    key = tune.split('=')[0].split('_', 1)[1]
    value = tune.split('=')[1]
    # Check prefix validity
    if prefix not in TUNE_PREFIX:
        print(f'Tune prefix \"{tune.split("_", 1)[0]}\" is malformed - available prefixes:')
        print(TUNE_PREFIX)
        exit(1)
    # Check attribute validity
    if key not in list(TUNE_ATTR['int'].keys()) + list(TUNE_ATTR['float'].keys()):
        print(f'Tune attribute \"{tune.split("=")[0].split("_", 1)[1]}\" is malformed - available attributes:')
        print(list(TUNE_ATTR['int'].keys()) + list(TUNE_ATTR['float'].keys()))
        exit(1)
    # Try parsing value to number
    try:
        # Try parsing value to number
        value = int(float(value)) if key in TUNE_ATTR['int'].keys() else float(value)
        value_type = 'int' if key in TUNE_ATTR['int'].keys() else 'float'
        # Ensure value is within accepted range
        if not TUNE_ATTR[value_type][key]['max'] >= value >= TUNE_ATTR[value_type][key]['min']:
            print(f'Error: value {value} for attribute {key} is outside the accepted range (min: '
                  f'{TUNE_ATTR[value_type][key]["min"]}, max: {TUNE_ATTR[value_type][key]["max"]})')
            exit(1)
        # Warn if value is outside recommended range
        if not TUNE_ATTR[value_type][key]['rec_max'] >= value >= TUNE_ATTR[value_type][key]['rec_min']:
            print(f'Warning: value {value} for attribute {key} is outside the recommended range (min: '
                  f'{TUNE_ATTR[value_type][key]["rec_min"]}, max: {TUNE_ATTR[value_type][key]["rec_max"]}), '
                  f'recommendations may be scarce')
    except ValueError:
        print(f'Tune value {value} does not match attribute {key} data type requirements')
        exit(1)


def parse_seed_info(seeds):
    """
    Adds seed data to recommendation object
    :param seeds: seed data as a string or a list
    """
    if len(shlex.split(seeds) if type(seeds) is str else seeds) > 5:
        print('Please enter at most 5 seeds')
        exit(1)
    # Parse each seed in input and add to seed string depending on type
    for x in shlex.split(seeds) if type(seeds) is str else seeds:
        if rec.seed_type == 'genres':
            rec.add_seed_info(data_string=x)
        elif rec.seed_type == 'custom':
            if check_if_valid_genre(x):
                rec.add_seed_info(data_string=x)
            elif re.match(URI_RE, x):
                rec.add_seed_info(data_dict=api.request_data(x, f'{x.split(":")[1]}s', headers))
            else:
                print(f'Input \"{x}\" does not match a genre or a valid URI syntax, skipping...')
        else:
            rec.add_seed_info(data_dict=x)


def add_to_blacklist(entries: list):
    """
    Add input uris to blacklist and exit
    :param entries: list of input uris
    """
    for x in entries:
        uri_data = api.request_data(x, f'{x.split(":")[1]}s', headers)
        conf.add_to_blacklist(uri_data, x)


def remove_from_blacklist(entries: list):
    """
    Remove track(s) and/or artist(s) from blacklist.
    :param entries: list of uris
    """
    for x in entries:
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
    # Hash tracks to a playlist-unique string
    track_hash = hashlib.sha256(''.join(str(x) for x in tracks).encode('utf-8')).hexdigest()
    # Use the first six chars of the hash to generate a color
    # The hex value of three pairs of chars are converted to integers, yielding a list on the form [r, g, b]
    color = [int(track_hash[i:i + 2], 16) for i in (0, 2, 4)]
    # Create an image object the size of the squared square root of the hash string - always 8x8
    img = Image.new('RGB', (int(math.sqrt(len(track_hash))), int(math.sqrt(len(track_hash)))))
    pixel_map = []
    # Iterate over hash string and assign to pixel map each digit to the generated color, each letter to light gray
    for x in track_hash:
        if re.match(r'[0-9]', x):
            pixel_map.append(color)
        else:
            pixel_map.append([200, 200, 200])
    # Add the pixel map to the image object and return as a size suited for the Spotify API
    img.putdata([tuple(x) for x in pixel_map])
    return img.resize((320, 320), Image.AFFINE)


def add_image_to_playlist(tracks: list):
    """
    base64 encode image data and upload to playlist.
    :param tracks: list of track uris
    """
    print('Generating and uploading playlist cover image')
    img_headers = {'Content-Type': 'image/jpeg',
                   'Authorization': f'Bearer {get_token()}'}
    img_buffer = BytesIO()
    generate_img(tracks).save(img_buffer, format='JPEG')
    img_str = base64.b64encode(img_buffer.getvalue())
    api.upload_image(rec.playlist_id, img_str, img_headers)


def save_preset(name: str):
    """
    Save recommendation object as preset
    :param name: name of preset
    """
    preset = {'limit': rec.limit_original,
              'based_on': rec.based_on,
              'seed': rec.seed,
              'seed_type': rec.seed_type,
              'seed_info': rec.seed_info,
              'rec_params': rec.rec_params,
              'auto_play': rec.auto_play,
              'playback_device': rec.playback_device}
    conf.save_preset(preset, name)


def load_preset(name: str) -> recommendation.Recommendation:
    """
    Load preset recommendation object from config
    :param name: name of preset
    :return: recommendation object with settings from preset
    """
    print(f'Using preset \"{name}\"')
    presets = conf.get_presets()
    try:
        contents = presets.get(name)
    except KeyError:
        print(f'Error: could not find preset \"{name}\", check spelling and try again')
        exit(1)
    preset = recommendation.Recommendation()
    preset.limit = contents['limit']
    preset.limit_original = contents['limit']
    preset.based_on = contents['based_on']
    preset.seed = contents['seed']
    preset.seed_type = contents['seed_type']
    preset.seed_info = contents['seed_info']
    preset.rec_params = contents['rec_params']
    preset.auto_play = contents['auto_play']
    preset.playback_device = contents['playback_device']
    return preset


def remove_presets(presets: list):
    """
    Remove preset(s) from user config
    :param presets: list of devices
    """
    for x in presets:
        conf.remove_preset(x)


def print_presets():
    """
    Format and print preset entries
    """
    presets = conf.get_presets()
    print('\033[1m' + f'Name{" " * 16}Type{" " * 21}Params{" " * 44}Seeds' + '\033[0m')
    for x in presets.items():
        params = ",".join(f"{y[0]}={y[1]}" if "seed" not in y[0] else "" for y in x[1]["rec_params"].items()).strip(',')
        print(f'{x[0]}{" " * (20 - len(x[0]))}{x[1]["based_on"]}{" " * (25 - len(x[1]["based_on"]))}'
              f'{params}{" " * (50 - len(params))}{",".join(str(y["name"]) for y in x[1]["seed_info"].values())}')


def get_device(device_name: str) -> dict:
    """
    Set playback device. Prompt from available devices if none exist.
    Print saved devices if it does not exist.
    :param device_name: name of playback device
    """
    devices = conf.get_devices()
    try:
        return devices.get(device_name)
    except KeyError:
        print(f'Error: device {device_name} does not exist in config')
        exit(1)


def save_device():
    """
    Prompt user for an identifier for device and save to config
    """

    def prompt_device_index() -> int:
        try:
            ind = input('Select a device by index[0]: ') or 0
        except KeyboardInterrupt:
            exit(0)
        try:
            assert devices[int(ind)] is not None
            return int(ind)
        except (ValueError, AssertionError, IndexError):
            print(f'Error: input \"{ind}\" is malformed.')
            print('Please ensure that your input is an integer and is a valid index.')
            return prompt_device_index()

    def prompt_name() -> str:
        try:
            try:
                inp = input('Enter an identifier for your device: ')
            except KeyboardInterrupt:
                exit(0)
            assert inp
            assert ' ' not in inp
            return inp
        except AssertionError:
            print(f'Error: device identifier \"{inp}\" is malformed.')
            print('Please ensure that the identifier contains at least one character, and no whitespaces.')
            return prompt_name()

    # Get available devices from API and print
    devices = api.get_available_devices(headers)['devices']
    print('Available devices:')
    print('\033[1m' + f'Name{" " * 19}Type' + '\033[0m')
    for x in devices:
        print(f'{devices.index(x)}. {x["name"]}{" " * (20 - len(x["name"]))}{x["type"]}')
    # Prompt device selection and identifier, and save to config
    device = devices[prompt_device_index()]
    device_dict = {'id': device['id'], 'name': device['name'], 'type': device['type']}
    name = prompt_name()
    conf.save_device(device_dict, name)


def remove_devices(devices: list):
    """
    Remove device(s) from user config
    :param devices: list of device(s)
    """
    for x in devices:
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
        print(f'{x[0]}{" " * (20 - len(x[0]))}{x[1]["name"]}{" " * (30 - len(x[1]["name"]))}{x[1]["uri"]}')


def save_playlist():
    """
    Prompt user for an identifier and URI for playlist and save to config
    """

    def input_id() -> str:
        try:
            iden = input('Please input an identifier for your playlist: ')
        except KeyboardInterrupt:
            exit(0)
        try:
            assert iden
            assert ' ' not in iden
            return iden
        except AssertionError:
            print(f'Error: playlist identifier \"{iden}\" is malformed.')
            print('Please ensure that the identifier contains at least one character, and no whitespaces.')
            return input_id()

    def input_uri() -> str:
        try:
            uri = input('Please input the URI for your playlist: ')
        except KeyboardInterrupt:
            exit(0)
        try:
            assert uri
            assert re.match(PLAYLIST_URI_RE, uri)
            return uri
        except AssertionError:
            print(f'Error: playlist uri \"{uri}\" is malformed.')
            return input_uri()

    # Prompt device identifier and URI, and save to config
    playlist_id = input_id()
    playlist_uri = input_uri()
    playlist = {'name': api.get_playlist(headers, playlist_uri.split(':')[2])["name"], 'uri': playlist_uri}
    conf.save_playlist(playlist, playlist_id)


def remove_playlists(playlists: list):
    """
    Remove playlist(s) from user config
    :param playlists: list of playlist(s)
    """
    for x in playlists:
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
            print(f'Error: playlist {playlist} does not exist in config')
            exit(1)
    print(f'Adding currently playing track to playlist')
    api.add_to_playlist([api.get_current_track(headers)], playlist_id, headers)


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
            print(f'Error: playlist {playlist} does not exist in config')
            exit(1)
    print(f'Removing currently playing track to playlist')
    api.remove_from_playlist([api.get_current_track(headers)], playlist_id, headers)


def print_track_features(uri: str):
    """
    Prints various information about a track
    :param uri: URI of track
    """
    if not re.match(TRACK_URI_RE, uri):
        print(f'Error: {uri} is not a valid track URI')
        exit(1)
    audio_features = api.get_audio_features(uri.split(':')[2], headers)
    track_info = api.request_data(uri, 'tracks', headers)
    print('\t' + '\033[1m' + f'{track_info["name"]} - {", ".join(x["name"] for x in track_info["artists"])}' + '\033[0m')
    print(f'Track URI{" " * 21}{track_info["uri"]}')
    print(f'Artist URI(s){" " * 17}{", ".join(x["name"] + ": " + x["uri"] for x in track_info["artists"])}')
    print(f'Album URI{" " * 21}{track_info["album"]["uri"]}')
    print(f'Release date{" " * 18}{track_info["album"]["release_date"]}')
    print(f'Duration{" " * 22}{audio_features["duration_ms"]}ms ({millis_to_stamp(audio_features["duration_ms"])})')
    print(f'Key{" " * 27}{audio_features["key"]}')
    print(f'Mode{" " * 26}{audio_features["mode"]} ({"minor" if audio_features["mode"] == 0 else "major"})')
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
    Convert milliseconds to a timestamp on the form "{hours}h {minutes}m {seconds}s". Hours and minutes are only
    included if they are present.
    :param x: milliseconds
    :return: formatted timestamp
    """
    sec_total = int(x / 1000)
    sec = sec_total % 60
    mins_total = math.floor(sec_total / 60)
    mins = mins_total % 60
    hours = int(mins_total / 60)
    return f'{f"{hours}h " if hours != 0 else ""}{f"{mins}m " if mins != 0 else ""}{sec}s'


def filter_recommendations(data: json) -> list:
    """
    Filter blacklisted artists and tracks from recommendations.
    :param data: recommendations as json object.
    :return: list of eligible track URIs
    """
    valid_tracks = []
    blacklist = conf.get_blacklist()
    for x in data['tracks']:
        # If the URI of the current track is blacklisted or there is an intersection between the set of blacklisted
        # artists and the set of artists of the current track, then skip - otherwise add to valid tracks
        if any(x['uri'] == s for s in blacklist['tracks'].keys()) or len(
                set(blacklist['artists'].keys()) & set(y['uri'] for y in x['artists'])) > 0:
            continue
        else:
            valid_tracks.append(x['uri'])
    return valid_tracks


def print_tuning_options():
    try:
        with open(f'{Path.home()}/.config/spotirec/tuning-opts', 'r') as file:
            tuning_opts = file.readlines()
    except FileNotFoundError:
        print('Error: could not find tuning options file.')
        exit(1)
    if len(tuning_opts) == 0:
        print('Error: tuning options file is empty.')
        exit(1)
    for x in tuning_opts:
        if tuning_opts.index(x) == 0:
            print('\033[1m' + x.strip('\n') + '\033[0m')
        else:
            print(x.strip('\n'))
    print('Note that recommendations may be scarce outside the recommended ranges. If the recommended range is not '
          'available, they may only be scarce at extreme values.')


def recommend():
    """
    Main function for recommendations. Retrieves recommendations and tops up list if any tracks
    were removed by the blacklist filter. Playlist is created and tracks are added. Seed info
    is printed to terminal.
    """
    print('Getting recommendations')
    # Create seed from user preferences
    rec.create_seed()
    # Save as preset if requested
    if args.save_preset:
        save_preset(args.save_preset[0])
    # Filter blacklisted artists and tracks from recommendations
    tracks = filter_recommendations(api.get_recommendations(rec.rec_params, headers))
    # If no tracks are left, notify an error and exit
    if len(tracks) == 0:
        print('Error: received zero tracks with your options - adjust and try again')
        exit(1)
    if len(tracks) <= rec.limit_original / 2:
        print(f'Warning: only received {len(tracks)} different recommendations, you may receive duplicates of '
              f'these (this might take a few seconds)')
    # Filter recommendations until length of track list matches limit preference
    while True:
        if len(tracks) < rec.limit_original:
            rec.update_limit(rec.limit_original - len(tracks))
            tracks += filter_recommendations(api.get_recommendations(rec.rec_params, headers))
        else:
            break

    def create_new_playlist():
        rec.playlist_id = api.create_playlist(rec.playlist_name, rec.playlist_description(), headers, cache_id=True)
        api.add_to_playlist(tracks, rec.playlist_id, headers=headers)

    # Create playlist and add tracks
    if args.preserve:
        create_new_playlist()
    else:
        try:
            rec.playlist_id = conf.get_playlists()['spotirec-default']['uri'].split(':')[2]
            assert api.check_if_playlist_exists(rec.playlist_id, headers) is True
            api.replace_playlist_tracks(rec.playlist_id, tracks, headers=headers)
            api.update_playlist_details(rec.playlist_name, rec.playlist_description(), rec.playlist_id, headers=headers)
        except (KeyError, AssertionError):
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
    if args.b:
        add_to_blacklist(args.b)
        exit(1)
    if args.br:
        remove_from_blacklist(args.br)
        exit(1)
    if args.bc:
        if args.bc[0] == 'track':
            add_to_blacklist([api.get_current_track(headers)])
        elif args.bc[0] == 'artist':
            add_to_blacklist(api.get_current_artists(headers))
        exit(1)

    if args.s:
        print('Liking current track')
        api.like_track(headers)
        exit(1)
    elif args.sr:
        print('Unliking current track')
        api.unlike_track(headers)
        exit(1)
    if args.save_playlist:
        save_playlist()
        exit(1)
    if args.remove_playlists:
        remove_playlists(args.remove_playlists)
        exit(1)
    if args.save_device:
        save_device()
        exit(1)
    if args.remove_devices:
        remove_devices(args.remove_devices)
        exit(1)
    if args.remove_presets:
        remove_presets(args.remove_presets)
        exit(1)
    if args.add_to:
        add_current_track(args.add_to[0])
        exit(1)
    elif args.remove_from:
        remove_current_track(args.remove_from[0])
        exit(1)

    if args.print:
        if args.print[0] == 'artists':
            print('Top artists:')
            print_artists_or_tracks(data=api.get_top_list('artists', 50, headers=headers), prompt=False)
        elif args.print[0] == 'tracks':
            print('Top tracks:')
            print_artists_or_tracks(data=api.get_top_list('tracks', 50, headers=headers), prompt=False)
        elif args.print[0] == 'genres':
            print('Top genres:')
            print_choices(data=get_user_top_genres(), sort=True, prompt=False)
        elif args.print[0] == 'genre-seeds':
            print('Genre seeds:')
            print_choices(data=api.get_genre_seeds(headers=headers)['genres'], prompt=False)
        elif args.print[0] == 'blacklist':
            print_blacklist()
        elif args.print[0] == 'devices':
            print_saved_devices()
        elif args.print[0] == 'presets':
            print_presets()
        elif args.print[0] == 'playlists':
            print_playlists()
        elif args.print[0] == 'tuning':
            print_tuning_options()
        exit(1)
    if args.track_features:
        print_track_features(api.get_current_track(headers) if
                             args.track_features[0] == 'current' else args.track_features[0])
        exit(1)

    if args.play:
        rec.auto_play = True
        rec.playback_device = get_device(args.play[0])

    if args.a:
        print(f'Basing recommendations off your top {args.a} artist(s)')
        rec.based_on = 'top artists'
        rec.seed_type = 'artists'
        parse_seed_info([x for x in api.get_top_list('artists', args.a, headers)['items']])
    elif args.t:
        print(f'Basing recommendations off your top {args.t} track(s)')
        rec.based_on = 'top tracks'
        rec.seed_type = 'tracks'
        parse_seed_info([x for x in api.get_top_list('tracks', args.t, headers)['items']])
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
    elif args.gc:
        rec.based_on = 'custom top genres'
        print_choices(data=get_user_top_genres(), sort=True)
    elif args.c:
        rec.based_on = 'custom mix'
        rec.seed_type = 'custom'
        print_choices(data=get_user_top_genres(), prompt=False, sort=True)
        try:
            user_input = input(
                'Enter a combination of 1-5 whitespace separated genre names, track uris, and artist uris. '
                '\nGenres with several words should be connected with dashes, e.g.; vapor-death-pop.\n')
        except KeyboardInterrupt:
            exit(0)
        if not user_input:
            print('Please enter 1-5 seeds')
            exit(1)
        parse_seed_info(user_input.strip(' '))
    else:
        print(f'Basing recommendations off your top {args.n} genres')
        add_top_genres_seed(args.n)

    if args.l:
        rec.update_limit(args.l[0], init=True)
    print(f'The playlist will contain {rec.limit} tracks')

    if args.tune:
        for x in args.tune:
            check_tune_validity(x)
            rec.rec_params[x.split('=')[0]] = x.split('=')[1]


args = parser.parse_args()

headers = {'Content-Type': 'application/json',
           'Authorization': f'Bearer {get_token()}'}
if args.load_preset:
    rec = load_preset(args.load_preset[0])
else:
    rec = recommendation.Recommendation()
    parse()

if __name__ == '__main__':
    recommend()

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
from io import BytesIO
from PIL import Image
from bottle import route, run, request
from pathlib import Path

port = 8080
config_path = f'{Path.home()}/.config/spotirec'
blacklist_path = f'{config_path}/blacklist'
preset_path = f'{config_path}/presets'
devices_path = f'{config_path}/devices'
tune_prefix = ['max', 'min', 'target']
tune_attr = ['acousticness', 'danceability', 'duration_ms', 'energy', 'instrumentalness', 'key', 'liveness',
             'loudness', 'mode', 'popularity', 'speechiness', 'tempo', 'time_signature', 'valence', 'popularity']
uri_re = r'spotify:(artist|track):[a-zA-Z0-9]'

# OAuth handler
sp_oauth = oauth2.SpotifyOAuth()

# Argument parser
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="""
passing no recommendation scheme argument defaults to basing recommendations off your top 5 valid seed genres
spotirec is released under GPL-3.0 and comes with ABSOLUTELY NO WARRANTY, for details read LICENSE""")

# Create mutually exclusive group for recommendation types to ensure only one is given
rec_scheme_group = parser.add_argument_group(title='Recommendation schemes')
mutex_group = rec_scheme_group.add_mutually_exclusive_group()
mutex_group.add_argument('-a', action='store_true', help='base recommendations on your top artists')
mutex_group.add_argument('-t', action='store_true', help='base recommendations on your top tracks')
mutex_group.add_argument('-ac', action='store_true', help='base recommendations on custom top artists')
mutex_group.add_argument('-tc', action='store_true', help='base recommendations on custom top tracks')
mutex_group.add_argument('-gc', action='store_true', help='base recommendations on custom top valid seed genres')
mutex_group.add_argument('-gcs', action='store_true', help='base recommendations on custom seed genres')
mutex_group.add_argument('-c', action='store_true', help='base recommendations on a custom seed')

save_group = parser.add_argument_group(title='Saving arguments')
save_mutex_group = save_group.add_mutually_exclusive_group()
save_mutex_group.add_argument('-s', action='store_true', help='like currently playing track')
save_mutex_group.add_argument('-sr', action='store_true', help='remove currently playing track from liked tracks')

rec_options_group = parser.add_argument_group(title='Recommendation options',
                                              description='These may only appear when creating a playlist')
rec_options_group.add_argument('-l', metavar='LIMIT', nargs=1, type=int, choices=range(1, 101),
                               help='amount of tracks to add (default: 20, max: 100)')
preset_mutex = rec_options_group.add_mutually_exclusive_group()
preset_mutex.add_argument('-p', metavar='NAME', nargs=1, type=str, help='load and use preset')
preset_mutex.add_argument('-ps', metavar='NAME', nargs=1, type=str, help='save options as preset')
rec_options_group.add_argument('--tune', metavar='ATTR', nargs='+', type=str, help='specify tunable attribute(s)')
play_mutex = rec_options_group.add_mutually_exclusive_group()
play_mutex.add_argument('--play', action='store_true', help='select playback device to start playing on')
play_mutex.add_argument('--play-device', metavar='DEVICE', nargs=1, type=str, help='start playback on saved device')

device_group = parser.add_argument_group(title='Playback devices')
device_group.add_argument('-d', action='store_true', help='save a device')
device_group.add_argument('-dr', metavar='DEVICE', nargs="+", type=str, help='remove device(s)')

blacklist_group = parser.add_argument_group(title='Blacklisting')
blacklist_group.add_argument('-b', metavar='URI', nargs='+', type=str, help='blacklist track(s) and/or artist(s)')
blacklist_group.add_argument('-br', metavar='URI', nargs='+', type=str,
                             help='remove track(s) and/or artists(s) from blacklist')
blacklist_group.add_argument('-bc', metavar='artist|track', nargs=1, choices=['artist', 'track'],
                             help='blacklist currently playing artist(s) or track')

print_group = parser.add_argument_group(title='Printing')
print_group.add_argument('--print', metavar='TYPE', nargs=1, type=str,
                         choices=['artists', 'tracks', 'genres', 'genre-seeds', 'devices', 'blacklist'],
                         help='print a list of genre seeds, or your top artists, tracks, or genres, where'
                              'TYPE=[artists|tracks|genres|genre-seeds|devices|blacklist]')

# Ensure config dir and blacklist file exists
if not os.path.isdir(config_path):
    os.makedirs(config_path)
if not os.path.exists(blacklist_path):
    f = open(blacklist_path, 'w')
    f.close()
if not os.path.exists(preset_path):
    f = open(preset_path, 'w')
    f.close()
if not os.path.exists(devices_path):
    f = open(devices_path, 'w')
    f.close()


def authorize():
    """
    Open redirect URL in browser, and host http server on localhost.
    Function index() will be routed on said http server.
    """
    webbrowser.open(sp_oauth.redirect)
    run(host='', port=port)


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
        return creds['access_token']
    else:
        authorize()
        exit(1)


def get_user_top_genres() -> dict:
    """
    Extract genres from user's top 50 artists and map them to their amount of occurrences
    :return: dict of genres and their count of occurrences
    """
    data = api.get_top_list('artists', 50, headers=headers)
    genres = {}
    genre_seeds = api.get_genre_seeds(headers=headers)
    for x in data['items']:
        for genre in x['genres']:
            genre = genre.replace(' ', '-')
            if genre in genre_seeds['genres']:
                if genre in genres.keys():
                    genres[genre] += 1
                else:
                    genres[genre] = 1
    return genres


def add_top_genres_seed():
    """
    Add top 5 genres to recommendation object seed info.
    """
    sort = sorted(get_user_top_genres().items(), key=lambda kv: kv[1], reverse=True)
    parse_seed_info([sort[x][0] for x in range(0, 5)])


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
        input_string = input('Enter integer identifiers for 1-5 whitespace separated selections that you wish to '
                             'include:\n')
        if 'genres' in rec.seed_type:
            parse_seed_info([data[int(x)] for x in input_string.split(' ')])
        else:
            return input_string


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
    if genre in get_user_top_genres():
        return True
    if genre in api.get_genre_seeds(headers=headers)['genres']:
        return True
    return False


def parse_seed_info(seeds):
    """
    Adds seed data to recommendation object
    :param seeds: seed data as a string or a list
    """
    for x in shlex.split(seeds) if type(seeds) is str else seeds:
        if rec.seed_type == 'genres':
            rec.add_seed_info(data_string=x)
        elif rec.seed_type == 'custom':
            if check_if_valid_genre(x):
                rec.add_seed_info(data_string=x)
            elif re.match(uri_re, x):
                rec.add_seed_info(data_dict=api.request_data(x, f'{x.split(":")[1]}s', headers=headers))
            else:
                print(f'Input \"{x}\" does not match a genre or a valid URI syntax, skipping...')
        else:
            rec.add_seed_info(data_dict=x)


def add_to_blacklist(entries: list):
    """
    Add input uris to blacklist and exit
    :param entries: list of input uris
    """
    with open(blacklist_path, 'r') as file:
        try:
            data = json.loads(file.read())
        except json.decoder.JSONDecodeError:
            data = {'tracks': {},
                    'artists': {}}
        for uri in entries:
            if re.match(uri_re, uri):
                uri_data = api.request_data(uri, f'{uri.split(":")[1]}s', headers=headers)
                data[f'{uri.split(":")[1]}s'][uri] = {'name': uri_data['name'],
                                                      'uri': uri}
                try:
                    data[f'{uri.split(":")[1]}s'][uri]['artists'] = [x['name'] for x in uri_data['artists']]
                    print(f'Added track \"{uri_data["name"]}\" by '
                          f'{", ".join(str(x["name"]) for x in uri_data["artists"])} to your blacklist')
                except KeyError:
                    print(f'Added artist \"{uri_data["name"]}\" to your blacklist')
            else:
                print(f'uri \"{uri}\" is either not a valid uri for a track or artist, or is malformed and has '
                      f'not been added to the blacklist')
    with open(blacklist_path, 'w+') as file:
        file.write(json.dumps(data))


def remove_from_blacklist(entries: list):
    """
    Remove track(s) and/or artist(s) from blacklist.
    :param entries: list of uris
    """
    try:
        with open(blacklist_path, 'r') as file:
            blacklist = json.loads(file.read())
    except json.decoder.JSONDecodeError:
        print('Error: blacklist is empty')
        exit(1)
    for uri in entries:
        if re.match(uri_re, uri):
            try:
                try:
                    print(f'Removing track {blacklist["tracks"][uri]["name"]} by '
                          f'{", ".join(str(x) for x in blacklist["tracks"][uri]["artists"]).strip(", ")} from blacklist')
                except KeyError:
                    print(f'Removing artist \"{blacklist["artists"][uri]["name"]}\" from blacklist')
                del blacklist[f'{uri.split(":")[1]}s'][uri]
            except KeyError:
                print(f'uri \"{uri}\" does not exist in your blacklist')
                # FIXME: Remove this notice at some point
                print('Blacklist structure was recently re-done, so you may need to remove and re-do your blacklist. '
                      'Sorry!')
        else:
            print(f'uri \"{uri}\" is either not a valid uri for a track or artist or is malformed')

    with open(blacklist_path, 'w+') as file:
        file.write(json.dumps(blacklist))


def print_blacklist():
    """
    Format and print blacklist entries
    """
    with open(blacklist_path, 'r') as file:
        try:
            blacklist = json.loads(file.read())
            print('Tracks')
            print('--------------------------')
            for x in blacklist['tracks']:
                print(f'{x["name"]} by {", ".join(x["artists"]).strip(", ")} - {x["uri"]}')
            print('\nArtists')
            print('--------------------------')
            for x in blacklist['artists']:
                print(f'{x["name"]} - {x["uri"]}')
        except json.decoder.JSONDecodeError:
            print('Blacklist is empty')


def generate_img(tracks: list) -> Image:
    """
    Generate personalized cover image for a playlist. Track uris are hashed. The hash is both mapped
    to an image and converted to a color.
    :param tracks: list of track uris
    :return: a 320x320 image generated from playlist hash
    """
    track_hash = hashlib.sha256(''.join(str(x) for x in tracks).encode('utf-8')).hexdigest()
    color = [int(track_hash[i:i + 2], 16) for i in (0, 2, 4)]
    img = Image.new('RGB', (int(math.sqrt(len(track_hash))), int(math.sqrt(len(track_hash)))))
    pixel_map = []
    for x in track_hash:
        if re.match(r'[0-9]', x):
            pixel_map.append(color)
        else:
            pixel_map.append([200, 200, 200])
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
    api.upload_image(playlist_id=rec.playlist_id, data=img_str, img_headers=img_headers)


def save_preset(name: str):
    """
    Save recommendation object as preset
    :param name: name of preset
    """
    try:
        with open(preset_path, 'r') as file:
            preset_data = json.loads(file.read())
    except json.decoder.JSONDecodeError:
        preset_data = {}
    preset_data[name] = {'limit': rec.limit_original,
                         'based_on': rec.based_on,
                         'seed': rec.seed,
                         'seed_type': rec.seed_type,
                         'seed_info': rec.seed_info,
                         'rec_params': rec.rec_params,
                         'auto_play': rec.auto_play,
                         'playback_device': rec.playback_device}
    with open(preset_path, 'w+') as file:
        print(f'Saving preset \"{name}\"')
        file.write(json.dumps(preset_data))


def load_preset(name: str) -> recommendation.Recommendation:
    """
    Load preset recommendation object from config
    :param name: name of preset
    :return: recommendation object with settings from preset
    """
    print(f'Using preset \"{name}\"')
    try:
        with open(preset_path, 'r') as file:
            preset_data = json.loads(file.read())
    except json.decoder.JSONDecodeError:
        print('Error: you do not have any presets')
        exit(1)
    try:
        contents = preset_data[name]
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
    except KeyError:
        print(f'Error: could not find preset \"{name}\", check spelling and try again')
        exit(1)


def get_device(device_name: str):
    """
    Set playback device. Prompt from available devices if none exist.
    Print saved devices if it does not exist.
    :param device_name: name of playback device
    """
    try:
        with open(devices_path, 'r') as file:
            devices = json.loads(file.read())
            try:
                rec.playback_device = devices[device_name]
                return
            except KeyError:
                print(f'Error: device \"{device_name}\" not recognized. Saved devices:')
                for x in devices:
                    print(x)
                exit(1)
    except json.decoder.JSONDecodeError:
        print('Your device list is empty')
        print_devices()


def print_devices(save_prompt=True, selection_prompt=True):
    """
    Print available devices and prompt user to select depending on params
    :param save_prompt: whether or not user should be prompted if they want to save
    :param selection_prompt: whether or not user should be prompted for a selection
    """
    devices = api.get_available_devices(headers)['devices']
    print('Available devices:')
    print(f'Name{" " * 19}Type')
    print("-" * 40)
    for x in devices:
        print(f'{devices.index(x)}. {x["name"]}{" " * (20 - len(x["name"]))}{x["type"]}')
    if selection_prompt:
        def prompt_selection() -> int:
            try:
                inp = int(input(f'Please select a device by index number [default: '
                                f'{devices[0]["name"]}]: ') or 0)
                assert devices[inp] is not None
                return inp
            except (IndexError, AssertionError, ValueError):
                print('Error: please input a valid index number')
                return prompt_selection()

        selection = prompt_selection()
        rec.playback_device = {'name': devices[selection]['name'],
                               'id': devices[selection]['id'],
                               'type': devices[selection]['type']}
        save = input(f'Would you like to save \"{rec.playback_device["name"]}\" '
                     'for later use? [y/n] ') or 'y' if save_prompt else save_device()
        if save == 'y':
            save_device()


def save_device():
    """
    Prompt user for an identifier for device and save to config
    """

    def prompt_name() -> str:
        try:
            inp = input('Enter an identifier for your device: ')
            assert inp
            return inp
        except AssertionError:
            prompt_name()

    name = prompt_name().replace(' ', '')
    try:
        with open(devices_path, 'r') as file:
            devices = json.loads(file.read())
    except json.decoder.JSONDecodeError:
        devices = {}
    devices[name] = rec.playback_device
    with open(devices_path, 'w+') as file:
        file.write(json.dumps(devices))
    print(f'Saved device \"{rec.playback_device["name"]}\" as \"{name}\"')


def remove_devices(devices: list):
    """
    Remove device(s) from user config
    :param devices: list of devices
    """
    try:
        with open(devices_path, 'r') as file:
            saved_devices = json.loads(file.read())
    except json.decoder.JSONDecodeError:
        print('You have no saved devices')
        exit(1)
    for x in devices:
        try:
            del saved_devices[x]
            print(f'Deleted device \"{x}\"')
        except KeyError:
            print(f'Could not find device \"{x}\" in saved devices')
            pass
    with open(devices_path, 'w+') as file:
        file.write(json.dumps(saved_devices))


def print_saved_devices():
    """
    Print all saved devices
    """
    try:
        with open(devices_path, 'r') as file:
            devices = json.loads(file.read())
    except json.decoder.JSONDecodeError:
        print('You have no saved devices')
        exit(1)
    print('Saved devices:')
    print(f'ID{" " * 18}Name{" " * 16}Type')
    print("-" * 50)
    for x in devices:
        print(f'{x}{" " * (20 - len(x))}{devices[x]["name"]}'
              f'{" " * (20 - len(devices[x]["name"]))}{devices[x]["type"]}')


def filter_recommendations(data: json) -> list:
    """
    Filter blacklisted artists and tracks from recommendations.
    :param data: recommendations as json object.
    :return: list of eligible track URIs
    """
    tracks = []
    with open(blacklist_path, 'r+') as file:
        try:
            blacklist = json.loads(file.read())
            blacklist_artists = [x for x in blacklist['artists'].keys()]
            blacklist_tracks = [x for x in blacklist['tracks'].keys()]
            for x in data['tracks']:
                if x['uri'] in blacklist_artists:
                    continue
                elif x['uri'] in blacklist_tracks:
                    continue
                else:
                    tracks.append(x['uri'])
        except json.decoder.JSONDecodeError:
            tracks = [x['uri'] for x in data['tracks']]
    return tracks


def recommend():
    """
    Main function for recommendations. Retrieves recommendations and tops up list if any tracks
    were removed by the blacklist filter. Playlist is created and tracks are added. Seed info
    is printed to terminal.
    """
    print('Getting recommendations')
    rec.create_seed()
    if args.ps:
        save_preset(args.ps[0])
    tracks = filter_recommendations(api.get_recommendations(rec.rec_params, headers=headers))
    if len(tracks) == 0:
        print('Error: received zero tracks with your options - adjust and try again')
        exit(1)
    while True:
        if len(tracks) < rec.limit_original:
            rec.update_limit(rec.limit_original - len(tracks))
            tracks += filter_recommendations(api.get_recommendations(rec.rec_params, headers=headers))
        else:
            break
    rec.playlist_id = api.create_playlist(rec.playlist_name, rec.playlist_description(), headers=headers)
    api.add_to_playlist(tracks, rec.playlist_id, headers=headers)
    add_image_to_playlist(tracks)
    rec.print_selection()
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
            print(api.get_current_track(headers))
            add_to_blacklist([api.get_current_track(headers)])
        elif args.bc[0] == 'artist':
            add_to_blacklist(api.get_current_artists(headers))
        exit(1)

    if args.s:
        api.like_track(headers=headers)
        exit(1)
    elif args.sr:
        api.unlike_track(headers=headers)
        exit(1)

    if args.play:
        rec.auto_play = True
        print_devices()
    elif args.play_device:
        rec.auto_play = True
        get_device(args.play_device[0])

    if args.d:
        print_devices(save_prompt=False)
        exit(1)
    if args.dr:
        remove_devices(args.dr)
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
        exit(1)

    if args.a:
        print('Basing recommendations off your top 5 artists')
        rec.based_on = 'top artists'
        rec.seed_type = 'artists'
        parse_seed_info([x for x in api.get_top_list('artists', 5, headers=headers)['items']])
    elif args.t:
        print('Basing recommendations off your top 5 tracks')
        rec.based_on = 'top tracks'
        rec.seed_type = 'tracks'
        parse_seed_info([x for x in api.get_top_list('tracks', 5, headers=headers)['items']])
    elif args.gcs:
        rec.based_on = 'custom seed genres'
        print_choices(data=api.get_genre_seeds(headers=headers)['genres'])
    elif args.ac:
        rec.based_on = 'custom artists'
        rec.seed_type = 'artists'
        print_artists_or_tracks(api.get_top_list('artists', 50, headers=headers))
    elif args.tc:
        rec.based_on = 'custom tracks'
        rec.seed_type = 'tracks'
        print_artists_or_tracks(api.get_top_list('tracks', 50, headers=headers))
    elif args.gc:
        rec.based_on = 'custom top genres'
        print_choices(data=get_user_top_genres(), sort=True)
    elif args.c:
        rec.based_on = 'custom mix'
        rec.seed_type = 'custom'
        print_choices(data=get_user_top_genres(), prompt=False, sort=True)
        user_input = input('Enter a combination of 1-5 whitespace separated genre names, track uris, and artist uris. '
                           '\nGenres with several words should be connected with dashes, e.g.; vapor-death-pop.\n')
        parse_seed_info(user_input)
    else:
        print('Basing recommendations off your top 5 genres')
        add_top_genres_seed()

    if args.l:
        rec.update_limit(args.l[0], init=True)
    print(f'The playlist will contain {rec.limit} tracks')

    if args.tune:
        for x in args.tune:
            if not x.split('_', 1)[0] in tune_prefix:
                print(f'Tune prefix \"{x.split("_", 1)[0]}\" is malformed - available prefixes:')
                print(tune_prefix)
                exit(1)
            if not x.split('=')[0].split('_', 1)[1] in tune_attr:
                print(f'Tune attribute \"{x.split("=")[0].split("_", 1)[1]}\" is malformed - available attributes:')
                print(tune_attr)
                exit(1)
            rec.rec_params[x.split('=')[0]] = x.split('=')[1]


args = parser.parse_args()

headers = {'Content-Type': 'application/json',
           'Authorization': f'Bearer {get_token()}'}
if args.p:
    rec = load_preset(args.p[0])
else:
    rec = recommendation.Recommendation()
    parse()

if __name__ == '__main__':
    recommend()

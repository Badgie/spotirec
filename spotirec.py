#!/usr/bin/env python
import requests
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
from io import BytesIO
from PIL import Image
from bottle import route, run, request
from pathlib import Path

port = 8080
client_id = '466a89a53359403b82df7d714030ec5f'
client_secret = '28147de72c3549e98b1e790f3d080b85'
redirect_uri = f'http://localhost:{port}'
scope = 'user-top-read playlist-modify-public playlist-modify-private user-read-private user-read-email ' \
        'ugc-image-upload'
cache = f'{Path.home()}/.config/spotirec/spotirecoauth'
url_base = 'https://api.spotify.com/v1'
blacklist_path = f'{Path.home()}/.config/spotirec/blacklist'
tune_prefix = ['max', 'min', 'target']
tune_attr = ['acousticness', 'danceability', 'duration_ms', 'energy', 'instrumentalness', 'key', 'liveness',
             'loudness', 'mode', 'popularity', 'speechiness', 'tempo', 'time_signature', 'valence', 'popularity']

# OAuth handler
sp_oauth = oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scopes=scope, cache=cache)

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

rec_options_group = parser.add_argument_group(title='Recommendation options',
                                              description='These may only appear when creating a playlist')
rec_options_group.add_argument('-l', metavar='LIMIT', nargs=1, type=int, choices=range(1, 101),
                               help='amount of tracks to add (default: 20, max: 100)')
rec_options_group.add_argument('--tune', metavar='ATTR', nargs='+', type=str, help='specify tunable attribute(s)')

blacklist_group = parser.add_argument_group(title='Blacklisting',
                                            description='Spotirec will exit once these actions are complete')
blacklist_group.add_argument('-b', metavar='URI', nargs='+', type=str, help='blacklist track(s) and/or artist(s)')
blacklist_group.add_argument('-br', metavar='URI', nargs='+', type=str,
                             help='remove track(s) and/or artists(s) from blacklist')
blacklist_group.add_argument('-b list', action='store_true', help='print blacklist entries')

# Ensure config dir and blacklist file exists
if not os.path.isdir(f'{Path.home()}/.config/spotirec'):
    os.makedirs(f'{Path.home()}/.config/spotirec')
if not os.path.exists(blacklist_path):
    f = open(blacklist_path, 'w')
    f.close()


def authorize():
    """
    Open redirect URL in browser, and host http server on localhost.
    Function index() will be routed on said http server.
    """
    webbrowser.open(redirect_uri)
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
    url = request.url
    code = sp_oauth.parse_response_code(url)
    if code:
        token_info = sp_oauth.retrieve_access_token(code)
        access_token = token_info['access_token']

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


def get_top_list(list_type: str, top_limit: int) -> json:
    """
    Retrieve list of top artists of tracks from user's profile.
    :param list_type: type of list to retrieve; 'artists' or 'tracks'
    :param top_limit: amount of entries to retrieve; min 1, max 50
    :return: top list as json object
    """
    params = {'limit': top_limit}
    response = requests.get(f'{url_base}/me/top/{list_type}', headers=headers, params=params)
    return json.loads(response.content.decode('utf-8'))


def get_user_top_genres() -> dict:
    """
    Extract genres from user's top 50 artists and map them to their amount of occurrences
    :return: dict of genres and their count of occurrences
    """
    data = get_top_list('artists', 50)
    genres = {}
    genre_seeds = get_genre_seeds()
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
    genres = get_user_top_genres()
    sort = sorted(genres.items(), key=lambda kv: kv[1], reverse=True)
    for x in range(0, 5):
        rec.add_seed_info(data_string=sort[x][0])


def get_user_id() -> str:
    """
    Retrieve user ID from API.
    :return: user ID as a string
    """
    response = requests.get(f'{url_base}/me', headers=headers)
    return json.loads(response.content.decode('utf-8'))['id']


def create_playlist():
    """
    Creates playlist on user's account.
    """
    data = {'name': rec.playlist_name,
            'description': rec.playlist_description()}
    print('Creating playlist')
    response = requests.post(f'{url_base}/users/{get_user_id()}/playlists', json=data, headers=headers)
    rec.playlist_id = json.loads(response.content.decode('utf-8'))['id']


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
    response = requests.put(f'{url_base}/playlists/{rec.playlist_id}/images', headers=img_headers, data=img_str)
    if response.reason != 'Accepted':
        print('Failed to update playlist cover image. If you would like this functionality, you should '
              f're-authorize your access token by removing \"{cache}\".')


def add_to_playlist(tracks: list):
    """
    Add tracks to playlist.
    :param tracks: list of track URIs
    """
    data = {'uris': tracks}
    print('Adding tracks to playlist')
    requests.post(f'{url_base}/playlists/{rec.playlist_id}/tracks', headers=headers, json=data)
    add_image_to_playlist(tracks)


def get_recommendations() -> json:
    """
    Retrieve recommendations from API.
    :return: recommendations as json object
    """
    response = requests.get(f'{url_base}/recommendations', params=rec.rec_params, headers=headers)
    return json.loads(response.content.decode('utf-8'))


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
    tracks = filter_recommendations(get_recommendations())
    if len(tracks) == 0:
        print('Error: received zero tracks with your options - adjust and try again')
        exit(1)
    limit_save = rec.limit
    while True:
        if len(tracks) < limit_save:
            rec.update_limit(limit_save - len(tracks))
            tracks += filter_recommendations(get_recommendations())
        else:
            break
    create_playlist()
    add_to_playlist(tracks)
    rec.print_selection()


def print_choices(data: list, prompt=True) -> str:
    """
    Used for custom seed creation. All valid choices are printed to terminal and user is prompted
    to select. If the seed type is genres, seeds are simply added to the recommendations object.
    :param data: valid choices as a list of names
    :param prompt: whether or not to prompt user for input
    :return: user input, if seed type is artists or tracks
    """
    line = ""
    for x in range(0, round(len(data)), 3):
        try:
            line += f'{x}: {data[x]}'
            if data[x+1]:
                line += f'{" "*(40-len(data[x]))}{x+1}: {data[x+1] if len(data[x+1]) < 40 else f"{data[x+1][0:37]}.. "}'
                if data[x+2]:
                    line += f'{" "*(40-len(data[x+1]))}{x+2}: ' \
                            f'{data[x+2] if len(data[x+2]) < 40 else f"{data[x+2][0:37]}.. "}\n'
        except IndexError:
            continue
    print(line.strip('\n'))
    if prompt:
        input_string = input('Enter integer identifiers for 1-5 whitespace separated selections that you wish to '
                             'include:\n')
        if 'genres' in rec.seed_type:
            for x in input_string.split(' '):
                rec.add_seed_info(data_string=data[int(x)])
        else:
            return input_string


def add_top_seed_info(data: json):
    """
    Add artists or tracks to seed info. This function should only be used in recommendations
    that use top 5 tracks or artists.
    :param data: artists or tracks as a json object
    """
    for x in data['items']:
        rec.add_seed_info(data_dict=x)


def add_custom_seed_info(data: json):
    """
    Construct dict only containing artist or track names and IDs and prompt for selection.
    Seeds are added to recommendation object.
    :param data: valid choices as json object
    """
    choices = {}
    for x in data['items']:
        choices[x['name']] = x['id']
    selection = print_choices(list(choices.keys()))
    for x in selection.split(' '):
        rec.add_seed_info(data_dict=data['items'][int(x)])


def request_data(uri: str, data_type: str) -> json:
    """
    Requests data about an artist or a track.
    :param uri: uri for the artist or track
    :param data_type: the type of data to request; 'artists' or 'tracks'
    :return: data about artist or track as a json obj
    """
    response = requests.get(f'{url_base}/{data_type}/{uri.split(":")[2]}', headers=headers)
    return json.loads(response.content.decode('utf-8'))


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
            if 'track' in uri:
                track = request_data(uri, 'tracks')
                artists = [x['name'] for x in track['artists']]
                data['tracks'][uri] = {'name': track['name'],
                                       'uri': uri,
                                       'artists': artists}
                print(f'Added track \"{track["name"]}\" by {", ".join(str(x) for x in artists).strip(", ")}'
                      f' to your blacklist')
            elif 'artist' in uri:
                artist = request_data(uri, 'artists')
                data['artists'][uri] = {'name': artist['name'],
                                        'uri': uri}
                print(f'Added artist \"{artist["name"]}\" to your blacklist')
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
        if 'track' in uri:
            print(f'Removing track {blacklist["tracks"][uri]["name"]} by '
                  f'{", ".join(str(x) for x in blacklist["tracks"][uri]["artists"]).strip(", ")} from blacklist')
            del blacklist['tracks'][uri]
        elif 'artist' in uri:
            print(f'Removing artist \"{blacklist["artists"][uri]["name"]}\" from blacklist')
            del blacklist['artists'][uri]
        else:
            print(f'uri \"{uri}\" is either not a valid uri for a track or artist, is malformed, or is not in '
                  f'your blacklist')
            # FIXME: Remove this notice at some point
            print('Blacklist structure was recently re-done, so you may need to remove and re-do your blacklist. '
                  'Sorry!')
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


def print_user_genres_sorted(prompt=True):
    """
    Print user top genres to terminal in a formatted list.
    :param prompt: whether or not user should be prompted for input
    """
    sort = sorted(get_user_top_genres().items(), key=lambda kv: kv[1], reverse=True)
    print_choices([sort[x][0] for x in range(0, len(sort))], prompt=prompt)


def get_genre_seeds() -> json:
    """
    Retrieves available genre seeds from Spotify API.
    :return: genre seeds as a json obj
    """
    response = requests.get(f'{url_base}/recommendations/available-genre-seeds', headers=headers)
    return json.loads(response.content.decode('utf-8'))


def check_if_valid_genre(genre: str) -> bool:
    """
    Checks if input genre is in user's top genres or available genre seeds.
    :param genre: user input genre
    :return: True if genre exists, False if not
    """
    top_genres = get_user_top_genres()
    seed_genres = get_genre_seeds()['genres']
    if genre in top_genres:
        return True
    if genre in seed_genres:
        return True
    return False


def parse_custom_input(user_input: str):
    """
    Parse custom input from user.
    :param user_input: input string
    """
    for x in shlex.split(user_input):
        if 'track' in x:
            rec.add_seed_info(data_dict=request_data(x, 'tracks'))
        elif 'artist' in x:
            rec.add_seed_info(data_dict=request_data(x, 'artists'))
        elif check_if_valid_genre(x):
            rec.add_seed_info(data_string=x)
        else:
            print(f'Error: input \"{x}\" is either a malformed uri or not a valid genre')


def parse():
    """
    Parse arguments
    """
    args = parser.parse_args()
    if args.b:
        if args.b[0] == 'list':
            print_blacklist()
        else:
            add_to_blacklist(args.b)
        exit(1)
    if args.br:
        remove_from_blacklist(args.br)
        exit(1)

    if args.a:
        print('Basing recommendations off your top 5 artists')
        rec.based_on = 'top artists'
        rec.seed_type = 'artists'
        add_top_seed_info(get_top_list('artists', 5))
    elif args.t:
        print('Basing recommendations off your top 5 tracks')
        rec.based_on = 'top tracks'
        rec.seed_type = 'tracks'
        add_top_seed_info(get_top_list('tracks', 5))
    elif args.gcs:
        data = get_genre_seeds()
        rec.based_on = 'custom seed genres'
        print_choices(data['genres'])
    elif args.ac:
        data = get_top_list('artists', 50)
        rec.based_on = 'custom artists'
        rec.seed_type = 'artists'
        add_custom_seed_info(data)
    elif args.tc:
        data = get_top_list('tracks', 50)
        rec.based_on = 'custom tracks'
        rec.seed_type = 'tracks'
        add_custom_seed_info(data)
    elif args.gc:
        rec.based_on = 'custom top genres'
        print_user_genres_sorted()
    elif args.c:
        rec.based_on = 'custom mix'
        rec.seed_type = 'custom'
        print_user_genres_sorted(prompt=False)
        user_input = input('Enter a combination of 1-5 whitespace separated genres, track uris, and artist uris. '
                           '\nGenres with several words should be connected with dashes, e.g.; \"vapor-death-pop\".\n')
        parse_custom_input(user_input)
    else:
        print('Basing recommendations off your top 5 genres')
        add_top_genres_seed()

    if args.l:
        rec.update_limit(args.l[0])
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


headers = {'Content-Type': 'application/json',
           'Authorization': f'Bearer {get_token()}'}
rec = recommendation.Recommendation()
parse()

if __name__ == '__main__':
    recommend()

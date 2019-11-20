#!/usr/bin/env python
import requests
import webbrowser
import json
import time
import argparse
import os
import oauth2
from bottle import route, run, request
from pathlib import Path

port = 8080
client_id = '466a89a53359403b82df7d714030ec5f'
client_secret = '28147de72c3549e98b1e790f3d080b85'
redirect_uri = f'http://localhost:{port}'
scope = 'user-top-read playlist-modify-public playlist-modify-private user-read-private user-read-email'
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
                                 epilog="""passing no optional arguments defaults to basing recommendations off the user\'s top genres
spotirec is released under GPL-3.0 and comes with ABSOLUTELY NO WARRANTY, for details read LICENSE""")
parser.add_argument('-l', metavar='limit', nargs=1, type=int, choices=range(1, 101),
                    help='amount of tracks to add (default: 20, max: 100)')
parser.add_argument('-b', metavar='uri', nargs='+', type=str, help='blacklist track or artist uri(s)')
parser.add_argument('-b list', action='store_true', help='print blacklist entries')

# Create mutually exclusive group for recommendation types to ensure only one is given
mutex_group = parser.add_mutually_exclusive_group()
mutex_group.add_argument('-a', action='store_true', help='base recommendations on your top artists')
mutex_group.add_argument('-t', action='store_true', help='base recommendations on your top tracks')
mutex_group.add_argument('-ac', action='store_true', help='base recommendations on custom top artists')
mutex_group.add_argument('-tc', action='store_true', help='base recommendations on custom top tracks')
mutex_group.add_argument('-gc', action='store_true', help='base recommendations on custom seed genres')

parser.add_argument('--tune', metavar='attr', nargs='+', type=str, help='specify tunable attribute(s)')

# Ensure config dir and blacklist file exists
if not os.path.isdir(f'{Path.home()}/.config/spotirec'):
    os.makedirs(f'{Path.home()}/.config/spotirec')
if not os.path.exists(blacklist_path):
    f = open(blacklist_path, 'w')
    f.close()


class Recommendation:
    """
    Recommendation object
    """
    def __init__(self, t=time.localtime()):
        self.limit = 20
        self.created_at = time.ctime(time.time())
        self.based_on = 'top genres'
        self.seed = ''
        self.seed_type = 'genres'
        self.seed_info = {}
        self.rec_params = {'limit': str(self.limit)}
        self.playlist_name = f'Spotirec-{t.tm_mday}-{t.tm_mon}-{t.tm_year}'

    def playlist_description(self) -> str:
        """
        Create playlist description string to be insterted into playlist. Description contains
        date and time of creation, recommendation method, and seed.
        :return: description string
        """
        desc = f'Created by Spotirec - {self.created_at} - based on {self.based_on} - seed: '
        if 'tracks' in self.seed_type:
            seeds = ' | '.join(str(f'{x["name"]} - {", ".join(str(y) for y in x["artists"])}')
                               for x in self.seed_info.values())
            return f'{desc}{seeds}'
        else:
            seeds = ' | '.join(str(x["name"]) for x in self.seed_info.values())
            return f'{desc}{seeds}'

    def update_limit(self, limit: int):
        """
        Update playlist limit as object field and in request parameters.
        :param limit: user-defined playlist limit
        """
        self.limit = limit
        self.rec_params['limit'] = str(self.limit)

    def print_selection(self):
        """
        Print seed selection into terminal.
        """
        print('Selection:')
        for x in self.seed_info:
            print(f'\t{self.seed_info[x]}')

    def add_seed_info(self, data_dict=None, data_string=None):
        """
        Add info about a single seed to the object fields.
        :param data_dict: seed info as a dict if seed is artist or track
        :param data_string: seed info as a string if seed is genre
        """
        if 'genres' in self.seed_type:
            self.seed_info[len(self.seed_info)] = {'name': data_string}
        else:
            self.seed_info[len(self.seed_info)] = {'name': data_dict['name'],
                                                   'id': data_dict['id']}
            if 'tracks' in self.seed_type:
                self.seed_info[len(self.seed_info)-1]['artists'] = []
                for x in data_dict['artists']:
                    self.seed_info[len(self.seed_info) - 1]['artists'].append(x['name'])

    def create_seed(self):
        """
        Construct seed string to use in request and add to object field.
        """
        if 'genres' in self.seed_type:
            self.seed = ','.join(str(x['name']) for x in self.seed_info.values())
        else:
            self.seed = ','.join(str(x['id']) for x in self.seed_info.values())
        self.rec_params[f'seed_{self.seed_type}'] = self.seed


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
    for x in data['items']:
        for genre in x['genres']:
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


def create_playlist() -> str:
    """
    Creates playlist on user's account.
    :return: ID of the newly created playlist
    """
    data = {'name': rec.playlist_name,
            'description': rec.playlist_description()}
    print('Creating playlist')
    response = requests.post(f'{url_base}/users/{get_user_id()}/playlists', json=data, headers=headers)
    return json.loads(response.content.decode('utf-8'))['id']


def add_to_playlist(tracks: list, playlist: str):
    """
    Add tracks to playlist.
    :param tracks: list of track URIs
    :param playlist: playlist ID
    """
    data = {'uris': tracks}
    print('Adding tracks to playlist')
    requests.post(f'{url_base}/playlists/{playlist}/tracks', headers=headers, json=data)


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
            blacklist_artists = [x['uri'] for x in blacklist['artists']]
            blacklist_tracks = [x['uri'] for x in blacklist['tracks']]
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
    add_to_playlist(tracks, create_playlist())
    rec.print_selection()


def print_choices(data: list) -> str:
    """
    Used for custom seed creation. All valid choices are printed to terminal and user is prompted
    to select. If the seed type is genres, seeds are simply added to the recommendations object.
    :param data: valid choices as a list of names
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
            data = {'tracks': [],
                    'artists': []}
        for uri in entries:
            if 'track' in uri:
                track = request_data(uri, 'tracks')
                artists = [x['name'] for x in track['artists']]
                data['tracks'].append({'name': track['name'],
                                       'uri': uri,
                                       'artists': artists})
                print(f'Added track \"{track["name"]}\" by {", ".join(str(x) for x in artists).strip(", ")}'
                      f' to your blacklist')
            elif 'artist' in uri:
                artist = request_data(uri, 'artists')
                data['artists'].append({'name': artist['name'],
                                        'uri': artist['uri']})
                print(f'Added artist \"{artist["name"]}\" to your blacklist')
            else:
                print(f'uri \"{uri}\" is either not a valid uri for a track or artist, or is malformed and has '
                      f'not been added to the blacklist')
    with open(blacklist_path, 'w+') as file:
        file.write(json.dumps(data))


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
    elif args.gc:
        response = requests.get(f'{url_base}/recommendations/available-genre-seeds', headers=headers)
        data = json.loads(response.content.decode('utf-8'))
        rec.based_on = 'custom genres'
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
rec = Recommendation()
parse()

if __name__ == '__main__':
    recommend()

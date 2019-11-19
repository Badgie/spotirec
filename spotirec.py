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

if not os.path.isdir(f'{Path.home()}/.config/spotirec'):
    os.makedirs(f'{Path.home()}/.config/spotirec')

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

sp_oauth = oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scopes=scope, cache=cache)

parser = argparse.ArgumentParser(epilog='passing no optional arguments defaults to basing recommendations off the '
                                        'user\'s top genres')
parser.add_argument('limit', metavar='n', nargs='?', type=int, choices=range(1, 101),
                    help='amount of tracks to add (default: 20, max: 100)')
parser.add_argument('-a', action='store_true', help='base recommendations on your top artists')
parser.add_argument('-t', action='store_true', help='base recommendations on your top tracks')
parser.add_argument('-ac', action='store_true', help='base recommendations on custom top artists')
parser.add_argument('-tc', action='store_true', help='base recommendations on custom top tracks')
parser.add_argument('-gc', action='store_true', help='base recommendations on custom seed genres')
parser.add_argument('-b', metavar='uri', nargs='+', type=str, help='blacklist track or artist uri(s)')
parser.add_argument('--tune', metavar='attr', nargs='+', type=str, help='specify tunable attribute(s)')


class Recommendation:
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
        desc = f'Created by Spotirec - {self.created_at} - based on {self.based_on} - seed: '
        if 'tracks' in self.seed_type:
            seeds = ' | '.join(str(f'{x["name"]} - {", ".join(str(y) for y in x["artists"])}')
                               for x in self.seed_info.values())
            return f'{desc}{seeds}'
        else:
            seeds = ' | '.join(str(x["name"]) for x in self.seed_info.values())
            return f'{desc}{seeds}'

    def update_limit(self, limit: int):
        self.limit = limit
        self.rec_params['limit'] = str(self.limit)

    def print_selection(self):
        print('Selection:')
        for x in self.seed_info:
            print(f'\t{self.seed_info[x]}')

    def add_seed_info(self, data_dict=None, data_string=None):
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
        if 'genres' in self.seed_type:
            self.seed = ','.join(str(x['name']) for x in self.seed_info.values())
        else:
            self.seed = ','.join(str(x['id']) for x in self.seed_info.values())
        self.rec_params[f'seed_{self.seed_type}'] = self.seed


def authorize():
    webbrowser.open(redirect_uri)
    run(host='', port=port)


@route('/')
def index() -> str:
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
    creds = sp_oauth.get_credentials()
    if creds:
        return creds['access_token']
    else:
        authorize()
        exit(1)


def get_top_list(list_type: str, top_limit: int) -> json:
    params = {'limit': top_limit}
    response = requests.get(f'{url_base}/me/top/{list_type}', headers=headers, params=params)
    return json.loads(response.content.decode('utf-8'))


def add_top_genres_seed():
    data = get_top_list('artists', 50)
    genres = {}
    for x in data['items']:
        for genre in x['genres']:
            if genre in genres.keys():
                genres[genre] += 1
            else:
                genres[genre] = 1
    sort = sorted(genres.items(), key=lambda kv: kv[1], reverse=True)
    for x in range(0, 5):
        rec.add_seed_info(data_string=sort[x][0])


def get_user_id() -> str:
    response = requests.get(f'{url_base}/me', headers=headers)
    return json.loads(response.content.decode('utf-8'))['id']


def create_playlist() -> str:
    data = {'name': rec.playlist_name,
            'description': rec.playlist_description()}
    print('Creating playlist')
    response = requests.post(f'{url_base}/users/{get_user_id()}/playlists', json=data, headers=headers)
    return json.loads(response.content.decode('utf-8'))['id']


def add_to_playlist(tracks: list, playlist: str):
    data = {'uris': tracks}
    print('Adding tracks to playlist')
    requests.post(f'{url_base}/playlists/{playlist}/tracks', headers=headers, json=data)


def get_recommendations() -> json:
    response = requests.get(f'{url_base}/recommendations', params=rec.rec_params, headers=headers)
    return json.loads(response.content.decode('utf-8'))


def filter_recommendations(data: json) -> list:
    tracks = []
    if not os.path.exists(blacklist_path):
        f = open(blacklist_path, 'w')
        f.close()
    with open(blacklist_path, 'r+') as file:
        try:
            blacklist = json.loads(file.read())
            for x in data['tracks']:
                artists = [y for y in x['artists'] if y['uri'] in blacklist['artists']]
                if len(artists) > 0:
                    continue
                elif x['uri'] in blacklist['tracks']:
                    continue
                else:
                    tracks.append(x['uri'])
        except json.decoder.JSONDecodeError:
            tracks = [x['uri'] for x in data['tracks']]
    return tracks


def recommend():
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
    for x in data['items']:
        rec.add_seed_info(data_dict=x)


def add_custom_seed_info(data: json):
    choices = {}
    for x in data['items']:
        choices[x['name']] = x['id']
    selection = print_choices(list(choices.keys()))
    for x in selection.split(' '):
        rec.add_seed_info(data_dict=data['items'][int(x)])


def parse():
    args = parser.parse_args()
    if args.b:
        if not os.path.exists(blacklist_path):
            f = open(blacklist_path, 'w')
            f.close()
        with open(blacklist_path, 'r') as file:
            try:
                data = json.loads(file.read())
            except json.decoder.JSONDecodeError:
                data = {'tracks': [],
                        'artists': []}
            for uri in args.b:
                if 'track' in uri:
                    data['tracks'].append(uri)
                elif 'artist' in uri:
                    data['artists'].append(uri)
                else:
                    print(f'uri \"{uri}\" is either not a valid uri for a track or artist, or is malformed and has '
                          f'not been added to the blacklist')
        with open(blacklist_path, 'w+') as file:
            file.write(json.dumps(data))
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

    if args.limit:
        rec.update_limit(args.limit)
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

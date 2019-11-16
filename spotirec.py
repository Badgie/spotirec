import requests
import webbrowser
import json
import time
import argparse
from bottle import route, run, request
from spotipy import oauth2
from pathlib import Path

port = 8080
client_id = '466a89a53359403b82df7d714030ec5f'
client_secret = '28147de72c3549e98b1e790f3d080b85'
redirect_uri = f'http://localhost:{port}'
scope = 'user-top-read playlist-modify-public playlist-modify-private user-read-private user-read-email'
cache = f'{Path.home()}/.spotirecoauth'
limit = 20

sp_oauth = oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scope=scope, cache_path=cache)

parser = argparse.ArgumentParser()
parser.add_argument('limit', metavar='n', nargs='?', type=int, help='amount of tracks to add (default: 20, max: 100)')


def authorize():
    webbrowser.open(redirect_uri)
    run(host='', port=port)


@route('/')
def index() -> str:
    access_token = ""
    url = request.url
    code = sp_oauth.parse_response_code(url)
    if code:
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info['access_token']

    if access_token:
        return "<span>Successfully retrieved OAuth token. You may close this tab and start using Spotisave.</span>"
    else:
        return f"<a href='{sp_oauth.get_authorize_url()}'>Login to Spotify</a>"


def get_token() -> str:
    token_info = sp_oauth.get_cached_token()
    if token_info:
        if (time.time() + 5) > int(sp_oauth.get_cached_token()['expires_at']):
            refresh_token()
        return sp_oauth.get_cached_token()['access_token']
    else:
        authorize()
        exit(1)


def refresh_token():
    print('OAuth token invalid, refreshing...')
    sp_oauth.refresh_access_token(sp_oauth.get_cached_token()['refresh_token'])


def get_top_list(list_type: str, top_limit: int) -> json:
    params = {'limit': top_limit}
    response = requests.get(f'https://api.spotify.com/v1/me/top/{list_type}', headers=headers, params=params)
    return json.loads(response.content.decode('utf-8'))


def get_genre_string() -> str:
    data = get_top_list('artists', 50)
    genres = {}
    for x in data['items']:
        for genre in x['genres']:
            if genre in genres.keys():
                genres[genre] += 1
            else:
                genres[genre] = 1
    sort = sorted(genres.items(), key=lambda kv: kv[1], reverse=True)
    genre_string = ""
    for x in range(0, 5):
        genre_string += f'{sort[x][0]},'
    return genre_string.strip(',')


def generate_playlist_name() -> str:
    t = time.localtime()
    return f'Spotirec-{t.tm_mday}-{t.tm_mon}-{t.tm_year}'


def get_user_id() -> str:
    response = requests.get('https://api.spotify.com/v1/me', headers=headers)
    return json.loads(response.content.decode('utf-8'))['id']


def create_playlist() -> str:
    data = {'name': generate_playlist_name(),
            'description': f'Created by Spotirec - {time.ctime(time.time())}'}
    print('Creating playlist')
    response = requests.post(f'https://api.spotify.com/v1/users/{get_user_id()}/playlists', json=data, headers=headers)
    return json.loads(response.content.decode('utf-8'))['id']


def add_to_playlist(tracks: list, playlist: str):
    data = {'uris': tracks}
    print('Adding tracks to playlist')
    requests.post(f'https://api.spotify.com/v1/playlists/{playlist}/tracks', headers=headers, json=data)


def get_recommendations():
    params = {'seed_genres': get_genre_string(),
              'limit': limit}
    print('Getting recommendations')
    response = requests.get('https://api.spotify.com/v1/recommendations', params=params, headers=headers)
    data = json.loads(response.content.decode('utf-8'))
    tracks = []
    for item in data['tracks']:
        tracks.append(item['uri'])
    add_to_playlist(tracks, create_playlist())


headers = {'Content-Type': 'application/json',
           'Authorization': f'Bearer {get_token()}'}

args = parser.parse_args()

if args.limit:
    if args.limit > 100:
        print('Limit value must be below 100')
        exit(1)
    elif args.limit < 1:
        print('Limit value must be above 0')
        exit(1)
    limit = args.limit

if __name__ == '__main__':
    get_recommendations()

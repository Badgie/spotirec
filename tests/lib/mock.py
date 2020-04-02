URL_MAP = {}


def route(path, methods):
    def decorator(f):
        global URL_MAP
        URL_MAP[path] = {'func': f, 'methods': methods}
        return f
    return decorator


class MockAPI:
    """
    Mock API for unit tests. URL_BASE in api.py should be set to an empty string before usage.
    Keep in mind that,
        - all return values are static
        - user ID is always "testuser"
        - modifications made to a playlist should always be playlist ID "testplaylist"
        - a singular track is always "testtrack"
        - a singular artist is always "testartist"
    """
    ACCEPTED_TOKEN = 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f'
    ACCEPTED_BASE64 = 'Y2xpZW50X2lkOmNsaWVudF9zZWNyZXQ='
    NO_SEND_REFRESH = '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f'
    SEND_REFRESH = 'no_refresh'
    USER = '{"id": "testuser", "external_urls": {"spotify": "/user/testuser"}, "type": "user"}'
    TOP_ARTISTS = '{"items": [{"name": "frankie0", "uri": "spotify:artist:testid0", "type": ' \
                  '"artist", "genres": ["pop",  "metal", "vapor-death-pop"], "id": "testid0"},' \
                  '{"name": "frankie1", "uri": "spotify:artist:testid1", "type": "artist", ' \
                  '"genres": ["pop", "vapor-death-pop", "hip-hop"],  "id": "testid1"},' \
                  '{"name": "frankie2", "uri": "spotify:artist:testid2", "type": "artist", ' \
                  '"genres": ["hip-hop", "holidays", "vapor"], "id": "testid2"},' \
                  '{"name": "frankie3", "uri": "spotify:artist:testid3", "type": "artist", ' \
                  '"genres": ["vapor-death-jazz", "invalid-genre", "siesta"], "id": "testid3"},' \
                  '{"name": "frankie4", "uri": "spotify:artist:testid4", "type": "artist", ' \
                  '"genres": ["metalcore", "making-up-genres-is-hard"], "id": "testid4"}]}'
    ARTIST = '{"name": "frankie0", "uri": "spotify:artist:testartist", "type": "artist", ' \
             '"genres": ["pop", "metal", "vapor-death-pop"], "id": "testartist"}'

    TOP_TRACKS = '{"items": [{"name": "track0", "uri": "spotify:track:testid0", "type": "track",' \
                 ' "id": "testid0", "artists": [{"name": "frankie0", "uri": ' \
                 '"spotify:artist:testid0", "type": "artist", "genres": ["pop", "metal", ' \
                 '"vapor-death-pop"]}, {"name": "frankie1", "uri": "spotify:artist:testid1", ' \
                 '"type": "artist", "genres": ["pop", "vapor-death-pop", "hip-hop"]}]},' \
                 '{"name": "track1", "uri": "spotify:track:testid1", "type": "track", "id": ' \
                 '"testid1", "artists": [{"name": "frankie1", "uri": "spotify:artist:testid1", ' \
                 '"type": "artist", "genres": ["pop", "vapor-death-pop", "hip-hop"]}]},' \
                 '{"name": "track2", "uri": "spotify:track:testid2", "type": "track", "id": ' \
                 '"testid2", "artists": [{"name": "frankie2", "uri": "spotify:artist:testid2", ' \
                 '"type": "artist", "genres": ["hip-hop", "holidays", "vapor"]}, {"name": ' \
                 '"frankie1", "uri": "spotify:artist:testid1", "type": "artist", "genres": ' \
                 '["pop", "vapor-death-pop", "hip-hop"]}]},' \
                 '{"name": "track3", "uri": "spotify:track:testid3", "type": "track", "id": ' \
                 '"testid3", "artists": [{"name": "frankie3", "uri": "spotify:artist:testid3", ' \
                 '"type": "artist", "genres": ["vapor-death-jazz", "invalid-genre", "siesta"]}, ' \
                 '{"name": "frankie1", "uri": "spotify:artist:testid1", "type": "artist", ' \
                 '"genres": ["pop", "vapor-death-pop", "hip-hop"]}]},' \
                 '{"name": "track4", "uri": "spotify:track:testid4", "type": "track", "id": ' \
                 '"testid4", "artists": [{"name": "frankie4", "uri": "spotify:artist:testid4", ' \
                 '"type": "artist", "genres": ["metalcore", "making-up-genres-is-hard"]}, ' \
                 '{"name": "frankie3", "uri": "spotify:artist:testid3", ' \
                 '"type": "artist", "genres": ["vapor-death-jazz", "invalid-genre", "siesta"]}]}]}'
    TRACK = '{"name": "track0", "uri": "spotify:track:testtrack", "type": "track", "id": ' \
            '"testtrack", "artists": [{"name": "frankie0", "uri": "spotify:artist:testartist", ' \
            '"type": "artist", "genres": ["pop", "metal", "vapor-death-pop"]}, {"name": ' \
            '"frankie1", "uri": "spotify:artist:testartist", "type": "artist", "genres": ' \
            '["pop", "vapor-death-pop", "hip-hop"]}], "album": {"uri": "spotify:album:testid0", ' \
            '"release_date": "never lol", "name": "cool album"}, "popularity": -3}'
    REC_TRACKS = '{"tracks": [{"name": "track0", "uri": "spotify:track:testid0", "type": ' \
                 '"track", "id": "testid0", "artists": [{"name": "frankie0", "uri": ' \
                 '"spotify:artist:testid0", "type": "artist", "genres": ["pop", "metal", ' \
                 '"vapor-death-pop"]}, {"name": "frankie1", "uri": "spotify:artist:testid1", ' \
                 '"type": "artist", "genres": ["pop", "vapor-death-pop", "hip-hop"]}]},' \
                 '{"name": "track1", "uri": "spotify:track:testid1", "type": "track", "id": ' \
                 '"testid1", "artists": [{"name": "frankie1", "uri": "spotify:artist:testid1", ' \
                 '"type": "artist", "genres": ["pop", "vapor-death-pop", "hip-hop"]}]},' \
                 '{"name": "track2", "uri": "spotify:track:testid2", "type": "track", "id": ' \
                 '"testid2", "artists": [{"name": "frankie2", "uri": "spotify:artist:testid2", ' \
                 '"type": "artist", "genres": ["hip-hop", "holidays", "vapor"]}, {"name": ' \
                 '"frankie1", "uri": "spotify:artist:testid1", "type": "artist", "genres": ' \
                 '["pop", "vapor-death-pop", "hip-hop"]}]},' \
                 '{"name": "track3", "uri": "spotify:track:testid3", "type": "track", "id": ' \
                 '"testid3", "artists": [{"name": "frankie3", "uri": "spotify:artist:testid3", ' \
                 '"type": "artist", "genres": ["vapor-death-jazz", "invalid-genre", "siesta"]}, ' \
                 '{"name": "frankie1", "uri": "spotify:artist:testid1", "type": "artist", ' \
                 '"genres": ["pop", "vapor-death-pop", "hip-hop"]}]},' \
                 '{"name": "track4", "uri": "spotify:track:testid4", "type": "track", "id": ' \
                 '"testid4", "artists": [{"name": "frankie4", "uri": "spotify:artist:testid4", ' \
                 '"type": "artist", "genres": ["metalcore", "making-up-genres-is-hard"]}, ' \
                 '{"name": "frankie3", "uri": "spotify:artist:testid3", ' \
                 '"type": "artist", "genres": ["vapor-death-jazz", "invalid-genre", "siesta"]}]}]}'
    PLAYLIST_TRUE = '{"id": "testplaylist", "name": "testplaylist", "type": "playlist", "uri": ' \
                    '"spotify:playlist:testid", "tracks": [], "public": true}'
    PLAYLIST_FALSE = '{"id": "testplaylist", "name": "testplaylist", "type": "playlist", "uri": ' \
                     '"spotify:playlist:testid", "tracks": [], "public": false}'
    GENRES = '{"genres": ["metal", "metalcore", "pop", "vapor-death-pop", "holidays"]}'
    DEVICES = '{"devices": [{"id": "testid0", "name": "test0", "type": "fridge"}, ' \
              '{"id": "testid1", "name": "test1", "type": "microwave"}]}'
    AUDIO_FEATURES = '{"duration_ms": 23984723, "key": 10, "mode": 0, "time_signature": 10, ' \
                     '"acousticness": 0.99, "danceability": 0.01, "energy": 0.7, ' \
                     '"instrumentalness": 0.001, "liveness": 0.8, "loudness": -50.0, ' \
                     '"speechiness": 0.1, "valence": 0.001, "tempo": 70.0, "id": "testid0", ' \
                     '"uri": "spotify:track:testid0", "type": "audio_features"}'
    PLAYER = '{"timestamp": 0, "device": {"id": "testid0", "name": "test0", "type": "fridge"}, ' \
             '"item": {"name": "track0", "uri": "spotify:track:testtrack", "type": "track", ' \
             '"id": "testtrack", "artists": [{"name": "frankie0", "uri": ' \
             '"spotify:artist:testartist", "type": "artist", "genres": ["pop", "metal", ' \
             '"vapor-death-pop"]}, {"name": "frankie1", "uri": "spotify:artist:testartist", ' \
             '"type": "artist", "genres": ["pop", "vapor-death-pop", "hip-hop"]}], "album": ' \
             '{"uri": "spotify:album:testid0", ' \
             '"release_date": "never lol", "name": "cool album"}, "popularity": -3}}'
    TOKEN = '{"access_token": "f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694b' \
            'f0f", "token_type": "Bearer", "expires_in": 3600, ' \
            '"scope": "user-modify-playback-state ugc-image-upload user-library-modify", ' \
            '"refresh_token": "737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f"}'
    TOKEN_NO_REFRESH = '{"access_token": "f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5' \
                       'bf694bf0f", "token_type": "Bearer", "expires_in": 3600, ' \
                       '"scope": "user-modify-playback-state ugc-image-upload user-library-modify"}'

    def get(self, url, **kwargs):
        error = self.test_validity(url, kwargs, 'GET')
        headers = kwargs.pop('headers')
        data = kwargs.pop('data', None)
        json = kwargs.pop('json', None)
        params = kwargs.pop('params', None)
        if error is None:
            return URL_MAP[url]['func'](self, 'GET', headers, data, json, params)
        else:
            return error

    def put(self, url, **kwargs):
        error = self.test_validity(url, kwargs, 'PUT')
        headers = kwargs.pop('headers')
        data = kwargs.pop('data', None)
        json = kwargs.pop('json', None)
        params = kwargs.pop('params', None)
        if error is None:
            return URL_MAP[url]['func'](self, 'PUT', headers, data, json, params)
        else:
            return error

    def post(self, url, **kwargs):
        error = self.test_validity(url, kwargs, 'POST')
        headers = kwargs.pop('headers')
        data = kwargs.pop('data', None)
        json = kwargs.pop('json', None)
        params = kwargs.pop('params', None)
        if error is None:
            return URL_MAP[url]['func'](self, 'POST', headers, data, json, params)
        else:
            return error

    def delete(self, url, **kwargs):
        error = self.test_validity(url, kwargs, 'DELETE')
        headers = kwargs.pop('headers')
        data = kwargs.pop('data', None)
        json = kwargs.pop('json', None)
        params = kwargs.pop('params', None)
        if error is None:
            return URL_MAP[url]['func'](self, 'DELETE', headers, data, json, params)
        else:
            return error

    def test_validity(self, url: str, kwargs: dict, request_type: str):
        if not kwargs['headers']:
            return MockResponse(401, 'Unauthorized (missing headers)', request_type, {}, url)

        if kwargs['headers']['Authorization'] != f'Bearer {self.ACCEPTED_TOKEN}':
            if kwargs['headers']['Authorization'] != f'Basic {self.ACCEPTED_BASE64}':
                return MockResponse(401, 'Unauthorized (invalid token)', request_type,
                                    kwargs['headers'], url)

        try:
            if not any(m == request_type for m in URL_MAP[url]['methods']):
                return MockResponse(403, 'Forbidden (invalid endpoint)', request_type,
                                    kwargs['headers'], url)

            return None
        except (KeyError, AssertionError):
            print('Error: invalid URL')
            return MockResponse(404, 'Not Found', 'GET', kwargs['headers'], url)

    @route('/me', ['GET'])
    def user(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/me', content=self.USER)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/me')

    @route('/me/top/artists', ['GET'])
    def top_artists(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/me/top/artists',
                                content=self.TOP_ARTISTS)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/me/top/artists')

    @route('/me/top/tracks', ['GET'])
    def top_tracks(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/me/top/tracks',
                                content=self.TOP_TRACKS)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/me/top/tracks')

    @route('/users/testuser/playlists', ['POST'])
    def user_playlists(self, method, headers, data, json, params):
        if method == 'POST':
            return MockResponse(201, 'Created', method, headers, '/users/testuser/playlists',
                                content=self.PLAYLIST_TRUE)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/users/testuser/playlists')

    @route('/playlists/testplaylist/images', ['PUT'])
    def playlist_image(self, method, headers, data, json, params):
        if method == 'PUT':
            return MockResponse(202, 'Accepted', method, headers, '/playlists/testplaylist/images')
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/playlists/testplaylist/images')

    @route('/playlists/testplaylist', ['PUT', 'GET'])
    def playlist(self, method, headers, data, json, params):
        if method == 'PUT':
            return MockResponse(200, 'OK', method, headers, '/playlists/testplaylist')
        elif method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/playlists/testplaylist',
                                content=self.PLAYLIST_TRUE)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/playlists/testplaylist')

    @route('/playlists/testplaylistprivate', ['PUT', 'GET'])
    def playlist_private(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/playlists/testplaylistprivate',
                                content=self.PLAYLIST_FALSE)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/playlists/testplaylistprivate')

    @route('/playlists/testplaylist/tracks', ['POST', 'PUT', 'DELETE'])
    def playlist_tracks(self, method, headers, data, json, params):
        if method == 'DELETE':
            return MockResponse(200, 'OK', method, headers, '/playlists/testplaylist/tracks')
        elif method == 'POST':
            return MockResponse(201, 'Created', method, headers, '/playlists/testplaylist/tracks')
        elif method == 'PUT':
            return MockResponse(201, 'Created', method, headers, '/playlists/testplaylist/tracks')
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/playlists/testplaylist/tracks')

    @route('/recommendations', ['GET'])
    def recommendations(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/recommendations',
                                content=self.REC_TRACKS)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/recommendations')

    @route('/artists/testartist', ['GET'])
    def request_artist(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/artists/testartist',
                                content=self.ARTIST)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/artists/testartist')

    @route('/tracks/testtrack', ['GET'])
    def request_track(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/tracks/testtrack', content=self.TRACK)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/artists/testtrack')

    @route('/recommendations/available-genre-seeds', ['GET'])
    def genre_seeds(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers,
                                '/recommendations/available-genre-seeds', content=self.GENRES)
        else:
            return MockResponse(403, 'Forbidden', method, headers,
                                '/recommendations/available-genre-seeds')

    @route('/me/player/devices', ['GET'])
    def devices(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/me/player/devices',
                                content=self.DEVICES)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/me/player/devices')

    @route('/me/player/play', ['PUT'])
    def play(self, method, headers, data, json, params):
        if method == 'PUT':
            return MockResponse(204, 'No Content', method, headers, '/me/player/play')
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/me/player/play')

    @route('/me/tracks', ['PUT', 'DELETE'])
    def saved_tracks(self, method, headers, data, json, params):
        if method == 'PUT':
            return MockResponse(200, 'OK', method, headers, '/me/tracks')
        elif method == 'DELETE':
            return MockResponse(200, 'OK', method, headers, '/me/tracks')
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/me/tracks')

    @route('/me/player', ['GET', 'PUT'])
    def player_status(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/me/player', content=self.PLAYER)
        elif method == 'PUT':
            return MockResponse(204, 'No Content', method, headers, '/me/player')
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/me/player')

    @route('/audio-features/testtrack', ['GET'])
    def audio_features(self, method, headers, data, json, params):
        if method == 'GET':
            return MockResponse(200, 'OK', method, headers, '/audio-features/testtrack',
                                content=self.AUDIO_FEATURES)
        else:
            return MockResponse(403, 'Forbidden', method, headers, '/audio-features/testtrack')

    @route('/api/token', ['POST'])
    def token(self, method, headers, data, json, params):
        if data:
            if method == 'POST':
                refresh = data.pop('refresh_token', None)
                code = data.pop('code', None)
                if refresh:
                    if refresh == self.NO_SEND_REFRESH:
                        return MockResponse(200, 'OK', method, headers, '/api/token',
                                            content=self.TOKEN_NO_REFRESH)
                    elif refresh == self.SEND_REFRESH:
                        return MockResponse(200, 'OK', method, headers, '/api/token',
                                            content=self.TOKEN)
                elif code:
                    return MockResponse(200, 'OK', method, headers, '/api/token',
                                        content=self.TOKEN)
        return MockResponse(403, 'Forbidden', method, headers, '/api/token')


class MockResponse:
    def __init__(self, status_code: int, reason: str, request: str, headers: dict, url: str,
                 content=None):
        self.status_code = status_code
        self.reason = reason
        self.request = request
        self.headers = headers
        self.url = url
        self.content = content if content is None else bytes(content.encode('utf-8'))


class MockRequest:
    def __init__(self, url: str):
        self.url = url


class MockArgs:
    def __init__(self, **kwargs):
        self.a = kwargs.pop('a', None)
        self.ac = kwargs.pop('ac', False)
        self.add_to = kwargs.pop('add_to', None)
        self.b = kwargs.pop('b', None)
        self.bc = kwargs.pop('bc', None)
        self.br = kwargs.pop('br', None)
        self.c = kwargs.pop('c', False)
        self.debug = kwargs.pop('debug', False)
        self.gc = kwargs.pop('gc', False)
        self.gcs = kwargs.pop('gcs', False)
        self.l = kwargs.pop('l', None)
        self.load_preset = kwargs.pop('load_preset', None)
        self.log = kwargs.pop('log', False)
        self.n = kwargs.pop('n', 5)
        self.play = kwargs.pop('play', None)
        self.preserve = kwargs.pop('preserve', False)
        self.print = kwargs.pop('print', None)
        self.quiet = kwargs.pop('quiet', False)
        self.remove_devices = kwargs.pop('remove_devices', None)
        self.remove_from = kwargs.pop('remove_from', None)
        self.remove_playlists = kwargs.pop('remove_playlists', None)
        self.remove_presets = kwargs.pop('remove_presets', None)
        self.s = kwargs.pop('s', False)
        self.save_device = kwargs.pop('save_device', False)
        self.save_playlist = kwargs.pop('save_playlist', False)
        self.save_preset = kwargs.pop('save_preset', None)
        self.sr = kwargs.pop('sr', False)
        self.suppress_warnings = kwargs.pop('suppress_warnings', False)
        self.t = kwargs.pop('t', None)
        self.tc = kwargs.pop('tc', False)
        self.track_features = kwargs.pop('track_features', None)
        self.transfer_playback = kwargs.pop('transfer_playback', None)
        self.tune = kwargs.pop('tune', None)
        self.verbose = kwargs.pop('verbose', False)


class MockWebbrowser:
    def __init__(self):
        self.url = None

    def open(self, url: str):
        self.url = url

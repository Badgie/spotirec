from tests.lib import ordered, mock, SpotirecTestCase, runner
from spotirec import api as sp_api, conf, log
import os
import sys


class TestAPI(SpotirecTestCase):
    """
    Running tests for api.py
    """

    @classmethod
    def setUpClass(cls) -> None:
        """
        Setup any necessary data or states before any tests in this class is run
        """
        if runner.verbosity > 0:
            super(TestAPI, cls).setUpClass()
            print(f'file:/{__file__}\n')
        cls.stdout_preserve = sys.__stdout__
        cls.api = sp_api.API()
        cls.api.URL_BASE = ''
        cls.test_log = 'tests/fixtures/test-api'
        sp_api.requests = mock.MockAPI()
        cls.logger = log.Log()
        cls.logger.LOG_PATH = 'tests/fixtures'
        cls.api.set_logger(cls.logger)
        cls.config = conf.Config()
        cls.config.CONFIG_DIR = 'tests/fixtures'
        cls.config.CONFIG_FILE = 'test.conf'
        cls.config.set_logger(cls.logger)
        cls.api.set_conf(cls.config)
        cls.headers = {'Content-Type': 'application/json',
                       'Authorization': f'Bearer {cls.config.get_oauth()["access_token"]}'}
        cls.img_headers = {'Content-Type': 'image/jpeg',
                           'Authorization': f'Bearer {cls.config.get_oauth()["access_token"]}'}

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Clear or resolve any necessary data or states after all tests in this class are run
        """
        if runner.verbosity > 0:
            super(TestAPI, cls).tearDownClass()

    def setUp(self):
        """
        Setup any necessary data or states before each test is run
        """
        self.logger.set_level(log.INFO)
        self.log_file = open(self.test_log, 'w')
        sys.stdout = self.log_file

    def tearDown(self):
        """
        Clear or resolve any necessary data or states after each test is run
        """
        self.log_file.close()
        sys.stdout = self.stdout_preserve
        os.remove(self.test_log)
        self.api.set_conf(self.config)

    @ordered
    def test_set_conf(self):
        """
        Testing set_conf()
        """
        expected = conf.Config()
        self.api.set_conf(expected)
        self.assertEqual(expected, self.api.CONF)

    @ordered
    def test_error_handle_success(self):
        """
        Testing error_handle()
        """
        response = mock.MockResponse(200, 'success', 'success', {'success': 'yes lol'}, 'https://success.test')
        self.api.error_handle('test', 200, 'TEST', response=response)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertEqual(stdout, '')

    @ordered
    def test_error_handle_error(self):
        """
        Testing error_handle() with error (non-200)
        """
        response = mock.MockResponse(400, 'error', 'error', {'success': 'no lol'}, 'https://error.test')
        expected = 'TEST request for test failed with status code 400 (expected 200). Reason: error'
        self.assertRaises(SystemExit, self.api.error_handle, request_domain='test', expected_code=200,
                          request_type='TEST', response=response)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_error_handle_401(self):
        """
        Testing error_handle() with error (401)
        """
        response = mock.MockResponse(401, 'error', 'error', {'success': 'no lol'}, 'https://error.test')
        expected = 'this may be because this is a new function, and additional authorization is required - try ' \
                   'reauthorizing and try again.'
        self.assertRaises(SystemExit, self.api.error_handle, request_domain='test', expected_code=200,
                          request_type='TEST', response=response)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_get_top_list_artists(self):
        """
        Testing get_top_list() (artists)
        """
        artists = self.api.get_top_list('artists', 20, self.headers)
        self.assertIn('items', artists.keys())
        self.assertTrue(any(x['name'] == 'frankie3' for x in artists['items']))
        self.assertTrue(any(x['uri'] == 'spotify:artist:testid1' for x in artists['items']))

    @ordered
    def test_get_top_list_tracks(self):
        """
        Testing get_top_list() (tracks)
        """
        tracks = self.api.get_top_list('tracks', 20, self.headers)
        self.assertIn('items', tracks.keys())
        self.assertTrue(any(x['name'] == 'track4' for x in tracks['items']))
        self.assertTrue(any(x['uri'] == 'spotify:track:testid2' for x in tracks['items']))

    @ordered
    def test_get_user_id(self):
        """
        Testing get_user_id()
        """
        iden = self.api.get_user_id(self.headers)
        self.assertEqual(iden, 'testuser')

    @ordered
    def test_create_playlist_no_cache(self):
        """
        Testing create_playlist() without caching
        """
        iden = self.api.create_playlist('test', 'test-description', self.headers)
        self.assertEqual(iden, 'testplaylist')

    @ordered
    def test_create_playlist_cached(self):
        """
        Testing create_playlist() with caching
        """
        iden = self.api.create_playlist('test', 'test-description', self.headers, cache_id=True)
        self.assertEqual(iden, 'testplaylist')
        playlists = self.config.get_playlists()
        self.assertIn('spotirec-default', playlists.keys())
        self.assertEqual(playlists['spotirec-default']['uri'], 'spotify:playlist:testid')
        self.config.remove_playlist('spotirec-default')

    @ordered
    def test_upload_image(self):
        """
        Testing upload_image()
        """
        # should not raise sysexit
        self.api.upload_image('testplaylist', 'base64string==', self.img_headers)

    @ordered
    def test_add_to_playlist(self):
        """
        Testing add_to_playlist()
        """
        # should not raise sysexit
        self.api.add_to_playlist(['spotify:track:trackid0', 'spotify:track:trackid1', 'spotify:track:trackid2'],
                                 'testplaylist', self.headers)

    @ordered
    def test_get_recommendations(self):
        """
        Testing get_recommendations()
        """
        recs = self.api.get_recommendations({}, self.headers)
        self.assertIn('tracks', recs.keys())
        self.assertTrue(any(x['name'] == 'track4' for x in recs['tracks']))
        self.assertTrue(any(x['uri'] == 'spotify:track:testid2' for x in recs['tracks']))

    @ordered
    def test_request_data_artist(self):
        """
        Testing request_data() (artist)
        """
        artist = self.api.request_data('spotify:artist:testartist', 'artists', self.headers)
        self.assertEqual('frankie0', artist['name'])
        self.assertEqual('spotify:artist:testartist', artist['uri'])
        self.assertListEqual(['pop', 'metal', 'vapor-death-pop'], artist['genres'])

    @ordered
    def test_request_data_track(self):
        """
        Testing request_data() (track)
        """
        track = self.api.request_data('spotify:track:testtrack', 'tracks', self.headers)
        self.assertEqual('track0', track['name'])
        self.assertEqual('spotify:track:testtrack', track['uri'])
        self.assertEqual('testtrack', track['id'])

    @ordered
    def test_get_genre_seeds(self):
        """
        Testing get_genre_seeds()
        """
        seeds = self.api.get_genre_seeds(self.headers)
        self.assertIn('genres', seeds.keys())
        self.assertIn('vapor-death-pop', seeds['genres'])
        self.assertIn('pop', seeds['genres'])
        self.assertEqual(seeds['genres'], ['metal', 'metalcore', 'pop', 'vapor-death-pop', 'holidays'])

    @ordered
    def test_get_available_devices(self):
        """
        Testing get_available_devices()
        """
        devices = self.api.get_available_devices(self.headers)
        self.assertIn('devices', devices.keys())
        self.assertIn({'id': 'testid0', 'name': 'test0', 'type': 'fridge'}, devices['devices'])

    @ordered
    def test_play(self):
        """
        Testing play()
        """
        # should not raise sysexit
        self.api.play('testid0', 'spotify:playlist:testplaylist', self.headers)

    @ordered
    def test_get_current_track(self):
        """
        Testing get_current_track()
        """
        uri = self.api.get_current_track(self.headers)
        self.assertEqual('spotify:track:testtrack', uri)

    @ordered
    def test_get_current_artists(self):
        """
        Testing get_current_artists()
        """
        artists = self.api.get_current_artists(self.headers)
        self.assertListEqual(['spotify:artist:testartist', 'spotify:artist:testartist'], artists)

    @ordered
    def test_like_track(self):
        """
        Testing like_track()
        """
        # should not raise sysexit
        self.api.like_track(self.headers)

    @ordered
    def test_unlike_track(self):
        """
        Testing unlike_track()
        """
        # should not raise sysexit
        self.api.unlike_track(self.headers)

    @ordered
    def test_update_playlist_details(self):
        """
        Testing update_playlist_details()
        """
        # should not raise sysexit
        self.api.update_playlist_details('new-name', 'new-description', 'testplaylist', self.headers)

    @ordered
    def test_replace_playlist_tracks(self):
        """
        Testing replace_playlist_tracks()
        """
        # should not raise sysexit
        self.api.replace_playlist_tracks('testplaylist', ['spotify:track:testid0', 'spotify:track:testid1'],
                                         self.headers)

    @ordered
    def test_get_playlist(self):
        """
        Testing get_playlist()
        """
        playlist = self.api.get_playlist(self.headers, 'testplaylist')
        self.assertEqual('testplaylist', playlist['id'])
        self.assertEqual('testplaylist', playlist['name'])
        self.assertEqual('spotify:playlist:testid', playlist['uri'])

    @ordered
    def test_remove_from_playlist(self):
        """
        Testing remove_from_playlist()
        """
        # should not raise sysexit
        self.api.remove_from_playlist(['spotify:track:testid0', 'spotify:track:testid1'], 'testplaylist', self.headers)

    @ordered
    def test_get_audio_features(self):
        """
        Testing get_audio_features()
        """
        features = self.api.get_audio_features('testtrack', self.headers)
        self.assertEqual(23984723, features['duration_ms'])
        self.assertEqual(10, features['key'])
        self.assertEqual(0, features['mode'])
        self.assertEqual(10, features['time_signature'])
        self.assertEqual(0.99, features['acousticness'])
        self.assertEqual(0.01, features['danceability'])
        self.assertEqual(0.7, features['energy'])
        self.assertEqual(0.001, features['instrumentalness'])
        self.assertEqual(0.8, features['liveness'])
        self.assertEqual(-50.0, features['loudness'])
        self.assertEqual(0.1, features['speechiness'])
        self.assertEqual(0.001, features['valence'])
        self.assertEqual(70.0, features['tempo'])
        self.assertEqual('testid0', features['id'])
        self.assertEqual('spotify:track:testid0', features['uri'])

    @ordered
    def test_check_if_playlist_exists_true(self):
        """
        Testing check_if_playlist_exists() (true)
        """
        self.assertTrue(self.api.check_if_playlist_exists('testplaylist', self.headers))

    @ordered
    def test_check_if_playlist_exists_false(self):
        """
        Testing check_if_playlist_exists() (false)
        """
        self.assertFalse(self.api.check_if_playlist_exists('testplaylistprivate', self.headers))

    @ordered
    def test_transfer_playback(self):
        """
        Testing transfer_playback() (true)
        """
        # should not raise sysexit
        self.api.transfer_playback('test0', self.headers)

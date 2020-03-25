import unittest
import os
import sys
import time
import argparse
import conf
import api
import log
import oauth2
import recommendation
import spotirec
import mock


def order_handler():
    order = {}

    def ordered_handler(f):
        order[f.__name__] = len(order)
        return f

    def compare_handler(a, b):
        return [1, -1][order[a] < order[b]]

    return ordered_handler, compare_handler


ordered, compare = order_handler()
unittest.defaultTestLoader.sortTestMethodsUsing = compare


class ConfTests(unittest.TestCase):
    def setUp(self):
        self.logger = log.Log()
        self.conf = conf.Config()

        self.logger.set_level(0)

        self.conf.CONFIG_DIR = 'fixtures/'
        self.conf.CONFIG_FILE = 'test.conf'
        self.conf.LOGGER = self.logger
        self.sections = ['spotirecoauth', 'presets', 'blacklist', 'devices', 'playlists']

    def tearDown(self):
        with open('fixtures/empty.conf', 'w') as f:
            f.write('')

    @ordered
    def test_set_logger(self):
        self.conf.set_logger(self.logger)
        self.assertEqual(self.logger, self.conf.LOGGER)

    @ordered
    def test_open_config(self):
        c = self.conf.open_config()
        self.assertEqual(c.sections(), self.sections)
        self.conf.CONFIG_FILE = 'this-does-not-exist.conf'
        c = self.conf.open_config()
        self.assertEqual(c.sections(), self.sections)
        os.remove('fixtures/this-does-not-exist.conf')

    @ordered
    def test_convert_or_create_config(self):
        self.conf.CONFIG_FILE = 'test-convert.conf'
        self.conf.convert_or_create_config()
        c = self.conf.open_config()
        self.assertEqual(self.sections, c.sections())
        self.assertNotEqual(c['spotirecoauth'], {})
        self.assertEqual(c['presets'], {})
        self.assertNotEqual(c['blacklist'], {})
        self.assertEqual(c['blacklist']['tracks'], '{}')
        self.assertEqual(c['blacklist']['artists'], '{}')
        self.assertNotEqual(c['devices'], {})
        self.assertNotEqual(c['playlists'], {})
        self.conf.CONFIG_FILE = 'test.conf'
        os.remove('fixtures/test-convert.conf')

    @ordered
    def test_save_config(self):
        c = self.conf.open_config()
        c.add_section('testsection')
        self.assertIn('testsection', c.sections())
        self.conf.save_config(c)
        c = self.conf.open_config()
        self.assertEqual(self.sections + ['testsection'], c.sections())
        c.remove_section('testsection')
        self.conf.save_config(c)

    @ordered
    def test_get_oauth(self):
        oauth = self.conf.get_oauth()
        self.assertEqual(oauth['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(oauth['token_type'], 'Bearer')
        self.assertEqual(oauth['expires_in'], '3600')
        self.assertEqual(oauth['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(oauth['expires_at'], '15848754832')
        self.assertEqual(oauth['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')
        self.conf.CONFIG_FILE = 'empty.conf'
        oauth = self.conf.get_oauth()
        self.assertEqual(oauth, {})

    @ordered
    def test_get_blacklist(self):
        blacklist = self.conf.get_blacklist()
        self.assertEqual(blacklist['tracks'], {})
        self.assertEqual(blacklist['artists'], {})
        self.conf.CONFIG_FILE = 'empty.conf'
        blacklist = self.conf.get_blacklist()
        self.assertEqual(blacklist['tracks'], {})
        self.assertEqual(blacklist['artists'], {})

    @ordered
    def test_add_to_blacklist(self):
        test_artist = {'name': 'frankie', 'uri': 'spotify:artist:testuri0frankie'}
        test_track = {'name': 'nights', 'uri': 'spotify:track:testuri0nights', 'artists': [{'name': 'frankie'}]}
        self.conf.add_to_blacklist(test_artist, test_artist['uri'])
        self.conf.add_to_blacklist(test_track, test_track['uri'])
        blacklist = self.conf.get_blacklist()
        test_track['artists'] = ['frankie']
        self.assertEqual(blacklist['tracks']['spotify:track:testuri0nights'], test_track)
        self.assertEqual(blacklist['artists']['spotify:artist:testuri0frankie'], test_artist)

    @ordered
    def test_remove_from_blacklist(self):
        # ensure proper functionality
        artist_uri = 'spotify:artist:testuri0frankie'
        track_uri = 'spotify:track:testuri0nights'
        self.conf.remove_from_blacklist(artist_uri)
        self.conf.remove_from_blacklist(track_uri)
        blacklist = self.conf.get_blacklist()
        self.assertEqual(blacklist['tracks'], {})
        self.assertEqual(blacklist['artists'], {})

        # ensure faulty uri returns None
        res = self.conf.remove_from_blacklist('this-is-not-a-uri')
        self.assertEqual(res, None)

        # coverage lol
        self.conf.remove_from_blacklist('spotify:track:thisdoesnotexist')

    @ordered
    def test_get_presets(self):
        presets = self.conf.get_presets()
        self.assertEqual(presets, {})

        # ensure empty section is added if it does not exist
        self.conf.CONFIG_FILE = 'empty.conf'
        presets = self.conf.get_presets()
        self.assertEqual(presets, {})

    @ordered
    def test_save_preset(self):
        preset = {'limit': 20, 'based_on': 'top genres', 'seed': 'hip-hop,metalcore,metal,pop,death-metal',
                  'seed_type': 'genres', 'seed_info':
                      {0: {'name': 'hip-hop', 'type': 'genre'}, 1: {'name': 'metalcore', 'type': 'genre'},
                       2: {'name': 'metal', 'type': 'genre'}, 3: {'name': 'pop', 'type': 'genre'},
                       4: {'name': 'death-metal', 'type': 'genre'}},
                  'rec_params': {'limit': '20', 'seed_genres': 'hip-hop,metalcore,metal,pop,death-metal'},
                  'auto_play': False, 'playback_device': {}}
        self.conf.save_preset(preset, 'test')
        presets = self.conf.get_presets()
        self.assertEqual(preset, presets['test'])

        # ensure preset is still added even if section does not exist
        self.conf.CONFIG_FILE = 'empty.conf'
        self.conf.save_preset(preset, 'test')
        presets = self.conf.get_presets()
        self.assertEqual(preset, presets['test'])

    @ordered
    def test_remove_preset(self):
        self.conf.remove_preset('test')
        presets = self.conf.get_presets()
        self.assertEqual(presets, {})

        # coverage lol
        self.conf.remove_preset('this-does-not-exist')

    @ordered
    def test_get_devices(self):
        devices = self.conf.get_devices()
        self.assertEqual(devices, {})

        # ensure empty section is added if it does not exist
        self.conf.CONFIG_FILE = 'empty.conf'
        devices = self.conf.get_devices()
        self.assertEqual(devices, {})

    @ordered
    def test_save_device(self):
        device = {'id': '9f7e0c7afa654ecea4052667e58a6e86ef4dd612e4b02155bbd8650757ed593f', 'name': 'pc',
                  'type': 'Computer'}
        self.conf.save_device(device, 'test')
        devices = self.conf.get_devices()
        self.assertEqual(device, devices['test'])

        # ensure device is still added even if section does not exist
        self.conf.CONFIG_FILE = 'empty.conf'
        self.conf.save_device(device, 'test')
        devices = self.conf.get_devices()
        self.assertEqual(device, devices['test'])

    @ordered
    def test_remove_device(self):
        self.conf.remove_device('test')
        devices = self.conf.get_devices()
        self.assertEqual(devices, {})

        # coverage lol
        self.conf.remove_device('this-does-not-exist')

    @ordered
    def test_get_playlists(self):
        playlists = self.conf.get_playlists()
        self.assertEqual(playlists, {})

        # ensure empty section is added if it does not exist
        self.conf.CONFIG_FILE = 'empty.conf'
        playlists = self.conf.get_playlists()
        self.assertEqual(playlists, {})

    @ordered
    def test_save_playlist(self):
        playlist = {'name': 'Spotirec-14-3-2020', 'uri': 'spotify:playlist:0Vu97Y7WoJgBlFzAwbrZ8h'}
        self.conf.save_playlist(playlist, 'test')
        playlists = self.conf.get_playlists()
        self.assertEqual(playlist, playlists['test'])

        # ensure device is still added even if section does not exist
        self.conf.CONFIG_FILE = 'empty.conf'
        self.conf.save_playlist(playlist, 'test')
        playlists = self.conf.get_playlists()
        self.assertEqual(playlist, playlists['test'])

    @ordered
    def test_remove_playlist(self):
        self.conf.remove_playlist('test')
        playlists = self.conf.get_playlists()
        self.assertEqual(playlists, {})

        # coverage lol
        self.conf.remove_playlist('this-does-not-exist')


class TestLog(unittest.TestCase):
    def setUp(self):
        self.logger = log.Log()
        self.logger.LOG_PATH = 'fixtures/logs'

        self.logger.set_level(50)

        sys.stdout = open('fixtures/log-test', 'w')

    def tearDown(self):
        os.remove('fixtures/log-test')
        sys.stdout.close()
        sys.stdout = sys.__stdout__

    @ordered
    def test_set_level(self):
        self.logger.set_level(log.INFO)
        self.assertEqual(self.logger.LEVEL, 30)

    @ordered
    def test_suppress_warnings(self):
        self.logger.suppress_warnings(True)
        self.assertTrue(self.logger.SUPPRESS_WARNINGS)

    @ordered
    def test_log_file_log(self):
        self.logger.info('test_log')
        self.logger.log_file()
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open('fixtures/log-test', 'r') as f:
            file = f.read().split('/')[2].strip('\n')
            with open(f'{self.logger.LOG_PATH}/{file}') as f1:
                stdout = f1.read()
                self.assertIn('test_log', stdout)
        os.remove(f'{self.logger.LOG_PATH}/{file}')
        os.rmdir(self.logger.LOG_PATH)

    @ordered
    def test_log_file_crash(self):
        self.logger.info('test_log')
        self.logger.log_file(crash=True)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open('fixtures/log-test', 'r') as f:
            file = f.read().split('/')[2].strip('\n')
            with open(f'{self.logger.LOG_PATH}/{file}') as f1:
                stdout = f1.read()
                self.assertIn('test_log', stdout)
        os.remove(f'{self.logger.LOG_PATH}/{file}')
        os.rmdir(self.logger.LOG_PATH)

    @ordered
    def test_error(self):
        s = 'test_error'
        self.logger.error(s)
        self.assertIn(s, self.logger.LOG)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open('fixtures/log-test', 'r') as f:
            stdout = f.read()
            self.assertIn('ERROR', stdout)
            self.assertIn('test_error', stdout)

    @ordered
    def test_warning(self):
        s = 'test_warning'
        self.logger.warning(s)
        self.assertIn(s, self.logger.LOG)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open('fixtures/log-test', 'r') as f:
            stdout = f.read()
            self.assertIn('WARNING', stdout)
            self.assertIn('test_warning', stdout)

    @ordered
    def test_info(self):
        s = 'test_info'
        self.logger.info(s)
        self.assertIn(s, self.logger.LOG)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open('fixtures/log-test', 'r') as f:
            stdout = f.read()
            self.assertIn('INFO', stdout)
            self.assertIn('test_info', stdout)

    @ordered
    def test_verbose(self):
        s = 'test_verbose'
        self.logger.verbose(s)
        self.assertIn(s, self.logger.LOG)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open('fixtures/log-test', 'r') as f:
            stdout = f.read()
            self.assertIn('INFO', stdout)
            self.assertIn('test_verbose', stdout)

    @ordered
    def test_debug(self):
        s = 'test_debug'
        self.logger.debug(s)
        self.assertIn(s, self.logger.LOG)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open('fixtures/log-test', 'r') as f:
            stdout = f.read()
            self.assertIn('DEBUG', stdout)
            self.assertIn('test_debug', stdout)

    @ordered
    def test_append_log(self):
        self.logger.append_log('TEST', 'test_message')
        self.assertIn('test_message', self.logger.LOG)


class TestRecommendation(unittest.TestCase):
    def setUp(self):
        self.t = time.localtime(0)  # 1-1-1970 1:0:0
        self.timestamp = time.ctime(time.time())
        self.rec = recommendation.Recommendation(t=self.t)

        self.logger = log.Log()
        self.logger.set_level(0)
        self.rec.set_logger(self.logger)

        self.test_seed = {0: {'name': 'metal', 'type': 'genre'},
                          1: {'name': 'test', 'id': 'testid', 'type': 'track', 'artists': ['frankie']},
                          2: {'name': 'frankie', 'id': 'testid', 'type': 'artist'}}
        self.test_track = {'name': 'test', 'id': 'testid', 'type': 'track', 'artists': [{'name': 'frankie'}]}
        self.test_artist = {'name': 'frankie', 'id': 'testid', 'type': 'artist'}

        # unset limit on string comparison
        self.maxDiff = None

    @ordered
    def test_init(self):
        self.assertEqual(self.rec.limit, 20)
        self.assertEqual(self.rec.limit_original, 20)
        self.assertEqual(self.rec.created_at, self.timestamp)
        self.assertEqual(self.rec.based_on, 'top genres')
        self.assertEqual(self.rec.seed, '')
        self.assertEqual(self.rec.seed_type, 'genres')
        self.assertEqual(self.rec.seed_info, {})
        self.assertEqual(self.rec.rec_params, {'limit': '20'})
        self.assertEqual(self.rec.playlist_name, 'Spotirec-1-1-1970')
        self.assertEqual(self.rec.playlist_id, '')
        self.assertEqual(self.rec.auto_play, False)
        self.assertEqual(self.rec.playback_device, {})

    @ordered
    def test_str(self):
        s = "{'limit': 20, 'original limit': 20, 'created at': '" + self.timestamp + \
            "', 'based on': 'top genres', 'seed': '', 'seed type': 'genres', 'seed info': {}, 'rec params': " \
            "{'limit': '20'}, 'name': 'Spotirec-1-1-1970', 'id': '', 'auto play': False, 'device': {}}"
        self.assertEqual(str(self.rec), s)

    @ordered
    def test_playlist_description(self):
        description = 'Created by Spotirec - ' + self.timestamp + ' - based on top genres - seed: '
        self.assertEqual(self.rec.playlist_description(), description)

    @ordered
    def test_update_limit(self):
        # both limit and original limit should be updated
        self.rec.update_limit(50, init=True)
        self.assertEqual(self.rec.limit, 50)
        self.assertEqual(self.rec.limit_original, 50)

        # only limit should be updated
        self.rec.update_limit(70)
        self.assertEqual(self.rec.limit, 70)

    @ordered
    def test_add_seed_info(self):
        self.rec.add_seed_info(data_string='metal')
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.add_seed_info(data_dict=self.test_artist)
        self.assertEqual(self.rec.seed_info, self.test_seed)

    @ordered
    def test_print_selection(self):
        self.rec.add_seed_info(data_string='metal')
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.add_seed_info(data_dict=self.test_artist)
        self.assertEqual(self.rec.seed_info, self.test_seed)
        self.rec.LOGGER.set_level(50)
        sys.stdout = open('fixtures/select', 'w')
        self.rec.print_selection()
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open('fixtures/select', 'r') as f:
            stdout = f.readlines()
            self.assertIn('Selection:', stdout[0])
            self.assertIn('Genre: metal', stdout[1])
            self.assertIn('Track: test - frankie', stdout[2])
            self.assertIn('Artist: frankie', stdout[3])
        os.remove('fixtures/select')

    @ordered
    def test_create_seed_genres(self):
        self.rec.add_seed_info(data_string='metal')
        self.rec.add_seed_info(data_string='metalcore')
        self.rec.add_seed_info(data_string='vapor-death-pop')
        self.rec.seed_type = 'genres'
        self.rec.create_seed()
        self.assertEqual(self.rec.seed, 'metal,metalcore,vapor-death-pop')

    @ordered
    def test_create_seed_artists_tracks(self):
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.seed_type = 'tracks'
        self.rec.create_seed()
        self.assertEqual(self.rec.seed, 'testid,testid,testid')

    @ordered
    def test_create_seed_custom(self):
        self.rec.add_seed_info(data_string='metal')
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.add_seed_info(data_dict=self.test_artist)
        self.rec.seed_type = 'custom'
        self.rec.create_seed()
        self.assertEqual(self.rec.rec_params['seed_tracks'], 'testid')
        self.assertEqual(self.rec.rec_params['seed_artists'], 'testid')
        self.assertEqual(self.rec.rec_params['seed_genres'], 'metal')


class TestOauth2(unittest.TestCase):
    def setUp(self):
        oauth2.requests = mock.MockAPI()
        self.logger = log.Log()
        self.conf = conf.Config()
        self.oauth = oauth2.SpotifyOAuth()
        self.api = api.API()
        self.oauth.OAUTH_TOKEN_URL = '/api/token'
        self.oauth.client_id = 'client_id'
        self.oauth.client_secret = 'client_secret'
        self.oauth.scopes = 'user-modify-playback-state ugc-image-upload user-library-modify'

        self.logger.set_level(0)

        self.api.set_logger(self.logger)

        self.conf.CONFIG_DIR = 'fixtures/'
        self.conf.CONFIG_FILE = 'test.conf'
        self.conf.set_logger(self.logger)

        self.oauth.set_logger(self.logger)
        self.oauth.set_conf(self.conf)
        self.oauth.set_api(self.api)

    @ordered
    def test_get_credentials(self):
        oauth = self.oauth.get_credentials()
        self.assertNotEqual(oauth, {})
        self.assertEqual(oauth['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(oauth['token_type'], 'Bearer')
        self.assertEqual(oauth['expires_in'], '3600')
        self.assertEqual(oauth['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(oauth['expires_at'], '15848754832')
        self.assertEqual(oauth['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')

    @ordered
    def test_get_credentials_refresh(self):
        config = self.conf.open_config()
        config.set('spotirecoauth', 'expires_at', '0')
        self.conf.save_config(config)

        expected_expire = round(time.time()) + 3600
        token = self.oauth.get_credentials()
        self.assertEqual(token['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(token['token_type'], 'Bearer')
        self.assertEqual(token['expires_in'], 3600)
        self.assertEqual(token['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(token['expires_at'], expected_expire)
        self.assertEqual(token['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')

        oauth = self.conf.get_oauth()
        self.assertEqual(oauth['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(oauth['token_type'], 'Bearer')
        self.assertEqual(oauth['expires_in'], '3600')
        self.assertEqual(oauth['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(oauth['expires_at'], str(expected_expire))
        self.assertEqual(oauth['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')

        config = self.conf.open_config()
        config.set('spotirecoauth', 'expires_at', '15848754832')
        self.conf.save_config(config)

    @ordered
    def test_get_credentials_empty_conf(self):
        self.conf.CONFIG_FILE = 'empty.conf'
        token = self.oauth.get_credentials()
        self.assertIsNone(token)
        with open(f'fixtures/empty.conf', 'w') as f:
            f.write('')

    @ordered
    def test_refresh_token(self):
        self.conf.CONFIG_FILE = 'test-refresh.conf'
        expected_expire = round(time.time()) + 3600
        token = self.oauth.refresh_token('737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')
        self.assertEqual(token['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(token['token_type'], 'Bearer')
        self.assertEqual(token['expires_in'], 3600)
        self.assertEqual(token['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(token['expires_at'], expected_expire)
        self.assertEqual(token['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')

        oauth = self.conf.get_oauth()
        self.assertEqual(oauth['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(oauth['token_type'], 'Bearer')
        self.assertEqual(oauth['expires_in'], '3600')
        self.assertEqual(oauth['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(oauth['expires_at'], str(expected_expire))
        self.assertEqual(oauth['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')
        os.remove('fixtures/test-refresh.conf')

    @ordered
    def test_refresh_token_no_refresh(self):
        self.conf.CONFIG_FILE = 'test-refresh.conf'
        expected_expire = round(time.time()) + 3600
        token = self.oauth.refresh_token('no_refresh')
        self.assertEqual(token['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(token['token_type'], 'Bearer')
        self.assertEqual(token['expires_in'], 3600)
        self.assertEqual(token['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(token['expires_at'], expected_expire)
        self.assertEqual(token['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')

        oauth = self.conf.get_oauth()
        self.assertEqual(oauth['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(oauth['token_type'], 'Bearer')
        self.assertEqual(oauth['expires_in'], '3600')
        self.assertEqual(oauth['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(oauth['expires_at'], str(expected_expire))
        self.assertEqual(oauth['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')
        os.remove('fixtures/test-refresh.conf')

    @ordered
    def test_is_token_expired(self):
        # config is set to expire in year ~2500
        oauth = self.oauth.get_credentials()
        self.assertFalse(self.oauth.is_token_expired(int(oauth['expires_at'])))
        self.assertTrue(self.oauth.is_token_expired(0))

    @ordered
    def test_encode_header(self):
        expected = {'Authorization': 'Basic dGhpc2lzYXJlYWxjbGllbnRpZDp0aGlzaXNhcmVhbGNsaWVudHNlY3JldA=='}
        self.oauth.client_id = 'thisisarealclientid'
        self.oauth.client_secret = 'thisisarealclientsecret'
        header = self.oauth.encode_header()
        self.assertEqual(header, expected)

    @ordered
    def test_retrieve_access_token(self):
        self.conf.CONFIG_FILE = 'test-retrieve.conf'
        expected_expire = round(time.time()) + 3600
        token = self.oauth.retrieve_access_token('testcode')
        self.assertEqual(token['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(token['token_type'], 'Bearer')
        self.assertEqual(token['expires_in'], 3600)
        self.assertEqual(token['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(token['expires_at'], expected_expire)
        self.assertEqual(token['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')

        oauth = self.conf.get_oauth()
        self.assertEqual(oauth['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(oauth['token_type'], 'Bearer')
        self.assertEqual(oauth['expires_in'], '3600')
        self.assertEqual(oauth['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(oauth['expires_at'], str(expected_expire))
        self.assertEqual(oauth['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')
        os.remove('fixtures/test-retrieve.conf')

    @ordered
    def test_get_authorize_url(self):
        expected = 'https://accounts.spotify.com/authorize?client_id=thisisarealclientid&response_type=code&redirect' \
                   '_uri=https%3A%2F%2Fthis-is-a-real-redirect.uri&scope=user-modify-playback-state+ugc-image-upload' \
                   '+user-library-modify'
        self.oauth.client_id = 'thisisarealclientid'
        self.oauth.redirect = 'https://this-is-a-real-redirect.uri'
        self.oauth.scopes = 'user-modify-playback-state ugc-image-upload user-library-modify'
        url = self.oauth.get_authorize_url()
        self.assertEqual(url, expected)

    @ordered
    def test_parse_response_code(self):
        expected = '03fjn439n9348fh928fn392fnkjd'
        # should give index error
        code = self.oauth.parse_response_code('')
        self.assertNotEqual(code, expected)
        # ensure it works with one arg
        url = 'https://this-is-a-real.url?code=03fjn439n9348fh928fn392fnkjd'
        code = self.oauth.parse_response_code(url)
        self.assertEqual(code, expected)
        # ensure it works with several args
        url += '&test=test&yeet=yote'
        code = self.oauth.parse_response_code(url)
        self.assertEqual(code, expected)

    @ordered
    def test_save_token(self):
        self.oauth.CONF.CONFIG_FILE = 'save-test'
        token = {'access_token': 'test', 'token_type': 'test', 'expires_in': '3600', 'scope': 'test-test'}
        expires_at = str(round(time.time()) + 3600)
        self.oauth.save_token(token, refresh_token='test')
        oauth = self.oauth.CONF.get_oauth()
        self.assertEqual(oauth['access_token'], 'test')
        self.assertEqual(oauth['token_type'], 'test')
        self.assertEqual(oauth['expires_in'], '3600')
        self.assertEqual(oauth['scope'], 'test-test')
        self.assertEqual(oauth['expires_at'], expires_at)
        self.assertEqual(oauth['refresh_token'], 'test')
        os.remove('fixtures/save-test')

    @ordered
    def test_set_api(self):
        api_test = api.API()
        self.oauth.set_api(api_test)
        self.assertEqual(api_test, self.oauth.API)


class TestAPI(unittest.TestCase):
    def setUp(self):
        api.requests = mock.MockAPI()
        self.api = api.API()
        self.api.URL_BASE = ''
        self.api.set_logger(log.Log())
        self.api.LOGGER.set_level(log.INFO)
        self.api.LOGGER.LOG_PATH = 'fixtures'
        self.test_log = 'fixtures/test-api'
        sys.stdout = open(self.test_log, 'w')
        self.config = conf.Config()
        self.config.set_logger(self.api.LOGGER)
        self.config.CONFIG_DIR = 'fixtures'
        self.config.CONFIG_FILE = 'test.conf'
        self.api.set_conf(self.config)
        self.headers = {'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.config.get_oauth()["access_token"]}'}
        self.img_headers = {'Content-Type': 'image/jpeg',
                            'Authorization': f'Bearer {self.config.get_oauth()["access_token"]}'}

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        os.remove(self.test_log)

    @ordered
    def test_set_conf(self):
        expected = conf.Config()
        self.api.set_conf(expected)
        self.assertEqual(expected, self.api.CONF)

    @ordered
    def test_error_handle_success(self):
        response = mock.MockResponse(200, 'success', 'success', {'success': 'yes lol'}, 'https://success.test')
        self.api.error_handle('test', 200, 'TEST', response=response)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertEqual(stdout, '')

    @ordered
    def test_error_handle_error(self):
        response = mock.MockResponse(400, 'error', 'error', {'success': 'no lol'}, 'https://error.test')
        expected = 'TEST request for test failed with status code 400 (expected 200). Reason: error'
        self.assertRaises(SystemExit, self.api.error_handle, request_domain='test', expected_code=200,
                          request_type='TEST', response=response)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_error_handle_401(self):
        response = mock.MockResponse(401, 'error', 'error', {'success': 'no lol'}, 'https://error.test')
        expected = 'this may be because this is a new function, and additional authorization is required - try ' \
                   'reauthorizing and try again.'
        self.assertRaises(SystemExit, self.api.error_handle, request_domain='test', expected_code=200,
                          request_type='TEST', response=response)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_get_top_list_artists(self):
        artists = self.api.get_top_list('artists', 20, self.headers)
        self.assertIn('items', artists.keys())
        self.assertTrue(any(x['name'] == 'frankie3' for x in artists['items']))
        self.assertTrue(any(x['uri'] == 'spotify:artist:testid1' for x in artists['items']))

    @ordered
    def test_get_top_list_tracks(self):
        tracks = self.api.get_top_list('tracks', 20, self.headers)
        self.assertIn('items', tracks.keys())
        self.assertTrue(any(x['name'] == 'track4' for x in tracks['items']))
        self.assertTrue(any(x['uri'] == 'spotify:track:testid2' for x in tracks['items']))

    @ordered
    def test_get_user_id(self):
        iden = self.api.get_user_id(self.headers)
        self.assertEqual(iden, 'testuser')

    @ordered
    def test_create_playlist_no_cache(self):
        iden = self.api.create_playlist('test', 'test-description', self.headers)
        self.assertEqual(iden, 'testplaylist')

    @ordered
    def test_create_playlist_cached(self):
        iden = self.api.create_playlist('test', 'test-description', self.headers, cache_id=True)
        self.assertEqual(iden, 'testplaylist')
        playlists = self.config.get_playlists()
        self.assertIn('spotirec-default', playlists.keys())
        self.assertEqual(playlists['spotirec-default']['uri'], 'spotify:playlist:testid')
        self.config.remove_playlist('spotirec-default')

    @ordered
    def test_upload_image(self):
        # should not raise sysexit
        self.api.upload_image('testplaylist', 'base64string==', self.img_headers)

    @ordered
    def test_add_to_playlist(self):
        # should not raise sysexit
        self.api.add_to_playlist(['spotify:track:trackid0', 'spotify:track:trackid1', 'spotify:track:trackid2'],
                                 'testplaylist', self.headers)

    @ordered
    def test_get_recommendations(self):
        recs = self.api.get_recommendations({}, self.headers)
        self.assertIn('tracks', recs.keys())
        self.assertTrue(any(x['name'] == 'track4' for x in recs['tracks']))
        self.assertTrue(any(x['uri'] == 'spotify:track:testid2' for x in recs['tracks']))

    @ordered
    def test_request_data_artist(self):
        artist = self.api.request_data('spotify:artist:testartist', 'artists', self.headers)
        self.assertEqual('frankie0', artist['name'])
        self.assertEqual('spotify:artist:testartist', artist['uri'])
        self.assertListEqual(['pop', 'metal', 'vapor-death-pop'], artist['genres'])

    @ordered
    def test_request_data_track(self):
        track = self.api.request_data('spotify:track:testtrack', 'tracks', self.headers)
        self.assertEqual('track0', track['name'])
        self.assertEqual('spotify:track:testtrack', track['uri'])
        self.assertEqual('testtrack', track['id'])

    @ordered
    def test_get_genre_seeds(self):
        seeds = self.api.get_genre_seeds(self.headers)
        self.assertIn('genres', seeds.keys())
        self.assertIn('vapor-death-pop', seeds['genres'])
        self.assertIn('pop', seeds['genres'])
        self.assertEqual(seeds['genres'], ['metal', 'metalcore', 'pop', 'vapor-death-pop', 'holidays'])

    @ordered
    def test_get_available_devices(self):
        devices = self.api.get_available_devices(self.headers)
        self.assertIn('devices', devices.keys())
        self.assertIn({'id': 'testid0', 'name': 'test0', 'type': 'fridge'}, devices['devices'])

    @ordered
    def test_play(self):
        # should not raise sysexit
        self.api.play('testid0', 'spotify:playlist:testplaylist', self.headers)

    @ordered
    def test_get_current_track(self):
        uri = self.api.get_current_track(self.headers)
        self.assertEqual('spotify:track:testtrack', uri)

    @ordered
    def test_get_current_artists(self):
        artists = self.api.get_current_artists(self.headers)
        self.assertListEqual(['spotify:artist:testartist', 'spotify:artist:testartist'], artists)

    @ordered
    def test_like_track(self):
        # should not raise sysexit
        self.api.like_track(self.headers)

    @ordered
    def test_unlike_track(self):
        # should not raise sysexit
        self.api.unlike_track(self.headers)

    @ordered
    def test_update_playlist_details(self):
        # should not raise sysexit
        self.api.update_playlist_details('new-name', 'new-description', 'testplaylist', self.headers)

    @ordered
    def test_replace_playlist_tracks(self):
        # should not raise sysexit
        self.api.replace_playlist_tracks('testplaylist', ['spotify:track:testid0', 'spotify:track:testid1'],
                                         self.headers)

    @ordered
    def test_get_playlist(self):
        playlist = self.api.get_playlist(self.headers, 'testplaylist')
        self.assertEqual('testplaylist', playlist['id'])
        self.assertEqual('testplaylist', playlist['name'])
        self.assertEqual('spotify:playlist:testid', playlist['uri'])

    @ordered
    def test_remove_from_playlist(self):
        # should not raise sysexit
        self.api.remove_from_playlist(['spotify:track:testid0', 'spotify:track:testid1'], 'testplaylist', self.headers)

    @ordered
    def test_get_audio_features(self):
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
        self.assertTrue(self.api.check_if_playlist_exists('testplaylist', self.headers))

    @ordered
    def test_check_if_playlist_exists_false(self):
        self.assertFalse(self.api.check_if_playlist_exists('testplaylistprivate', self.headers))

    @ordered
    def test_transfer_playback(self):
        # should not raise sysexit
        self.api.transfer_playback('test0', self.headers)


class TestSpotirec(unittest.TestCase):
    def setUp(self):
        spotirec.CONFIG_PATH = 'fixtures/.config'
        spotirec.logger = log.Log()
        spotirec.logger.set_level(0)
        spotirec.logger.LOG_PATH = 'fixtures'
        spotirec.conf = conf.Config()
        spotirec.conf.set_logger(spotirec.logger)
        spotirec.conf.CONFIG_DIR = 'fixtures'
        spotirec.conf.CONFIG_FILE = 'test.conf'
        spotirec.sp_oauth = oauth2.SpotifyOAuth()
        spotirec.sp_oauth.set_logger(spotirec.logger)
        spotirec.sp_oauth.set_conf(spotirec.conf)
        spotirec.sp_oauth.OAUTH_TOKEN_URL = '/api/token'
        spotirec.sp_oauth.OAUTH_AUTH_URL = '/authorize'
        spotirec.sp_oauth.client_secret = 'client_secret'
        spotirec.sp_oauth.client_id = 'client_id'
        spotirec.sp_oauth.redirect = 'https://real.url'
        spotirec.sp_oauth.scopes = 'scope'
        spotirec.api = api.API()
        spotirec.api.URL_BASE = ''
        spotirec.api.requests = mock.MockAPI()
        spotirec.api.set_logger(spotirec.logger)
        spotirec.api.set_conf(spotirec.conf)
        spotirec.sp_oauth.set_api(spotirec.api)
        spotirec.rec = recommendation.Recommendation()
        spotirec.rec.set_logger(spotirec.logger)
        spotirec.headers = {'Content-Type': 'application/json',
                            'Authorization': 'Bearer f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f'}
        self.test_log = 'fixtures/test-log'
        sys.stdout = open(self.test_log, 'w')

        self.test_track0 = {'name': 'test0', 'id': 'testid0', 'type': 'track', 'artists': [{'name': 'frankie0'}]}
        self.test_track1 = {'name': 'test1', 'id': 'testid1', 'type': 'track', 'artists': [{'name': 'frankie1'}]}
        self.test_track2 = {'name': 'test2', 'id': 'testid2', 'type': 'track', 'artists': [{'name': 'frankie2'}]}

        self.test_artist0 = {'name': 'frankie0', 'id': 'testid0', 'type': 'artist'}
        self.test_artist1 = {'name': 'frankie1', 'id': 'testid1', 'type': 'artist'}
        self.test_artist2 = {'name': 'frankie2', 'id': 'testid2', 'type': 'artist'}

        self.test_device0 = {'id': 'testid', 'name': 'test', 'type': 'tester'}

        self.test_playlist0 = {'name': 'test', 'uri': 'spotify:playlist:testid'}

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        if os.path.isfile(self.test_log):
            os.remove(self.test_log)
        spotirec.input = input
        spotirec.args = spotirec.parser.parse_args()

    @ordered
    def test_index_no_code(self):
        spotirec.request = mock.MockRequest('https://real.url')
        expected = "<a href='/authorize?client_id=client_id&response_type=code&redirect_uri=https%3A%2F%2Freal.url&" \
                   "scope=scope'>Login to Spotify</a>"
        res = spotirec.index()
        self.assertEqual(res, expected)

    @ordered
    def test_index_code(self):
        spotirec.conf.CONFIG_FILE = 'test-index.conf'
        spotirec.request = mock.MockRequest('https://real.url?code=testcode')
        expected = '<span>Successfully retrieved OAuth token. You may close this tab and start using Spotirec.</span>'
        expected_expire = str(round(time.time()) + 3600)
        res = spotirec.index()
        self.assertEqual(res, expected)

        oauth = spotirec.conf.get_oauth()
        self.assertEqual(oauth['access_token'], 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(oauth['token_type'], 'Bearer')
        self.assertEqual(oauth['expires_in'], '3600')
        self.assertEqual(oauth['scope'], 'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(oauth['expires_at'], expected_expire)
        self.assertEqual(oauth['refresh_token'], '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')
        os.remove('fixtures/test-index.conf')

    @ordered
    def test_get_token(self):
        self.assertEqual(spotirec.get_token(), 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')

    @ordered
    def test_get_token_fail(self):
        def mock_authorize():
            self.test = 'success'

        self.test = ''
        auth_save = spotirec.authorize
        spotirec.authorize = mock_authorize
        spotirec.conf.CONFIG_FILE = 'empty.conf'
        self.assertRaises(SystemExit, spotirec.get_token)
        self.assertEqual(self.test, 'success')
        spotirec.authorize = auth_save
        with open('fixtures/empty.conf', 'w') as f:
            f.write('')

    @ordered
    def test_get_user_top_genres(self):
        genres = spotirec.get_user_top_genres()
        self.assertEqual(list(genres.keys()), ['pop', 'metal', 'vapor-death-pop', 'holidays', 'metalcore'])

    @ordered
    def test_add_top_genres_seed(self):
        spotirec.add_top_genres_seed(5)
        # rec object should have one seed
        self.assertNotEqual(spotirec.rec.seed_info, {})
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'pop', 'type': 'genre'},
                                                      1: {'name': 'vapor-death-pop', 'type': 'genre'},
                                                      2: {'name': 'metal', 'type': 'genre'},
                                                      3: {'name': 'holidays', 'type': 'genre'},
                                                      4: {'name': 'metalcore', 'type': 'genre'}})

    @ordered
    def test_print_choices(self):
        expected = f'0: metal{" " * 35}1: metalcore{" " * 31}2: vapor-death-pop\n3: pop\n'
        spotirec.print_choices(data=['metal', 'metalcore', 'vapor-death-pop', 'pop'], prompt=False)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertEqual(expected, stdout)

    @ordered
    def test_print_choices_sorted(self):
        expected = f'0: vapor-death-pop{" " * 25}1: metalcore{" " * 31}2: metal\n3: pop\n'
        spotirec.print_choices(data={'metal': 3, 'metalcore': 7, 'vapor-death-pop': 23, 'pop': 1},
                               prompt=False, sort=True)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertEqual(expected, stdout)

    @ordered
    def test_print_choices_prompt_genres(self):
        def mock_input(prompt: str):
            return '0 2'
        spotirec.input = mock_input
        spotirec.print_choices(data=['metal', 'metalcore', 'vapor-death-pop', 'pop'])
        self.assertNotEqual(spotirec.rec.seed_info, {})
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'metal', 'type': 'genre'},
                                                      1: {'name': 'vapor-death-pop', 'type': 'genre'}})

    @ordered
    def test_print_choices_prompt_other(self):
        def mock_input(prompt: str):
            return '1 2 3'
        spotirec.rec.seed_type = 'tracks'
        spotirec.input = mock_input
        choice = spotirec.print_choices(data=['metal', 'metalcore', 'vapor-death-pop', 'pop'])
        self.assertEqual(choice, mock_input(''))

    @ordered
    def test_print_choices_keyboard_interrupt(self):
        def mock_input(prompt: str):
            raise KeyboardInterrupt
        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.print_choices, data=[])

    @ordered
    def test_print_artists_or_tracks(self):
        data = {'items': [{'name': 'test0', 'id': 'test0'}, {'name': 'test1', 'id': 'test1'},
                          {'name': 'test2', 'id': 'test2'}, {'name': 'test3', 'id': 'test3'}]}
        expected = f'0: test0{" " * 35}1: test1{" " * 35}2: test2\n3: test3\n'
        spotirec.print_artists_or_tracks(data, prompt=False)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertEqual(expected, stdout)

    @ordered
    def test_print_artists_or_tracks_prompt(self):
        def mock_input(prompt: str):
            return '0 2'
        spotirec.input = mock_input
        spotirec.rec.seed_type = 'artists'
        spotirec.print_artists_or_tracks(spotirec.api.get_top_list('artists', 20, spotirec.headers))
        self.assertNotEqual(spotirec.rec.seed_info, {})
        self.assertEqual(spotirec.rec.seed_info, {0: {'id': 'testid0', 'name': 'frankie0', 'type': 'artist'},
                                                  1: {'id': 'testid2', 'name': 'frankie2', 'type': 'artist'}})

    @ordered
    def test_check_if_valid_genre_true(self):
        self.assertTrue(spotirec.check_if_valid_genre('vapor-death-pop'))

    @ordered
    def test_check_if_valid_genre_false(self):
        self.assertFalse(spotirec.check_if_valid_genre('vapor-death-jazz'))

    @ordered
    def test_check_tune_validity_success(self):
        expected = 'tune attribute tempo with prefix min and value 160.0 is valid'
        spotirec.logger.set_level(log.DEBUG)
        spotirec.check_tune_validity('min_tempo=160')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_check_tune_validity_fail_prefix(self):
        expected = 'tune prefix \"mox\" is malformed'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.check_tune_validity, tune='mox_tempo=160')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_check_tune_validity_fail_attribute(self):
        expected = 'tune attribute \"tampo\" is malformed'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.check_tune_validity, tune='max_tampo=160')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_check_tune_validity_fail_value_type(self):
        expected = 'tune value test does not match attribute tempo data type requirements'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.check_tune_validity, tune='max_tempo=test')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_check_tune_validity_fail_value_range(self):
        expected = 'value 300.0 for attribute tempo is outside the accepted range (min: 0.0, max: 220.0)'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.check_tune_validity, tune='max_tempo=300')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_check_tune_validity_warn_value_range(self):
        expected = 'value 215.0 for attribute tempo is outside the recommended range (min: 60.0, max: 210.0), ' \
                   'recommendations may be scarce'
        spotirec.logger.set_level(log.WARNING)
        spotirec.check_tune_validity('max_tempo=215')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_parse_seed_info_error_str(self):
        expected = 'please enter at most 5 seeds'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.parse_seed_info, seeds='0 1 2 3 4 5')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_parse_seed_info_error_list(self):
        expected = 'please enter at most 5 seeds'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.parse_seed_info, seeds=[0, 1, 2, 3, 4, 5])
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_parse_seed_info_genres_str(self):
        expected = {0: {'name': 'metal', 'type': 'genre'}, 1: {'name': 'vapor-death-pop', 'type': 'genre'}}
        spotirec.rec.seed_type = 'genres'
        spotirec.parse_seed_info('metal vapor-death-pop')
        self.assertDictEqual(expected, spotirec.rec.seed_info)

    @ordered
    def test_parse_seed_info_genres_list(self):
        expected = {0: {'name': 'metal', 'type': 'genre'}, 1: {'name': 'vapor-death-pop', 'type': 'genre'}}
        spotirec.rec.seed_type = 'genres'
        spotirec.parse_seed_info(['metal', 'vapor-death-pop'])
        self.assertDictEqual(expected, spotirec.rec.seed_info)

    @ordered
    def test_parse_seed_info_genres_tracks_list(self):
        expected = {0: {'name': 'test0', 'id': 'testid0', 'type': 'track', 'artists': ['frankie0']},
                    1: {'name': 'test1', 'id': 'testid1', 'type': 'track', 'artists': ['frankie1']},
                    2: {'name': 'test2', 'id': 'testid2', 'type': 'track', 'artists': ['frankie2']}}
        spotirec.rec.seed_type = 'tracks'
        spotirec.parse_seed_info([self.test_track0, self.test_track1, self.test_track2])
        self.assertDictEqual(expected, spotirec.rec.seed_info)

    @ordered
    def test_parse_seed_info_genres_artists_list(self):
        expected = {0: {'name': 'frankie0', 'id': 'testid0', 'type': 'artist'},
                    1: {'name': 'frankie1', 'id': 'testid1', 'type': 'artist'},
                    2: {'name': 'frankie2', 'id': 'testid2', 'type': 'artist'}}
        spotirec.rec.seed_type = 'artists'
        spotirec.parse_seed_info([self.test_artist0, self.test_artist1, self.test_artist2])
        self.assertDictEqual(expected, spotirec.rec.seed_info)

    @ordered
    def test_parse_seed_info_custom_genres(self):
        spotirec.rec.seed_type = 'custom'
        spotirec.parse_seed_info(['vapor-death-pop'])
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'vapor-death-pop', 'type': 'genre'}})

    @ordered
    def test_parse_seed_info_custom_uri(self):
        spotirec.rec.seed_type = 'custom'
        spotirec.parse_seed_info(['spotify:track:testtrack'])
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'track0', 'id': 'testtrack', 'type': 'track',
                                                          'artists': ['frankie0', 'frankie1']}})

    @ordered
    def test_parse_seed_info_custom_warning(self):
        expected = 'input \"vapor-death-jazz\" does not match a genre or a valid URI syntax, skipping...'
        spotirec.logger.set_level(log.WARNING)
        spotirec.rec.seed_type = 'custom'
        spotirec.parse_seed_info(['vapor-death-jazz'])
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_add_to_blacklist(self):
        spotirec.add_to_blacklist(['spotify:track:testtrack'])
        blacklist = spotirec.conf.get_blacklist()
        self.assertIn('spotify:track:testtrack', blacklist['tracks'].keys())
        self.assertDictEqual(blacklist['tracks']['spotify:track:testtrack'],
                             {'name': 'track0', 'uri': 'spotify:track:testtrack', 'artists': ['frankie0', 'frankie1']})
        spotirec.conf.remove_from_blacklist('spotify:track:testtrack')
        blacklist = spotirec.conf.get_blacklist()
        self.assertDictEqual(blacklist['tracks'], {})

    @ordered
    def test_remove_from_blacklist(self):
        spotirec.conf.add_to_blacklist(self.test_track0, 'spotify:track:testid0')
        spotirec.conf.add_to_blacklist(self.test_artist0, 'spotify:artist:testid0')
        blacklist = spotirec.conf.get_blacklist()
        self.assertIn('spotify:track:testid0', blacklist['tracks'].keys())
        self.assertIn('spotify:artist:testid0', blacklist['artists'].keys())
        spotirec.remove_from_blacklist(['spotify:track:testid0', 'spotify:artist:testid0'])
        blacklist = spotirec.conf.get_blacklist()
        self.assertNotIn('spotify:track:testid0', blacklist['tracks'].keys())
        self.assertNotIn('spotify:artist:testid0', blacklist['artists'].keys())

    @ordered
    def test_print_blacklist(self):
        spotirec.conf.add_to_blacklist(self.test_track0, 'spotify:track:testid0')
        spotirec.conf.add_to_blacklist(self.test_artist0, 'spotify:artist:testid0')
        spotirec.print_blacklist()
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn('Tracks', stdout)
            self.assertIn('Artists', stdout)
            self.assertIn('test0 by frankie0 - spotify:track:testid0', stdout)
            self.assertIn('frankie0 - spotify:artist:testid0', stdout)

    @ordered
    def test_generate_img(self):
        img = spotirec.generate_img(['test:test:test', 'test:test:test', 'test:test:test'])
        # hash: 2eccd587915e21ab37d6352bb55cfc8754545daa6ba1c3be0b759d66fbb36acb
        # color: [46, 204, 213]
        self.assertTrue(any(x[1] == (46, 204, 213) for x in img.getcolors()))
        self.assertTrue(any(x[1] == (200, 200, 200) for x in img.getcolors()))
        self.assertEqual(img.size, (320, 320))

    @ordered
    def test_add_image_to_playlist(self):
        # should not cause system exit
        spotirec.rec.playlist_id = 'testplaylist'
        spotirec.add_image_to_playlist(['test:test:test', 'test:test:test', 'test:test:test'])

    @ordered
    def test_save_preset(self):
        spotirec.save_preset('test')
        presets = spotirec.conf.get_presets()
        self.assertIn('test', presets.keys())
        self.assertEqual(presets['test']['limit'], spotirec.rec.limit_original)
        self.assertEqual(presets['test']['based_on'], spotirec.rec.based_on)
        self.assertEqual(presets['test']['seed'], spotirec.rec.seed)
        self.assertEqual(presets['test']['seed_type'], spotirec.rec.seed_type)
        self.assertEqual(presets['test']['seed_info'], spotirec.rec.seed_info)
        self.assertEqual(presets['test']['rec_params'], spotirec.rec.rec_params)
        self.assertEqual(presets['test']['auto_play'], spotirec.rec.auto_play)
        self.assertEqual(presets['test']['playback_device'], spotirec.rec.playback_device)
        spotirec.conf.remove_preset('test')
        presets = spotirec.conf.get_presets()
        self.assertNotIn('test', presets.keys())

    @ordered
    def test_load_preset(self):
        spotirec.save_preset('test')
        expected_preset = spotirec.conf.get_presets()['test']
        preset = spotirec.load_preset('test')
        self.assertEqual(expected_preset['limit'], preset.limit_original)
        self.assertEqual(expected_preset['based_on'], preset.based_on)
        self.assertEqual(expected_preset['seed'], preset.seed)
        self.assertEqual(expected_preset['seed_type'], preset.seed_type)
        self.assertEqual(expected_preset['seed_info'], preset.seed_info)
        self.assertEqual(expected_preset['rec_params'], preset.rec_params)
        self.assertEqual(expected_preset['auto_play'], preset.auto_play)
        self.assertEqual(expected_preset['playback_device'], preset.playback_device)
        spotirec.conf.remove_preset('test')
        presets = spotirec.conf.get_presets()
        self.assertNotIn('test', presets.keys())

    @ordered
    def test_load_preset_error(self):
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.load_preset, name='this-does-not-exist')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_remove_presets(self):
        spotirec.save_preset('test')
        presets = spotirec.conf.get_presets()
        self.assertIn('test', presets.keys())
        spotirec.remove_presets(['test'])
        presets = spotirec.conf.get_presets()
        self.assertNotIn('test', presets.keys())

    @ordered
    def test_print_presets(self):
        expected0 = f'Name{" " * 16}Type{" " * 21}Params{" " * 44}Seeds'
        expected1 = f'test{" " * 16}top genres{" " * 15}limit=20{" " * 42}'
        spotirec.save_preset('test')
        spotirec.print_presets()
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)
        spotirec.conf.remove_preset('test')

    @ordered
    def test_get_device_error(self):
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.get_device, device_name='this-does-not-exist')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_get_device_success(self):
        spotirec.conf.save_device(self.test_device0, 'test')
        device = spotirec.get_device('test')
        self.assertDictEqual(device, self.test_device0)
        spotirec.conf.remove_device('test')

    @ordered
    def test_save_device(self):
        def mock_input(prompt: str):
            return '1'
        spotirec.input = mock_input
        spotirec.save_device()
        devices = spotirec.conf.get_devices()
        self.assertIn('1', devices.keys())
        self.assertDictEqual(devices['1'], {'id': 'testid1', 'name': 'test1', 'type': 'microwave'})
        spotirec.conf.remove_device('1')

    @ordered
    def test_save_device_sigint_device_index(self):
        def mock_input(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.save_device)

    @ordered
    def test_save_device_sigint_name(self):
        def mock_input(prompt: str):
            spotirec.input = mock_input_name
            return ''

        def mock_input_name(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.save_device)

    @ordered
    def test_save_device_value_error(self):
        def mock_input(prompt: str):
            spotirec.input = mock_input_index
            return 'test'

        def mock_input_index(prompt: str):
            spotirec.input = mock_input_sigint
            return 1

        def mock_input_sigint(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.save_device)

    @ordered
    def test_save_device_name_error(self):
        def mock_input_index(prompt: str):
            spotirec.input = mock_input_name_error
            return 1

        def mock_input_name_error(prompt: str):
            spotirec.input = mock_input_name
            return 'this will not work'

        def mock_input_name(prompt: str):
            return 'test'

        spotirec.input = mock_input_index
        spotirec.save_device()
        devices = spotirec.conf.get_devices()
        self.assertIn('test', devices.keys())
        self.assertDictEqual(devices['test'], {'id': 'testid1', 'name': 'test1', 'type': 'microwave'})
        spotirec.conf.remove_device('test')

    @ordered
    def test_remove_devices(self):
        spotirec.conf.save_device(self.test_device0, 'test')
        devices = spotirec.conf.get_devices()
        self.assertIn('test', devices.keys())
        spotirec.remove_devices(['test'])
        devices = spotirec.conf.get_devices()
        self.assertNotIn('test', devices.keys())

    @ordered
    def test_print_saved_devices(self):
        expected0 = f'ID{" " * 18}Name{" " * 16}Type'
        expected1 = f'test{" " * 16}test{" " * 16}tester'
        spotirec.conf.save_device(self.test_device0, 'test')
        spotirec.print_saved_devices()
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)
        spotirec.conf.remove_device('test')

    @ordered
    def test_print_playlists(self):
        expected0 = f'ID{" " * 18}Name{" " * 26}URI'
        expected1 = f'test{" " * 16}test{" " * 26}spotify:playlist:testid'
        spotirec.conf.save_playlist(self.test_playlist0, 'test')
        spotirec.print_playlists()
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)
        spotirec.conf.remove_playlist('test')

    @ordered
    def test_save_playlist(self):
        def mock_input_uri(prompt: str):
            return 'spotify:playlist:testplaylist'

        def mock_input_name(prompt: str):
            spotirec.input = mock_input_uri
            return 'test'

        spotirec.input = mock_input_name
        spotirec.save_playlist()
        playlists = spotirec.conf.get_playlists()
        self.assertIn('test', playlists.keys())
        self.assertDictEqual(playlists['test'], {'name': 'testplaylist', 'uri': 'spotify:playlist:testplaylist'})
        spotirec.conf.remove_playlist('test')

    @ordered
    def test_save_playlist_sigint_name(self):
        def mock_input(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.save_playlist)

    @ordered
    def test_save_playlist_sigint_uri(self):
        def mock_input_name(prompt: str):
            spotirec.input = mock_input_uri
            return 'test'

        def mock_input_uri(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input_name
        self.assertRaises(SystemExit, spotirec.save_playlist)

    @ordered
    def test_save_playlist_name_error(self):
        def mock_input(prompt: str):
            spotirec.input = mock_input_sigint
            return 'this will not work'

        def mock_input_sigint(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.save_playlist)

    @ordered
    def test_save_playlist_uri_error(self):
        def mock_input_name(prompt: str):
            spotirec.input = mock_input_uri_error
            return 'test'

        def mock_input_uri_error(prompt: str):
            spotirec.input = mock_input_uri
            return 'this is not a URI'

        def mock_input_uri(prompt: str):
            return 'spotify:playlist:testplaylist'

        spotirec.input = mock_input_name
        spotirec.save_playlist()
        playlists = spotirec.conf.get_playlists()
        self.assertIn('test', playlists.keys())
        self.assertDictEqual(playlists['test'], {'name': 'testplaylist', 'uri': 'spotify:playlist:testplaylist'})

    @ordered
    def test_remove_playlists(self):
        spotirec.conf.save_playlist(self.test_playlist0, 'test')
        playlists = spotirec.conf.get_playlists()
        self.assertIn('test', playlists.keys())
        spotirec.remove_playlists(['test'])
        playlists = spotirec.conf.get_playlists()
        self.assertNotIn('test', playlists.keys())

    @ordered
    def test_add_current_track_error(self):
        playlists = spotirec.conf.get_playlists()
        self.assertNotIn('test', playlists.keys())
        self.assertRaises(SystemExit, spotirec.add_current_track, playlist='test')

    @ordered
    def test_add_current_track(self):
        # should not cause system exit
        spotirec.add_current_track('spotify:playlist:testplaylist')

    @ordered
    def test_remove_current_track_error(self):
        playlists = spotirec.conf.get_playlists()
        self.assertNotIn('test', playlists.keys())
        self.assertRaises(SystemExit, spotirec.remove_current_track, playlist='test')

    @ordered
    def test_remove_current_track(self):
        # should not cause system exit
        spotirec.remove_current_track('spotify:playlist:testplaylist')

    @ordered
    def test_print_track_features_error(self):
        expected = 'this is not a URI is not a valid track URI'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.print_track_features, uri='this is not a URI')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_print_track_features(self):
        spotirec.print_track_features('spotify:track:testtrack')
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn('track0 - frankie0, frankie1', stdout)
            self.assertIn(f'Track URI{" " * 21}spotify:track:testtrack', stdout)
            self.assertIn(f'Artist URI(s){" " * 17}frankie0: spotify:artist:testartist, '
                          f'frankie1: spotify:artist:testartist', stdout)
            self.assertIn(f'Album URI{" " * 21}spotify:album:testid0', stdout)
            self.assertIn(f'Release date{" " * 18}never lol', stdout)
            self.assertIn(f'Duration{" " * 22}23984723ms (6h 39m 44s)', stdout)
            self.assertIn(f'Key{" " * 27}10', stdout)
            self.assertIn(f'Mode{" " * 26}0 (minor)', stdout)
            self.assertIn(f'Time signature{" " * 16}10', stdout)
            self.assertIn(f'Popularity{" " * 20}-3', stdout)
            self.assertIn(f'Acousticness{" " * 18}0.99', stdout)
            self.assertIn(f'Danceability{" " * 18}0.01', stdout)
            self.assertIn(f'Energy{" " * 24}0.7', stdout)
            self.assertIn(f'Instrumentalness{" " * 14}0.001', stdout)
            self.assertIn(f'Liveness{" " * 22}0.8', stdout)
            self.assertIn(f'Loudness{" " * 22}-50.0 dB', stdout)
            self.assertIn(f'Speechiness{" " * 19}0.1', stdout)
            self.assertIn(f'Valence{" " * 23}0.001', stdout)
            self.assertIn(f'Tempo{" " * 25}70.0 bpm', stdout)

    @ordered
    def test_millis_to_stamp(self):
        self.assertEqual(spotirec.millis_to_stamp(60 * 1000), '1m 0s')
        self.assertEqual(spotirec.millis_to_stamp(300 * 1000), '5m 0s')
        self.assertEqual(spotirec.millis_to_stamp(225 * 1000), '3m 45s')
        self.assertEqual(spotirec.millis_to_stamp(3690 * 1000), '1h 1m 30s')

    @ordered
    def test_transfer_playback(self):
        spotirec.conf.save_device({'id': 'testid0', 'name': 'test0', 'type': 'fridge'}, 'test')
        # should not cause system exit
        spotirec.transfer_playback('test')
        spotirec.conf.remove_device('test')

    @ordered
    def test_transfer_playback_error(self):
        self.assertRaises(SystemExit, spotirec.transfer_playback, device_id='this will not work')

    @ordered
    def test_filter_recommendations(self):
        test_data = {'tracks': [{'uri': 'spotify:track:testid0', 'artists': [{'uri': 'spotify:artist:testid0'}]},
                                {'uri': 'spotify:track:testid1', 'artists': [{'uri': 'spotify:artist:testid1'}]},
                                {'uri': 'spotify:track:testid2', 'artists': [{'uri': 'spotify:artist:testid2'}]},
                                {'uri': 'spotify:track:testid3', 'artists': [{'uri': 'spotify:artist:testid3'}]},
                                {'uri': 'spotify:track:testid4', 'artists': [{'uri': 'spotify:artist:testid1'}]},
                                {'uri': 'spotify:track:testid5', 'artists': [{'uri': 'spotify:artist:testid5'}]}]}
        spotirec.conf.add_to_blacklist(self.test_track2, 'spotify:track:testid2')
        spotirec.conf.add_to_blacklist(self.test_artist1, 'spotify:artist:testid1')
        valid = spotirec.filter_recommendations(test_data)
        # tracks 1, 2, and 4 should be removed
        self.assertNotIn('spotify:track:testid1', valid)
        self.assertNotIn('spotify:track:testid2', valid)
        self.assertNotIn('spotify:track:testid4', valid)
        # 0, 3, and 5 should remain
        self.assertIn('spotify:track:testid0', valid)
        self.assertIn('spotify:track:testid3', valid)
        self.assertIn('spotify:track:testid5', valid)
        # length should be 3
        self.assertEqual(len(valid), 3)
        spotirec.conf.remove_from_blacklist('spotify:track:testid2')
        spotirec.conf.remove_from_blacklist('spotify:artist:testid1')

    @ordered
    def test_print_tuning_options_no_file(self):
        expected = 'could not find tuning options file'
        spotirec.TUNING_FILE = 'this-does-not-exist'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.print_tuning_options)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_print_tuning_options_empty(self):
        expected = 'tuning options file is empty'
        spotirec.TUNING_FILE = 'fixtures/tuning-opts-empty'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.print_tuning_options)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_print_tuning_options_success(self):
        expected0 = 'Attribute           Data type   Range   Recommended range   Function'
        expected1 = 'note that recommendations may be scarce outside the recommended ranges. If the recommended ' \
                    'range is not available, they may only be scarce at extreme values.'
        spotirec.TUNING_FILE = 'tuning-opts'
        spotirec.print_tuning_options()
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_recommend(self):
        spotirec.args = mock.MockArgs()
        spotirec.recommend()
        self.assertEqual(spotirec.rec.seed, '')
        playlists = spotirec.conf.get_playlists()
        self.assertIn('spotirec-default', playlists.keys())
        spotirec.conf.remove_playlist('spotirec-default')

    @ordered
    def test_recommend_save_preset(self):
        spotirec.args = mock.MockArgs(save_preset=['test'])
        spotirec.recommend()
        presets = spotirec.conf.get_presets()
        self.assertIn('test', presets.keys())
        spotirec.conf.remove_preset('test')
        spotirec.conf.remove_playlist('spotirec-default')

    @ordered
    def test_recommend_no_tracks(self):
        def mock_filter(data):
            return []

        expected = 'received zero tracks with your options - adjust and try again'
        filter_func = spotirec.filter_recommendations
        spotirec.logger.set_level(log.INFO)
        spotirec.filter_recommendations = mock_filter
        spotirec.args = mock.MockArgs()
        self.assertRaises(SystemExit, spotirec.recommend)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')
        spotirec.filter_recommendations = filter_func

    @ordered
    def test_recommend_preserve(self):
        spotirec.args = mock.MockArgs(preserve=True)
        spotirec.recommend()
        playlists = spotirec.conf.get_playlists()
        self.assertIn('spotirec-default', playlists.keys())
        spotirec.conf.remove_playlist('spotirec-default')

    @ordered
    def test_recommend_playlist_exists(self):
        spotirec.args = mock.MockArgs()
        spotirec.conf.save_playlist({'name': 'test', 'uri': 'spotify:playlist:testplaylist'}, 'spotirec-default')
        # should not cause system exit
        spotirec.recommend()
        spotirec.conf.remove_playlist('spotirec-default')

    @ordered
    def test_recommend_auto_play(self):
        spotirec.args = mock.MockArgs(play=['test'], n=1)
        spotirec.conf.save_device({'id': 'testid1', 'name': 'test1', 'type': 'microwave'}, 'test')
        spotirec.parse()
        # should not cause system exit
        spotirec.recommend()
        spotirec.conf.remove_playlist('spotirec-default')
        spotirec.conf.remove_device('test')

    @ordered
    def test_parse_b(self):
        spotirec.args = mock.MockArgs(b=['spotify:track:testtrack'])
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_from_blacklist('spotify:track:testtrack')

    @ordered
    def test_args_br(self):
        spotirec.args = mock.MockArgs(br=['spotify:track:testtrack'])
        spotirec.conf.add_to_blacklist({'name': 'test', 'uri': 'spotify:track:testtrack'}, 'spotify:track:testtrack')
        self.assertRaises(SystemExit, spotirec.parse)
        blacklist = spotirec.conf.get_blacklist()
        self.assertNotIn('spotify:track:testtrack', blacklist['tracks'])

    @ordered
    def test_args_bc_track(self):
        spotirec.args = mock.MockArgs(bc=['track'])
        self.assertRaises(SystemExit, spotirec.parse)
        blacklist = spotirec.conf.get_blacklist()
        self.assertIn('spotify:track:testtrack', blacklist['tracks'].keys())
        spotirec.conf.remove_from_blacklist('spotify:track:testtrack')

    @ordered
    def test_args_bc_artist(self):
        spotirec.args = mock.MockArgs(bc=['artist'])
        self.assertRaises(SystemExit, spotirec.parse)
        blacklist = spotirec.conf.get_blacklist()
        self.assertIn('spotify:artist:testartist', blacklist['artists'].keys())
        spotirec.conf.remove_from_blacklist('spotify:artist:testartist')

    @ordered
    def test_args_transfer_playback(self):
        spotirec.conf.save_device({'id': 'testid0', 'name': 'test0', 'type': 'fridge'}, 'test')
        spotirec.args = mock.MockArgs(transfer_playback=['test'])
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_device('test')

    @ordered
    def test_args_s(self):
        spotirec.args = mock.MockArgs(s=True)
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_sr(self):
        spotirec.args = mock.MockArgs(sr=True)
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_save_playlist(self):
        def mock_input_name(prompt: str):
            spotirec.input = mock_input_uri
            return 'test'

        def mock_input_uri(prompt: str):
            return 'spotify:playlist:testplaylist'

        spotirec.input = mock_input_name
        spotirec.args = mock.MockArgs(save_playlist=True)
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_playlist('test')

    @ordered
    def test_args_remove_playlists(self):
        spotirec.args = mock.MockArgs(remove_playlists=['test'])
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_save_device(self):
        def mock_input(prompt: str):
            return '0'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(save_device=True)
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_device('0')

    @ordered
    def test_args_remove_devices(self):
        spotirec.args = mock.MockArgs(remove_devices=['test'])
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_remove_presets(self):
        spotirec.args = mock.MockArgs(remove_presets=['test'])
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_add_to(self):
        spotirec.args = mock.MockArgs(add_to=['test'])
        spotirec.conf.save_playlist({'name': 'testplaylist', 'uri': 'spotify:playlist:testplaylist'}, 'test')
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_playlist('test')

    @ordered
    def test_args_remove_from(self):
        spotirec.args = mock.MockArgs(remove_from=['test'])
        spotirec.conf.save_playlist({'name': 'testplaylist', 'uri': 'spotify:playlist:testplaylist'}, 'test')
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_playlist('test')

    @ordered
    def test_args_print_artists(self):
        expected0 = f'0: frankie0{" " * 32}1: frankie1{" " * 32}2: frankie2\n'
        expected1 = f'3: frankie3{" " * 32}4: frankie4\n'
        spotirec.args = mock.MockArgs(print=['artists'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_args_print_tracks(self):
        expected0 = f'0: track0{" " * 34}1: track1{" " * 34}2: track2\n'
        expected1 = f'3: track3{" " * 34}4: track4\n'
        spotirec.args = mock.MockArgs(print=['tracks'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_args_print_genres(self):
        expected0 = f'0: pop{" " * 37}1: vapor-death-pop{" " * 25}2: metal\n'
        expected1 = f'3: holidays{" " * 32}4: metalcore\n'
        spotirec.args = mock.MockArgs(print=['genres'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)


    @ordered
    def test_args_print_genre_seeds(self):
        expected0 = f'0: metal{" " * 35}1: metalcore{" " * 31}2: pop\n'
        expected1 = f'3: vapor-death-pop{" " * 25}4: holidays\n'
        spotirec.args = mock.MockArgs(print=['genre-seeds'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_args_print_blacklist(self):
        spotirec.args = mock.MockArgs(print=['blacklist'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn('Tracks', stdout)
            self.assertIn('Artists', stdout)

    @ordered
    def test_args_print_devices(self):
        expected = f'ID{" " * 18}Name{" " * 16}Type'
        spotirec.args = mock.MockArgs(print=['devices'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_args_print_presets(self):
        expected = f'Name{" " * 16}Type{" " * 21}Params{" " * 44}Seeds'
        spotirec.args = mock.MockArgs(print=['presets'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_args_print_playlists(self):
        expected = f'ID{" " * 18}Name{" " * 26}URI'
        spotirec.args = mock.MockArgs(print=['playlists'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_args_print_tuning(self):
        expected0 = 'Attribute           Data type   Range   Recommended range   Function'
        expected1 = 'note that recommendations may be scarce outside the recommended ranges. If the recommended ' \
                    'range is not available, they may only be scarce at extreme values.'
        spotirec.args = mock.MockArgs(print=['tuning'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_args_track_features_current(self):
        spotirec.args = mock.MockArgs(track_features=['current'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn('track0 - frankie0, frankie1', stdout)
            self.assertIn(f'Track URI{" " * 21}spotify:track:testtrack', stdout)
            self.assertIn(f'Artist URI(s){" " * 17}frankie0: spotify:artist:testartist, '
                          f'frankie1: spotify:artist:testartist', stdout)
            self.assertIn(f'Album URI{" " * 21}spotify:album:testid0', stdout)
            self.assertIn(f'Release date{" " * 18}never lol', stdout)
            self.assertIn(f'Duration{" " * 22}23984723ms (6h 39m 44s)', stdout)
            self.assertIn(f'Key{" " * 27}10', stdout)
            self.assertIn(f'Mode{" " * 26}0 (minor)', stdout)
            self.assertIn(f'Time signature{" " * 16}10', stdout)
            self.assertIn(f'Popularity{" " * 20}-3', stdout)
            self.assertIn(f'Acousticness{" " * 18}0.99', stdout)
            self.assertIn(f'Danceability{" " * 18}0.01', stdout)
            self.assertIn(f'Energy{" " * 24}0.7', stdout)
            self.assertIn(f'Instrumentalness{" " * 14}0.001', stdout)
            self.assertIn(f'Liveness{" " * 22}0.8', stdout)
            self.assertIn(f'Loudness{" " * 22}-50.0 dB', stdout)
            self.assertIn(f'Speechiness{" " * 19}0.1', stdout)
            self.assertIn(f'Valence{" " * 23}0.001', stdout)
            self.assertIn(f'Tempo{" " * 25}70.0 bpm', stdout)

    @ordered
    def test_args_track_features_uri(self):
        spotirec.args = mock.MockArgs(track_features=['spotify:track:testtrack'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn('track0 - frankie0, frankie1', stdout)
            self.assertIn(f'Track URI{" " * 21}spotify:track:testtrack', stdout)
            self.assertIn(f'Artist URI(s){" " * 17}frankie0: spotify:artist:testartist, '
                          f'frankie1: spotify:artist:testartist', stdout)
            self.assertIn(f'Album URI{" " * 21}spotify:album:testid0', stdout)
            self.assertIn(f'Release date{" " * 18}never lol', stdout)
            self.assertIn(f'Duration{" " * 22}23984723ms (6h 39m 44s)', stdout)
            self.assertIn(f'Key{" " * 27}10', stdout)
            self.assertIn(f'Mode{" " * 26}0 (minor)', stdout)
            self.assertIn(f'Time signature{" " * 16}10', stdout)
            self.assertIn(f'Popularity{" " * 20}-3', stdout)
            self.assertIn(f'Acousticness{" " * 18}0.99', stdout)
            self.assertIn(f'Danceability{" " * 18}0.01', stdout)
            self.assertIn(f'Energy{" " * 24}0.7', stdout)
            self.assertIn(f'Instrumentalness{" " * 14}0.001', stdout)
            self.assertIn(f'Liveness{" " * 22}0.8', stdout)
            self.assertIn(f'Loudness{" " * 22}-50.0 dB', stdout)
            self.assertIn(f'Speechiness{" " * 19}0.1', stdout)
            self.assertIn(f'Valence{" " * 23}0.001', stdout)
            self.assertIn(f'Tempo{" " * 25}70.0 bpm', stdout)

    @ordered
    def test_args_a(self):
        spotirec.args = mock.MockArgs(a=5)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'top artists')
        self.assertEqual(spotirec.rec.seed_type, 'artists')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 5)
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'frankie0', 'id': 'testid0', 'type': 'artist'},
                                                      1: {'name': 'frankie1', 'id': 'testid1', 'type': 'artist'},
                                                      2: {'name': 'frankie2', 'id': 'testid2', 'type': 'artist'},
                                                      3: {'name': 'frankie3', 'id': 'testid3', 'type': 'artist'},
                                                      4: {'name': 'frankie4', 'id': 'testid4', 'type': 'artist'}})

    @ordered
    def test_args_t(self):
        spotirec.args = mock.MockArgs(t=5)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'top tracks')
        self.assertEqual(spotirec.rec.seed_type, 'tracks')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 5)
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'track0', 'id': 'testid0', 'type': 'track',
                                                          'artists': ['frankie0', 'frankie1']},
                                                      1: {'name': 'track1', 'id': 'testid1', 'type': 'track',
                                                          'artists': ['frankie1']},
                                                      2: {'name': 'track2', 'id': 'testid2', 'type': 'track',
                                                          'artists': ['frankie2', 'frankie1']},
                                                      3: {'name': 'track3', 'id': 'testid3', 'type': 'track',
                                                          'artists': ['frankie3', 'frankie1']},
                                                      4: {'name': 'track4', 'id': 'testid4', 'type': 'track',
                                                          'artists': ['frankie4', 'frankie3']}})

    @ordered
    def test_args_gcs(self):
        def mock_input(prompt: str):
            return '0 1 3'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(gcs=True)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'custom seed genres')
        self.assertEqual(spotirec.rec.seed_type, 'genres')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 3)
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'metal', 'type': 'genre'},
                                                      1: {'name': 'metalcore', 'type': 'genre'},
                                                      2: {'name': 'vapor-death-pop', 'type': 'genre'}})

    @ordered
    def test_args_ac(self):
        def mock_input(prompt: str):
            return '1 2'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(ac=True)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'custom artists')
        self.assertEqual(spotirec.rec.seed_type, 'artists')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 2)
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'frankie1', 'id': 'testid1', 'type': 'artist'},
                                                      1: {'name': 'frankie2', 'id': 'testid2', 'type': 'artist'}})

    @ordered
    def test_args_tc(self):
        def mock_input(prompt: str):
            return '0 4'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(tc=True)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'custom tracks')
        self.assertEqual(spotirec.rec.seed_type, 'tracks')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 2)
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'track0', 'id': 'testid0', 'type': 'track',
                                                          'artists': ['frankie0', 'frankie1']},
                                                      1: {'name': 'track4', 'id': 'testid4', 'type': 'track',
                                                          'artists': ['frankie4', 'frankie3']}})

    @ordered
    def test_args_gc(self):
        def mock_input(prompt: str):
            return '0'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(gc=True)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'custom top genres')
        self.assertEqual(spotirec.rec.seed_type, 'genres')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 1)
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'pop', 'type': 'genre'}})

    @ordered
    def test_args_c_sigint(self):
        def mock_input(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(c=True)
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_c_no_input(self):
        def mock_input(prompt: str):
            return ''

        spotirec.logger.set_level(log.INFO)
        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(c=True)
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            crash_file = stdout.split('/')[1].strip('\n')
            os.remove(f'fixtures/{crash_file}')

    @ordered
    def test_args_c(self):
        def mock_input(prompt: str):
            return 'vapor-death-pop spotify:track:testtrack spotify:artist:testartist'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(c=True)
        spotirec.parse()
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 3)
        self.assertDictEqual(spotirec.rec.seed_info, {0: {'name': 'vapor-death-pop', 'type': 'genre'},
                                                      1: {'name': 'track0', 'id': 'testtrack', 'type': 'track',
                                                          'artists': ['frankie0', 'frankie1']},
                                                      2: {'name': 'frankie0', 'id': 'testartist', 'type': 'artist'}})

    @ordered
    def test_args_l(self):
        spotirec.args = mock.MockArgs(l=[83], n=1)
        spotirec.parse()
        self.assertEqual(spotirec.rec.limit, 83)
        self.assertEqual(spotirec.rec.limit_original, 83)

    @ordered
    def test_args_tune(self):
        spotirec.args = mock.MockArgs(tune=['min_tempo=160'], n=1)
        spotirec.parse()
        self.assertDictEqual(spotirec.rec.rec_params, {'limit': '20', 'min_tempo': '160'})

    @ordered
    def test_setup_config_dir(self):
        spotirec.setup_config_dir()
        os.rmdir(spotirec.CONFIG_PATH)

    @ordered
    def test_authorize(self):
        def mock_run(host: str, port: int):
            return

        spotirec.webbrowser = mock.MockWebbrowser()
        spotirec.run = mock_run
        spotirec.authorize()
        self.assertEqual(spotirec.webbrowser.url, 'https://real.url')

    @ordered
    def test_create_parser(self):
        parser = spotirec.create_parser()
        args = parser.parse_args()
        self.assertIn('a', args)
        self.assertIsNone(args.a)
        self.assertIn('ac', args)
        self.assertFalse(args.ac)
        self.assertIn('add_to', args)
        self.assertIsNone(args.add_to)
        self.assertIn('b', args)
        self.assertIsNone(args.b)
        self.assertIn('bc', args)
        self.assertIsNone(args.bc)
        self.assertIn('br', args)
        self.assertIsNone(args.br)
        self.assertIn('c', args)
        self.assertFalse(args.c)
        self.assertIn('debug', args)
        self.assertFalse(args.debug)
        self.assertIn('gc', args)
        self.assertFalse(args.gc)
        self.assertIn('gcs', args)
        self.assertFalse(args.gcs)
        self.assertIn('l', args)
        self.assertIsNone(args.l)
        self.assertIn('load_preset', args)
        self.assertIsNone(args.load_preset)
        self.assertIn('log', args)
        self.assertFalse(args.log)
        self.assertIn('n', args)
        self.assertEqual(args.n, 5)
        self.assertIn('play', args)
        self.assertIsNone(args.play)
        self.assertIn('preserve', args)
        self.assertFalse(args.preserve)
        self.assertIn('print', args)
        self.assertIsNone(args.print)
        self.assertIn('quiet', args)
        self.assertFalse(args.quiet)
        self.assertIn('remove_devices', args)
        self.assertIsNone(args.remove_devices)
        self.assertIn('remove_from', args)
        self.assertIsNone(args.remove_from)
        self.assertIn('remove_playlists', args)
        self.assertIsNone(args.remove_playlists)
        self.assertIn('remove_presets', args)
        self.assertIsNone(args.remove_presets)
        self.assertIn('s', args)
        self.assertFalse(args.s)
        self.assertIn('save_device', args)
        self.assertFalse(args.save_device)
        self.assertIn('save_playlist', args)
        self.assertFalse(args.save_playlist)
        self.assertIn('save_preset', args)
        self.assertIsNone(args.save_preset)
        self.assertIn('sr', args)
        self.assertFalse(args.sr)
        self.assertIn('suppress_warnings', args)
        self.assertFalse(args.suppress_warnings)
        self.assertIn('t', args)
        self.assertIsNone(args.t)
        self.assertIn('tc', args)
        self.assertFalse(args.tc)
        self.assertIn('track_features', args)
        self.assertIsNone(args.track_features)
        self.assertIn('transfer_playback', args)
        self.assertIsNone(args.transfer_playback)
        self.assertIn('tune', args)
        self.assertIsNone(args.tune)
        self.assertIn('verbose', args)
        self.assertFalse(args.verbose)

    @ordered
    def test_init(self):
        def mock_get_token():
            return 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f'

        def mock_get_user_top_genres():
            return {'metal': 3, 'vapor-death-pop': 7, 'metalcore': 2, 'pop': 1, 'poo': 23}

        get_token_save = spotirec.get_token
        top_genres_save = spotirec.get_user_top_genres
        spotirec.get_token = mock_get_token
        spotirec.get_user_top_genres = mock_get_user_top_genres
        expected_args = spotirec.create_parser().parse_args()
        spotirec.init()
        self.assertEqual(spotirec.args, expected_args)
        self.assertIsInstance(spotirec.logger, log.Log)
        self.assertIsInstance(spotirec.conf, conf.Config)
        self.assertIsInstance(spotirec.conf.LOGGER, log.Log)
        self.assertIsInstance(spotirec.api, api.API)
        self.assertIsInstance(spotirec.api.LOGGER, log.Log)
        self.assertIsInstance(spotirec.api.CONF, conf.Config)
        self.assertIsInstance(spotirec.sp_oauth, oauth2.SpotifyOAuth)
        self.assertIsInstance(spotirec.sp_oauth.LOGGER, log.Log)
        self.assertIsInstance(spotirec.sp_oauth.CONF, conf.Config)
        self.assertIsInstance(spotirec.sp_oauth.API, api.API)
        self.assertDictEqual(spotirec.headers, {'Content-Type': 'application/json',
                                                'Authorization': 'Bearer f6952d6eef555ddd87aca66e56b91530222d6e3184148'
                                                                 '16f3ba7cf5bf694bf0f'})
        self.assertIsInstance(spotirec.rec, recommendation.Recommendation)
        spotirec.get_token = get_token_save
        spotirec.get_user_top_genres = top_genres_save

    @ordered
    def test_init_args_verbose(self):
        def mock_get_token():
            return 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f'

        def mock_get_user_top_genres():
            return {'metal': 3, 'vapor-death-pop': 7, 'metalcore': 2, 'pop': 1, 'poo': 23}

        get_token_save = spotirec.get_token
        top_genres_save = spotirec.get_user_top_genres
        spotirec.get_token = mock_get_token
        spotirec.get_user_top_genres = mock_get_user_top_genres
        spotirec.args = mock.MockArgs(verbose=True)
        spotirec.init()
        self.assertEqual(spotirec.logger.LEVEL, log.VERBOSE)
        spotirec.get_token = get_token_save
        spotirec.get_user_top_genres = top_genres_save

    @ordered
    def test_init_args_quiet(self):
        def mock_get_token():
            return 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f'

        def mock_get_user_top_genres():
            return {'metal': 3, 'vapor-death-pop': 7, 'metalcore': 2, 'pop': 1, 'poo': 23}

        get_token_save = spotirec.get_token
        top_genres_save = spotirec.get_user_top_genres
        spotirec.get_token = mock_get_token
        spotirec.get_user_top_genres = mock_get_user_top_genres
        spotirec.args = mock.MockArgs(quiet=True)
        spotirec.init()
        self.assertEqual(spotirec.logger.LEVEL, log.WARNING)
        spotirec.get_token = get_token_save
        spotirec.get_user_top_genres = top_genres_save

    @ordered
    def test_init_args_debug(self):
        def mock_get_token():
            return 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f'

        def mock_get_user_top_genres():
            return {'metal': 3, 'vapor-death-pop': 7, 'metalcore': 2, 'pop': 1, 'poo': 23}

        get_token_save = spotirec.get_token
        top_genres_save = spotirec.get_user_top_genres
        spotirec.get_token = mock_get_token
        spotirec.get_user_top_genres = mock_get_user_top_genres
        spotirec.args = mock.MockArgs(debug=True)
        spotirec.init()
        self.assertEqual(spotirec.logger.LEVEL, log.DEBUG)
        spotirec.get_token = get_token_save
        spotirec.get_user_top_genres = top_genres_save

    @ordered
    def test_init_args_suppress_warnings(self):
        def mock_get_token():
            return 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f'

        def mock_get_user_top_genres():
            return {'metal': 3, 'vapor-death-pop': 7, 'metalcore': 2, 'pop': 1, 'poo': 23}

        get_token_save = spotirec.get_token
        top_genres_save = spotirec.get_user_top_genres
        spotirec.get_token = mock_get_token
        spotirec.get_user_top_genres = mock_get_user_top_genres
        spotirec.args = mock.MockArgs(suppress_warnings=True)
        spotirec.init()
        self.assertTrue(spotirec.logger.SUPPRESS_WARNINGS)
        spotirec.get_token = get_token_save
        spotirec.get_user_top_genres = top_genres_save

    @ordered
    def test_init_args_load_preset(self):
        def mock_get_token():
            return 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f'

        class MockConfig:
            def Config(self):
                config = conf.Config()
                config.CONFIG_DIR = 'fixtures'
                config.CONFIG_FILE = 'test.conf'
                return config

        preset = {'limit': 100, 'based_on': 'top artists', 'seed': 'hip-hop,metalcore,metal,pop,death-metal',
                  'seed_type': 'tracks', 'seed_info':
                      {0: {'name': 'hip-hop', 'type': 'genre'}, 1: {'name': 'metalcore', 'type': 'genre'},
                       2: {'name': 'metal', 'type': 'genre'}, 3: {'name': 'pop', 'type': 'genre'},
                       4: {'name': 'death-metal', 'type': 'genre'}},
                  'rec_params': {'limit': '100', 'seed_genres': 'hip-hop,metalcore,metal,pop,death-metal'},
                  'auto_play': True, 'playback_device': {}}
        spotirec.conf.save_preset(preset, 'test-preset')
        get_token_save = spotirec.get_token
        spotirec.get_token = mock_get_token
        spotirec.sp_conf = MockConfig()
        spotirec.args = mock.MockArgs(load_preset=['test-preset'])
        spotirec.init()
        self.assertEqual(preset['limit'], spotirec.rec.limit)
        self.assertEqual(preset['limit'], spotirec.rec.limit_original)
        self.assertEqual(preset['based_on'], spotirec.rec.based_on)
        self.assertEqual(preset['seed'], spotirec.rec.seed)
        self.assertEqual(preset['seed_type'], spotirec.rec.seed_type)
        self.assertDictEqual(preset['seed_info'], spotirec.rec.seed_info)
        self.assertDictEqual(preset['rec_params'], spotirec.rec.rec_params)
        self.assertTrue(spotirec.rec.auto_play)
        self.assertDictEqual(preset['playback_device'], spotirec.rec.playback_device)
        spotirec.get_token = get_token_save
        spotirec.conf.remove_preset('test-preset')

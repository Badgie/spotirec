import unittest
import os
import sys
import time
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
        self.assertIn('items', recs.keys())
        self.assertTrue(any(x['name'] == 'track4' for x in recs['items']))
        self.assertTrue(any(x['uri'] == 'spotify:track:testid2' for x in recs['items']))

    @ordered
    def test_request_data_artist(self):
        artist = self.api.request_data('spotify:artist:testartist', 'artists', self.headers)
        self.assertEqual('frankie0', artist['name'])
        self.assertEqual('spotify:artist:testid0', artist['uri'])
        self.assertListEqual(['poo', 'poop'], artist['genres'])

    @ordered
    def test_request_data_track(self):
        track = self.api.request_data('spotify:track:testtrack', 'tracks', self.headers)
        self.assertEqual('track0', track['name'])
        self.assertEqual('spotify:track:testid0', track['uri'])
        self.assertEqual('testid0', track['id'])

    @ordered
    def test_get_genre_seeds(self):
        seeds = self.api.get_genre_seeds(self.headers)
        self.assertIn('genres', seeds.keys())
        self.assertIn('vapor-death-pop', seeds['genres'])
        self.assertIn('poo', seeds['genres'])

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
        self.assertEqual('spotify:track:testid0', uri)

    @ordered
    def test_get_current_artists(self):
        artists = self.api.get_current_artists(self.headers)
        self.assertListEqual(['spotify:artist:testid0', 'spotify:artist:testid1'], artists)

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
        spotirec.api = api.API()
        spotirec.api.URL_BASE = ''
        spotirec.api.requests = mock.MockAPI()
        spotirec.api.set_logger(spotirec.logger)
        spotirec.api.set_conf(spotirec.conf)
        spotirec.rec = recommendation.Recommendation()
        spotirec.rec.set_logger(spotirec.logger)
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

    @ordered
    def test_index(self):
        return

    @ordered
    def test_get_token(self):
        self.assertEqual(spotirec.get_token(), 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')

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
    def test_save_preset(self):
        presets = spotirec.conf.get_presets()
        self.assertNotIn('test', presets.keys())
        spotirec.save_preset('test')
        presets = spotirec.conf.get_presets()
        self.assertIn('test', presets.keys())

    @ordered
    def test_remove_presets(self):
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
        spotirec.remove_presets(['test'])

    @ordered
    def test_get_device_error(self):
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.get_device, device_name='test')
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
    def test_remove_devices(self):
        spotirec.conf.save_device(self.test_device0, 'test')
        devices = spotirec.conf.get_devices()
        self.assertIn('test', devices.keys())
        spotirec.remove_devices(['test'])
        devices = spotirec.conf.get_devices()
        self.assertNotIn('test', devices.keys())

    @ordered
    def print_saved_devices(self):
        expected0 = f'ID{" " * 18}Name{" " * 16}Type'
        expected1 = f'testid{" " * 14}test{" " * 16}tester'
        spotirec.conf.save_device(self.test_device0, 'test')
        spotirec.print_saved_devices()
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

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
    def test_remove_current_track_error(self):
        playlists = spotirec.conf.get_playlists()
        self.assertNotIn('test', playlists.keys())
        self.assertRaises(SystemExit, spotirec.remove_current_track, playlist='test')

    @ordered
    def test_millis_to_stamp(self):
        self.assertEqual(spotirec.millis_to_stamp(60 * 1000), '1m 0s')
        self.assertEqual(spotirec.millis_to_stamp(300 * 1000), '5m 0s')
        self.assertEqual(spotirec.millis_to_stamp(225 * 1000), '3m 45s')
        self.assertEqual(spotirec.millis_to_stamp(3690 * 1000), '1h 1m 30s')

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

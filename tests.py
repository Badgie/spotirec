import unittest
import os
import sys
import time
import conf
import api
import log
import oauth2
import recommendation


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
        self.assertEqual(oauth['expires_at'], '1584875483')
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

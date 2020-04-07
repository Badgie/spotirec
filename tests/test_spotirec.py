from tests.lib import ordered, mock, runner
from tests.lib.ut_ext import SpotirecTestCase
from spotirec import oauth2, api, conf, log, recommendation, spotirec
import os
import sys
import time
import errno
from PIL import Image


class TestSpotirec(SpotirecTestCase):
    """
    Running tests for spotirec.py
    """

    @classmethod
    def setUpClass(cls) -> None:
        """
        Setup any necessary data or states before any tests in this class is run
        """
        if runner.verbosity > 0:
            super(TestSpotirec, cls).setUpClass()
            print(f'file:/{__file__}\n')
        spotirec.logger = log.Log()
        spotirec.conf = conf.Config()
        spotirec.conf.set_logger(spotirec.logger)
        spotirec.sp_oauth = oauth2.SpotifyOAuth()
        spotirec.sp_oauth.set_logger(spotirec.logger)
        spotirec.sp_oauth.set_conf(spotirec.conf)
        spotirec.api = api.API()
        spotirec.api.requests = mock.MockAPI()
        spotirec.api.set_logger(spotirec.logger)
        spotirec.api.set_conf(spotirec.conf)
        spotirec.sp_oauth.set_api(spotirec.api)
        spotirec.headers = \
            {'Content-Type': 'application/json', 'Authorization':
                'Bearer f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f'}
        cls.test_track0 = {'name': 'test0', 'id': 'testid0', 'type': 'track', 'artists':
                           [{'name': 'frankie0'}]}
        cls.test_track1 = {'name': 'test1', 'id': 'testid1', 'type': 'track', 'artists':
                           [{'name': 'frankie1'}]}
        cls.test_track2 = {'name': 'test2', 'id': 'testid2', 'type': 'track', 'artists':
                           [{'name': 'frankie2'}]}
        cls.test_artist0 = {'name': 'frankie0', 'id': 'testid0', 'type': 'artist'}
        cls.test_artist1 = {'name': 'frankie1', 'id': 'testid1', 'type': 'artist'}
        cls.test_artist2 = {'name': 'frankie2', 'id': 'testid2', 'type': 'artist'}
        cls.test_device0 = {'id': 'testid', 'name': 'test', 'type': 'tester'}
        cls.test_playlist0 = {'name': 'test', 'uri': 'spotify:playlist:testid'}
        cls.stdout_preserve = sys.__stdout__

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Clear or resolve any necessary data or states after all tests in this class are run
        """
        if runner.verbosity > 0:
            super(TestSpotirec, cls).tearDownClass()

    def setUp(self):
        """
        Setup any necessary data or states before each test is run
        """
        spotirec.CONFIG_PATH = 'tests/fixtures/.config'
        spotirec.logger.set_level(0)
        spotirec.rec = recommendation.Recommendation()
        spotirec.rec.set_logger(spotirec.logger)
        spotirec.logger.LOG_PATH = 'tests/fixtures'
        spotirec.conf.CONFIG_DIR = 'tests/fixtures'
        spotirec.conf.CONFIG_FILE = 'test.conf'
        spotirec.sp_oauth.OAUTH_TOKEN_URL = '/api/token'
        spotirec.sp_oauth.OAUTH_AUTH_URL = '/authorize'
        spotirec.sp_oauth.client_secret = 'client_secret'
        spotirec.sp_oauth.client_id = 'client_id'
        spotirec.sp_oauth.redirect = 'https://real.url'
        spotirec.sp_oauth.scopes = ['user-modify-playback-state', 'ugc-image-upload',
                                    'user-library-modify']
        spotirec.api.URL_BASE = ''
        self.test_log = 'tests/fixtures/test-log'
        self.log_file = open(self.test_log, 'w')
        sys.stdout = self.log_file

    def tearDown(self):
        """
        Clear or resolve any necessary data or states after each test is run
        """
        self.log_file.close()
        sys.stdout = self.stdout_preserve
        if os.path.isfile(self.test_log):
            os.remove(self.test_log)
        spotirec.input = input
        spotirec.args = spotirec.create_parser().parse_args()

    @ordered
    def test_index_no_code(self):
        """
        Testing index() without url code
        """
        spotirec.request = mock.MockRequest('https://real.url')
        expected = "<a href='/authorize?client_id=client_id&response_type=code&" \
                   "redirect_uri=https%3A%2F%2Freal.url%3A0&scope=user-modify-playback-state+" \
                   "ugc-image-upload+user-library-modify'>Login to Spotify</a>"
        res = spotirec.index()
        self.assertEqual(res, expected)

    @ordered
    def test_index_code(self):
        """
        Testing index() with url code
        """
        spotirec.conf.CONFIG_FILE = 'test-index.conf'
        spotirec.request = mock.MockRequest('https://real.url?code=testcode')
        expected = '<span>Successfully retrieved OAuth token. You may close this tab and start ' \
                   'using Spotirec.</span>'
        expected_expire = str(round(time.time()) + 3600)
        res = spotirec.index()
        self.assertEqual(res, expected)

        oauth = spotirec.conf.get_oauth()
        self.assertEqual(oauth['access_token'],
                         'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')
        self.assertEqual(oauth['token_type'], 'Bearer')
        self.assertEqual(oauth['expires_in'], '3600')
        self.assertEqual(oauth['scope'],
                         'user-modify-playback-state ugc-image-upload user-library-modify')
        self.assertEqual(oauth['expires_at'], expected_expire)
        self.assertEqual(oauth['refresh_token'],
                         '737dd1bca21d67a7c158ed425276b04581e3c2b1f209e25a7cff37d8cb333f0f')
        os.remove('tests/fixtures/test-index.conf')

    @ordered
    def test_get_token(self):
        """
        Testing get_token() success
        """
        self.assertEqual(spotirec.get_token(),
                         'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f')

    @ordered
    def test_get_token_fail(self):
        """
        Testing get_token() fail
        """

        def mock_authorize():
            self.test = 'success'

        self.test = ''
        auth_save = spotirec.authorize
        spotirec.authorize = mock_authorize
        spotirec.conf.CONFIG_FILE = 'empty.conf'
        self.assertRaises(SystemExit, spotirec.get_token)
        self.assertEqual(self.test, 'success')
        spotirec.authorize = auth_save
        with open('tests/fixtures/empty.conf', 'w') as f:
            f.write('')

    @ordered
    def test_get_user_top_genres(self):
        """
        Testing get_user_top_genres()
        """
        genres = spotirec.get_user_top_genres()
        self.assertEqual(list(genres.keys()),
                         ['pop', 'metal', 'vapor-death-pop', 'holidays', 'metalcore'])

    @ordered
    def test_add_top_genres_seed(self):
        """
        Testing add_top_genres_seed()
        """
        spotirec.add_top_genres_seed(5)
        self.assertNotEqual(spotirec.rec.seed_info, {})
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'pop', 'type': 'genre'},
                              1: {'name': 'vapor-death-pop', 'type': 'genre'},
                              2: {'name': 'metal', 'type': 'genre'},
                              3: {'name': 'holidays', 'type': 'genre'},
                              4: {'name': 'metalcore', 'type': 'genre'}})

    @ordered
    def test_add_top_genres_seed_out_of_bounds(self):
        """
        Testing add_top_genres_seed() more seeds than available
        """
        spotirec.add_top_genres_seed(7)
        self.assertNotEqual(spotirec.rec.seed_info, {})
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'pop', 'type': 'genre'},
                              1: {'name': 'vapor-death-pop', 'type': 'genre'},
                              2: {'name': 'metal', 'type': 'genre'},
                              3: {'name': 'holidays', 'type': 'genre'},
                              4: {'name': 'metalcore', 'type': 'genre'}})

    @ordered
    def test_print_choices(self):
        """
        Testing print_choices() default
        """
        expected = f'0: metal{" " * 34}1: metalcore{" " * 30}2: vapor-death-pop\n3: pop\n'
        spotirec.print_choices(data=['metal', 'metalcore', 'vapor-death-pop', 'pop'], prompt=False)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertEqual(expected, stdout)

    @ordered
    def test_print_choices_sorted(self):
        """
        Testing print_choices() sorted
        """
        expected = f'0: vapor-death-pop{" " * 24}1: metalcore{" " * 30}2: metal\n3: pop\n'
        spotirec.print_choices(data={'metal': 3, 'metalcore': 7, 'vapor-death-pop': 23, 'pop': 1},
                               prompt=False, sort=True)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertEqual(expected, stdout)

    @ordered
    def test_print_choices_prompt_genres(self):
        """
        Testing print_choices() with genre prompt
        """
        def mock_input(prompt: str):
            return '0 2'
        spotirec.input = mock_input
        spotirec.print_choices(data=['metal', 'metalcore', 'vapor-death-pop', 'pop'])
        self.assertNotEqual(spotirec.rec.seed_info, {})
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'metal', 'type': 'genre'},
                              1: {'name': 'vapor-death-pop', 'type': 'genre'}})

    @ordered
    def test_print_choices_prompt_other(self):
        """
        Testing print_choices() with artist/track prompt
        """
        def mock_input(prompt: str):
            return '1 2 3'
        spotirec.rec.seed_type = 'tracks'
        spotirec.input = mock_input
        choice = spotirec.print_choices(data=['metal', 'metalcore', 'vapor-death-pop', 'pop'])
        self.assertEqual(choice, mock_input(''))

    @ordered
    def test_print_choices_keyboard_interrupt(self):
        """
        Testing print_choices() sigint
        """
        def mock_input(prompt: str):
            raise KeyboardInterrupt
        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.print_choices, data=[])

    @ordered
    def test_print_artists_or_tracks(self):
        """
        Testing print_artists_or_tracks() default
        """
        data = {'items': [{'name': 'test0', 'id': 'test0'}, {'name': 'test1', 'id': 'test1'},
                          {'name': 'test2', 'id': 'test2'}, {'name': 'test3', 'id': 'test3'}]}
        expected = f'0: test0{" " * 34}1: test1{" " * 34}2: test2\n3: test3\n'
        spotirec.print_artists_or_tracks(data, prompt=False)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertEqual(expected, stdout)

    @ordered
    def test_print_artists_or_tracks_prompt(self):
        """
        Testing print_artists_or_tracks() prompt
        """
        def mock_input(prompt: str):
            return '0 2'
        spotirec.input = mock_input
        spotirec.rec.seed_type = 'artists'
        spotirec.print_artists_or_tracks(spotirec.api.get_top_list('artists', 20, spotirec.headers))
        self.assertNotEqual(spotirec.rec.seed_info, {})
        self.assertEqual(spotirec.rec.seed_info,
                         {0: {'id': 'testid0', 'name': 'frankie0', 'type': 'artist'},
                          1: {'id': 'testid2', 'name': 'frankie2', 'type': 'artist'}})

    @ordered
    def test_check_if_valid_genre_true(self):
        """
        Testing check_if_valid_genre() true
        """
        self.assertTrue(spotirec.check_if_valid_genre('vapor-death-pop'))

    @ordered
    def test_check_if_valid_genre_false(self):
        """
        Testing check_if_valid_genre() false
        """
        self.assertFalse(spotirec.check_if_valid_genre('vapor-death-jazz'))

    @ordered
    def test_check_tune_validity_success(self):
        """
        Testing check_tune_validity() success
        """
        expected = 'tune attribute tempo with prefix min and value 160.0 is valid'
        spotirec.logger.set_level(log.DEBUG)
        spotirec.check_tune_validity('min_tempo=160')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_check_tune_validity_improper_format(self):
        """
        Testing check_tune_validity() improper format
        """
        expected = 'tune max_tempo_160 does not match the proper format'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.check_tune_validity, tune='max_tempo_160')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_check_tune_validity_fail_prefix(self):
        """
        Testing check_tune_validity() invalid prefix
        """
        expected = 'tune prefix \"mox\" is malformed'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.check_tune_validity, tune='mox_tempo=160')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_check_tune_validity_fail_attribute(self):
        """
        Testing check_tune_validity() invalid attribute
        """
        expected = 'tune attribute \"tampo\" is malformed'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.check_tune_validity, tune='max_tampo=160')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_check_tune_validity_fail_value_type(self):
        """
        Testing check_tune_validity() invalid value
        """
        expected = 'tune value 160,0 does not match attribute tempo data type requirements'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.check_tune_validity, tune='max_tempo=160,0')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_check_tune_validity_fail_value_range(self):
        """
        Testing check_tune_validity() invalid value range
        """
        expected = 'value 300.0 for attribute tempo is outside the accepted range ' \
                   '(min: 0.0, max: 220.0)'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.check_tune_validity, tune='max_tempo=300')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_check_tune_validity_warn_value_range(self):
        """
        Testing check_tune_validity() outside recommended range
        """
        expected = 'value 215.0 for attribute tempo is outside the recommended range ' \
                   '(min: 60.0, max: 210.0), recommendations may be scarce'
        spotirec.logger.set_level(log.WARNING)
        spotirec.check_tune_validity('max_tempo=215')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_parse_seed_info_error_str(self):
        """
        Testing parse_seed_info() invalid str length
        """
        expected = 'please enter at most 5 seeds'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.parse_seed_info, seeds='0 1 2 3 4 5')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_parse_seed_info_error_list(self):
        """
        Testing parse_seed_info() invalid list length
        """
        expected = 'please enter at most 5 seeds'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.parse_seed_info, seeds=[0, 1, 2, 3, 4, 5])
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_parse_seed_info_genres_str(self):
        """
        Testing parse_seed_info() genres str
        """
        expected = {0: {'name': 'metal', 'type': 'genre'},
                    1: {'name': 'vapor-death-pop', 'type': 'genre'}}
        spotirec.rec.seed_type = 'genres'
        spotirec.parse_seed_info('metal vapor-death-pop')
        self.assertDictEqual(expected, spotirec.rec.seed_info)

    @ordered
    def test_parse_seed_info_genres_list(self):
        """
        Testing parse_seed_info() genres list
        """
        expected = {0: {'name': 'metal', 'type': 'genre'},
                    1: {'name': 'vapor-death-pop', 'type': 'genre'}}
        spotirec.rec.seed_type = 'genres'
        spotirec.parse_seed_info(['metal', 'vapor-death-pop'])
        self.assertDictEqual(expected, spotirec.rec.seed_info)

    @ordered
    def test_parse_seed_info_genres_tracks_list(self):
        """
        Testing parse_seed_info() tracks list
        """
        expected = {0: {'name': 'test0', 'id': 'testid0', 'type': 'track', 'artists': ['frankie0']},
                    1: {'name': 'test1', 'id': 'testid1', 'type': 'track', 'artists': ['frankie1']},
                    2: {'name': 'test2', 'id': 'testid2', 'type': 'track', 'artists': ['frankie2']}}
        spotirec.rec.seed_type = 'tracks'
        spotirec.parse_seed_info([self.test_track0, self.test_track1, self.test_track2])
        self.assertDictEqual(expected, spotirec.rec.seed_info)

    @ordered
    def test_parse_seed_info_genres_artists_list(self):
        """
        Testing parse_seed_info() artists list
        """
        expected = {0: {'name': 'frankie0', 'id': 'testid0', 'type': 'artist'},
                    1: {'name': 'frankie1', 'id': 'testid1', 'type': 'artist'},
                    2: {'name': 'frankie2', 'id': 'testid2', 'type': 'artist'}}
        spotirec.rec.seed_type = 'artists'
        spotirec.parse_seed_info([self.test_artist0, self.test_artist1, self.test_artist2])
        self.assertDictEqual(expected, spotirec.rec.seed_info)

    @ordered
    def test_parse_seed_info_custom_genres(self):
        """
        Testing parse_seed_info() custom genres
        """
        spotirec.rec.seed_type = 'custom'
        spotirec.parse_seed_info(['vapor-death-pop'])
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'vapor-death-pop', 'type': 'genre'}})

    @ordered
    def test_parse_seed_info_custom_uri(self):
        """
        Testing parse_seed_info() custom uri
        """
        spotirec.rec.seed_type = 'custom'
        spotirec.parse_seed_info(['spotify:track:testtrack'])
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'track0', 'id': 'testtrack', 'type': 'track',
                                  'artists': ['frankie0', 'frankie1']}})

    @ordered
    def test_parse_seed_info_custom_warning(self):
        """
        Testing parse_seed_info() custom uri warning
        """
        expected = 'input \"vapor-death-jazz\" does not match a genre or a valid URI syntax, ' \
                   'skipping...'
        spotirec.logger.set_level(log.WARNING)
        spotirec.rec.seed_type = 'custom'
        spotirec.parse_seed_info(['vapor-death-jazz'])
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_add_to_blacklist(self):
        """
        Testing add_to_blacklist()
        """
        spotirec.add_to_blacklist(['spotify:track:testtrack'])
        blacklist = spotirec.conf.get_blacklist()
        self.assertIn('spotify:track:testtrack', blacklist['tracks'].keys())
        self.assertDictEqual(blacklist['tracks']['spotify:track:testtrack'],
                             {'name': 'track0', 'uri': 'spotify:track:testtrack',
                              'artists': ['frankie0', 'frankie1']})
        spotirec.conf.remove_from_blacklist('spotify:track:testtrack')
        blacklist = spotirec.conf.get_blacklist()
        self.assertDictEqual(blacklist['tracks'], {})

    @ordered
    def test_remove_from_blacklist(self):
        """
        Testing remove_from_blacklist()
        """
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
        """
        Testing print_blacklist()
        """
        spotirec.conf.add_to_blacklist(self.test_track0, 'spotify:track:testid0')
        spotirec.conf.add_to_blacklist(self.test_artist0, 'spotify:artist:testid0')
        spotirec.print_blacklist()
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn('Tracks', stdout)
            self.assertIn('Artists', stdout)
            self.assertIn('test0 by frankie0 - spotify:track:testid0', stdout)
            self.assertIn('frankie0 - spotify:artist:testid0', stdout)

    @ordered
    def test_generate_img(self):
        """
        Testing generate_img()
        """
        img = spotirec.generate_img(['test:test:test', 'test:test:test', 'test:test:test'])
        # hash: 2eccd587915e21ab37d6352bb55cfc8754545daa6ba1c3be0b759d66fbb36acb
        # color: [46, 204, 213]
        self.assertTrue(any(x[1] == (46, 204, 213) for x in img.getcolors()))
        self.assertTrue(any(x[1] == (200, 200, 200) for x in img.getcolors()))
        self.assertEqual(img.size, (320, 320))
        # resize img
        img = img.resize((10, 10), Image.ANTIALIAS)
        # reduce colors
        img = img.convert('L')
        # find average pixel
        pixels = list(img.getdata())
        avg_pixel = sum(pixels) / len(pixels)
        # convert to bits
        bits = ''.join('1' if px >= avg_pixel else '0' for px in pixels)
        # hash
        hashed_img = str(hex(int(bits, 2)))[2:][::-1].upper()
        self.assertEqual(hashed_img, 'FC33689D57F00F814C01320C7')

    @ordered
    def test_add_image_to_playlist(self):
        """
        Testing add_image_to_playlist()
        """
        # should not cause system exit
        spotirec.rec.playlist_id = 'testplaylist'
        spotirec.add_image_to_playlist(['test:test:test', 'test:test:test', 'test:test:test'])

    @ordered
    def test_save_preset(self):
        """
        Testing save_preset()
        """
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
        """
        Testing load_preset()
        """
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
        """
        Testing load_preset() wrong iden
        """
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.load_preset, name='this-does-not-exist')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_remove_presets(self):
        """
        Testing remove_presets()
        """
        spotirec.save_preset('test')
        presets = spotirec.conf.get_presets()
        self.assertIn('test', presets.keys())
        spotirec.remove_presets(['test'])
        presets = spotirec.conf.get_presets()
        self.assertNotIn('test', presets.keys())

    @ordered
    def test_print_presets(self):
        """
        Testing print_presets()
        """
        expected0 = f'Name{" " * 16}Type{" " * 21}Params{" " * 44}Seeds'
        expected1 = f'test{" " * 16}top genres{" " * 15}limit=20{" " * 42}'
        spotirec.save_preset('test')
        spotirec.print_presets()
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)
        spotirec.conf.remove_preset('test')

    @ordered
    def test_get_device_error(self):
        """
        Testing get_device() wrong iden
        """
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.get_device, device_name='this-does-not-exist')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_get_device_success(self):
        """
        Testing get_device()
        """
        spotirec.conf.save_device(self.test_device0, 'test')
        device = spotirec.get_device('test')
        self.assertDictEqual(device, self.test_device0)
        spotirec.conf.remove_device('test')

    @ordered
    def test_save_device(self):
        """
        Testing save_device()
        """

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
        """
        Testing save_device() sigint index prompt
        """

        def mock_input(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.save_device)

    @ordered
    def test_save_device_sigint_name(self):
        """
        Testing save_device() sigint name prompt
        """

        def mock_input(prompt: str):
            spotirec.input = mock_input_name
            return ''

        def mock_input_name(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.save_device)

    @ordered
    def test_save_device_value_error(self):
        """
        Testing save_device() invalid index
        """

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
        """
        Testing save_device() invalid iden
        """

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
        self.assertDictEqual(devices['test'], {'id': 'testid1', 'name': 'test1',
                                               'type': 'microwave'})
        spotirec.conf.remove_device('test')

    @ordered
    def test_remove_devices(self):
        """
        Testing remove_devices()
        """
        spotirec.conf.save_device(self.test_device0, 'test')
        devices = spotirec.conf.get_devices()
        self.assertIn('test', devices.keys())
        spotirec.remove_devices(['test'])
        devices = spotirec.conf.get_devices()
        self.assertNotIn('test', devices.keys())

    @ordered
    def test_print_saved_devices(self):
        """
        Testing print_saved_devices()
        """
        expected0 = f'ID{" " * 18}Name{" " * 16}Type'
        expected1 = f'test{" " * 16}test{" " * 16}tester'
        spotirec.conf.save_device(self.test_device0, 'test')
        spotirec.print_saved_devices()
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)
        spotirec.conf.remove_device('test')

    @ordered
    def test_print_playlists(self):
        """
        Testing print_playlists()
        """
        expected0 = f'ID{" " * 18}Name{" " * 26}URI'
        expected1 = f'test{" " * 16}test{" " * 26}spotify:playlist:testid'
        spotirec.conf.save_playlist(self.test_playlist0, 'test')
        spotirec.print_playlists()
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)
        spotirec.conf.remove_playlist('test')

    @ordered
    def test_save_playlist(self):
        """
        Testing save_playlist()
        """

        def mock_input_uri(prompt: str):
            return 'spotify:playlist:testplaylist'

        def mock_input_name(prompt: str):
            spotirec.input = mock_input_uri
            return 'test'

        spotirec.input = mock_input_name
        spotirec.save_playlist()
        playlists = spotirec.conf.get_playlists()
        self.assertIn('test', playlists.keys())
        self.assertDictEqual(playlists['test'], {'name': 'testplaylist',
                                                 'uri': 'spotify:playlist:testplaylist'})
        spotirec.conf.remove_playlist('test')

    @ordered
    def test_save_playlist_sigint_name(self):
        """
        Testing save_playlist() sigint
        """

        def mock_input(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.save_playlist)

    @ordered
    def test_save_playlist_sigint_uri(self):
        """
        Testing save_playlist() sigint uri prompt
        """

        def mock_input_name(prompt: str):
            spotirec.input = mock_input_uri
            return 'test'

        def mock_input_uri(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input_name
        self.assertRaises(SystemExit, spotirec.save_playlist)

    @ordered
    def test_save_playlist_name_error(self):
        """
        Testing save_playlist() invalid name
        """

        def mock_input(prompt: str):
            spotirec.input = mock_input_sigint
            return 'this will not work'

        def mock_input_sigint(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        self.assertRaises(SystemExit, spotirec.save_playlist)

    @ordered
    def test_save_playlist_uri_error(self):
        """
        Testing save_playlist() invalid uri
        """

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
        self.assertDictEqual(playlists['test'], {'name': 'testplaylist',
                                                 'uri': 'spotify:playlist:testplaylist'})

    @ordered
    def test_remove_playlists(self):
        """
        Testing remove_playlists()
        """
        spotirec.conf.save_playlist(self.test_playlist0, 'test')
        playlists = spotirec.conf.get_playlists()
        self.assertIn('test', playlists.keys())
        spotirec.remove_playlists(['test'])
        playlists = spotirec.conf.get_playlists()
        self.assertNotIn('test', playlists.keys())

    @ordered
    def test_add_current_track_error(self):
        """
        Testing add_current_track() invalid playlist
        """
        playlists = spotirec.conf.get_playlists()
        self.assertNotIn('test', playlists.keys())
        self.assertRaises(SystemExit, spotirec.add_current_track, playlist='test')

    @ordered
    def test_add_current_track(self):
        """
        Testing add_current_track()
        """
        # should not cause system exit
        spotirec.add_current_track('spotify:playlist:testplaylist')

    @ordered
    def test_remove_current_track_error(self):
        """
        Testing remove_current_track() invalid playlist
        """
        playlists = spotirec.conf.get_playlists()
        self.assertNotIn('test', playlists.keys())
        self.assertRaises(SystemExit, spotirec.remove_current_track, playlist='test')

    @ordered
    def test_remove_current_track(self):
        """
        Testing remove_current_track()
        """
        # should not cause system exit
        spotirec.remove_current_track('spotify:playlist:testplaylist')

    @ordered
    def test_print_track_features_error(self):
        """
        Testing print_track_features() invalid uri
        """
        expected = 'this is not a URI is not a valid track URI'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.print_track_features, uri='this is not a URI')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_print_track_features(self):
        """
        Testing print_track_features()
        """
        spotirec.print_track_features('spotify:track:testtrack')
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
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
        """
        Testing millis_to_stamp()
        """
        self.assertEqual(spotirec.millis_to_stamp(60 * 1000), '1m 0s')
        self.assertEqual(spotirec.millis_to_stamp(300 * 1000), '5m 0s')
        self.assertEqual(spotirec.millis_to_stamp(225 * 1000), '3m 45s')
        self.assertEqual(spotirec.millis_to_stamp(3690 * 1000), '1h 1m 30s')

    @ordered
    def test_transfer_playback(self):
        """
        Testing transfer_playback()
        """
        spotirec.conf.save_device({'id': 'testid0', 'name': 'test0', 'type': 'fridge'}, 'test')
        # should not cause system exit
        spotirec.transfer_playback('test')
        spotirec.conf.remove_device('test')

    @ordered
    def test_transfer_playback_error(self):
        """
        Testing transfer_playback() invalid device
        """
        self.assertRaises(SystemExit, spotirec.transfer_playback, device_id='this will not work')

    @ordered
    def test_filter_recommendations(self):
        """
        Testing filter_recommendations()
        """
        test_data = \
            {'tracks': [{'uri': 'spotify:track:testid0', 'artists':
                        [{'uri': 'spotify:artist:testid0'}]},
                        {'uri': 'spotify:track:testid1', 'artists':
                        [{'uri': 'spotify:artist:testid1'}]},
                        {'uri': 'spotify:track:testid2', 'artists':
                        [{'uri': 'spotify:artist:testid2'}]},
                        {'uri': 'spotify:track:testid3', 'artists':
                        [{'uri': 'spotify:artist:testid3'}]},
                        {'uri': 'spotify:track:testid4', 'artists':
                        [{'uri': 'spotify:artist:testid1'}]},
                        {'uri': 'spotify:track:testid5', 'artists':
                        [{'uri': 'spotify:artist:testid5'}]}]}
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
        """
        Testing print_tuning_options() no file
        """
        expected = 'could not find tuning options file'
        spotirec.TUNING_FILE = 'this-does-not-exist'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.print_tuning_options)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_print_tuning_options_empty(self):
        """
        Testing print_tuning_options() empty file
        """
        expected = 'tuning options file is empty'
        spotirec.TUNING_FILE = 'tests/fixtures/tuning-opts-empty'
        spotirec.logger.set_level(log.INFO)
        self.assertRaises(SystemExit, spotirec.print_tuning_options)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_print_tuning_options_success(self):
        """
        Testing print_tuning_options()
        """
        expected0 = 'Attribute           Data type   Range   Recommended range   Function'
        expected1 = 'note that recommendations may be scarce outside the recommended ranges. ' \
                    'If the recommended range is not available, they may only be scarce at ' \
                    'extreme values.'
        spotirec.TUNING_FILE = 'tuning-opts'
        spotirec.print_tuning_options()
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_recommend(self):
        """
        Testing recommend()
        """
        spotirec.args = mock.MockArgs()
        spotirec.recommend()
        self.assertEqual(spotirec.rec.seed, '')
        playlists = spotirec.conf.get_playlists()
        self.assertIn('spotirec-default', playlists.keys())
        spotirec.conf.remove_playlist('spotirec-default')

    @ordered
    def test_recommend_save_preset(self):
        """
        Testing recommend() with save preset arg
        """
        spotirec.args = mock.MockArgs(save_preset=['test'])
        spotirec.recommend()
        presets = spotirec.conf.get_presets()
        self.assertIn('test', presets.keys())
        spotirec.conf.remove_preset('test')
        spotirec.conf.remove_playlist('spotirec-default')

    @ordered
    def test_recommend_no_tracks(self):
        """
        Testing recommend() yielding no tracks
        """

        def mock_filter(data):
            return []

        expected = 'received zero tracks with your options - adjust and try again'
        filter_func = spotirec.filter_recommendations
        spotirec.logger.set_level(log.INFO)
        spotirec.filter_recommendations = mock_filter
        spotirec.args = mock.MockArgs()
        self.assertRaises(SystemExit, spotirec.recommend)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')
        spotirec.filter_recommendations = filter_func

    @ordered
    def test_recommend_preserve(self):
        """
        Testing recommend() with preserve arg
        """
        spotirec.args = mock.MockArgs(preserve=True)
        spotirec.recommend()
        playlists = spotirec.conf.get_playlists()
        self.assertIn('spotirec-default', playlists.keys())
        spotirec.conf.remove_playlist('spotirec-default')

    @ordered
    def test_recommend_playlist_exists(self):
        """
        Testing recommend() with existing playlist
        """
        spotirec.args = mock.MockArgs()
        spotirec.conf.save_playlist({'name': 'test', 'uri': 'spotify:playlist:testplaylist'},
                                    'spotirec-default')
        # should not cause system exit
        spotirec.recommend()
        spotirec.conf.remove_playlist('spotirec-default')

    @ordered
    def test_recommend_auto_play(self):
        """
        Testing recommend() with play arg
        """
        spotirec.args = mock.MockArgs(play=['test'], n=1)
        spotirec.conf.save_device({'id': 'testid1', 'name': 'test1', 'type': 'microwave'}, 'test')
        spotirec.parse()
        # should not cause system exit
        spotirec.recommend()
        spotirec.conf.remove_playlist('spotirec-default')
        spotirec.conf.remove_device('test')

    @ordered
    def test_args_b(self):
        """
        Testing parse() with b arg
        """
        spotirec.args = mock.MockArgs(b=['spotify:track:testtrack'])
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_from_blacklist('spotify:track:testtrack')

    @ordered
    def test_args_br(self):
        """
        Testing parse() with br arg
        """
        spotirec.args = mock.MockArgs(br=['spotify:track:testtrack'])
        spotirec.conf.add_to_blacklist({'name': 'test', 'uri': 'spotify:track:testtrack'},
                                       'spotify:track:testtrack')
        self.assertRaises(SystemExit, spotirec.parse)
        blacklist = spotirec.conf.get_blacklist()
        self.assertNotIn('spotify:track:testtrack', blacklist['tracks'])

    @ordered
    def test_args_bc_track(self):
        """
        Testing parse() with bc arg (track)
        """
        spotirec.args = mock.MockArgs(bc=['track'])
        self.assertRaises(SystemExit, spotirec.parse)
        blacklist = spotirec.conf.get_blacklist()
        self.assertIn('spotify:track:testtrack', blacklist['tracks'].keys())
        spotirec.conf.remove_from_blacklist('spotify:track:testtrack')

    @ordered
    def test_args_bc_artist(self):
        """
        Testing parse() with bc arg (artist)
        """
        spotirec.args = mock.MockArgs(bc=['artist'])
        self.assertRaises(SystemExit, spotirec.parse)
        blacklist = spotirec.conf.get_blacklist()
        self.assertIn('spotify:artist:testartist', blacklist['artists'].keys())
        spotirec.conf.remove_from_blacklist('spotify:artist:testartist')

    @ordered
    def test_args_transfer_playback(self):
        """
        Testing parse() with transfer playback arg
        """
        spotirec.conf.save_device({'id': 'testid0', 'name': 'test0', 'type': 'fridge'}, 'test')
        spotirec.args = mock.MockArgs(transfer_playback=['test'])
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_device('test')

    @ordered
    def test_args_s(self):
        """
        Testing parse() with s arg
        """
        spotirec.args = mock.MockArgs(s=True)
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_sr(self):
        """
        Testing parse() with sr arg
        """
        spotirec.args = mock.MockArgs(sr=True)
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_save_playlist(self):
        """
        Testing parse() with save playlist arg
        """

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
        """
        Testing parse() with with remove playlist arg
        """
        spotirec.args = mock.MockArgs(remove_playlists=['test'])
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_save_device(self):
        """
        Testing parse() with save device arg
        """

        def mock_input(prompt: str):
            return '0'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(save_device=True)
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_device('0')

    @ordered
    def test_args_remove_devices(self):
        """
        Testing parse() with remove devices arg
        """
        spotirec.args = mock.MockArgs(remove_devices=['test'])
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_remove_presets(self):
        """
        Testing parse() with remove presets arg
        """
        spotirec.args = mock.MockArgs(remove_presets=['test'])
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_add_to(self):
        """
        Testing parse() with add to arg
        """
        spotirec.args = mock.MockArgs(add_to=['test'])
        spotirec.conf.save_playlist({'name': 'testplaylist',
                                     'uri': 'spotify:playlist:testplaylist'}, 'test')
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_playlist('test')

    @ordered
    def test_args_remove_from(self):
        """
        Testing parse() with remove from arg
        """
        spotirec.args = mock.MockArgs(remove_from=['test'])
        spotirec.conf.save_playlist({'name': 'testplaylist',
                                     'uri': 'spotify:playlist:testplaylist'}, 'test')
        self.assertRaises(SystemExit, spotirec.parse)
        spotirec.conf.remove_playlist('test')

    @ordered
    def test_args_print_artists(self):
        """
        Testing parse() with print arg (artists)
        """
        expected0 = f'0: frankie0{" " * 31}1: frankie1{" " * 31}2: frankie2\n'
        expected1 = f'3: frankie3{" " * 31}4: frankie4\n'
        spotirec.args = mock.MockArgs(print=['artists'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_args_print_tracks(self):
        """
        Testing parse() with print arg (tracks)
        """
        expected0 = f'0: track0{" " * 33}1: track1{" " * 33}2: track2\n'
        expected1 = f'3: track3{" " * 33}4: track4\n'
        spotirec.args = mock.MockArgs(print=['tracks'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_args_print_genres(self):
        """
        Testing parse() with print arg (genres)
        """
        expected0 = f'0: pop{" " * 36}1: vapor-death-pop{" " * 24}2: metal\n'
        expected1 = f'3: holidays{" " * 31}4: metalcore\n'
        spotirec.args = mock.MockArgs(print=['genres'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_args_print_genre_seeds(self):
        """
        Testing parse() with print arg (genre seeds)
        """
        expected0 = f'0: metal{" " * 34}1: metalcore{" " * 30}2: pop\n'
        expected1 = f'3: vapor-death-pop{" " * 24}4: holidays\n'
        spotirec.args = mock.MockArgs(print=['genre-seeds'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_args_print_blacklist(self):
        """
        Testing parse() with print arg (blacklist)
        """
        spotirec.args = mock.MockArgs(print=['blacklist'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn('Tracks', stdout)
            self.assertIn('Artists', stdout)

    @ordered
    def test_args_print_devices(self):
        """
        Testing parse() with print arg (devices)
        """
        expected = f'ID{" " * 18}Name{" " * 16}Type'
        spotirec.args = mock.MockArgs(print=['devices'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_args_print_presets(self):
        """
        Testing parse() with print arg (presets)
        """
        expected = f'Name{" " * 16}Type{" " * 21}Params{" " * 44}Seeds'
        spotirec.args = mock.MockArgs(print=['presets'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_args_print_playlists(self):
        """
        Testing parse() with print arg (playlists)
        """
        expected = f'ID{" " * 18}Name{" " * 26}URI'
        spotirec.args = mock.MockArgs(print=['playlists'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected, stdout)

    @ordered
    def test_args_print_tuning(self):
        """
        Testing parse() with print arg (tuning)
        """
        expected0 = 'Attribute           Data type   Range   Recommended range   Function'
        expected1 = 'note that recommendations may be scarce outside the recommended ranges. ' \
                    'If the recommended range is not available, they may only be scarce at ' \
                    'extreme values.'
        spotirec.args = mock.MockArgs(print=['tuning'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            self.assertIn(expected0, stdout)
            self.assertIn(expected1, stdout)

    @ordered
    def test_args_track_features_current(self):
        """
        Testing parse() with track features arg (current)
        """
        spotirec.args = mock.MockArgs(track_features=['current'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
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
        """
        Testing parse() with track features arg (uri)
        """
        spotirec.args = mock.MockArgs(track_features=['spotify:track:testtrack'])
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
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
        """
        Testing parse() with a arg
        """
        spotirec.args = mock.MockArgs(a=5)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'top artists')
        self.assertEqual(spotirec.rec.seed_type, 'artists')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 5)
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'frankie0', 'id': 'testid0', 'type': 'artist'},
                              1: {'name': 'frankie1', 'id': 'testid1', 'type': 'artist'},
                              2: {'name': 'frankie2', 'id': 'testid2', 'type': 'artist'},
                              3: {'name': 'frankie3', 'id': 'testid3', 'type': 'artist'},
                              4: {'name': 'frankie4', 'id': 'testid4', 'type': 'artist'}})

    @ordered
    def test_args_t(self):
        """
        Testing parse() with t arg
        """
        spotirec.args = mock.MockArgs(t=5)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'top tracks')
        self.assertEqual(spotirec.rec.seed_type, 'tracks')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 5)
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'track0', 'id': 'testid0', 'type': 'track',
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
        """
        Testing parse() with gcs arg
        """

        def mock_input(prompt: str):
            return '0 1 3'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(gcs=True)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'custom seed genres')
        self.assertEqual(spotirec.rec.seed_type, 'genres')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 3)
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'metal', 'type': 'genre'},
                              1: {'name': 'metalcore', 'type': 'genre'},
                              2: {'name': 'vapor-death-pop', 'type': 'genre'}})

    @ordered
    def test_args_ac(self):
        """
        Testing parse() with ac arg
        """

        def mock_input(prompt: str):
            return '1 2'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(ac=True)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'custom artists')
        self.assertEqual(spotirec.rec.seed_type, 'artists')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 2)
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'frankie1', 'id': 'testid1', 'type': 'artist'},
                              1: {'name': 'frankie2', 'id': 'testid2', 'type': 'artist'}})

    @ordered
    def test_args_tc(self):
        """
        Testing parse() with tc arg
        """

        def mock_input(prompt: str):
            return '0 4'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(tc=True)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'custom tracks')
        self.assertEqual(spotirec.rec.seed_type, 'tracks')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 2)
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'track0', 'id': 'testid0', 'type': 'track',
                                  'artists': ['frankie0', 'frankie1']},
                              1: {'name': 'track4', 'id': 'testid4', 'type': 'track',
                                  'artists': ['frankie4', 'frankie3']}})

    @ordered
    def test_args_gc(self):
        """
        Testing parse() with gc arg
        """

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
        """
        Testing parse() with c arg (sigint)
        """

        def mock_input(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(c=True)
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_c_no_input(self):
        """
        Testing parse() with c arg (no input)
        """

        def mock_input(prompt: str):
            return ''

        spotirec.logger.set_level(log.INFO)
        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(c=True)
        self.assertRaises(SystemExit, spotirec.parse)
        sys.stdout.close()
        sys.stdout = self.stdout_preserve
        with open(self.test_log, 'r') as f:
            stdout = f.read()
            crash_file = stdout.split('/')[2].strip('\n')
            os.remove(f'tests/fixtures/{crash_file}')

    @ordered
    def test_args_c(self):
        """
        Testing parse() with c arg
        """

        def mock_input(prompt: str):
            return 'vapor-death-pop spotify:track:testtrack spotify:artist:testartist'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(c=True)
        spotirec.parse()
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 3)
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'vapor-death-pop', 'type': 'genre'},
                              1: {'name': 'track0', 'id': 'testtrack', 'type': 'track',
                                  'artists': ['frankie0', 'frankie1']},
                              2: {'name': 'frankie0', 'id': 'testartist', 'type': 'artist'}})

    @ordered
    def test_args_st(self):
        """
        Testing parse() with st arg
        """
        spotirec.args = mock.MockArgs(st=3)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'recent saved tracks')
        self.assertEqual(spotirec.rec.seed_type, 'tracks')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 3)
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'track0', 'id': 'testid0', 'type': 'track',
                                  'artists': ['frankie0', 'frankie1']},
                              1: {'name': 'track1', 'id': 'testid1', 'type': 'track',
                                  'artists': ['frankie1']},
                              2: {'name': 'track2', 'id': 'testid2', 'type': 'track',
                                  'artists': ['frankie2', 'frankie1']}})

    @ordered
    def test_args_stc(self):
        """
        Testing parse() with stc arg
        """

        def mock_input(prompt: str):
            return '0 4'

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(stc=True)
        spotirec.parse()
        self.assertEqual(spotirec.rec.based_on, 'custom saved tracks')
        self.assertEqual(spotirec.rec.seed_type, 'tracks')
        self.assertEqual(len(spotirec.rec.seed_info.keys()), 2)
        self.assertDictEqual(spotirec.rec.seed_info,
                             {0: {'name': 'track0', 'id': 'testid0', 'type': 'track',
                                  'artists': ['frankie0', 'frankie1']},
                              1: {'name': 'track4', 'id': 'testid4', 'type': 'track',
                                  'artists': ['frankie4', 'frankie3']}})

    @ordered
    def test_args_stc_sigint(self):
        """
        Testing parse() with stc arg (sigint)
        """

        def mock_input(prompt: str):
            raise KeyboardInterrupt

        spotirec.input = mock_input
        spotirec.args = mock.MockArgs(stc=True)
        self.assertRaises(SystemExit, spotirec.parse)

    @ordered
    def test_args_l(self):
        """
        Testing parse() with l arg
        """
        spotirec.args = mock.MockArgs(l=[83], n=1)
        spotirec.parse()
        self.assertEqual(spotirec.rec.limit, 83)
        self.assertEqual(spotirec.rec.limit_original, 83)

    @ordered
    def test_args_tune(self):
        """
        Testing parse() with tune arg
        """
        spotirec.args = mock.MockArgs(tune=['min_tempo=160'], n=1)
        spotirec.parse()
        self.assertDictEqual(spotirec.rec.rec_params, {'limit': '20', 'min_tempo': '160'})

    @ordered
    def test_setup_config_dir(self):
        """
        Testing setup_config_dir()
        """
        spotirec.setup_config_dir()
        os.rmdir(spotirec.CONFIG_PATH)

    @ordered
    def test_authorize(self):
        """
        Testing authorize()
        """

        def mock_run(host: str, port: int, quiet: bool):
            return

        spotirec.webbrowser = mock.MockWebbrowser()
        spotirec.run = mock_run
        spotirec.authorize()
        self.assertEqual(spotirec.webbrowser.url, 'https://real.url:8000')

    @ordered
    def test_authorize_retry_once(self):
        """
        Testing authorize() with one retry
        """

        def mock_run(host: str, port: int, quiet: bool):
            spotirec.run = mock_run_second
            raise OSError(errno.EADDRINUSE, 'address in use')

        def mock_run_second(host: str, port: int, quiet: bool):
            nonlocal second_port
            second_port = port

        second_port = 0
        spotirec.webbrowser = mock.MockWebbrowser()
        spotirec.run = mock_run
        spotirec.authorize()
        self.assertEqual(second_port, 8001)

    @ordered
    def test_authorize_all_ports_in_use(self):
        """
        Testing authorize() all ports in use
        """

        def mock_run(host: str, port: int, quiet: bool):
            raise OSError(errno.EADDRINUSE, 'address in use')

        spotirec.webbrowser = mock.MockWebbrowser()
        spotirec.run = mock_run
        self.assertRaises(SystemExit, spotirec.authorize)

    @ordered
    def test_create_parser(self):
        """
        Testing create_parser()
        """
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
        self.assertIn('st', args)
        self.assertIsNone(args.st)
        self.assertIn('stc', args)
        self.assertFalse(args.stc)
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
        """
        Testing init()
        """

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
        self.assertDictEqual(
            spotirec.headers, {'Content-Type': 'application/json',
                               'Authorization': 'Bearer f6952d6eef555ddd87aca66e56b91530222d6e3184'
                                                '14816f3ba7cf5bf694bf0f'})
        self.assertIsInstance(spotirec.rec, recommendation.Recommendation)
        spotirec.get_token = get_token_save
        spotirec.get_user_top_genres = top_genres_save

    @ordered
    def test_init_args_verbose(self):
        """
        Testing init() with verbose arg
        """

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
        """
        Testing init() with quiet arg
        """

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
        """
        Testing init() with debug arg
        """

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
        """
        Testing init() with suppress warnings arg
        """

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
        """
        Testing init() with load preset arg
        """

        def mock_get_token():
            return 'f6952d6eef555ddd87aca66e56b91530222d6e318414816f3ba7cf5bf694bf0f'

        class MockConfig:
            def Config(self):
                config = conf.Config()
                config.CONFIG_DIR = 'tests/fixtures'
                config.CONFIG_FILE = 'test.conf'
                return config

        preset = {'limit': 100, 'based_on': 'top artists',
                  'seed': 'hip-hop,metalcore,metal,pop,death-metal',
                  'seed_type': 'tracks', 'seed_info':
                      {0: {'name': 'hip-hop', 'type': 'genre'},
                       1: {'name': 'metalcore', 'type': 'genre'},
                       2: {'name': 'metal', 'type': 'genre'}, 3: {'name': 'pop', 'type': 'genre'},
                       4: {'name': 'death-metal', 'type': 'genre'}},
                  'rec_params': {'limit': '100',
                                 'seed_genres': 'hip-hop,metalcore,metal,pop,death-metal'},
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

    @ordered
    def test_check_scope_perms(self):
        """
        Testing check_scope_permissions()
        """
        # should not cause system exit
        spotirec.check_scope_permissions()

    @ordered
    def test_check_scope_perms_error(self):
        """
        Testing check_scope_permissions() fail
        """

        def mock_authorize():
            self.test = 'success'

        self.test = ''
        spotirec.sp_oauth.scopes.append('this-is-not-a-scope')
        auth_save = spotirec.authorize
        spotirec.authorize = mock_authorize
        self.assertRaises(SystemExit, spotirec.check_scope_permissions)
        self.assertEqual(self.test, 'success')
        spotirec.authorize = auth_save
        spotirec.sp_oauth.scopes.remove('this-is-not-a-scope')

from tests.lib import ordered, runner
from tests.lib.ut_ext import SpotirecTestCase
from spotirec import log, recommendation
import os
import sys
import time


class TestRecommendation(SpotirecTestCase):
    """
    Running tests for recommendation.py
    """

    @classmethod
    def setUpClass(cls) -> None:
        """
        Setup any necessary data or states before any tests in this class is run
        """
        if runner.verbosity > 0:
            super(TestRecommendation, cls).setUpClass()
            print(f'file:/{__file__}\n')
        cls.test_seed = {0: {'name': 'metal', 'type': 'genre'},
                         1: {'name': 'test', 'id': 'testid', 'type': 'track', 'artists':
                             ['frankie']},
                         2: {'name': 'frankie', 'id': 'testid', 'type': 'artist'}}
        cls.test_track = {'name': 'test', 'id': 'testid', 'type': 'track', 'artists':
                          [{'name': 'frankie'}]}
        cls.test_artist = {'name': 'frankie', 'id': 'testid', 'type': 'artist'}
        # unset limit on string comparison
        cls.maxDiff = None
        cls.logger = log.Log()

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Clear or resolve any necessary data or states after all tests in this class are run
        """
        if runner.verbosity > 0:
            super(TestRecommendation, cls).tearDownClass()

    def setUp(self):
        """
        Setup any necessary data or states before each test is run
        """
        self.t = time.localtime(0)  # 1-1-1970 1:0:0
        self.timestamp = time.ctime(time.time())
        self.rec = recommendation.Recommendation(t=self.t)
        self.logger.set_level(0)
        self.rec.set_logger(self.logger)

    @ordered
    def test_init(self):
        """
        Testing recommendation defaults
        """
        self.assertEqual(self.rec.limit, 100)
        self.assertEqual(self.rec.limit_original, 100)
        self.assertEqual(self.rec.created_at, self.timestamp)
        self.assertEqual(self.rec.based_on, 'top genres')
        self.assertEqual(self.rec.seed, '')
        self.assertEqual(self.rec.seed_type, 'genres')
        self.assertEqual(self.rec.seed_info, {})
        self.assertEqual(self.rec.rec_params, {'limit': '100'})
        self.assertEqual(self.rec.playlist_name, 'Spotirec-1-1-1970')
        self.assertEqual(self.rec.playlist_id, '')
        self.assertEqual(self.rec.auto_play, False)
        self.assertEqual(self.rec.playback_device, {})

    @ordered
    def test_str(self):
        """
        Testing __str__()
        """
        s = "{'limit': 100, 'original limit': 100, 'created at': '" + self.timestamp + \
            "', 'based on': 'top genres', 'seed': '', 'seed type': 'genres', 'seed info': {}, " \
            "'rec params': {'limit': '100'}, 'name': 'Spotirec-1-1-1970', 'id': '', " \
            "'auto play': False, 'device': {}}"
        self.assertEqual(str(self.rec), s)

    @ordered
    def test_playlist_description(self):
        """
        Testing playlist_description()
        """
        description = 'Created by Spotirec - ' + self.timestamp + ' - based on top genres - seed: '
        self.assertEqual(self.rec.playlist_description(False), description)

    @ordered
    def test_update_limit(self):
        """
        Testing update_limit()
        """
        # both limit and original limit should be updated
        self.rec.update_limit(50, init=True)
        self.assertEqual(self.rec.limit, 50)
        self.assertEqual(self.rec.limit_original, 50)

        # only limit should be updated
        self.rec.update_limit(70)
        self.assertEqual(self.rec.limit, 70)

    @ordered
    def test_add_seed_info(self):
        """
        Testing add_seed_info()
        """
        self.rec.add_seed_info(data_string='metal')
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.add_seed_info(data_dict=self.test_artist)
        self.assertEqual(self.rec.seed_info, self.test_seed)

    @ordered
    def test_print_selection(self):
        """
        Testing print_selection()
        """
        self.rec.add_seed_info(data_string='metal')
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.add_seed_info(data_dict=self.test_artist)
        self.assertEqual(self.rec.seed_info, self.test_seed)
        self.rec.LOGGER.set_level(50)
        sys.stdout = open('tests/fixtures/select', 'w')
        self.rec.print_selection()
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        with open('tests/fixtures/select', 'r') as f:
            stdout = f.readlines()
            self.assertIn('Selection:', stdout[0])
            self.assertIn('Genre: metal', stdout[1])
            self.assertIn('Track: test - frankie', stdout[2])
            self.assertIn('Artist: frankie', stdout[3])
        os.remove('tests/fixtures/select')

    @ordered
    def test_create_seed_genres(self):
        """
        Testing create_seed() (genres)
        """
        self.rec.add_seed_info(data_string='metal')
        self.rec.add_seed_info(data_string='metalcore')
        self.rec.add_seed_info(data_string='vapor-death-pop')
        self.rec.seed_type = 'genres'
        self.rec.create_seed()
        self.assertEqual(self.rec.seed, 'metal,metalcore,vapor-death-pop')

    @ordered
    def test_create_seed_artists_tracks(self):
        """
        Testing create_seed() (tracks)
        """
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.seed_type = 'tracks'
        self.rec.create_seed()
        self.assertEqual(self.rec.seed, 'testid,testid,testid')

    @ordered
    def test_create_seed_custom(self):
        """
        Testing create_seed() (custom)
        """
        self.rec.add_seed_info(data_string='metal')
        self.rec.add_seed_info(data_dict=self.test_track)
        self.rec.add_seed_info(data_dict=self.test_artist)
        self.rec.seed_type = 'custom'
        self.rec.create_seed()
        self.assertEqual(self.rec.rec_params['seed_tracks'], 'testid')
        self.assertEqual(self.rec.rec_params['seed_artists'], 'testid')
        self.assertEqual(self.rec.rec_params['seed_genres'], 'metal')

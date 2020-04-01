from tests.lib import ordered, mock, SpotirecTestCase, runner
import log
import oauth2
import api
import conf
import os
import time


class TestOauth2(SpotirecTestCase):
    """
    Running tests for oauth2.py
    """

    @classmethod
    def setUpClass(cls) -> None:
        """
        Setup any necessary data or states before any tests in this class is run
        """
        if runner.verbosity > 0:
            super(TestOauth2, cls).setUpClass()
            print(f'file:/{__file__}\n')
        oauth2.requests = mock.MockAPI()
        cls.logger = log.Log()
        cls.conf = conf.Config()
        cls.oauth = oauth2.SpotifyOAuth()
        cls.api = api.API()
        cls.conf.set_logger(cls.logger)
        cls.oauth.set_logger(cls.logger)
        cls.oauth.set_conf(cls.conf)
        cls.oauth.set_api(cls.api)
        cls.api.set_logger(cls.logger)

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Clear or resolve any necessary data or states after all tests in this class are run
        """
        if runner.verbosity > 0:
            super(TestOauth2, cls).tearDownClass()

    def setUp(self):
        """
        Setup any necessary data or states before each test is run
        """
        self.oauth.OAUTH_TOKEN_URL = '/api/token'
        self.oauth.client_id = 'client_id'
        self.oauth.client_secret = 'client_secret'
        self.oauth.scopes = 'user-modify-playback-state ugc-image-upload user-library-modify'
        self.logger.set_level(0)
        self.conf.CONFIG_DIR = 'tests/fixtures/'
        self.conf.CONFIG_FILE = 'test.conf'

    @ordered
    def test_get_credentials(self):
        """
        Testing get_credentials()
        """
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
        """
        Testing get_credentials() with expired token
        """
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
        """
        Testing get_credentials() with empty conf
        """
        self.conf.CONFIG_FILE = 'empty.conf'
        token = self.oauth.get_credentials()
        self.assertIsNone(token)
        with open(f'tests/fixtures/empty.conf', 'w') as f:
            f.write('')

    @ordered
    def test_refresh_token(self):
        """
        Testing refresh_token()
        """
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
        os.remove('tests/fixtures/test-refresh.conf')

    @ordered
    def test_refresh_token_no_refresh(self):
        """
        Testing refresh_token() preserving refresh token
        """
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
        os.remove('tests/fixtures/test-refresh.conf')

    @ordered
    def test_is_token_expired(self):
        """
        Testing is_token_expired()
        """
        # config is set to expire in year ~2500
        oauth = self.oauth.get_credentials()
        self.assertFalse(self.oauth.is_token_expired(int(oauth['expires_at'])))
        self.assertTrue(self.oauth.is_token_expired(0))

    @ordered
    def test_encode_header(self):
        """
        Testing encode_header()
        """
        expected = {'Authorization': 'Basic dGhpc2lzYXJlYWxjbGllbnRpZDp0aGlzaXNhcmVhbGNsaWVudHNlY3JldA=='}
        self.oauth.client_id = 'thisisarealclientid'
        self.oauth.client_secret = 'thisisarealclientsecret'
        header = self.oauth.encode_header()
        self.assertEqual(header, expected)

    @ordered
    def test_retrieve_access_token(self):
        """
        Testing retrieve_access_token()
        """
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
        os.remove('tests/fixtures/test-retrieve.conf')

    @ordered
    def test_get_authorize_url(self):
        """
        Testing get_authorize_url()
        """
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
        """
        Testing parse_response_code()
        """
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
        """
        Testing save_token()
        """
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
        os.remove('tests/fixtures/save-test')

    @ordered
    def test_set_api(self):
        """
        Testing set_api()
        """
        api_test = api.API()
        self.oauth.set_api(api_test)
        self.assertEqual(api_test, self.oauth.API)

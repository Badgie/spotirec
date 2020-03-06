#!/usr/bin/env python
import json
import time
import requests
import base64
import api
import conf
from urllib import parse


class SpotifyOAuth:
    OAUTH_AUTH_URL = 'https://accounts.spotify.com/authorize'
    OAUTH_TOKEN_URL = 'https://accounts.spotify.com/api/token'
    PORT = 8080

    def __init__(self):
        self.client_id = '466a89a53359403b82df7d714030ec5f'
        self.client_secret = '28147de72c3549e98b1e790f3d080b85'
        self.redirect = f'http://localhost:{self.PORT}'
        self.scopes = 'user-top-read playlist-modify-public playlist-modify-private user-read-private ' \
                      'user-read-email ugc-image-upload user-read-playback-state user-modify-playback-state ' \
                      'user-library-modify'

    def get_credentials(self) -> json:
        """
        Get credentials from cache file. Refresh token if it's about to expire.
        :return: token contents as a json object
        """
        try:
            creds = conf.get_oauth()
            print(creds)
            if self.is_token_expired(int(creds['expires_at'])):
                print('OAuth token is expired, refreshing...')
                creds = self.refresh_token(creds['refresh_token'])
        except (IOError, json.decoder.JSONDecodeError):
            print('Error: cache does not exist or is empty')
            return None
        return creds

    def is_token_expired(self, token_expire: int) -> bool:
        """
        Check if token is about to expire - add 30 sec to current time to ensure it doesn't expire during run.
        :param token_expire: time at which the token expires in seconds
        :return: whether or not token is about to expire as a bool
        """
        return (time.time() + 30) > token_expire

    def refresh_token(self, refresh_token: str) -> json:
        """
        Refresh token and update cache file.
        :param refresh_token: refresh token from credentials
        :return: refreshed credentials as a json object
        """
        body = {'grant_type': 'refresh_token',
                'refresh_token': refresh_token}
        response = requests.post(self.OAUTH_TOKEN_URL, data=body, headers=self.encode_header())
        api.error_handle('token refresh', 200, 'POST', response=response)
        token = json.loads(response.content.decode('utf-8'))
        try:
            assert token['refresh_token'] is not None
            self.save_token(token)
        except (KeyError, AssertionError):
            print('Did not receive new refresh token, saving old')
            self.save_token(token, refresh_token=refresh_token)
        return token

    def encode_header(self) -> dict:
        """
        Encode header token as required by OAuth specification.
        :return: dict containing header with base64 encoded client credentials
        """
        encoded_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("ascii")).decode("ascii")
        return {'Authorization': f'Basic {encoded_header}'}

    def retrieve_access_token(self, code: str) -> json:
        """
        Request token from API, save to cache, and return it.
        :param code: authorization code retrieved from spotify API
        :return: credentials as a json object
        """
        body = {'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect}
        response = requests.post(self.OAUTH_TOKEN_URL, data=body, headers=self.encode_header())
        api.error_handle('token retrieve', 200, 'POST', response=response)
        token = json.loads(response.content.decode('utf-8'))
        self.save_token(token)
        return token

    def get_authorize_url(self) -> str:
        """
        Create authorization URL with parameters.
        :return: authorization url with parameters appended
        """
        params = {'client_id': self.client_id,
                  'response_type': 'code',
                  'redirect_uri': self.redirect,
                  'scope': self.scopes}
        return f'{self.OAUTH_AUTH_URL}?{parse.urlencode(params)}'

    def parse_response_code(self, url: str) -> str:
        """
        Extract code from response url after authorization by user.
        :url: url retrieved after user authorized access
        :return: authorization code extracted from url
        """
        try:
            return url.split('?code=')[1].split('&')[0]
        except IndexError:
            pass

    def save_token(self, token: json, refresh_token=None):
        """
        Add 'expires at' field and reapplies refresh token to token, and save to cache
        :param token: credentials as a json object
        :param refresh_token: user refresh token
        """
        token['expires_at'] = round(time.time()) + int(token['expires_in'])
        if refresh_token:
            token['refresh_token'] = refresh_token
        c = conf.open_config()
        for x in token.items():
            c['spotirecoauth'][x[0]] = str(x[1])
        conf.save_config(c)

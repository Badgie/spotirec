#!/usr/bin/env python
import json
import time
import requests
import base64
from urllib import parse


class SpotifyOAuth:
    oauth_auth_url = 'https://accounts.spotify.com/authorize'
    oauth_token_url = 'https://accounts.spotify.com/api/token'

    def __init__(self, client_id: str, client_secret: str, redirect: str, scopes: str, cache: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect = redirect
        self.scopes = scopes
        self.cache = cache

    '''
    Get credentials from cache file. Refresh token if it's about to expire.
    '''
    def get_credentials(self) -> json:
        try:
            with open(self.cache, 'r') as file:
                creds = json.loads(file.read())
                if self.is_token_expired(creds['expires_at']):
                    print('OAuth token is expired, refreshing...')
                    creds = self.refresh_token(creds['refresh_token'])
        except (IOError, json.decoder.JSONDecodeError):
            print('Error: cache does not exist or is empty')
            exit(1)
        return creds

    '''
    Check if token is about to expire - add 30 sec to current time to ensure it doesn't expire during run.
    '''
    def is_token_expired(self, token_expire: int) -> bool:
        current_time = time.time()
        return (current_time + 30) > token_expire

    '''
    Refresh token and update cache file.
    '''
    def refresh_token(self, refresh_token: str) -> json:
        body = {'grant_type': 'refresh_token',
                'refresh_token': refresh_token}
        response = requests.post(self.oauth_token_url, data=body, headers=self.encode_header())
        token = json.loads(response.content.decode('utf-8'))
        self.save_token(token)
        return token

    '''
    Encode header token as required by OAuth specification.
    '''
    def encode_header(self) -> dict:
        encoded_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("ascii")).decode("ascii")
        return {'Authorization': f'Basic {encoded_header}'}

    '''
    Request token from API, save to cache, and return it.
    '''
    def retrieve_access_token(self, code: str) -> json:
        body = {'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect}
        response = requests.post(self.oauth_token_url, data=body, headers=self.encode_header())
        token = json.loads(response.content.decode('utf-8'))
        self.save_token(token)
        return token

    '''
    Create authorization URL with parameters.
    '''
    def get_authorize_url(self) -> str:
        params = {'client_id': self.client_id,
                  'response_type': 'code',
                  'redirect_uri': self.redirect,
                  'scope': self.scopes}
        return f'{self.oauth_auth_url}?{parse.urlencode(params)}'

    '''
    Extract code from response url after authorization by user.
    '''
    def parse_response_code(self, url: str) -> str:
        try:
            return url.split('?code=')[1].split('&')[0]
        except IndexError:
            pass

    '''
    Add 'expires at' field to token and save to cache
    '''
    def save_token(self, token: json):
        token['expires_at'] = round(time.time()) + int(token['expires_in'])
        with open(self.cache, 'w') as file:
            file.write(json.dumps(token))

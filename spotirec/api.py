#!/usr/bin/env python
import json
import requests
import sys
from . import conf as sp_conf, log


class API:
    URL_BASE = 'https://api.spotify.com/v1'
    LOGGER = None
    CONF = None

    def set_logger(self, logger: log.Log):
        self.LOGGER = logger

    def set_conf(self, conf: sp_conf.Config):
        self.CONF = conf

    def error_handle(self, request_domain: str, expected_code: int, request_type: str,
                     response=None):
        """
        Dispatch error message depending on request type
        :param request_domain: domain of the request, e.g. 'recommendation'
        :param expected_code: expected status code
        :param request_type: type of request, e.g. GET, POST, PUT
        :param response: response object
        """
        if response.status_code is not expected_code:
            self.LOGGER.error(
                f'{request_type} request for {request_domain} failed with status code '
                f'{response.status_code} (expected {expected_code}). Reason: {response.reason}')
            self.LOGGER.debug(f'request: {response.request}')
            self.LOGGER.debug(f'headers: {response.headers}')
            self.LOGGER.debug(f'url: {response.url}')
            if response.status_code == 401:
                self.LOGGER.info('this may be because this is a new function, and additional '
                                 'authorization is required - try reauthorizing and try again.')
            self.LOGGER.log_file(crash=True)
            sys.exit(1)

    def get_top_list(self, list_type: str, limit: int, headers: dict) -> json:
        """
        Retrieve list of top artists of tracks from user's profile.
        :param list_type: type of list to retrieve; 'artists' or 'tracks'
        :param limit: amount of entries to retrieve; min 1, max 50
        :param headers: request headers
        :return: top list as json object
        """
        params = {'limit': limit}
        response = requests.get(f'{self.URL_BASE}/me/top/{list_type}', headers=headers,
                                params=params)
        self.error_handle(f'top {list_type}', 200, 'GET', response=response)
        return json.loads(response.content.decode('utf-8'))

    def get_user_id(self, headers: dict) -> str:
        """
        Retrieve user ID from API.
        :param headers: request headers
        :return: user ID as a string
        """
        response = requests.get(f'{self.URL_BASE}/me', headers=headers)
        self.error_handle('user info', 200, 'GET', response=response)
        return json.loads(response.content.decode('utf-8'))['id']

    def create_playlist(self, playlist_name: str, playlist_description: str, headers: dict,
                        cache_id=False) -> str:
        """
        Creates playlist on user's account.
        :param cache_id: whether playlist id should be saved as default or not
        :param playlist_name: name of the playlist
        :param playlist_description: description of the playlist
        :param headers: request headers
        :return: playlist id
        """
        data = {'name': playlist_name,
                'description': playlist_description}
        self.LOGGER.info('creating playlist')
        response = requests.post(f'{self.URL_BASE}/users/{self.get_user_id(headers)}/playlists',
                                 json=data, headers=headers)
        self.error_handle('playlist creation', 201, 'POST', response=response)
        playlist = json.loads(response.content.decode('utf-8'))
        if cache_id:
            self.CONF.save_playlist({'name': playlist['name'], 'uri': playlist['uri']},
                                    'spotirec-default')
        return playlist['id']

    def upload_image(self, playlist_id: str, data: str, img_headers: dict):
        """
        Upload the generated image to the playlist
        :param playlist_id: id of the playlist
        :param data: base64 encoded jpeg image
        :param img_headers: request headers
        """
        response = requests.put(f'{self.URL_BASE}/playlists/{playlist_id}/images',
                                headers=img_headers, data=data)
        self.error_handle('image upload', 202, 'PUT', response=response)

    def add_to_playlist(self, tracks: list, playlist_id: str, headers: dict):
        """
        Add tracks to playlist.
        :param tracks: list of track URIs
        :param playlist_id: id of playlist
        :param headers: request headers
        """
        data = {'uris': tracks}
        self.LOGGER.debug(f'tracks: {tracks}')
        response = requests.post(f'{self.URL_BASE}/playlists/{playlist_id}/tracks',
                                 headers=headers, json=data)
        self.error_handle('adding tracks', 201, 'POST', response=response)

    def get_recommendations(self, rec_params: dict, headers: dict) -> json:
        """
        Retrieve recommendations from API.
        :param rec_params: parameters for recommendation request
        :param headers: request headers
        :return: recommendations as json object
        """
        response = requests.get(f'{self.URL_BASE}/recommendations', params=rec_params,
                                headers=headers)
        self.error_handle('recommendations', 200, 'GET', response=response)
        return json.loads(response.content.decode('utf-8'))

    def request_data(self, uri: str, data_type: str, headers: dict) -> json:
        """
        Requests data about an artist or a track.
        :param uri: uri for the artist or track
        :param data_type: the type of data to request; 'artists' or 'tracks'
        :param headers: request headers
        :return: data about artist or track as a json obj
        """
        response = requests.get(f'{self.URL_BASE}/{data_type}/{uri.split(":")[2]}', headers=headers)
        self.error_handle(f'single {data_type}', 200, 'GET', response=response)
        return json.loads(response.content.decode('utf-8'))

    def get_genre_seeds(self, headers: dict) -> json:
        """
        Retrieves available genre seeds from Spotify API.
        :param headers: request headers
        :return: genre seeds as a json obj
        """
        response = requests.get(f'{self.URL_BASE}/recommendations/available-genre-seeds',
                                headers=headers)
        self.error_handle('genre seeds', 200, 'GET', response=response)
        return json.loads(response.content.decode('utf-8'))

    def get_available_devices(self, headers: dict) -> json:
        """
        Retrieves user's available playback devices
        :param headers: request headers
        :return: devices as json object
        """
        response = requests.get(f'{self.URL_BASE}/me/player/devices', headers=headers)
        self.error_handle('playback devices', 200, 'GET', response=response)
        return json.loads(response.content.decode('utf-8'))

    def play(self, device_id: str, context_uri: str, headers: dict):
        """
        Begin playback on user's account
        :param device_id: id of the device to play on
        :param context_uri: uri of what should be played
        :param headers: request headers
        """
        body = {'context_uri': context_uri}
        params = {'device_id': device_id}
        response = requests.put(f'{self.URL_BASE}/me/player/play', json=body, headers=headers,
                                params=params)
        self.error_handle('start playback', 204, 'PUT', response=response)

    def get_current_track(self, headers: dict) -> str:
        """
        Retrieve data about currently playing track
        :param headers: request headers
        :return: uri of current track if present, else return playing type
        """
        response = requests.get(f'{self.URL_BASE}/me/player', headers=headers)
        self.error_handle('retrieve current track', 200, 'GET', response=response)
        data = json.loads(response.content.decode('utf-8'))
        try:
            return data['item']['uri']
        except (TypeError, KeyError):
            return data['currently_playing_type']

    def get_current_artists(self, headers: dict) -> list:
        """
        Retrieve list of artists from currently playing track
        :param headers: request headers
        :return: list of artist uris if present, else return playing type
        """
        response = requests.get(f'{self.URL_BASE}/me/player', headers=headers)
        self.error_handle('retrieve current artists', 200, 'GET', response=response)
        data = json.loads(response.content.decode('utf-8'))
        try:
            return [str(x['uri']) for x in data['item']['artists']]
        except (TypeError, KeyError):
            return [data['currently_playing_type']]

    def like_track(self, headers: dict, uri_check):
        """
        Like currently playing track
        :param headers: request headers
        :param uri_check: function that checks if uri is a show or episode
        """
        current_track = self.get_current_track(headers)
        if uri_check(current_track):
            return
        track = {'ids': current_track.split(':')[2]}
        response = requests.put(f'{self.URL_BASE}/me/tracks', headers=headers, params=track)
        self.error_handle('like track', 200, 'PUT', response=response)

    def unlike_track(self, headers: dict, uri_check):
        """
        Remove currently playing track from liked tracks
        :param headers: request headers
        :param uri_check: function that checks if uri is a show or episode
        """
        current_track = self.get_current_track(headers)
        if uri_check(current_track):
            return
        track = {'ids': current_track.split(':')[2]}
        response = requests.delete(f'{self.URL_BASE}/me/tracks', headers=headers, params=track)
        self.error_handle('remove liked track', 200, 'DELETE', response=response)

    def update_playlist_details(self, name: str, description: str, playlist_id: str, headers: dict):
        """
        Update the details of a playlist
        :param playlist_id: id of the playlist
        :param name: new name of the playlist
        :param description: new description of the playlist
        :param headers: request headers
        :return:
        """
        data = {'name': name, 'description': description}
        response = requests.put(f'{self.URL_BASE}/playlists/{playlist_id}', headers=headers,
                                json=data)
        self.error_handle('update playlist details', 200, 'PUT', response=response)

    def replace_playlist_tracks(self, playlist_id: str, tracks: list, headers: dict):
        """
        Remove the tracks from a playlist
        :param tracks: list of track uris
        :param playlist_id: id of the playlist
        :param headers: request headers
        :return:
        """
        data = {'uris': tracks}
        response = requests.put(f'{self.URL_BASE}/playlists/{playlist_id}/tracks', headers=headers,
                                json=data)
        self.error_handle('remove tracks from playlist', 201, 'PUT', response=response)

    def get_playlist(self, headers: dict, playlist_id: str):
        """
        Retrieve playlist from API
        :param headers: request headers
        :param playlist_id: ID of the playlist
        :return: playlist object
        """
        response = requests.get(f'{self.URL_BASE}/playlists/{playlist_id}', headers=headers)
        self.error_handle('retrieve playlist', 200, 'GET', response=response)
        return json.loads(response.content.decode('utf-8'))

    def remove_from_playlist(self, tracks: list, playlist_id: str, headers: dict):
        """
        Remove track(s) from a playlist
        :param tracks: the tracks to remove
        :param playlist_id: identifier of the playlist to remove tracks from
        :param headers: request headers
        """
        data = {'tracks': [{'uri': x} for x in tracks]}
        self.LOGGER.debug(f'tracks: {data["tracks"]}')
        response = requests.delete(f'{self.URL_BASE}/playlists/{playlist_id}/tracks',
                                   headers=headers, json=data)
        self.error_handle('delete track from playlist', 200, 'DELETE', response=response)

    def get_audio_features(self, track_id: str, headers: dict) -> json:
        """
        Get audio features of a track
        :param track_id: id of the track
        :param headers: request headers
        :return: audio features object
        """
        response = requests.get(f'{self.URL_BASE}/audio-features/{track_id}', headers=headers)
        self.error_handle('retrieve audio features', 200, 'GET', response=response)
        return json.loads(response.content.decode('utf-8'))

    def check_if_playlist_exists(self, playlist_id: str, headers: dict) -> bool:
        """
        Checks whether a playlist exists
        :param playlist_id: id of playlist
        :param headers: request headers
        :return: bool determining if playlist exists
        """
        response = requests.get(f'{self.URL_BASE}/playlists/{playlist_id}', headers=headers)
        self.error_handle('retrieve playlist', 200, 'GET', response=response)
        # If playlist is public, return true (if playlist has been deleted, this value is false)
        if json.loads(response.content.decode('utf-8'))['public']:
            return True
        else:
            return False

    def transfer_playback(self, device_id: str, headers: dict, start_playback=True):
        """
        Transfer playback to device
        :param device_id: id to transfer playback to
        :param headers: request headers
        :param start_playback: if music should start playing or not
        """
        data = {'device_ids': [device_id], 'play': start_playback}
        response = requests.put(f'{self.URL_BASE}/me/player', headers=headers, json=data)
        self.error_handle('transfer playback', 204, 'PUT', response=response)

    def get_saved_tracks(self, headers: dict, limit=50) -> json:
        """
        Gets a users saved tracks
        :param headers: request headers
        :param limit: the amount of tracks to get
        :return: json object
        """
        params = {'limit': limit}
        response = requests.get(f'{self.URL_BASE}/me/tracks', headers=headers, params=params)
        self.error_handle('retrieve saved tracks', 200, 'GET', response=response)
        return json.loads(response.content.decode('utf-8'))

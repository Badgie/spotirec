#!/usr/bin/env python
import json
import requests

url_base = 'https://api.spotify.com/v1'


def error_handle(request_domain: str, expected_code: int, request_type: str, response=None):
    """
    Dispatch error message depending on request type
    :param request_domain: domain of the request, e.g. 'recommendation'
    :param expected_code: expected status code
    :param request_type: type of request, e.g. GET, POST, PUT
    :param response: response object
    """
    if response.status_code is not expected_code:
        print(f'{request_type} request for {request_domain} failed with status code {response.status_code} '
              f'(expected {expected_code}). Reason: {response.reason}')
        if response.status_code == 401:
            print('NOTE: This may be because this is a new function, and additional authorization is required. '
                  'Try reauthorizing and try again.')
        exit(1)


def get_top_list(list_type: str, limit: int, headers: dict) -> json:
    """
    Retrieve list of top artists of tracks from user's profile.
    :param list_type: type of list to retrieve; 'artists' or 'tracks'
    :param limit: amount of entries to retrieve; min 1, max 50
    :param headers: request headers
    :return: top list as json object
    """
    params = {'limit': limit}
    response = requests.get(f'{url_base}/me/top/{list_type}', headers=headers, params=params)
    error_handle(f'top {list_type}', 200, 'GET', response=response)
    return json.loads(response.content.decode('utf-8'))


def get_user_id(headers: dict) -> str:
    """
    Retrieve user ID from API.
    :param headers: request headers
    :return: user ID as a string
    """
    response = requests.get(f'{url_base}/me', headers=headers)
    error_handle('user info', 200, 'GET', response=response)
    return json.loads(response.content.decode('utf-8'))['id']


def create_playlist(playlist_name: str, playlist_description: str, headers: dict) -> str:
    """
    Creates playlist on user's account.
    :param playlist_name: name of the playlist
    :param playlist_description: description of the playlist
    :param headers: request headers
    :return: playlist id
    """
    data = {'name': playlist_name,
            'description': playlist_description}
    print('Creating playlist')
    response = requests.post(f'{url_base}/users/{get_user_id(headers)}/playlists', json=data, headers=headers)
    error_handle('playlist creation', 201, 'POST', response=response)
    return json.loads(response.content.decode('utf-8'))['id']


def upload_image(playlist_id: str, data: str, img_headers: dict):
    """
    Upload the generated image to the playlist
    :param playlist_id: id of the playlist
    :param data: base64 encoded jpeg image
    :param img_headers: request headers
    """
    response = requests.put(f'{url_base}/playlists/{playlist_id}/images', headers=img_headers, data=data)
    error_handle('image upload', 202, 'PUT', response=response)


def add_to_playlist(tracks: list, playlist_id: str, headers: dict):
    """
    Add tracks to playlist.
    :param tracks: list of track URIs
    :param playlist_id: id of playlist
    :param headers: request headers
    """
    data = {'uris': tracks}
    response = requests.post(f'{url_base}/playlists/{playlist_id}/tracks', headers=headers, json=data)
    error_handle('adding tracks', 201, 'POST', response=response)


def get_recommendations(rec_params: dict, headers: dict) -> json:
    """
    Retrieve recommendations from API.
    :param rec_params: parameters for recommendation request
    :param headers: request headers
    :return: recommendations as json object
    """
    response = requests.get(f'{url_base}/recommendations', params=rec_params, headers=headers)
    error_handle('recommendations', 200, 'GET', response=response)
    return json.loads(response.content.decode('utf-8'))


def request_data(uri: str, data_type: str, headers: dict) -> json:
    """
    Requests data about an artist or a track.
    :param uri: uri for the artist or track
    :param data_type: the type of data to request; 'artists' or 'tracks'
    :param headers: request headers
    :return: data about artist or track as a json obj
    """
    response = requests.get(f'{url_base}/{data_type}/{uri.split(":")[2]}', headers=headers)
    error_handle(f'single {data_type}', 200, 'GET', response=response)
    return json.loads(response.content.decode('utf-8'))


def get_genre_seeds(headers: dict) -> json:
    """
    Retrieves available genre seeds from Spotify API.
    :param headers: request headers
    :return: genre seeds as a json obj
    """
    response = requests.get(f'{url_base}/recommendations/available-genre-seeds', headers=headers)
    error_handle('genre seeds', 200, 'GET', response=response)
    return json.loads(response.content.decode('utf-8'))


def get_available_devices(headers: dict) -> json:
    """
    Retrieves user's available playback devices
    :param headers: request headers
    :return: devices as json object
    """
    response = requests.get(f'{url_base}/me/player/devices', headers=headers)
    error_handle('playback devices', 200, 'GET', response=response)
    return json.loads(response.content.decode('utf-8'))


def play(device_id: str, context_uri: str, headers: dict):
    """
    Begin playback on user's account
    :param device_id: id of the device to play on
    :param context_uri: uri of what should be played
    :param headers: request headers
    """
    body = {'context_uri': context_uri}
    params = {'device_id': device_id}
    response = requests.put(f'{url_base}/me/player/play', json=body, headers=headers, params=params)
    error_handle('start playback', 204, 'PUT', response=response)

                            
def get_current_track(headers: dict) -> str:
    """
    Retrieve data about currently playing track
    :param headers: request headers
    :return: uri of current track
    """
    response = requests.get(f'{url_base}/me/player', headers=headers)
    error_handle('retrieve current track', 200, 'GET', response=response)
    return json.loads(response.content.decode('utf-8'))['item']['uri']

                            
def get_current_artists(headers: dict) -> list:
    """
    Retrieve list of artists from currently playing track
    :param headers: request headers
    :return: list of artist uris
    """
    response = requests.get(f'{url_base}/me/player', headers=headers)
    error_handle('retrieve current artists', 200, 'GET', response=response)
    return [str(x['uri']) for x in json.loads(response.content.decode('utf-8'))['item']['artists']]

                            
def like_track(headers: dict):
    """
    Like currently playing track
    :param headers: request headers
    """
    track = {'ids': get_current_track(headers).split(':')[2]}
    response = requests.put(f'{url_base}/me/tracks', headers=headers, params=track)
    error_handle('like track', 200, 'PUT', response=response)


def unlike_track(headers: dict):
    """
    Remove currently playing track from liked tracks
    :param headers: request headers
    """
    track = {'ids': get_current_track(headers).split(':')[2]}
    response = requests.delete(f'{url_base}/me/tracks', headers=headers, params=track)
    error_handle('remove liked track', 200, 'DELETE', response=response)


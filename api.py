#!/usr/bin/env python
import json
import requests

url_base = 'https://api.spotify.com/v1'


def error(request_type: str, status_code: int, reason: str):
    """
    Print error message and exit.
    :param request_type: type of request; get, put, post
    :param status_code: status code of the response
    :param reason: textual reason for response code
    """
    print(f'{request_type} request failed with status code {status_code}. Reason: {reason}')
    exit(1)


def error_handle(response=None, get=False, put=False, post=False):
    """
    Dispatch error message depending on request type
    :param response: response object
    :param get: GET request
    :param put: PUT request
    :param post: POST request
    """
    if get:
        if response.status_code != 200:
            error('GET', response.status_code, response.reason)
    elif put:
        if response.status_code != 202:
            error('PUT', response.status_code, response.reason)
    elif post:
        if response.status_code != 201:
            error('POST', response.status_code, response.reason)


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
    error_handle(response=response, get=True)
    return json.loads(response.content.decode('utf-8'))


def get_user_id(headers: dict) -> str:
    """
    Retrieve user ID from API.
    :param headers: request headers
    :return: user ID as a string
    """
    response = requests.get(f'{url_base}/me', headers=headers)
    error_handle(response=response, get=True)
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
    error_handle(response=response, post=True)
    return json.loads(response.content.decode('utf-8'))['id']


def upload_image(playlist_id: str, data: str, img_headers: dict):
    """
    Upload the generated image to the playlist
    :param playlist_id: id of the playlist
    :param data: base64 encoded jpeg image
    :param img_headers: request headers
    """
    response = requests.put(f'{url_base}/playlists/{playlist_id}/images', headers=img_headers, data=data)
    error_handle(response=response, put=True)


def add_to_playlist(tracks: list, playlist_id: str, headers: dict):
    """
    Add tracks to playlist.
    :param tracks: list of track URIs
    :param playlist_id: id of playlist
    :param headers: request headers
    """
    data = {'uris': tracks}
    response = requests.post(f'{url_base}/playlists/{playlist_id}/tracks', headers=headers, json=data)
    error_handle(response=response, post=True)


def get_recommendations(rec_params: dict, headers: dict) -> json:
    """
    Retrieve recommendations from API.
    :param rec_params: parameters for recommendation request
    :param headers: request headers
    :return: recommendations as json object
    """
    response = requests.get(f'{url_base}/recommendations', params=rec_params, headers=headers)
    error_handle(response=response, get=True)
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
    error_handle(response=response, get=True)
    return json.loads(response.content.decode('utf-8'))


def get_genre_seeds(headers: dict) -> json:
    """
    Retrieves available genre seeds from Spotify API.
    :param headers: request headers
    :return: genre seeds as a json obj
    """
    response = requests.get(f'{url_base}/recommendations/available-genre-seeds', headers=headers)
    error_handle(response=response, get=True)
    return json.loads(response.content.decode('utf-8'))

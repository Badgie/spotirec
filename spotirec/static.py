"""
Contains static data in constant objects
"""

from pathlib import Path
import sys

# regex
VALID_URI_RE = r'spotify:(artist|track):[a-zA-Z0-9]+'
PLAYLIST_URI_RE = r'spotify:playlist:[a-zA-Z0-9]+'
TRACK_URI_RE = r'spotify:track:[a-zA-Z0-9]+'
TUNE_RE = r'\w+_\w+=\d+(.\d+)?'
SHOW_EPI_RE = r'spotify:(show|episode):[a-zA-Z0-9]+'
FULL_URI_RE = r'spotify:(artist|track|show|episode):[a-zA-Z0-9]'

# urls
API_URL_BASE = 'https://api.spotify.com/v1'
OAUTH_AUTH_URL = 'https://accounts.spotify.com/authorize'
OAUTH_TOKEN_URL = 'https://accounts.spotify.com/api/token'

# paths
CONFIG_PATH = f'{Path.home()}/.config/spotirec'
CONFIG_FILE = 'spotirec.conf'
LOG_PATH = f'{Path.home()}/.config/spotirec/logs'

# misc
PORTS = [8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009]

# tuning
TUNE_PREFIX = ['max', 'min', 'target']
TUNE_ATTR = {'int':
             {'duration_ms': {'min': 0, 'max': sys.maxsize * 2 + 1, 'rec_min': 0,
                              'rec_max': 3600000,
                              'desc': 'The duration of the track in milliseconds',
                              'has_range': False, 'has_rec_range': False,
                              'range_sub': 'R+', 'rec_range_sub': 'N/A'},
              'key': {'min': 0, 'max': 11, 'rec_min': 0, 'rec_max': 11,
                      'desc': 'Pitch class of the track', 'has_range': True, 'has_rec_range': False,
                      'rec_range_sub': 'N/A'},
              'mode': {'min': 0, 'max': 1, 'rec_min': 0, 'rec_max': 1,
                       'desc': 'Modality of the track. 1 is major, 0 is minor',
                       'has_range': True, 'has_rec_range': False, 'rec_range_sub': 'N/A'},
              'time_signature': {'min': 0, 'max': 500, 'rec_min': 0, 'rec_max': 500,
                                 'desc': 'Estimated overall time signature of the track',
                                 'has_range': False, 'has_rec_range': False,
                                 'range_sub': 'N/A', 'rec_range_sub': 'N/A'},
              'popularity': {'min': 0, 'max': 100, 'rec_min': 0, 'rec_max': 100,
                             'desc': 'Popularity of the track. High is popular, low is barely '
                                     'known',
                             'has_range': True, 'has_rec_range': True}},
             'float':
                 {'acousticness': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 1.0,
                                   'desc': 'Confidence measure for whether or not the track '
                                           'is acoustic. High value is acoustic',
                                   'has_range': True, 'has_rec_range': True},
                  'danceability': {'min': 0.0, 'max': 1.0, 'rec_min': 0.1, 'rec_max': 0.9,
                                   'desc': 'How well fit a track is for dancing. Measurement '
                                           'includes among others tempo, rhythm stability, '
                                           'and beat strength. High value is suitable for dancing',
                                   'has_range': True, 'has_rec_range': True},
                  'energy': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 1.0,
                             'desc': 'Perceptual measure of intensity and activity. High '
                                     'energy is fast, loud, and noisy, and low is slow and mellow',
                             'has_range': True, 'has_rec_range': True},
                  'instrumentalness': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 1.0,
                                       'desc': 'Whether or not a track contains vocals. '
                                               'Low contains vocals, high is purely instrumental',
                                       'has_range': True, 'has_rec_range': True},
                  'liveness': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 0.4,
                               'desc': 'Predicts whether or not a track is live. High value is '
                                       'live',
                               'has_range': True, 'has_rec_range': True},
                  'loudness': {'min': -60, 'max': 0, 'rec_min': -20, 'rec_max': 0,
                               'desc': 'Overall loudness of the track, measured in decibels',
                               'has_range': True, 'has_rec_range': True},
                  'speechiness': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 0.3,
                                  'desc': 'Presence of spoken words. Low is a song, and high '
                                          'is likely to be a talk show or podcast',
                                  'has_range': True, 'has_rec_range': True},
                  'valence': {'min': 0.0, 'max': 1.0, 'rec_min': 0.0, 'rec_max': 1.0,
                              'desc': 'Positivity of the track. High value is positive, '
                                      'low value is negative',
                              'has_range': True, 'has_rec_range': True},
                  'tempo': {'min': 0.0, 'max': 220.0, 'rec_min': 60.0, 'rec_max': 210.0,
                            'desc': 'Overall estimated beats per minute of the track',
                            'has_range': True, 'has_rec_range': True}}}

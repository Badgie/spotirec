#!/usr/bin/env python
import time
import log


class Recommendation:
    """
    Recommendation object
    """
    LOGGER = None

    def __init__(self, t=time.localtime()):
        self.limit = 20
        self.limit_original = self.limit
        self.created_at = time.ctime(time.time())
        self.based_on = 'top genres'
        self.seed = ''
        self.seed_type = 'genres'
        self.seed_info = {}
        self.rec_params = {'limit': str(self.limit)}
        self.playlist_name = f'Spotirec-{t.tm_mday}-{t.tm_mon}-{t.tm_year}'
        self.playlist_id = ''
        self.auto_play = False
        self.playback_device = {}

    def playlist_description(self) -> str:
        """
        Create playlist description string to be insterted into playlist. Description contains
        date and time of creation, recommendation method, and seed.
        :return: description string
        """
        self.LOGGER.verbose('generating playlist description')
        desc = f'Created by Spotirec - {self.created_at} - based on {self.based_on} - seed: '
        seeds = ' | '.join(
            f'{str(x["name"])}{" - " + ", ".join(str(y) for y in x["artists"]) if x["type"] == "track" else ""}'
            for x in self.seed_info.values())
        self.LOGGER.debug(f'description: {desc}{seeds}')
        return f'{desc}{seeds}'

    def update_limit(self, limit: int, init=False):
        """
        Update playlist limit as object field and in request parameters.
        :param limit: user-defined playlist limit
        :param init: should only be true when updated by -l arg
        """
        self.LOGGER.verbose('updating limit')
        self.limit = limit
        self.rec_params['limit'] = str(self.limit)
        if init:
            self.limit_original = limit
        self.LOGGER.debug(f'limit: {limit}, original: {self.limit_original}')

    def print_selection(self):
        """
        Print seed selection into terminal.
        """
        self.LOGGER.info('Selection:')
        for x in self.seed_info.values():
            try:
                self.LOGGER.info(f'\t{x["type"].capitalize()}: {x["name"]} - {", ".join(str(y) for y in x["artists"])}')
            except KeyError:
                self.LOGGER.info(f'\t{x["type"].capitalize()}: {x["name"]}')

    def add_seed_info(self, data_dict=None, data_string=None):
        """
        Add info about a single seed to the object fields.
        :param data_dict: seed info as a dict if seed is artist or track
        :param data_string: seed info as a string if seed is genre
        """
        if data_string:
            self.seed_info[len(self.seed_info)] = {'name': data_string,
                                                   'type': 'genre'}
        else:
            self.seed_info[len(self.seed_info)] = {'name': data_dict['name'],
                                                   'id': data_dict['id'],
                                                   'type': data_dict['type']}
            try:
                assert data_dict['artists'] is not None
                self.seed_info[len(self.seed_info)-1]['artists'] = [x['name'] for x in data_dict['artists']]
            except (KeyError, AssertionError):
                pass
            self.LOGGER.debug(f'data: {self.seed_info[len(self.seed_info)-1]}')

    def create_seed(self):
        """
        Construct seed string to use in request and add to object field.
        """
        self.LOGGER.verbose('generating seed')
        if 'genres' in self.seed_type:
            self.seed = ','.join(str(x['name']) for x in self.seed_info.values())
        elif 'custom' in self.seed_type:
            self.rec_params['seed_tracks'] = ','.join(str(x['id']) for x in self.seed_info.values()
                                                      if x['type'] == 'track')
            self.rec_params['seed_artists'] = ','.join(str(x['id']) for x in self.seed_info.values()
                                                       if x['type'] == 'artist')
            self.rec_params['seed_genres'] = ','.join(str(x['name']) for x in self.seed_info.values()
                                                      if x['type'] == 'genre')
            self.LOGGER.debug(f'tracks: {self.rec_params["seed_tracks"]}, artists: {self.rec_params["seed_artists"]}, '
                              f'genres: {self.rec_params["seed_genres"]}')
            return
        else:
            self.seed = ','.join(str(x['id']) for x in self.seed_info.values())
        self.rec_params[f'seed_{self.seed_type}'] = self.seed
        self.LOGGER.debug(f'seeds: {self.seed}')

    def set_logger(self, logger: log.Log):
        self.LOGGER = logger

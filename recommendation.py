#!/usr/bin/env python
import time


class Recommendation:
    """
    Recommendation object
    """
    def __init__(self, t=time.localtime()):
        self.limit = 20
        self.created_at = time.ctime(time.time())
        self.based_on = 'top genres'
        self.seed = ''
        self.seed_type = 'genres'
        self.seed_info = {}
        self.rec_params = {'limit': str(self.limit)}
        self.playlist_name = f'Spotirec-{t.tm_mday}-{t.tm_mon}-{t.tm_year}'

    def playlist_description(self) -> str:
        """
        Create playlist description string to be insterted into playlist. Description contains
        date and time of creation, recommendation method, and seed.
        :return: description string
        """
        desc = f'Created by Spotirec - {self.created_at} - based on {self.based_on} - seed: '
        if 'tracks' in self.seed_type:
            seeds = ' | '.join(str(f'{x["name"]} - {", ".join(str(y) for y in x["artists"])}')
                               for x in self.seed_info.values())
            return f'{desc}{seeds}'
        else:
            seeds = ' | '.join(str(x["name"]) for x in self.seed_info.values())
            return f'{desc}{seeds}'

    def update_limit(self, limit: int):
        """
        Update playlist limit as object field and in request parameters.
        :param limit: user-defined playlist limit
        """
        self.limit = limit
        self.rec_params['limit'] = str(self.limit)

    def print_selection(self):
        """
        Print seed selection into terminal.
        """
        print('Selection:')
        for x in self.seed_info:
            print(f'\t{self.seed_info[x]}')

    def add_seed_info(self, data_dict=None, data_string=None):
        """
        Add info about a single seed to the object fields.
        :param data_dict: seed info as a dict if seed is artist or track
        :param data_string: seed info as a string if seed is genre
        """
        if 'genres' in self.seed_type:
            self.seed_info[len(self.seed_info)] = {'name': data_string}
        else:
            self.seed_info[len(self.seed_info)] = {'name': data_dict['name'],
                                                   'id': data_dict['id']}
            if 'tracks' in self.seed_type:
                self.seed_info[len(self.seed_info)-1]['artists'] = []
                for x in data_dict['artists']:
                    self.seed_info[len(self.seed_info) - 1]['artists'].append(x['name'])

    def create_seed(self):
        """
        Construct seed string to use in request and add to object field.
        """
        if 'genres' in self.seed_type:
            self.seed = ','.join(str(x['name']) for x in self.seed_info.values())
        else:
            self.seed = ','.join(str(x['id']) for x in self.seed_info.values())
        self.rec_params[f'seed_{self.seed_type}'] = self.seed

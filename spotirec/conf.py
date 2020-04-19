import json
import re
import configparser
import ast
from . import log
from pathlib import Path


class Config:
    CONFIG_DIR = f'{Path.home()}/.config/spotirec'
    CONFIG_FILE = 'spotirec.conf'
    URI_RE = r'spotify:(artist|track|show|episode):[a-zA-Z0-9]'
    LOGGER = None

    def set_logger(self, logger: log.Log):
        self.LOGGER = logger

    def open_config(self) -> configparser.ConfigParser:
        """
        Open configuration file as object
        :return: config object
        """
        try:
            # Read config and assert size
            self.LOGGER.verbose('getting config')
            c = configparser.ConfigParser()
            with open(f'{self.CONFIG_DIR}/{self.CONFIG_FILE}', 'r') as f:
                c.read_file(f)
            assert len(c.keys()) > 0
            return c
        except (FileNotFoundError, AssertionError):
            self.LOGGER.info('config file not found, generating...')
            # If config does not exist or is empty, convert old or create new and do recursive call
            self.convert_or_create_config()
            return self.open_config()

    def save_config(self, c: configparser.ConfigParser):
        """
        Write config to file
        :param c: config object
        """
        self.LOGGER.verbose('writing config')
        with open(f'{self.CONFIG_DIR}/{self.CONFIG_FILE}', 'w') as f:
            c.write(f)

    def convert_or_create_config(self):
        """
        Convert old config files to new. If old files do not exist, simply add the
        necessary sections.
        """
        c = configparser.ConfigParser()
        old_conf = ['spotirecoauth', 'presets', 'blacklist', 'devices', 'playlists']
        for x in old_conf:
            # Add new section
            c.add_section(x)
            try:
                with open(f'{self.CONFIG_DIR}/{x}', 'r') as f:
                    # Set each configuration to section
                    for y in json.loads(f.read()).items():
                        c.set(x, y[0], str(y[1]))
            except (FileNotFoundError, json.JSONDecodeError):
                # If file isn't found or is empty, pass and leave section empty
                if x == 'blacklist':
                    c.set(x, 'tracks', str({}))
                    c.set(x, 'artists', str({}))
                pass
        self.LOGGER.info('done')
        self.LOGGER.info('if you have the old style config files you may safely delete these, '
                         'or save them as backup')
        self.save_config(c)

    def get_oauth(self) -> dict:
        """
        Retrieve OAuth section from config
        :return: OAuth section as dict
        """
        c = self.open_config()
        try:
            self.LOGGER.verbose('getting oauth')
            return c['spotirecoauth']
        except KeyError:
            self.LOGGER.verbose('oauth not found, creating empty')
            c.add_section('spotirecoauth')
            self.save_config(c)
            return c['spotirecoauth']

    def get_blacklist(self) -> dict:
        """
        Retrieve blacklist section from config
        :return: blacklist section as dict
        """
        c = self.open_config()
        try:
            self.LOGGER.verbose('getting blacklist')
            blacklist = {}
            for x in c['blacklist'].items():
                # Parse each blacklist entry as dict
                blacklist[x[0]] = ast.literal_eval(x[1])
            return blacklist
        except KeyError:
            self.LOGGER.verbose('blacklist not found, creating empty')
            c.add_section('blacklist')
            c.set('blacklist', 'tracks', str({}))
            c.set('blacklist', 'artists', str({}))
            self.save_config(c)
            return {'tracks': ast.literal_eval(c.get('blacklist', 'tracks')),
                    'artists': ast.literal_eval(c.get('blacklist', 'artists'))}

    def check_item_in_blacklist(self, uri):
        """
        Checks whether or not a track or artist is blacklisted
        :param uri: uri of track or artist
        :return: bool: true if uri is blacklisted, false if not
        """
        return uri in self.get_blacklist()[f'{uri.split(":")[1]}s'].keys()

    def add_to_blacklist(self, uri_data: json, uri: str):
        """
        Add entry to blacklist
        :param uri_data: data regarding blacklist entry retrieved from API
        :param uri: URI of blacklist entry
        :return:
        """
        # Ensure input is valid
        if not re.match(self.URI_RE, uri):
            self.LOGGER.warning(f'uri {uri} is not a valid uri')
            return
        uri_type = uri.split(':')[1]
        # Convert entry to dict
        data = {'name': uri_data['name'], 'uri': uri}
        try:
            data['artists'] = [x['name'] for x in uri_data['artists']]
        except KeyError:
            pass
        c = self.open_config()
        self.LOGGER.info(f'adding {uri_type} {data["name"]} to blacklist')
        # Get the blacklist type entry from config and parse as dict, and add entry
        blacklist = ast.literal_eval(c.get('blacklist', f'{uri_type}s'))
        blacklist[uri] = data
        c.set('blacklist', f'{uri_type}s', str(blacklist))
        self.save_config(c)

    def remove_from_blacklist(self, uri: str):
        """
        Remove entry from blacklsit
        :param uri:
        :return:
        """
        # Ensure input is valid
        if not re.match(self.URI_RE, uri):
            self.LOGGER.warning(f'uri {uri} is not a valid uri')
            return
        c = self.open_config()
        uri_type = uri.split(':')[1]
        # Ensure entry exists and delete if so
        try:
            blacklist = ast.literal_eval(c.get('blacklist', f'{uri_type}s'))
            self.LOGGER.info(f'removing {uri_type} {blacklist[uri]["name"]} from blacklist')
            del blacklist[uri]
            c.set('blacklist', f'{uri_type}s', str(blacklist))
        except KeyError:
            self.LOGGER.error(f'{uri_type} {uri} does not exist in blacklist')
        self.save_config(c)

    def get_presets(self) -> dict:
        """
        Retrieve preset section from config
        :return: preset section as dict
        """
        c = self.open_config()
        try:
            self.LOGGER.verbose('getting presets')
            presets = {}
            for x in c['presets'].items():
                presets[x[0]] = ast.literal_eval(x[1])
            return presets
        except KeyError:
            self.LOGGER.verbose('presets not found, creating empty')
            c.add_section('presets')
            self.save_config(c)
            return c['presets']

    def save_preset(self, preset: dict, preset_id: str):
        """
        Add entry to presets
        :param preset: preset data
        :param preset_id: identifier of new preset
        """
        c = self.open_config()
        try:
            c['presets']
        except KeyError:
            c.add_section('presets')
        c.set('presets', preset_id, str(preset))
        self.LOGGER.info(f'added preset {preset_id} to config')
        self.save_config(c)

    def remove_preset(self, iden: str):
        """
        Remove entry from presets
        :param iden: identifier of preset to remove
        :return:
        """
        c = self.open_config()
        if c.remove_option('presets', iden):
            self.LOGGER.info(f'deleted preset {iden} from config')
            self.save_config(c)
        else:
            self.LOGGER.error(f'preset {iden} does not exist in config')

    def get_devices(self) -> dict:
        """
        Retrieve device section from config
        :return: device section as dict
        """
        c = self.open_config()
        try:
            self.LOGGER.verbose('getting devices')
            devices = {}
            for x in c['devices'].items():
                # Parse each preset entry as dict
                devices[x[0]] = ast.literal_eval(x[1])
            return devices
        except KeyError:
            self.LOGGER.verbose('devices not found, creating empty')
            c.add_section('devices')
            self.save_config(c)
            return c['devices']

    def save_device(self, device: dict, device_id: str):
        """
        Add entry to devices
        :param device: device data
        :param device_id: identifier of the new device
        :return:
        """
        c = self.open_config()
        try:
            c['devices']
        except KeyError:
            c.add_section('devices')
        c.set('devices', device_id, str(device))
        self.LOGGER.info(f'added device {device_id} to config')
        self.save_config(c)

    def remove_device(self, iden: str):
        """
        Remove entry from devices
        :param iden: identifier of the device to remove
        :return:
        """
        c = self.open_config()
        if c.remove_option('devices', iden):
            self.LOGGER.info(f'deleted device {iden} from config')
            self.save_config(c)
        else:
            self.LOGGER.error(f'device {iden} does not exist in config')

    def get_playlists(self) -> dict:
        """
        Retrieve playlist section from config
        :return: playlist section as dict
        """
        c = self.open_config()
        try:
            self.LOGGER.verbose('getting playlists')
            playlists = {}
            for x in c['playlists'].items():
                # Parse each playlist entry as dict
                playlists[x[0]] = ast.literal_eval(x[1])
            return playlists
        except KeyError:
            self.LOGGER.verbose('playlists not found, creating empty')
            c.add_section('playlists')
            self.save_config(c)
            return c['playlists']

    def save_playlist(self, playlist: dict, playlist_id: str):
        """
        Add entry to playlists
        :param playlist: playlist data
        :param playlist_id: identifier of the new playlist
        :return:
        """
        c = self.open_config()
        try:
            c['playlists']
        except KeyError:
            c.add_section('playlists')
        c.set('playlists', playlist_id, str(playlist))
        self.LOGGER.info(f'added playlist {playlist_id} to config')
        self.save_config(c)

    def remove_playlist(self, iden: str):
        """
        Remove entry from playlists
        :param iden: identifier of the playlist to remove
        :return:
        """
        c = self.open_config()
        if c.remove_option('playlists', iden):
            self.LOGGER.info(f'deleted playlist {iden} from config')
            self.save_config(c)
        else:
            self.LOGGER.error(f'playlist {iden} does not exist in config')

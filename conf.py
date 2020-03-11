import json
import re
import configparser
import ast
from pathlib import Path


CONFIG_DIR = f'{Path.home()}/.config/spotirec'
URI_RE = r'spotify:(artist|track):[a-zA-Z0-9]'


def open_config() -> configparser.ConfigParser:
    """
    Open configuration file as object
    :return: config object
    """
    try:
        # Read config and assert size
        c = configparser.ConfigParser()
        c.read_file(open(f'{CONFIG_DIR}/spotirec.conf'))
        assert len(c.keys()) > 0
        return c
    except (FileNotFoundError, AssertionError):
        print('Config file not found, generating...')
        # If config does not exist or is empty, convert old or create new and do recursive call
        convert_or_create_config()
        return open_config()


def save_config(c: configparser.ConfigParser):
    """
    Write config to file
    :param c: config object
    """
    c.write(open(f'{CONFIG_DIR}/spotirec.conf', 'w'))


def convert_or_create_config():
    """
    Convert old config files to new. If old files do not exist, simply add the necessary sections.
    """
    c = configparser.ConfigParser()
    old_conf = ['spotirecoauth', 'presets', 'blacklist', 'devices', 'playlists']
    for x in old_conf:
        # Add new section
        c.add_section(x)
        try:
            with open(f'{CONFIG_DIR}/{x}', 'r') as f:
                # Set each configuration to section
                for y in json.loads(f.read()).items():
                    c.set(x, y[0], str(y[1]))
        except (FileNotFoundError, json.JSONDecodeError):
            # If file isn't found or is empty, pass and leave section empty
            if x == 'blacklist':
                c.set(x, 'tracks', str({}))
                c.set(x, 'artists', str({}))
            pass
    print('Done')
    print('If you have the old style config files you may safely delete these, or save them as backup')
    save_config(c)


def get_oauth() -> dict:
    """
    Retrieve OAuth section from config
    :return: OAuth section as dict
    """
    c = open_config()
    try:    
        return c['spotirecoauth']
    except KeyError:
        c.add_section('spotirecoauth')
        save_config(c)
        return c['spotirecoauth']


def get_blacklist() -> dict:
    """
    Retrieve blacklist section from config
    :return: blacklist section as dict
    """
    c = open_config()
    try:
        blacklist = {}
        for x in c['blacklist'].items():
            # Parse each blacklist entry as dict
            blacklist[x[0]] = ast.literal_eval(x[1])
        return blacklist
    except KeyError:
        c.add_section('blacklist')
        save_config(c)
        return c['blacklist']


def add_to_blacklist(uri_data: json, uri: str):
    """
    Add entry to blacklist
    :param uri_data: data regarding blacklist entry retrieved from API
    :param uri: URI of blacklist entry
    :return:
    """
    uri_type = uri.split(':')[1]
    # Convert entry to dict
    data = {'name': uri_data['name'], 'uri': uri}
    try:
        data['artists'] = [x['name'] for x in uri_data['artists']]
    except KeyError:
        pass
    c = open_config()
    print(f'Adding {uri_type} {data["name"]} to blacklist')
    # Get the blacklist type entry from config and parse as dict, and add entry
    blacklist = ast.literal_eval(c.get('blacklist', f'{uri_type}s'))
    blacklist[uri] = data
    c.set('blacklist', f'{uri_type}s', str(blacklist))
    save_config(c)


def remove_from_blacklist(uri: str):
    """
    Remove entry from blacklsit
    :param uri:
    :return:
    """
    # Ensure input is valid
    if not re.match(URI_RE, uri):
        print(f'Error: uri {uri} is not a valid uri')
        return
    c = open_config()
    uri_type = uri.split(':')[1]
    # Ensure entry exists and delete if so
    try:
        blacklist = ast.literal_eval(c.get('blacklist', f'{uri_type}s'))
        print(f'Removing {uri_type} {blacklist[uri]["name"]} from blacklist')
        del blacklist[uri]
        c.set('blacklist', f'{uri_type}s', str(blacklist))
    except KeyError:
        print(f'Error: {uri_type} {uri} does not exist in blacklist')
    save_config(c)


def get_presets() -> dict:
    """
    Retrieve preset section from config
    :return: preset section as dict
    """
    c = open_config()
    try:
        presets = {}
        for x in c['presets'].items():
            presets[x[0]] = ast.literal_eval(x[1])
        return presets
    except KeyError:
        c.add_section('presets')
        save_config(c)
        return c['presets']


def save_preset(preset: dict, preset_id: str):
    """
    Add entry to presets
    :param preset: preset data
    :param preset_id: identifier of new preset
    """
    c = open_config()
    try:
        c['presets']
    except KeyError:
        c.add_section('presets')
    c.set('presets', preset_id, str(preset))
    print(f'Added preset {preset_id} to config')
    save_config(c)


def remove_preset(iden: str):
    """
    Remove entry from presets
    :param iden: identifier of preset to remove
    :return:
    """
    c = open_config()
    try:
        c.remove_option('presets', iden)
        print(f'Deleted preset {iden} from config')
        save_config(c)
    except KeyError:
        print(f'Error: preset {iden} does not exist in config')


def get_devices() -> dict:
    """
    Retrieve device section from config
    :return: device section as dict
    """
    c = open_config()
    try:
        devices = {}
        for x in c['devices'].items():
            # Parse each preset entry as dict
            devices[x[0]] = ast.literal_eval(x[1])
        return devices
    except KeyError:
        c.add_section('devices')
        save_config(c)
        return c['devices']


def save_device(device: dict, device_id: str):
    """
    Add entry to devices
    :param device: device data
    :param device_id: identifier of the new device
    :return:
    """
    c = open_config()
    try:
        c['devices']
    except KeyError:
        c.add_section('devices')
    c.set('devices', device_id, str(device))
    print(f'Added device {device_id} to config')
    save_config(c)


def remove_device(iden: str):
    """
    Remove entry from devices
    :param iden: identifier of the device to remove
    :return:
    """
    c = open_config()
    try:
        c.remove_option('devices', iden)
        print(f'Deleted device {iden} from config')
        save_config(c)
    except KeyError:
        print(f'Error: device {iden} does not exist in config')


def get_playlists() -> dict:
    """
    Retrieve playlist section from config
    :return: playlist section as dict
    """
    c = open_config()
    try:
        playlists = {}
        for x in c['playlists'].items():
            # Parse each playlist entry as dict
            playlists[x[0]] = ast.literal_eval(x[1])
        return playlists
    except KeyError:
        c.add_section('playlists')
        save_config(c)
        return c['playlists']


def save_playlist(playlist: dict, playlist_id: str):
    """
    Add entry to playlists
    :param playlist: playlist data
    :param playlist_id: identifier of the new playlist
    :return:
    """
    c = open_config()
    try:
        c['playlists']
    except KeyError:
        c.add_section('playlists')
    c.set('playlists', playlist_id, str(playlist))
    print(f'Added playlist {playlist_id} to config')
    save_config(c)


def remove_playlist(iden: str):
    """
    Remove entry from playlists
    :param iden: identifier of the playlist to remove
    :return:
    """
    c = open_config()
    try:
        c.remove_option('playlists', iden)
        print(f'Deleted playlist {iden} from config')
        save_config(c)
    except KeyError:
        print(f'Error: playlist {iden} does not exist in config')

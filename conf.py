import json
import re
import configparser
import ast
from pathlib import Path


CONFIG_DIR = f'{Path.home()}/.config/spotirec'
URI_RE = r'spotify:(artist|track):[a-zA-Z0-9]'


def open_config() -> configparser.ConfigParser:
    try:
        c = configparser.ConfigParser()
        c.read_file(open(f'{CONFIG_DIR}/spotirec.conf'))
        assert len(c.keys()) > 0
        return c
    except (FileNotFoundError, AssertionError):
        print('Config file not found, generating...')
        convert_or_create_config()
        return open_config()


def save_config(c: configparser.ConfigParser):
    c.write(open(f'{CONFIG_DIR}/spotirec.conf', 'w'))


def convert_or_create_config():
    c = configparser.ConfigParser()
    old_conf = ['spotirecoauth', 'presets', 'blacklist', 'devices', 'playlists']
    for x in old_conf:
        c.add_section(x)
        try:
            with open(f'{CONFIG_DIR}/{x}', 'r') as f:
                for y in json.loads(f.read()).items():
                    c.set(x, y[0], str(y[1]))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    print('Done')
    print('If you have the old style config files you may safely delete these, or save them as backup')
    save_config(c)


def get_oauth() -> dict:
    c = open_config()
    try:
        c['spotirecoauth']
    except KeyError:
        c.add_section('spotirecoauth')
        save_config(c)
    return c['spotirecoauth']


def get_blacklist() -> dict:
    c = open_config()
    try:
        blacklist = {}
        for x in c['blacklist'].items():
            blacklist[x[0]] = ast.literal_eval(x[1])
        return blacklist
    except KeyError:
        c.add_section('blacklist')
        save_config(c)
        return c['blacklist']


def add_to_blacklist(uri_data: json, uri: str):
    uri_type = uri.split(':')[1]
    data = {'name': uri_data['name'], 'uri': uri}
    try:
        data['artists'] = [x['name'] for x in uri_data['artists']]
    except KeyError:
        pass
    c = open_config()
    print(f'Adding {uri_type} {data["name"]} to blacklist')
    blacklist = ast.literal_eval(c.get('blacklist', f'{uri_type}s'))
    blacklist[uri] = data
    c.set('blacklist', f'{uri_type}s', str(blacklist))
    save_config(c)


def remove_from_blacklist(uri: str):
    if not re.match(URI_RE, uri):
        print(f'Error: uri {uri} is not a valid uri')
        return
    c = open_config()
    uri_type = uri.split(':')[1]
    try:
        blacklist = ast.literal_eval(c.get('blacklist', f'{uri_type}s'))
        print(f'Removing {uri_type} {blacklist[uri]["name"]} from blacklist')
        del blacklist[uri]
        c.set('blacklist', f'{uri_type}s', str(blacklist))
    except KeyError:
        print(f'Error: {uri_type} {uri} does not exist in blacklist')
    save_config(c)


def get_presets() -> dict:
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
    c = open_config()
    try:
        c['presets']
    except KeyError:
        c.add_section('presets')
    c.set('presets', preset_id, str(preset))
    print(f'Added preset {preset_id} to config')
    save_config(c)


def remove_preset(iden: str):
    c = open_config()
    try:
        c.remove_option('presets', iden)
        print(f'Deleted preset {iden} from config')
        save_config(c)
    except KeyError:
        print(f'Error: preset {iden} does not exist in config')


def get_devices() -> dict:
    c = open_config()
    try:
        devices = {}
        for x in c['devices'].items():
            devices[x[0]] = ast.literal_eval(x[1])
        return devices
    except KeyError:
        c.add_section('devices')
        save_config(c)
        return c['devices']


def save_device(device: dict, device_id: str):
    c = open_config()
    try:
        c['devices']
    except KeyError:
        c.add_section('devices')
    c.set('devices', device_id, str(device))
    print(f'Added device {device_id} to config')
    save_config(c)


def remove_device(iden: str):
    c = open_config()
    try:
        c.remove_option('devices', iden)
        print(f'Deleted device {iden} from config')
        save_config(c)
    except KeyError:
        print(f'Error: device {iden} does not exist in config')


def get_playlists() -> dict:
    c = open_config()
    try:
        playlists = {}
        for x in c['playlists'].items():
            playlists[x[0]] = ast.literal_eval(x[1])
        return playlists
    except KeyError:
        c.add_section('playlists')
        save_config(c)
        return c['playlists']


def save_playlist(playlist: dict, playlist_id: str):
    c = open_config()
    try:
        c['playlists']
    except KeyError:
        c.add_section('playlists')
    c.set('playlists', playlist_id, str(playlist))
    print(f'Added playlist {playlist_id} to config')
    save_config(c)


def remove_playlist(iden: str):
    c = open_config()
    try:
        c.remove_option('playlists', iden)
        print(f'Deleted playlist {iden} from config')
        save_config(c)
    except KeyError:
        print(f'Error: playlist {iden} does not exist in config')

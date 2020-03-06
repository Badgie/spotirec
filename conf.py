import configparser
import json
from pathlib import Path


CONFIG_DIR = f'{Path.home()}/.config/spotirec'


def open_config() -> configparser.ConfigParser:
    try:
        with open(f'{CONFIG_DIR}/spotirec.conf') as f:
            c = configparser.ConfigParser()
            c.read_file(f)
            return c
    except FileNotFoundError:
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
                    c.set(x, y[0], json.dumps(y[1]) if type(y[1]) == dict else str(y[1]))
        except FileNotFoundError:
            pass
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
            blacklist[x[0]] = json.loads(x[1])
        return blacklist
    except KeyError:
        c.add_section('blacklist')
        save_config(c)
        return c['blacklist']


def get_presets() -> dict:
    c = open_config()
    try:
        presets = {}
        for x in c['presets'].items():
            presets[x[0]] = json.loads(x[1])
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
    c['presets'][preset_id] = json.dumps(preset)
    print(f'Added preset {preset_id} to config')
    save_config(c)


def remove_preset(iden: str):
    c = open_config()
    try:
        del c['presets'][iden]
        print(f'Deleted preset {iden} from config')
        save_config(c)
    except KeyError:
        print(f'Error: preset {iden} does not exist in config')


def get_devices() -> dict:
    c = open_config()
    try:
        devices = {}
        for x in c['devices'].items():
            devices[x[0]] = json.loads(x[1])
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
    c['devices'][device_id] = json.dumps(device)
    print(f'Added device {device_id} to config')
    save_config(c)


def remove_device(iden: str):
    c = open_config()
    try:
        del c['devices'][iden]
        print(f'Deleted device {iden} from config')
        save_config(c)
    except KeyError:
        print(f'Error: device {iden} does not exist in config')


def get_playlists() -> dict:
    c = open_config()
    try:
        playlists = {}
        for x in c['playlists'].items():
            playlists[x[0]] = json.loads(x[1])
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
    c['playlists'][playlist_id] = json.dumps(playlist)
    print(f'Added playlist {playlist_id} to config')
    save_config(c)


def remove_playlist(iden: str):
    c = open_config()
    try:
        del c['playlists'][iden]
        print(f'Deleted playlist {iden} from config')
        save_config(c)
    except KeyError:
        print(f'Error: playlist {iden} does not exist in config')
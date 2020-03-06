import configparser
import json
import re
from pathlib import Path


CONFIG_DIR = f'{Path.home()}/.config/spotirec'
URI_RE = r'spotify:(artist|track):[a-zA-Z0-9]'
SECTION_RE = r'^\[([a-zA-Z]+)\]$'
OPTION_RE = r'([a-z\_]*) = ([a-zA-Z0-9{}\[\]:,\"])'
INT_RE = r'^([0-9]+)$'
FLOAT_RE = r'^([0-9]+)\.([0-9]+)$'
DICT_RE = r'\{.+\}'


def config_test():
    config = {}
    current_section = ''
    with open(f'{CONFIG_DIR}/spotirec.conf') as f:
        for x in f.readlines():
            line = x.strip('\n')
            if re.match(SECTION_RE, line):
                config[line.strip('[]')] = {}
                current_section = line.strip('[]')
            elif re.match(OPTION_RE, line):
                option = line.split(' = ')
                if re.match(INT_RE, option[1]):
                    val = int(option[1])
                elif re.match(FLOAT_RE, option[1]):
                    val = float(option[1])
                elif re.match(DICT_RE, option[1]):
                    print(option[1])
                    val = json.loads(option[1])
                else:
                    val = str(option[1])
                config[current_section][option[0]] = val
    print(type(config['blacklist']['artists']))


def open_config() -> dict:
    config = {}
    current_section = ''
    try:
        with open(f'{CONFIG_DIR}/spotirec.conf') as f:
            for x in f.readlines():
                line = x.strip('\n')
                if re.match(SECTION_RE, line):
                    config[line.strip('[]')] = {}
                    current_section = line.strip('[]')
                elif re.match(OPTION_RE, line):
                    option = line.split(' = ')
                    if re.match(INT_RE, option[1]):
                        val = int(option[1])
                    elif re.match(FLOAT_RE, option[1]):
                        val = float(option[1])
                    elif re.match(DICT_RE, option[1]):
                        val = dict(option[1])
                    else:
                        val = str(option[1])
                    config[current_section][option[0]] = val
            assert len(config) > 0
            return config
    except (FileNotFoundError, AssertionError):
        convert_or_create_config()
        return open_config()


def save_config(c: dict):
    conf = ''
    for x in c.items():
        conf += f'[{x[0]}]\n'
        for y in x[1].items():
            conf += f'{y[0]} = {y[1]}\n'
        conf += '\n'
    with open(f'{CONFIG_DIR}/spotirec.conf', 'w') as f:
        f.write(conf)


def convert_or_create_config():
    c = {}
    old_conf = ['spotirecoauth', 'presets', 'blacklist', 'devices', 'playlists']
    for x in old_conf:
        c[x] = {}
        try:
            with open(f'{CONFIG_DIR}/{x}', 'r') as f:
                for y in json.loads(f.read()).items():
                    c[x][y[0]] = json.dumps(y[1]) if type(y[1]) == dict else str(y[1])
        except FileNotFoundError:
            pass
    save_config(c)


def get_oauth() -> dict:
    c = open_config()
    print(c)
    try:
        c['spotirecoauth']
    except KeyError:
        c['spotirecoauth'] = {}
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
        c['blacklist'] = {}
        save_config(c)
        return c['blacklist']


def add_to_blacklist(uri_data: json, uri: str):
    data = {'name': uri_data['name'], 'uri': uri}
    try:
        data['artists'] = [x['name'] for x in uri_data['artists']]
    except KeyError:
        pass
    c = open_config()
    c['blacklist'][f'{uri.split(":")[1]}s'][uri] = data
    save_config(c)


def remove_from_blacklist(uri: str):
    if not re.match(URI_RE, uri):
        print(f'Error: uri {uri} is not a valid uri')
        return
    c = open_config()
    print(type(c['blacklist']['artists']))
    uri_type = uri.split(':')[1]
    try:
        print(f'Removing {uri_type} {c["blacklist"][f"{uri_type}s"][uri]["name"]} from blacklist')
        del c['blacklist'][f'{uri_type}s'][uri]
    except KeyError:
        print(f'Error: {uri_type} {uri} does not exist in blacklist')
    save_config(c)


def get_presets() -> dict:
    c = open_config()
    try:
        presets = {}
        for x in c['presets'].items():
            presets[x[0]] = json.loads(x[1])
        return presets
    except KeyError:
        c['presets'] = {}
        save_config(c)
        return c['presets']


def save_preset(preset: dict, preset_id: str):
    c = open_config()
    try:
        c['presets']
    except KeyError:
        c['presets'] = {}
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
        c['devices'] = {}
        save_config(c)
        return c['devices']


def save_device(device: dict, device_id: str):
    c = open_config()
    try:
        c['devices']
    except KeyError:
        c['devices'] = {}
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
        c['playlists'] = {}
        save_config(c)
    return c['playlists']


def save_playlist(playlist: dict, playlist_id: str):
    c = open_config()
    try:
        c['playlists']
    except KeyError:
        c['playlists'] = {}
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
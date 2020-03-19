<p align="center">
  <img alt="GitHub release" src="https://img.shields.io/github/release/badgie/spotirec.svg">
  <img alt="GitHub" src="https://img.shields.io/github/license/badgie/spotirec.svg">
  <img alt="AUR votes" src="https://img.shields.io/aur/votes/spotirec-git.svg?label=AUR%20votes">
  <img alt="GitHub last commit (master)" src="https://img.shields.io/github/last-commit/badgie/spotirec/master.svg?label=last%20update">
</p>

# Spotirec
A tool that can create a playlist of recommendations based on the user's top artists or tracks, or genres extracted from top artists with various parameters - a sort of Discover Weekly on demand. Also includes functionality for various other Spotify-related actions, such as saving the currently playing track.

## Table of Contents
- [Installation](#installation)
  - [AUR](#aur-helper)
  - [Manual](#manual)
- [Usage](#usage)
  - [Recommendation Schemes](#recommendation-schemes)
  - [Preserving Playlists](#preserving-playlists)
  - [Limits](#limits)
  - [Presets](#presets)
  - [Tuning](#tuning)
  - [Blacklists](#blacklists)
  - [Autoplay](#autoplay)
  - [Devices](#devices)
  - [Saving Playlists](#saving-playlists)
  - [Saving Tracks](#saving-tracks)
  - [Printing](#printing)
  - [Playback](#playback)
  - [Logging](#logging)
- [Troubleshooting](#troubleshooting)

## Installation
When installing Spotirec, you have two options.

#### AUR Helper
Spotirec is packaged for [AUR](https://aur.archlinux.org/packages/spotirec-git/), and as such it can be installed using an AUR helper
```
yay -S spotirec-git
```

#### Manual
On any other distribution you need to install Spotirec manually. Spotirec has three dependencies
```
bottle>=0.12.17
requests>=2.22.0
Pillow>=6.2.1
```
If available, these **should** be installed as packages through your package manager. Alternatively, these can be installed through `pip` - this should only be done as a last resort.

Once these are installed, you can proceed to install Spotirec
```
git clone https://github.com/Badgie/spotirec.git
cd spotirec

mkdir -p /usr/lib/spotirec
mkdir -p /usr/bin
mkdir -p $HOME/.config/spotirec

install tuning-opts -t $HOME/.config/spotirec
install spotirec.py oauth2.py conf.py recommendation.py api.py -t /usr/lib/spotirec

ln -s /usr/lib/spotirec/spotirec.py /usr/bin/spotirec
```

---

Run the script in terminal for a first time setup
```
$ spotirec
```
The first time setup will cache access and refresh tokens used to perform various remote actions on your spotify account. The first time setup will host a localhost port and open this in your browser. On this page you simply log in to your spotify account to authorize access to Spotirec - once this is done, you can close the page and exit the script.


## Usage
To use Spotirec, simply run it from terminal
```
$ spotirec
```

### Recommendation schemes
You can pass arguments to specify the what the recommendations should be based on - these are mutually exclusive
```
$ spotirec -t 
$ spotirec -a
$ spotirec -tc
$ spotirec -ac
$ spotirec -gc
$ spotirec -gcs
$ spotirec -c
```
where
- `-t` is based off your 5 most played tracks,
- `-a` is based off your 5 most played artists,
- `-tc` you can define 1-5 of your most played tracks,
- `-ac` you can define 1-5 of your most played artists,
- `-gc` you can define 1-5 of your most played valid seed genres,
- `-gcs` you can define 1-5 preset genre seeds,
- `-c` you can manually input 1-5 genres, artist uris, or track uris

By default, the script will base recommendations off of your top valid seed genres extracted from your top artists. For this method, pass none of the above 7 arguments.

On all non-custom schemes, e.g.; `-a`, `-t`, and no-arg, you can specify how many seeds should be included in the recommendation. The value must be in the range 1-5, and the default value is 5
```
$ spotirec 3
$ spotirec -a 2
$ spotirec -t 4
```
Note that if this option is used with no-arg, it **must** be the very first argument

### Preserving Playlists
By default, Spotirec caches the id of the first playlist created and uses this every time new recommendations are requested, meaning that any old tracks are overwritten. To avoid this and create a new playlist instead, pass the `--preserve` flag. 

### Limits
You can add a limit as an integer value with the `-l` argument
```
$ spotirec -l 50
```
This option determines how many tracks should be added to your new playlist. The default value is 20, the minimum value is 1, and the max value is 100.

### Presets
You can save the settings for a recommendation with the `--save-preset` flag followed by a name
```
$ spotirec -t --save-preset preset_name -l 50 --tune prefix_attribute=value prefix_attribute=value
```
To load and use a saved preset, pass the `--load-preset` flag followed by the name of the preset
```
$ spotirec --load-preset preset_name
```
To remove one or more saved presets, pass the `--remove-presets` flag followed by a sequence of preset names
```
$ spotirec --remove-presets preset_name0 preset_name1 preset_name2
```
If you forgot which presets you have saved, see [printing](#printing)

### Tuning
You can also specify tunable attributes with the `--tune` flag, followed by any number of whitespace separated inputs on the form `prefix_attribute=value`
```
$ spotirec --tune prefix_attribute=value prefix_attribute=value
```

#### Prefixes

| Prefix | Function |
|---|---|
| max | The attribute value serves as a hard ceiling |
| min | The attribute value serves as a hard floor |
| target | The attribute value serves as a target for recommendations. Recommendations will be as close as possible to the value. |

#### Attributes
| Attribute | Data type | Range | Recomm. range | Function |
|---|---|---|---|---|
| duration_ms | int | **R+** | N/A | The duration of the track in milliseconds. |
| key | int | 0-11 | N/A | [Pitch class](https://en.wikipedia.org/wiki/Pitch_class#Other_ways_to_label_pitch_classes) of the track. |
| mode | int | 0-1 | N/A | Modality of the track. 1 is major, 0 is minor. |
| time_signature | int | N/A | N/A | Estimated overall [time signature](https://en.wikipedia.org/wiki/Time_signature) of the track. |
| popularity | int | 0-100 | 0-100 | Popularity of the track. High is popular, low is barely known. |
| acousticness | float | 0.0-1.0 | 0.0-1.0 | Confidence measure for whether or not the track is acoustic. High value is acoustic. |
| danceability | float | 0.0-1.0 | 0.1-0.9 | How well fit a track is for dancing. Measurement includes among others tempo, rhythm stability, and beat strength. High value is suitable for dancing. |
| energy | float | 0.0-1.0 | 0.0-1.0 | Perceptual measure of intensity and activity. High energy is fast, loud, and noisy, and low is slow and mellow. |
| instrumentalness | float | 0.0-1.0 | 0.0-1.0 | Whether or not a track contains vocals. Low contains vocals, high is purely instrumental. |
| liveness | float | 0.0-1.0 | 0.0-0.4 | Predicts whether or not a track is live. High value is live. |
| loudness | float | -60-0 | -20-0 | Overall loudness of the track, measured in decibels. |
| speechiness | float | 0.0-1.0 | 0.0-0.3 | Presence of spoken words. Low is a song, high is likely to be a talk show or podcast. |
| valence | float | 0.0-1.0 | 0.0-1.0 | Positivity of the track. High value is positive, low value is negative. |
| tempo | float | 0.0-220.0 | 60.0-210.0 | Overall estimated beats per minute of the track. |

Recommendations may be scarce outside the recommended range.

### Blacklists
To blacklist tracks or artists, pass the `-b` argument followed by an arbitrary number of whitespace separated Spotify URIs
```
$ spotirec -b spotify:track:id spotify:track:id spotify:artist:id
```
To remove entries from your blacklist, pass the `-br` argument followed by an arbitrary number of whitespace separated Spotify URIs
```
$ spotirec -br spotify:track:id spotify:track:id spotify:artist:id
```
To blacklist the currently playing track, or the artists that created the track, pass the `-bc` argument followed by either 'artist' or 'track'
```
$ spotirec -bc track
$ spotirec -bc artist
```
If you forgot which tracks and artists you have blacklisted, see [printing](#printing)

### Autoplay
You can also automatically play your new playlist upon creation using the `--play` flag followed by a name of a saved device - see [devices](#devices)
```
$ spotirec --play device_name
```

### Devices
You can save devices using the `--save-device` flag, whereafter you will be prompted to select a device from your currently connected devices, and to input a name that will serve as an identifier
```
$ spotirec --save-device
Name                   Type
0. Phone               Smartphone
1. Laptop              Computer
Select a device by index [0]: 1
Enter an identifier for your device: laptop
Added device laptop to config
```
To remove one or more saved devices, pass the `--remove-devices` flag followed by a sequence of names for devices
```
$ spotirec --remove-devices device_name0 device_name1 device_name2
```
If you forgot which devices you have saved, see [printing](#printing)

### Saving playlists
You can save playlists using the `--save-playlist` flag, whereafter you will be prompted to input an identifier for the playlist, and then a URI for the playlist. For further usage of this, see [saving tracks](#saving-tracks)
```
$ spotirec --save-playlist
Please input an identifier for your playlist: test
Please input the URI for your playlist: spotify:playlist:0Vu97Y7WoJgBlFzAwbrZ8h
Added playlist test to config
```
To remove one or more saved playlists, pass the `--remove-playlists` flag followed by a sequence of names for playlists
```
$ spotirec --remove-playlists playlist_name0 playlist_name1 playlist_name2
```
If you forgot which playlists you have saved, see [printing](#printing)

### Saving Tracks
To like the currently playing track, pass the `-s` argument
```
$ spotirec -s
```
To remove the currently playing track from liked tracks, pass the `-sr` argument
```
$ spotirec -sr
```

To add the currently playing track to a specific playlist, pass the `--add-to` flag followed by a name for a saved playlist, or a playlist URI
```
$ spotirec --add-to playlist_name
$ spotirec --add-to spotify:playlist:0Vu97Y7WoJgBlFzAwbrZ8h
```

To remove the currently playing track from a specific playlist, pass the `--remove-from` flag followed by a name for a saved playlist, or a playlist URI
```
$ spotirec --remove-from playlist_name
$ spotirec --remove-from spotify:playlist:0Vu97Y7WoJgBlFzAwbrZ8h
```

### Printing
You can print lists of various data contained within your Spotify account and config files using the `--print` flag followed by any of the following strings, depending on what you would like to print
```
$ spotirec --print artists
$ spotirec --print tracks
$ spotirec --print genres
$ spotirec --print genre-seeds
$ spotirec --print devices
$ spotirec --print blacklist
$ spotirec --print presets
$ spotirec --print playlists
$ spotirec --print tuning
```

You can also print various features of a track with the `--track-features` flag followed by either a URI or 'current' if you want information about the currently playing track. Features include track attributes (as used in [tuning](#tuning)) and URIs.
```
$ spotirec --track-features current
$ spotirec --track-features spotify:track:4uLU6hMCjMI75M1A2tKUQC
```

### Playback
You can change playback to a different device by passing the `--transfer-playback` device followed by an identifier for a saved device
```
$ spotirec --transfer-playback phone
```

### Logging
If you want more or less logging in terminal, you can specify this with the following flags
```
# log only errors and warnings
$ spotirec -q
$ spotirec --quiet

# log errors, warnings, and few relevant info messages
# pass nothing
$ spotirec

# log errors, warnings, and extensive info messages
$ spotirec -v
$ spotirec --verbose

# log errors, warnings, extensive info messages, and relevant data for debugging
$ spotirec --debug

# any of the above, but suppress warnings
$ spotirec --suppress-warnings
$ spotirec -q --suppress-warnings
$ spotirec -v --suppress-warnings
$ spotirec --debug --suppress-warnings
```
Passing `--log` will, no matter which of the above flags you have passed, log on `--debug` level to a file in your config directory. This is also done on errors, no matter the presence of `--log`.
```
$ spotirec --log
INFO: saved log to /path/to/.config/spotirec/logs/spotirec_19-3-2020.log
```

## Troubleshooting
If you encounter issues with Spotirec, you can try either passing the `--log` flag - this will log all outputs on all logging levels to a file in your config directory -, or the `--debug` flag - this will yield the same information, however, to your terminal instead. On errors, the former should be done automatically.

If the error is related to a request, you should get a status code - consult the table in the `Response Status Codes` section [here](https://developer.spotify.com/documentation/web-api/)

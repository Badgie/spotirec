# Spotirec
Script that creates a playlist of recommendations based on the user's top artists or tracks, or genres extracted from top artists. A sort of Discover Weekly on demand.

## Installation
When installing Spotirec, you have two options.

#### AUR Helper
Spotirec is packaged for AUR, and as such it can be installed using an AUR helper
```
yay -S spotirec
```

#### Manual
On any other distribution you need to install Spotirec manually. Spotirec has two dependencies
```
bottle>=0.12.17
requests>=2.22.0
```
If available, these should be installed as packages through your package manager. Alternatively, these can be installed through `pip` - this should only be done as a last resort.

Once these are installed, you can proceed to install Spotirec
```
git clone https://github.com/Badgie/spotirec.git
cd spotirec

mkdir -p /usr/lib/spotirec
mkdir -p /usr/bin
mkdir -p $HOME/.config/spotirec

install spotirec.py oauth2.py -t /usr/lib/spotirec

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
Optionally you can add a limit as an integer value
```
$ spotirec 50
```
This option determines how many tracks should be added to your new playlist. The default value is 20, and the max value is 100.

Additionally, you can pass arguments to specify the what the recommendations should be based on
```
$ spotirec -t 
$ spotirec -a
$ spotirec -tc
$ spotirec -ac
$ spotirec -gc
```
where
- `-t` is based off your most played tracks,
- `-a` is based off your most played artists,
- `-tc` you can define 1-5 of your most played tracks,
- `-ac` you can define 1-5 of your most played artists,
- `-gc` you can define 1-5 genre seeds

By default, the script will base recommendations off of your top genres extracted from your top artists. For this method, pass none of the above 5 arguments.

You can also specify tunable attributes with the `--tune` option, followed by any number of whitespace separated arguments on the form `prefix_attribute=value`
```
$ spotirec --tune prefix_attribute=value prefix_attribute=value
```
If you wish to specify a limit, this should appear before `--tune`
### Prefixes

| Prefix | Function |
|---|---|
| max | The attribute value serves as a hard ceiling |
| min | The attribute value serves as a hard floor |
| target | The attribute value serves as a target for recommendations. Recommendations will be as close as possible to the value. |

### Attributes
| Attribute | Data type | Range | Recomm. range | Function |
|---|---|---|---|---|
| duration_ms | int | **R+** | N/A | The duration of the track in milliseconds. |
| key | int | 0-11 | N/A | [Pitch class](https://en.wikipedia.org/wiki/Pitch_class#Other_ways_to_label_pitch_classes) of the track. |
| mode | int | 0-1 | N/A | Modality of the track. 1 is major, 0 is minor. |
| time_signature | int | N/A | N/A | Estimated overall [time signature](https://en.wikipedia.org/wiki/Time_signature) of the track. |
| popularity | int | 0-100 | 0-100 | Popularity of the track. High is popular, low is barely known |
| acousticness | float | 0.0-1.0 | Any | Confidence measure for whether or not the track is acoustic. High value is acoustic. |
| danceability | float | 0.0-1.0 | 0.1-0.9 | How well fit a track is for dancing. Measurement includes among others tempo, rhythm stability, and beat strength. High value is suitable for dancing. |
| energy | float | 0.0-1.0 | Any | Perceptual measure of intensity and activity. High energy is fast, loud, and noisy, and low is slow and mellow. |
| instrumentalness | float | 0.0-1.0 | 0.0-1.0 | Whether or not a track contains vocals. Low contains vocals, high is purely instrumental. |
| liveness | float | 0.0-1.0 | 0.0-0.4 | Predicts whether or not a track is live. High value is live. |
| loudness | float | -60-0 | -20-0 | Overall loudness of the track, measured in decibels. |
| speechiness | float | 0.0-1.0 | 0.0-0.3 | Presence of spoken words. Low is a song, and high is likely to be a talk show or podcast. |
| valence | float | 0.0-1.0 | Any | Positivity of the track. High value is positive, and low value is negative. |
| tempo | float | 0.0-220.0 | 60.0-210.0 | Overall estimated beats per minute of the track. |

Recommendations may be sparce outside the recommended range.

---

To blacklist tracks or artists, pass the `-b` option followed by an arbitrary number of whitespace separated Spotify URIs
```
$ spotirec -b spotify:track:id spotify:track:id spotify:artist:id
```
To see your current blacklist entries, pass the `list` argument to the `-b` option
```
$ spotirec -b list
```

## Troubleshooting
If you encounter issues adding tracks to your playlist, try running the script from a terminal. This should output a status code of the request, as well as some information about the code. Should you need additional help regarding status codes, consult the table in the `Response Status Codes` section [here](https://developer.spotify.com/documentation/web-api/)
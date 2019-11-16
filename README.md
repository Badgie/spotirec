# Spotirec
Script that creates a playlist of recommendations based on genres extracted from the user's top artists. A sort of Discover Weekly on demand.

## Setup
Install dependencies with `pip`
```
pip install requests
pip install spotipy
pip install bottle
```
---
Run the script in terminal for a first time setup
```
$ python /path/to/spotirec.py
```
The first time setup will cache access and refresh tokens used to perform various remote actions on your spotify account. The first time setup will host a localhost port and open this in your browser. On this page you simply log in to your spotify account to authorize access to Spotirec - once this is done, you can close the page and exit the script.

## Usage
To use Spotirec, simply run it from terminal
```
$ python /path/to/spotirec.py
```
Optionally you can add a limit as an integer value
```
$ python /path/to/spotirec.py 50
```
This option determines how many tracks should be added to your new playlist. The default value is 20, and the max value is 100.

## Troubleshooting
If you encounter issues adding tracks to your playlist, try running the script from a terminal. This should output a status code of the request, as well as some information about the code. Should you need additional help regarding status codes, consult the table in the `Response Status Codes` section [here](https://developer.spotify.com/documentation/web-api/)
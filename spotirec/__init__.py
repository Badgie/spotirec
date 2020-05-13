import os
from shutil import copyfile
from pathlib import Path

CONFIG_PATH = f'{Path.home()}/.config/spotirec'
TUNING_FILE = f'{Path.home()}/.config/spotirec/tuning-opts'

# ensure config dir exists
if not os.path.isdir(CONFIG_PATH):
    os.makedirs(CONFIG_PATH)

# ensure tuning file exists
if not os.path.isfile(TUNING_FILE):
    copyfile('tuning-opts', TUNING_FILE)

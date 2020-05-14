import os

from .static import CONFIG_PATH

# ensure config dir exists
if not os.path.isdir(CONFIG_PATH):
    os.makedirs(CONFIG_PATH)

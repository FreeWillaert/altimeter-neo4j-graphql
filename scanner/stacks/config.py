import json
from os import name
import os.path

CONFIG_FILENAME = "config.json"

[staticmethod]
def read_config():
    if not os.path.isfile(CONFIG_FILENAME):
        print(f"Please provide a {CONFIG_FILENAME} file.")
    else:
        with open(CONFIG_FILENAME, "r") as f:
            config = json.loads(f.read())
            return config
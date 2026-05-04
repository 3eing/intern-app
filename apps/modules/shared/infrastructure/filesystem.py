from pathlib import Path


def create_dir_if_dont_exist(dir_name):
    Path(dir_name).mkdir(parents=True, exist_ok=True)
    return Path(dir_name)
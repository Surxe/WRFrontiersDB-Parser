# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steam.depot_downloader import DepotDownloader
from utils import init_params, Params

def main(params=None):
    if params is None:
        raise ValueError("Params must be provided")
    
    DepotDownloader(
        output_dir=params.output_path,
        wrf_dir=params.steam_game_download_path,
        depot_downloader_cmd_path=params.depot_downloader_cmd_path,
        steam_username=params.steam_username,
        steam_password=params.steam_password,
        force=params.force_download,
    ).run(manifest_id=None) # get latest

if __name__ == "__main__":
    Params()
    params = init_params()
    main(params)
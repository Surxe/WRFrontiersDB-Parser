
import argparse
from dotenv import load_dotenv

# Parse command-line arguments for Params fields
parser = argparse.ArgumentParser(description="Run WRFrontiersDB Parser with optional overrides.")
parser.add_argument('--EXPORTS_PATH', type=str, help='Override EXPORTS_PATH')
parser.add_argument('--GAME_NAME', type=str, help='Override GAME_NAME')
parser.add_argument('--LOG_LEVEL', type=str, help='Override LOG_LEVEL')
parser.add_argument('--OUTPUT_PATH', type=str, help='Override OUTPUT_PATH')
args = parser.parse_args()

# Force reload .env file, overriding any existing environment variables
load_dotenv(override=True)

from utils import clear_dir, init_params

# Initialize parameters with command-line args
init_params(
    export_path=args.EXPORTS_PATH,
    game_name=args.GAME_NAME,
    log_level=args.LOG_LEVEL,
    output_path=args.OUTPUT_PATH
)

from parsers.module import *
from parsers.localization import *
from parsers.pilot import *
from parsers.progression_table import *
from parsers.game_mode import *
from parsers.bot_preset import *
from parsers.powerup import *
from analysis import *

clear_dir("output")  # Clear the data directory before parsing

parse_localizations()
parse_modules() #module relies on english localization being added to each key just as a helpful Ctrl+F reference
parse_pilots()  # Pilot parser relies on module data being parsed first
parse_progression_table()
parse_game_modes()
parse_bot_presets()
parse_powerups()
analyze(Module, ModuleStat)


ProgressionTable.to_file()
Currency.to_file()
ContentUnlock.to_file()
Decal.to_file()
CustomizationType.to_file()
CustomizationRarity.to_file()
Rarity.to_file()
GroupReward.to_file()
Material.to_file()
Weathering.to_file()
Skin.to_file()

Module.to_file()
ModuleRarity.to_file()
CharacterModule.to_file()
Ability.to_file()
Faction.to_file()
ModuleClass.to_file()
CharacterClass.to_file()
ModuleTag.to_file()
ModuleType.to_file()
ModuleCategory.to_file()
ModuleSocketType.to_file()
ModuleStat.to_file()
ModuleStatsTable.to_file()

Pilot.to_file()
PilotType.to_file()
PilotClass.to_file()
PilotPersonality.to_file()
PilotTalentType.to_file()
PilotTalent.to_file()

GameMode.to_file()
BotNames.to_file()
HonorReward.to_file()

BotPreset.to_file()
DropTeam.to_file()
CharacterPreset.to_file()

Powerup.to_file()

Localization.to_file()
Image.to_file()
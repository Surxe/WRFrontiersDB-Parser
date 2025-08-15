from dotenv import load_dotenv
# Force reload .env file, overriding any existing environment variables
load_dotenv(override=True)

from utils import clear_dir

# call other parsers
from parsers.module import *
from parsers.localization import *
from parsers.pilot import *
from parsers.progression_table import *
from parsers.game_mode import *

clear_dir("output")  # Clear the data directory before parsing

parse_localizations()
print()
parse_modules() #module relies on english localization being added to each key just as a helpful Ctrl+F reference
parse_pilots()  # Pilot parser relies on module data being parsed first
parse_progression_table()
parse_game_modes()

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
Image.to_file()

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

Localization.to_file()
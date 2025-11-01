# Can be run directly for convenience, but only offers env vars, and not arguments. For running just parse with args, use run.py with --should-parse

import sys
import os

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add current parse directory to path so parsers can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from utils import clear_dir
from options import OPTIONS

from parsers.module import *
from parsers.localization import *
from parsers.pilot import *
from parsers.progression_table import *
from parsers.game_mode import *
from parsers.bot_preset import *
from parsers.factory_preset import *
from parsers.powerup import *
from analysis import *

def main():
    """Main parsing function - uses global OPTIONS singleton."""
    clear_dir(OPTIONS.output_dir)  # Clear the data directory before parsing

    parse_localizations()
    parse_modules() #module relies on english localization being added to each key just as a helpful Ctrl+F reference
    parse_pilots()  # Pilot parser relies on module data being parsed first
    parse_progression_table()
    parse_game_modes()
    parse_bot_presets()
    parse_factory_presets()
    parse_powerups()
    analyze(Module, ModuleStat, UpgradeCost, ScrapReward, FactoryPreset, Ability)


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
    UpgradeCost.to_file()
    ScrapReward.to_file()

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
    League.to_file()

    FactoryPreset.to_file()

    Powerup.to_file()

    Localization.to_file()
    Image.to_file()
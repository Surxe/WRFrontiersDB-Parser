# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

class VirtualBot(ParseObject):
    objects = dict()

    def __init__(self, id: str, name: dict, character_type: str, core_modules: list, factory_presets: list, iconPath: str = None):
        self.id = id
        self.name = name
        self.character_type = character_type
        self.core_modules = core_modules
        self.factory_presets = factory_presets
        self.iconPath = iconPath
        
        self.objects[id] = self

    def _parse(self):
        # VirtualBot is a synthetic object, it doesn't parse from a single source asset.
        pass

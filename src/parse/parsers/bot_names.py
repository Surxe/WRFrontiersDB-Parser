# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

class BotNames(ParseObject):
    objects = dict()  # Dictionary to hold all ModuleStat instances
    
    def _parse(self):
        bot_names = self.source_data["Properties"]["BotNames"]

        """
        {
          "Key": "global", # or "ru", "fr", etc.
          "Value": {
            "BotNames": [
              {
                "Nickname": "Ben"
              },

        transform to

        {
        "global": [Ben, x, y]
        }
        """

        bot_names_by_lang = {}
        for table in bot_names:
            lang_code = table["Key"]
            bot_names_arr = []
            for bot_name in table["Value"]["BotNames"]:
                bot_names_arr.append(bot_name["Nickname"])
            bot_names_by_lang[lang_code] = bot_names_arr

        self.bot_names_by_lang = bot_names_by_lang
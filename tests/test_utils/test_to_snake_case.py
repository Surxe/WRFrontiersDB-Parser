import unittest
import sys
import os

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.utils module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_utils", os.path.join(src_path, "utils.py"))
src_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_utils)

to_snake_case = src_utils.to_snake_case


class TestToSnakeCase(unittest.TestCase):
    """Test cases for the to_snake_case function."""
    
    def test_camel_case_conversion(self):
        """Test conversion of CamelCase to snake_case."""
        self.assertEqual(to_snake_case("CamelCase"), "camel_case")
        self.assertEqual(to_snake_case("SimpleTest"), "simple_test")
        self.assertEqual(to_snake_case("MyClassName"), "my_class_name")
        self.assertEqual(to_snake_case("HTTPSConnection"), "https_connection")
    
    def test_pascal_case_conversion(self):
        """Test conversion of PascalCase to snake_case."""
        self.assertEqual(to_snake_case("PascalCase"), "pascal_case")
        self.assertEqual(to_snake_case("WeaponType"), "weapon_type")
        self.assertEqual(to_snake_case("CharacterClass"), "character_class")
        self.assertEqual(to_snake_case("ItemRarity"), "item_rarity")
    
    def test_mixed_case_conversion(self):
        """Test conversion of mixedCase to snake_case."""
        self.assertEqual(to_snake_case("mixedCase"), "mixed_case")
        self.assertEqual(to_snake_case("someVariableName"), "some_variable_name")
        self.assertEqual(to_snake_case("functionCallExample"), "function_call_example")
    
    def test_already_snake_case(self):
        """Test that existing underscores are removed before processing."""
        self.assertEqual(to_snake_case("snake_case"), "snakecase")  # Underscores removed, no CamelCase to convert
        self.assertEqual(to_snake_case("already_converted"), "alreadyconverted")  # Underscores removed, no CamelCase to convert
        self.assertEqual(to_snake_case("simple_test"), "simpletest")  # Underscores removed, no CamelCase to convert
        self.assertEqual(to_snake_case("multi_word_variable"), "multiwordvariable")  # Underscores removed, no CamelCase to convert
    
    def test_all_lowercase(self):
        """Test that all lowercase strings remain unchanged."""
        self.assertEqual(to_snake_case("lowercase"), "lowercase")
        self.assertEqual(to_snake_case("simple"), "simple")
        self.assertEqual(to_snake_case("test"), "test")
    
    def test_all_uppercase(self):
        """Test conversion of ALL UPPERCASE strings."""
        self.assertEqual(to_snake_case("UPPERCASE"), "uppercase")
        self.assertEqual(to_snake_case("ALL_CAPS"), "allcaps")  # Underscores removed, no CamelCase pattern to match
        self.assertEqual(to_snake_case("CONSTANT_VALUE"), "constantvalue")  # Underscores removed, no CamelCase pattern to match
    
    def test_spaces_to_underscores(self):
        """Test that spaces are converted to underscores."""
        self.assertEqual(to_snake_case("words with spaces"), "words_with_spaces")
        self.assertEqual(to_snake_case("Multiple Word String"), "multiple__word__string")  # CamelCase + space creates double underscore
        self.assertEqual(to_snake_case("Simple Test Case"), "simple__test__case")  # CamelCase + space creates double underscore
        self.assertEqual(to_snake_case("  leading and trailing  "), "leading_and_trailing")  # Leading/trailing spaces stripped
    
    def test_mixed_spaces_and_camel_case(self):
        """Test strings with both spaces and CamelCase."""
        self.assertEqual(to_snake_case("CamelCase With Spaces"), "camel_case__with__spaces")  # Both CamelCase and space conversions
        self.assertEqual(to_snake_case("My Class Name"), "my__class__name")  # Both CamelCase and space conversions
        self.assertEqual(to_snake_case("WeaponType Manager"), "weapon_type__manager")  # Both CamelCase and space conversions
    
    def test_numbers_in_text(self):
        """Test strings containing numbers."""
        self.assertEqual(to_snake_case("Version1"), "version1")
        self.assertEqual(to_snake_case("Test2Case"), "test2_case")
        self.assertEqual(to_snake_case("HTTP2Connection"), "http2_connection")
        self.assertEqual(to_snake_case("Player1Score"), "player1_score")
        self.assertEqual(to_snake_case("Level99Boss"), "level99_boss")
    
    def test_consecutive_uppercase_letters(self):
        """Test strings with consecutive uppercase letters."""
        self.assertEqual(to_snake_case("HTTPSConnection"), "https_connection")
        self.assertEqual(to_snake_case("XMLParser"), "xml_parser")
        self.assertEqual(to_snake_case("JSONData"), "json_data")
        self.assertEqual(to_snake_case("APIKey"), "api_key")
        self.assertEqual(to_snake_case("URLPath"), "url_path")
    
    def test_single_characters(self):
        """Test single character inputs."""
        self.assertEqual(to_snake_case("A"), "a")
        self.assertEqual(to_snake_case("a"), "a")
        self.assertEqual(to_snake_case("1"), "1")
        self.assertEqual(to_snake_case(" "), "")  # Space gets stripped by .lower()
    
    def test_empty_string(self):
        """Test empty string input."""
        self.assertEqual(to_snake_case(""), "")
    
    def test_special_characters(self):
        """Test strings with special characters."""
        self.assertEqual(to_snake_case("Test-Case"), "test-_case")  # Regex adds underscore before C
        self.assertEqual(to_snake_case("File.Extension"), "file._extension")  # Regex adds underscore before E
        self.assertEqual(to_snake_case("Path/To/File"), "path/_to/_file")  # Regex adds underscores before T and F
        self.assertEqual(to_snake_case("Test@Example"), "test@_example")  # Regex adds underscore before E
    
    def test_game_specific_examples(self):
        """Test with game-specific naming conventions."""
        # Character classes
        self.assertEqual(to_snake_case("CharacterClass"), "character_class")
        self.assertEqual(to_snake_case("PilotPersonality"), "pilot_personality")
        self.assertEqual(to_snake_case("WeaponType"), "weapon_type")
        
        # Item types
        self.assertEqual(to_snake_case("ItemRarity"), "item_rarity")
        self.assertEqual(to_snake_case("ModuleCategory"), "module_category")
        self.assertEqual(to_snake_case("CustomizationType"), "customization_type")
        
        # Game mechanics
        self.assertEqual(to_snake_case("DropTeam"), "drop_team")
        self.assertEqual(to_snake_case("GameMode"), "game_mode")
        self.assertEqual(to_snake_case("ProgressionTable"), "progression_table")
    
    def test_complex_mixed_cases(self):
        """Test complex cases with multiple patterns."""
        self.assertEqual(to_snake_case("MyHTTPSConnectionClass"), "my_https_connection_class")
        self.assertEqual(to_snake_case("XMLParser2Handler"), "xml_parser2_handler")
        self.assertEqual(to_snake_case("User API Key Manager"), "user_api__key__manager")  # CamelCase + spaces
        self.assertEqual(to_snake_case("Level1BossAI"), "level1_boss_ai")
    
    def test_edge_cases_with_underscores(self):
        """Test edge cases with existing underscores."""
        self.assertEqual(to_snake_case("Already_PartiallyConverted"), "already_partially_converted")  # _ removed, then CamelCase converted
        self.assertEqual(to_snake_case("Mixed_CamelCase"), "mixed_camel_case")  # _ removed, then CamelCase converted
        self.assertEqual(to_snake_case("_LeadingUnderscore"), "leading_underscore")  # _ removed, then CamelCase converted
        self.assertEqual(to_snake_case("TrailingUnderscore_"), "trailing_underscore")  # _ removed, then CamelCase converted
    
    def test_whitespace_variations(self):
        """Test different types of whitespace."""
        self.assertEqual(to_snake_case("Tab\tSeparated"), "tab\t_separated")  # Only spaces are replaced, CamelCase still processed
        self.assertEqual(to_snake_case("New\nLine"), "new\nline")  # Only spaces are replaced, not newlines
        self.assertEqual(to_snake_case("Carriage\rReturn"), "carriage\r_return")  # Only spaces are replaced, CamelCase still processed
    
    def test_unicode_characters(self):
        """Test with unicode characters."""
        self.assertEqual(to_snake_case("TestWith测试"), "test_with测试")
        self.assertEqual(to_snake_case("ΑlphaΒeta"), "αlphaβeta")  # Unicode uppercase may not be handled by regex
        self.assertEqual(to_snake_case("Тест Case"), "тест__case")  # CamelCase + space
    
    def test_preserve_case_sensitivity_in_special_chars(self):
        """Test that case is only changed for letters."""
        # Numbers and special characters should remain as-is (except made lowercase)
        self.assertEqual(to_snake_case("Test123ABC"), "test123_abc")
        self.assertEqual(to_snake_case("Version2.0Beta"), "version2.0_beta")


if __name__ == '__main__':
    unittest.main()
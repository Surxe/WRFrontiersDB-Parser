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

parse_colon_colon = src_utils.parse_colon_colon


class TestParseColonColon(unittest.TestCase):
    """Test cases for the parse_colon_colon function."""
    
    def test_basic_enum_parsing(self):
        """Test basic enum-style parsing with double colons."""
        # Example from the function comment
        self.assertEqual(parse_colon_colon("ESWeaponReloadType::X"), "X")
        
        # Other basic enum examples
        self.assertEqual(parse_colon_colon("EItemType::Weapon"), "Weapon")
        self.assertEqual(parse_colon_colon("ECharacterClass::Fighter"), "Fighter")
        self.assertEqual(parse_colon_colon("EGameMode::PvP"), "PvP")
    
    def test_multiple_double_colons_raise_error(self):
        """Test strings with multiple :: separators - should raise ValueError."""
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("Namespace::SubNamespace::EnumType::Value")
        self.assertIn("contains more than one '::'", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("A::B::C::D::E")
        self.assertIn("contains more than one '::'", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("Game::Data::Items::Weapons::Sword")
        self.assertIn("contains more than one '::'", str(context.exception))
    
    def test_no_double_colons_raise_error(self):
        """Test strings without :: - should raise ValueError."""
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("SimpleValue")
        self.assertIn("does not contain '::' to split", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("NoColons")
        self.assertIn("does not contain '::' to split", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("123")
        self.assertIn("does not contain '::' to split", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("")
        self.assertIn("does not contain '::' to split", str(context.exception))
    
    def test_single_colons_raise_error(self):
        """Test that single colons raise errors - only exactly one :: is allowed."""
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("Path:With:Single:Colons")
        self.assertIn("does not contain '::' to split", str(context.exception))
        
        # Mixed single and double colons - has more than one ::
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("Mixed:Single::Double::More")
        self.assertIn("contains more than one '::'", str(context.exception))
        
        # Valid case - exactly one ::
        self.assertEqual(parse_colon_colon("Type:Name::Value"), "Value")
    
    def test_empty_segments_with_one_separator(self):
        """Test strings with empty segments around exactly one ::."""
        # These have more than one :: separator due to empty segments creating multiple splits
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("Type::::Value")  # This creates ["Type", "", "", "Value"] - 4 parts
        self.assertIn("contains more than one '::'", str(context.exception))
        
        # Valid cases with exactly one ::
        self.assertEqual(parse_colon_colon("::Value"), "Value")
        self.assertEqual(parse_colon_colon("Type::"), "")
        
        # This has multiple :: separators
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("::::") 
        self.assertIn("contains more than one '::'", str(context.exception))
    
    def test_whitespace_in_values(self):
        """Test values with whitespace."""
        self.assertEqual(parse_colon_colon("Type::Value With Spaces"), "Value With Spaces")
        self.assertEqual(parse_colon_colon("EType:: Value "), " Value ")
        self.assertEqual(parse_colon_colon("Namespace::	TabValue"), "	TabValue")
    
    def test_special_characters(self):
        """Test values with special characters."""
        self.assertEqual(parse_colon_colon("Type::Value_123"), "Value_123")
        self.assertEqual(parse_colon_colon("EType::Value-With-Dashes"), "Value-With-Dashes")
        self.assertEqual(parse_colon_colon("Category::@#$%"), "@#$%")
        self.assertEqual(parse_colon_colon("Type::Value.Extension"), "Value.Extension")
    
    def test_numeric_values(self):
        """Test numeric values after ::."""
        self.assertEqual(parse_colon_colon("ELevel::1"), "1")
        self.assertEqual(parse_colon_colon("Type::42"), "42")
        self.assertEqual(parse_colon_colon("Version::1.0.0"), "1.0.0")
        self.assertEqual(parse_colon_colon("Counter::-5"), "-5")
    
    def test_game_specific_examples(self):
        """Test with game-specific enum examples."""
        # Weapon-related enums
        self.assertEqual(parse_colon_colon("ESWeaponReloadType::Automatic"), "Automatic")
        self.assertEqual(parse_colon_colon("ESWeaponReloadType::Manual"), "Manual")
        
        # Character-related enums
        self.assertEqual(parse_colon_colon("ECharacterClass::Barbarian"), "Barbarian")
        self.assertEqual(parse_colon_colon("ECharacterClass::Wizard"), "Wizard")
        self.assertEqual(parse_colon_colon("ECharacterClass::Rogue"), "Rogue")
        
        # Item-related enums
        self.assertEqual(parse_colon_colon("EItemRarity::Common"), "Common")
        self.assertEqual(parse_colon_colon("EItemRarity::Legendary"), "Legendary")
        
        # Game state enums
        self.assertEqual(parse_colon_colon("EGameState::InLobby"), "InLobby")
        self.assertEqual(parse_colon_colon("EGameState::InGame"), "InGame")
    
    def test_case_sensitivity(self):
        """Test that the function preserves case."""
        self.assertEqual(parse_colon_colon("type::value"), "value")
        self.assertEqual(parse_colon_colon("TYPE::VALUE"), "VALUE")
        self.assertEqual(parse_colon_colon("Type::MixedCase"), "MixedCase")
        self.assertEqual(parse_colon_colon("ESomeType::camelCase"), "camelCase")
    
    def test_unicode_characters(self):
        """Test with unicode characters."""
        self.assertEqual(parse_colon_colon("Type::测试"), "测试")
        self.assertEqual(parse_colon_colon("Тип::Значение"), "Значение")
        self.assertEqual(parse_colon_colon("Type::αβγ"), "αβγ")
    
    def test_very_long_strings(self):
        """Test with very long strings."""
        # Long namespace with multiple :: would raise error
        long_namespace = "::".join(["Level"] * 100)
        long_string = f"{long_namespace}::FinalValue"
        with self.assertRaises(ValueError) as context:
            parse_colon_colon(long_string)
        self.assertIn("contains more than one '::'", str(context.exception))
        
        # Very long final value with exactly one ::
        long_value = "A" * 1000
        self.assertEqual(parse_colon_colon(f"Type::{long_value}"), long_value)
    
    def test_edge_cases_with_strict_validation(self):
        """Test edge cases with the strict validation."""
        # Just double colons - exactly one ::
        self.assertEqual(parse_colon_colon("::"), "")
        
        # Multiple consecutive double colons - should raise error
        with self.assertRaises(ValueError) as context:
            parse_colon_colon("Type::::::::Value")
        self.assertIn("contains more than one '::'", str(context.exception))


if __name__ == '__main__':
    unittest.main()
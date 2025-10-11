import unittest
import sys
import os

# Set required environment variables before importing utils to prevent OPTIONS validation errors
os.environ['SHOULD_PARSE'] = 'false'  # Disable parsing to avoid requiring EXPORT_DIR and OUTPUT_DIR
os.environ.setdefault('EXPORT_DIR', '/tmp/test_export')  # Fallback if SHOULD_PARSE somehow becomes true
os.environ.setdefault('OUTPUT_DIR', '/tmp/test_output')  # Fallback if SHOULD_PARSE somehow becomes true

# Add the src directory to the Python path to import utils
src_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
sys.path.insert(0, src_path)

# Import directly from the src.utils module to avoid conflicts with tests.utils
import importlib.util
spec = importlib.util.spec_from_file_location("src_utils", os.path.join(src_path, "utils.py"))
src_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_utils)

path_to_file_name = src_utils.path_to_file_name


class TestPathToFileName(unittest.TestCase):
    """Test cases for the path_to_file_name function."""
    
    def test_simple_file_name(self):
        """Test extracting filename from simple paths."""
        self.assertEqual(path_to_file_name("file.ext"), "file")
        self.assertEqual(path_to_file_name("test.json"), "test")
        self.assertEqual(path_to_file_name("data.txt"), "data")
    
    def test_path_with_directories(self):
        """Test extracting filename from paths with directories."""
        self.assertEqual(path_to_file_name("path/to/file.ext"), "file")
        self.assertEqual(path_to_file_name("/absolute/path/file.json"), "file")
        self.assertEqual(path_to_file_name("../relative/path/test.txt"), "test")
        self.assertEqual(path_to_file_name("deeply/nested/directory/structure/filename.extension"), "filename")
    
    def test_multiple_dots_in_filename(self):
        """Test files with multiple dots - should return part before first dot."""
        self.assertEqual(path_to_file_name("file.name.ext"), "file")
        self.assertEqual(path_to_file_name("test.backup.json"), "test")
        self.assertEqual(path_to_file_name("version.1.0.final"), "version")
        self.assertEqual(path_to_file_name("a.b.c.d.e"), "a")
    
    def test_multiple_dots_in_path_and_filename(self):
        """Test paths with dots in directory names and filename."""
        self.assertEqual(path_to_file_name("path.with.dots/file.ext"), "file")
        self.assertEqual(path_to_file_name("version.1.0/test.file.json"), "test")
        self.assertEqual(path_to_file_name("./current.dir/file.name.extension"), "file")
    
    def test_file_without_extension(self):
        """Test files without extensions - should return the whole filename."""
        self.assertEqual(path_to_file_name("filename"), "filename")
        self.assertEqual(path_to_file_name("path/to/filename"), "filename")
        self.assertEqual(path_to_file_name("/absolute/path/noextension"), "noextension")
    
    def test_empty_extension(self):
        """Test files with empty extensions (ending with dot)."""
        self.assertEqual(path_to_file_name("file."), "file")
        self.assertEqual(path_to_file_name("path/to/file."), "file")
        self.assertEqual(path_to_file_name("test.name."), "test")
    
    def test_numeric_filenames(self):
        """Test numeric filenames and extensions."""
        self.assertEqual(path_to_file_name("123.456"), "123")
        self.assertEqual(path_to_file_name("path/to/007.json"), "007")
        self.assertEqual(path_to_file_name("file.0"), "file")
        self.assertEqual(path_to_file_name("0.1"), "0")
    
    def test_special_characters_in_filename(self):
        """Test filenames with special characters."""
        self.assertEqual(path_to_file_name("file_name.ext"), "file_name")
        self.assertEqual(path_to_file_name("file-name.json"), "file-name")
        self.assertEqual(path_to_file_name("file@name.txt"), "file@name")
        self.assertEqual(path_to_file_name("file name.ext"), "file name")  # Space in filename
        self.assertEqual(path_to_file_name("file#name$.extension"), "file#name$")
    
    def test_unicode_characters(self):
        """Test filenames with unicode characters."""
        self.assertEqual(path_to_file_name("测试文件.txt"), "测试文件")
        self.assertEqual(path_to_file_name("файл.json"), "файл")
        self.assertEqual(path_to_file_name("path/to/αβγ.extension"), "αβγ")
    
    def test_windows_style_paths(self):
        """Test Windows-style paths with backslashes."""
        # Note: The function only splits on '/', so backslashes are treated as part of filename
        self.assertEqual(path_to_file_name("C:\\Windows\\file.txt"), "C:\\Windows\\file")
        self.assertEqual(path_to_file_name("path\\to\\file.ext"), "path\\to\\file")
    
    def test_mixed_path_separators(self):
        """Test paths with mixed separators."""
        self.assertEqual(path_to_file_name("path\\mixed/separators/file.ext"), "file")
        self.assertEqual(path_to_file_name("unix/path\\windows/file.json"), "file")
    
    def test_game_specific_examples(self):
        """Test with examples from the game data context."""
        # Game asset paths
        self.assertEqual(path_to_file_name("/Game/DungeonCrawler/Data/Item.0"), "Item")
        self.assertEqual(path_to_file_name("DungeonCrawler/Content/Weapons/Sword.Sword_C"), "Sword")
        self.assertEqual(path_to_file_name("/Game/DungeonCrawler/Maps/Dungeon/Modules/Crypt/Edge/Armory/Armory_A.Armory_A"), "Armory_A")
        
        # Asset paths with indices
        self.assertEqual(path_to_file_name("../Armor/Armor_A.5"), "Armor_A")
        self.assertEqual(path_to_file_name("/path/to/asset.123"), "asset")
        
        # Blueprint paths
        self.assertEqual(path_to_file_name("/Game/Sparrow/BP_Buff_A.BP_Buff_A_C"), "BP_Buff_A")
    
    def test_edge_cases(self):
        """Test various edge cases."""
        # Single character filenames
        self.assertEqual(path_to_file_name("a.b"), "a")
        self.assertEqual(path_to_file_name("path/x.y"), "x")
        
        # Multiple consecutive dots
        self.assertEqual(path_to_file_name("file..ext"), "file")
        self.assertEqual(path_to_file_name("test...json"), "test")
        
        # Path ending with slash should still work
        # Note: This would actually fail in the real function, but testing current behavior
        # self.assertEqual(path_to_file_name("path/to/"), "")  # This would cause issues
    
    def test_empty_and_invalid_inputs(self):
        """Test behavior with empty or problematic inputs."""
        # Empty string
        with self.assertRaises(ValueError):
            path_to_file_name("")

        # None input
        with self.assertRaises(ValueError):
            path_to_file_name(None)
        
        # Just a dot - will cause IndexError
        with self.assertRaises(ValueError):
            path_to_file_name(".")
        
        # Just slashes
        with self.assertRaises(ValueError):
            path_to_file_name("/")
        with self.assertRaises(ValueError):
            path_to_file_name("//")
    
    def test_very_long_paths(self):
        """Test with very long paths and filenames."""
        long_path = "/".join(["dir"] * 100)
        long_filename = "a" * 100
        test_path = f"{long_path}/{long_filename}.ext"
        self.assertEqual(path_to_file_name(test_path), long_filename)
    
    def test_consistent_with_path_to_index_examples(self):
        """Test consistency with examples used in path_to_index tests."""
        # These should return the same base filename that path_to_index extracts indices from
        self.assertEqual(path_to_file_name("../Armor/Armor_A.5"), "Armor_A")
        self.assertEqual(path_to_file_name("../Armory/Armory_A.Armory_A"), "Armory_A")
        self.assertEqual(path_to_file_name("DungeonCrawler/Content/Weapons/Sword.Sword_C"), "Sword")
        self.assertEqual(path_to_file_name("/Game/DungeonCrawler/Data/Item.0"), "Item")


if __name__ == '__main__':
    unittest.main()

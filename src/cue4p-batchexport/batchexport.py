# Add two levels of parent dirs to sys path
import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import init_params, Params, run_process
from loguru import logger


class BatchExporter:
    """
    A class to handle batch exporting of game assets using the CUE4P BatchExport tool.
    
    This class manages the execution of BatchExport.exe with the appropriate parameters
    for extracting War Robots Frontiers game data from .pak files to JSON format.
    """
    
    def __init__(self, params=None, mapping_file_path=None):
        """
        Initialize the BatchExporter.
        
        Args:
            params (Params, optional): Params object containing configuration. If None, will create default.
            mapping_file_path (str): Path to the mapping file for UE4 assets (required)
        """
        if params is None:
            params = init_params()
        
        if mapping_file_path is None:
            raise ValueError("mapping_file_path is required for BatchExporter")
        
        self.params = params
        self.mapping_file_path = mapping_file_path
        
        # Path to BatchExport executable
        self.batch_export_dir = Path(__file__).parent / "BatchExport"
        self.executable_path = self.batch_export_dir / "BatchExport.exe"
        
        # Build the command once during initialization
        self.command = [
            str(self.executable_path),
            "--preset", "WarRobotsFrontiers",
            "--pak-files-directory", self.params.steam_game_download_path,
            "--export-output-path", self.params.export_path,
            "--mapping-file-path", self.mapping_file_path
        ]
        
        # Validate paths
        self._validate_setup()
    
    def _validate_setup(self):
        """Validate that all required paths and files exist."""
        if not self.executable_path.exists():
            raise FileNotFoundError(
                f"BatchExport.exe not found at {self.executable_path}. "
                "Please run install_batch_export.sh first to download it."
            )
        
        if not os.path.exists(self.params.steam_game_download_path):
            raise FileNotFoundError(
                f"Steam game download path not found: {self.params.steam_game_download_path}. "
                "Please ensure STEAM_GAME_DOWNLOAD_PATH is set correctly in your environment."
            )
        
        if not os.path.exists(self.params.export_path):
            raise FileNotFoundError(
                f"Export path not found: {self.params.export_path}. "
                "Please ensure EXPORTS_PATH is set correctly in your environment."
            )
        
        if not os.path.exists(self.mapping_file_path):
            raise FileNotFoundError(
                f"Mapping file not found: {self.mapping_file_path}. "
                "Please provide a valid mapping file path."
            )
    
    def run(self):
        """
        Execute BatchExport with the configured parameters.
        
        Returns:
            None: The process completes successfully or raises an exception
            
        Raises:
            RuntimeError: If BatchExport execution fails
        """
        logger.info("Starting BatchExport process...")
        logger.info(f"Using mapping file: {self.mapping_file_path}")
        logger.info(f"Executing BatchExport with command: {str(self)}")
        logger.info(f"PAK files directory: {self.params.steam_game_download_path}")
        logger.info(f"Export output path: {self.params.export_path}")
        
        try:
            # Execute BatchExport using run_process from utils
            # run_process handles logging, timeouts, and error handling internally
            run_process(
                params=self.command,
                name="BatchExport",
                timeout=3600  # 1 hour timeout
            )
            
            logger.success("BatchExport completed successfully!")
            
        except Exception as e:
            error_msg = f"BatchExport execution failed: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def __str__(self):
        """Return the command that would be executed as a string."""
        return ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in self.command)


def main(params=None, mapping_file_path=None):
    """
    Main function to run BatchExport with the given parameters.
    
    Args:
        params (Params, optional): Configuration parameters
        mapping_file_path (str): Path to the mapping file (required)
    """
    if params is None:
        raise ValueError("Params must be provided")
    
    if mapping_file_path is None:
        raise ValueError("mapping_file_path must be provided")
    
    try:
        batch_exporter = BatchExporter(params, mapping_file_path)
        
        # Show command preview
        logger.info(f"Command to execute: {str(batch_exporter)}")
        
        # Run BatchExport
        batch_exporter.run()
        
        logger.success("BatchExport process completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"BatchExport failed: {e}")
        raise


if __name__ == "__main__":
    # Example usage
    params = Params()
    
    # Set the mapping file path (required)
    mapping_file = r"C:\path\to\your\mapping\file.usmap"  # Update this path
    
    if mapping_file == r"C:\path\to\your\mapping\file.usmap":
        raise ValueError("Please set the actual mapping file path before running")
    
    main(params, mapping_file)

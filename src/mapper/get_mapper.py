# Add two levels of parent dirs to sys path
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import init_params, Params, clear_dir, run_process, wait_for_process_ready_for_injection, terminate_process_by_name, terminate_process_object, is_admin
from loguru import logger

def main(params=None):
    if params is None:
        raise ValueError("Params must be provided")

    game_process_name = os.path.basename(params.shipping_cmd_path)
    launch_game_params = [
        params.shipping_cmd_path,
    ]

    logger.info(f"Clearing Dumper-7 output directory: {params.dumper7_output_path}")
    clear_dir(params.dumper7_output_path)  # Clear Dumper-7 output directory before starting the game to ensure only new dumps are present

    # Launch the game normally (with window/UI) but don't wait for it to complete
    logger.info("Starting game process with UI...")

    # Check if running as administrator (required for DLL injection)
    if not is_admin():
        logger.warning("Not running as administrator - DLL injection could fail but historically can succeed anyway.")
    else:
        logger.info("Running with administrator privileges")

    # Verify DLL file exists before bothering launching the game
    dll_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mapper', 'Dumper-7.dll')
    if not os.path.exists(dll_path):
        raise Exception(f"DLL file not found: {dll_path}")
    logger.info(f"DLL file confirmed: {dll_path}")
    
    # Use subprocess.Popen directly to start game with normal window behavior
    import subprocess
    game_process = subprocess.Popen(launch_game_params)
    logger.info(f"Game process started with PID: {game_process.pid}")

    def get_mapper_from_sdk():
        # If more than 1 dir (name does not matter) exists in the Dumper-7 output path, throw an error
        sdk_dirs = [d for d in os.listdir(params.dumper7_output_path) if os.path.isdir(os.path.join(params.dumper7_output_path, d))]
        if len(sdk_dirs) != 1:
            logger.error(f"Expected exactly one directory in Dumper-7 output path, found {len(sdk_dirs)}: {sdk_dirs}")
            raise e
        
        # If exactly one dir, check if the Mappings dir exists within it
        mapper_dir = os.path.join(params.dumper7_output_path, sdk_dirs[0], 'Mappings')
        if not os.path.exists(mapper_dir):
            logger.error(f"Mappings directory not found in Dumper-7 output: {mapper_dir}")
            raise e
        
        logger.info(f"SDK creation appears to have succeeded - found Mappings directory: {mapper_dir}")
        
        # If mappings dir exists, get the file names
        mapper_files = [f for f in os.listdir(mapper_dir) if os.path.isfile(os.path.join(mapper_dir, f))]
        if len(mapper_files) == 0:
            logger.error(f"No mapper files found in Mappings directory: {mapper_dir}")
            raise e
        elif len(mapper_files) > 1:
            logger.error(f"Multiple mapper files found in Mappings directory, expected only one: {mapper_files}")
            raise e
        mapper_file_path = os.path.join(mapper_dir, mapper_files[0])

        if not os.path.exists(mapper_file_path):
            logger.error(f"Mapper file not found at expected location: {mapper_file_path}")
            raise e

        logger.info(f"Mapper file successfully created: {mapper_file_path}")

        return mapper_file_path
    
    def terminate():
        # sleep for 5 seconds
        logger.info("Waiting 5 seconds before terminating game process just in case the dll did inject and just needs time to process...")
        time.sleep(5)

        # Always try to terminate the game when done
        logger.info("Terminating game process...")
        
        # First try terminating the subprocess object
        if not terminate_process_object(game_process, 'launch-game'):
            # If that fails, try terminating by process name
            terminate_process_by_name(game_process_name)
    has_terminated = False
    mapping_file_path = None
    
    try:
        # Check if the process started successfully
        time.sleep(2)  # Give it a moment to start
        if game_process.poll() is not None:
            raise Exception(f"Game process failed to start (exit code: {game_process.returncode})")
        
        # Wait for the game to be ready for injection
        logger.info("Waiting for game to be ready for DLL injection...")
        wait_for_process_ready_for_injection(game_process_name, initialization_time=20)  # 3 minutes total timeout
        
        logger.info("Game is ready, starting SDK creation process via DLL injection...")
        
        create_sdk_params = [
            params.dll_injector_cmd_path,
            '--process-name', game_process_name,
            '--inject', dll_path
        ]
        
        # Run the sdk creation process - this will block until completion
        run_process(create_sdk_params, name='create-sdk')

        logger.info("SDK creation process completed successfully!")

    # If the error message contains "Call to LoadLibraryW in remote process failed", it may have actually worked # This actually happens every time for me, but I don't know why.
    except Exception as e:
        terminate()
        has_terminated = True

        logger.error("DLL injection says it failed, but it could be incorrect. Checking if the mapping file was created...")
        mapping_file_path = get_mapper_from_sdk()
        if mapping_file_path is None:
            logger.error("DLL injection failed and mapping file was not created. Cannot continue.")
            raise e
        
    if not has_terminated:
        terminate()

    if mapping_file_path is None:
        # If we didn't already get the mapper file path from the exception handler, try to get it now 
        mapping_file_path = get_mapper_from_sdk()




if __name__ == '__main__':
    Params()
    params = init_params()
    main(params)
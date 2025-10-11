import sys
import os
import stat
import shutil
import subprocess
import tempfile
from pathlib import Path

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from options import init_options
from loguru import logger

# Force reload .env file, overriding any existing environment variables
load_dotenv(override=True)


def run_git_command(cmd, cwd=None, capture_output=True, check=True, log_output=False):
    """
    Run a git command with proper error handling and logging.
    
    Args:
        cmd: List of command arguments or string command
        cwd: Working directory for the command
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit
        log_output: Whether to log command output (respects LOG_LEVEL)
    
    Returns:
        CompletedProcess result
    """
    if isinstance(cmd, str):
        cmd = cmd.split()
    
    # Set Git environment variables to avoid config issues on Windows
    env = os.environ.copy()
    env.update({
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_CONFIG_GLOBAL': '/dev/null',
        'HOME': env.get('USERPROFILE', env.get('HOME', ''))
    })
    
    logger.debug(f"Running git command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=capture_output,
            text=True,
            encoding='utf-8',
            errors='ignore',  # Ignore problematic unicode characters instead of failing
            check=check
        )
        
        if log_output and result.stdout:
            logger.info(result.stdout.strip())
        
        return result
        
    except subprocess.CalledProcessError as e:
        # If ''nothing to commit' is in the error, make it a warning instead of error
        if "nothing to commit" in e.stdout:
            logger.warning("No changes to commit.")
            return e  # Return the exception object for further handling if needed
        logger.error(f"Git command failed: {' '.join(cmd)}")
        if e.stdout:
            logger.error(f"STDOUT: {e.stdout}")
        if e.stderr:
            logger.error(f"STDERR: {e.stderr}")
        raise


def remove_readonly(func, path, _):
    """Error handler for Windows read-only files during rmtree."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clone_data_repo(data_repo_url, data_repo_dir):
    """
    Clone or re-clone the data repository to ensure clean state.
    
    Args:
        data_repo_url: URL of the data repository
        data_repo_dir: Local directory path for the repository
    """
    if os.path.exists(data_repo_dir):
        logger.debug("Repository already exists, deleting...")
        # Use error handler to deal with Windows read-only files
        shutil.rmtree(data_repo_dir, onerror=remove_readonly)
    
    logger.info("Cloning WRFrontiersDB-Data...")
    run_git_command(
        ['git', 'clone', data_repo_url, data_repo_dir],
        log_output=True  # Always log git clone output for important operations
    )


def configure_git_repo(repo_dir):
    """
    Configure Git settings for the cloned repository.
    
    Args:
        repo_dir: Path to the repository directory
    """
    logger.debug("Configuring Git settings...")
    
    commands = [
        ['git', 'config', '--local', 'user.email', 'parser@example.com'],
        ['git', 'config', '--local', 'user.name', 'Parser'],
        ['git', 'config', '--local', 'credential.helper', '']
    ]
    
    for cmd in commands:
        run_git_command(cmd, cwd=repo_dir, log_output=False)


def switch_to_target_branch(repo_dir, target_branch):
    """
    Switch to the target branch, creating it if it doesn't exist.
    
    Args:
        repo_dir: Path to the repository directory
        target_branch: Name of the target branch
    """
    logger.info(f"Switching to branch: {target_branch}")
    
    try:
        # Try to checkout existing branch first
        run_git_command(['git', 'checkout', target_branch], cwd=repo_dir, log_output=False)
    except subprocess.CalledProcessError:
        # Branch doesn't exist, create it
        logger.debug(f"Branch {target_branch} doesn't exist, creating it...")
        run_git_command(['git', 'checkout', '-b', target_branch], cwd=repo_dir, log_output=False)


def get_latest_commit_info():
    """
    Get the latest commit title and date from the current repository.
    
    Returns:
        String with commit message and date
    """
    try:
        result = run_git_command(
            ['git', 'log', '-1', '--format=%s - %ad', '--date=short'],
            capture_output=True,
            log_output=False
        )
        latest_commit = result.stdout.strip()
        logger.info(f"Latest commit: {latest_commit}")
        return latest_commit
    except subprocess.CalledProcessError:
        logger.warning("Could not get latest commit info")
        return "Unknown commit"


def get_current_version(repo_dir):
    """
    Get the current game version from version.txt file.
    
    Args:
        repo_dir: Path to the repository directory
        
    Returns:
        String with current version or None if not found
    """
    version_file = os.path.join(repo_dir, 'current', 'version.txt')
    
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            current_version = f.read().strip()
        logger.debug(f"Will archive version {current_version} from current/version.txt")
        return current_version
    else:
        logger.debug("No current/version.txt found, will not archive any data.")
        return None


def update_current_data(repo_dir, output_dir, new_game_version, latest_commit):
    """
    Update the current data with new parsed output.
    
    Args:
        repo_dir: Path to the data repository directory
        output_dir: Path to the output directory with new data
        new_game_version: Version string for the new data
        latest_commit: Latest commit info for commit message
    """
    current_path = os.path.join(repo_dir, 'current')
    
    # Clear existing current data
    if os.path.exists(current_path):
        logger.debug("Deleting old current data...")
        for item in os.listdir(current_path):
            item_path = os.path.join(current_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    else:
        logger.debug("No current directory found, creating it...")
        os.makedirs(current_path)
    
    logger.info("Copying new output to current/...")
    
    # Copy all files from output directory to current directory
    if os.path.exists(output_dir):
        for item in os.listdir(output_dir):
            src = os.path.join(output_dir, item)
            dst = os.path.join(current_path, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
    else:
        raise ValueError(f"Output directory {output_dir} does not exist")
    
    # Write version file
    version_file = os.path.join(current_path, 'version.txt')
    with open(version_file, 'w') as f:
        f.write(new_game_version)
    
    # Commit the changes
    commit_message = f"Update current data to version:{new_game_version} from latest Parser commit:{latest_commit}"
    
    run_git_command(['git', 'add', '.'], cwd=repo_dir, log_output=False)
    
    # Try to commit, but don't fail if there's nothing to commit
    try:
        run_git_command(['git', 'commit', '-m', commit_message], cwd=repo_dir, 
                       log_output=True)
        logger.info(f"Updated current data to version {new_game_version} and committed changes.")
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in e.stdout:
            logger.info(f"No changes detected - current data is already version {new_game_version}.")
        else:
            raise  # Re-raise if it's a different error


def archive_old_data(repo_dir, game_version_to_archive, new_game_version):
    """
    Archive the previous version's data if different from new version.
    
    Args:
        repo_dir: Path to the data repository directory
        game_version_to_archive: Version to archive
        new_game_version: New version being deployed
    """
    if not game_version_to_archive or game_version_to_archive == new_game_version:
        logger.debug(f"Skipping archive - versions are the same: {game_version_to_archive}")
        return
    
    archive_path = os.path.join(repo_dir, 'archive', game_version_to_archive)
    logger.info(f"Archiving previous data to {archive_path}...")
    
    os.makedirs(archive_path, exist_ok=True)
    
    # Create temporary directory to extract old data from git
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Try to extract the old data from the previous commit
            result = run_git_command(
                ['git', 'show', 'HEAD~1:current/'],
                cwd=repo_dir,
                capture_output=True,
                check=False
            )
            
            if result.returncode == 0:
                # Extract files from previous commit using git archive
                run_git_command(
                    ['git', 'archive', 'HEAD~1', 'current/'],
                    cwd=repo_dir,
                    capture_output=True,
                    check=False
                )
                
                # Use git show to extract individual files
                try:
                    # Get list of files from previous commit's current directory
                    file_list_result = run_git_command(
                        ['git', 'ls-tree', '-r', '--name-only', 'HEAD~1', 'current/'],
                        cwd=repo_dir,
                        capture_output=True,
                        check=False
                    )
                    
                    if file_list_result.returncode == 0 and file_list_result.stdout.strip():
                        files = file_list_result.stdout.strip().split('\n')
                        
                        for file_path in files:
                            if file_path.startswith('current/'):
                                # Remove 'current/' prefix for destination
                                relative_path = file_path[8:]  # len('current/') = 8
                                dest_file = os.path.join(archive_path, relative_path)
                                
                                # Create destination directory if needed
                                dest_dir = os.path.dirname(dest_file)
                                if dest_dir:
                                    os.makedirs(dest_dir, exist_ok=True)
                                
                                # Extract file content from git
                                file_content_result = run_git_command(
                                    ['git', 'show', f'HEAD~1:{file_path}'],
                                    cwd=repo_dir,
                                    capture_output=True,
                                    check=False
                                )
                                
                                if file_content_result.returncode == 0:
                                    with open(dest_file, 'w', encoding='utf-8') as f:
                                        f.write(file_content_result.stdout)
                        
                        # Check if we successfully archived any files
                        if os.listdir(archive_path):
                            # Commit the archival changes
                            commit_message = f"Archive version:{game_version_to_archive} data"
                            
                            run_git_command(['git', 'add', '.'], cwd=repo_dir, log_output=False)
                            run_git_command(['git', 'commit', '-m', commit_message], cwd=repo_dir,
                                           log_output=True)
                            
                            logger.info(f"Archived version {game_version_to_archive} and committed changes.")
                        else:
                            logger.debug("No files were successfully archived.")
                    else:
                        logger.debug("No previous current data found in git history.")
                        
                except subprocess.CalledProcessError:
                    logger.debug("Could not extract file list from previous commit.")
            else:
                logger.debug("No previous current data found to archive.")
                
        except Exception as e:
            logger.warning(f"Error during archival process: {e}")


def push_changes(repo_dir, target_branch):
    """
    Push all commits to the remote repository.
    
    Args:
        repo_dir: Path to the repository directory
        target_branch: Branch to push to
    """
    logger.info(f"Pushing changes to branch '{target_branch}'...")
    
    run_git_command(['git', 'push', 'origin', target_branch], cwd=repo_dir,
                   log_output=True)
    
    logger.info(f"All changes committed and pushed successfully to branch '{target_branch}'.")


def main():
    """Main function that orchestrates the data pushing process."""
    # Validate required options
    if not OPTIONS.game_version:
        raise ValueError("GAME_VERSION is required for pushing data")
    
    if not OPTIONS.gh_data_repo_pat:
        raise ValueError("GH_DATA_REPO_PAT is required for pushing data")
    
    # Validate target branch
    valid_branches = ['testing-grounds', 'main']
    if OPTIONS.target_branch not in valid_branches:
        raise ValueError(f"Invalid branch '{OPTIONS.target_branch}'. Only {valid_branches} are allowed.")
    
    # Configuration
    data_repo_url = f"https://{OPTIONS.gh_data_repo_pat}@github.com/Surxe/WRFrontiersDB-Data.git"
    data_repo_dir = "WRFrontiersDB-Data"
    output_dir = OPTIONS.output_dir or "output"
    
    logger.info(f"Using game version: {OPTIONS.game_version}")
    logger.info(f"Using branch: {OPTIONS.target_branch}")
    logger.info(f"Using output directory: {output_dir}")
    
    try:
        # Clone or refresh data repository
        clone_data_repo(data_repo_url, data_repo_dir)
        
        # Configure Git settings
        configure_git_repo(data_repo_dir)
        
        # Switch to target branch
        switch_to_target_branch(data_repo_dir, OPTIONS.target_branch)
        
        # Get latest commit info from parser repo
        latest_commit = get_latest_commit_info()
        
        # Get current version for archival
        current_version = get_current_version(data_repo_dir)
        
        # Update current data with new output
        update_current_data(data_repo_dir, output_dir, OPTIONS.game_version, latest_commit)
        
        # Archive old data if version changed
        archive_old_data(data_repo_dir, current_version, OPTIONS.game_version)
        
        # Push all changes
        push_changes(data_repo_dir, OPTIONS.target_branch)
        
    except Exception as e:
        logger.error(f"Error during push process: {e}")
        raise
    finally:
        # Cleanup - remove cloned repository
        if os.path.exists(data_repo_dir):
            logger.debug(f"Cleaning up {data_repo_dir}...")
            shutil.rmtree(data_repo_dir, ignore_errors=True)


if __name__ == "__main__":
    OPTIONS = init_options()
    main()
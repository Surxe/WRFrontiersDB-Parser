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
from options import init_options, Options
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


def upload_to_archive(repo_dir, output_dir, game_version, latest_commit):
    """
    Upload parsed data to the archive directory for the specified version.
    
    Args:
        repo_dir: Path to the data repository directory
        output_dir: Path to the output directory with new data
        game_version: Version string for the data being archived
        latest_commit: Latest commit info for commit message
    """
    archive_path = os.path.join(repo_dir, 'archive', game_version)
    
    # Clear existing archive data for this version (if it exists)
    if os.path.exists(archive_path):
        logger.debug(f"Deleting old archive data for version {game_version}...")
        shutil.rmtree(archive_path)
    
    logger.info(f"Creating archive directory: archive/{game_version}/")
    os.makedirs(archive_path, exist_ok=True)
    
    logger.info(f"Copying new output to archive/{game_version}/...")
    
    # Copy all files from output directory to archive directory
    if os.path.exists(output_dir):
        for item in os.listdir(output_dir):
            src = os.path.join(output_dir, item)
            dst = os.path.join(archive_path, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
    else:
        raise ValueError(f"Output directory {output_dir} does not exist")
    
    # Write version file
    version_file = os.path.join(archive_path, 'version.txt')
    with open(version_file, 'w') as f:
        f.write(game_version)
    
    # Commit the changes
    commit_title = f"Add archive version '{game_version}'"
    commit_description = f"Parser commit: '{latest_commit}'"
    
    run_git_command(['git', 'add', '.'], cwd=repo_dir, log_output=False)
    
    # Try to commit, but don't fail if there's nothing to commit
    try:
        run_git_command(['git', 'commit', '-m', commit_title, '-m', commit_description], cwd=repo_dir,
                       log_output=True)
        logger.info(f"Uploaded archive data for version {game_version} and committed changes.")
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in e.stdout:
            logger.info(f"No changes detected - archive data is already version {game_version}.")
        else:
            raise  # Re-raise if it's a different error


def update_current_data(repo_dir, output_dir, game_version, latest_commit):
    """
    Update the current directory with new parsed output.
    
    Args:
        repo_dir: Path to the data repository directory
        output_dir: Path to the output directory with new data
        game_version: Version string for the new data
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
        f.write(game_version)
    
    # Commit the changes
    commit_title = f"Update current to version '{game_version}'"
    commit_description = f"Parser commit: '{latest_commit}'"
    
    run_git_command(['git', 'add', '.'], cwd=repo_dir, log_output=False)
    
    # Try to commit, but don't fail if there's nothing to commit
    try:
        run_git_command(['git', 'commit', '-m', commit_title, '-m', commit_description], cwd=repo_dir,
                       log_output=True)
        logger.info(f"Updated current data to version {game_version} and committed changes.")
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in e.stdout:
            logger.info(f"No changes detected - current data is already version {game_version}.")
        else:
            raise  # Re-raise if it's a different error


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


def main(OPTIONS: Options):
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
        
        # Always upload to archive
        upload_to_archive(data_repo_dir, output_dir, OPTIONS.game_version, latest_commit)
        
        # Only update current if IS_CURRENT is true
        if OPTIONS.is_current:
            logger.info("IS_CURRENT is true, updating current directory...")
            update_current_data(data_repo_dir, output_dir, OPTIONS.game_version, latest_commit)
        else:
            logger.info("IS_CURRENT is false, skipping current directory update.")
        
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
    main(init_options())
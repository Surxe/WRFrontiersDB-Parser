# Can be run directly for convenience, but only offers env vars, and not arguments. For running just push with args, use run.py with --should-push-data

import sys
import os
import stat
import shutil
import subprocess
from pathlib import Path
import requests
import json

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from options import OPTIONS
from loguru import logger


def run_git_command(cmd, cwd=None, capture_output=True, check=True, log_output=False, log_command_str=True):
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
    
    if log_command_str:
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
        log_output=False,
        log_command_str=False
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
        run_git_command(['git', 'checkout', target_branch], cwd=repo_dir, log_output=True)
    except subprocess.CalledProcessError:
        # Branch doesn't exist, create it
        raise ValueError(f"Target branch '{target_branch}' does not exist in the repository.")

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
            log_output=True
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
    with open(version_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(game_version)
    
    # Commit the changes
    commit_title = f"Add/update archive version '{game_version}'"
    commit_description = f"Parser commit: '{latest_commit}'"
    
    run_git_command(['git', 'add', '.'], cwd=repo_dir, log_output=True)
    
    # Try to commit, but don't fail if there's nothing to commit
    try:
        run_git_command(['git', 'commit', '-m', commit_title, '-m', commit_description], cwd=repo_dir,
                       log_output=True)
        logger.info(f"Uploaded archive data for version {game_version} and committed changes.")
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in e.stdout:
            logger.info(f"No changes detected for archive version {game_version}.")
        else:
            raise  # Re-raise if it's a different error


def update_current_data(repo_dir, output_dir, game_version, latest_commit, target_branch):
    """
    Update the current directory with new parsed output.
    
    Args:
        repo_dir: Path to the data repository directory
        output_dir: Path to the output directory with new data
        game_version: Version string for the new data
        latest_commit: Latest commit info for commit message
        target_branch: Name of the target branch (used for tag naming)

    Returns:
        changes_made: Boolean indicating if changes were made. False if e.g. its the same as before.
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
    with open(version_file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(game_version)
    
    # Commit the changes
    commit_title = f"Update current to version '{game_version}'"
    commit_description = f"Parser commit: '{latest_commit}'"
    
    run_git_command(['git', 'add', '.'], cwd=repo_dir, log_output=True)
    
    # Try to commit, but don't fail if there's nothing to commit
    try:
        run_git_command(['git', 'commit', '-m', commit_title, '-m', commit_description], cwd=repo_dir,
                       log_output=True)
        logger.info(f"Updated current data to version {game_version} and committed changes.")
        
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in e.stdout:
            logger.info(f"No changes detected for current version {game_version}.")
            return False
        else:
            raise  # Re-raise if it's a different error
    
    return True


def trigger_data_repo_workflow():
    """
    Trigger a workflow in the data repository via repository dispatch.
    """
    logger.info("Triggering workflow in data repository...")
    
    url = "https://api.github.com/repos/Surxe/WRFrontiersDB-Data/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {OPTIONS.gh_data_repo_pat}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    payload = {
        "from_version": "",
        "to_version": ""
    } # this will be auto-detected when the workflow calls the summarizer. 
    # it checks against archive, as such, this function is only ran when pushing to archive.
    
    data = {
        "event_type": "data_updated",
        "client_payload": payload
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 204:
            logger.info("Successfully triggered workflow in data repository.")
        else:
            logger.error(f"Failed to trigger workflow: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error triggering workflow: {e}")


def push_changes(repo_dir, target_branch):
    """
    Push all commits and tags to the remote repository.
    
    Args:
        repo_dir: Path to the repository directory
        target_branch: Branch to push to
    """
    logger.info(f"Pushing changes to branch '{target_branch}'...")
    
    run_git_command(['git', 'push', 'origin', target_branch], cwd=repo_dir,
                   log_output=True)
    
    # Push tags (use --force to update existing tags)
    logger.info("Pushing tags...")
    run_git_command(['git', 'push', 'origin', '--tags', '--force'], cwd=repo_dir,
                   log_output=True)
    
    logger.info(f"All changes and tags committed and pushed successfully to branch '{target_branch}'.")

def create_version_config(repo_dir, game_version):
    """
    Update the version configuration file in the repository to include the current game version.
    
    Args:
        repo_dir: Path to the repository directory
        game_version: Current game version being pushed
    """
    logger.info("Updating version configuration file...")
    
    config_file = os.path.join(repo_dir, 'versions.json')
    # Read current config file
    with open(config_file, 'r') as f:
        version_configs = json.load(f)
    
    if game_version in version_configs:
        logger.info(f"Version {game_version} already exists in configuration, skipping update.")
        return
    
    # Prompt the user for title, date_utc, manifest_id, patch_notes_url, is_season_release
    title = input(f"Enter title for version {game_version}. Title should be concise and usually reference the biggest content released. If no content was released, name it 'Hotfix'. e.g. 'Decker and Tortuga': ")
    date_utc = input(f"Enter release date (UTC) for version {game_version} in YYYY-MM-DD format. Double check the utc date at https://steamdb.info/depot/1491005/manifests: ")
    manifest_id = input(f"Enter manifest ID for version {game_version}. Double check the manifest id at https://steamdb.info/depot/1491005/manifests: ")
    patch_notes_url_raw = input(f"Enter patch notes URL for version {game_version}. If no patch notes exist, press Enter: Double check the url at https://warrobotsfrontiers.com/en/news/ : ")
    is_season_release_raw = input(f"Is version {game_version} a season release? (yes/no): ")
    patch_notes_url = patch_notes_url_raw.strip() if patch_notes_url_raw.strip() else None
    is_season_release = bool(is_season_release_raw.strip().lower() in ['yes', 'y', 'true', '1'])
    is_season_release = True if is_season_release else None # if false it won't be stored. for cleaner JSON
    
    # Create the version config
    while True:
        version_config = {}
        version_config['title'] = title
        version_config['date_utc'] = date_utc
        version_config['manifest_id'] = manifest_id
        if patch_notes_url:
            version_config['patch_notes_url'] = patch_notes_url
        if is_season_release is not None:
            version_config['is_season_release'] = is_season_release
        logger.debug(f"Version config to add: {version_config}")
        confirm = input("Is this information correct? (yes/no): ")
        if confirm.strip().lower() in ['yes', 'y']:
            break


    # Add the version config to the overall configs at the very top
    version_configs = {game_version: version_config, **version_configs}

    # Write back the updated config file
    with open(config_file, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(version_configs, f, indent=4)

    # Add and commit the changes
    run_git_command(['git', 'add', 'versions.json'], cwd=repo_dir, log_output=True)
    
    try:
        run_git_command(['git', 'commit', '-m', f"Add the version configuration for {game_version}"], cwd=repo_dir,
                       log_output=True)
        logger.info("Version configuration file created/updated and committed.")
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in e.stdout:
            logger.info("No changes detected for version configuration file.")
        else:
            raise  # Re-raise if it's a different error

def upload_textures(repo_dir, texture_output_dir, game_version):
    """
    Copies textures from texture_output_dir/path/to/icon.ext 
    to repo_dir/textures/path/to/icon.ext and commits the changes.
    """

    # Copy textures
    textures_dest_dir = os.path.join(repo_dir, 'textures')
    if os.path.exists(texture_output_dir):
        for root, dirs, files in os.walk(texture_output_dir):
            for file in files:
                src = os.path.join(root, file)
                relative_path = os.path.relpath(src, texture_output_dir)
                dst = os.path.join(textures_dest_dir, relative_path)
                dst_dir = os.path.dirname(dst)
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(src, dst)
    else:
        raise ValueError(f"Texture output directory {texture_output_dir} does not exist")
    
    # Commit the changes
    logger.info("Committing texture updates...")
    run_git_command(['git', 'add', 'textures'], cwd=repo_dir, log_output=True)

    # Try to commit, but don't fail if there's nothing to commit
    commit_title = f"Update textures to {game_version}"
    commit_description = "Updated textures from parser output."
    try:
        run_git_command(['git', 'commit', '-m', commit_title, '-m', commit_description], cwd=repo_dir,
                       log_output=True)
        logger.info(f"Updated textures and committed changes.")
        
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in e.stdout:
            logger.info(f"No changes detected for texture updates.")
            return False
        else:
            raise  # Re-raise if it's a different error
    
    return True

def main():
    """Main function that orchestrates the data pushing process. Uses global OPTIONS singleton."""
    # Quit early if neither push option is enabled
    if not OPTIONS.push_to_archive and not OPTIONS.push_to_current and not OPTIONS.should_push_textures:
        logger.info("None of push_to_archive nor push_to_current nor should_push_textures are enabled. Exiting push process.")
        return
    
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
        
        # Upload to archive if enabled
        if OPTIONS.push_to_archive:
            logger.info("Pushing to archive is true, updating archive directory...")
            upload_to_archive(data_repo_dir, output_dir, OPTIONS.game_version, latest_commit)
        else:
            logger.info("Pushing to archive is false, skipping archive directory update.")

        # Update current if enabled
        changes_made = False
        if OPTIONS.push_to_current:
            logger.info("Pushing to current is true, updating current directory...")
            changes_made = update_current_data(data_repo_dir, output_dir, OPTIONS.game_version, latest_commit, OPTIONS.target_branch)
        else:
            logger.info("Pushing to current is false, skipping current directory update.")

        if OPTIONS.create_version_config:
            create_version_config(data_repo_dir, OPTIONS.game_version)

        # Update Textures
        if OPTIONS.should_push_textures:
            logger.info("Copying textures to data repository...")
            upload_textures(data_repo_dir, OPTIONS.texture_output_dir, game_version=OPTIONS.game_version)
        else:
            logger.info("should_push_textures is false, skipping texture upload.")
        
        # Push all changes
        push_changes(data_repo_dir, OPTIONS.target_branch)
        
        # Trigger workflow in data repository
        if OPTIONS.push_to_archive and OPTIONS.trigger_data_workflow and changes_made:
            trigger_data_repo_workflow()
        else:
            logger.info("Triggering data workflow is false or no previous version, skipping workflow trigger.")
        
    except Exception as e:
        logger.error(f"Error during push process: {e}")
        raise
    finally:
        # Cleanup - remove cloned repository
        if os.path.exists(data_repo_dir):
            logger.debug(f"Cleaning up {data_repo_dir}...")
            shutil.rmtree(data_repo_dir, ignore_errors=True)
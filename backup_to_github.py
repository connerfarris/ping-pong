#!/usr/bin/env python3
"""
Database backup script for Ping Pong Stats
Automatically creates database backups and pushes them to GitHub
"""
import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
import sys

def setup_git():
    """Configure git with the necessary settings"""
    subprocess.run(["git", "config", "--global", "user.name", "PingPongBackupBot"], check=False)
    subprocess.run(["git", "config", "--global", "user.email", "backup@pingpong.app"], check=False)

def ensure_backup_repo():
    """Ensure the backup repository is cloned and up to date"""
    backup_repo = "ping-pong-backups"
    backup_dir = Path("..") / backup_repo
    
    if not backup_dir.exists():
        print(f"Cloning backup repository to {backup_dir}...")
        subprocess.run(
            ["git", "clone", f"git@github.com:connerfarris/{backup_repo}.git", str(backup_dir)],
            check=True
        )
    
    # Ensure we're on the main branch
    os.chdir(backup_dir)
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "pull", "--rebase"], check=False)
    os.chdir("..")
    
    return backup_dir

def create_backup(backup_dir: Path) -> str:
    """
    Create a database backup
    Returns the path to the created backup file
    """
    # Get database path
    db_path = Path("instance/ping_pong.db")
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")
    
    # Create timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"ping_pong_{timestamp}.db"
    
    try:
        # Copy the database file
        shutil.copy2(db_path, backup_file)
        print(f"✓ Created backup: {backup_file}")
        return str(backup_file)
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        raise

def push_to_github(backup_dir: Path) -> bool:
    """Commit and push changes to GitHub"""
    try:
        os.chdir(backup_dir)
        
        # Add all files in the backup directory
        subprocess.run(["git", "add", "."], check=True)
        
        # Commit with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subprocess.run(
            ["git", "commit", "-m", f"Backup {timestamp}"],
            check=True
        )
        
        # Push to GitHub
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✓ Pushed backup to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to push to GitHub: {e}")
        return False
    finally:
        # Always return to the original directory
        os.chdir("..")

def backup_to_github():
    """Main function to create and push a backup to GitHub
    
    Returns:
        tuple: (success: bool, message: str)
    """
    print("🚀 Starting database backup...")
    
    try:
        # Setup git
        setup_git()
        
        # Ensure backup repo is ready
        backup_dir = ensure_backup_repo()
        
        # Create backup
        backup_file = create_backup(backup_dir)
        
        # Push to GitHub
        if push_to_github(backup_dir):
            msg = "✅ Backup completed and pushed to GitHub successfully!"
            print(msg)
            return True, msg
        else:
            msg = "⚠️  Backup created but could not push to GitHub"
            print(msg)
            return False, msg
            
    except Exception as e:
        error_msg = f"❌ Backup failed: {e}"
        print(error_msg)
        return False, str(e)

def main():
    """Command-line entry point"""
    success, message = backup_to_github()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Database backup script for Ping Pong Stats
Automatically creates SQL dumps and pushes them to GitHub
"""
import os
import subprocess
import datetime
from pathlib import Path
import sys
from typing import Optional

def setup_git():
    """Configure git with the necessary settings"""
    subprocess.run("git config --global user.name 'PingPongBackupBot'", shell=True, check=False)
    subprocess.run("git config --global user.email 'backup@pingpong.app'", shell=True, check=False)

def create_backup() -> str:
    """
    Create a database backup
    Returns the path to the created backup file
    """
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Create backups directory if it doesn't exist
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    # Create timestamped backup filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    backup_file = backup_dir / f"db_backup_{timestamp}.sql"
    
    # Dump database (using pg_dump for PostgreSQL)
    try:
        cmd = f"pg_dump {db_url} > {backup_file}"
        subprocess.run(cmd, shell=True, check=True)
        print(f"✓ Created backup: {backup_file}")
        return str(backup_file)
    except subprocess.CalledProcessError as e:
        print(f"✗ Backup failed: {e}")
        raise

def push_to_github():
    """Commit and push changes to GitHub"""
    try:
        # Add all backup files
        subprocess.run("git add backups/", shell=True, check=True)
        
        # Check if there are changes to commit
        result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
        if not result.stdout.strip():
            print("ℹ No changes to commit")
            return False
            
        # Commit and push
        commit_msg = f"🔒 Automated database backup - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(f'git commit -m "{commit_msg}"', shell=True, check=True)
        subprocess.run("git push origin main", shell=True, check=True)
        print("✓ Pushed changes to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ GitHub push failed: {e}")
        return False

def main():
    print("🚀 Starting database backup...")
    
    # Setup git config
    setup_git()
    
    try:
        # Create backup
        backup_file = create_backup()
        
        # Push to GitHub
        if push_to_github():
            print(f"✅ Backup completed successfully: {backup_file}")
        else:
            print("⚠ Backup created but not pushed to GitHub")
    except Exception as e:
        print(f"❌ Backup failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Database restore script for Ping Pong Stats
Restores the database from a backup file
"""
import os
import subprocess
import sys
from pathlib import Path

def list_backups() -> list:
    """List all available backups"""
    backup_dir = Path("backups")
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("*.sql"), reverse=True)

def restore_database(backup_file: str) -> bool:
    """Restore database from a backup file"""
    if not os.path.exists(backup_file):
        print(f"✗ Backup file not found: {backup_file}")
        return False
    
    db_url = os.getenv('DATABASE_URL', 'sqlite:///ping_pong.db')
    db_file = db_url.replace('sqlite:///', '')
    
    try:
        print(f"🔄 Restoring from {backup_file}...")
        import shutil
        shutil.copy2(backup_file, db_file)
        print("✅ Database restored successfully!")
        return True
    except Exception as e:
        print(f"✗ Restore failed: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        # Restore from specified file
        backup_file = sys.argv[1]
        if not os.path.exists(backup_file):
            print(f"Error: File not found: {backup_file}")
            sys.exit(1)
    else:
        # Show list of available backups
        backups = list_backups()
        if not backups:
            print("No backup files found in backups/ directory")
            sys.exit(1)
            
        print("\nAvailable backups (newest first):")
        for i, backup in enumerate(backups, 1):
            print(f"{i}. {backup.name}")
        
        try:
            choice = int(input("\nSelect backup to restore (number): "))
            if 1 <= choice <= len(backups):
                backup_file = str(backups[choice - 1])
            else:
                print("Invalid selection")
                sys.exit(1)
        except ValueError:
            print("Please enter a valid number")
            sys.exit(1)
    
    # Confirm before restoring
    confirm = input(f"\nWARNING: This will overwrite your current database with data from {backup_file}\n"
                    "Are you sure you want to continue? (y/N): ")
    
    if confirm.lower() == 'y':
        if not restore_database(backup_file):
            sys.exit(1)
    else:
        print("Restore cancelled")

if __name__ == "__main__":
    main()

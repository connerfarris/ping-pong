#!/usr/bin/env python3
"""
Database restore script for Ping Pong Stats
Restores the database from a backup file in the ping-pong-backups repository
"""
import os
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime

def ensure_backup_repo() -> Path:
    """Ensure the backup repository is cloned and return its path"""
    backup_repo = "ping-pong-backups"
    backup_dir = Path("..") / backup_repo
    
    if not backup_dir.exists():
        print(f"Cloning backup repository to {backup_dir}...")
        subprocess.run(
            ["git", "clone", f"git@github.com:connerfarris/{backup_repo}.git", str(backup_dir)],
            check=True
        )
    
    # Update the repository
    os.chdir(backup_dir)
    subprocess.run(["git", "pull"], check=False)
    os.chdir("..")
    
    return backup_dir

def list_backups(backup_dir: Path) -> list:
    """List all available backups with their details"""
    if not backup_dir.exists():
        return []
        
    backups = []
    for file in backup_dir.glob("ping_pong_*.db"):
        try:
            # Extract timestamp from filename
            timestamp_str = file.stem.replace("ping_pord_", "")
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            
            backups.append({
                'path': file,
                'filename': file.name,
                'timestamp': timestamp,
                'size': file.stat().st_size,
                'formatted_date': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'size_mb': file.stat().st_size / (1024 * 1024)
            })
        except ValueError:
            continue
    
    # Sort by timestamp (newest first)
    return sorted(backups, key=lambda x: x['timestamp'], reverse=True)

def restore_database(backup_file: Path) -> bool:
    """Restore database from a backup file"""
    if not backup_file.exists():
        print(f"✗ Backup file not found: {backup_file}")
        return False
    
    # Path to the current database
    db_path = Path("instance/ping_pong.db")
    
    try:
        # Create a backup of the current database
        if db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = db_path.parent / f"ping_pong_backup_{timestamp}.db"
            shutil.copy2(db_path, backup_path)
            print(f"✓ Created backup of current database at {backup_path}")
        
        # Restore from the selected backup
        print(f"🔄 Restoring from {backup_file.name}...")
        shutil.copy2(backup_file, db_path)
        print("✅ Database restored successfully!")
        return True
    except Exception as e:
        print(f"✗ Restore failed: {e}")
        return False

def main():
    # Ensure we have the backup repository
    try:
        backup_dir = ensure_backup_repo()
    except Exception as e:
        print(f"❌ Failed to access backup repository: {e}")
        sys.exit(1)
    
    # List available backups
    backups = list_backups(backup_dir)
    
    if not backups:
        print("❌ No backup files found in the repository")
        sys.exit(1)
    
    # If a specific backup was requested via command line
    if len(sys.argv) > 1:
        backup_file = Path(sys.argv[1])
        if not backup_file.exists():
            print(f"Error: File not found: {backup_file}")
            sys.exit(1)
        
        if not backup_file.is_relative_to(backup_dir):
            print(f"Warning: The specified file is not in the backup repository: {backup_file}")
            confirm = input("Do you want to proceed? (y/n): ")
            if confirm.lower() != 'y':
                print("Restore cancelled.")
                sys.exit(0)
        
        restore_database(backup_file)
        sys.exit(0)
    
    # Interactive mode: show list of available backups
    print("\nAvailable backups (newest first):\n")
    print(f"{'#':<4} {'Date/Time':<20} {'Size (MB)':<10} {'File'}")
    print("-" * 60)
    
    for i, backup in enumerate(backups, 1):
        print(f"{i:<4} {backup['formatted_date']:<20} {backup['size_mb']:<10.2f} {backup['filename']}")
    
    while True:
        try:
            choice = input("\nEnter backup number to restore (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                print("Restore cancelled.")
                break
                
            index = int(choice) - 1
            if 0 <= index < len(backups):
                backup_file = backups[index]['path']
                if restore_database(backup_file):
                    print("\n✅ Database restored successfully!")
                    print(f"Restored from: {backup_file.name}")
                    break
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number or 'q' to quit.")
    
    print("\nRestore process completed.")

if __name__ == "__main__":
    main()

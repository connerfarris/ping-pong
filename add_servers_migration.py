#!/usr/bin/env python3
import os
import sys
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask_migrate import upgrade, stamp
from ping_pong_web import app, db

def add_servers_columns():
    with app.app_context():
        # This will create a new migration with the model changes
        print("Creating migration for server columns...")
        
        # Create a new migration
        from alembic import command
        from alembic.config import Config
        
        # Initialize Alembic configuration
        config = Config("migrations/alembic.ini")
        config.set_main_option('script_location', 'migrations')
        
        # Create a new migration
        command.revision(config, autogenerate=True, message="Add server columns to doubles_matches")
        
        # Apply the migration
        command.upgrade(config, 'head')
        
        print("Migration completed successfully!")

if __name__ == '__main__':
    add_servers_columns()

#!/usr/bin/env python3
import os
from flask_migrate import Migrate, upgrade, migrate as migrate_cmd, init, stamp
from ping_pong_web import app, db

# Initialize Flask-Migrate
def run_migrations():
    with app.app_context():
        # Initialize the migrations repository (only needed once)
        try:
            init()
            print("Initialized new migration repository")
        except:
            print("Migration repository already exists")
        
        # Create a new migration
        migrate_cmd(message="Initial migration")
        
        # Apply the migration
        upgrade()
        print("Successfully applied migrations!")

if __name__ == '__main__':
    run_migrations()

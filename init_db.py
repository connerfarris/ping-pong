#!/usr/bin/env python3
import os
import json
from datetime import datetime
from ping_pong_web import app, db
from models import Player, Match

def init_db():
    """Initialize the database with existing data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if we already have data
        if Player.query.first() is None:
            # Load existing players from JSON if available
            players_file = os.path.join(os.path.dirname(__file__), 'players.json')
            if os.path.exists(players_file):
                with open(players_file, 'r') as f:
                    players_data = json.load(f)
                    for name in players_data.get('players', []):
                        player = Player(name=name)
                        db.session.add(player)
            else:
                # Add default players
                default_players = ["Conner", "Ridzky", "Ryan", "Prasidh", "Carson", "Tanner"]
                for name in default_players:
                    player = Player(name=name)
                    db.session.add(player)
            
            # TODO: Add code to migrate existing matches from JSON to database
            # This would parse your existing match data and create Match records
            
            db.session.commit()
            print("Database initialized successfully!")
        else:
            print("Database already contains data. No initialization needed.")

if __name__ == '__main__':
    init_db()

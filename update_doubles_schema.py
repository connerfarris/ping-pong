#!/usr/bin/env python3
import os
import sys
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create a minimal Flask app
app = Flask(__name__)
# Use the same database path as in your main application
import os
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'ping_pong.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

# Define the models directly in this script to avoid import issues
class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    singles_rating = db.Column(db.Float, default=1000.0)
    doubles_rating = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    players = db.relationship('Player', secondary='team_players')

class DoublesMatch(db.Model):
    __tablename__ = 'doubles_matches'
    id = db.Column(db.Integer, primary_key=True)
    team1_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    team2_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    team1_server_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    team1_partner_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    team2_receiver_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    team2_partner_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    score1 = db.Column(db.Integer, nullable=False, default=0)
    score2 = db.Column(db.Integer, nullable=False, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    team1 = db.relationship('Team', foreign_keys=[team1_id])
    team2 = db.relationship('Team', foreign_keys=[team2_id])
    team1_server = db.relationship('Player', foreign_keys=[team1_server_id])
    team1_partner = db.relationship('Player', foreign_keys=[team1_partner_id])
    team2_receiver = db.relationship('Player', foreign_keys=[team2_receiver_id])
    team2_partner = db.relationship('Player', foreign_keys=[team2_partner_id])

# Association table
team_players = db.Table('team_players',
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True),
    db.Column('player_id', db.Integer, db.ForeignKey('players.id'), primary_key=True)
)

def get_or_create_player(session, name):
    """Get or create a player by name"""
    if not name:
        return None
        
    player = Player.query.filter_by(name=name).first()
    if not player:
        player = Player(name=name)
        session.add(player)
        try:
            session.commit()
        except:
            session.rollback()
            player = Player.query.filter_by(name=name).first()
    return player

def get_or_create_team(session, player1_name, player2_name):
    """Get or create a team with the given players"""
    if not player1_name or not player2_name:
        return None
        
    # Create a consistent team name (sorted to avoid duplicates)
    team_name = " & ".join(sorted([player1_name, player2_name]))
    
    # Check if team exists
    team = Team.query.filter_by(name=team_name).first()
    if not team:
        player1 = get_or_create_player(session, player1_name)
        player2 = get_or_create_player(session, player2_name)
        if not player1 or not player2:
            return None
            
        team = Team(name=team_name)
        team.players = [player1, player2]
        session.add(team)
        try:
            session.commit()
        except:
            session.rollback()
            team = Team.query.filter_by(name=team_name).first()
    return team

def migrate_doubles_matches():
    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()
        
        # Check if we have any existing data to migrate
        matches_file = 'ping_pong_matches.json'
        if not os.path.exists(matches_file):
            print(f"No {matches_file} file found. No data to migrate.")
            return
            
        print("Starting data migration...")
        
        # Load existing data
        with open(matches_file, 'r') as f:
            matches_data = json.load(f)
            
        # Process all matches
        match_count = 0
        for date_data in matches_data:
            date_str = date_data.get('date')
            try:
                match_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                print(f"Invalid date format: {date_str}, skipping...")
                continue
                
            for match in date_data.get('matches', []):
                if match.get('type') != 'doubles':
                    continue
                    
                match_id = match.get('id', str(uuid.uuid4()))
                team1 = match.get('team1', {})
                team2 = match.get('team2', {})
                
                if not all([team1.get('server'), team1.get('partner'), 
                          team2.get('receiver'), team2.get('partner')]):
                    print(f"Skipping invalid doubles match: {match}")
                    continue
                
                try:
                    # Get or create teams and players
                    team1_obj = get_or_create_team(
                        db.session,
                        team1['server'],
                        team1['partner']
                    )
                    
                    team2_obj = get_or_create_team(
                        db.session,
                        team2['receiver'],
                        team2['partner']
                    )
                    
                    if not team1_obj or not team2_obj:
                        print(f"Skipping match {match_id} due to missing team data")
                        continue
                    
                    # Get all player objects
                    team1_server = get_or_create_player(db.session, team1['server'])
                    team1_partner = get_or_create_player(db.session, team1['partner'])
                    team2_receiver = get_or_create_player(db.session, team2['receiver'])
                    team2_partner = get_or_create_player(db.session, team2['partner'])
                    
                    # Check if the match already exists
                    existing_match = DoublesMatch.query.get(match_id)
                    if existing_match:
                        # Update existing match
                        existing_match.team1_id = team1_obj.id
                        existing_match.team2_id = team2_obj.id
                        existing_match.team1_server_id = team1_server.id if team1_server else None
                        existing_match.team1_partner_id = team1_partner.id if team1_partner else None
                        existing_match.team2_receiver_id = team2_receiver.id if team2_receiver else None
                        existing_match.team2_partner_id = team2_partner.id if team2_partner else None
                        existing_match.score1 = match.get('score', {}).get('team1', 0) or 0
                        existing_match.score2 = match.get('score', {}).get('team2', 0) or 0
                        existing_match.timestamp = datetime.combine(match_date, datetime.min.time())
                    else:
                        # Create new match
                        match_timestamp = datetime.combine(match_date, datetime.min.time())
                        doubles_match = DoublesMatch(
                            id=match_id,
                            team1_id=team1_obj.id,
                            team2_id=team2_obj.id,
                            team1_server_id=team1_server.id if team1_server else None,
                            team1_partner_id=team1_partner.id if team1_partner else None,
                            team2_receiver_id=team2_receiver.id if team2_receiver else None,
                            team2_partner_id=team2_partner.id if team2_partner else None,
                            score1=match.get('score', {}).get('team1', 0) or 0,
                            score2=match.get('score', {}).get('team2', 0) or 0,
                            timestamp=match_timestamp
                        )
                        db.session.add(doubles_match)
                    
                    match_count += 1
                    if match_count % 10 == 0:
                        db.session.commit()
                        print(f"Processed {match_count} matches...")
                        
                except Exception as e:
                    print(f"Error processing match {match_id}: {str(e)}")
                    db.session.rollback()
        
        # Commit any remaining changes
        db.session.commit()
        print(f"Data migration completed! Processed {match_count} matches.")

if __name__ == '__main__':
    import json
    import uuid
    migrate_doubles_matches()

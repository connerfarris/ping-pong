#!/usr/bin/env python3
import os
import sys
import json
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and models
from ping_pong_web import app, db
from models import Player, SinglesMatch, DoublesMatch, Team

def get_or_create_player(session, name):
    """Get or create a player by name"""
    player = Player.query.filter_by(name=name).first()
    if not player:
        player = Player(name=name)
        session.add(player)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            player = Player.query.filter_by(name=name).first()
    return player

def get_or_create_team(session, player1_name, player2_name):
    """Get or create a team with the given players"""
    # Get or create players first
    player1 = get_or_create_player(session, player1_name)
    player2 = get_or_create_player(session, player2_name)
    
    # Create a consistent team name (sorted to avoid duplicates)
    team_name = " & ".join(sorted([player1_name, player2_name]))
    
    # Check if team exists
    team = Team.query.filter_by(name=team_name).first()
    if not team:
        team = Team(name=team_name)
        team.players = [player1, player2]
        session.add(team)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            team = Team.query.filter_by(name=team_name).first()
    return team

def migrate_data():
    # Use the existing app context
    with app.app_context():
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
                match_type = match.get('type', 'singles')
                match_id = match.get('id', str(uuid.uuid4()))
                
                try:
                    if match_type == 'singles':
                        # Handle singles match
                        player1_name = match.get('player1')
                        player2_name = match.get('player2')
                        
                        if not all([player1_name, player2_name]):
                            print(f"Skipping invalid singles match: {match}")
                            continue
                        
                        player1 = get_or_create_player(db.session, player1_name)
                        player2 = get_or_create_player(db.session, player2_name)
                        
                        singles_match = SinglesMatch(
                            id=match_id,
                            player1_id=player1.id,
                            player2_id=player2.id,
                            score1=match.get('score', {}).get('player1', 0) or 0,
                            score2=match.get('score', {}).get('player2', 0) or 0,
                            timestamp=datetime.combine(match_date, datetime.min.time())
                        )
                        db.session.add(singles_match)
                        
                    elif match_type == 'doubles':
                        # Handle doubles match
                        team1 = match.get('team1', {})
                        team2 = match.get('team2', {})
                        
                        if not all([team1.get('server'), team1.get('partner'), 
                                  team2.get('receiver'), team2.get('partner')]):
                            print(f"Skipping invalid doubles match: {match}")
                            continue
                        
                        # Create or get teams
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
                        
                        # Get all player information with their specific positions
                        team1_server = get_or_create_player(db.session, team1['server'])
                        team1_partner = get_or_create_player(db.session, team1['partner'])
                        team2_receiver = get_or_create_player(db.session, team2['receiver'])
                        team2_partner = get_or_create_player(db.session, team2['partner'])
                        
                        # Create the doubles match with all player positions
                        doubles_match = DoublesMatch(
                            id=match_id,
                            team1_id=team1_obj.id,
                            team2_id=team2_obj.id,
                            team1_server_id=team1_server.id,
                            team1_partner_id=team1_partner.id,
                            team2_receiver_id=team2_receiver.id,
                            team2_partner_id=team2_partner.id,
                            score1=match.get('score', {}).get('team1', 0) or 0,
                            score2=match.get('score', {}).get('team2', 0) or 0,
                            timestamp=datetime.combine(match_date, datetime.min.time())
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
    migrate_data()

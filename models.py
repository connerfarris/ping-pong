from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Association table for many-to-many relationship between players and doubles teams
team_players = db.Table('team_players',
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True),
    db.Column('player_id', db.Integer, db.ForeignKey('players.id'), primary_key=True)
)

class Player(db.Model):
    __tablename__ = 'players'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    singles_rating = db.Column(db.Float, default=1000.0)
    doubles_rating = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    singles_matches_as_player1 = db.relationship('SinglesMatch', 
                                               foreign_keys='SinglesMatch.player1_id',
                                               backref='player1',
                                               lazy=True)
    singles_matches_as_player2 = db.relationship('SinglesMatch',
                                               foreign_keys='SinglesMatch.player2_id',
                                               backref='player2',
                                               lazy=True)
    
    # Teams this player is part of for doubles
    doubles_teams = db.relationship('Team',
                                  secondary=team_players,
                                  lazy='subquery',
                                  backref=db.backref('players', lazy=True))
    
    def __repr__(self):
        return f'<Player {self.name}>'

class Team(db.Model):
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Float, default=1000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    doubles_matches_as_team1 = db.relationship('DoublesMatch',
                                             foreign_keys='DoublesMatch.team1_id',
                                             backref='team1',
                                             lazy=True)
    doubles_matches_as_team2 = db.relationship('DoublesMatch',
                                             foreign_keys='DoublesMatch.team2_id',
                                             backref='team2',
                                             lazy=True)
    
    def __repr__(self):
        player_names = ", ".join([p.name for p in self.players])
        return f'<Team {self.name} ({player_names})>'

class BaseMatch:
    """Base class with common match functionality"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    score1 = db.Column(db.Integer, nullable=False)
    score2 = db.Column(db.Integer, nullable=False)
    winner = db.Column(db.Integer, nullable=True)  # 1 or 2 for winner, None for draw
    
    def determine_winner(self):
        """Determine and set the winner based on scores"""
        if self.score1 > self.score2:
            self.winner = 1
        elif self.score2 > self.score1:
            self.winner = 2
        else:
            self.winner = None  # Draw
    
    def to_dict(self):
        """Convert match to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'score1': self.score1,
            'score2': self.score2,
            'winner': self.winner
        }

class SinglesMatch(db.Model, BaseMatch):
    __tablename__ = 'singles_matches'
    
    player1_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    
    def to_dict(self):
        """Extend base to_dict with singles-specific data"""
        data = super().to_dict()
        data.update({
            'match_type': 'singles',
            'player1': self.player1.name,
            'player2': self.player2.name
        })
        return data

class DoublesMatch(db.Model, BaseMatch):
    __tablename__ = 'doubles_matches'
    
    team1_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    team2_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    
    # Player positions and roles
    team1_server_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    team1_partner_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    team2_receiver_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    team2_partner_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    
    # Relationships for players in their specific positions
    team1_server = db.relationship('Player', foreign_keys=[team1_server_id])
    team1_partner = db.relationship('Player', foreign_keys=[team1_partner_id])
    team2_receiver = db.relationship('Player', foreign_keys=[team2_receiver_id])
    team2_partner = db.relationship('Player', foreign_keys=[team2_partner_id])
    
    def to_dict(self):
        """Extend base to_dict with doubles-specific data"""
        data = super().to_dict()
        
        # Get all player objects
        team1_players = [self.team1_server, self.team1_partner] if self.team1_server and self.team1_partner else []
        team2_players = [self.team2_receiver, self.team2_partner] if self.team2_receiver and self.team2_partner else []
        
        data.update({
            'match_type': 'doubles',
            'team1': {
                'id': self.team1.id,
                'name': self.team1.name,
                'server': self.team1_server.name if self.team1_server else None,
                'partner': self.team1_partner.name if self.team1_partner else None,
                'players': [p.name for p in team1_players]
            },
            'team2': {
                'id': self.team2.id,
                'name': self.team2.name,
                'receiver': self.team2_receiver.name if self.team2_receiver else None,
                'partner': self.team2_partner.name if self.team2_partner else None,
                'players': [p.name for p in team2_players]
            },
            'play_order': [
                self.team1_server.name if self.team1_server else None,
                self.team2_receiver.name if self.team2_receiver else None,
                self.team1_partner.name if self.team1_partner else None,
                self.team2_partner.name if self.team2_partner else None
            ]
        })
        return data

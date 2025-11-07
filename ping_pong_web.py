#!/usr/bin/env python3
# Written by Windsurf
import json
import os
import re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import statistics calculator
from stats_calculator import get_all_statistics, get_match_expected_map

# Import the parsing function from the existing script
from parse_ping_pong_matches import parse_ping_pong_matches

# Player management functions
def load_players():
    """Written by Windsurf
    Load player names from players.json
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    players_file = os.path.join(script_dir, "players.json")
    
    if not os.path.exists(players_file):
        # Create default players file if it doesn't exist
        default_players = {
            "players": ["Conner", "Ridzky", "Ryan", "Prasidh", "Carson", "Tanner"]
        }
        with open(players_file, 'w') as f:
            json.dump(default_players, f, indent=2)
        return default_players["players"]
    
    try:
        with open(players_file, 'r') as f:
            data = json.load(f)
            return data.get("players", [])
    except Exception as e:
        print(f"Error loading players: {e}")
        return []

def save_players(players):
    """Written by Windsurf
    Save player names to players.json
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    players_file = os.path.join(script_dir, "players.json")
    
    try:
        with open(players_file, 'w') as f:
            json.dump({"players": players}, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving players: {e}")
        return False

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', "ping-pong-tracker-secret-key")

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # For production, consider using Redis
)

# Stricter rate limiting for authentication attempts
auth_limiter = limiter.shared_limit(
    "5 per minute",
    scope="auth",
    error_message="Too many login attempts. Please try again later."
)

# Authentication configuration
USERNAME = os.environ.get('ADMIN_USERNAME', 'pingpongadmin')
PASSWORD = os.environ.get('ADMIN_PASSWORD')

def check_auth(username, password):
    """Check if a username/password combination is valid."""
    return username == USERNAME and password == PASSWORD

def requires_auth(f):
    @wraps(f)
    @auth_limiter  # Apply rate limiting to all auth attempts
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

def quote_name(name):
    """Written by Windsurf
    """
    try:
        s = str(name)
    except Exception:
        return name
    if not s:
        return s
    if re.search(r"\s", s) or '"' in s:
        return '"' + s.replace('"', '\\"') + '"'
    return s

@app.route('/')
@requires_auth
def index():
    """Written by Windsurf"""
    # Always use today's date
    today = datetime.now().strftime("%Y-%m-%d")
    date = today
    match_text = ""
    
    # Try to load matches for today's date from JSON file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, "ping_pong_matches.json")
    
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r') as f:
                all_data = json.load(f)
            
            # Find entry for today's date
            for entry in all_data:
                if entry.get('date') == today:
                    # Convert JSON data to match_text format
                    match_text = convert_json_to_match_text(entry)
                    break
        except Exception as e:
            flash(f"Error loading matches for today: {str(e)}", "error")
    
    # If no matches found for today, also check ping_pong_day.txt as fallback
    if not match_text:
        input_file = os.path.join(script_dir, "ping_pong_day.txt")
        if os.path.exists(input_file):
            try:
                with open(input_file, 'r') as f:
                    content = f.read()
                    
                lines = content.strip().split('\n')
                if lines:
                    # First line is the date
                    file_date = lines[0].strip()
                    
                    # Only use the file data if it's for today
                    try:
                        datetime.strptime(file_date, "%Y-%m-%d")
                        if file_date == today:
                            # Rest of the lines are matches
                            match_text = '\n'.join(lines[1:])
                    except ValueError:
                        pass  # Invalid date format, ignore
            except Exception as e:
                flash(f"Error loading file: {str(e)}", "error")
    
    return render_template('index.html', date=date, match_text=match_text)

@app.route('/parse', methods=['GET', 'POST'])
@requires_auth
def parse():
    """Written by Windsurf"""
    date = request.form.get('date', '').strip()
    match_text = request.form.get('match_text', '').strip()
    
    if not date:
        flash("Please select a date", "error")
        return redirect(url_for('index'))
        
    # If no match text is provided, just load the date without adding matches
    if not match_text:
        return redirect(url_for('load_from_file', date=date))
    
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD", "error")
        return redirect(url_for('index'))
    
    # Combine date and match text
    input_text = f"{date}\n{match_text}"
    
    try:
        # Parse the input
        result = parse_ping_pong_matches(input_text)
        
        # Ensure result has matches
        if not result or 'matches' not in result or not result['matches']:
            flash("No valid matches were found in the input. Please check your match entries.", "warning")
            return redirect(url_for('index'))
        
        # Get script directory for saving the file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, "ping_pong_matches.json")
        
        # Read existing JSON data if file exists
        existing_data = []
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    existing_data = json.load(f)
                    # If the existing data is not a list, convert it to a list with one item
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
            except (json.JSONDecodeError, FileNotFoundError):
                # If file is empty or invalid JSON, start with empty list
                existing_data = []
        
        # Check if an entry with the same date already exists
        found_existing = False
        for i, entry in enumerate(existing_data):
            if entry.get('date') == date:
                # Replace existing matches with new ones for the same date
                new_matches = result.get('matches', [])
                
                # Replace the matches entirely
                entry['matches'] = new_matches
                
                # Update the entry
                existing_data[i] = entry
                found_existing = True
                flash(f"Updated {len(new_matches)} matches for {date}", "success")
                break
                
        # If no existing entry was found, append the new data
        if not found_existing:
            existing_data.append(result)
        
        # Save to JSON file
        with open(output_file, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        flash(f"Match data saved to {output_file}", "success")
        
        # Redirect to loader for the selected date so refresh shows the saved matches
        return redirect(url_for('load_from_file', date=date))
        
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/load-from-file')
def load_from_file():
    """Written by Windsurf"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, "ping_pong_matches.json")
    
    try:
        # Get the date from the query parameter or use today's date
        date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            date = datetime.now().strftime("%Y-%m-%d")
            flash("Invalid date format. Using current date.", "warning")
        
        # Load JSON data
        if not os.path.exists(json_file):
            flash(f"JSON file {json_file} not found", "error")
            return redirect(url_for('index'))
            
        with open(json_file, 'r') as f:
            all_data = json.load(f)
        
        # Find entry for the specified date
        date_data = None
        for entry in all_data:
            if entry.get('date') == date:
                date_data = entry
                break
        
        # If no data found for the date, create an empty data structure
        if not date_data:
            date_data = {
                'date': date,
                'matches': []
            }
            flash(f"No matches found for {date}. You can add new matches below.", "info")
        
        # Convert JSON data to match_text format
        match_text = convert_json_to_match_text(date_data)
        
        # Only show the "loaded data" message if we actually found matches
        if date_data.get('matches'):
            flash(f"Loaded {len(date_data.get('matches'))} matches for {date}", "success")
        return render_template('index.html', date=date, match_text=match_text)
        
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
    
    return redirect(url_for('index'))

def convert_json_to_match_text(date_data):
    """Written by Windsurf
    Convert JSON match data to the text format expected by the UI
    """
    match_lines = []
    
    for match in date_data.get('matches', []):
        result_type = match.get('result_type', 'score')  # Default to 'score' for backward compatibility
        
        if match.get('type') == 'singles':
            player1 = quote_name(match.get('player1', ''))
            player2 = quote_name(match.get('player2', ''))
            
            if result_type == 'score':
                # Singles match format with score: player1 player2 score1-score2
                score1 = match.get('score', {}).get('player1', 0)
                score2 = match.get('score', {}).get('player2', 0)
                match_lines.append(f"{player1} {player2} {score1}-{score2}")
            else:
                # Singles match format with win/loss: player1 player2 P1/P2
                result_value = match.get('result_value', 'P1')  # Default to P1 if missing
                # Convert old W/L format to P1/P2 if needed
                if result_value == 'W':
                    result_value = 'P1'
                elif result_value == 'L':
                    result_value = 'P2'
                match_lines.append(f"{player1} {player2} {result_value}")
                
        elif match.get('type') == 'doubles':
            team1_server = quote_name(match.get('team1', {}).get('server', ''))
            team1_partner = quote_name(match.get('team1', {}).get('partner', ''))
            team2_receiver = quote_name(match.get('team2', {}).get('receiver', ''))
            team2_partner = quote_name(match.get('team2', {}).get('partner', ''))
            
            if result_type == 'score':
                # Doubles match format with score: team1_server team1_partner team2_receiver team2_partner score1-score2
                score1 = match.get('score', {}).get('team1', 0)
                score2 = match.get('score', {}).get('team2', 0)
                match_lines.append(f"{team1_server} {team1_partner} {team2_receiver} {team2_partner} {score1}-{score2}")
            else:
                # Doubles match format with win/loss: team1_server team1_partner team2_receiver team2_partner T1/T2
                result_value = match.get('result_value', 'T1')  # Default to T1 if missing
                # Convert old W/L format to T1/T2 if needed
                if result_value == 'W':
                    result_value = 'T1'
                elif result_value == 'L':
                    result_value = 'T2'
                match_lines.append(f"{team1_server} {team1_partner} {team2_receiver} {team2_partner} {result_value}")
    
    return '\n'.join(match_lines)

@app.route('/statistics')
@requires_auth
def statistics():
    """Written by Windsurf
    Display statistics page with various ping pong statistics
    """
    try:
        # Get all statistics
        stats = get_all_statistics()
        return render_template('statistics.html', stats=stats)
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/players')
@requires_auth
def players():
    """Written by Windsurf
    Display player management page
    """
    try:
        # Load players from JSON file
        player_list = load_players()
        return render_template('players.html', players=player_list)
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/add_player', methods=['POST'])
@requires_auth
def add_player():
    """Written by Windsurf
    Add a new player
    """
    try:
        player_name = request.form.get('player_name', '').strip()
        if not player_name:
            flash("Player name cannot be empty", "error")
            return redirect(url_for('players'))
        
        # Load existing players
        player_list = load_players()
        
        # Check if player already exists
        if player_name in player_list:
            flash(f"Player '{player_name}' already exists", "warning")
            return redirect(url_for('players'))
        
        # Add new player
        player_list.append(player_name)
        player_list.sort()  # Sort alphabetically
        
        # Save updated player list
        if save_players(player_list):
            flash(f"Player '{player_name}' added successfully", "success")
        else:
            flash("Failed to save player list", "error")
        
        return redirect(url_for('players'))
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('players'))

@app.route('/delete_player/<player_name>', methods=['POST'])
@requires_auth
def delete_player():
    """Written by Windsurf
    Delete a player
    """
    try:
        player_name = player_name
        player_name = request.form.get('player_name', '').strip()
        if not player_name:
            flash("Player name cannot be empty", "error")
            return redirect(url_for('players'))
        
        # Load existing players
        player_list = load_players()
        
        # Check if player exists
        if player_name not in player_list:
            flash(f"Player '{player_name}' not found", "warning")
            return redirect(url_for('players'))
        
        # Remove player
        player_list.remove(player_name)
        
        # Save updated player list
        if save_players(player_list):
            flash(f"Player '{player_name}' deleted successfully", "success")
        else:
            flash("Failed to save player list", "error")
        
        return redirect(url_for('players'))
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('players'))

@app.route('/get_players', methods=['GET'])
def get_players():
    """Written by Windsurf
    API endpoint to get player list as JSON
    """
    try:
        player_list = load_players()
        return jsonify({"players": player_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_match_details', methods=['GET'])
def get_match_details():
    """Written by Windsurf
    API endpoint to get match details based on different criteria
    """
    try:
        detail_type = request.args.get('type', '')
        detail_id = request.args.get('id', '')
        
        if not detail_type or not detail_id:
            return jsonify({"error": "Missing type or id parameter"}), 400
        
        # Load all match data
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_file = os.path.join(script_dir, "ping_pong_matches.json")
        
        if not os.path.exists(json_file):
            return jsonify({"error": "No match data found"}), 404
            
        with open(json_file, 'r') as f:
            all_data = json.load(f)
        # Build expected probabilities map for this request
        expected_map = get_match_expected_map()
        
        matches = []
        
        # Filter matches based on the requested type and ID
        if detail_type == 'player':
            # Find matches involving the specified player
            player_name = detail_id
            
            for day_data in all_data:
                date = day_data.get('date', '')
                for match in day_data.get('matches', []):
                    match_type = match.get('type', '')
                    
                    if match_type == 'singles':
                        if match.get('player1') == player_name or match.get('player2') == player_name:
                            # Determine winner
                            score1 = match.get('score', {}).get('player1', 0)
                            score2 = match.get('score', {}).get('player2', 0)
                            winner = 'player1' if score1 > score2 else 'player2'
                            
                            # Add match details
                            match_copy = match.copy()
                            match_copy['date'] = date
                            match_copy['winner'] = winner
                            # Attach expected probabilities if available
                            exp = expected_map.get(match.get('id'))
                            if exp and exp.get('type') == 'singles':
                                match_copy['expected'] = {
                                    'p1': round(exp.get('expected_p1', 0) * 100, 1),
                                    'p2': round(exp.get('expected_p2', 0) * 100, 1)
                                }
                            matches.append(match_copy)
                    elif match_type == 'doubles':
                        team1_server = match.get('team1', {}).get('server', '')
                        team1_partner = match.get('team1', {}).get('partner', '')
                        team2_receiver = match.get('team2', {}).get('receiver', '')
                        team2_partner = match.get('team2', {}).get('partner', '')
                        
                        if player_name in [team1_server, team1_partner, team2_receiver, team2_partner]:
                            # Determine winner
                            score1 = match.get('score', {}).get('team1', 0)
                            score2 = match.get('score', {}).get('team2', 0)
                            winner = 'team1' if score1 > score2 else 'team2'
                            
                            # Add match details
                            match_copy = match.copy()
                            match_copy['date'] = date
                            match_copy['winner'] = winner
                            # Attach expected probabilities if available (doubles)
                            exp = expected_map.get(match.get('id'))
                            if exp and exp.get('type') == 'doubles':
                                match_copy['expected'] = {
                                    'team1': round(exp.get('expected_team1', 0) * 100, 1),
                                    'team2': round(exp.get('expected_team2', 0) * 100, 1)
                                }
                            matches.append(match_copy)
        
        elif detail_type == 'team':
            # Find matches with the specified team
            team_key = detail_id
            team_players = team_key.replace("'", "").replace("(", "").replace(")", "").split(",")
            team_players = [p.strip() for p in team_players]
            
            if len(team_players) == 2:
                player1, player2 = team_players
                
                for day_data in all_data:
                    date = day_data.get('date', '')
                    for match in day_data.get('matches', []):
                        if match.get('type') == 'doubles':
                            team1_server = match.get('team1', {}).get('server', '')
                            team1_partner = match.get('team1', {}).get('partner', '')
                            team2_receiver = match.get('team2', {}).get('receiver', '')
                            team2_partner = match.get('team2', {}).get('partner', '')
                            
                            # Check if the team played in this match
                            if ((player1 == team1_server and player2 == team1_partner) or
                                (player2 == team1_server and player1 == team1_partner) or
                                (player1 == team2_receiver and player2 == team2_partner) or
                                (player2 == team2_receiver and player1 == team2_partner)):
                                
                                # Determine winner
                                score1 = match.get('score', {}).get('team1', 0)
                                score2 = match.get('score', {}).get('team2', 0)
                                winner = 'team1' if score1 > score2 else 'team2'
                                
                                # Add match details
                                match_copy = match.copy()
                                match_copy['date'] = date
                                match_copy['winner'] = winner
                                # Attach expected probabilities if available (doubles)
                                exp = expected_map.get(match.get('id'))
                                if exp and exp.get('type') == 'doubles':
                                    match_copy['expected'] = {
                                        'team1': round(exp.get('expected_team1', 0) * 100, 1),
                                        'team2': round(exp.get('expected_team2', 0) * 100, 1)
                                    }
                                matches.append(match_copy)
                            
        elif detail_type == 'headtohead':
            # Find singles matches between two specific players
            # detail_id expected format: "PlayerA>PlayerB"
            try:
                p_left, p_right = detail_id.split('>')
            except ValueError:
                return jsonify({"error": "Invalid headtohead id format. Use 'PlayerA>PlayerB'"}), 400
            target_set = {p_left, p_right}
            for day_data in all_data:
                date = day_data.get('date', '')
                for match in day_data.get('matches', []):
                    if match.get('type') != 'singles':
                        continue
                    m_p1 = match.get('player1', '')
                    m_p2 = match.get('player2', '')
                    if {m_p1, m_p2} != target_set:
                        continue
                    score1 = match.get('score', {}).get('player1', 0)
                    score2 = match.get('score', {}).get('player2', 0)
                    winner = 'player1' if score1 > score2 else 'player2'
                    match_copy = match.copy()
                    match_copy['date'] = date
                    match_copy['winner'] = winner
                    exp = expected_map.get(match.get('id'))
                    if exp and exp.get('type') == 'singles':
                        match_copy['expected'] = {
                            'p1': round(exp.get('expected_p1', 0) * 100, 1),
                            'p2': round(exp.get('expected_p2', 0) * 100, 1)
                        }
                    matches.append(match_copy)

        # Sort matches by date (newest first)
        matches.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return jsonify({"matches": matches})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update_match', methods=['POST'])
def update_match():
    """Written by Windsurf
    API endpoint to update a specific match by ID
    """
    try:
        data = request.get_json()
        match_id = data.get('id')
        
        if not match_id:
            return jsonify({"error": "Match ID is required"}), 400
        
        # Load all match data
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_file = os.path.join(script_dir, "ping_pong_matches.json")
        
        if not os.path.exists(json_file):
            return jsonify({"error": "No match data found"}), 404
            
        with open(json_file, 'r') as f:
            all_data = json.load(f)
        
        # Find and update the match
        match_found = False
        for day_data in all_data:
            for i, match in enumerate(day_data.get('matches', [])):
                if match.get('id') == match_id:
                    # Update match data
                    if 'score' in data:
                        match['score'] = data['score']
                    if 'result_type' in data:
                        match['result_type'] = data['result_type']
                    if 'result_value' in data:
                        match['result_value'] = data['result_value']
                    
                    # Update player/team names if provided
                    if match.get('type') == 'singles':
                        if 'player1' in data:
                            match['player1'] = data['player1']
                        if 'player2' in data:
                            match['player2'] = data['player2']
                    elif match.get('type') == 'doubles':
                        if 'team1' in data:
                            match['team1'] = data['team1']
                        if 'team2' in data:
                            match['team2'] = data['team2']
                    
                    match_found = True
                    break
            if match_found:
                break
        
        if not match_found:
            return jsonify({"error": "Match not found"}), 404
        
        # Save updated data
        with open(json_file, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        return jsonify({"success": True, "message": "Match updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete_match', methods=['POST'])
def delete_match():
    """Written by Windsurf
    API endpoint to delete a specific match by ID
    """
    try:
        data = request.get_json()
        match_id = data.get('id')
        
        if not match_id:
            return jsonify({"error": "Match ID is required"}), 400
        
        # Load all match data
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_file = os.path.join(script_dir, "ping_pong_matches.json")
        
        if not os.path.exists(json_file):
            return jsonify({"error": "No match data found"}), 404
            
        with open(json_file, 'r') as f:
            all_data = json.load(f)
        
        # Find and delete the match
        match_found = False
        for day_data in all_data:
            matches = day_data.get('matches', [])
            for i, match in enumerate(matches):
                if match.get('id') == match_id:
                    matches.pop(i)
                    match_found = True
                    break
            if match_found:
                break
        
        if not match_found:
            return jsonify({"error": "Match not found"}), 404
        
        # Save updated data
        with open(json_file, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        return jsonify({"success": True, "message": "Match deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_match/<match_id>', methods=['GET'])
def get_match(match_id):
    """Written by Windsurf
    API endpoint to get a specific match by ID
    """
    try:
        # Load all match data
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_file = os.path.join(script_dir, "ping_pong_matches.json")
        
        if not os.path.exists(json_file):
            return jsonify({"error": "No match data found"}), 404
            
        with open(json_file, 'r') as f:
            all_data = json.load(f)
        
        # Find the match
        for day_data in all_data:
            for match in day_data.get('matches', []):
                if match.get('id') == match_id:
                    # Add date to match data for context
                    match_with_date = match.copy()
                    match_with_date['date'] = day_data.get('date')
                    return jsonify(match_with_date)
        
        return jsonify({"error": "Match not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(script_dir, "templates")
    os.makedirs(templates_dir, exist_ok=True)
    
    # Configure rate limit headers for debugging
    app.config['RATELIMIT_HEADERS_ENABLED'] = True
    
    # Use port 5000
    app.run(debug=True, port=5000)

#!/usr/bin/env python3
# Written by Windsurf
import json
import re
import shlex
import os
import uuid
from datetime import datetime
from typing import List, Dict, Union, Tuple, Any

def parse_ping_pong_matches(input_text: str) -> Dict[str, Any]:
    """
    Written by Windsurf
    Parse ping pong match data into structured JSON format.
    
    Args:
        input_text: String containing match data with date and match results
        
    Returns:
        Dictionary with parsed match data ready for JSON serialization
    """
    lines = input_text.strip().split('\n')
    
    # Extract date from the first line
    date_str = lines[0]
    try:
        # Validate date format
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date = date_str
    except ValueError:
        # If first line isn't a valid date, use current date
        date = datetime.now().strftime("%Y-%m-%d")
        # Put the first line back as it might be a match
        lines = [date] + lines
    
    matches = []
    
    # Process each match line
    for i, line in enumerate(lines[1:], 1):
        # Use shlex to support quoted names with spaces (e.g., "John Smith")
        parts = shlex.split(line.strip())
        
        # Check if we have enough parts for a valid match
        if len(parts) < 3:  # Need at least 2 players/teams + result
            continue
        
        # Extract result from the end of the line
        result_part = parts[-1]
        
        # Check if it's a score format (e.g., 21-18)
        score_match = re.match(r'(\d+)-(\d+)', result_part)
        
        # Check if it's a win/loss format (P1/P2 for singles, T1/T2 for doubles)
        win_loss_match = re.match(r'[WwLlPpTt][12]?', result_part)
        
        if score_match:
            # Score format
            team1_score = int(score_match.group(1))
            team2_score = int(score_match.group(2))
            # Remove score from parts
            parts = parts[:-1]
            
            # Check if this is a 1-0 or 0-1 score (win/loss indicator)
            if (team1_score == 1 and team2_score == 0) or (team1_score == 0 and team2_score == 1):
                # This is a win/loss indicator
                result_type = "winloss"
                result_value = "W" if team1_score > team2_score else "L"
            else:
                # This is a real score
                result_type = "score"
        elif win_loss_match:
            # Win/Loss format with player/team selection
            win_indicator = result_part.upper()
            result_type = "winloss"
            result_value = win_indicator
            
            # Set placeholder scores for determining winner
            if win_indicator in ['W', 'P1', 'T1']:
                # Player 1 or Team 1 won
                team1_score = 1
                team2_score = 0
            else:  # 'L', 'P2', 'T2'
                # Player 2 or Team 2 won
                team1_score = 0
                team2_score = 1
            
            # Remove win/loss indicator from parts
            parts = parts[:-1]
        else:
            # Invalid format
            continue
        
        match_data = {}
        
        if len(parts) == 2:
            # Singles match
            match_data = {
                "id": str(uuid.uuid4()),
                "type": "singles",
                "player1": parts[0],
                "player2": parts[1],
                "score": {
                    "player1": team1_score,
                    "player2": team2_score
                },
                "result_type": result_type
            }
            
            # Add result_value for win/loss entries
            if result_type == "winloss":
                match_data["result_value"] = result_value
        elif len(parts) == 4:
            # Doubles match
            match_data = {
                "id": str(uuid.uuid4()),
                "type": "doubles",
                "team1": {
                    "server": parts[0],
                    "partner": parts[1]
                },
                "team2": {
                    "receiver": parts[2],
                    "partner": parts[3]
                },
                "score": {
                    "team1": team1_score,
                    "team2": team2_score
                },
                "result_type": result_type
            }
            
            # Add result_value for win/loss entries
            if result_type == "winloss":
                match_data["result_value"] = result_value
        else:
            # Invalid format
            continue
            
        matches.append(match_data)
    
    return {
        "date": date,
        "matches": matches
    }

def main():
    """Written by Windsurf"""
    import sys
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Parse ping pong match data into JSON')
    parser.add_argument('-f', '--file', help='Input file containing match data (default: ping_pong_day.txt)')
    parser.add_argument('-o', '--output', help='Output JSON file name (default: ping_pong_matches.json)')
    args = parser.parse_args()
    
    # Get script directory for file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Default to ping_pong_day.txt if no file specified
    input_file = args.file if args.file else os.path.join(script_dir, "ping_pong_day.txt")
    
    # Read from file
    try:
        with open(input_file, 'r') as f:
            input_text = f.read()
        print(f"Reading match data from {input_file}")
    except FileNotFoundError:
        print(f"Error: File {input_file} not found")
        print("Using example data instead...")
        input_text = """2025-09-03
conner ridzky carson ryan 21-18
carson ryan conner ridzky 21-16
carson ryan conner ridzky 18-21
carson conner 17-21"""
    
    # Parse the input
    result = parse_ping_pong_matches(input_text)
    
    # Get script directory for saving the file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = args.output if args.output else os.path.join(script_dir, "ping_pong_matches.json")
    
    # Ensure output_file has absolute path if not already
    if not os.path.isabs(output_file):
        output_file = os.path.join(script_dir, output_file)
    
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
    
    # Append new data to existing data
    existing_data.append(result)
    
    # Save to JSON file
    with open(output_file, 'w') as f:
        json.dump(existing_data, f, indent=2)
    
    print(f"\nParsed data saved to: {output_file}")
    print("\nJSON Output Preview (latest entry):")
    print(json.dumps(result, indent=2))
    print(f"\nTotal entries in JSON file: {len(existing_data)}")

if __name__ == "__main__":
    main()

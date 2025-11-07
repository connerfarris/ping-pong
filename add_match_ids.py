#!/usr/bin/env python3
# Written by Windsurf
"""
Migration script to add unique IDs to existing matches in ping_pong_matches.json
"""
import json
import uuid
import os

def add_ids_to_matches():
    """Written by Windsurf
    Add unique IDs to all existing matches that don't have them
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, "ping_pong_matches.json")
    
    if not os.path.exists(json_file):
        print(f"File {json_file} not found")
        return
    
    # Load existing data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    matches_updated = 0
    
    # Process each day's data
    for day_data in data:
        matches = day_data.get('matches', [])
        
        for match in matches:
            # Add ID if it doesn't exist
            if 'id' not in match:
                match['id'] = str(uuid.uuid4())
                matches_updated += 1
    
    # Save updated data
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Migration complete! Added IDs to {matches_updated} matches.")
    print(f"Updated file: {json_file}")

if __name__ == "__main__":
    add_ids_to_matches()

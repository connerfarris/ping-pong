#!/usr/bin/env python3
# Written by Windsurf
import json
import os
from collections import defaultdict, Counter
from datetime import datetime
import statistics

def load_match_data():
    """
    Load all match data from the JSON file
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, "ping_pong_matches.json")
    
    if not os.path.exists(json_file):
        return []
        
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def get_player_stats(data):
    """
    Calculate player statistics
    """
    players = set()
    player_stats = defaultdict(lambda: {
        'singles_played': 0,
        'singles_won': 0,
        'doubles_played': 0,
        'doubles_won': 0,
        'total_played': 0,
        'total_won': 0,
        'points_scored': 0,
        'points_conceded': 0,
        'avg_score_in_wins': 0,
        'avg_score_in_losses': 0,
        'win_streak': 0,
        'current_streak': 0,
        'best_streak': 0
    })
    
    # First pass to collect all players
    for day_data in data:
        for match in day_data.get('matches', []):
            if match.get('type') == 'singles':
                players.add(match.get('player1', ''))
                players.add(match.get('player2', ''))
            elif match.get('type') == 'doubles':
                players.add(match.get('team1', {}).get('server', ''))
                players.add(match.get('team1', {}).get('partner', ''))
                players.add(match.get('team2', {}).get('receiver', ''))
                players.add(match.get('team2', {}).get('partner', ''))
    
    # Also include registered players from players.json so they appear even with zero matches
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        players_file = os.path.join(script_dir, "players.json")
        if os.path.exists(players_file):
            with open(players_file, 'r') as f:
                pdata = json.load(f)
                players.update(pdata.get('players', []))
    except Exception:
        pass
    
    # Remove empty strings
    players.discard('')
    
    # Pre-initialize stats entries so players with zero matches still appear
    for p in players:
        _ = player_stats[p]
    
    # Second pass to calculate stats
    for day_data in data:
        for match in day_data.get('matches', []):
            if match.get('type') == 'singles':
                player1 = match.get('player1', '')
                player2 = match.get('player2', '')
                score1 = match.get('score', {}).get('player1', 0)
                score2 = match.get('score', {}).get('player2', 0)
                result_type = match.get('result_type', 'score')  # Default to 'score' for backward compatibility
                
                # Update singles stats
                if player1 and player2:
                    # Player 1 stats
                    player_stats[player1]['singles_played'] += 1
                    player_stats[player1]['total_played'] += 1
                    
                    # Player 2 stats
                    player_stats[player2]['singles_played'] += 1
                    player_stats[player2]['total_played'] += 1
                    
                    # Only update score-related stats if it's a real score
                    if result_type == 'score':
                        player_stats[player1]['points_scored'] += score1
                        player_stats[player1]['points_conceded'] += score2
                        player_stats[player2]['points_scored'] += score2
                        player_stats[player2]['points_conceded'] += score1
                    
                    # Determine winner
                    if score1 > score2:
                        player_stats[player1]['singles_won'] += 1
                        player_stats[player1]['total_won'] += 1
                        update_streak(player_stats[player1], True)
                        update_streak(player_stats[player2], False)
                    else:
                        player_stats[player2]['singles_won'] += 1
                        player_stats[player2]['total_won'] += 1
                        update_streak(player_stats[player2], True)
                        update_streak(player_stats[player1], False)
            
            elif match.get('type') == 'doubles':
                team1_server = match.get('team1', {}).get('server', '')
                team1_partner = match.get('team1', {}).get('partner', '')
                team2_receiver = match.get('team2', {}).get('receiver', '')
                team2_partner = match.get('team2', {}).get('partner', '')
                score1 = match.get('score', {}).get('team1', 0)
                score2 = match.get('score', {}).get('team2', 0)
                result_type = match.get('result_type', 'score')  # Default to 'score' for backward compatibility
                
                # Update doubles stats
                if team1_server and team1_partner and team2_receiver and team2_partner:
                    # Team 1 stats - always update match counts
                    player_stats[team1_server]['doubles_played'] += 1
                    player_stats[team1_server]['total_played'] += 1
                    
                    player_stats[team1_partner]['doubles_played'] += 1
                    player_stats[team1_partner]['total_played'] += 1
                    
                    # Team 2 stats - always update match counts
                    player_stats[team2_receiver]['doubles_played'] += 1
                    player_stats[team2_receiver]['total_played'] += 1
                    
                    player_stats[team2_partner]['doubles_played'] += 1
                    player_stats[team2_partner]['total_played'] += 1
                    
                    # Only update score-related stats if it's a real score
                    if result_type == 'score':
                        # Team 1 score stats
                        player_stats[team1_server]['points_scored'] += score1
                        player_stats[team1_server]['points_conceded'] += score2
                        player_stats[team1_partner]['points_scored'] += score1
                        player_stats[team1_partner]['points_conceded'] += score2
                        
                        # Team 2 score stats
                        player_stats[team2_receiver]['points_scored'] += score2
                        player_stats[team2_receiver]['points_conceded'] += score1
                        player_stats[team2_partner]['points_scored'] += score2
                        player_stats[team2_partner]['points_conceded'] += score1
                    
                    # Determine winner and update win stats
                    if score1 > score2:
                        # Team 1 won
                        for player in [team1_server, team1_partner]:
                            if player:
                                player_stats[player]['doubles_won'] += 1
                                player_stats[player]['total_won'] += 1
                                update_streak(player_stats[player], True)
                        
                        # Team 2 lost
                        for player in [team2_receiver, team2_partner]:
                            if player:
                                update_streak(player_stats[player], False)
                    else:
                        # Team 2 won
                        for player in [team2_receiver, team2_partner]:
                            if player:
                                player_stats[player]['doubles_won'] += 1
                                player_stats[player]['total_won'] += 1
                                update_streak(player_stats[player], True)
                        
                        # Team 1 lost
                        for player in [team1_server, team1_partner]:
                            if player:
                                update_streak(player_stats[player], False)
    
    # Calculate derived stats
    for player, stats in player_stats.items():
        # Overall win percentage
        total_played = stats['total_played']
        if total_played > 0:
            stats['win_percentage'] = round((stats['total_won'] / total_played) * 100, 1)
        else:
            stats['win_percentage'] = 0
        
        # Singles win percentage
        if stats['singles_played'] > 0:
            stats['singles_win_percentage'] = round((stats['singles_won'] / stats['singles_played']) * 100, 1)
        else:
            stats['singles_win_percentage'] = 0
        
        # Doubles win percentage
        if stats['doubles_played'] > 0:
            stats['doubles_win_percentage'] = round((stats['doubles_won'] / stats['doubles_played']) * 100, 1)
        else:
            stats['doubles_win_percentage'] = 0
        
        # Finalize best streak
        stats['best_streak'] = max(stats['best_streak'], stats['current_streak'])
    
    return dict(player_stats)

def update_streak(player_stats, won):
    """Helper function to update winning/losing streaks"""
    if won:
        player_stats['current_streak'] = max(1, player_stats['current_streak'] + 1)
        player_stats['best_streak'] = max(player_stats['best_streak'], player_stats['current_streak'])
    else:
        player_stats['current_streak'] = min(-1, player_stats['current_streak'] - 1)

def get_match_analytics(data):
    """
    Calculate match analytics
    """
    total_singles = 0
    total_doubles = 0
    score_differences = []
    matchups = []
    dates = []
    
    for day_data in data:
        date = day_data.get('date', '')
        if date:
            dates.append(date)
        
        for match in day_data.get('matches', []):
            # Check if this is a real score or just win/loss
            result_type = match.get('result_type', 'score')  # Default to 'score' for backward compatibility
            
            if match.get('type') == 'singles':
                total_singles += 1
                player1 = match.get('player1', '')
                player2 = match.get('player2', '')
                score1 = match.get('score', {}).get('player1', 0)
                score2 = match.get('score', {}).get('player2', 0)
                
                if player1 and player2:
                    # Sort players alphabetically for consistent matchup tracking
                    matchup = tuple(sorted([player1, player2]))
                    matchups.append(matchup)
                
                # Only include score differences for real scores
                if score1 and score2 and result_type == "score":
                    score_differences.append(abs(score1 - score2))
            
            elif match.get('type') == 'doubles':
                total_doubles += 1
                team1_server = match.get('team1', {}).get('server', '')
                team1_partner = match.get('team1', {}).get('partner', '')
                team2_receiver = match.get('team2', {}).get('receiver', '')
                team2_partner = match.get('team2', {}).get('partner', '')
                score1 = match.get('score', {}).get('team1', 0)
                score2 = match.get('score', {}).get('team2', 0)
                
                if team1_server and team1_partner and team2_receiver and team2_partner:
                    # Sort teams for consistent matchup tracking
                    team1 = tuple(sorted([team1_server, team1_partner]))
                    team2 = tuple(sorted([team2_receiver, team2_partner]))
                    matchup = (team1, team2)
                    matchups.append(matchup)
                
                # Only include score differences for real scores
                if score1 and score2 and result_type == "score":
                    score_differences.append(abs(score1 - score2))
    
    # Calculate statistics
    avg_score_diff = round(sum(score_differences) / len(score_differences), 1) if score_differences else 0
    common_matchups = Counter(matchups).most_common(5)
    
    # Process dates for day of week frequency
    day_of_week_counts = defaultdict(int)
    for date_str in dates:
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            day_name = date_obj.strftime("%A")
            day_of_week_counts[day_name] += 1
        except ValueError:
            pass
    
    return {
        'total_matches': total_singles + total_doubles,
        'singles_matches': total_singles,
        'doubles_matches': total_doubles,
        'avg_score_difference': avg_score_diff,
        'common_matchups': common_matchups,
        'day_frequency': dict(day_of_week_counts)
    }

def get_team_dynamics(data):
    """
    Calculate team dynamics for doubles matches
    """
    partnerships = defaultdict(lambda: {
        'played': 0,
        'won': 0,
        'points_scored': 0,
        'points_conceded': 0,
        'score_matches': 0
    })
    
    for day_data in data:
        for match in day_data.get('matches', []):
            if match.get('type') == 'doubles':
                team1_server = match.get('team1', {}).get('server', '')
                team1_partner = match.get('team1', {}).get('partner', '')
                team2_receiver = match.get('team2', {}).get('receiver', '')
                team2_partner = match.get('team2', {}).get('partner', '')
                score1 = match.get('score', {}).get('team1', 0)
                score2 = match.get('score', {}).get('team2', 0)
                result_type = match.get('result_type', 'score')
                
                # Create partnership keys (sorted for consistency)
                team1 = tuple(sorted([team1_server, team1_partner]))
                team2 = tuple(sorted([team2_receiver, team2_partner]))
                
                # Skip if any player is missing
                if '' in team1 or '' in team2:
                    continue
                
                # Update partnership stats
                partnerships[team1]['played'] += 1
                # Only include real score matches in points (exclude win/loss only)
                if result_type == 'score':
                    partnerships[team1]['points_scored'] += score1
                    partnerships[team1]['points_conceded'] += score2
                    partnerships[team1]['score_matches'] += 1
                
                partnerships[team2]['played'] += 1
                if result_type == 'score':
                    partnerships[team2]['points_scored'] += score2
                    partnerships[team2]['points_conceded'] += score1
                    partnerships[team2]['score_matches'] += 1
                
                # Update wins
                if score1 > score2:
                    partnerships[team1]['won'] += 1
                else:
                    partnerships[team2]['won'] += 1
    
    # Calculate win rates and point differential metrics
    for team, stats in partnerships.items():
        if stats['played'] > 0:
            stats['win_rate'] = round((stats['won'] / stats['played']) * 100, 1)
        else:
            stats['win_rate'] = 0
        # Add point differential, based only on accumulated points from real score matches
        stats['point_diff'] = stats['points_scored'] - stats['points_conceded']
        # Add point differential per game (only considering score-based matches)
        sm = stats.get('score_matches', 0)
        stats['point_diff_per_game'] = round(stats['point_diff'] / sm, 2) if sm > 0 else 0
    
    # Convert to regular dict for easier serialization
    return {str(k): v for k, v in partnerships.items()}

def get_score_patterns(data):
    """
    Written by Windsurf
    Analyze score patterns and distributions
    """
    all_scores = []
    score_differences = []
    closest_matches = []
    decisive_victories = []
    
    for day_data in data:
        date = day_data.get('date', '')
        for match in day_data.get('matches', []):
            # Skip matches that don't have real scores (win/loss only)
            result_type = match.get('result_type', 'score')  # Default to 'score' for backward compatibility
            if result_type != 'score':
                continue
                
            if match.get('type') == 'singles':
                score1 = match.get('score', {}).get('player1', 0)
                score2 = match.get('score', {}).get('player2', 0)
                player1 = match.get('player1', '')
                player2 = match.get('player2', '')
                
                all_scores.extend([score1, score2])
                diff = abs(score1 - score2)
                score_differences.append(diff)
                
                match_info = {
                    'date': date,
                    'type': 'singles',
                    'player1': player1,
                    'player2': player2,
                    'score': f"{score1}-{score2}",
                    'difference': diff
                }
                
                if diff <= 2:  # Close match
                    closest_matches.append(match_info)
                elif diff >= 10:  # Decisive victory
                    decisive_victories.append(match_info)
    
    # Sort for closest matches and most decisive victories
    closest_matches.sort(key=lambda x: x['difference'])
    decisive_victories.sort(key=lambda x: x['difference'], reverse=True)
    
    # Calculate statistics
    avg_points = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    
    try:
        median_diff = statistics.median(score_differences) if score_differences else 0
    except statistics.StatisticsError:
        median_diff = 0
    
    # Score distribution
    score_distribution = Counter(all_scores)
    
    return {
        'avg_points_per_player': avg_points,
        'median_score_difference': median_diff,
        'closest_matches': closest_matches[:5],  # Top 5 closest matches
        'decisive_victories': decisive_victories[:5],  # Top 5 most decisive victories
        'score_distribution': dict(score_distribution)
    }

def get_temporal_analysis(data):
    """
    Analyze performance trends over time
    """
    matches_by_date = defaultdict(int)
    points_by_date = defaultdict(int)
    
    for day_data in data:
        date = day_data.get('date', '')
        if not date:
            continue
        
        match_count = len(day_data.get('matches', []))
        matches_by_date[date] = match_count
        
        # Count total points scored on this date
        total_points = 0
        for match in day_data.get('matches', []):
            if match.get('type') == 'singles':
                total_points += match.get('score', {}).get('player1', 0)
                total_points += match.get('score', {}).get('player2', 0)
            elif match.get('type') == 'doubles':
                total_points += match.get('score', {}).get('team1', 0)
                total_points += match.get('score', {}).get('team2', 0)
        
        points_by_date[date] = total_points
    
    # Sort by date
    sorted_dates = sorted(matches_by_date.keys())
    
    # Create time series data
    time_series = {
        'dates': sorted_dates,
        'match_counts': [matches_by_date[date] for date in sorted_dates],
        'point_counts': [points_by_date[date] for date in sorted_dates]
    }
    
    # Find most active day
    most_active_date = max(matches_by_date.items(), key=lambda x: x[1])[0] if matches_by_date else None
    
    return {
        'time_series': time_series,
        'most_active_date': most_active_date,
        'matches_by_date': dict(matches_by_date)
    }

def get_doubles_serving_stats(data):
    """
    Written by Windsurf
    Calculate statistics for doubles serving rotations.
    """
    # Track server-receiver pairs by specific players
    player_pairs = {}
    
    # Track matches with the same 4 players but different serving arrangements
    match_groups = {}
    
    for day_data in data:
        for match in day_data.get('matches', []):
            if match.get('type') == 'doubles':
                team1_server = match.get('team1', {}).get('server', '')
                team1_partner = match.get('team1', {}).get('partner', '')
                team2_receiver = match.get('team2', {}).get('receiver', '')
                team2_partner = match.get('team2', {}).get('partner', '')
                score1 = match.get('score', {}).get('team1', 0)
                score2 = match.get('score', {}).get('team2', 0)
                result_type = match.get('result_type', 'score')  # Default to 'score' for backward compatibility
                
                # Skip if any player is missing
                if not team1_server or not team1_partner or not team2_receiver or not team2_partner:
                    continue
                    
                # Skip win/loss matches for serving rotation statistics
                if result_type != 'score':
                    continue
                
                # Determine if team1 won
                team1_won = score1 > score2
                
                # Create a key for the match group (all 4 players, sorted alphabetically)
                all_players = sorted([team1_server, team1_partner, team2_receiver, team2_partner])
                match_group_key = ",".join(all_players)
                
                # Initialize match group if needed
                if match_group_key not in match_groups:
                    match_groups[match_group_key] = {'matches': 0, 'configurations': {}}
                
                # Update match group stats
                match_groups[match_group_key]['matches'] += 1
                
                # Create normalized team keys (sort players within each team)
                t1_pair = tuple(sorted([team1_server, team1_partner]))
                t2_pair = tuple(sorted([team2_receiver, team2_partner]))
                
                # Normalize configuration as a combination: sort the two pairs so side/order doesn't matter
                if t1_pair <= t2_pair:
                    left_pair, right_pair = t1_pair, t2_pair
                    left_won = team1_won
                else:
                    left_pair, right_pair = t2_pair, t1_pair
                    left_won = not team1_won
                
                config_key = f"{left_pair[0]},{left_pair[1]},{right_pair[0]},{right_pair[1]}"
                
                # Initialize configuration if needed
                if config_key not in match_groups[match_group_key]['configurations']:
                    match_groups[match_group_key]['configurations'][config_key] = {'matches': 0, 'wins': 0, 'win_rate': 0}
                
                # Update totals; 'wins' tracks wins for the left (normalized) pair
                match_groups[match_group_key]['configurations'][config_key]['matches'] += 1
                if left_won:
                    match_groups[match_group_key]['configurations'][config_key]['wins'] += 1
                
                # Track individual player serving stats
                if team1_server not in player_pairs:
                    player_pairs[team1_server] = {}
                if team2_receiver not in player_pairs[team1_server]:
                    player_pairs[team1_server][team2_receiver] = {'matches': 0, 'wins': 0, 'win_rate': 0}
                
                player_pairs[team1_server][team2_receiver]['matches'] += 1
                if team1_won:
                    player_pairs[team1_server][team2_receiver]['wins'] += 1
                
                if team2_receiver not in player_pairs:
                    player_pairs[team2_receiver] = {}
                if team1_partner not in player_pairs[team2_receiver]:
                    player_pairs[team2_receiver][team1_partner] = {'matches': 0, 'wins': 0, 'win_rate': 0}
                
                player_pairs[team2_receiver][team1_partner]['matches'] += 1
                if not team1_won:
                    player_pairs[team2_receiver][team1_partner]['wins'] += 1
                
                if team1_partner not in player_pairs:
                    player_pairs[team1_partner] = {}
                if team2_partner not in player_pairs[team1_partner]:
                    player_pairs[team1_partner][team2_partner] = {'matches': 0, 'wins': 0, 'win_rate': 0}
                
                player_pairs[team1_partner][team2_partner]['matches'] += 1
                if team1_won:
                    player_pairs[team1_partner][team2_partner]['wins'] += 1
                
                if team2_partner not in player_pairs:
                    player_pairs[team2_partner] = {}
                if team1_server not in player_pairs[team2_partner]:
                    player_pairs[team2_partner][team1_server] = {'matches': 0, 'wins': 0, 'win_rate': 0}
                
                player_pairs[team2_partner][team1_server]['matches'] += 1
                if not team1_won:
                    player_pairs[team2_partner][team1_server]['wins'] += 1
    
    # Calculate win rates for player pairs
    for server, receivers in player_pairs.items():
        for receiver, stats in receivers.items():
            if stats['matches'] > 0:
                stats['win_rate'] = round((stats['wins'] / stats['matches']) * 100, 1)
    
    # Calculate win rates for match group configurations
    for group_key, group_stats in match_groups.items():
        for config_key, config_stats in group_stats['configurations'].items():
            if config_stats['matches'] > 0:
                config_stats['win_rate'] = round((config_stats['wins'] / config_stats['matches']) * 100, 1)
    
    return {
        'player_pairs': player_pairs,
        'match_groups': match_groups
    }

def get_head_to_head_singles(data):
    """
    Written by Windsurf
    Compute head-to-head records for singles matches.
    Returns a dict keyed by "P1>P2" (alphabetical order), with values:
    {
      'p1': P1,
      'p2': P2,
      'matches': int,
      'wins_p1': int,
      'wins_p2': int,
      'win_rate_p1': float,
      'win_rate_p2': float
    }
    """
    from collections import defaultdict
    records = defaultdict(lambda: {'p1': '', 'p2': '', 'matches': 0, 'wins_p1': 0, 'wins_p2': 0, 'win_rate_p1': 0.0, 'win_rate_p2': 0.0})
    
    for day_data in data:
        for match in day_data.get('matches', []):
            if match.get('type') != 'singles':
                continue
            p1 = match.get('player1', '')
            p2 = match.get('player2', '')
            if not p1 or not p2:
                continue
            s1 = match.get('score', {}).get('player1', 0)
            s2 = match.get('score', {}).get('player2', 0)
            # Normalize pair ordering alphabetically for the key
            a, b = sorted([p1, p2])
            key = f"{a}>{b}"
            rec = records[key]
            rec['p1'] = a
            rec['p2'] = b
            rec['matches'] += 1
            # Determine winner by score
            if s1 == s2:
                # In case of malformed data, ignore ties for wins tally
                continue
            # Map score winner to normalized p1/p2
            actual_winner = p1 if s1 > s2 else p2
            if actual_winner == a:
                rec['wins_p1'] += 1
            else:
                rec['wins_p2'] += 1
    
    # Compute win rates
    for rec in records.values():
        if rec['matches'] > 0:
            rec['win_rate_p1'] = round((rec['wins_p1'] / rec['matches']) * 100, 1)
            rec['win_rate_p2'] = round((rec['wins_p2'] / rec['matches']) * 100, 1)
        else:
            rec['win_rate_p1'] = 0.0
            rec['win_rate_p2'] = 0.0
    
    return dict(records)

def get_total_points_stat(data):
    """
    Calculate total points scored across all players from score-based matches
    """
    total_points = 0
    
    for day_data in data:
        for match in day_data.get('matches', []):
            result_type = match.get('result_type', 'score')
            
            # Only count points from actual scores, not win/loss matches
            if result_type == 'score':
                if match.get('type') == 'singles':
                    score1 = match.get('score', {}).get('player1', 0)
                    score2 = match.get('score', {}).get('player2', 0)
                    total_points += score1 + score2
                elif match.get('type') == 'doubles':
                    score1 = match.get('score', {}).get('team1', 0)
                    score2 = match.get('score', {}).get('team2', 0)
                    # In doubles, each point is scored by a team, so we count it once
                    total_points += score1 + score2
    
    return total_points

def get_match_expected_map():
    """
    Written by Windsurf
    Compute Elo-style expected win probabilities for each match.
    Returns a dict mapping match id -> expected probabilities.
    Singles entries have keys: 'type': 'singles', 'expected_p1', 'expected_p2'.
    Doubles entries have keys: 'type': 'doubles', 'expected_team1', 'expected_team2'.
    """
    data = load_match_data()
    ratings = {}
    K = 24
    expected_map = {}
    # Collect matches with dates for chronological processing
    chron = []
    for day_data in data:
        date = day_data.get('date', '')
        for match in day_data.get('matches', []):
            chron.append((date, match))
    # Sort by date ascending (unknown dates last)
    def _key(item):
        d, _ = item
        try:
            return datetime.strptime(d, "%Y-%m-%d")
        except Exception:
            return datetime.max
    chron.sort(key=_key)
    # Helper for Elo expectation
    def expect(r_a, r_b):
        return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400.0))
    # Iterate matches, compute expected, then update ratings
    for _, m in chron:
        mtype = m.get('type')
        mid = m.get('id')
        if not mid:
            continue
        rtype = m.get('result_type', 'score')
        if mtype == 'singles':
            p1 = m.get('player1', '')
            p2 = m.get('player2', '')
            if not p1 or not p2:
                continue
            r1 = ratings.get(p1, 1500.0)
            r2 = ratings.get(p2, 1500.0)
            e1 = expect(r1, r2)
            e2 = 1.0 - e1
            expected_map[mid] = {'type': 'singles', 'expected_p1': e1, 'expected_p2': e2}
            # Determine result
            if rtype == 'score':
                s1 = m.get('score', {}).get('player1', 0)
                s2 = m.get('score', {}).get('player2', 0)
                res1 = 1.0 if s1 > s2 else 0.0
            else:
                rv = str(m.get('result_value', '')).upper()
                # 'W' means player1 win, 'L' player2 win; also support 'P1'/'P2'
                if rv in ('W', 'P1'):
                    res1 = 1.0
                elif rv in ('L', 'P2'):
                    res1 = 0.0
                else:
                    # Unknown, skip rating update
                    continue
            # Update ratings
            delta = K * (res1 - e1)
            ratings[p1] = r1 + delta
            ratings[p2] = r2 - delta
        elif mtype == 'doubles':
            t1s = m.get('team1', {}).get('server', '')
            t1p = m.get('team1', {}).get('partner', '')
            t2r = m.get('team2', {}).get('receiver', '')
            t2p = m.get('team2', {}).get('partner', '')
            if not t1s or not t1p or not t2r or not t2p:
                continue
            r_t1 = (ratings.get(t1s, 1500.0) + ratings.get(t1p, 1500.0)) / 2.0
            r_t2 = (ratings.get(t2r, 1500.0) + ratings.get(t2p, 1500.0)) / 2.0
            e1 = expect(r_t1, r_t2)
            e2 = 1.0 - e1
            expected_map[mid] = {'type': 'doubles', 'expected_team1': e1, 'expected_team2': e2}
            # Determine result
            if rtype == 'score':
                s1 = m.get('score', {}).get('team1', 0)
                s2 = m.get('score', {}).get('team2', 0)
                res1 = 1.0 if s1 > s2 else 0.0
            else:
                rv = str(m.get('result_value', '')).upper()
                if rv in ('T1', 'W'):
                    res1 = 1.0
                elif rv in ('T2', 'L'):
                    res1 = 0.0
                else:
                    continue
            # Update each player's rating equally by team delta
            # Convert team delta to per-player delta (apply same delta to both players on a team)
            # We treat team ratings as the average, so each player gets the same delta
            r1s = ratings.get(t1s, 1500.0)
            r1p = ratings.get(t1p, 1500.0)
            r2r = ratings.get(t2r, 1500.0)
            r2p = ratings.get(t2p, 1500.0)
            delta_team = K * (res1 - e1)
            ratings[t1s] = r1s + delta_team
            ratings[t1p] = r1p + delta_team
            ratings[t2r] = r2r - delta_team
            ratings[t2p] = r2p - delta_team
        else:
            continue
    return expected_map

def get_elo_ratings_and_history():
    """
    Written by Windsurf
    Compute Elo ratings and per-player rating history over time.
    Returns {
      'current_ratings': {player: float},
      'history': {player: [{'date': 'YYYY-MM-DD', 'rating': float}, ...]}
    }
    """
    data = load_match_data()
    K = 24
    MIN_MATCHES = 3
    # Per-mode containers
    modes = ['overall', 'singles', 'doubles']
    ratings = {m: {} for m in modes}
    matches_played = {m: defaultdict(int) for m in modes}
    daily_history = {m: defaultdict(list) for m in modes}
    # Group matches by date
    matches_by_date = defaultdict(list)
    for day_data in data:
        date = day_data.get('date', '')
        for match in day_data.get('matches', []):
            matches_by_date[date].append(match)
    # Sort dates
    def try_parse_date(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d")
        except Exception:
            return None
    sorted_dates = sorted([d for d in matches_by_date.keys() if d], key=lambda x: datetime.strptime(x, "%Y-%m-%d"))
    # Helpers
    def get_r(mode, player):
        return ratings[mode].get(player, 1500.0)
    def set_r(mode, player, r):
        ratings[mode][player] = r
    def expect(r_a, r_b):
        return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400.0))
    # Process day by day
    for date in sorted_dates:
        for m in matches_by_date[date]:
            mtype = m.get('type')
            rtype = m.get('result_type', 'score')
            if mtype == 'singles':
                p1 = m.get('player1', '')
                p2 = m.get('player2', '')
                if not p1 or not p2:
                    continue
                r1 = get_r('overall', p1)
                r2 = get_r('overall', p2)
                e1 = expect(r1, r2)
                if rtype == 'score':
                    s1 = m.get('score', {}).get('player1', 0)
                    s2 = m.get('score', {}).get('player2', 0)
                    res1 = 1.0 if s1 > s2 else 0.0
                else:
                    rv = str(m.get('result_value', '')).upper()
                    if rv in ('W', 'P1'):
                        res1 = 1.0
                    elif rv in ('L', 'P2'):
                        res1 = 0.0
                    else:
                        continue
                delta = K * (res1 - e1)
                # Update overall
                set_r('overall', p1, r1 + delta)
                set_r('overall', p2, r2 - delta)
                matches_played['overall'][p1] += 1
                matches_played['overall'][p2] += 1
                # Update singles-only Elo independently
                r1s = get_r('singles', p1)
                r2s = get_r('singles', p2)
                e1s = expect(r1s, r2s)
                deltas = K * (res1 - e1s)
                set_r('singles', p1, r1s + deltas)
                set_r('singles', p2, r2s - deltas)
                matches_played['singles'][p1] += 1
                matches_played['singles'][p2] += 1
            elif mtype == 'doubles':
                t1s = m.get('team1', {}).get('server', '')
                t1p = m.get('team1', {}).get('partner', '')
                t2r = m.get('team2', {}).get('receiver', '')
                t2p = m.get('team2', {}).get('partner', '')
                if not t1s or not t1p or not t2r or not t2p:
                    continue
                r_t1 = (get_r('overall', t1s) + get_r('overall', t1p)) / 2.0
                r_t2 = (get_r('overall', t2r) + get_r('overall', t2p)) / 2.0
                e1 = expect(r_t1, r_t2)
                if rtype == 'score':
                    s1 = m.get('score', {}).get('team1', 0)
                    s2 = m.get('score', {}).get('team2', 0)
                    res1 = 1.0 if s1 > s2 else 0.0
                else:
                    rv = str(m.get('result_value', '')).upper()
                    if rv in ('T1', 'W'):
                        res1 = 1.0
                    elif rv in ('T2', 'L'):
                        res1 = 0.0
                    else:
                        continue
                delta_team = K * (res1 - e1)
                # Update overall per-player
                set_r('overall', t1s, get_r('overall', t1s) + delta_team)
                set_r('overall', t1p, get_r('overall', t1p) + delta_team)
                set_r('overall', t2r, get_r('overall', t2r) - delta_team)
                set_r('overall', t2p, get_r('overall', t2p) - delta_team)
                matches_played['overall'][t1s] += 1
                matches_played['overall'][t1p] += 1
                matches_played['overall'][t2r] += 1
                matches_played['overall'][t2p] += 1
                # Update doubles-only Elo independently (team average expectation computed from doubles-only ratings)
                r_t1d = (get_r('doubles', t1s) + get_r('doubles', t1p)) / 2.0
                r_t2d = (get_r('doubles', t2r) + get_r('doubles', t2p)) / 2.0
                e1d = expect(r_t1d, r_t2d)
                delta_team_d = K * (res1 - e1d)
                set_r('doubles', t1s, get_r('doubles', t1s) + delta_team_d)
                set_r('doubles', t1p, get_r('doubles', t1p) + delta_team_d)
                set_r('doubles', t2r, get_r('doubles', t2r) - delta_team_d)
                set_r('doubles', t2p, get_r('doubles', t2p) - delta_team_d)
                matches_played['doubles'][t1s] += 1
                matches_played['doubles'][t1p] += 1
                matches_played['doubles'][t2r] += 1
                matches_played['doubles'][t2p] += 1
        # End of day: record each eligible player's rating as of this date
        for mode in modes:
            for p, r in ratings[mode].items():
                if matches_played[mode][p] >= MIN_MATCHES:
                    daily_history[mode][p].append({'date': date, 'rating': round(r, 1)})
    # Build current ratings for eligible players only, per mode
    result = {}
    for mode in modes:
        current = {p: round(ratings[mode][p], 1) for p, cnt in matches_played[mode].items() if cnt >= MIN_MATCHES}
        # Densify history across all dates by carrying forward the last known rating
        filled = {}
        for p, entries in daily_history[mode].items():
            by_date = {e['date']: e['rating'] for e in entries}
            last = None
            out = []
            for d in sorted_dates:
                if d in by_date:
                    last = by_date[d]
                if last is not None:
                    out.append({'date': d, 'rating': last})
            if out:
                filled[p] = out
        result[mode] = {
            'current_ratings': current,
            'history': filled
        }
    return result

def get_all_statistics():
    """
    Get all statistics in one call
    """
    data = load_match_data()
    
    return {
        'player_stats': get_player_stats(data),
        'match_analytics': get_match_analytics(data),
        'team_dynamics': get_team_dynamics(data),
        'score_patterns': get_score_patterns(data),
        'temporal_analysis': get_temporal_analysis(data),
        'doubles_serving': get_doubles_serving_stats(data),
        'total_points': get_total_points_stat(data),
        'head_to_head_singles': get_head_to_head_singles(data),
        'elo': get_elo_ratings_and_history()
    }

if __name__ == "__main__":
    # Test the statistics functions
    stats = get_all_statistics()
    print(json.dumps(stats, indent=2))

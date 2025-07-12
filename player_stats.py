# import list of NBA players
from nba_api.stats.static import players
# import endpoints to retrieve player stats
from nba_api.stats.endpoints import playercareerstats
# import pandas to work with tabular data
import pandas as pd

# this function will find a player's ID using their full name
def find_player_id(player_name):
    # search for players matching the given name
    input_matches = players.find_players_by_full_name(player_name)

    # if match is found, return the first result
    if input_matches:
        return input_matches[0]
    # return none if no match is found
    else:
        return None

# this function will find and display the stats the searched player
def display_player_stats(player_name):
    # get the players dictionary (include ID, name, etc.)
    player = find_player_id(player_name)

    # if player wasn't found, print an error message and stop
    if not player:
        print(f"no player found with the name: {player_name}")
        return
    
    # retrieve player's id from player's info
    player_id = player['id']
    print(f"found: {player['full_name']} (ID: {player_id})\n")

    # use player ID to get career stats with NBA API
    career = playercareerstats.PlayerCareerStats(player_id=player_id)

    # convert returned data into a pandas dataframe
    career_df = career.get_data_frames()[0]

    # get last row in dataframe (most recent season)
    recent_season = career_df.iloc[-1]
    
    # display selected stats from that row
    print("most recent season stats: ")
    print(f"season: {recent_season['SEASON_ID']}")
    print(f"team id: {recent_season['TEAM_ID']}")
    print(f"games played: {recent_season['GP']}")
    print(f"points per game: {recent_season['PTS'] / recent_season['GP']:.2f}")
    print(f"rebounds per game: {recent_season['REB'] / recent_season['GP']:.2f}")
    print(f"assists per game: {recent_season['AST'] / recent_season['GP']:.2f}")
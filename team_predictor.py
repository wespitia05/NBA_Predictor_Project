# import list of nba teams
from nba_api.stats.static import teams
# import game finder to find specific games between two teams
from nba_api.stats.endpoints import leaguegamefinder
# import pandas to work with tabular data
import pandas as pd
# use for any dates
from datetime import datetime

# this function will find the teams name
def find_team_id(team_name):
    # search for teams matching the given input
    all_teams = teams.get_teams()

    # iterate through all team names
    for team in all_teams:
        # if the team name inputted matches the team name found, return the team name
        if team_name.lower() in team['full_name'].lower():
            return team
    # otherwise return none
    return None

# this function returns the last 5 games for each inputted team separartely
def get_recent_games(team_id, num_games = 5):
    # gets all regular season games played by given team
    gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id, season_type_nullable='Regular Season')
    
    # gets the first result for the teams games
    games_df = gamefinder.get_data_frames()[0]
    
    # converts 'GAME_DATE' column of strings to datetime objects
    games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
    
    # sorts dataframe in descending order (most recent game first)
    games_df = games_df.sort_values('GAME_DATE', ascending = False)
    
    # returns the first num_games rows (5)
    return games_df.head(num_games)

# this function will return the last 5 games both teams have played against each other
def get_head_to_head_games(team1_abbr, team2_abbr, num_games = 5):
    # gets all league games involving team 1
    gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=None, season_type_nullable='Regular Season')
    
    # gets the first result for the teams games
    all_games_df = gamefinder.get_data_frames()[0]

    # filter for games where team 1 and team 2 played against each other
    head_to_head = all_games_df[
        (all_games_df['MATCHUP'].str.contains(f"{team1_abbr} vs {team2_abbr}") |
         all_games_df['MATCHUP'].str.contains(f"{team1_abbr} @ {team2_abbr}") |
         all_games_df['MATCHUP'].str.contains(f"{team2_abbr} vs {team1_abbr}") |
         all_games_df['MATCHUP'].str.contains(f"{team2_abbr} @ {team1_abbr}"))
    ]

    # converts 'GAME_DATE' column of strings to datetime objects
    head_to_head.loc[:, 'GAME_DATE'] = pd.to_datetime(head_to_head['GAME_DATE']).dt.date

    # sorts dataframe in descending order (most recent game first)
    head_to_head = head_to_head.sort_values('GAME_DATE', ascending=False).reset_index(drop=True)

    # return the 5 games they played each other
    return head_to_head.head(num_games)

# this function will predict who will win between the two teams chosen
def match_predictor(team1_name, team2_name):
    # finds the team names from given input
    team1 = find_team_id(team1_name)
    team2 = find_team_id(team2_name)

    # if one or both teams were not found, retun the error message
    if not team1 or not team2:
        print("one or both team names weren't found, please try again")
        return
    
    # display the two teams we will be predicitng
    print("predicting match between:")
    print(f"{team1['full_name']} vs {team2['full_name']}")
    print()

    # get info of the last 5 games for both teams
    team1_games = get_recent_games(team1['id'])
    team2_games = get_recent_games(team2['id'])

    # display the info for the last 5 games for team 1
    print(f"last 5 games for {team1['full_name']}:")
    print(team1_games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']])

    print()

    # display the info for the last 5 games for team 2
    print(f"last 5 games for {team2['full_name']}:")
    print(team2_games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']])

    print()

    # get the info for the last 5 games both teams played against each other
    head_to_head = get_head_to_head_games(team1['abbreviation'], team2['abbreviation'])

    # display the info for the last 5 games both teams played against each other
    print(f"last 5 games between {team1['full_name']} and {team2['full_name']}:")
    print(head_to_head[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']])
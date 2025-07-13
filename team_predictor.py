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

# this function returns the last 5 games for the inputted team
def get_recent_games(team_id, num_games = 5):
    gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=team_id, season_type_nullable='Regular Season')
    games_df = gamefinder.get_data_frames()[0]
    games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
    games_df = games_df.sort_values('GAME_DATE', ascending = False)
    return games_df.head(num_games)

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

    # display the info for the last 5 games for team 1
    print(f"last 5 games for {team2['full_name']}:")
    print(team2_games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']])

    print()
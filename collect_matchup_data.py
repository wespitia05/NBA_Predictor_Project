# import pandas to work with tabular data
import pandas as pd
# import game finder to find specific games between two teams
from nba_api.stats.endpoints import leaguegamefinder
# import list of nba teams
from nba_api.stats.static import teams

# this function will find the teams name
def find_team_info(team_name):
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

# prompt user to enter the name of the two teams
team1_name = input("\nenter first team name: ")
team2_name = input("\nenter second team name: ")

# find the info for each inputted team
team1_info = find_team_info(team1_name)
team2_info = find_team_info(team2_name)

# if we cannot find info on one of both teams, exit
if not team1_info or not team2_info:
    print("couldn't find one or both teams")
    exit()

# get last 5 games for each team
team1_last_five_games = get_recent_games(team1_info['id'])
team2_last_five_games = get_recent_games(team2_info['id'])

# get last 5 head-to-head games
head_to_head_games = get_head_to_head_games(team1_info['abbreviation'], team2_info['abbreviation'])

# display the info
print(f"\nlast 5 games for {team1_info['full_name']}: ")
print(team1_last_five_games[['GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'TOV']])

print(f"\nlast 5 games for {team2_info['full_name']}: ")
print(team2_last_five_games[['GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'TOV']])

print(f"\nlast 5 head to head games between {team1_info['full_name']} and {team2_info['full_name']}: ")
print(head_to_head_games[['GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'TOV']])

# add a column to each to label the source
team1_games = team1_last_five_games[['GAME_DATE','TEAM_ABBREVIATION','MATCHUP','PTS','REB','AST','TOV']].copy()
team1_games.columns = ['Game Date', 'Team', 'Matchup', 'Points', 'Rebounds', 'Assists', 'Turnovers']
team1_games['SOURCE'] = f"{team1_info['abbreviation']}_last5"

team2_games = team2_last_five_games[['GAME_DATE','TEAM_ABBREVIATION','MATCHUP','PTS','REB','AST','TOV']].copy()
team2_games.columns = ['Game Date', 'Team', 'Matchup', 'Points', 'Rebounds', 'Assists', 'Turnovers']
team2_games['SOURCE'] = f"{team2_info['abbreviation']}_last5"

head_to_head_games = head_to_head_games[['GAME_DATE','TEAM_ABBREVIATION','MATCHUP','PTS','REB','AST','TOV']].copy()
head_to_head_games.columns = ['Game Date', 'Team', 'Matchup', 'Points', 'Rebounds', 'Assists', 'Turnovers']
head_to_head_games['SOURCE'] = "head_to_head"

# combine them
combined = pd.concat([team1_games, team2_games, head_to_head_games], ignore_index=True)

# save to CSV
combined.to_csv("nba_team1_team2_stats.csv", index=False)
print("\n✅ Data saved to nba_team1_team2_stats.csv")

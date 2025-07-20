# import pandas to work with tabular data
import pandas as pd
# import game finder to find specific games between two teams
from nba_api.stats.endpoints import leaguegamefinder
# import list of nba teams
from nba_api.stats.static import teams
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

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
team1_games = team1_last_five_games[['GAME_DATE','TEAM_ABBREVIATION','MATCHUP','PTS','REB','AST','TOV', 'WL']].copy()
team1_games.columns = ['Game Date', 'Team', 'Matchup', 'Points', 'Rebounds', 'Assists', 'Turnovers', 'Result']
team1_games['SOURCE'] = f"{team1_info['abbreviation']}_last5"

team2_games = team2_last_five_games[['GAME_DATE','TEAM_ABBREVIATION','MATCHUP','PTS','REB','AST','TOV', 'WL']].copy()
team2_games.columns = ['Game Date', 'Team', 'Matchup', 'Points', 'Rebounds', 'Assists', 'Turnovers', 'Result']
team2_games['SOURCE'] = f"{team2_info['abbreviation']}_last5"

head_to_head_games = head_to_head_games[['GAME_DATE','TEAM_ABBREVIATION','MATCHUP','PTS','REB','AST','TOV', 'WL']].copy()
head_to_head_games.columns = ['Game Date', 'Team', 'Matchup', 'Points', 'Rebounds', 'Assists', 'Turnovers', 'Result']
head_to_head_games['SOURCE'] = "head_to_head"

# combine them
combined = pd.concat([team1_games, team2_games, head_to_head_games], ignore_index=True)

# save to CSV
combined.to_csv("nba_team1_team2_stats.csv", index=False)
print("\n✅ Data saved to nba_team1_team2_stats.csv")

# load the dataset to being the predictions
df = pd.read_csv("nba_team1_team2_stats.csv")

# ***** PREPARING THE DATA ***** #
# convert win/lose into 1/0
df['WIN'] = df['Result'].apply(lambda x: 1 if x == 'W' else 0)

# our features: stats we want the model to learn from
X = df[['Points', 'Rebounds', 'Assists', 'Turnovers']]

# our target: what we want model to predict
y = df['WIN']

# ***** SPLIT DATA FOR TRAINING/TESTING ***** #
# 80% will be used to train the model, 20% will be used to test it
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ***** CREATE/TRAIN THE MODEL ***** #
# allows enough iterations to train
model = LogisticRegression(max_iter=1000)
# train the model
model.fit(X_train, y_train)

# ***** CHECK MODEL ACCURACY ***** #
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
print(f"\nmodel accuracy: {accuracy:.2f}")

# ***** PREDICT MATCHUP ***** #
# prompt user to input team abbreviations
team1_name = input("\nenter first team abbreviation (ex. LAL): ").upper()
team2_name = input("\nenter secon team abbreviation (ex. NYK): ").upper()

# filter rows for each team
team1_rows = df[df['Team'] == team1_name]
team2_rows = df[df['Team'] == team2_name]

# if we dont have data for both teams, display error message
if team1_rows.empty or team2_rows.empty:
    print("\ncouldn't find data for one or both teams")
else:
    # calculate average stats for each team
    team1_stats = [
        float(team1_rows['Points'].mean()),
        float(team1_rows['Rebounds'].mean()),
        float(team1_rows['Assists'].mean()),
        float(team1_rows['Turnovers'].mean())
    ]
    team2_stats = [
        float(team2_rows['Points'].mean()),
        float(team2_rows['Rebounds'].mean()),
        float(team2_rows['Assists'].mean()),
        float(team2_rows['Turnovers'].mean())
    ]

    # create dataframes with feature names
    team1_df = pd.DataFrame([team1_stats], columns=['Points','Rebounds','Assists','Turnovers'])
    team2_df = pd.DataFrame([team2_stats], columns=['Points','Rebounds','Assists','Turnovers'])

    # predict results for each team
    team1_predict = model.predict(team1_df)[0]
    team2_predict = model.predict(team2_df)[0]

    # display results
    print(f"\naverage stats for {team1_name}: {team1_stats}")
    print(f"predicted result: {'WIN' if team1_predict == 1 else 'LOSS'}")

    print(f"\naverage stats for {team2_name}: {team2_stats}")
    print(f"predicted result: {'WIN' if team2_predict == 1 else 'LOSS'}")

    # final matchup decision 
    print("\nfinal matchup prediction:")
    if team1_predict == 1 and team2_predict == 0:
        print(f"{team1_name} is more likely to WIN over {team2_name}")
    elif team1_predict == 0 and team2_predict == 1:
        print(f"{team2_name} is more likely to WIN over {team1_name}")
    elif team1_predict == 1 and team2_predict == 1:
        print(f"both {team1_name} and {team2_name} will have a close match")
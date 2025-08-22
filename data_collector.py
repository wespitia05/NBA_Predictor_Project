# import game finder to find specific games between two teams
from nba_api.stats.endpoints import leaguegamefinder
# import pandas to work with tabular data
import pandas as pd

# this function will add the data for the inputted season
def get_games_for_season(season):
    # we want both regular season and playoffs
    all_types = ['Regular Season', 'Playoffs']
    season_frames = []

    for stype in all_types:
        # get games for that season and season type
        gamefinder = leaguegamefinder.LeagueGameFinder(season_nullable=season, season_type_nullable=stype)

        # gets the first result for the teams games
        games_df = gamefinder.get_data_frames()[0]

        # NEW: skip if this season type returned no rows
        if games_df is None or games_df.empty:
            continue

        # add column to keep track of season type (regular/playoffs)
        games_df['SEASON_TYPE'] = stype

        season_frames.append(games_df)

    # combine regular + playoff games into one dataframe
    if len(season_frames) == 0:
        # NEW: if nothing came back at all, return empty in your output shape
        return pd.DataFrame(columns=[
            'TEAM ID','TEAM NAME','TEAM ABBR','OPP ABBR','GAME DATE','HOME/AWAY',
            'POINTS','REBOUNDS','ASSISTS','TURNOVERS','WIN','SEASON_TYPE'
        ])

    games_df = pd.concat(season_frames, ignore_index=True)

    # NEW: drop any rows with missing matchup to avoid None.split errors
    games_df = games_df.dropna(subset=['MATCHUP']).copy()

    # converts 'GAME_DATE' column of strings to datetime objects
    games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])

    # create new dataframe to hold only the info we want
    output_df = pd.DataFrame()

    # print(games_df.columns.tolist())

    # basic team info
    output_df['TEAM ID'] = games_df['TEAM_ID']
    output_df['TEAM NAME'] = games_df['TEAM_NAME']
    output_df['TEAM ABBR'] = games_df['TEAM_ABBREVIATION']

    # get opponent name from matchup
    opponent_names= []
    for matchup in games_df['MATCHUP']:
        # MATCHUP: "LAL vs NYK" or "LAL @ BOS"
        # opponent is always last part
        parts = matchup.split(" ")
        opponent_names.append(parts[-1])
    output_df['OPP ABBR'] = opponent_names

    # add game date
    output_df['GAME DATE'] = games_df['GAME_DATE']

    # figure out if the game was home or away
    home_away = []
    for matchup in games_df['MATCHUP']:
        if "vs" in matchup:
            home_away.append("Home")
        else:
            home_away.append("Away")
    output_df['HOME/AWAY'] = home_away

    # add stats
    output_df['POINTS'] = games_df['PTS']
    output_df['REBOUNDS'] = games_df['REB']
    output_df['ASSISTS'] = games_df['AST']
    output_df['TURNOVERS'] = games_df['TOV']

    # add win/loss column (1 for win, 0 for loss)
    win_column = []
    for result in games_df['WL']:
        if result == "W":
            win_column.append(1)
        else:
            win_column.append(0)
    output_df['WIN'] = win_column

    # keep track of whether it was Regular Season or Playoffs
    output_df['SEASON_TYPE'] = games_df['SEASON_TYPE']

    return output_df

# test function
if __name__ == "__main__":
    # list of seasons from past 5 years
    seasons = ["2023-24", "2024-25"]

    all_data = pd.DataFrame()

    for season in seasons:
        print(f"fetching data for season: {season}...")
        season_data = get_games_for_season(season)
        all_data = pd.concat([all_data, season_data], ignore_index=True)
    
    # save to csv
    all_data.to_csv("nba_games_2023_to_2025.csv", index=False)
    print("saved to nba_games_2023_to_2025.csv")
    print(all_data.head().to_string())
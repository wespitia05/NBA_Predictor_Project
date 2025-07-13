# import list of nba teams
from nba_api.stats.static import teams
# import endpoints to retrieve team stats/info
from nba_api.stats.endpoints import teamyearbyyearstats, teaminfocommon

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

# this function will find the name of the team using team_name
def display_team_stats(team_name):
    # search for all teams that match the inputed team name
    team = find_team_id(team_name)

    # if not match found, return error message
    if not team:
        print(f"no team found matching {team_name}")
        return
    # ***** TEAM INFO ***** #
    # retrieve team id from team info
    team_id = team['id']
    print(f"found: {team['full_name']} (ID: {team_id})")
    print()

    # fetch the team info
    info = teaminfocommon.TeamInfoCommon(team_id=team_id)
    
    # get the first result of team info
    info_df = info.get_data_frames()[0]
    row = info_df.iloc[0]
    # print("Returned TeamInfoCommon columns:")
    # print(info_df.columns.tolist())

    # display team information
    print("*****************************")
    print("          TEAM INFO          ") 
    print(f"team name: {row['TEAM_NAME']}")
    print(f"city: {row['TEAM_CITY']}")
    print(f"abbreviation: {row['TEAM_ABBREVIATION']}")
    print(f"conference: {row['TEAM_CONFERENCE']}")
    print(f"division: {row['TEAM_DIVISION']}")
    print(f"division rank: {row['DIV_RANK']}")
    print(f"conference rank: {row['CONF_RANK']}")
    print("*****************************")
    print()

    # ***** TEAM STATS ***** #
    # use team id to get team stats with NBA API
    stats = teamyearbyyearstats.TeamYearByYearStats(team_id=team_id)

    # convert returned data into a pandas dataframe
    stats_df = stats.get_data_frames()[0]

    nba_stats = stats_df
    # print("Columns returned by API:")
    # print(stats_df.columns.tolist())

    # list available seasons for chosen team
    print("seasons availiable:")
    for season in nba_stats['YEAR'].tolist():
        print(f"{season}", end=", ")
    
    # while loop will keep prompting user to enter a valid season
    while True:
        # ask user to choose a season
        selected_season = input("Enter a year to view stats (ex. 2022-23): ")

        # find the matching season row
        season_row = nba_stats[nba_stats['YEAR'] == selected_season]

        # if there is no seasons for inputted team, exit program
        if not season_row.empty:
            break
        
        # print error message for incorrect input
        print(f"no stats found for the year {selected_season}, try again")
    
    # get the first row for given season
    row = season_row.iloc[0]

    # display selected stats from that row
    print("*****************************")
    print(f"TEAM STATS FOR SEASON {selected_season}")
    print(f"wins: {row['WINS']}")
    print(f"losses: {row['LOSSES']}")
    print(f"win percentage: {row['WIN_PCT']:.3f}")
    print(f"conference rank: {row['CONF_RANK']}")
    print(f"division rank: {row['DIV_RANK']}")
    print(f"games played: {row['GP']}")
    print(f"points per game: {row['PTS'] / row ['GP']:.2f}")
    print(f"NBA finals appearance: {row['NBA_FINALS_APPEARANCE']}")
    print("*****************************")
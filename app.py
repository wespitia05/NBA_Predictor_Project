from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
# import list of nba teams
from nba_api.stats.static import teams
# import endpoints to retrieve team info
from nba_api.stats.endpoints import teaminfocommon, commonteamroster
# import list of NBA players
from nba_api.stats.static import players
# import endpoints to retrieve player stats
from nba_api.stats.endpoints import playercareerstats, commonplayerinfo, playergamelog
# import datetime
from datetime import datetime, UTC

# creates the flask app
app = Flask(__name__)

# print(df.columns)

# this function will get the player averages for ppg, tpg and apg for their current team
def get_player_average(player_id):
    try:
        # find out players current team using id and abbr
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        df_info = info.get_data_frames()[0]

        # extracts players current team id and abbr from profile info
        team_id = df_info.at[0, 'TEAM_ID']
        team_abbr = df_info.at[0, 'TEAM_ABBREVIATION']

        # if player does not have a current team, return none
        if not team_id:
            return None, None, None

        # pull game logs for a past 5 seasons
        seasons = ['2024-25', '2023-24', '2022-23', '2021-22', '2020-21']

        # this list will hold the dataframes from each season
        frames = []

        # loop through each season
        for s in seasons:
            try:
                # fetch players game log
                gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=s)
                df_gamelog = gamelog.get_data_frames()[0]

                # appends it if data exists
                if df_gamelog is not None and not df_gamelog.empty:
                    frames.append(df_gamelog)
            except Exception:
                continue
        
        # if no game logs were collected, return empty value
        if not frames:
            return None, None, None
        
        # combines all dataframes from different seasons into one big dataset
        logs = pd.concat(frames, ignore_index=True)

        # keep only games player played for the current team
        team_id_col = 'TEAM_ID' if 'TEAM_ID' in logs.columns else ('Team_ID' if 'Team_ID' in logs.columns else None)
        
        # filters logs so you only keep games where the player was on their current team
        if team_id_col:
            logs = logs[logs[team_id_col] == team_id]
        else:
            logs = logs[logs['MATCHUP'].str.contains(team_abbr, na=False)]

        # if there are no games for the curretn team, return empty values
        if logs.empty:
            return None, None, None
        
        # compute the averages
        ppg = float(logs['PTS'].mean()) if 'PTS' in logs.columns else None
        rpg = float(logs['REB'].mean()) if 'REB' in logs.columns else None
        apg = float(logs['AST'].mean()) if 'AST' in logs.columns else None
        tpg = float(logs['TOV'].mean()) if 'TOV' in logs.columns else None
        
        # returns the averages as a tuple
        return ppg, rpg, apg, tpg
    
    except Exception:
        return None, None, None, None

# route for the homepage
@app.route('/')
def home_page():
    return render_template('index.html')  # this will look in the templates/ folder

# route for the predictions page
@app.route('/predict')
def predict_page():
    return "<h1>Predict page coming soon!</h1>"

# route for the players statistics page
@app.route('/player_stats/<int:player_id>')
def players_stats_page(player_id):
    try:
        # get player info from the nba api
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        df = info.get_data_frames()[0]
        player_name = df.at[0, 'DISPLAY_FIRST_LAST']
        team_name   = df.at[0, 'TEAM_NAME'] or "Free Agent"
        jersey      = df.at[0, 'JERSEY'] or "N/A"
        position    = df.at[0, 'POSITION'] or "N/A"
        height = df.at[0, 'HEIGHT']
        weight = df.at[0, 'WEIGHT']
        college = df.at[0, 'SCHOOL'] or df.at[0, 'LAST_AFFILIATION']
        country = df.at[0, 'COUNTRY']
        birthdate = df.at[0, 'BIRTHDATE']
        experience = df.at[0, 'SEASON_EXP']
        draft_year = df.at[0, 'DRAFT_YEAR']
        draft_round = df.at[0, 'DRAFT_ROUND']
        draft_pick = df.at[0, 'DRAFT_NUMBER']
    except Exception:
        player_name = "Unknown Player"
        team_name   = "N/A"
        jersey      = "N/A"
        position    = "N/A"
        height      = "N/A"
        weight      = "N/A"
        college     = "N/A"
        country     = "N/A"
        birthdate   = "N/A"
        experience  = "N/A"
        draft_year  = "N/A"
        draft_round = "N/A"
        draft_pick  = "N/A"
    
    # nba headshot url
    headshot_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

    # compute averages for the current team
    ppg, rpg, apg, tpg = get_player_average(player_id)

    # format birthday and age
    try:
        dob = datetime.strptime(birthdate.split("T")[0], "%Y-%m-%d")
        birthdate = dob.strftime("%B %d, %Y")
        today = datetime.now(UTC).date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except Exception:
        birthdate = "N/A"
        age = "N/A"

    # format draft information as one
    year_str  = str(draft_year).strip() if draft_year is not None else ""
    round_str = str(draft_round).strip() if draft_round is not None else ""
    pick_str  = str(draft_pick).strip() if draft_pick is not None else ""

    if year_str.lower() == "undrafted" or year_str == "" or year_str == "0":
        draft_text = "Undrafted"
    else:
        # if round/pick missing or "0", just show the year
        if round_str in ("", "0") or pick_str in ("", "0"):
            draft_text = year_str
        else:
            draft_text = f"{year_str} R{round_str} Pick {pick_str}"

    # this function will get the gamelogs for this season, if not then last season
    def fetch_recent_games(player_id):
        seasons = ["2024-25", "2023-24"]
        dfs = [] # dataframes collected here

        # this for loop will iterate through each season in seasons
        for season in seasons:
            # this for loop will iterate through the type of season
            for season_type in ("Playoffs", "Regular Season"):
                try:
                    # asks api for players log for the given season and type
                    gl = playergamelog.PlayerGameLog(
                        player_id=player_id,
                        season=season,
                        season_type_all_star=season_type
                    )

                    # the first dataframe returned has the logs
                    df = gl.get_data_frames()[0]

                    # if we got actual data we save it
                    if df is not None and not df.empty:
                        # add season type column if it doesnt exist (so we know if it was playoffs or regular)
                        if "SEASON_TYPE" not in df.columns:
                            df = df.copy()
                            df["SEASON_TYPE"] = season_type
                        dfs.append(df)
                except Exception as e:
                    print(f"[DEBUG] Error fetching {season} {season_type}: {e}")

        # any game logs collected we combine into one dataframe
        if dfs:
            combined = pd.concat(dfs, ignore_index=True)

            # drop duplicate games in case api returns overlaps
            if "GAME_ID" in combined.columns:
                combined = combined.drop_duplicates(subset=["GAME_ID"])

            return combined

        # if nothing worked above, we try calling without specifying season type
        try:
            gl = playergamelog.PlayerGameLog(player_id=player_id)
            df = gl.get_data_frames()[0]
            if df is not None and not df.empty:
                return df
        except Exception:
            pass

        # return none if neither method works
        return None
    
    games_df = fetch_recent_games(player_id)

    # default values
    player_recent_games = []

    if games_df is not None and not games_df.empty:
        # converts gamed ate column into real datetime objects
        games_df['GAME_DATE_PARSED'] = pd.to_datetime(
            games_df['GAME_DATE'], format='%b %d, %Y', errors='coerce'
        )

        # if more than half the rows failed to parse try better conversion
        if games_df['GAME_DATE_PARSED'].isna().mean() > 0.5:
            games_df['GAME_DATE_PARSED'] = pd.to_datetime(
                games_df['GAME_DATE'].astype(str).str.strip(), errors='coerce'
            )

        # sort games from newest to oldest (keep recent 5)
        recent_five_games = (
            games_df.sort_values('GAME_DATE_PARSED', ascending=False, na_position='last')
                    .head(5)
                    .copy()
        )

        # format decimal percentages to whole number percentages
        if 'FG_PCT' in recent_five_games.columns:   recent_five_games['FG_PCT']   = (recent_five_games['FG_PCT']*100).round(1).astype(float)
        if 'FG3_PCT' in recent_five_games.columns:   recent_five_games['FG3_PCT']   = (recent_five_games['FG3_PCT']*100).round(1).astype(float)
        if 'FT_PCT' in recent_five_games.columns:   recent_five_games['FT_PCT']   = (recent_five_games['FT_PCT']*100).round(1).astype(float)

        # shape into list of dicts (for HTML loop)
        for _, row in recent_five_games.iterrows():
            player_recent_games.append({
                'Game Date': row['GAME_DATE'],
                'Matchup': row['MATCHUP'],
                "Season Type": row['SEASON_TYPE'],
                'W/L': row['WL'],
                'MIN': row['MIN'],
                'PTS': row['PTS'],
                'REB': row['REB'],
                'AST': row['AST'],
                'STL': row['STL'],
                'BLK': row['BLK'],
                'TOV': row['TOV'],
                'FG%': row['FG_PCT'],
                '3P%': row['FG3_PCT'],
                'FT%': row['FT_PCT'],
                '+/-': row['PLUS_MINUS'],
            })

    return render_template('player_stats.html', 
                           player_name=player_name, 
                           headshot_url=headshot_url,
                           team_name=team_name,
                           jersey=jersey,
                           position=position,
                           ppg=ppg,
                           rpg=rpg,
                           apg=apg,
                           tpg=tpg,
                           height=height,
                           weight=weight,
                           college=college,
                           country=country,
                           birthdate=birthdate,
                           age=age,
                           draft_text=draft_text,
                           experience=experience,
                           player_recent_games=player_recent_games)

# route for the teams statistics page
@app.route('/team/<team_abbr>')
def team_stats(team_abbr):
    # load our stats data 
    df = pd.read_csv('nba_games_2023_to_2025.csv')

    # filter games for this team from the CSV
    team_games = df[df['TEAM ABBR'] == team_abbr.upper()]

    # get static team metadata
    nba_teams = teams.get_teams()
    team_info = next((t for t in nba_teams if t['abbreviation'] == team_abbr.upper()), None)

    if not team_info:
        return f"<h1>Could not find metadata for team: {team_abbr}</h1>"

    team_id = team_info['id']
    team_name = team_info['full_name']

    # get detailed team info from API
    team_details = teaminfocommon.TeamInfoCommon(team_id=team_id)
    team_data = team_details.get_data_frames()[0]

    # extract city, conference, division, ranks
    team_city = team_data.loc[0, 'TEAM_CITY']
    team_conference = team_data.loc[0, 'TEAM_CONFERENCE']
    team_division = team_data.loc[0, 'TEAM_DIVISION']
    conf_rank = team_data.loc[0, 'CONF_RANK']
    div_rank = team_data.loc[0, 'DIV_RANK']

    # this function turns team name into images/team_name_logo.png
    def build_logo_filename(team_name: str) -> str:
        return f"images/{team_name.lower().replace(' ', '_')}_logo.png"

    logo_filename = build_logo_filename(team_name)

    if team_games.empty:
        return f"<h1>No data found for team: {team_abbr}</h1>"

    # get the last 20 games (by date)
    recent_games = team_games.sort_values(by='GAME DATE', ascending=False).head(20)

    # extract the team name from the first matching row
    team_name = team_games.iloc[0]['TEAM NAME']

    # calculate averages
    avg_points = recent_games['POINTS'].mean()
    avg_rebounds = recent_games['REBOUNDS'].mean()
    avg_assists = recent_games['ASSISTS'].mean()
    avg_turnovers = recent_games['TURNOVERS'].mean()

    # rename columns for clarity in html file
    games = recent_games.rename(columns={
        'GAME DATE': 'Game Date',
        'SEASON_TYPE': 'Season Type',
        'OPP ABBR': 'Opponent',
        'HOME/AWAY': 'Location',
        'POINTS': 'Points',
        'REBOUNDS': 'Rebounds',
        'ASSISTS': 'Assists',
        'TURNOVERS': 'Turnovers',
        'WIN': 'Win'
    })

    # here we will extract the roster information
    season_str = "2024-25"
    try: 
        latest_date = pd.to_datetime(team_games['GAME DATE']).max()
        if pd.notna(latest_date):
            y = latest_date.year
            season_str = f"{y}-{str(y+1)[-2:]}" if latest_date.month >= 7 else f"{y-1}-{str(y)[-2:]}"
    except Exception:
        pass

    try:
        roster_df = commonteamroster.CommonTeamRoster(team_id=team_id, season=season_str).get_data_frames()[0]
    except Exception:
        roster_df = pd.DataFrame()
    
    roster = []
    if not roster_df.empty:
        for _, r in roster_df.iterrows():
            pid    = int(r.get('PLAYER_ID', 0)) if pd.notna(r.get('PLAYER_ID')) else None
            name   = r.get('PLAYER', 'N/A')
            jersey = r.get('NUM', 'N/A')
            pos    = r.get('POSITION', 'N/A')
            height = r.get('HEIGHT', 'N/A')
            weight = r.get('WEIGHT', 'N/A')
            bday   = r.get('BIRTH_DATE', 'N/A')
            raw_age = r.get('AGE')
            if pd.notna(raw_age):
                try:
                    age = int(float(raw_age))
                except (ValueError, TypeError):
                    age = 'N/A'
            else:
                age = 'N/A'
            exp    = r.get('EXP', 'N/A')
            school = r.get('SCHOOL', 'N/A')

            roster.append({
                "id": pid,
                "name": name,
                "jersey": jersey,
                "position": pos,
                "height": height,
                "weight": weight,
                "birthdate": bday,
                "age": age,
                "experience": exp,
                "school": school,
            })

        return render_template('team_stats.html',
                            team_name=team_name,
                            team_abbr=team_abbr.upper(),
                            team_city=team_city,
                            team_conference=team_conference,
                            team_division=team_division,
                            conf_rank=conf_rank,
                            div_rank=div_rank,
                            games=games.to_dict(orient='records'),
                            avg_points=avg_points,
                            avg_rebounds=avg_rebounds,
                            avg_assists=avg_assists,
                            avg_turnovers=avg_turnovers,
                            logo_filename=logo_filename,
                            roster=roster)

# route for the players page
@app.route('/players')
def players_page():
    # read input from the search bar
    query = (request.args.get('q') or "").strip()

    # calls api to return list of all active nba players
    all_players = players.get_active_players()

    # if there is a search, filter by name otherwise use all
    if query:
        filtered = [p for p in all_players if query.lower() in p['full_name'].lower()]
    else:
        filtered = all_players

    # first 5 players (takes longer to load with more)
    selected_players = filtered[:5] 

    # initialize empty list to store player data
    player_data = []

    # loops through each selected player to fetch info
    for player in selected_players:
        player_id = player['id'] # get id
        full_name = player['full_name'] # get full name

        # try block in case api fails
        try:
            # get player profile info
            info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            # retrieves first dataframe
            df = info.get_data_frames()[0]

            # extract team name and position
            team_name = df.at[0, 'TEAM_NAME']
            position = df.at[0, 'POSITION']
        
        # in case there's an error, display msg
        except Exception as e:
            team_name = "N/A"
            position = "N/A"

        # otherwise add player data into list
        player_data.append({
            'id': player_id,
            'full_name': full_name,
            'team_name': team_name,
            'position': position
        })

    return render_template('players.html', players=player_data, query=query)

# routes for load players button
@app.route('/load_players')
def load_more_players():
    # get how many players we've already loaded (default is 0)
    offset = int(request.args.get('offset', 0))

    # read input from the search bar
    query = (request.args.get('q') or "").strip()

    # get all current NBA players
    all_players = players.get_active_players()

    # if there is a search, filter by name otherwise use all
    if query:
        filtered = [p for p in all_players if query.lower() in p['full_name'].lower()]
    else:
        filtered = all_players

    # get the next 5 players
    selected_players = filtered[offset:offset + 5]

    player_data = []

    for player in selected_players:
        player_id = player['id']
        full_name = player['full_name']

        try:
            # get extra info like team and position
            info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            df = info.get_data_frames()[0]
            team_name = df.at[0, 'TEAM_NAME']
            position = df.at[0, 'POSITION']
        except Exception:
            team_name = "N/A"
            position = "N/A"

        # add to our list of player info
        player_data.append({
            'id': player_id,
            'full_name': full_name,
            'team_name': team_name,
            'position': position
        })

    # send the list of players back to JavaScript
    return jsonify(player_data)

# route for the teams page
@app.route('/teams')
def teams_page():
    return render_template('teams.html')  # this will look in the templates/ folder

# run the application
if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
# import list of nba teams
from nba_api.stats.static import teams
# import endpoints to retrieve team info
from nba_api.stats.endpoints import teaminfocommon
# import list of NBA players
from nba_api.stats.static import players
# import endpoints to retrieve player stats
from nba_api.stats.endpoints import playercareerstats, commonplayerinfo

# creates the flask app
app = Flask(__name__)

# print(df.columns)

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
    except Exception:
        player_name = "Unknown Player"

    return render_template('player_stats.html', player_name=player_name)

# route for the teams statistics page
@app.route('/team/<team_abbr>')
def team_stats(team_abbr):
    # load our stats data 
    df = pd.read_csv('nba_games_2020_to_2025.csv')

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
        'OPP ABBR': 'Opponent',
        'HOME/AWAY': 'Location',
        'POINTS': 'Points',
        'REBOUNDS': 'Rebounds',
        'ASSISTS': 'Assists',
        'TURNOVERS': 'Turnovers',
        'WIN': 'Win'
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
                           avg_turnovers=avg_turnovers)

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
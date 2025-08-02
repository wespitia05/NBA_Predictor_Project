from flask import Flask, render_template, request
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
@app.route('/player_stats')
def players_stats_page():
    return "<h1>Player statistics page coming soon!</h1>"

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
    # get all active NBA players
    all_players = players.get_active_players()
    
    # select the first 30 players (in the order returned by the API)
    selected_players = all_players[:30]
    
    # extract relevant fields
    player_data = []
    for player in selected_players:
        player_data.append({
            'full_name': player['full_name'],
            'team_id': player.get('team_id', 'N/A'),
            'team_name': player.get('team_name', 'N/A'),
            'position': player.get('position', 'N/A'),
            'id': player['id']
        })

    return render_template('players.html', players=player_data)

# route for the teams page
@app.route('/teams')
def teams_page():
    return render_template('teams.html')  # this will look in the templates/ folder

# run the application
if __name__ == '__main__':
    app.run(debug=True)
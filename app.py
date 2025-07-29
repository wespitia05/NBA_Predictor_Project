from flask import Flask, render_template
import pandas as pd
import os

# creates the flask app
app = Flask(__name__)

# load our stats data 
df = pd.read_csv('nba_games_2020_to_2025.csv')
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
    # filter games for this team from the CSV
    team_games = df[df['TEAM ABBR'] == team_abbr.upper()]

    if team_games.empty:
        return f"<h1>No data found for team: {team_abbr}</h1>"

    # get the last 20 games (by date)
    recent_games = team_games.sort_values(by='GAME DATE', ascending=False).head(20)

    # calculate averages
    avg_points = recent_games['POINTS'].mean()
    avg_rebounds = recent_games['REBOUNDS'].mean()
    avg_assists = recent_games['ASSISTS'].mean()
    avg_turnovers = recent_games['TURNOVERS'].mean()

    return render_template('team_stats.html',
                           team_abbr=team_abbr.upper(),
                           games=recent_games.to_dict(orient='records'),
                           avg_points=avg_points,
                           avg_rebounds=avg_rebounds,
                           avg_assists=avg_assists,
                           avg_turnovers=avg_turnovers)

# route for the players page
@app.route('/players')
def players_page():
    return "<h1>Players page coming soon!</h1>"

# route for the teams page
@app.route('/teams')
def teams_page():
    return render_template('teams.html')  # this will look in the templates/ folder

# run the application
if __name__ == '__main__':
    app.run(debug=True)
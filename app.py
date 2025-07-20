from flask import Flask, render_template

# creates the flask app
app = Flask(__name__)

# route for the homepage
@app.route('/')
def home_page():
    return render_template('index.html')  # this will look in the templates/ folder

# route for the predictions page
@app.route('/predict')
def predict_page():
    return "<h1>Predict page coming soon!</h1>"

# route for the players statistics page
@app.route('/stats')
def players_stats_page():
    return "<h1>Player statistics page coming soon!</h1>"

# route for the teams statistics page
@app.route('/stats')
def teams_stats_page():
    return "<h1>Team statistics page coming soon!</h1>"

# route for the players page
@app.route('/players')
def players_page():
    return "<h1>Players page coming soon!</h1>"

# route for the teams page
@app.route('/teams')
def teams_page():
    return "<h1>Teams page coming soon!</h1>"

# run the application
if __name__ == '__main__':
    app.run(debug=True)
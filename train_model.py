# import pandas to work with tabular data
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# load our csv
df = pd.read_csv("nba_games_2020_to_2025.csv")

# print out the columns in our dataset
# print("columns in dataset:")
# print(df.columns.tolist())

# print out the first 5 rows
# print("\nfirst 5 rows:")
# print(df.head().to_string())

# convert home/away to numeric value
home_away_num = []
for value in df['HOME/AWAY']:
    if value == 'Home':
        home_away_num.append(1)
    else:
        home_away_num.append(0)
df['HOME/AWAY'] = home_away_num

# gather data, these stats will be used to train the model
X = df[['POINTS', 'REBOUNDS', 'ASSISTS', 'TURNOVERS', 'HOME/AWAY']]
# this is what we want to predict
y = df['WIN']

# split our data into training and testing
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# train our model (allow more iteration so it can learn)
model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)

# test our model
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
print(f"\nmodel accuracy: {accuracy:.2f}")

# prompt user for a team
team_name_input = input("\nenter the name of the team you want to predict for: ")

# filter the datafram for that inputted team
team_games = df[df['TEAM NAME'].str.lower() == team_name_input.lower()]

# check if we found the games
if team_games.empty:
    print(f"no games found for team: {team_name_input}")
else:
    # sort by date to get most recent games
    team_games = team_games.sort_values('GAME DATE', ascending=False)

    # get the last 5 recent games
    recent_games = team_games.head(5)

    # calculate average for points, rebounds, assists and turnovers
    avg_points = recent_games['POINTS'].mean()
    avg_rebounds = recent_games['REBOUNDS'].mean()
    avg_assists = recent_games['ASSISTS'].mean()
    avg_turnovers = recent_games['TURNOVERS'].mean()

    # get most recent games home/away value
    home_away_value = recent_games.iloc[0]['HOME/AWAY']

    # build new set of values
    features = [[avg_points, avg_rebounds, avg_assists, avg_turnovers, home_away_value]]

    # predict
    predicted_result = model.predict(features)[0]

    # display the predictions
    print(f"\naveraged over last 5 games for {team_name_input}")
    print(f"points: {avg_points:.2f}")
    print(f"rebounds: {avg_rebounds:.2f}")
    print(f"assists: {avg_assists:.2f}")
    print(f"turnovers: {avg_turnovers:.2f}")
    print(f"home/away: {home_away_value}")

    if predicted_result == 1:
        print(f"\npredicted result for {team_name_input} is: WIN")
    else:
        print(f"\npredicted result for {team_name_input} is: LOSS")

    # explain how we came to this prediciton
    for feature_name, value, coef in zip(X.columns, [avg_points, avg_rebounds, avg_assists, avg_turnovers, home_away_value], model.coef_[0]):
        # contribution value
        contribution = value * coef
        direction = "WIN" if coef > 0 else "LOSS"
        print(f"{feature_name}: value = {value:.2f}, weight = {coef:.4f}, contribution = {contribution:.2f} (leans {direction})")
    
    print(f"\nmodel intercept (bias): {model.intercept_[0]:.4f}")

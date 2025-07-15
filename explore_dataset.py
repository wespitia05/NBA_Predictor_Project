# import pandas to work with tabular data
import pandas as pd
# import matlotlib to visualize stats
import matplotlib.pyplot as plt

# load the dataset
df = pd.read_csv("nba_games_2020_to_2025.csv")

# see basic info
print("\ndataset info:")
print(df.info())

# see first 10 rows
print("\nfirst 10 rows:")
print(df.head(10).to_string())

# see the columns available
print("\ncolumns available:")
print(df.columns.tolist())

# see basic statistics
print("\nbasic stats:")
print(df.describe(include='all'))

# see win/loss distribution
print("\nwin/loss distribution:")
print(df['WIN'].value_counts())
win_rate = df['WIN'].mean() * 100
print(f"overall win % in dataset: {win_rate:.2f}%")

# average stats per game
print("\naverage stats per game:")
print(f"points: {df['POINTS'].mean():.2f}")
print(f"rebounds: {df['REBOUNDS'].mean():.2f}")
print(f"assists: {df['ASSISTS'].mean():.2f}")
print(f"turnovers: {df['TURNOVERS'].mean():.2f}")

# home/away performance
home_games = df[df['HOME/AWAY'] == 'Home']
away_games = df[df['HOME/AWAY'] == 'Away']

print("\nhome games win rate:")
print(home_games['WIN'].mean() * 100)

print("\naway games win rate:")
print(away_games['WIN'].mean() * 100)

# teams with highest average points
team_points = df.groupby('TEAM ABBR')['POINTS'].mean().sort_values(ascending=False)
print("\naverage points per team:")
print(team_points.head(10))

# using matplotlib to visualize distribution of points
plt.hist(df['POINTS'], bins=20)
plt.title("distribution of points")
plt.xlabel("points scored")
plt.ylabel("number of games")
plt.show()

# using matplotlib to visualize number of wins from each team
team_wins = df.groupby('TEAM NAME')['WIN'].sum().sort_values(ascending=False)

plt.figure(figsize=(10,6))
team_wins.plot(kind='bar')
plt.title("total wins by team (2020–2025)")
plt.xlabel("team")
plt.ylabel("total wins")
plt.xticks(rotation=90)
plt.tight_layout()
plt.show()
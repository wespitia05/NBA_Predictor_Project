from player_stats import display_player_stats
from team_stats import display_team_stats

if __name__ == "__main__":
    while True:
        user_input = input("Would you like to search for 'player' or 'team' stats? (or 'exit' to quit): ").lower()

        if user_input == 'exit':
            break
        elif user_input == 'player':
            name = input("enter the NBA player's full name: ")
            display_player_stats(name)
        elif user_input == 'team':
            team_name = input("enter the NBA team name (ex. Lakers): ")
            display_team_stats(team_name)
        elif user_input == 'exit':
            break
        else:
            print("invalid option. please try again")
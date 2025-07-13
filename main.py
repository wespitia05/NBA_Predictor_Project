from player_stats import display_player_stats
from team_stats import display_team_stats
from team_predictor import match_predictor

if __name__ == "__main__":
    while True:
        user_input = input("would you like to view 'stats' or 'predict'? (or 'exit' to quit): ")
        print()
        # ***** USER CHOSE STATS ***** #
        if user_input == 'stats'.lower():
            while True:
                user_input = input("would you like to search for 'player' or 'team' stats? (or 'exit' to quit): ").lower()
                print()
                # USER CHOSE PLAYER
                if user_input == 'player':
                    name = input("enter the NBA player's full name: ")
                    display_player_stats(name)
                # USER CHOSE TEAM
                elif user_input == 'team':
                    team_name = input("enter the NBA team name (ex. Lakers): ")
                    display_team_stats(team_name)
                # USER CHOSE EXIT
                elif user_input == 'exit':
                    break
                # INVALID OPTION
                else:
                    print("invalid option. please try again")

        # ***** USER CHOSE PREDICT ***** #
        elif user_input == 'predict'.lower():
            while True:
                user_input = input("would you like to search for 'team' or 'player' predictions? (or 'exit' to quit): ")
                print()
                # USER CHOSE TEAM
                if user_input == 'team'.lower():
                    team1 = input("enter the first team: ")
                    team2 = input("enter the opposing team: ")

                    match_predictor(team1, team2)
                # USER CHOSE PLAYER
                elif user_input == 'player'.lower():
                    pass
                # USER CHOSE EXIT
                elif user_input == 'exit'.lower():
                    break
                # INVALID INPUT
                else:
                    print("invalid input. please try again")
        elif user_input == 'exit'.lower():
            break
        else:
            print("invalid option. please try again")
from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
import numpy as np
# import list of nba teams
from nba_api.stats.static import teams
# import endpoints to retrieve team info
from nba_api.stats.endpoints import teaminfocommon, commonteamroster, boxscoresummaryv2
# import list of NBA players
from nba_api.stats.static import players
# import endpoints to retrieve player stats
from nba_api.stats.endpoints import commonplayerinfo, playergamelog
# import datetime
from datetime import timezone, datetime, UTC
# import zoneinfo
from zoneinfo import ZoneInfo
from sklearn.linear_model import LogisticRegression
from scipy.stats import norm

# creates the flask app
app = Flask(__name__)

# print(df.columns)
# this keeps the trained model memory so we dont retrain every click
model_cache = {"clf": None}

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

# this function will get the players team abbreviations for use when displaying upcoming games
def get_player_team_abbreviation(player_id: int) -> str:
    try:
        df = commonplayerinfo.CommonPlayerInfo(player_id=player_id).get_data_frames()[0]
        abbr = str(df.at[0, "TEAM_ABBREVIATION"]).strip()
        return abbr if abbr and abbr != "None" else ""
    except Exception:
        return ""

# this function will extract the opponent name from the player game page
def extract_opp_from_matchup(matchup: str) -> str:
    """
    NBA API uses strings like 'NYK vs PHI' or 'NYK @ BOS'.
    Opponent is always the last token.
    """
    if not isinstance(matchup, str):
        return ""
    parts = matchup.strip().split()
    return parts[-1].upper() if parts else ""

# this function will extract the players performance against the specified opponent for the last 5 matches
def get_player_last_n_vs_opponent(player_id: int, opponent_abbr: str, n: int = 5):
    seasons_try = ["2024-25", "2023-24", "2022-23"]
    season_types = ("Playoffs", "Regular Season")
    dfs = []

    # collect game logs across a couple seasons & both season types
    for season in seasons_try:
        for st in season_types:
            try:
                gl = playergamelog.PlayerGameLog(
                    player_id=player_id,
                    season=season,
                    season_type_all_star=st
                )
                df = gl.get_data_frames()[0]
                if df is not None and not df.empty:
                    # ensure we keep season type so we can show it in the table
                    if "SEASON_TYPE" not in df.columns:
                        df = df.copy()
                        df["SEASON_TYPE"] = st
                    dfs.append(df)
                    tmp_all = pd.concat(dfs, ignore_index=True)
                    opp_series = tmp_all["MATCHUP"].apply(extract_opp_from_matchup)
                    if (opp_series == str(opponent_abbr).upper()).sum() >= n:
                        raise StopIteration  # jump to except to exit both loops
            except StopIteration:
                break
            except Exception as e:
                print(f"[DEBUG] get_player_last_n_vs_opponent: error {season} {st} -> {e}")
        else:
            # inner loop didn't break -> continue outer
            continue
        # inner loop broke with StopIteration
        break

    if not dfs:
        return []  # no data

    all_logs = pd.concat(dfs, ignore_index=True)

    # robust opponent filter: parse from MATCHUP's last token
    try:
        opp_series = all_logs["MATCHUP"].apply(extract_opp_from_matchup)
        mask = (opp_series == str(opponent_abbr).upper())
        vs_df = all_logs.loc[mask].copy()
    except Exception:
        vs_df = pd.DataFrame()

    if vs_df.empty:
        return []

    # parse game date for sorting (handle typical 'Jan 15, 2025' and fallbacks)
    vs_df["GAME_DATE_PARSED"] = pd.to_datetime(
        vs_df["GAME_DATE"], format="%b %d, %Y", errors="coerce"
    )
    if vs_df["GAME_DATE_PARSED"].isna().mean() > 0.5:
        vs_df["GAME_DATE_PARSED"] = pd.to_datetime(vs_df["GAME_DATE"], errors="coerce")

    # sort newest -> oldest and keep last N meetings vs that opponent
    vs_df = vs_df.sort_values("GAME_DATE_PARSED", ascending=False, na_position="last").head(n)

    # format shooting % to 0–100 scale (like you do elsewhere)
    for col in ("FG_PCT", "FG3_PCT", "FT_PCT"):
        if col in vs_df.columns:
            vs_df[col] = (vs_df[col] * 100).round(1).astype(float)

    # shape into list of dicts your template can loop over
    rows = []
    for _, row in vs_df.iterrows():
        rows.append({
            "Game Date": row.get("GAME_DATE", ""),
            "Matchup": row.get("MATCHUP", ""),
            "Season Type": row.get("SEASON_TYPE", ""),
            "W/L": row.get("WL", ""),
            "MIN": row.get("MIN", ""),
            "PTS": row.get("PTS", ""),
            "REB": row.get("REB", ""),
            "AST": row.get("AST", ""),
            "STL": row.get("STL", ""),
            "BLK": row.get("BLK", ""),
            "TOV": row.get("TOV", ""),
            "FG%": row.get("FG_PCT", ""),
            "3PM": row.get("FG3M", ""),
            "3P%": row.get("FG3_PCT", ""),
            "FT%": row.get("FT_PCT", ""),
            "+/-": row.get("PLUS_MINUS", ""),
        })
    return rows

# this function will extract the stats from the last 5 games a team has versed a specified team
def get_team_last_n_vs_opponent_from_csv(
    team_abbr: str,
    opp_abbr: str,
    n: int = 5,
    csv_path: str = "nba_games_2023_to_2025.csv",
):
    """
    Returns a list of dict rows for the last N games this TEAM played vs the given OPP,
    from the TEAM's perspective, using your aggregated CSV.
    Each row includes: Game Date, Matchup, Season Type, Points, Rebounds, Assists, Turnovers, Win.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return []

    # normalize columns we rely on
    for col in ["TEAM ABBR", "OPP ABBR", "GAME DATE"]:
        if col not in df.columns:
            return []

    # coerce dates once (avoids SettingWithCopy warnings downstream)
    df = df.copy()
    df["GAME DATE"] = pd.to_datetime(df["GAME DATE"], errors="coerce")

    # your CSV sometimes has SEASON_TYPE or "Season Type"—standardize to SEASON_TYPE
    if "SEASON_TYPE" not in df.columns and "Season Type" in df.columns:
        df["SEASON_TYPE"] = df["Season Type"]

    # filter to this team vs this opponent
    mask = (
        df["TEAM ABBR"].astype(str).str.upper().eq(team_abbr.upper())
        & df["OPP ABBR"].astype(str).str.upper().eq(opp_abbr.upper())
    )
    sub = df.loc[mask].sort_values("GAME DATE", ascending=False).head(n)

    # build rows for template
    rows = []
    for _, r in sub.iterrows():
        # matchup string (use HOME/AWAY if present)
        if "HOME/AWAY" in r and isinstance(r["HOME/AWAY"], str):
            sep = "vs" if r["HOME/AWAY"] == "Home" else "@"
        else:
            # fallback if HOME/AWAY missing
            sep = "vs"
        matchup = f"{team_abbr.upper()} {sep} {opp_abbr.upper()}"

        rows.append({
            "Game Date": r["GAME DATE"].strftime("%b %d, %Y") if pd.notna(r["GAME DATE"]) else "",
            "Matchup": matchup,
            "Season Type": r.get("SEASON_TYPE", ""),
            "Points": int(r["POINTS"]) if pd.notna(r.get("POINTS")) else None,
            "Rebounds": int(r["REBOUNDS"]) if pd.notna(r.get("REBOUNDS")) else None,
            "Assists": int(r["ASSISTS"]) if pd.notna(r.get("ASSISTS")) else None,
            "Turnovers": int(r["TURNOVERS"]) if pd.notna(r.get("TURNOVERS")) else None,
            "Win": int(r["WIN"]) if pd.notna(r.get("WIN")) else None,
        })
    return rows

# this function will get the 2025-26 schedule for the selected team
def get_upcoming_games(team_abbr: str, n: int = 5):
    # url for the nba's json schedule file
    url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
    # makes sure abbreviation is uppercase
    team_abbr = (team_abbr or "").upper()
    # creates timezone object for eastern time
    ET = ZoneInfo("America/New_York")  

    # this helper function takes any value and ensures its a clean string
    def clean(val):
        # if its not a string, return ""
        if not isinstance(val, str):
            return ""
        # if its TBD, (TBD) or empty, return "" otherwise return stripped string
        v = val.strip()
        return "" if v in {"", "TBD", "(TBD)"} else v

    # fetches json scheudle from the nba
    try:
        # uses user agent so nba.com doesn't reject the request, will time out if it takes more than 6 seconds
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        data = resp.json()
        # game_dates will list all game blocks in upcoming season
        game_dates = data.get("leagueSchedule", {}).get("gameDates", [])
    except Exception as e:
        print("[DEBUG] schedule fetch failed:", e)
        return []

    # here we define the season window
    # july 1, 2025 00:00:00 to june 30, 2026 23:59:59
    season_start = datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
    season_end   = datetime(2026, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc) # stores utc to filter out past games

    # create an empty list where we will store upcoming games for selected team
    results = []
    # loops over each gameDate block in the json
    for gd in game_dates:
        # then loops over each actual game
        for g in gd.get("games", []):
            # safely pulls team abbr for the home and away teams
            home_tri = ((g.get("homeTeam") or {}).get("teamTricode")) or ""
            away_tri = ((g.get("awayTeam") or {}).get("teamTricode")) or ""
            # makes sure they are uppercase
            home = home_tri.upper() if isinstance(home_tri, str) else ""
            away = away_tri.upper() if isinstance(away_tri, str) else ""
            # skips game if home/away abbr are missing or selected team abbr is not playing
            if not home or not away or team_abbr not in (home, away):
                continue
            
            # gets the scheduled tip off time from json
            dt_str = g.get("gameDateTimeUTC")
            # if its not a string, skip
            if not isinstance(dt_str, str):
                continue
            # convert from iso string to python datetime in utc
            try:
                dt_utc = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except Exception:
                continue

            # skip games that are outside of 2025-26 season window or already happened
            if not (season_start <= dt_utc <= season_end) or dt_utc < now_utc:
                continue
            
            # converts from utc to eastern time
            dt_et = dt_utc.astimezone(ET)
            # formats date to "Month Day, Year"
            date_et_str = dt_et.strftime("%B %d, %Y")

            # figures out the type of game
            label = clean(g.get("gameLabel"))
            # if gameLabel is read properly we return it
            if label:
                game_type = label
            # if its missing, fall back to gameId prefix or display unknown
            else:
                gid = str(g.get("gameId", ""))
                prefix = gid[:3]
                game_type = {
                    "001": "Preseason",
                    "002": "Regular Season",
                    "003": "All-Star",
                    "004": "Playoffs",
                    "005": "Play-In",
                }.get(prefix, "Unknown")

            # get the games tip off time and arena, if missing display (TBD)
            time_et = clean(g.get("gameStatusText")) or "(TBD)"
            arena   = clean(g.get("arenaName")) or "(TBD)"

            # get the games week number and side cup if available
            week_name = clean(g.get("weekName"))            
            game_sub  = clean(g.get("gameSubLabel"))        

            # build descriptive label for notes (week)
            label_for_notes = label or game_type
            # if both label and subLabel exist, combine
            #otherwise, if only label display only label or if none then ""
            label_part = f"{label_for_notes} : {game_sub}" if (label_for_notes and game_sub) \
                         else (label_for_notes if label_for_notes else "")

            # combines week name and label_part into one string separated by comma
            notes_parts = []
            if week_name:
                notes_parts.append(week_name)
            if label_part:
                notes_parts.append(label_part)
            notes = ", ".join(notes_parts)

            # build our results dictionary for this game with everything we need
            results.append({
                "game_id": str(g.get("gameId", "")),
                "date": date_et_str,          
                "time_et": time_et,           
                "home_abbr": home,
                "away_abbr": away,
                "is_home": (team_abbr == home),
                "game_type": game_type,       
                "arena": arena,               
                "notes": notes,               
                "when": dt_utc,               
            })

    # sorts all of the team's games chronologically (by when utc datetime)
    results.sort(key=lambda x: x["when"])
    # takes only the first n games, removes the hidden when field and returns cleaned list
    return [{k: v for k, v in r.items() if k != "when"} for r in results[:n]]

# this function will find a selected game in the 2025-26 schedule
def find_game_in_schedule(game_id: str, timeout: float = 6.0):
    # url for the nba's json schedule file
    url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
    # creates timezone object for eastern time
    ET = ZoneInfo("America/New_York") 

    # fetches json scheudle from the nba
    try:
        # uses user agent so nba.com doesn't reject the request, will time out if it takes more than 6 seconds
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        data = resp.json()
        # game_dates will list all game blocks in upcoming season
        game_dates = data.get("leagueSchedule", {}).get("gameDates", [])
    except Exception as e:
        print("[DEBUG] schedule fetch failed:", e)
        return []

    # loops over each gameDate block in the json
    for gd in game_dates:
        # then loops over each actual game
        for g in gd.get("games", []):
            # if current game's gameId doesn't match the one we are looking for, skip it
            if str(g.get("gameId", "")) != str(game_id):
                continue

            # extract homeTeam and awayTeam blocks from json or {} if missing
            home = (g.get("homeTeam") or {})
            away = (g.get("awayTeam") or {})

            # builds full name of teams by combining city and name
            home_full = f"{(home.get('teamCity') or '').strip()} {(home.get('teamName') or '').strip()}".strip()
            away_full = f"{(away.get('teamCity')  or '').strip()} {(away.get('teamName')  or '').strip()}".strip()

            # gets the scheduled tip off time from json
            dt_et_str = ""
            dt_utc_str = g.get("gameDateTimeUTC")
            if isinstance(dt_utc_str, str) and dt_utc_str:
                # convert from iso string to python datetime in utc and formats date
                try:
                    dt_utc = datetime.fromisoformat(dt_utc_str.replace("Z", "+00:00"))
                    dt_et_str = dt_utc.astimezone(ET).strftime("%B %d, %Y")
                except Exception:
                    pass

            # extract match type and week/game info
            game_label = (g.get("gameLabel") or "").strip()        
            game_sub   = (g.get("gameSubLabel") or "").strip()     
            week_name  = (g.get("weekName") or "").strip()    

            # builds week/game info text      
            label_part = f"{game_label} : {game_sub}" if (game_label and game_sub) else game_label
            notes = ", ".join([x for x in (week_name, label_part) if x])

            # returns dictionary with relevant info for this game
            return {
                "home_full": home_full or (home.get("teamTricode") or "Home Team"),
                "away_full": away_full or (away.get("teamTricode") or "Away Team"),
                "home_abbr": (home.get("teamTricode") or "").upper(),
                "away_abbr": (away.get("teamTricode") or "").upper(),
                "arena": (g.get("arenaName") or "").strip(),
                "date_et": dt_et_str,                         
                "time_et_text": (g.get("gameStatusText").upper() or "").strip(),  
                "label": game_label,
                "sub_label": game_sub,
                "notes": notes,
            }

    return {}

# this function will load the csv into a dataframe and build a small training matrix
def load_training_df_and_features():
    # load our stats data 
    df = pd.read_csv('nba_games_2023_to_2025.csv')

    # ensure the GAME DATE column is datetime (we use it for sorting/rest days)
    if not np.issubdtype(df["GAME DATE"].dtype, np.datetime64):
        df["GAME DATE"] = pd.to_datetime(df["GAME DATE"], errors="coerce")

    # convert text "Home"/"Away" to a simple numeric flag (Home=1, Away=0)
    home_away_map = {"Home": 1, "Away": 0}
    df["HOME_FLAG"] = df["HOME/AWAY"].map(home_away_map).fillna(0).astype(int)

    # features (X) and label (y)
    X = df[["POINTS", "REBOUNDS", "ASSISTS", "TURNOVERS", "HOME_FLAG"]].copy()
    y = df["WIN"].astype(int)

    # drop any rows with missing values so model training is safe
    mask = ~X.isna().any(axis=1) & y.notna()
    X = X[mask]
    y = y[mask]
    return df, X, y

# this function will either train the small logistic regression model once or reuse it
def train_or_get_cache_model():
    # if we already have a trained model stored in model_cache, reuse it
    if model_cache["clf"] is not None:
        return model_cache["clf"]
    
    # otherwise load training data (features X, labels y)
    _, X, y = load_training_df_and_features()
    if len(X) < 100:
        model_cache["clf"] = None
        return None
    
    # train new logistic regression model with up to 1000 iterations
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X,y)
    # save it into the cache so next call can reuse it
    model_cache["clf"] = clf
    return clf

# this function will compute averages over its last n games, return small dict with exact features
def compute_last_n_game_averages_for_team(team_df: pd.DataFrame, n: int = 10):
    # if the team df is empty, return none
    if team_df.empty:
        return None
    
    # sort by game date descending and take the last n games
    recent = team_df.sort_values("GAME DATE", ascending=False).head(n)
    # return dictionary of mean values for each stat
    return {
        "POINTS": recent["POINTS"].mean(),
        "REBOUNDS": recent["REBOUNDS"].mean(),
        "ASSISTS": recent["ASSISTS"].mean(),
        "TURNOVERS": recent["TURNOVERS"].mean(),
    }

# this function converts avgs + home/away flag into models expected feature order
def build_feature_vector_from_averages(averages, is_home_flag: int):
    return pd.DataFrame([{
        "POINTS": averages["POINTS"],
        "REBOUNDS": averages["REBOUNDS"],
        "ASSISTS": averages["ASSISTS"],
        "TURNOVERS": averages["TURNOVERS"],
        "HOME_FLAG": is_home_flag
    }])

# this function looks at the last head-to-head games between the two teams
def compute_head_to_head_win_rate_home_perspective(df: pd.DataFrame, home_abbr: str, away_abbr: str, meetings_to_look: int = 6) -> float:
    # filter games where team = home_abbr and app = away_abbr
    mask = (df["TEAM ABBR"].str.upper() == home_abbr.upper()) & (df["OPP ABBR"].str.upper() == away_abbr.upper())
    h2h = df.loc[mask].sort_values("GAME DATE", ascending=False).head(meetings_to_look)

    # if no recent games found, default to 50%
    if h2h.empty:
        return 0.5
    # otherwise return the average of the win column
    return float(h2h["WIN"].mean())

# this function returns the home court advantage value
def get_home_court_baseline_bump() -> float:
    return 0.05 

# this function returns how many full days before today the team last played
def days_since_last_game_for_team(df: pd.DataFrame, team_abbr: str, as_of_date: pd.Timestamp) -> int:
    # finds all games before as_of_date for the given team
    played = df[(df["TEAM ABBR"].str.upper() == team_abbr.upper()) & (df["GAME DATE"] < as_of_date)]

    # if no previous games, return 0 rest days
    if played.empty:
        return 0
    
    # find the lastest game date, normalize to midnight
    last_game_day = played["GAME DATE"].max().normalize()
    # subtract from as_of_date to count days of rest
    return int((as_of_date.normalize() - last_game_day).days)

# this function converts rest-days into a small probability bump for the home team
def convert_rest_difference_to_bump(home_minus_away_days: int) -> float:
    # clamp the value between -3 and +3 days
    rd = max(-3, min(3, home_minus_away_days))
    # each extra rest day add a 2% bump
    return 0.02 * rd

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
    
    # find the player's current team abbreviation
    team_abbr = get_player_team_abbreviation(player_id)

    # get next 5 games using the same helper for team stats page
    upcoming_games = get_upcoming_games(team_abbr, n=5) if team_abbr else []

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
                           player_id=player_id,
                           player_recent_games=player_recent_games,
                           upcoming_games=upcoming_games,
                           team_abbr=team_abbr)

# route for the players game page
@app.route("/player_game/<int:player_id>/<game_id>")
def player_game_page(player_id, game_id):
    # get player name from API
    try:
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id).get_data_frames()[0]
        player_name = str(info.at[0, "DISPLAY_FIRST_LAST"]).strip()
    except Exception:
        player_name = "Unknown Player"

    # get player + team info
    team_abbr = get_player_team_abbreviation(player_id)
    meta = find_game_in_schedule(game_id)

    if not meta:
        return f"<h1>Game {game_id} not found in schedule</h1>"
    
    # this function turns team name into images/team_name_logo.png
    def build_logo_filename(team_name: str) -> str:
        return f"images/{team_name.lower().replace(' ', '_')}_logo.png"

    home_name = meta["home_full"]
    away_name = meta["away_full"]

    home_logo = build_logo_filename(home_name)
    away_logo = build_logo_filename(away_name)

    # player team + opponent team abbr
    player_team_abbr = get_player_team_abbreviation(player_id)
    home_abbr = meta.get("home_abbr", "")
    away_abbr = meta.get("away_abbr", "")
    opponent_abbr = away_abbr if (player_team_abbr and player_team_abbr == home_abbr) else home_abbr

    # last 5 vs this opponent
    last5_vs_opp = get_player_last_n_vs_opponent(player_id, opponent_abbr, n=5)

    # build context
    return render_template(
        "player_game_page.html",
        player_id=player_id,
        player_name=player_name,
        game_id=game_id,
        home_full=meta.get("home_full"),
        away_full=meta.get("away_full"),
        home_name=home_name,
        away_name=away_name,
        home_logo=home_logo,
        away_logo=away_logo,
        date_et=meta.get("date_et"),
        time_et=meta.get("time_et_text"),
        arena=meta.get("arena"),
        notes=meta.get("notes"),
        home_abbr=home_abbr,
        away_abbr=away_abbr,
        opponent_abbr=opponent_abbr,
        player_last5_vs_opponent=last5_vs_opp,
    )

# route for predicting a player's performance vs opponent (PTS, 3PM, REB, AST, TOV, FTM)
@app.route("/api/player_predict/<int:player_id>/<game_id>")
def api_player_predict(player_id, game_id):
    # get game meta (opponent info)
    meta = find_game_in_schedule(game_id)
    if not meta:
        return jsonify({"error": "game not found"}), 404

    # determine opponent abbreviation
    player_team_abbr = get_player_team_abbreviation(player_id)
    home_abbr = meta.get("home_abbr", "")
    away_abbr = meta.get("away_abbr", "")
    opponent_abbr = away_abbr if (player_team_abbr and player_team_abbr == home_abbr) else home_abbr

    # get last 5 games for this player vs this opponent
    last5 = get_player_last_n_vs_opponent(player_id, opponent_abbr, n=5)
    if not last5:
        return jsonify({
            "player_id": player_id,
            "game_id": game_id,
            "opponent": opponent_abbr,
            "features": {},
            "reason": "No recent games vs opponent"
        })

    # features we want to predict
    feature_map = {
        "PTS": [10, 15, 20],   # thresholds for points
        "3PM": [2, 3, 4],      # 3-pointers made
        "REB": [5, 7, 10],     # rebounds
        "AST": [3, 5, 7],      # assists
        "TOV": [2, 3, 5],      # turnovers
    }

    results = {}

    # loop over each feature and compute probabilities
    for feature, thresholds in feature_map.items():
        try:
            values = [float(row.get(feature, 0)) for row in last5 if row.get(feature) not in ("", None)]
        except Exception:
            values = []

        if not values:
            results[feature] = [{"condition": "N/A", "prob": "No data"}]
            continue

        avg = np.mean(values)
        std = np.std(values) if np.std(values) > 0 else 1.0

        feature_probs = []
        for t in thresholds:
            # probability over threshold = 1 - CDF(t)
            p_over = 1 - norm.cdf(t, loc=avg, scale=std)
            p_under = 1 - p_over

            feature_probs.append({"condition": f"Over {t}", "prob": round(100 * p_over, 1)})
            feature_probs.append({"condition": f"Under {t}", "prob": round(100 * p_under, 1)})

        results[feature] = feature_probs

    return jsonify({
        "player_id": player_id,
        "game_id": game_id,
        "opponent": opponent_abbr,
        "features": results
    })

# route for the teams statistics page
@app.route('/team/<team_abbr>')
def team_stats(team_abbr):
    # load our stats data 
    df = pd.read_csv('nba_games_2023_to_2025.csv')

    df['GAME DATE'] = pd.to_datetime(df['GAME DATE'], errors='coerce')

    team_games = df.loc[df['TEAM ABBR'].str.upper() == team_abbr.upper()].copy()

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
    }).copy()

    # format the dates 
    games['Game Date'] = games['Game Date'].dt.strftime("%B %d, %Y")

    # here we will extract the win-loss for the team
    # define 2024-25 season window (Oct 2024 – Jun 2025)
    season_start = pd.Timestamp("2024-10-22")
    season_end   = pd.Timestamp("2025-06-30")

    games_2024_25 = team_games[
        (team_games['GAME DATE'] >= season_start) &
        (team_games['GAME DATE'] <= season_end)
    ]

    wins_2024_25 = games_2024_25['WIN'].sum()
    losses_2024_25 = len(games_2024_25) - wins_2024_25
    record_2024_25 = f"{int(wins_2024_25)} - {int(losses_2024_25)}"

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

    upcoming_games = get_upcoming_games(team_abbr, n=5)

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
                        roster=roster,
                        record_2024_25=record_2024_25,
                        upcoming_games=upcoming_games)

# route for the team prediction functionality
@app.route("/api/predict/<game_id>")
def api_predict(game_id):
    # find who plays + when, from your schedule helper
    meta = find_game_in_schedule(game_id)
    # if the game id isn't found in the schedule, return 404 error
    if not meta:
        return jsonify({"error": "game not found"}), 404

    # retrieve team names and abbreviations
    home_name = meta.get("home_full", "Home Team")
    away_name = meta.get("away_full", "Away Team")
    home_abbr = meta.get("home_abbr", "")
    away_abbr = meta.get("away_abbr", "")

    # load csv and train model if needed
    df, X_train, y_train = load_training_df_and_features()
    clf = train_or_get_cache_model()
    # if there is not enough data, return neutral 50/50 with reason
    if clf is None:
        return jsonify({
            "game_id": game_id,
            "prediction": f"{home_name} vs {away_name}",
            "home_name": home_name,
            "away_name": away_name,
            "probabilities": {"home": 50.0, "away": 50.0},
            "accuracy": None,
            "explain": {"reason": "not enough training data"}
        })

    # compute each team’s recent form (last 10 games)
    # filter big df down to rows for each team
    df_home = df[df["TEAM NAME"].str.lower() == home_name.lower()]
    df_away = df[df["TEAM NAME"].str.lower() == away_name.lower()]
    # turn those last 10 rows into averages for each stats
    avgs_home = compute_last_n_game_averages_for_team(df_home, n=10)
    avgs_away = compute_last_n_game_averages_for_team(df_away, n=10)

    # if one team doesn't have any recent games in the csv, fall back to 50/50 with reason
    if not avgs_home or not avgs_away:
        return jsonify({
            "game_id": game_id,
            "prediction": f"{home_name} vs {away_name}",
            "home_name": home_name,
            "away_name": away_name,
            "probabilities": {"home": 50.0, "away": 50.0},
            "accuracy": float((clf.predict(X_train) == y_train).mean()),
            "explain": {"reason": "insufficient recent games for one team"}
        })

    # base model P(win) for each side, from the small logistic regression
    # build one row feature tables in the same column order used for training
    x_home = build_feature_vector_from_averages(avgs_home, is_home_flag=1)
    x_away = build_feature_vector_from_averages(avgs_away, is_home_flag=0)
    # predict_proba returns either 1 or 0 where 1 is WIN
    p_home_win = float(clf.predict_proba(x_home)[0, 1])
    p_away_win = float(clf.predict_proba(x_away)[0, 1])

    # head-to-head home team’s win rate vs this opponent over last 6 meetings
    h2h_home_win_rate = compute_head_to_head_win_rate_home_perspective(
        df,
        # use abbreviations from schedule, if missing fall back to team rows we just filtered
        home_abbr or (df_home["TEAM ABBR"].iloc[0] if not df_home.empty else ""),
        away_abbr or (df_away["TEAM ABBR"].iloc[0] if not df_away.empty else ""),
        meetings_to_look=6
    )
    # away rate is the complement
    h2h_away_win_rate = 1.0 - h2h_home_win_rate

    # constant home-court baseline (tiny tilt toward home team)
    home_court = get_home_court_baseline_bump()

    # rest-day bump: parse ET date; if parsing fails, fall back to latest CSV date
    try:
        as_of_date = pd.to_datetime(meta.get("date_et"), format="%B %d, %Y", errors="coerce")
    except Exception:
        as_of_date = None
    if pd.isna(as_of_date):
        as_of_date = df["GAME DATE"].max()

    # compute full days since each team's previous game (positive difference favors home team)
    home_days_rest = days_since_last_game_for_team(df, home_abbr or (df_home["TEAM ABBR"].iloc[0] if not df_home.empty else ""), as_of_date)
    away_days_rest = days_since_last_game_for_team(df, away_abbr or (df_away["TEAM ABBR"].iloc[0] if not df_away.empty else ""), as_of_date)
    rest_diff = home_days_rest - away_days_rest                         # positive means HOME is more rested
    rest_bump = convert_rest_difference_to_bump(rest_diff)              # small signed bump in [-0.06, +0.06]

    # blend everything together (weights are easy to adjust)
    weight_model    = 0.80  # main signal: the small logistic regression
    weight_h2h      = 0.15  # recent head-to-head
    weight_homec    = 0.05  # constant home-court baseline
    weight_rest     = 0.05  # rest days effect

    blended_home = (
        weight_model * p_home_win +             # model probability for home
        weight_h2h   * h2h_home_win_rate +      # recent h2h for home
        weight_homec * (0.5 + home_court) +     # turn 5% edge into 55/45 source
        weight_rest  * (0.5 + rest_bump)        # rest bump as another small source
    )
    blended_away = (
        weight_model * p_away_win +             # model probability for away
        weight_h2h   * h2h_away_win_rate +      # recent h2h for away (complement)
        weight_homec * (0.5 - home_court) +     # opposite of home source
        weight_rest  * (0.5 - rest_bump)        # opposite of rest source
    )

    # normalize to exactly two buckets that sum to 100%
    total = blended_home + blended_away
    if total <= 0:
        # safety fallback, shouldn't happen
        home_pct = away_pct = 50.0
    else:
        home_pct = 100.0 * blended_home / total
        away_pct = 100.0 * blended_away / total

    # pick a label + simple training accuracy (we can replace with validation later)
    predicted_label = f"{home_name} wins" if home_pct >= away_pct else f"{away_name} wins"
    training_accuracy = float((clf.predict(X_train) == y_train).mean())

    # respone with json the front end expects
    return jsonify({
        "game_id": game_id,
        "prediction": predicted_label,
        "home_name": home_name,
        "away_name": away_name,
        "probabilities": {"home": round(home_pct, 2), "away": round(away_pct, 2)},
        "accuracy": round(training_accuracy, 4),
        "explain": {
            "h2h_home": round(h2h_home_win_rate, 3),
            "home_rest_days": int(home_days_rest),
            "away_rest_days": int(away_days_rest),
            "rest_diff": int(rest_diff),
            "rest_bump": round(rest_bump, 3),
            "weights": {
                "model": weight_model,
                "h2h": weight_h2h,
                "home_court": weight_homec,
                "rest": weight_rest
            }
        }
    })

# route for the game page
@app.route("/game/<game_id>")
def game_page(game_id):
    meta = find_game_in_schedule(game_id)
    if not meta:
        return f"<h1>No schedule data found for game {game_id}</h1>"

    # logo helper
    def build_logo_filename(team_name: str) -> str:
        return f"images/{team_name.lower().replace(' ', '_')}_logo.png"

    home_name = meta.get("home_full", "Home Team")
    away_name = meta.get("away_full", "Away Team")

    home_abbr = meta.get("home_abbr", "")
    away_abbr = meta.get("away_abbr", "")

    if not home_abbr or not away_abbr:
        try:
            name_to_abbr = {t["full_name"]: t["abbreviation"] for t in teams.get_teams()}
            if not home_abbr:
                home_abbr = name_to_abbr.get(home_name, "")
            if not away_abbr:
                away_abbr = name_to_abbr.get(away_name, "")
        except Exception:
            pass

    home_logo = build_logo_filename(home_name)
    away_logo = build_logo_filename(away_name)

    # only one table: last 5 meetings home vs away
    last5_h2h = []
    if home_abbr and away_abbr:
        last5_h2h = get_team_last_n_vs_opponent_from_csv(home_abbr, away_abbr, n=5)

    return render_template(
        "game_page.html",
        game_id=game_id,
        home_name=home_name,
        away_name=away_name,
        home_logo=home_logo,
        away_logo=away_logo,
        date_et=meta.get("date_et", ""),
        time_et_text=meta.get("time_et_text", ""),
        arena=meta.get("arena", ""),
        label=meta.get("label", ""),
        sub_label=meta.get("sub_label", ""),
        notes=meta.get("notes", ""),
        home_abbr=home_abbr,
        away_abbr=away_abbr,
        last5_h2h=last5_h2h,
    )

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
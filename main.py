#! /usr/bin/python3

import datetime
from espn_api.football import League
from flask import Flask, request, render_template_string

app = Flask(__name__)
""" def find_optimal_players_for_position(players: list, slot: str) -> League.BoxPlayer:
    Return a list of players with the highest points for a given slot.
"""

class Accolade:

    def __init__(self, title, team, points):
        self.title = title
        self.team = team
        self.points = points
        self.opp_score = 0
        self.effeciency = 0
        self.projected = 0
        self.opponent = None
        self.optimal_score = 0
        self.player = None

    def __repr__(self):
        return self.points


def get_best_by_skill(lineup_copy: list, slot: str):
    """ gets the best player for a given slot from the provided list of players"""
    # turns FLEX like "RB/WR/TE" to ["RB", "WR", "TE"]
    eligible_players = [
        p for p in lineup_copy
        if slot in p.eligibleSlots
        and p.game_played == 100
        and not p.on_bye_week
    ]

    try:
        best_available = sorted(eligible_players, key=lambda x: x.points)[-1]
    except IndexError:
        print(f"No eligible players for: {slot}")
        return []
    lineup_copy.remove(best_available)

    return best_available


def get_optimal_lineup(lineup: list) -> float:
    """Compute the difference between optimal lineup and current lineup."""
    optimal_lineup = []
    lineup_slots = []
    for i in lineup:
        lineup_slots.append(i.slot_position)

    lineup_slots = [item for item in lineup_slots if item not in ("BE", "IR")]

    # ensures that main positions (ex: "RB") get priority over FLEX ones (ex: "WR/RB")
    lineup_slots = sorted(lineup_slots, key=len)
    lineup_copy = lineup.copy()

    for slot in lineup_slots:
        optimal_lineup.append(get_best_by_skill(lineup_copy, slot))

    return sum([x.points for x in optimal_lineup])

def get_team_awards(box_scores: list):
    """ gets the team based performance awards"""
    dominant_winner = Accolade("Most Dominant Win", box_scores[0].home_team, 0)
    narrowest_winner = Accolade("Closest Win", box_scores[0].home_team, 9999)
    highest_loser = Accolade("Most Undeserving Loss", box_scores[0].home_team, 0)
    lowest_winner = Accolade("Luckiest Win", box_scores[0].home_team, 9999)
    highest_scorer = Accolade("Highest Scorer", box_scores[0].home_team, 0)
    lowest_scorer = Accolade("Lowest Scorer", box_scores[0].home_team, 9999)

    for matchup in box_scores:
        home_team = matchup.home_team
        away_team = matchup.away_team
        home_score = matchup.home_score
        away_score = matchup.away_score

        # Determine winner and loser for the matchup
        if home_score > away_score:
            winner, loser = home_team, away_team
            winning_score, losing_score = home_score, away_score
        else:
            winner, loser = away_team, home_team
            winning_score, losing_score = away_score, home_score

        score_diff = abs(home_score - away_score)

        # Check for biggest win
        if score_diff > (dominant_winner.points - dominant_winner.opp_score):
            dominant_winner.team = winner
            dominant_winner.points = winning_score
            dominant_winner.opp_score = losing_score
            dominant_winner.opponent = loser

        # Check for narrowest win
        if score_diff < (narrowest_winner.points - narrowest_winner.opp_score):
            narrowest_winner.team = winner
            narrowest_winner.points = winning_score
            narrowest_winner.opp_score = losing_score
            narrowest_winner.opponent = loser

        # Check for highest scoring loser
        if losing_score > highest_loser.points:
            highest_loser.team = loser
            highest_loser.points = losing_score
            highest_loser.opp_score = winning_score
            highest_loser.opponent = winner

        # Check for lowest scoring winner
        if winning_score < lowest_winner.points:
            lowest_winner.team = winner
            lowest_winner.points = winning_score
            lowest_winner.opp_score = losing_score
            lowest_winner.opponent = loser

        # highest scorer
        if winning_score > highest_scorer.points:
            highest_scorer.team = winner
            highest_scorer.points = winning_score

        # highest scorer
        if losing_score < lowest_scorer.points:
            lowest_scorer.team = loser
            lowest_scorer.points = losing_score

    return [dominant_winner,
            narrowest_winner,
            highest_loser,
            lowest_winner,
            highest_scorer,
            lowest_scorer]

def get_lineup_awards(box_scores):

    best_manager = Accolade("Best Manager", None, 0)
    worst_manager = Accolade("Worst Manager", None, 9999)

    effeciency_dict = {}
    for matchup in box_scores:
        effeciency_dict[matchup.home_team] = get_roster_effeciency(matchup.home_lineup,
                                                                   matchup.home_score)
        effeciency_dict[matchup.away_team] = get_roster_effeciency(matchup.away_lineup,
                                                                   matchup.away_score)

    best_manager.team = max(effeciency_dict, key=lambda k: effeciency_dict[k][2])
    best_manager.points = effeciency_dict[best_manager.team][0]
    best_manager.optimal_score = effeciency_dict[best_manager.team][1]
    best_manager.effeciency = effeciency_dict[best_manager.team][2]


    worst_manager.team = min(effeciency_dict, key=lambda k: effeciency_dict[k][2])
    worst_manager.points = effeciency_dict[worst_manager.team][0]
    worst_manager.optimal_score = effeciency_dict[worst_manager.team][1]
    worst_manager.effeciency = effeciency_dict[worst_manager.team][2]

    return [best_manager, worst_manager]

def get_player_awards(box_scores):

    boom_player = Accolade("Biggest Boom", box_scores[0].home_team, 0)
    bust_player = Accolade("Biggest Bust", box_scores[0].home_team, 999)

    for matchup in box_scores:
        for lineup in [matchup.home_lineup, matchup.away_lineup]:
            for player in lineup:
                performance = player.points - player.projected_points
                if performance > boom_player.points:
                    boom_player.player = player
                    boom_player.points = performance
                    if boom_player.player in matchup.home_lineup:
                        boom_player.team = matchup.home_team
                    else:
                        boom_player.team = matchup.away_team
                if performance < bust_player.points:
                    bust_player.player = player
                    bust_player.points = performance
                    if bust_player.player in matchup.home_lineup:
                        bust_player.team = matchup.home_team
                    else:
                        bust_player.team = matchup.away_team

    return [boom_player, bust_player]


def get_accolades(box_scores: list):
    """ gets all the the accolades"""
    awards = get_team_awards(box_scores)
    awards += get_lineup_awards(box_scores)
    awards += get_player_awards(box_scores)

    return awards


def get_roster_effeciency(lineup, score):
    """ gets the roster effeciency"""
    optimal_score = round(get_optimal_lineup(lineup), 2)
    effeciency = round(score / optimal_score, 2)
    return (score, optimal_score, effeciency)

def prepare_card(accolade):

    try:
        opp_name = accolade.opponent.team_name
    except AttributeError:
        opp_name = ""

    try:
        player_points = accolade.player.points
        player_proj_points = accolade.player.projected_points
        player_name = accolade.player.name
    except AttributeError:
        player_points = 0
        player_proj_points = 0
        player_name = ""


    diff_score = accolade.points - accolade.opp_score
    team_name = accolade.team.team_name
    eff_score = accolade.effeciency * 100
    optimal = accolade.optimal_score

    boom_diff = player_points - player_proj_points
    bust_diff = player_proj_points - player_points

    subtitles = {
        "Most Dominant Win": f"{team_name} dominated '{opp_name}' by {diff_score:.2f} points!",
        "Closest Win": f"{team_name} beat '{opp_name}' by just {diff_score:.2f} points",
        "Most Undeserving Loss": f"{team_name} scored more than any other loser",
        "Luckiest Win": f"{team_name} scored less than any other winner",
        "Highest Scorer": "👑",
        "Lowest Scorer": "💩",
        "Best Manager": f"{team_name} scored {eff_score:.2f}% of their possible {optimal} points!",
        "Worst Manager": f"{team_name} scored {eff_score:.2f}% of their possible {optimal} points.",
        "Biggest Boom": f"{team_name} started {player_name}, the boom player of the week,"
                        f"scoring {boom_diff} more than projected!",
        "Biggest Bust": f"{team_name} started {player_name}, the boom player of the week,"
                        f"scoring {bust_diff} less than projected!",
    }

    card = {
        "title": accolade.title,  # Assuming accolade always has a title.
        "subtitle": subtitles.get(accolade.title, ""),
        "image": getattr(accolade.team, 'logo_url', None),
        "middle_text": getattr(accolade.team, 'team_name', ""),
        "middle_sub_text": None,
        "middle_sub_sub_text": None,
        "points": accolade.points  # Assuming accolade always has points.
    }

    # overrides for player cards
    if ("Boom" in accolade.title or "Bust" in accolade.title):
        card["middle_text"] = player_name
        card["middle_sub_text"] = f"{accolade.player.position} - {accolade.player.proTeam}"
        card["points"] = round(accolade.player.points, 2)


    return card


@app.route('/', methods=['GET', 'POST'])
def index():
    cards_data = []
    if request.method == 'POST':
        league_id = request.form.get('league_id')
        if league_id:
            league = League(league_id, datetime.date.today().year, debug=False)
            weekly_scores = league.box_scores(1)
            accolades = get_accolades(weekly_scores)
            for accolade in accolades:
                cards_data.append(prepare_card(accolade))

    return render_template_string('''
   <link rel="stylesheet" href="{{ url_for('static', filename='accolades.css') }}">

    <form action="/" method="post">
        Enter League ID: <input type="text" name="league_id">
        <input type="submit" value="Get Accolades">
    </form>

    <div class="cards-wrapper">
        {% for card in cards_data %}
            <div class="card">
                <h2>{{ card.title }}</h2>
                {% if card.subtitle %}<p>{{ card.subtitle }}</p>{% endif %}

                <div class="content-row">  <!-- Container div for flexbox -->
                    {% if card.image %}<img src="{{ card.image }}" alt="Image" style="width: 100px; height: 100px;">{% endif %}
                    <div>
                        <p>{{ card.middle_text }}</p>
                        {% if card.middle_sub_text %}<p>{{ card.middle_sub_text }}</p>{% endif %}
                        {% if card.middle_sub_sub_text %}<p>{{ card.middle_sub_sub_text }}</p>{% endif %}
                    </div>
                </div>

                <span class="points">{{ card.points }}</span>
            </div>
        {% endfor %}
    </div>
    ''', cards_data=cards_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
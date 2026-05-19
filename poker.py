import random
from collections import Counter
from itertools import combinations

# ─── Colors ───────────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"

def red(s):    return f"{RED}{s}{RESET}"
def green(s):  return f"{GREEN}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def bold(s):   return f"{BOLD}{s}{RESET}"
def dim(s):    return f"{DIM}{s}{RESET}"

# ─── Card Setup ───────────────────────────────────────────────────────────────

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {r: i for i, r in enumerate(RANKS, 2)}

def make_deck():
    return [(r, s) for s in SUITS for r in RANKS]

def card_str(card):
    r, s = card
    return red(f"{r}{s}") if s in ('♥', '♦') else f"{r}{s}"

def hand_str(cards):
    return "  ".join(card_str(c) for c in cards)

# ─── Hand Evaluation ──────────────────────────────────────────────────────────

def evaluate_hand(cards):
    """Returns (rank_score, tiebreaker_list) for a 5-7 card hand."""
    best = (0, [])
    for combo in combinations(cards, 5):
        score = score_five(combo)
        if score > best[0]:
            best = (score[0], score[1])
    return best

def score_five(cards):
    ranks = sorted([RANK_VALUES[c[0]] for c in cards], reverse=True)
    suits = [c[1] for c in cards]
    is_flush = len(set(suits)) == 1
    is_straight = (max(ranks) - min(ranks) == 4 and len(set(ranks)) == 5)
    # Ace-low straight
    if set(ranks) == {14, 2, 3, 4, 5}:
        is_straight = True
        ranks = [5, 4, 3, 2, 1]

    counts = Counter(ranks)
    freq = sorted(counts.values(), reverse=True)
    grouped = sorted(counts.keys(), key=lambda r: (counts[r], r), reverse=True)

    if is_straight and is_flush:
        return (8, ranks)
    if freq == [4, 1]:
        return (7, grouped)
    if freq == [3, 2]:
        return (6, grouped)
    if is_flush:
        return (5, ranks)
    if is_straight:
        return (4, ranks)
    if freq[0] == 3:
        return (3, grouped)
    if freq[:2] == [2, 2]:
        return (2, grouped)
    if freq[0] == 2:
        return (1, grouped)
    return (0, ranks)

HAND_NAMES = {
    8: "Straight Flush", 7: "Four of a Kind", 6: "Full House",
    5: "Flush", 4: "Straight", 3: "Three of a Kind",
    2: "Two Pair", 1: "One Pair", 0: "High Card"
}

# ─── Save / Load ──────────────────────────────────────────────────────────────

import json, os
SAVE_FILE = os.path.expanduser("~/.poker_save.json")

def save_bankroll(balance):
    with open(SAVE_FILE, 'w') as f:
        json.dump({'balance': balance}, f)
    print(dim(f"  Bankroll saved: ${balance:.2f}"))

def load_bankroll():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE) as f:
                return json.load(f).get('balance')
        except Exception:
            pass
    return None

# ─── Side Pots ────────────────────────────────────────────────────────────────

def compute_side_pots(contributions):
    """
    contributions: list of (name, amount_invested, folded)
    Returns list of {'amount': int, 'eligible': [name]}
    """
    levels = sorted(set(amt for _, amt, _ in contributions if amt > 0))
    pots = []
    prev = 0
    for lvl in levels:
        at_level = [(name, folded) for name, amt, folded in contributions if amt >= lvl]
        pot_amount = (lvl - prev) * len(at_level)
        eligible = [name for name, folded in at_level if not folded]
        if pot_amount > 0 and eligible:
            pots.append({'amount': pot_amount, 'eligible': eligible})
        prev = lvl
    return pots

# ─── AI Players ───────────────────────────────────────────────────────────────

PERSONAS = ['tight', 'aggressive', 'loose', 'maniac']
AI_NAMES = ['Alex', 'Blake', 'Casey', 'Dana', 'Eddie', 'Fran', 'Gabe', 'Harper']

class AIPlayer:
    def __init__(self, name, persona=None):
        self.name = name
        self.persona = persona or random.choice(PERSONAS)

    def decide(self, win_pct, to_call, pot):
        """Returns ('fold'|'call'|'check'|'raise', raise_amount)"""
        bluff = random.random() < 0.10
        p = self.persona

        if p == 'tight':
            if win_pct > 65 or bluff:     return ('raise', int(pot * 0.75))
            if win_pct > 35:              return ('call', to_call)
            return ('fold', 0)

        elif p == 'aggressive':
            if win_pct > 40 or bluff:     return ('raise', int(pot * 1.0))
            if win_pct > 22:              return ('call', to_call)
            return ('fold', 0)

        elif p == 'loose':
            if win_pct > 55:              return ('raise', int(pot * 0.5))
            if win_pct > 18 or bluff:     return ('call', to_call)
            return ('fold', 0)

        else:  # maniac
            if random.random() < 0.65:    return ('raise', int(pot * 1.5))
            return ('call', to_call)

# ─── Win Probability via Monte Carlo ──────────────────────────────────────────

def estimate_win_probability(player_hand, community_cards, num_players, simulations=2000):
    known = set(map(tuple, player_hand + community_cards))
    remaining_deck = [c for c in make_deck() if tuple(c) not in known]
    wins = 0
    ties = 0

    for _ in range(simulations):
        deck = remaining_deck[:]
        random.shuffle(deck)

        # Complete community cards to 5
        needed = 5 - len(community_cards)
        board = community_cards + deck[:needed]
        deck = deck[needed:]

        player_score = evaluate_hand(player_hand + board)

        # Deal hands to opponents
        opponent_scores = []
        for i in range(num_players - 1):
            opp_hand = deck[i*2:(i*2)+2]
            if len(opp_hand) < 2:
                break
            opponent_scores.append(evaluate_hand(opp_hand + board))

        if not opponent_scores:
            wins += 1
            continue

        best_opp = max(opponent_scores, key=lambda x: (x[0], x[1]))

        if (player_score[0], player_score[1]) > (best_opp[0], best_opp[1]):
            wins += 1
        elif (player_score[0], player_score[1]) == (best_opp[0], best_opp[1]):
            ties += 1

    win_pct = (wins / simulations) * 100
    tie_pct = (ties / simulations) * 100
    return win_pct, tie_pct

# ─── Display ──────────────────────────────────────────────────────────────────

def print_banner():
    print("\n" + bold("="*55))
    print(bold("          ♠ ♥  TEXAS HOLD'EM POKER  ♦ ♣"))
    print(bold("="*55))

def print_table(community, stage):
    labels = {"preflop": "", "flop": "FLOP", "turn": "TURN", "river": "RIVER"}
    print(f"\n  [ {labels.get(stage, stage)} ]  Board: ", end="")
    if community:
        print(hand_str(community))
    else:
        print("(no cards yet)")

def print_prob_bar(win_pct):
    filled = int(win_pct / 5)
    color = GREEN if win_pct >= 50 else (YELLOW if win_pct >= 30 else RED)
    bar = f"{color}{'█' * filled}{RESET}{dim('░' * (20 - filled))}"
    print(f"  Win chance:  [{bar}] {win_pct:.1f}%")

def print_ev(win_pct, to_call, pot):
    """Show expected value of calling."""
    if to_call <= 0:
        return
    win_prob = win_pct / 100
    ev = win_prob * pot - (1 - win_prob) * to_call
    ev_str = green(f"+${ev:.2f}") if ev >= 0 else red(f"-${abs(ev):.2f}")
    print(f"  EV of call:  {ev_str}")

def color_money(amount):
    if amount > 0:
        return green(f"+${amount:.2f}")
    elif amount < 0:
        return red(f"-${abs(amount):.2f}")
    return f"${amount:.2f}"

# ─── Betting ──────────────────────────────────────────────────────────────────

def betting_round(balance, pot, stage, current_bet=0, last_raise=None):
    """
    current_bet: the total bet amount players must match this street.
    last_raise:  size of the last raise (min re-raise must be >= this).
    Returns (new_balance, new_pot, action).
    """
    if last_raise is None:
        last_raise = current_bet if current_bet > 0 else 1

    to_call = current_bet  # human has put in $0 this street
    print(f"\n  Pot: {yellow(f'${pot:.2f}')}   To call: ${to_call:.2f}   Stack: {green(f'${balance:.2f}')}")

    if to_call > 0:
        pot_odds = to_call / (pot + to_call) * 100
        print(f"  Pot odds: need >{pot_odds:.0f}% win chance to call profitably")
    if to_call == 0:
        print(f"  Actions: [c]heck  [r]aise  [f]old")
    else:
        print(f"  Actions: [c]all ${to_call:.2f}  [r]aise  [a]ll-in ${balance:.2f}  [f]old")

    while True:
        choice = input("  > ").strip().lower()

        if choice == 'f':
            return balance, pot, 'fold'

        elif choice == 'c':
            if to_call == 0:
                print(dim("  Checked."))
                return balance, pot, 'check'
            else:
                call_amt = min(to_call, balance)
                balance -= call_amt
                pot += call_amt
                print(dim(f"  Called ${call_amt:.2f}."))
                return balance, pot, 'call'

        elif choice == 'a' and to_call > 0:
            pot += balance
            print(yellow(f"  ALL-IN! ${balance:.2f}"))
            balance = 0
            return balance, pot, 'allin'

        elif choice == 'r':
            min_raise_to = current_bet + last_raise
            print(f"  Min raise to: ${min_raise_to:.2f}   Your stack: ${balance:.2f}")
            try:
                raise_to = float(input("  Raise to total: $"))
            except ValueError:
                print("  Enter a number.")
                continue
            if raise_to < min_raise_to:
                print(f"  Must raise to at least ${min_raise_to:.2f}")
                continue
            if raise_to > balance + current_bet:
                print(f"  Not enough chips. Max raise to: ${balance + current_bet:.2f}")
                continue
            amount_to_add = raise_to - current_bet   # what player adds to pot
            amount_to_add = min(amount_to_add, balance)
            balance -= amount_to_add
            pot += amount_to_add
            print(dim(f"  Raised to ${raise_to:.2f}."))
            return balance, pot, raise_to   # return new current_bet level

        else:
            print("  Type c, r, or f.")

# ─── Main Game ────────────────────────────────────────────────────────────────

def play_game(practice=False):
    print_banner()
    if practice:
        print(yellow(bold("  [PRACTICE MODE] — Opponent hands are shown face-up")))

    # Starting bankroll — offer to load saved
    saved = load_bankroll()
    balance = None
    if saved:
        choice = input(f"\n  Saved bankroll found: ${saved:.2f}. Load it? [y/n]: ").strip().lower()
        if choice == 'y':
            balance = saved
            print(green(f"  Loaded ${balance:.2f}"))
    if balance is None:
        while True:
            try:
                balance = float(input("\n  Enter starting bankroll: $"))
                if balance > 0:
                    break
                print("  Must be positive.")
            except ValueError:
                print("  Enter a number.")

    # Number of players
    while True:
        try:
            num_players = int(input("  Number of players (2-9): "))
            if 2 <= num_players <= 9:
                break
            print("  Enter 2-9.")
        except ValueError:
            print("  Enter a number.")

    ai_players = [AIPlayer(AI_NAMES[i]) for i in range(num_players - 1)]
    print("\n  Opponents:")
    for ai in ai_players:
        print(f"    {ai.name} — {dim(ai.persona)}")

    game_count = 0

    while balance > 0:
        game_count += 1
        print(f"\n{'─'*55}")
        print(f"  GAME #{game_count}   Bankroll: ${balance:.2f}")
        print(f"{'─'*55}")

        # Blinds
        small_blind = max(1.0, round(balance * 0.02, 2))
        big_blind = small_blind * 2
        print(f"\n  Blinds — Small: ${small_blind:.2f}  Big: ${big_blind:.2f}")

        if balance < big_blind:
            print(f"\n  Not enough to post blinds. Game over!")
            break

        # Post big blind automatically
        balance -= big_blind
        pot = big_blind
        print(f"  You post big blind: ${big_blind:.2f}")

        # Deal
        deck = make_deck()
        random.shuffle(deck)
        player_hand = [deck.pop(), deck.pop()]
        community = []

        print(f"\n  Your hand:  {hand_str(player_hand)}")
        score = evaluate_hand(player_hand + community)
        print(f"  Hand rank:  {HAND_NAMES[score[0]]}")

        # Deal AI hands
        ai_hands = {ai.name: [deck.pop(), deck.pop()] for ai in ai_players}
        ai_folded = {ai.name: False for ai in ai_players}

        if practice:
            print("\n  Opponent hands (practice):")
            for ai in ai_players:
                print(f"    {ai.name}: {hand_str(ai_hands[ai.name])}")

        def ai_street_action(community_cards):
            nonlocal pot
            active_ai = [ai for ai in ai_players if not ai_folded[ai.name]]
            for ai in active_ai:
                ai_wp, _ = estimate_win_probability(ai_hands[ai.name], community_cards, num_players, simulations=400)
                action, raise_amt = ai.decide(ai_wp, 0, pot)
                if action == 'fold':
                    ai_folded[ai.name] = True
                    print(dim(f"  {ai.name} ({ai.persona}) folds."))
                elif action == 'raise' and raise_amt > 0:
                    pot += raise_amt
                    print(dim(f"  {ai.name} ({ai.persona}) raises ${raise_amt:.2f}."))
                else:
                    print(dim(f"  {ai.name} ({ai.persona}) calls."))

        # ── Pre-flop ──
        print_table(community, "preflop")
        win_pct, tie_pct = estimate_win_probability(player_hand, community, num_players)
        print_prob_bar(win_pct)
        print(f"  Tie chance: {tie_pct:.1f}%")
        print_ev(win_pct, big_blind, pot)

        balance, pot, action = betting_round(balance, pot, "preflop", current_bet=big_blind)
        if action == 'fold':
            print(f"\n  You folded. Lost ${big_blind:.2f} (blind).")
            print(f"  Bankroll: ${balance:.2f}")
            continue
        ai_street_action(community)

        # ── Flop ──
        community += [deck.pop(), deck.pop(), deck.pop()]
        print_table(community, "flop")
        score = evaluate_hand(player_hand + community)
        print(f"  Your best:  {HAND_NAMES[score[0]]}")
        win_pct, tie_pct = estimate_win_probability(player_hand, community, num_players)
        print_prob_bar(win_pct)

        balance, pot, action = betting_round(balance, pot, "flop", current_bet=0)
        if action == 'fold':
            print(f"\n  You folded.")
            print(f"  Bankroll: ${balance:.2f}")
            continue
        ai_street_action(community)

        # ── Turn ──
        community.append(deck.pop())
        print_table(community, "turn")
        score = evaluate_hand(player_hand + community)
        print(f"  Your best:  {HAND_NAMES[score[0]]}")
        win_pct, tie_pct = estimate_win_probability(player_hand, community, num_players)
        print_prob_bar(win_pct)

        balance, pot, action = betting_round(balance, pot, "turn", current_bet=0)
        if action == 'fold':
            print(f"\n  You folded.")
            print(f"  Bankroll: ${balance:.2f}")
            continue
        ai_street_action(community)

        # ── River ──
        community.append(deck.pop())
        print_table(community, "river")
        score = evaluate_hand(player_hand + community)
        print(f"  Your best:  {HAND_NAMES[score[0]]}")
        win_pct, tie_pct = estimate_win_probability(player_hand, community, num_players)
        print_prob_bar(win_pct)

        balance, pot, action = betting_round(balance, pot, "river", current_bet=0)
        if action == 'fold':
            print(f"\n  You folded.")
            print(f"  Bankroll: ${balance:.2f}")
            continue
        ai_street_action(community)

        # ── Showdown ──
        print(f"\n{'─'*55}")
        print(bold("  ♦  SHOWDOWN  ♦"))
        print(f"{'─'*55}")
        print(f"  Board:       {hand_str(community)}")
        print(f"  Your hand:   {hand_str(player_hand)}")

        player_score = evaluate_hand(player_hand + community)
        print(f"  Your best:   {bold(HAND_NAMES[player_score[0]])}")

        opponents = []
        for ai in ai_players:
            if not ai_folded[ai.name]:
                opp_hand = ai_hands[ai.name]
                opp_score = evaluate_hand(opp_hand + community)
                opponents.append((ai.name, opp_hand, opp_score))
                print(f"\n  {ai.name} ({dim(ai.persona)}): {hand_str(opp_hand)}  →  {HAND_NAMES[opp_score[0]]}")
            else:
                print(dim(f"\n  {ai.name} ({ai.persona}): folded"))

        # Build contributions for side pot calc (simplified: equal investment assumed)
        contributions = [('You', pot // num_players, False)]
        for ai in ai_players:
            contributions.append((ai.name, pot // num_players, ai_folded[ai.name]))
        pots = compute_side_pots(contributions)

        all_scores = {'You': (player_score[0], player_score[1])}
        for name, hand, score in opponents:
            all_scores[name] = (score[0], score[1])

        print()
        balance_before = balance
        for sp in pots:
            eligible = sp['eligible']
            best = max(eligible, key=lambda n: all_scores.get(n, (0, [])))
            best_score = all_scores.get(best, (0, []))
            winners = [n for n in eligible if all_scores.get(n, (0, [])) == best_score]
            split = sp['amount'] / len(winners)
            if 'You' in winners:
                balance += split
                print(green(bold(f"  ★  YOU WIN ${split:.2f}!")) + f"  ({HAND_NAMES[player_score[0]]})")
            else:
                print(red(f"  ✗  {winners[0]} wins ${split:.2f}."))

        net = balance - balance_before - big_blind
        print(f"  Net result:  {color_money(net)}")

        print(f"\n  Bankroll: ${balance:.2f}")
        save_bankroll(balance)

        # Play again?
        again = input("\n  Play another hand? [y/n]: ").strip().lower()
        if again != 'y':
            break

    print(f"\n{'='*55}")
    print(f"  Final Bankroll: ${balance:.2f}")
    print(f"  Hands played:   {game_count}")
    print(f"{'='*55}\n")

# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    print("\n" + bold("="*55))
    print(bold("          ♠ ♥  TEXAS HOLD'EM POKER  ♦ ♣"))
    print(bold("="*55))
    print("  [1] Cash Game")
    print("  [2] Practice Mode  (see opponent hands)")
    print("  [3] Quit")
    while True:
        choice = input("\n  Choose: ").strip()
        if choice == '1':
            play_game(practice=False)
        elif choice == '2':
            play_game(practice=True)
        elif choice == '3':
            print("\n  Thanks for playing!\n")
            break
        else:
            print("  Enter 1, 2, or 3.")

if __name__ == "__main__":
    main()

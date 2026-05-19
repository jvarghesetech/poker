import random
from collections import Counter
from itertools import combinations

# ─── Card Setup ───────────────────────────────────────────────────────────────

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {r: i for i, r in enumerate(RANKS, 2)}

def make_deck():
    return [(r, s) for s in SUITS for r in RANKS]

def card_str(card):
    return f"{card[0]}{card[1]}"

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
    print("\n" + "="*55)
    print("          ♠ ♥  TEXAS HOLD'EM POKER  ♦ ♣")
    print("="*55)

def print_table(community, stage):
    labels = {"preflop": "", "flop": "FLOP", "turn": "TURN", "river": "RIVER"}
    print(f"\n  [ {labels.get(stage, stage)} ]  Board: ", end="")
    if community:
        print(hand_str(community))
    else:
        print("(no cards yet)")

def print_prob_bar(win_pct):
    filled = int(win_pct / 5)
    bar = "█" * filled + "░" * (20 - filled)
    print(f"  Win chance:  [{bar}] {win_pct:.1f}%")

def color_money(amount):
    if amount > 0:
        return f"+${amount:.2f}"
    elif amount < 0:
        return f"-${abs(amount):.2f}"
    return f"${amount:.2f}"

# ─── Betting ──────────────────────────────────────────────────────────────────

def betting_round(balance, pot, stage, min_bet=0):
    print(f"\n  Your balance: ${balance:.2f}  |  Pot: ${pot:.2f}")
    print(f"  Options: [b]et  [c]heck/call  [f]old")
    while True:
        choice = input("  > ").strip().lower()
        if choice == 'f':
            return balance, pot, 'fold'
        elif choice in ('c', 'check', 'call'):
            if min_bet > 0:
                call_amt = min(min_bet, balance)
                print(f"  Calling ${call_amt:.2f}")
                return balance - call_amt, pot + call_amt, 'call'
            print("  Checked.")
            return balance, pot, 'check'
        elif choice == 'b':
            while True:
                try:
                    amt = float(input(f"  Bet amount (max ${balance:.2f}): $"))
                    if amt <= 0:
                        print("  Must be positive.")
                    elif amt > balance:
                        print(f"  You only have ${balance:.2f}.")
                    else:
                        return balance - amt, pot + amt, amt
                except ValueError:
                    print("  Enter a number.")
        else:
            print("  Type b, c, or f.")

# ─── Main Game ────────────────────────────────────────────────────────────────

def play_game():
    print_banner()

    # Starting bankroll
    while True:
        try:
            balance = float(input("\n  Enter your starting bankroll: $"))
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

        # ── Pre-flop ──
        print_table(community, "preflop")
        win_pct, tie_pct = estimate_win_probability(player_hand, community, num_players)
        print_prob_bar(win_pct)
        print(f"  Tie chance: {tie_pct:.1f}%")

        balance, pot, action = betting_round(balance, pot, "preflop", min_bet=big_blind)
        if action == 'fold':
            print(f"\n  You folded. Lost ${big_blind:.2f} (blind).")
            print(f"  Bankroll: ${balance:.2f}")
            continue

        # ── Flop ──
        community += [deck.pop(), deck.pop(), deck.pop()]
        print_table(community, "flop")
        score = evaluate_hand(player_hand + community)
        print(f"  Your best:  {HAND_NAMES[score[0]]}")
        win_pct, tie_pct = estimate_win_probability(player_hand, community, num_players)
        print_prob_bar(win_pct)

        balance, pot, action = betting_round(balance, pot, "flop")
        if action == 'fold':
            print(f"\n  You folded.")
            print(f"  Bankroll: ${balance:.2f}")
            continue

        # ── Turn ──
        community.append(deck.pop())
        print_table(community, "turn")
        score = evaluate_hand(player_hand + community)
        print(f"  Your best:  {HAND_NAMES[score[0]]}")
        win_pct, tie_pct = estimate_win_probability(player_hand, community, num_players)
        print_prob_bar(win_pct)

        balance, pot, action = betting_round(balance, pot, "turn")
        if action == 'fold':
            print(f"\n  You folded.")
            print(f"  Bankroll: ${balance:.2f}")
            continue

        # ── River ──
        community.append(deck.pop())
        print_table(community, "river")
        score = evaluate_hand(player_hand + community)
        print(f"  Your best:  {HAND_NAMES[score[0]]}")
        win_pct, tie_pct = estimate_win_probability(player_hand, community, num_players)
        print_prob_bar(win_pct)

        balance, pot, action = betting_round(balance, pot, "river")
        if action == 'fold':
            print(f"\n  You folded.")
            print(f"  Bankroll: ${balance:.2f}")
            continue

        # ── Showdown ──
        print(f"\n{'─'*55}")
        print("  ♦  SHOWDOWN  ♦")
        print(f"{'─'*55}")
        print(f"  Your hand:   {hand_str(player_hand)}")
        print(f"  Board:       {hand_str(community)}")

        player_score = evaluate_hand(player_hand + community)
        print(f"  Your best:   {HAND_NAMES[player_score[0]]}")

        # Simulate opponents' hands
        opponents = []
        for i in range(num_players - 1):
            opp_hand = [deck.pop(), deck.pop()]
            opp_score = evaluate_hand(opp_hand + community)
            opponents.append((opp_hand, opp_score))
            print(f"\n  Opponent {i+1}: {hand_str(opp_hand)}  →  {HAND_NAMES[opp_score[0]]}")

        # Determine winner
        best_opp_score = max(opponents, key=lambda x: (x[1][0], x[1][1]))[1] if opponents else (0, [])
        p = (player_score[0], player_score[1])
        o = (best_opp_score[0], best_opp_score[1])

        print()
        if p > o:
            print(f"  ★  YOU WIN!  Pot: ${pot:.2f}")
            balance += pot
            print(f"  Net result:  {color_money(pot - big_blind)}")
        elif p == o:
            split = pot / (num_players)
            print(f"  ★  TIE! You split ${pot:.2f} — you get ${split:.2f}")
            balance += split
            print(f"  Net result:  {color_money(split - big_blind)}")
        else:
            print(f"  ✗  You lose. Pot goes to opponent.")
            print(f"  Net result:  {color_money(-big_blind)}")

        print(f"\n  Bankroll: ${balance:.2f}")

        # Play again?
        again = input("\n  Play another hand? [y/n]: ").strip().lower()
        if again != 'y':
            break

    print(f"\n{'='*55}")
    print(f"  Final Bankroll: ${balance:.2f}")
    print(f"  Hands played:   {game_count}")
    print(f"{'='*55}\n")

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    play_game()

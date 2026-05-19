#!/usr/bin/env python3
"""
Texas Hold'em Poker — Full Featured Terminal Game
No external dependencies required.
"""

import random
import json
import os
import sys
import itertools
from collections import Counter

# ─────────────────────────────────────────────
#  ANSI COLOR CODES
# ─────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"

def red(s):        return f"{RED}{s}{RESET}"
def green(s):      return f"{GREEN}{s}{RESET}"
def yellow(s):     return f"{YELLOW}{s}{RESET}"
def blue(s):       return f"{BLUE}{s}{RESET}"
def magenta(s):    return f"{MAGENTA}{s}{RESET}"
def cyan(s):       return f"{CYAN}{s}{RESET}"
def bold(s):       return f"{BOLD}{s}{RESET}"
def dim(s):        return f"{DIM}{s}{RESET}"
def bold_green(s): return f"{BOLD}{GREEN}{s}{RESET}"
def bold_red(s):   return f"{BOLD}{RED}{s}{RESET}"
def white_t(s):    return f"{WHITE}{s}{RESET}"

SAVE_FILE = os.path.expanduser("~/.poker_save.json")

# ─────────────────────────────────────────────
#  CARD / DECK
# ─────────────────────────────────────────────
SUITS  = ["s", "h", "d", "c"]
SUIT_DISPLAY = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
RANKS  = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
RANK_V = {r: i for i, r in enumerate(RANKS, 2)}

def card_str(card, hidden=False):
    if hidden:
        return dim("[??]")
    rank, suit = card
    sym = SUIT_DISPLAY[suit]
    s = f"{rank}{sym}"
    if suit in ("h", "d"):
        return red(s)
    return white_t(s)

def make_deck():
    deck = [(r, s) for s in SUITS for r in RANKS]
    random.shuffle(deck)
    return deck

# ─────────────────────────────────────────────
#  HAND EVALUATOR
# ─────────────────────────────────────────────
HAND_NAMES = [
    "High Card", "One Pair", "Two Pair", "Three of a Kind",
    "Straight", "Flush", "Full House", "Four of a Kind",
    "Straight Flush", "Royal Flush"
]

def hand_rank(cards):
    """Evaluate best 5-card hand from up to 7 cards. Higher is better."""
    best = None
    for combo in itertools.combinations(cards, 5):
        score = eval5(combo)
        if best is None or score > best:
            best = score
    return best

def eval5(cards):
    ranks  = sorted([RANK_V[r] for r, s in cards], reverse=True)
    suits  = [s for _, s in cards]
    flush  = len(set(suits)) == 1

    # Ace-low straight check
    if set(ranks) == {14, 2, 3, 4, 5}:
        straight = True
        ranks = [5, 4, 3, 2, 1]
    else:
        straight = (ranks[0] - ranks[4] == 4 and len(set(ranks)) == 5)

    cnt   = Counter(ranks)
    freqs = sorted(cnt.values(), reverse=True)
    grps  = sorted(cnt.keys(), key=lambda r: (cnt[r], r), reverse=True)

    if flush and straight:
        if ranks[0] == 14:
            return (9, ranks)
        return (8, ranks)
    if freqs[0] == 4:           return (7, grps)
    if freqs[:2] == [3, 2]:     return (6, grps)
    if flush:                   return (5, ranks)
    if straight:                return (4, ranks)
    if freqs[0] == 3:           return (3, grps)
    if freqs[:2] == [2, 2]:     return (2, grps)
    if freqs[0] == 2:           return (1, grps)
    return (0, ranks)

def hand_name(cards):
    r, _ = hand_rank(cards)
    return HAND_NAMES[r]

# ─────────────────────────────────────────────
#  MONTE CARLO WIN PROBABILITY
# ─────────────────────────────────────────────
def win_probability(hole, board, num_opponents, simulations=800):
    wins = ties = 0
    known = set(map(tuple, hole)) | set(map(tuple, board))
    deck = [(r, s) for s in SUITS for r in RANKS if (r, s) not in known]
    needed = 5 - len(board)

    for _ in range(simulations):
        random.shuffle(deck)
        idx = 0
        sim_board = list(board) + deck[idx:idx + needed]
        idx += needed
        my_score = hand_rank(hole + sim_board)
        opp_scores = []
        valid = True
        for _ in range(num_opponents):
            if idx + 2 > len(deck):
                valid = False
                break
            opp_hole = deck[idx:idx + 2]
            idx += 2
            opp_scores.append(hand_rank(opp_hole + sim_board))
        if not valid or not opp_scores:
            wins += 1
            continue
        best_opp = max(opp_scores)
        if my_score > best_opp:
            wins += 1
        elif my_score == best_opp:
            ties += 1

    return wins / simulations, ties / simulations

def win_bar(pct, width=20):
    filled = int(round(pct * width))
    bar = "█" * filled + "░" * (width - filled)
    if pct >= 0.5:
        color = GREEN
    elif pct >= 0.3:
        color = YELLOW
    else:
        color = RED
    return f"{color}[{bar}]{RESET} {pct * 100:.1f}%"

# ─────────────────────────────────────────────
#  PLAYER CLASS
# ─────────────────────────────────────────────
PERSONAS = ["tight", "aggressive", "loose", "maniac"]

class Player:
    def __init__(self, name, stack, human=False, persona=None):
        self.name       = name
        self.stack      = stack
        self.human      = human
        self.persona    = persona or random.choice(PERSONAS)
        self.hand       = []
        self.folded     = False
        self.all_in     = False
        self.invested   = 0   # total chips put in this hand
        self.street_bet = 0   # chips bet on current street

    def reset_for_hand(self):
        self.hand       = []
        self.folded     = False
        self.all_in     = False
        self.invested   = 0
        self.street_bet = 0

    def reset_street(self):
        self.street_bet = 0

    def bet(self, amount):
        """Commit chips to the pot. Returns actual amount committed."""
        amount = min(int(amount), self.stack)
        self.stack      -= amount
        self.invested   += amount
        self.street_bet += amount
        if self.stack == 0:
            self.all_in = True
        return amount

    def label(self):
        if self.human:
            return bold("You")
        return f"{self.name} {dim(f'({self.persona})')}"

    def ai_act(self, to_call, pot, win_pct, current_bet, big_blind):
        """Returns (action, amount). action in: fold, check, call, raise, allin"""
        p  = self.persona
        wp = win_pct
        bluff = random.random() < 0.10

        if to_call >= self.stack:
            # Must go all-in or fold
            if wp > 0.35 or bluff:
                return ("allin", self.stack)
            return ("fold", 0)

        def do_raise():
            raise_size = max(big_blind, int(pot * random.uniform(0.5, 0.8)))
            raise_to   = current_bet + raise_size
            extra      = raise_to - self.street_bet
            if extra >= self.stack:
                return ("allin", self.stack)
            if extra <= 0:
                extra = big_blind
            return ("raise", extra)

        if p == "tight":
            if wp < 0.35 and not bluff:
                return ("fold", 0) if to_call > 0 else ("check", 0)
            if to_call == 0:
                return do_raise() if wp > 0.55 else ("check", 0)
            if wp > 0.55 or bluff:
                return do_raise()
            return ("call", to_call)

        elif p == "aggressive":
            if wp < 0.22 and not bluff:
                return ("fold", 0) if to_call > 0 else ("check", 0)
            if to_call == 0:
                return do_raise() if (wp > 0.35 or bluff) else ("check", 0)
            if wp < 0.30 and not bluff:
                return ("call", to_call)
            return do_raise()

        elif p == "loose":
            if wp < 0.18 and not bluff:
                return ("fold", 0) if to_call > 0 else ("check", 0)
            if random.random() < 0.25:
                return ("call", to_call) if to_call > 0 else ("check", 0)
            if to_call == 0:
                return do_raise() if wp > 0.45 else ("check", 0)
            return do_raise() if wp > 0.50 else ("call", to_call)

        elif p == "maniac":
            if wp < 0.10 and not bluff and random.random() < 0.25:
                return ("fold", 0) if to_call > 0 else ("check", 0)
            if random.random() < 0.65:
                return do_raise()
            return ("call", to_call) if to_call > 0 else ("check", 0)

        # Fallback
        return ("call", to_call) if to_call > 0 else ("check", 0)

# ─────────────────────────────────────────────
#  SIDE POT CALCULATOR
# ─────────────────────────────────────────────
def compute_side_pots(all_players):
    """
    Returns list of (pot_amount, eligible_players) from lowest to highest.
    eligible = players who contributed at that level and have not folded.
    """
    invested = [(p, p.invested) for p in all_players if p.invested > 0]
    if not invested:
        return []
    levels = sorted(set(v for _, v in invested))
    pots   = []
    prev   = 0
    for lvl in levels:
        at       = [p for p, v in invested if v >= lvl]
        amt      = (lvl - prev) * len(at)
        eligible = [p for p in at if not p.folded]
        if amt > 0 and eligible:
            pots.append((amt, eligible))
        prev = lvl
    return pots

# ─────────────────────────────────────────────
#  DISPLAY HELPERS
# ─────────────────────────────────────────────
DIV = "  " + "─" * 52

def print_div():
    print(DIV)

def print_street_header(street, board):
    print()
    print_div()
    print(f"  {bold(street)}")
    cards_str = "  ".join(card_str(c) for c in board)
    print(f"  Board: {cards_str}")
    print_div()

def print_players(players, practice=False):
    for p in players:
        label_str = p.label()
        stack_str = f"${p.stack:>8.2f}"
        line = f"  {label_str:<35} {stack_str}"
        if p.folded:
            line += dim("  [FOLDED]")
        elif p.all_in:
            line += yellow("  [ALL-IN]")
        print(line)
        # In practice mode, show opponent hands
        if practice and not p.human and p.hand and not p.folded:
            hcards = "  ".join(card_str(c) for c in p.hand)
            print(f"    {dim('Cards:')} {hcards}")

def print_hand_info(player, board, num_opponents, pot, to_call):
    if not player.hand:
        return
    cards = "  ".join(card_str(c) for c in player.hand)
    all_cards = player.hand + board
    hname = hand_name(all_cards) if board else ""
    hand_display = f"  Your hand:  {cards}"
    if hname:
        hand_display += f"  {cyan(f'({hname})')}"
    print(hand_display)

    if board and num_opponents > 0:
        wp, tp = win_probability(player.hand, board, num_opponents)
        bar = win_bar(wp)
        tie_str = f"  Tie: {tp * 100:.1f}%" if tp > 0.005 else ""
        print(f"  Win:  {bar}{tie_str}")

        if to_call > 0:
            pot_odds_pct = to_call / (pot + to_call) if (pot + to_call) > 0 else 0
            ev = wp * pot - (1 - wp) * to_call
            odds_color = green if (wp >= pot_odds_pct) else red
            print(f"  Pot odds: {odds_color(f'{pot_odds_pct * 100:.1f}%')} "
                  f"(need >{pot_odds_pct * 100:.1f}% win chance to call profitably)")
            ev_str = f"+${ev:.2f}" if ev >= 0 else f"-${abs(ev):.2f}"
            ev_color = green if ev >= 0 else red
            print(f"  EV of call: {ev_color(ev_str)}")

# ─────────────────────────────────────────────
#  PREFLOP STRENGTH ESTIMATE
# ─────────────────────────────────────────────
def preflop_strength(hand):
    ranks  = sorted([RANK_V[r] for r, _ in hand], reverse=True)
    suited = hand[0][1] == hand[1][1]
    r1, r2 = ranks
    if r1 == r2:
        return min(0.45 + r1 * 0.025, 0.90)
    base = (r1 + r2) / 28.0 * 0.65
    if suited:
        base += 0.05
    return min(base, 0.85)

# ─────────────────────────────────────────────
#  AI ANNOUNCEMENT
# ─────────────────────────────────────────────
def ai_announce(player, action, amount, to_call):
    label = player.label()
    if action == "fold":
        print(f"  {dim(label + ' folds')}")
    elif action == "check":
        print(f"  {dim(label + ' checks')}")
    elif action == "call":
        print(f"  {label} calls ${to_call:.2f}")
    elif action == "raise":
        print(f"  {bold(label + f' raises, adding ${amount:.2f}')}")
    elif action == "allin":
        print(f"  {yellow(bold(label + ' goes ALL-IN!'))}")

# ─────────────────────────────────────────────
#  HUMAN INPUT
# ─────────────────────────────────────────────
def get_human_action(player, to_call, pot, current_bet, big_blind):
    while True:
        try:
            raw = input(f"  {bold('>')} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        if raw in ("f", "fold"):
            return ("fold", 0)

        elif raw in ("c", "call", "check", ""):
            if to_call == 0:
                return ("check", 0)
            return ("call", to_call)

        elif raw in ("a", "allin", "all-in", "all in"):
            return ("allin", player.stack)

        elif raw.startswith("r"):
            parts = raw.split()
            min_extra = max(big_blind, (current_bet - player.street_bet) + big_blind)
            if len(parts) >= 2:
                try:
                    total_raise_to = float(parts[1])
                    extra = total_raise_to - player.street_bet
                    if extra < min_extra:
                        print(f"  {red(f'Min raise: total ${player.street_bet + min_extra:.2f} (add ${min_extra:.2f})')}")
                        continue
                    if extra >= player.stack:
                        return ("allin", player.stack)
                    return ("raise", extra)
                except ValueError:
                    pass

            min_total = player.street_bet + min_extra
            print(f"  Raise to total (min ${min_total:.2f}, stack ${player.stack + player.street_bet:.2f}):")
            try:
                raw2 = input(f"  {bold('>')} ").strip()
                total_raise_to = float(raw2)
                extra = total_raise_to - player.street_bet
                if extra < min_extra:
                    print(f"  {red(f'Min raise to ${min_total:.2f}')}")
                    continue
                if extra >= player.stack:
                    return ("allin", player.stack)
                return ("raise", extra)
            except (ValueError, EOFError):
                print(f"  {red('Invalid amount')}")
                continue
        else:
            if to_call == 0:
                print(f"  {red('Options: [c]heck  [r]aise  [f]old  [a]ll-in')}")
            else:
                print(f"  {red('Options: [c]all  [r]aise  [f]old  [a]ll-in')}")

# ─────────────────────────────────────────────
#  BETTING ROUND (queue-based)
# ─────────────────────────────────────────────
def betting_round(players, pot, current_bet, big_blind, board, practice=False):
    """
    Queue-based betting round.
    current_bet: current total street bet that must be matched.
    Returns updated pot.
    """
    # Players eligible to act
    queue = [p for p in players if not p.folded and not p.all_in]
    if len(queue) <= 1:
        return pot

    while queue:
        p = queue.pop(0)
        if p.folded or p.all_in:
            continue

        # Check if only one non-folded player remains
        active_now = [x for x in players if not x.folded]
        if len(active_now) <= 1:
            break

        to_call   = max(0, current_bet - p.street_bet)
        num_opp   = len([x for x in players if not x.folded and x is not p])

        # Print current state
        print()
        if board:
            cards_str = "  ".join(card_str(c) for c in board)
            print(f"  Board: {cards_str}")
        print_players(players, practice=practice)
        print()

        if p.human:
            print_hand_info(p, board, num_opp, pot, to_call)
            print()
            print(f"  {dim('Pot:')} {bold(f'${pot:.2f}')}   "
                  f"{dim('To call:')} {bold(f'${to_call:.2f}')}   "
                  f"{dim('Stack:')} {bold(f'${p.stack:.2f}')}")

            if to_call == 0:
                opts = [dim("[c]") + "heck", dim("[r]") + "aise",
                        dim("[f]") + "old", dim("[a]") + "ll-in"]
            else:
                opts = [dim("[c]") + f"all ${to_call:.2f}", dim("[r]") + "aise",
                        dim("[f]") + "old", dim("[a]") + "ll-in"]
            print(f"  Actions: {'  '.join(opts)}")
            action, amount = get_human_action(p, to_call, pot, current_bet, big_blind)

        else:
            # AI decision
            wp = preflop_strength(p.hand) if not board else win_probability(p.hand, board, num_opp)[0]
            action, amount = p.ai_act(to_call, pot, wp, current_bet, big_blind)
            ai_announce(p, action, amount, to_call)

        # Execute action
        if action == "fold":
            p.folded = True

        elif action == "check":
            pass

        elif action == "call":
            actual = p.bet(to_call)
            pot   += actual

        elif action == "raise":
            actual = p.bet(amount)
            pot   += actual
            new_total = p.street_bet  # what they've committed this street total
            if new_total > current_bet:
                current_bet = new_total
                # Re-add all other active (non-folded, non-all-in) players
                for other in players:
                    if other is p or other.folded or other.all_in:
                        continue
                    if other not in queue:
                        queue.append(other)

        elif action == "allin":
            actual = p.bet(p.stack)
            pot   += actual
            p.all_in = True
            if p.street_bet > current_bet:
                current_bet = p.street_bet
                for other in players:
                    if other is p or other.folded or other.all_in:
                        continue
                    if other not in queue:
                        queue.append(other)

        # Re-check if only one player remains
        active_left = [x for x in players if not x.folded]
        if len(active_left) <= 1:
            break

    return pot

# ─────────────────────────────────────────────
#  SHOWDOWN
# ─────────────────────────────────────────────
def showdown(players, board, pot, stats):
    print()
    print_div()
    print(f"  {bold(cyan('SHOWDOWN'))}")
    print_div()
    cards_str = "  ".join(card_str(c) for c in board)
    print(f"  Board: {cards_str}")
    print()

    active = [p for p in players if not p.folded]

    # Single player remaining (everyone else folded)
    if len(active) == 1:
        winner = active[0]
        print(f"  {bold_green(winner.label() + f' wins ${pot:.2f} — everyone else folded!')}")
        winner.stack += pot
        _update_stats(stats, winner, pot)
        return

    # Show all hands
    for p in active:
        cards = "  ".join(card_str(c) for c in p.hand)
        full  = p.hand + board
        hname = hand_name(full)
        print(f"  {p.label()}: {cards}  →  {cyan(hname)}")
    print()

    # Distribute via side pots
    pots = compute_side_pots(players)
    if not pots:
        pots = [(pot, active)]

    total_awarded = 0
    for i, (pot_amt, eligible) in enumerate(pots):
        pot_label = "Main pot" if i == 0 else f"Side pot {i}"
        if len(eligible) == 1:
            w = eligible[0]
            print(f"  {bold_green(w.label() + f' wins {pot_label} ${pot_amt:.2f}')}")
            w.stack += pot_amt
            _update_stats(stats, w, pot_amt)
            total_awarded += pot_amt
        else:
            scores  = [(p, hand_rank(p.hand + board)) for p in eligible]
            best    = max(s for _, s in scores)
            winners = [p for p, s in scores if s == best]
            share   = pot_amt / len(winners)
            for w in winners:
                if len(winners) > 1:
                    print(f"  {bold_green(w.label() + f' splits {pot_label} — ${share:.2f}')}")
                else:
                    hname = hand_name(w.hand + board)
                    print(f"  {bold_green(w.label() + f' wins {pot_label} ${pot_amt:.2f}  ({hname})')}")
                w.stack += share
                _update_stats(stats, w, share)
            total_awarded += pot_amt

    # Rounding remainder to first active player
    remainder = pot - total_awarded
    if abs(remainder) > 0.005 and active:
        active[0].stack += remainder

def _update_stats(stats, winner, amount):
    if winner.human:
        stats["hands_won"]   += 1
        stats["biggest_pot"]  = max(stats["biggest_pot"], amount)

# ─────────────────────────────────────────────
#  SAVE / LOAD BANKROLL
# ─────────────────────────────────────────────
def save_bankroll(stack):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump({"stack": round(stack, 2)}, f)
    except Exception:
        pass

def load_bankroll(default=1000):
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE) as f:
                data = json.load(f)
                return float(data.get("stack", default))
    except Exception:
        pass
    return default

# ─────────────────────────────────────────────
#  PLAY A SINGLE HAND
# ─────────────────────────────────────────────
def play_hand(players, small_blind, big_blind, stats, practice=False):
    """Play one hand. Returns pot size."""
    for p in players:
        p.reset_for_hand()

    deck = make_deck()
    pot  = 0

    # players[0] = SB, players[1] = BB
    sb = players[0]
    bb = players[1]

    sb_amt = sb.bet(small_blind)
    pot += sb_amt
    print(f"  {sb.label()} posts small blind ${sb_amt:.2f}")

    bb_amt = bb.bet(big_blind)
    pot += bb_amt
    print(f"  {bb.label()} posts big blind ${bb_amt:.2f}")

    # Deal hole cards
    for p in players:
        p.hand = [deck.pop(), deck.pop()]

    human = next((p for p in players if p.human), None)
    if human:
        hcards = "  ".join(card_str(c) for c in human.hand)
        print(f"\n  Your hole cards: {hcards}\n")

    stats["hands_played"] += 1

    # ── PREFLOP ──────────────────────────────
    print_div()
    print(f"  {bold('PREFLOP')}")
    print_div()
    pot = betting_round(players, pot, big_blind, big_blind, [], practice=practice)

    active = [p for p in players if not p.folded]
    if len(active) == 1:
        w = active[0]
        print(f"\n  {bold_green(w.label() + f' wins ${pot:.2f}!')}")
        w.stack += pot
        _update_stats(stats, w, pot)
        return pot

    # ── FLOP ─────────────────────────────────
    board = [deck.pop(), deck.pop(), deck.pop()]
    for p in players:
        p.reset_street()
    print_street_header("FLOP", board)
    pot = betting_round(players, pot, 0, big_blind, board, practice=practice)

    active = [p for p in players if not p.folded]
    if len(active) == 1:
        w = active[0]
        print(f"\n  {bold_green(w.label() + f' wins ${pot:.2f}!')}")
        w.stack += pot
        _update_stats(stats, w, pot)
        return pot

    # ── TURN ─────────────────────────────────
    board.append(deck.pop())
    for p in players:
        p.reset_street()
    print_street_header("TURN", board)
    pot = betting_round(players, pot, 0, big_blind, board, practice=practice)

    active = [p for p in players if not p.folded]
    if len(active) == 1:
        w = active[0]
        print(f"\n  {bold_green(w.label() + f' wins ${pot:.2f}!')}")
        w.stack += pot
        _update_stats(stats, w, pot)
        return pot

    # ── RIVER ────────────────────────────────
    board.append(deck.pop())
    for p in players:
        p.reset_street()
    print_street_header("RIVER", board)
    pot = betting_round(players, pot, 0, big_blind, board, practice=practice)

    # ── SHOWDOWN ─────────────────────────────
    showdown(players, board, pot, stats)
    return pot

# ─────────────────────────────────────────────
#  SESSION STATS
# ─────────────────────────────────────────────
def print_stats(stats, starting_stack, ending_stack):
    print()
    print_div()
    print(f"  {bold(cyan('SESSION STATS'))}")
    print_div()
    hands = stats["hands_played"]
    won   = stats["hands_won"]
    rate  = (won / hands * 100) if hands > 0 else 0.0
    net   = ending_stack - starting_stack
    print(f"  Hands played:   {hands}")
    print(f"  Hands won:      {won}  ({rate:.1f}% win rate)")
    print(f"  Biggest pot:    ${stats['biggest_pot']:.2f}")
    print(f"  Starting stack: ${starting_stack:.2f}")
    print(f"  Ending stack:   ${ending_stack:.2f}")
    net_str   = f"+${net:.2f}" if net >= 0 else f"-${abs(net):.2f}"
    net_color = bold_green if net >= 0 else bold_red
    print(f"  Net profit:     {net_color(net_str)}")
    print_div()

# ─────────────────────────────────────────────
#  PLAYER FACTORY
# ─────────────────────────────────────────────
AI_NAMES = ["Alex", "Blake", "Casey", "Dana", "Ellis", "Finn", "Gray", "Harper"]

def make_players(human_stack, num_ai=3):
    names   = random.sample(AI_NAMES, min(num_ai, len(AI_NAMES)))
    players = [Player("You", human_stack, human=True)]
    for i, name in enumerate(names):
        persona = PERSONAS[i % len(PERSONAS)]
        players.append(Player(name, human_stack, persona=persona))
    return players

# ─────────────────────────────────────────────
#  CASH GAME / PRACTICE MODE
# ─────────────────────────────────────────────
def cash_game(practice=False):
    os.system("clear")
    mode_label = "PRACTICE MODE" if practice else "CASH GAME"
    print(f"\n  {bold(cyan(mode_label))}")

    saved = load_bankroll()
    print(f"  Saved bankroll: ${saved:.2f}")
    try:
        raw    = input(f"  Buy-in amount [{saved:.0f}]: ").strip()
        buy_in = float(raw) if raw else saved
    except (ValueError, EOFError):
        buy_in = saved

    try:
        raw    = input("  Number of AI opponents [3]: ").strip()
        num_ai = int(raw) if raw else 3
        num_ai = max(1, min(7, num_ai))
    except (ValueError, EOFError):
        num_ai = 3

    small_blind    = 5
    big_blind      = 10
    players        = make_players(buy_in, num_ai)
    stats          = {"hands_played": 0, "hands_won": 0, "biggest_pot": 0}
    starting_stack = buy_in
    hand_num       = 0

    while True:
        # Remove busted AIs (keep human even if broke)
        players = [p for p in players if p.stack > 0 or p.human]
        human   = next((p for p in players if p.human), None)

        if not human or human.stack <= 0:
            print(bold_red("\n  You're out of chips! Game over."))
            break
        if len(players) < 2:
            print(bold_green("\n  All opponents eliminated — you win!"))
            break

        # Rotate blinds
        players  = players[1:] + [players[0]]
        hand_num += 1

        print()
        print_div()
        print(f"  {bold(f'Hand #{hand_num} — {mode_label}')}   "
              f"Blinds: {small_blind}/{big_blind}   "
              f"Stack: {bold(f'${human.stack:.2f}')}")
        print_div()

        play_hand(players, small_blind, big_blind, stats, practice=practice)
        save_bankroll(human.stack)

        print()
        try:
            again = input(f"  {dim('Next hand?')} [Y/n]: ").strip().lower()
            if again in ("n", "no", "q", "quit"):
                break
        except (EOFError, KeyboardInterrupt):
            break

    human      = next((p for p in players if p.human), None)
    end_stack  = human.stack if human else 0
    save_bankroll(end_stack)
    print_stats(stats, starting_stack, end_stack)

# ─────────────────────────────────────────────
#  TOURNAMENT MODE
# ─────────────────────────────────────────────
def tournament_mode():
    os.system("clear")
    print(f"\n  {bold(cyan('TOURNAMENT MODE'))}\n")

    try:
        raw    = input("  Buy-in per player [$500]: ").strip()
        buy_in = float(raw) if raw else 500.0
    except (ValueError, EOFError):
        buy_in = 500.0

    try:
        raw    = input("  Number of AI opponents [4]: ").strip()
        num_ai = int(raw) if raw else 4
        num_ai = max(1, min(7, num_ai))
    except (ValueError, EOFError):
        num_ai = 4

    small_blind    = 10
    big_blind      = 20
    players        = make_players(buy_in, num_ai)
    stats          = {"hands_played": 0, "hands_won": 0, "biggest_pot": 0}
    starting_stack = buy_in
    hand_num       = 0
    blind_level    = 0

    total = len(players)
    print(f"\n  Tournament: {total} players, buy-in ${buy_in:.0f}")
    print(f"  Blinds increase every 5 hands (×1.5)\n")

    while True:
        # Eliminate broke players
        players = [p for p in players if p.stack > 0]
        if not players:
            break

        human_alive = any(p.human for p in players)

        if len(players) == 1:
            winner = players[0]
            print()
            print_div()
            if winner.human:
                print(bold_green(f"  *** YOU WIN THE TOURNAMENT! Stack: ${winner.stack:.2f} ***"))
            else:
                print(bold_red(f"  Tournament over. {winner.label()} wins with ${winner.stack:.2f}"))
            print_div()
            break

        if not human_alive:
            print(bold_red("\n  You have been eliminated from the tournament."))
            break

        # Increase blinds every 5 hands
        new_level = hand_num // 5
        if new_level > blind_level:
            blind_level = new_level
            small_blind = int(small_blind * 1.5)
            big_blind   = int(big_blind   * 1.5)
            print(yellow(f"\n  *** BLIND INCREASE — Now: {small_blind}/{big_blind} ***\n"))

        # Rotate and play
        players  = players[1:] + [players[0]]
        hand_num += 1

        human = next((p for p in players if p.human), None)
        remaining = len(players)
        print()
        print_div()
        print(f"  {bold(f'Tournament Hand #{hand_num}')}   "
              f"Blinds: {small_blind}/{big_blind}   "
              f"Players remaining: {remaining}")
        if human:
            print(f"  Your stack: {bold(f'${human.stack:.2f}')}")
        print_div()

        play_hand(players, small_blind, big_blind, stats)

        print()
        try:
            input(f"  {dim('Press Enter for next hand...')} ")
        except (EOFError, KeyboardInterrupt):
            break

    human     = next((p for p in players if p.human), None)
    end_stack = human.stack if human else 0
    print_stats(stats, starting_stack, end_stack)

# ─────────────────────────────────────────────
#  MAIN MENU
# ─────────────────────────────────────────────
def print_menu():
    print()
    sep = cyan("═" * 43)
    print(f"  {sep}")
    title = "       ♠ ♥  TEXAS HOLD'EM POKER  ♦ ♣"
    print(f"  {bold(cyan(title))}")
    print(f"  {sep}")
    saved = load_bankroll(default=None)
    if saved is not None:
        print(f"  Saved bankroll: {green(f'${saved:.2f}')}")
    print(f"  {dim('[1]')} Cash Game")
    print(f"  {dim('[2]')} Practice Mode  {dim('(see opponent cards)')}")
    print(f"  {dim('[3]')} Tournament")
    print(f"  {dim('[4]')} Quit")
    print(f"  {sep}")

def main():
    while True:
        print_menu()
        try:
            choice = input(f"  {bold('Select [1-4]:')} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "1":
            cash_game(practice=False)
        elif choice == "2":
            cash_game(practice=True)
        elif choice == "3":
            tournament_mode()
        elif choice in ("4", "q", "quit", "exit"):
            print(f"\n  {dim('Thanks for playing. Good luck!')}\n")
            break
        else:
            print(f"  {red('Please enter 1, 2, 3, or 4.')}")

if __name__ == "__main__":
    main()

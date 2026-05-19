# ♠ Texas Hold'em Poker — Terminal Game

A fully playable Texas Hold'em poker game in the terminal, built with Python. No dependencies needed — just Python 3.

## Features

- **Full betting system** — bet, check/call, or fold at every street
- **Real-time win probability** — Monte Carlo simulation runs after each street to show your odds
- **Complete hand evaluation** — High Card all the way to Straight Flush
- **Multi-player support** — play against 1 to 8 opponents
- **Bankroll tracking** — tracks your money across hands, auto-scales blinds
- **Showdown** — see opponents' cards and who wins at the end

## How to Run

```bash
python3 poker.py
```

No installs required. Python 3 only.

## How to Play

1. Enter your starting bankroll and number of players
2. You're automatically posted the big blind each hand
3. At each stage (Pre-flop, Flop, Turn, River) you'll see:
   - Your current hand
   - The community cards
   - Your win probability bar
   - Betting options: `b` = bet, `c` = check/call, `f` = fold
4. At showdown, all hands are revealed and the pot is awarded

## Betting Options

| Key | Action |
|-----|--------|
| `b` | Bet — enter a custom amount |
| `c` | Check (free) or Call (match the bet) |
| `f` | Fold — give up your hand |

## Hand Rankings (Best to Worst)

| Rank | Hand |
|------|------|
| 8 | Straight Flush |
| 7 | Four of a Kind |
| 6 | Full House |
| 5 | Flush |
| 4 | Straight |
| 3 | Three of a Kind |
| 2 | Two Pair |
| 1 | One Pair |
| 0 | High Card |

## Example Output

```
=======================================================
          ♠ ♥  TEXAS HOLD'EM POKER  ♦ ♣
=======================================================

  Your hand:  A♠  K♥
  Hand rank:  High Card

  [ FLOP ]  Board: A♦  K♣  7♠
  Your best:  Two Pair
  Win chance:  [████████████████░░░░] 82.4%
  Tie chance: 0.5%
```

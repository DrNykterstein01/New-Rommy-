# Rummy500 AI Bot Integration Guide

## Overview

Your Rummy500 game now includes a sophisticated AI Bot system that can learn and improve progressively. The AI Bot inherits all attributes and methods from the `Player` class, making it a native player in your game.

## Files Added

1. **AIBot.py** - Main AI Bot class with decision-making algorithms
2. **AITrainer.py** - Training system for teaching the bot through simulated games
3. **train_bot.py** - Command-line tool for training the bot
4. **aibot_model.json** - Trained model file (generated after training)
5. **aibot_model_summary.json** - Training statistics summary

## Quick Start

### Step 1: Train the Bot

Open a terminal in your project directory and run:

```bash
python train_bot.py --games 500
```

This will:
- Train the AI bot through 500 simulated games
- Save the trained model to `aibot_model.json`
- Display training progress and final statistics

Optional parameters:
- `--games N` : Number of training games (default: 100)
- `--output filename` : Output model file (default: aibot_model.json)
- `--load filename` : Continue training from existing model
- `--bots N` : Number of bots to train (default: 1)

Example with all parameters:
```bash
python train_bot.py --games 1000 --output my_ai_bot.json --bots 1
```

### Step 2: Integrate into ui2.py

Modify your `ui2.py` to support AI players. Add this import at the top:

```python
from AIBot import AIBot
```

In your player initialization section (where you create players), add code like this:

```python
# Example: Creating a mix of human and AI players
players = []

# Human player
from Player import Player
player1 = Player(0, "You")
players.append(player1)

# AI players
bot1 = AIBot(1, "AI Opponent")
bot1.load_model('aibot_model.json')  # Load trained model
players.append(bot1)

bot2 = AIBot(2, "AI Rival")
bot2.load_model('aibot_model.json')
players.append(bot2)
```

### Step 3: Handle AI Decisions During Game

When it's the AI's turn, call its decision methods instead of waiting for user input:

```python
# Check if current player is AI
if hasattr(current_player, 'is_ai') and current_player.is_ai:
    # Drawing phase
    should_draw_discard = current_player.decide_draw_source(
        discard_top_card,
        len(deck),
        get_players_info(players)
    )

    if should_draw_discard and discard_pile:
        # Draw from discard
        drawCard(current_player, round_obj, fromDiscards=True, ...)
    else:
        # Draw from deck
        drawCard(current_player, round_obj)

    # Playing phase
    play = current_player.decide_play_cards(current_round_number)
    if play:
        # Execute the play on the board
        apply_play(current_player, play, board_state)

    # Discard phase
    card_to_discard = current_player.decide_discard()
    if card_to_discard:
        discard_pile.append(card_to_discard)
        current_player.playerHand.remove(card_to_discard)

else:
    # Human player turn - wait for UI input as normal
    # Your existing code here
```

### Step 4: Record Game Results (Optional)

After each round or game, update the AI's learning:

```python
if hasattr(winner, 'is_ai') and winner.is_ai:
    winner.learn_from_game({
        'win': True,
        'points_gained': 0,
        'plays_made': len(winner.playMade)
    })

for loser in other_players:
    if hasattr(loser, 'is_ai') and loser.is_ai:
        loser.learn_from_game({
            'win': False,
            'points_gained': loser.playerPoints,
            'plays_made': len(loser.playMade)
        })
        loser.save_model('aibot_model.json')
```

## AI Bot Methods Reference

### Decision Methods (Called during gameplay)

#### `decide_draw_source(discard_top_card, deck_size, players_info)`
Decides whether to draw from discard pile or deck.
- **Returns:** `True` (discard) or `False` (deck)
- **Parameters:**
  - `discard_top_card`: Card object at top of discard pile
  - `deck_size`: Number of cards remaining in deck
  - `players_info`: List of dicts with player hand sizes

#### `decide_play_cards(round_number)`
Decides which cards to play based on round rules.
- **Returns:** Tuple of (trios, sequences) or None
- **Parameters:**
  - `round_number`: Current round (1-4)

#### `decide_discard(must_burn_joker=False)`
Chooses which card to discard.
- **Returns:** Card object to discard
- **Parameters:**
  - `must_burn_joker`: Boolean if joker must be burned with another card

#### `decide_buy_card(discard_card, hand_value, players_info)`
Decides whether to buy a discarded card from another player.
- **Returns:** `True` (buy) or `False` (don't buy)
- **Parameters:**
  - `discard_card`: Card being offered
  - `hand_value`: Total point value of current hand
  - `players_info`: Information about other players

#### `decide_move_joker(plays_in_table)`
Decides if joker should be moved in a sequence.
- **Returns:** `(play_index, new_position)` tuple or `None`

#### `decide_substitute_joker(plays_in_table)`
Decides if a joker should be substituted for a regular card.
- **Returns:** `(play_index, card_to_use)` tuple or `None`

### Learning Methods

#### `learn_from_game(game_result)`
Updates bot's strategy based on game outcome.
- **Parameters:**
  ```python
  game_result = {
      'win': bool,           # Did the bot win?
      'points_gained': int,  # Points received
      'plays_made': int      # Number of plays made
  }
  ```

#### `save_model(filename='aibot_model.json')`
Saves trained bot state to file.

#### `load_model(filename='aibot_model.json')`
Loads previously trained bot state from file.

## AI Bot Attributes

- `is_ai` - Boolean flag identifying this as an AI player
- `strategy_weights` - Dictionary with strategy distribution (aggressive, conservative, balanced)
- `win_rate` - Bot's win percentage (0.0 to 1.0)
- `games_played` - Total number of games played
- `games_won` - Total number of games won
- `learned_patterns` - Dictionary storing learned game patterns
- `game_history` - List of recent games and results

All other attributes are inherited from `Player` class:
- `playerHand` - List of Card objects in hand
- `playerPoints` - Total points accumulated
- `downHand` - Boolean if bot has made initial play
- `playMade` - List of plays made in current round
- `playerName` - Bot's display name
- `playerId` - Unique identifier

## Example Integration in ui2.py

Here's a minimal example of how to integrate AI into your game loop:

```python
from AIBot import AIBot
from Player import Player

def initialize_game(player_count, ai_count=1):
    """Initialize game with human and AI players"""
    players = []

    # Add human player
    human = Player(0, "Player")
    players.append(human)

    # Add AI players
    for i in range(ai_count):
        bot = AIBot(i + 1, f"AI Bot {i + 1}")
        bot.load_model('aibot_model.json')
        players.append(bot)

    return players

def play_turn(current_player, game_state):
    """Execute a player's turn"""

    # Check if AI player
    if hasattr(current_player, 'is_ai') and current_player.is_ai:
        # Let AI make decisions
        draw_source = current_player.decide_draw_source(
            game_state['discard_top'],
            game_state['deck_size'],
            game_state['players_info']
        )

        # Execute draw based on decision
        if draw_source:
            take_discard_card(current_player, game_state)
        else:
            draw_from_deck(current_player, game_state)

        # Try to play cards
        play = current_player.decide_play_cards(game_state['round_number'])
        if play:
            execute_play(current_player, play, game_state)

        # Discard a card
        card = current_player.decide_discard()
        execute_discard(current_player, card, game_state)
    else:
        # Human player - show UI and wait for input
        wait_for_human_input(current_player, game_state)

def end_game(winner, players):
    """Record game results and update AI learning"""
    for player in players:
        if hasattr(player, 'is_ai') and player.is_ai:
            result = {
                'win': player == winner,
                'points_gained': player.playerPoints,
                'plays_made': len(player.playMade)
            }
            player.learn_from_game(result)
            player.save_model('aibot_model.json')
```

## Training Tips

1. **Start Training:** Train with at least 100 games to build initial patterns
2. **Continuous Learning:** Periodically train with more games to improve
3. **Multiple Bots:** Training 3-4 bots together improves their play against each other
4. **Load and Continue:** Use `--load` parameter to continue training from previous state

## Troubleshooting

### Bot makes invalid plays
- Ensure round rules are correctly passed to `decide_play_cards()`
- Check that Card class properties (value, suit, joker) are properly set

### Bot keeps losing
- Train with more games (500-1000)
- Increase strategy diversity by training multiple bots together

### Game crashes when bot plays
- Verify all decision methods return expected types
- Check that discarded cards are removed from `playerHand`
- Ensure `playerCardsPos` dictionary is updated for UI rendering

### Model file not found
- Run training script first: `python train_bot.py`
- Check filename matches exactly in `load_model()` call

## Advanced Usage

### Custom Strategy Weighting

```python
bot = AIBot(1, "Custom Bot")

# Adjust strategy preferences
bot.strategy_weights = {
    'aggressive': 0.6,   # More aggressive plays
    'conservative': 0.2,
    'balanced': 0.2
}

bot.learn_from_game({'win': True, 'points_gained': 0, 'plays_made': 5})
```

### Analyzing Bot Performance

```python
bot = AIBot(1, "Test Bot")
bot.load_model('aibot_model.json')

print(f"Win Rate: {bot.win_rate:.2%}")
print(f"Games Played: {bot.games_played}")
print(f"Current Strategy: {bot.strategy_weights}")
print(f"Recent History: {bot.game_history[-5:]}")
```

## Notes

- AI Bot inherits all Player functionality including drawing, playing, and discarding cards
- The learning system is statistical - bot improves through pattern recognition
- Each bot saves independently, so you can have multiple trained bots with different skill levels
- Training is CPU-intensive but runs offline, not affecting gameplay

Good luck with your AI-powered Rummy500 game!

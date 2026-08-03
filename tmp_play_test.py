from AIBot import AIBot
from Card import Card

bot = AIBot(0, 'TestBot')

# Example hand that should allow round 1: one trio and one sequence.
bot.playerHand = [
    Card('5', '♠'), Card('5', '♥'), Card('5', '♦'),
    Card('7', '♣'), Card('8', '♣'), Card('9', '♣'), Card('10', '♣')
]

bot.current_round = 1
plays = bot._find_valid_plays(1)
print('Found plays:', len(plays))
for p in plays:
    print([[str(c) for c in play] for play in p])

# Example hand for round 2: two sequences
bot.playerHand = [
    Card('4', '♠'), Card('5', '♠'), Card('6', '♠'), Card('7', '♠'),
    Card('8', '♥'), Card('9', '♥'), Card('10', '♥'), Card('J', '♥')
]
bot.current_round = 2
plays = bot._find_valid_plays(2)
print('\nRound 2 plays:', len(plays))
for p in plays:
    print([[str(c) for c in play] for play in p])

# Example hand with joker for round 1
bot.playerHand = [
    Card('5', '♠'), Card('5', '♥'), Card('Joker', '♠', joker=True),
    Card('7', '♣'), Card('8', '♣'), Card('9', '♣'), Card('10', '♣')
]
bot.current_round = 1
plays = bot._find_valid_plays(1)
print('\nRound 1 with joker plays:', len(plays))
for p in plays:
    print([[str(c) for c in play] for play in p])

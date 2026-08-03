from AIBot import AIBot
from Card import Card
from rummy_env import RummyEnv

# Create 3 bots; only first will attempt to bajar.
bots = [AIBot(i, f'TestBot_{i}') for i in range(3)]
env = RummyEnv(bots)
# Minimal enough to avoid missing attributes
for bot in bots:
    bot.playerPoints = 0
    bot.playerHand = []
    bot.downHand = False
    bot.isHand = False
    bot.winner = False
    bot.isSpectator = False
    bot.cardDrawn = False
    bot.canDiscard = True
    bot.playerBuy = False
    bot.playerPass = False
    bot.playMade = []
    bot.jugadas_bajadas = []

# Set just the first player's hand to a valid round-1 bajada
bots[0].playerHand = [
    Card('5', '♠'), Card('5', '♥'), Card('5', '♦'),
    Card('7', '♣'), Card('8', '♣'), Card('9', '♣'), Card('10', '♣')
]
# Provide a discard pile and deck for draw logic if needed
env.round = type('R', (), {'discards': [Card('3','♠')], 'pile':[Card('2','♠')], 'hands': {0:bots[0].playerHand}})()
print('Before down:', bots[0].playerHand)
# Simulate draw phase completed
bots[0].cardDrawn = True
res = env._apply_play(bots[0], 0)
print('apply_play result:', res)
print('Player down:', bots[0].downHand)
print('playMade:', [[str(c) for c in play] for play in bots[0].playMade])
print('Remaining hand:', [str(c) for c in bots[0].playerHand])

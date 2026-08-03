from AIBot import AIBot
from rummy_env import RummyEnv

bots = [AIBot(i, f'TestBot_{i}') for i in range(3)]
env = RummyEnv(bots)
obs = env.reset()
player = env._current_player()
print('current round', env.round_number, 'hand size', len(player.playerHand))
print('hand:', [str(c) for c in player.playerHand])
play = player.decide_play_cards(env.round_number)
print('decide_play_cards returned:', play)
if play:
    print('play structure:', [[str(c) for c in segment] for segment in play])
else:
    print('no play')

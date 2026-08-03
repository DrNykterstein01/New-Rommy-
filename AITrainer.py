import json
import os
from datetime import datetime
from AIBot import AIBot
from Game import mainGameLoop, startRound, electionPhase
from Deck import Deck
from Round import Round
from rummy_env import RummyEnv


class AITrainer:

    def __init__(self, num_bots=1, training_games=100, use_rl=False):
        self.num_bots = num_bots
        self.training_games = training_games
        self.use_rl = use_rl
        self.bots = [AIBot(i, f"AIBot_{i}") for i in range(num_bots)]
        self.training_history = []

        if self.use_rl:
            self._initialize_rl_models()

    def _initialize_rl_models(self):
        dummy_bot = AIBot(0, "dummy")
        state_dim = len(dummy_bot.encode_state(None, 0, [{'hand_size': 0} for _ in range(self.num_bots)], 1, phase=0))
        action_dim = RummyEnv.ACTION_SPACE

        for i, bot in enumerate(self.bots):
            model_file = f"aibot_model_{i}.pt"
            bot.initialize_rl(state_dim, action_dim, model_file=model_file)

    def save_training_state(self, output_file='aibot_model.json'):
        """
        Saves current training state.
        """
        if self.bots:
            self.bots[0].save_model(output_file)
            for i, bot in enumerate(self.bots[1:], start=1):
                bot.save_rl_model(output_file.replace('.json', f'_{i}.pt'))

    def train_bots(self, output_file='aibot_model.json'):
        """
        Trains bots through simulated games.
        """
        print(f"Starting training with {self.training_games} games...")

        for game_num in range(self.training_games):
            print(f"\n--- Training Game {game_num + 1}/{self.training_games} ---")

            game_result = self._simulate_game()

            self._process_game_result(game_result)

            if (game_num + 1) % 10 == 0:
                self._print_progress(game_num + 1)

            if (game_num + 1) % 20 == 0:
                self.save_training_state(output_file)

        self.finalize_training(output_file)
        return self.bots[0]

    def _simulate_game(self):
        """
        Simulates a single game between bots.
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'bot_stats': {},
            'game_details': {}
        }

        for bot in self.bots:
            bot.playerPoints = 0
            bot.playerHand = []
            bot.downHand = False
            bot.isHand = False
            bot.winner = False
            bot.isSpectator = False
            bot.cardDrawn = False
            bot.canDiscard = True
            bot.playerBuy = False
            bot.playerTurn = False
            bot.current_round = None
            bot.playMade = []
            bot.jugadas_bajadas = []

        if self.use_rl:
            env = RummyEnv(self.bots)
            state = env.reset()
            done = False
            while not done:
                current_player = env._current_player()
                if not getattr(current_player, 'rl_enabled', False):
                    raise RuntimeError('RummyEnv advanced to a non-RL player during RL simulation.')

                action = current_player.select_rl_action(state, phase=env.turn_phase, player=current_player)
                next_state, reward, done, info = env.step(action)
                current_player.rl_store_transition(state, action, reward, next_state, done)
                state = next_state

            winner = next((p for p in self.bots if p.winner), None)
            if not winner:
                winner = min(self.bots, key=lambda b: sum(self._get_card_point_value(c) for c in b.playerHand))
        else:
            # Game loop mutates its player list when eliminating players. Use a fresh
            # roster per game so training bots are all restored for the next match.
            game_players = list(self.bots)
            mainGameLoop(None, game_players)
            winner = None
            winner_points = float('inf')
            for bot in self.bots:
                total_points = sum(self._get_card_point_value(c) for c in bot.playerHand)
                if total_points < winner_points:
                    winner = bot
                    winner_points = total_points

        result['bot_stats'] = {
            bot.playerName: {
                'hand_size': len(bot.playerHand),
                'points': sum(self._get_card_point_value(c) for c in bot.playerHand),
                'win': bot == winner
            }
            for bot in self.bots
        }

        result['game_details']['winner'] = winner.playerName if winner else None

        return result

    def _process_game_result(self, game_result):
        """
        Processes game result and updates bots' learning.
        """
        for bot in self.bots:
            bot_result = game_result['bot_stats'][bot.playerName]
            game_outcome = {
                'win': bot_result['win'],
                'points_gained': bot_result['points'],
                'timestamp': game_result['timestamp']
            }

            bot.learn_from_game(game_outcome)

        self.training_history.append(game_result)

    def _print_progress(self, games_completed):
        """
        Prints training progress.
        """
        print(f"\nProgress: {games_completed}/{self.training_games} games completed")

        for bot in self.bots:
            print(f"{bot.playerName}: Win Rate = {bot.win_rate:.2%}, Games = {bot.games_played}")

    def save_training_state(self, output_file='aibot_model.json'):
        """
        Saves current training state.
        """
        if self.bots:
            self.bots[0].save_model(output_file)

    def finalize_training(self, output_file='aibot_model.json'):
        """
        Finalizes training and saves final model.
        """
        print("\n--- Training Complete ---")
        print(f"Total games: {self.training_games}")

        for bot in self.bots:
            print(f"\n{bot.playerName}:")
            print(f"  Games Played: {bot.games_played}")
            print(f"  Games Won: {bot.games_won}")
            print(f"  Win Rate: {bot.win_rate:.2%}")
            print(f"  Strategy Weights: {bot.strategy_weights}")

        self.save_training_state(output_file)

        self._save_training_summary(output_file.replace('.json', '_summary.json'))

    def _save_training_summary(self, summary_file):
        """
        Saves a summary of training results.
        """
        summary = {
            'total_games': self.training_games,
            'total_bots': self.num_bots,
            'timestamp': datetime.now().isoformat(),
            'bot_statistics': [
                {
                    'name': bot.playerName,
                    'games_played': bot.games_played,
                    'games_won': bot.games_won,
                    'win_rate': bot.win_rate,
                    'strategy_weights': bot.strategy_weights
                }
                for bot in self.bots
            ],
            'training_history_sample': self.training_history[-10:]
        }

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

    def _get_card_point_value(self, card):
        """
        Returns point value of a card.
        """
        if card.joker:
            return 25
        elif card.value == 'A':
            return 15
        elif card.value in ['10', 'J', 'Q', 'K']:
            return 10
        else:
            return 5

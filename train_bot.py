#!/usr/bin/env python3

import sys
import argparse
from AITrainer import AITrainer
from AIBot import AIBot


def main():
    parser = argparse.ArgumentParser(
        description='Train the Rummy500 AI Bot'
    )
    parser.add_argument(
        '--games',
        type=int,
        default=2,
        help='Number of games to train (default: 2)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='aibot_model.json',
        help='Output file for trained model (default: aibot_model.json)'
    )
    parser.add_argument(
        '--load',
        type=str,
        help='Load existing model before training'
    )
    parser.add_argument(
        '--bots',
        type=int,
        default=2,
        help='Number of AI bots to train (default: 2)'
    )
    parser.add_argument(
        '--rl',
        action='store_true',
        help='Enable RL training using PyTorch'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Rummy500 AI Bot Trainer")
    print("=" * 60)
    print(f"Training Configuration:")
    print(f"  Games: {args.games}")
    print(f"  Output Model: {args.output}")
    print(f"  Number of Bots: {args.bots}")
    if args.load:
        print(f"  Loading Model: {args.load}")
    print("=" * 60)

    trainer = AITrainer(num_bots=args.bots, training_games=args.games, use_rl=args.rl)

    if args.load:
        print(f"\nLoading existing model from {args.load}...")
        trainer.bots[0].load_model(args.load)
        print("Model loaded successfully!")

    print("\nStarting training...")
    trained_bot = trainer.train_bots(output_file=args.output)

    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    print(f"Model saved to: {args.output}")
    print(f"Final Bot Statistics:")
    print(f"  Win Rate: {trained_bot.win_rate:.2%}")
    print(f"  Games Played: {trained_bot.games_played}")
    print(f"  Games Won: {trained_bot.games_won}")
    print("=" * 60)


if __name__ == "__main__":
    main()

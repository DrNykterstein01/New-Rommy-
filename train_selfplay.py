#!/usr/bin/env python3
"""
CLI para entrenar la DQNNetwork de los bots de Rummy 500 mediante self-play
multi-agente (ver self_play.py para el diseño completo).

Ejemplos:
    # Entrenamiento básico: 4 bots comparten una sola política
    python train_selfplay.py --matches 500 --players 4

    # Continuar entrenando un modelo ya guardado
    python train_selfplay.py --matches 500 --load aibot_selfplay.pt --output aibot_selfplay.pt

    # Con bolsa de oponentes congelados (más robusto, un poco más lento)
    python train_selfplay.py --matches 1000 --opponent-pool 10 --opponent-refresh 50
"""

import argparse

from self_play import SelfPlayTrainer


def main():
    parser = argparse.ArgumentParser(description="Entrenamiento self-play (RL) para Rummy 500")
    parser.add_argument('--matches', type=int, default=200, help='Número de partidas completas a jugar (default: 200)')
    parser.add_argument('--players', type=int, default=4, help='Cantidad de asientos/bots en cada partida (mínimo 3, default: 4)')
    parser.add_argument('--independent', action='store_true', help='Cada bot entrena su propia red en vez de compartir una sola política')
    parser.add_argument('--output', type=str, default='aibot_selfplay.pt', help='Archivo donde guardar el modelo entrenado')
    parser.add_argument('--load', type=str, default=None, help='Cargar un modelo existente antes de seguir entrenando')
    parser.add_argument('--train-every', type=int, default=4, help='Cada cuántos pasos se hace una optimización de la red (default: 4)')
    parser.add_argument('--min-buffer', type=int, default=256, help='Tamaño mínimo del buffer antes de empezar a optimizar (default: 256)')
    parser.add_argument('--target-update', type=int, default=500, help='Cada cuántos pasos se sincroniza la red objetivo (default: 500)')
    parser.add_argument('--epsilon-start', type=float, default=0.9)
    parser.add_argument('--epsilon-min', type=float, default=0.05)
    parser.add_argument('--epsilon-decay-steps', type=int, default=20000)
    parser.add_argument('--opponent-pool', type=int, default=0, help='Tamaño de la bolsa de oponentes congelados (0 = desactivada)')
    parser.add_argument('--opponent-refresh', type=int, default=50, help='Cada cuántas partidas se guarda un nuevo snapshot')
    parser.add_argument('--opponent-prob', type=float, default=0.3, help='Probabilidad de que un asiento use un oponente congelado')
    parser.add_argument('--max-turns', type=int, default=1500, help='Límite de turnos por partida completa (default: 1500)')
    parser.add_argument('--save-every', type=int, default=50, help='Cada cuántas partidas se guarda el modelo (default: 50)')
    parser.add_argument('--verbose-every', type=int, default=10, help='Cada cuántas partidas se imprime el progreso (default: 10)')
    parser.add_argument('--seed', type=int, default=None)

    args = parser.parse_args()

    print("=" * 60)
    print("Rummy500 - Entrenamiento Self-Play (DQN)")
    print("=" * 60)
    print(f"  Partidas: {args.matches}")
    print(f"  Jugadores por partida: {args.players}")
    print(f"  Política: {'independiente por bot' if args.independent else 'compartida (self-play real)'}")
    print(f"  Bolsa de oponentes congelados: {args.opponent_pool if args.opponent_pool > 0 else 'desactivada'}")
    print(f"  Salida: {args.output}")
    print("=" * 60)

    trainer = SelfPlayTrainer(
        num_players=args.players,
        shared_policy=not args.independent,
        train_every=args.train_every,
        min_buffer_size=args.min_buffer,
        target_update_steps=args.target_update,
        epsilon_start=args.epsilon_start,
        epsilon_min=args.epsilon_min,
        epsilon_decay_steps=args.epsilon_decay_steps,
        opponent_pool_size=args.opponent_pool,
        opponent_refresh_every=args.opponent_refresh,
        opponent_use_prob=args.opponent_prob,
        max_turns_per_match=args.max_turns,
        seed=args.seed,
    )

    if args.load:
        print(f"\nCargando modelo desde {args.load}...")
        trainer.load(args.load)

    print("\nIniciando entrenamiento...\n")
    trainer.run(
        num_matches=args.matches,
        verbose_every=args.verbose_every,
        save_path=args.output,
        save_every=args.save_every,
    )

    print("\n" + "=" * 60)
    print("Entrenamiento completado.")
    print(f"Modelo final guardado en: {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()

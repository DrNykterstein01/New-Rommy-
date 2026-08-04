"""
Ciclo de auto-juego (self-play) multi-agente para entrenar la red neuronal
(DQNNetwork, en AIBot.py) del bot de Rummy 500 con aprendizaje por refuerzo.

Este módulo es NUEVO y no reemplaza a AITrainer.py/train_bot.py, que siguen
sirviendo para el entrenamiento heurístico rápido (sin red). SelfPlayTrainer
está pensado específicamente para entrenar de verdad la DQNNetwork, arreglando
dos problemas que tenía el entrenamiento RL tal como estaba antes de hoy:

1. Antes solo un asiento del entorno (RummyEnv) podía ser un agente RL; los
   demás jugaban siempre con la heurística de AIBot. Aquí TODOS los asientos
   pueden ser agentes de la misma red (self-play real), compartiendo un solo
   buffer de repetición para aprovechar cada partida al máximo.
2. Antes solo se hacía UN paso de optimización por partida completa
   (AIBot.rl_finalize_episode), lo cual es demasiado disperso: una partida
   puede tener cientos de turnos y miles de transiciones acumuladas sin que
   la red aprenda nada de ellas hasta el final. Aquí se optimiza cada
   `train_every` pasos, como es estándar en DQN.

Diseño en resumen
------------------
- shared_policy=True (recomendado): todos los bots comparten LA MISMA
  DQNNetwork, el mismo optimizador y el mismo buffer de repetición. Cada bot
  sigue viendo solo su propia mano al codificar el estado (encode_state usa
  self.playerHand), así que la información sigue siendo asimétrica como en
  el juego real; lo único compartido es "el cerebro" que decide.
- shared_policy=False: cada bot entrena su propia red de forma independiente
  (más lento, pero útil si en el futuro quieres bots con estilos distintos).
- Bolsa de oponentes congelados (opcional, opponent_pool_size > 0): cada
  cierto número de partidas se guarda una copia ("snapshot") de los pesos
  actuales. En partidas futuras, algunos asientos (nunca todos) juegan con
  una de esas copias congeladas en vez de con la política más reciente. Esto
  evita que el self-play "persiga su propia cola" (inestabilidad clásica de
  entrenar siempre contra una copia idéntica de uno mismo que cambia a la
  vez que uno).

Requiere PyTorch instalado (igual que el resto del sistema RL de AIBot.py).
"""

import os
import copy
import random
from collections import deque

import numpy as np

from AIBot import AIBot, DQNNetwork, torch
from rummy_env import RummyEnv


class SelfPlayTrainer:

    def __init__(self,
                 num_players=4,
                 shared_policy=True,
                 train_every=4,
                 min_buffer_size=256,
                 target_update_steps=500,
                 epsilon_start=0.9,
                 epsilon_min=0.05,
                 epsilon_decay_steps=20000,
                 opponent_pool_size=0,
                 opponent_refresh_every=50,
                 opponent_use_prob=0.3,
                 max_turns_per_match=2500,
                 seed=None):
        if torch is None:
            raise RuntimeError(
                "PyTorch no está instalado en este entorno. Instálalo con "
                "'pip install torch' antes de usar SelfPlayTrainer."
            )

        # La regla de compra de cartas (y por lo tanto buena parte de la
        # señal estratégica que le interesa aprender a la red) solo aplica
        # de 3 jugadores en adelante, según las reglas del juego.
        if num_players < 3:
            raise ValueError(
                "SelfPlayTrainer necesita al menos 3 jugadores para reflejar "
                "correctamente la regla de compra de cartas."
            )

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)

        self.num_players = num_players
        self.shared_policy = shared_policy
        self.train_every = train_every
        self.min_buffer_size = min_buffer_size
        self.target_update_steps = target_update_steps
        self.epsilon_start = epsilon_start
        self.epsilon_min = epsilon_min
        self.epsilon_decay_steps = epsilon_decay_steps
        self.opponent_pool_size = opponent_pool_size
        self.opponent_refresh_every = opponent_refresh_every
        self.opponent_use_prob = opponent_use_prob
        self.max_turns_per_match = max_turns_per_match

        self.global_step = 0
        self.matches_played = 0
        self.opponent_snapshots = (
            deque(maxlen=opponent_pool_size) if opponent_pool_size > 0 else None
        )

        self.bots = [AIBot(i, f"SelfPlayBot_{i}") for i in range(num_players)]

        dummy_state = self.bots[0].encode_state(
            None, 0, [{'hand_size': 0} for _ in range(num_players)], 1, phase=0
        )
        self.state_dim = len(dummy_state)
        self.action_dim = RummyEnv.ACTION_SPACE

        self._primary = None
        self._build_networks()

        # Historial de métricas por partida (útil para graficar el progreso
        # más adelante, por ejemplo con matplotlib fuera de este módulo).
        self.history = []

    # ------------------------------------------------------------------
    # Construcción de redes
    # ------------------------------------------------------------------
    def _build_networks(self):
        if self.shared_policy:
            primary = self.bots[0]
            primary.initialize_rl(self.state_dim, self.action_dim)
            for bot in self.bots[1:]:
                bot.rl_enabled = True
                bot.rl_state_dim = self.state_dim
                bot.rl_action_dim = self.action_dim
                bot.rl_policy_net = primary.rl_policy_net
                bot.rl_target_net = primary.rl_target_net
                bot.rl_optimizer = primary.rl_optimizer
                bot.rl_buffer = primary.rl_buffer
            self._primary = primary
        else:
            for bot in self.bots:
                bot.initialize_rl(self.state_dim, self.action_dim)
            self._primary = None

        for bot in self.bots:
            bot.rl_epsilon = self.epsilon_start
            bot.rl_epsilon_min = self.epsilon_min

    def _current_epsilon(self):
        if self.global_step >= self.epsilon_decay_steps:
            return self.epsilon_min
        frac = self.global_step / max(1, self.epsilon_decay_steps)
        return self.epsilon_start + frac * (self.epsilon_min - self.epsilon_start)

    # ------------------------------------------------------------------
    # Bolsa de oponentes congelados
    # ------------------------------------------------------------------
    def _maybe_snapshot_opponent(self):
        if self.opponent_snapshots is None:
            return
        if self.matches_played == 0 or self.matches_played % self.opponent_refresh_every != 0:
            return
        source_net = self._primary.rl_policy_net if self.shared_policy else self.bots[0].rl_policy_net
        self.opponent_snapshots.append(copy.deepcopy(source_net.state_dict()))

    def _pick_frozen_seats(self):
        """
        Devuelve {indice_de_asiento: red_congelada} para la próxima partida.
        Nunca deja TODOS los asientos congelados: siempre debe quedar al
        menos uno generando datos de entrenamiento en vivo.
        """
        if not self.opponent_snapshots:
            return {}

        frozen = {}
        for idx in range(self.num_players):
            if random.random() < self.opponent_use_prob:
                snapshot = random.choice(self.opponent_snapshots)
                net = DQNNetwork(self.state_dim, self.action_dim)
                net.load_state_dict(snapshot)
                net.eval()
                frozen[idx] = net

        if len(frozen) == self.num_players:
            frozen.pop(random.choice(list(frozen.keys())))

        return frozen

    # ------------------------------------------------------------------
    # Entrenamiento
    # ------------------------------------------------------------------
    def run(self, num_matches=100, verbose_every=10, save_path=None, save_every=50):
        for match_idx in range(num_matches):
            self._maybe_snapshot_opponent()
            frozen_seats = self._pick_frozen_seats()
            self._play_match(frozen_seats)
            self.matches_played += 1

            if save_path and (match_idx + 1) % save_every == 0:
                self.save(save_path)

            if (match_idx + 1) % verbose_every == 0:
                self._print_progress(match_idx + 1)

        if save_path:
            self.save(save_path)

        return self.history

    def _reset_bots(self):
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

    def _play_match(self, frozen_seats):
        self._reset_bots()
        env = RummyEnv(self.bots, max_turns=self.max_turns_per_match)
        state = env.reset()
        done = False
        turns_taken = 0
        # Red de seguridad ante un bucle sin fin por algún caso límite no
        # contemplado: cada turno real implica varias llamadas a step()
        # (robar / bajarse / descartar), así que damos bastante margen por
        # encima del límite de turnos que ya aplica RummyEnv internamente.
        safety_cap = self.max_turns_per_match * 6

        print(f"\n{'='*70}")
        print(f"[NUEVA PARTIDA #{self.matches_played + 1}] {self.num_players} jugadores | "
              f"límite de turnos: {self.max_turns_per_match} | asientos congelados: {list(frozen_seats.keys()) or 'ninguno'}")
        print(f"{'='*70}")

        while not done and turns_taken < safety_cap:
            seat_idx = env.current_player_index
            current_player = env._current_player()
            is_frozen = seat_idx in frozen_seats

            if is_frozen:
                action = self._frozen_action(frozen_seats[seat_idx], state)
            else:
                current_player.rl_epsilon = self._current_epsilon()
                action = current_player.select_rl_action(state, phase=env.turn_phase, player=current_player)

            next_state, reward, done, info = env.step(action)

            if not is_frozen:
                current_player.rl_store_transition(state, action, reward, next_state, done)
                self.global_step += 1

                if self.global_step % self.train_every == 0:
                    self._optimize_step()
                if self.global_step % self.target_update_steps == 0:
                    self._sync_target()

            state = next_state
            turns_taken += 1

        # OJO: player.winner se marca cada vez que alguien gana una RONDA
        # (rummy_env.py líneas ~82/97/209/590) y nunca se limpia entre rondas
        # dentro de la misma partida. Por eso NO sirve para saber quién ganó
        # la partida completa: si SelfPlayBot_0 ganó la primera ronda, esa
        # bandera se le queda pegada aunque después sea eliminado. El ganador
        # real de la partida es, simplemente, el único jugador que sigue sin
        # estar eliminado (isSpectator=False) cuando la partida termina. Si
        # la partida se cortó por timeout o por el safety_cap, sigue habiendo
        # más de un jugador activo, así que no hay ganador (None).
        active_players = [p for p in self.bots if not p.isSpectator]
        winner = active_players[0] if len(active_players) == 1 else None
        if turns_taken >= safety_cap and not done:
            print(f"[SAFETY CAP] Partida cortada por el propio SelfPlayTrainer tras {turns_taken} pasos "
                  f"(no debería pasar seguido; si ocurre a menudo, algo sigue atascado).")
        print(f"[FIN PARTIDA #{self.matches_played + 1}] Ganador: {winner.playerName if winner else '(nadie - cortada)'} "
              f"| pasos: {turns_taken}\n{'='*70}")

        self.history.append({
            'match': self.matches_played + 1,
            'steps': turns_taken,
            'winner': winner.playerName if winner else None,
            'epsilon': self._current_epsilon(),
            'buffer_size': len(self._primary.rl_buffer) if self.shared_policy else None,
            'frozen_seats': list(frozen_seats.keys()),
        })

    def _frozen_action(self, net, state):
        # Casi siempre juega greedy con la política congelada; un poquito de
        # exploración evita que sea 100% predecible para el agente en vivo.
        if random.random() < 0.05:
            return random.randrange(self.action_dim)
        with torch.no_grad():
            state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            q_values = net(state_tensor)
            return int(torch.argmax(q_values, dim=1).item())

    def _optimize_step(self):
        if self.shared_policy:
            buffer_ready = len(self._primary.rl_buffer) >= max(self.min_buffer_size, self._primary.rl_batch_size)
            if buffer_ready:
                self._primary._rl_optimize_model()
        else:
            for bot in self.bots:
                if len(bot.rl_buffer) >= max(self.min_buffer_size, bot.rl_batch_size):
                    bot._rl_optimize_model()

    def _sync_target(self):
        if self.shared_policy:
            self._primary.rl_target_net.load_state_dict(self._primary.rl_policy_net.state_dict())
        else:
            for bot in self.bots:
                bot.rl_target_net.load_state_dict(bot.rl_policy_net.state_dict())

    def _print_progress(self, matches_done):
        recent = self.history[-10:]
        avg_steps = sum(h['steps'] for h in recent) / len(recent)
        buf = recent[-1]['buffer_size']
        print(
            f"[Self-play] Partidas: {matches_done} | pasos globales: {self.global_step} | "
            f"epsilon: {self._current_epsilon():.3f} | pasos/partida (prom. últimas {len(recent)}): "
            f"{avg_steps:.1f}" + (f" | buffer: {buf}" if buf is not None else "")
        )

    # ------------------------------------------------------------------
    # Guardado / carga
    # ------------------------------------------------------------------
    def save(self, path):
        if self.shared_policy:
            torch.save(self._primary.rl_policy_net.state_dict(), path)
            print(f"Modelo compartido guardado en: {path}")
        else:
            base, ext = os.path.splitext(path)
            for i, bot in enumerate(self.bots):
                fname = f"{base}_{i}{ext}"
                torch.save(bot.rl_policy_net.state_dict(), fname)
            print(f"Modelos independientes guardados como: {base}_N{ext}")

    def load(self, path):
        if self.shared_policy:
            state_dict = torch.load(path)
            self._primary.rl_policy_net.load_state_dict(state_dict)
            self._primary.rl_target_net.load_state_dict(state_dict)
            print(f"Modelo compartido cargado desde: {path}")
        else:
            base, ext = os.path.splitext(path)
            for i, bot in enumerate(self.bots):
                fname = f"{base}_{i}{ext}"
                if os.path.exists(fname):
                    state_dict = torch.load(fname)
                    bot.rl_policy_net.load_state_dict(state_dict)
                    bot.rl_target_net.load_state_dict(state_dict)
                    print(f"Modelo de {bot.playerName} cargado desde: {fname}")

import json
import os
from datetime import datetime
from itertools import combinations
from Player import Player
from Card import Card
import random
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
except ImportError:
    torch = None
    nn = None
    optim = None

if torch is not None:
    class DQNNetwork(nn.Module):
        def __init__(self, input_dim, output_dim):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, 64),
                nn.ReLU(),
                nn.Linear(64, 64),
                nn.ReLU(),
                nn.Linear(64, output_dim)
            )

        def forward(self, x):
            return self.net(x)


class AIBot(Player):

    # Phase constants match RummyEnv
    PHASE_DRAW = 0
    PHASE_PLAY = 1
    PHASE_DISCARD = 2

    # Must match RummyEnv insertion encoding parameters.
    MAX_TABLE_PLAYS = 8
    MAX_HAND_SLOTS = 13
    POS_COUNT = 2

    def __init__(self, bot_id, bot_name="AI Bot"):
        super().__init__(bot_id, bot_name)
        self.is_ai = True

        # Current round context (set by Game loop) to adapt strategy
        self.current_round = None
        self.strategy_weights = {
            'aggressive': 0.5,
            'conservative': 0.3,
            'balanced': 0.2
        }

        self.learned_patterns = {
            'optimal_plays': {},
            'discard_strategy': {},
            'card_values': {}
        }

        self.game_history = []
        self.decisions_made = []
        self.win_rate = 0.0
        self.games_played = 0
        self.games_won = 0
        self.purchase_count = 0

        self.rl_enabled = False
        self.rl_state_dim = 0
        self.rl_action_dim = 0
        self.rl_policy_net = None
        self.rl_target_net = None
        self.rl_optimizer = None
        self.rl_buffer = []
        self.rl_buffer_capacity = 10000
        self.rl_batch_size = 32
        self.rl_gamma = 0.99
        self.rl_epsilon = 0.9
        self.rl_epsilon_min = 0.05
        self.rl_epsilon_decay = 0.995
        self.rl_target_update = 10
        self.rl_episode_count = 0
        self.rl_model_file = None
        # Guardan el (estado, acción) de la fase de robo mientras se juega a
        # través de Game.mainGameLoop, para poder completar esa transición más
        # tarde con rl_record_draw_transition(). RummyEnv/SelfPlayTrainer NO
        # necesitan esto: manejan sus propias transiciones directamente.
        self._rl_last_draw_state = None
        self._rl_last_draw_action = None

    def initialize_rl(self, state_dim, action_dim, model_file=None):
        if torch is None:
            print("PyTorch no está instalado: RL no disponible.")
            self.rl_enabled = False
            return

        self.rl_enabled = True
        self.rl_state_dim = state_dim
        self.rl_action_dim = action_dim
        self.rl_policy_net = DQNNetwork(state_dim, action_dim)
        self.rl_target_net = DQNNetwork(state_dim, action_dim)
        self.rl_target_net.load_state_dict(self.rl_policy_net.state_dict())
        self.rl_target_net.eval()
        self.rl_optimizer = optim.Adam(self.rl_policy_net.parameters(), lr=1e-3)
        self.rl_buffer = []
        self.rl_episode_steps = []
        self.rl_episode_count = 0
        self.rl_model_file = model_file

    def _card_value_index(self, card):
        if card is None:
            return None
        if getattr(card, 'joker', False):
            return len(Card.values)
        return Card.values.index(card.value)

    def _card_suit_index(self, card):
        if card is None or getattr(card, 'joker', False):
            return None
        return Card.types.index(card.type)

    def encode_state(self, discard_top_card, deck_size, players_info, round_number, phase=0):
        hand_value_counts = [0] * (len(Card.values) + 1)
        hand_suit_counts = [0] * len(Card.types)
        for card in self.playerHand:
            if card.joker:
                hand_value_counts[-1] += 1
            else:
                hand_value_counts[Card.values.index(card.value)] += 1
                hand_suit_counts[Card.types.index(card.type)] += 1

        hand_size = len(self.playerHand)
        joker_count = sum(1 for c in self.playerHand if getattr(c, 'joker', False))

        discard_rank = [0] * (len(Card.values) + 1)
        discard_suit = [0] * len(Card.types)
        if discard_top_card:
            rank_index = self._card_value_index(discard_top_card)
            if rank_index is not None:
                discard_rank[rank_index] = 1
            suit_index = self._card_suit_index(discard_top_card)
            if suit_index is not None:
                discard_suit[suit_index] = 1

        hand_sizes = [info.get('hand_size', 0) for info in players_info]
        other_sizes = hand_sizes[:]
        if hand_size in other_sizes:
            try:
                other_sizes.remove(hand_size)
            except ValueError:
                pass

        avg_other_size = sum(other_sizes) / max(1, len(other_sizes))
        max_other_size = max(other_sizes) if other_sizes else 0
        min_other_size = min(other_sizes) if other_sizes else 0

        round_onehot = [0, 0, 0, 0]
        if 1 <= round_number <= 4:
            round_onehot[round_number - 1] = 1

        features = []
        features.extend(hand_value_counts)
        features.extend(hand_suit_counts)
        features.append(hand_size / 13.0)
        features.append(joker_count / 3.0)
        features.extend(discard_rank)
        features.extend(discard_suit)
        features.append(deck_size / 100.0)
        features.extend(round_onehot)

        phase_onehot = [0, 0, 0]
        if 0 <= phase < 3:
            phase_onehot[phase] = 1
        features.extend(phase_onehot)

        features.extend([avg_other_size / 13.0, max_other_size / 13.0, min_other_size / 13.0])
        features.append(1.0 if self.downHand else 0.0)

        return np.array(features, dtype=np.float32)

    def select_rl_action(self, state, phase=None, player=None):
        if not self.rl_enabled or self.rl_policy_net is None:
            return None

        allowed_actions = self._rl_allowed_actions(phase, player)
        explore = random.random() < self.rl_epsilon
        if explore:
            return random.choice(allowed_actions)

        with torch.no_grad():
            state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            q_values = self.rl_policy_net(state_tensor)[0]
            if phase is None or allowed_actions == list(range(self.rl_action_dim)):
                action = int(torch.argmax(q_values).item())
            else:
                subset = q_values[allowed_actions]
                best_rel = int(torch.argmax(subset).item())
                action = allowed_actions[best_rel]

        return action

    # ---------------------- RL action / insertion mapping ---------------------
    # NOTA: estos dos métodos ya no se usan en el flujo activo (la inserción
    # ahora es automática, ver RummyEnv._apply_play). Se dejan por si en el
    # futuro se quiere volver a experimentar con inserciones como decisión
    # explícita de RL.
    def encode_insertion_action(self, play_idx, hand_slot, pos):
        """Encodes an insertion choice to a single integer RL action.

        play_idx: index of target play on table (0-based)
        hand_slot: index of card in current hand (0-based)
        pos: 0 for start, 1 for end
        """
        base = 3
        return base + (play_idx * (self.MAX_HAND_SLOTS * self.POS_COUNT)) + (hand_slot * self.POS_COUNT) + pos

    def decode_insertion_action(self, action):
        """Decodes an RL action integer into (play_idx, hand_slot, pos) or None if not insertion."""
        base = 3
        if action < base:
            return None
        rel = action - base
        per_play = self.MAX_HAND_SLOTS * self.POS_COUNT
        play_idx = rel // per_play
        rem = rel % per_play
        hand_slot = rem // self.POS_COUNT
        pos = rem % self.POS_COUNT
        return int(play_idx), int(hand_slot), int(pos)

    def _rl_allowed_actions(self, phase, player):
        """Return allowed RL action indices for the current phase and player state.

        Nota: la inserción de cartas (cuando el jugador ya se bajó) ya NO se
        decide como una acción de RL — se ejecuta automáticamente en
        RummyEnv._apply_play(). Antes existía un espacio de acciones mucho
        más grande para codificar inserciones explícitas, pero eso diluía
        tanto la exploración que la red casi nunca llegaba a intentarlas.
        """
        return [0, 1, 2]

    def rl_record_draw_transition(self, next_state, reward=0.0, done=False):
        """
        Completa la transición de la fase de "robar carta" cuando el bot juega
        a través de Game.mainGameLoop (fuera de RummyEnv, que gestiona sus
        propias transiciones directamente en cada step()). Debe llamarse justo
        después de que el bot terminó de robar. Si decide_draw_source() no usó
        la red en este turno (rl_enabled apagado, o no había elección previa
        guardada), no hace nada.
        """
        if not self.rl_enabled or torch is None:
            return
        state = self._rl_last_draw_state
        action = self._rl_last_draw_action
        if state is None or action is None:
            return
        self.rl_store_transition(state, action, reward, next_state, done)
        self._rl_last_draw_state = None
        self._rl_last_draw_action = None

    def rl_store_transition(self, state, action, reward, next_state, done):
        if not self.rl_enabled or torch is None:
            return
        if len(self.rl_buffer) >= self.rl_buffer_capacity:
            self.rl_buffer.pop(0)
        self.rl_buffer.append((state, action, reward, next_state, done))

    def rl_finalize_episode(self, win):
        if not self.rl_enabled or torch is None:
            return

        # Optimize the model once per episode.
        self._rl_optimize_model()
        self.rl_episode_count += 1
        self.rl_epsilon = max(self.rl_epsilon_min, self.rl_epsilon * self.rl_epsilon_decay)
        if self.rl_episode_count % self.rl_target_update == 0:
            self.rl_target_net.load_state_dict(self.rl_policy_net.state_dict())

    def _rl_store_transition(self, state, action, reward, next_state, done):
        if len(self.rl_buffer) >= self.rl_buffer_capacity:
            self.rl_buffer.pop(0)
        self.rl_buffer.append((state, action, reward, next_state, done))

    def _rl_optimize_model(self):
        if torch is None or len(self.rl_buffer) < self.rl_batch_size:
            return

        batch = random.sample(self.rl_buffer, self.rl_batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states_tensor = torch.tensor(np.stack(states), dtype=torch.float32)
        actions_tensor = torch.tensor(actions, dtype=torch.long).unsqueeze(1)
        rewards_tensor = torch.tensor(rewards, dtype=torch.float32).unsqueeze(1)
        next_states_tensor = torch.tensor(np.stack(next_states), dtype=torch.float32)
        dones_tensor = torch.tensor(dones, dtype=torch.float32).unsqueeze(1)

        q_values = self.rl_policy_net(states_tensor).gather(1, actions_tensor)
        next_q_values = self.rl_target_net(next_states_tensor).max(1)[0].detach().unsqueeze(1)
        expected_q = rewards_tensor + (1.0 - dones_tensor) * self.rl_gamma * next_q_values

        loss = nn.functional.mse_loss(q_values, expected_q)
        self.rl_optimizer.zero_grad()
        loss.backward()
        self.rl_optimizer.step()

    def save_rl_model(self, filename=None):
        if torch is None or not self.rl_enabled or self.rl_policy_net is None:
            return
        filename = filename or self.rl_model_file
        if filename is None:
            return
        torch.save(self.rl_policy_net.state_dict(), filename)

    def load_rl_model(self, filename):
        if torch is None:
            print("PyTorch no está instalado: no se puede cargar el modelo RL.")
            return
        self.initialize_rl(self.rl_state_dim or 50, self.rl_action_dim or 3, model_file=filename)
        if os.path.exists(filename):
            self.rl_policy_net.load_state_dict(torch.load(filename))
            self.rl_target_net.load_state_dict(self.rl_policy_net.state_dict())
            print(f"Modelo RL cargado desde {filename}")
        else:
            print(f"Archivo de modelo RL {filename} no encontrado.")

    def decide_draw_source(self, discard_top_card, deck_size, players_info):
        """
        Decides whether to draw from discard pile or deck.
        Returns True for discard, False for deck.
        """
        if self.rl_enabled:
            state = self.encode_state(discard_top_card, deck_size, players_info, self.current_round or 1, phase=0)
            rl_choice = self.select_rl_action(state, phase=self.PHASE_DRAW, player=self)
            if rl_choice is not None:
                self._rl_last_draw_state = state
                self._rl_last_draw_action = rl_choice
                return rl_choice == 0

        if not discard_top_card:
            return False

        card_usefulness = self._evaluate_card_usefulness(discard_top_card)
        hand_completion = self._evaluate_hand_completion()

        risk_factor = self._calculate_risk_factor(players_info)

        if card_usefulness > 0.6 and hand_completion < 0.5:
            return True
        elif random.random() < (0.3 - risk_factor):
            return True

        return False

    def decide_play_cards(self, round_number):
        """
        Decides which cards to play based on current hand and round requirements.
        Returns list of tuples: (cards_to_play, play_type)
        """
        self.current_round = round_number

        # Only allowed to bajar once per round. If already down, return None
        # (insertions are handled elsewhere via decide_insert_card).
        if self.downHand:
            return None

        valid_plays = self._find_valid_plays(round_number)

        if not valid_plays:
            return None

        # Round 4 requires using ALL cards. Partial plays are only used to
        # guide discarding — they must NOT be played as a bajar attempt.
        if round_number == 4:
            full_plays = []
            for play in valid_plays:
                if isinstance(play, tuple):
                    total = sum(len(p) for p in play)
                else:
                    total = len(play)
                if total == len(self.playerHand):
                    full_plays.append(play)
            if not full_plays:
                return None
            valid_plays = full_plays

        best_play = self._select_best_play(valid_plays, round_number)
        return best_play

    def decide_discard(self, must_burn_joker=False):
        """
        Decides which card to discard.
        Returns the card to discard.
        """
        #AQUÍ EL CONDICIONAL QUE DEFINE UNA SITUACIÓN BÁSICA EN LA QUE SEA LO MEJOR QUEMAR UN JOKER.
        #ESTO DESPUÉS LO CAMBIARÉ, YA QUE DEBO PROGRAMAR UNA FUNCIÓN QUE LE PERMITA AL BOT DECIDIR
        #SI LE CONVIENE QUEMAR UN JOKER O NO.
        if self.cardDrawn and self.downHand and any(c.joker for c in self.playerHand):
            must_burn_joker = True
        if len(self.playerHand) == 0:
            return
        if must_burn_joker:
            return self._find_joker_burn_pair()

        # Avoid discarding cards that are part of a valid play for the current round
        try:
            round_ctx = self.current_round
        except Exception:
            round_ctx = None

        if round_ctx and not self.downHand:
            # Round 4: use partial play to protect cards that are part of the
            # best partial combination (2 trios + 1 sequence, even if incomplete).
            # Discard from the cards NOT in the partial play first.
            if round_ctx == 4:
                protected = self._get_partial_play_cards()
                if protected:
                    candidates = [c for c in self.playerHand if c not in protected]
                    if candidates:
                        card_values = self._calculate_card_values()
                        worst_card = min(candidates, key=lambda c: card_values.get(c, 0))
                        return worst_card
                    # All cards are in the partial play but we still can't bajar:
                    # discard the lowest-value card from the smallest group.
                    partial = self._find_best_partial_play()
                    if partial:
                        smallest = min(partial, key=len)
                        if smallest:
                            card_values = self._calculate_card_values()
                            worst_card = min(smallest, key=lambda c: card_values.get(c, 0))
                            return worst_card

            valid_plays = self._find_valid_plays(round_ctx)
            if valid_plays:
                best = self._select_best_play(valid_plays, round_ctx)
                if best:
                    # `best` is a tuple of plays (each play is a list of Card)
                    used_cards = [c for play in best for c in play]
                    # prefer discarding a card not needed for the best play
                    candidates = [c for c in self.playerHand if c not in used_cards]
                    if candidates:
                        card_values = self._calculate_card_values()
                        worst_card = min(candidates, key=lambda c: card_values.get(c, 0))
                        return worst_card

        # fallback: discard the lowest-value card
        card_values = self._calculate_card_values()
        worst_card = min(self.playerHand, key=lambda c: card_values.get(c, 0))

        return worst_card

    def decide_buy_card(self, discard_card, hand_value, players_info):
        """
        Decides whether to buy a discarded card.
        Returns True or False.
        """
        if not discard_card:
            return False

        # Válvula de seguridad dura: comprar entrega SIEMPRE una carta extra
        # de castigo, así que sin importar qué tan "completa" parezca la
        # mano, no tiene sentido seguir comprando si ya se acumularon
        # demasiadas cartas (empezamos con 10; más allá de esto el riesgo de
        # quedar con una mano imposible de vaciar supera cualquier beneficio).
        if len(self.playerHand) >= 16:
            return False

        usefulness = self._evaluate_card_usefulness(discard_card)
        current_hand_score = sum(self._get_card_point_value(c) for c in self.playerHand)
        completion = self._evaluate_hand_completion()

        # Heurística conservadora: si no estás bajado aún y tu mano NO está
        # lo suficientemente cerca de completar una bajada, evitar comprar.
        # Comprar entrega además una carta de castigo y puede dificultar bajar.
        if (not self.downHand and completion < 0.25) or self.downHand:
            return False

        # Ronda 4 es especialmente sensible: necesitas usar TODAS las cartas.
        # Si la carta del descarte pertenece a la jugada parcial, conviene comprar.
        if self.current_round == 4 and not self.downHand:
            partial = self._get_partial_play_cards()
            if discard_card in partial:
                return True
            if self.purchase_count >= 2:
                return False
            if len(self.playerHand) >= 14:
                return False
            if len(self.playerHand) >= 12:
                return usefulness > 0.9 and completion >= 0.65
            if len(self.playerHand) >= 10:
                return usefulness > 0.75 and completion >= 0.45
            return usefulness > 0.7

        if current_hand_score > 200:
            return usefulness > 0.4

        return usefulness > 0.5

    def decide_move_joker(self, plays_in_table):
        """
        Decides if joker should be moved in a sequence.
        Returns (play_index, new_position) or None
        """
        for i, play in enumerate(plays_in_table):
            if self._has_movable_joker(play):
                new_pos = self._calculate_best_joker_position(play)
                if new_pos is not None:
                    return (i, new_pos)

        return None

    def decide_substitute_joker(self, plays_in_table):
        """
        Decides if a joker should be substituted in a sequence.
        Returns (play_index, card_to_use) or None
        """
        for i, play in enumerate(plays_in_table):
            if self._contains_joker(play):
                joker_card = self._find_substitutable_card(play)
                if joker_card and joker_card in self.playerHand:
                    return (i, joker_card)

        return None

    def decide_insert_card(self, plays_in_table):
        """
        Decides which card to insert into existing plays.
        This is a key strategy: inserting cards reduces hand size without initial play.
        Returns (play_index, card_to_insert, position) or None.

        position siempre es la cadena "start" o "end" (insertCard() espera
        exactamente eso; para un trío la posición no cambia la validez de la
        jugada, así que usamos "end").
        """
        if not self.downHand:
            return None

        best_insertion = None
        best_score = -1

        for play_idx, play in enumerate(plays_in_table):
            play_type = self._get_play_type(play)
            for card in self.playerHand:
                if play_type == 'sequence':
                    candidate_positions = self._get_insertion_positions(card, play)
                elif play_type == 'trio':
                    candidate_positions = ["end"] if self._can_insert_into_trio(card, play) is not None else []
                else:
                    # Jugada 'mixed' o no reconocida: no debería ocurrir para
                    # algo que ya está bajado en la mesa, pero por seguridad
                    # simplemente no se intenta insertar ahí.
                    candidate_positions = []

                for position in candidate_positions:
                    insertion_score = self._score_insertion(card, play, play_idx)
                    if card.joker:
                        # A Joker is worth 25 points, so dispose of it whenever
                        # the table accepts it without breaking the play.
                        insertion_score += 2.0
                    if position == "end":
                        insertion_score += 0.01

                    if insertion_score > best_score:
                        best_score = insertion_score
                        best_insertion = (play_idx, card, position)

        return best_insertion

    def _try_insert_card(self, card, play):
        """
        Tries to insert a card into a play.
        Returns the position where it can be inserted, or None if impossible.

        Validates:
        - Card can extend a sequence
        - Card value matches a trio
        - Joker can be substituted for a trio card
        """
        play_type = self._get_play_type(play)

        if play_type == 'sequence':
            positions = self._get_insertion_positions(card, play)
            return positions[0] if positions else None
        elif play_type == 'trio':
            return self._can_insert_into_trio(card, play)

        return None

    def _get_insertion_positions(self, card, sequence):
        """Returns every valid end where a card can extend a sequence."""
        if self._get_play_type(sequence) != 'sequence':
            return []

        positions = []
        if self._is_valid_sequence_extension(card, sequence, "start"):
            positions.append("start")
        if self._is_valid_sequence_extension(card, sequence, "end"):
            positions.append("end")
        return positions

    def _is_valid_sequence_extension(self, card, sequence, position):
        """Validates one concrete sequence extension without mutating the table."""
        candidate = ([card] + list(sequence)) if position == "start" else (list(sequence) + [card])
        if card.joker or any(current_card.joker for current_card in sequence):
            return self.isValidStraightFJoker(candidate)
        return self.isValidStraightF(candidate)

    def _can_insert_into_sequence(self, card, sequence):
        """
        Checks if a card can be inserted into a sequence.
        Sequences can be extended at the ends if the card is consecutive.
        Returns the position (0 for start, len for end) or None.
        """
        sequence_type = next((c.type for c in sequence if not c.joker), None)
        if sequence_type is None:
            return None

        if card.joker:
            positions = self._get_insertion_positions(card, sequence)
            return positions[0] if positions else None

        card_values = Card.values
        card_idx = card_values.index(card.value) if card.value in card_values else -1

        if card_idx == -1 or card.type != sequence_type:
            return None

        sequence_indices = []
        for seq_card in sequence:
            if not seq_card.joker:
                idx = card_values.index(seq_card.value) if seq_card.value in card_values else -1
                if idx != -1:
                    sequence_indices.append(idx)

        if not sequence_indices:
            return None

        min_idx = min(sequence_indices)
        max_idx = max(sequence_indices)

        positions = []
        if card_idx == min_idx - 1:
            positions.append("start")
        if card_idx == max_idx + 1:
            positions.append("end")

        if positions:
            return positions[0]

        return None

    def _can_insert_into_trio(self, card, trio):
        """
        Checks if a card can be inserted into a trio.
        Trios accept cards with the same value (max 1 joker per trio).
        Returns position 0 (always append for trios) or None.
        """
        if not trio or len(trio) < 3:
            return None

        trio_value = trio[0].value

        if card.value == trio_value:
            joker_count = sum(1 for c in trio if c.joker)
            if not card.joker and joker_count <= 1:
                return 0

        if card.joker and not any(c.joker for c in trio):
            return 0

        return None

    def _get_play_type(self, play):
        """
        Determines if a play is a sequence or trio.
        """
        if not play or len(play) < 3:
            return None

        first_card = play[0]
        #print(f"PLAY EN CUESTIÓN PARA EL GETPLAYTYPE: {[str(c) for c in play]}")

        types = set(c.type for c in play if not c.joker) #ANALIZAR ESTA LÍNEA
        #AttributeError: 'str' object has no attribute 'joker'. Did you mean: 'lower'?
        #lo está leyendo como string, eso quiere decir, que seguramente en esta línea
        #está leyendo es el nombre del jugador, cosa que no debería ser
        if len(types) == 1:
            return 'sequence'

        values = set(c.value for c in play if not c.joker)
        if len(values) == 1:
            return 'trio'

        return 'mixed'

    def _score_insertion(self, card, play, play_idx):
        """
        Scores how good an insertion would be.
        Higher score = better insertion.
        """
        score = 0.0

        card_points = self._get_card_point_value(card)
        score += (25 - card_points) / 25

        remaining_hand = [c for c in self.playerHand if c != card]
        remaining_points = sum(self._get_card_point_value(c) for c in remaining_hand)

        if remaining_points < 50:
            score += 0.5

        play_type = self._get_play_type(play)
        if play_type == 'sequence':
            score += 0.3
        elif play_type == 'trio':
            score += 0.2

        return score

    def _find_valid_plays(self, round_number):
        """
        Finds all valid plays possible with current hand.
        """
        plays = []

        trios = self._find_all_trios()
        sequences = self._find_all_sequences()

        if round_number == 1:
            combinations = self._combine_plays(trios, sequences, min_trios=1, min_sequences=1)
        elif round_number == 2:
            combinations = self._combine_plays([], sequences, min_sequences=2)
        elif round_number == 3:
            combinations = self._combine_plays(trios, [], min_trios=3)
        elif round_number == 4:
            combinations = self._combine_plays(trios, sequences, min_trios=2, min_sequences=1, use_all=True)
            if not combinations:
                partial = self._find_best_partial_play()
                if partial:
                    combinations = [partial]
        else:
            combinations = []

        return combinations

    def _find_best_partial_play(self):
        """
        Para la ronda 4: si no existe una bajada completa (2 tríos + 1 seguidilla
        que use TODAS las cartas), busca la mejor combinación parcial: el conjunto
        de 2 tríos + 1 seguidilla (sin compartir cartas) que use la mayor cantidad
        de cartas posible. Esto guía la decisión de descarte: las cartas que NO
        pertenecen a la jugada parcial son las que se descartan primero.

        Retorna una tupla de jugadas (cada una una lista de Card) o None.
        """
        trios = self._find_all_trios()
        sequences = self._find_all_sequences()

        if not trios or not sequences:
            return None

        best_play = None
        best_card_count = 0
        hand_size = len(self.playerHand)

        def trio_value(t):
            return next((c.value for c in t if not c.joker), None)

        def cards_overlap(group_a, group_b):
            return len({c for play in group_a for c in play} & {c for play in group_b for c in play}) > 0

        for i, trio1 in enumerate(trios):
            for j, trio2 in enumerate(trios):
                if i == j:
                    continue
                if trio_value(trio1) == trio_value(trio2):
                    continue
                if cards_overlap([trio1], [trio2]):
                    continue
                for seq in sequences:
                    if cards_overlap([trio1, trio2], [seq]):
                        continue
                    used = list(trio1) + list(trio2) + list(seq)
                    count = len(used)
                    if count > best_card_count and count <= hand_size:
                        best_card_count = count
                        best_play = (trio1, trio2, seq)

        if best_play is None:
            best_play = self._find_best_two_group_play(trios, sequences, hand_size)

        return best_play

    def _find_best_two_group_play(self, trios, sequences, hand_size):
        """
        Si no se encuentran 2 tríos + 1 seguidilla sin solaparse, busca la mejor
        combinación de 2 grupos cualesquiera (2 tríos, 2 seguidillas, o 1 trío +
        1 seguidilla) que use la mayor cantidad de cartas sin solaparse.
        """
        best_play = None
        best_card_count = 0

        def cards_overlap(group_a, group_b):
            return len({c for play in group_a for c in play} & {c for play in group_b for c in play}) > 0

        all_groups = [(g, 'trio') for g in trios] + [(g, 'seq') for g in sequences]

        for i in range(len(all_groups)):
            for j in range(i + 1, len(all_groups)):
                g1, t1 = all_groups[i]
                g2, t2 = all_groups[j]
                if cards_overlap([g1], [g2]):
                    continue
                if t1 == 'trio' and t2 == 'trio':
                    v1 = next((c.value for c in g1 if not c.joker), None)
                    v2 = next((c.value for c in g2 if not c.joker), None)
                    if v1 == v2:
                        continue
                used = list(g1) + list(g2)
                count = len(used)
                if count > best_card_count and count <= hand_size:
                    best_card_count = count
                    if t1 == 'trio' and t2 == 'trio':
                        best_play = (g1, g2, [])
                    elif t1 == 'seq' and t2 == 'seq':
                        best_play = ([], g1, g2) if False else (g1, g2, [])
                    else:
                        if t1 == 'trio':
                            best_play = (g1, [], g2)
                        else:
                            best_play = (g2, [], g1)

        if best_play is None:
            best_play = self._find_best_single_group_play(trios, sequences, hand_size)

        return best_play

    def _find_best_single_group_play(self, trios, sequences, hand_size):
        """
        Último recurso: si no hay dos grupos sin solaparse, retorna el grupo
        individual más grande (trío o seguidilla) que use más cartas.
        """
        best_play = None
        best_card_count = 0

        all_groups = trios + sequences

        for g in all_groups:
            count = len(g)
            if count > best_card_count and count <= hand_size:
                best_card_count = count
                is_trio = len({c.value for c in g if not c.joker}) == 1
                if is_trio:
                    best_play = (g, [], [])
                else:
                    best_play = (g, [], [])

        return best_play

    def _get_partial_play_cards(self):
        """
        Retorna el conjunto de cartas que pertenecen a la mejor jugada parcial
        de ronda 4. Si no hay jugada parcial, retorna un conjunto vacío.
        """
        if self.current_round != 4 or self.downHand:
            return set()
        partial = self._find_best_partial_play()
        if not partial:
            return set()
        return {c for play in partial for c in play}

    def _find_all_trios(self):
        """
        Finds all valid trios in current hand, including combinations that use one joker.

        El juego usa 2 mazos completos (Round.initDeck), así que puede haber
        cartas EXACTAMENTE duplicadas (p. ej. dos 7♣) en la mano. Antes esto
        se enumeraba con itertools.combinations probando TODOS los tamaños de
        grupo posibles, lo cual escala mal cuando un bot acumula muchas
        cartas del mismo valor (comprando sin bajarse). Aquí solo se prueban
        el tamaño mínimo (3) y el tamaño completo del grupo disponible, que
        alcanza para que la heurística sepa "hay un trío" y "cuál es el
        trío más grande posible", sin la explosión combinatoria.
        """
        trios = []
        natural_cards = [c for c in self.playerHand if not c.joker]
        joker_cards = [c for c in self.playerHand if c.joker]

        value_groups = {}
        for card in natural_cards:
            value_groups.setdefault(card.value, []).append(card)

        seen_keys = set()
        for value, cards in value_groups.items():
            # Un trío solo admite 1 Joker como máximo.
            card_pool = cards + joker_cards[:1]
            pool_size = len(card_pool)
            if pool_size < 3:
                continue

            for r in sorted({3, pool_size}):
                for combo in combinations(card_pool, r):
                    if self._is_valid_trio_combo(combo):
                        combo_list = list(combo)
                        key = tuple(sorted(c.id for c in combo_list))
                        if key not in seen_keys:
                            seen_keys.add(key)
                            trios.append(combo_list)

        return trios

    def _find_all_sequences(self):
        """
        Finds all valid sequences in current hand, including sequences that use jokers.

        Igual que en _find_all_trios: con 2 mazos puede haber cartas
        EXACTAMENTE duplicadas (mismo valor y palo). Para armar una
        seguidilla, una segunda copia de la misma carta nunca ayuda a
        extenderla (una seguidilla no repite rangos), así que primero se
        deduplica por rango dentro de cada palo -eso ya evita casi toda la
        explosión combinatoria-, y luego solo se prueban el tamaño mínimo (4)
        y el tamaño completo del grupo, en vez de todos los tamaños
        intermedios.
        """
        sequences = []
        natural_cards = [c for c in self.playerHand if not c.joker]
        joker_cards = [c for c in self.playerHand if c.joker]

        suit_groups = {}
        for card in natural_cards:
            suit_groups.setdefault(card.type, []).append(card)

        seen_sequences = set()
        for suit, cards in suit_groups.items():
            # Deduplicar por rango: una segunda copia del mismo rango+palo no
            # aporta nada nuevo para formar una escalera más larga.
            unique_by_rank = {}
            for card in cards:
                unique_by_rank.setdefault(card.value, card)
            deduped_cards = list(unique_by_rank.values())

            card_pool = deduped_cards + joker_cards
            pool_size = len(card_pool)
            if pool_size < 4:
                continue

            for r in sorted({4, pool_size}):
                for combo in combinations(card_pool, r):
                    combo_list = list(combo)
                    if self._is_valid_sequence_combo(combo_list):
                        sorted_combo = self.sortedStraight(combo_list)
                        if sorted_combo:
                            if sorted_combo is True:
                                sorted_combo = combo_list
                            key = tuple(sorted(c.id for c in sorted_combo))
                            if key not in seen_sequences:
                                seen_sequences.add(key)
                                sequences.append(sorted_combo)

        return sequences

    def _is_valid_trio_combo(self, cards):
        if len(cards) < 3:
            return False
        if len([c for c in cards if c.joker]) > 1:
            return False
        return self.isValidTrioF(list(cards))

    def _is_valid_sequence_combo(self, cards):
        if len(cards) < 4:
            return False
        joker_count = 0
        for c in cards:
            if c.joker:
                joker_count += 1
                continue
            elif not c.joker:
                joker_count = 0
                continue
        if joker_count > 2:
            return False

        non_jokers = [c for c in cards if not c.joker]
        if not non_jokers:
            return False

        suit = non_jokers[0].type
        if any(c.type != suit for c in non_jokers):
            return False

        sorted_combo = self.sortedStraight(list(cards))
        return bool(sorted_combo)

    def _get_valid_trio_combinations(self, cards):
        """
        Returns valid trio combinations (3+ cards with same value, max 2 jokers total).
        Jokers can replace missing cards to complete trios.
        """
        if len(cards) < 3:
            return []

        combinations = []
        non_joker_cards = [c for c in cards if not c.joker]
        joker_cards = [c for c in cards if c.joker]

        if len(non_joker_cards) >= 3:
            combinations.append(non_joker_cards[:3])
            if len(non_joker_cards) >= 4:
                combinations.append(non_joker_cards[:4])

        if len(non_joker_cards) >= 2 and joker_cards:
            combinations.append(non_joker_cards[:2] + [joker_cards[0]])

        return combinations

    def _find_sequences_in_type(self, cards):
        """
        Finds valid sequences (4+ consecutive cards of same suit).
        Includes sequences using Jokers as wildcards.
        """
        if len(cards) < 4:
            return []

        sequences = []
        card_values = Card.values

        sorted_cards = sorted(cards, key=lambda c: card_values.index(c.value) if c.value in card_values else -1)

        non_joker_cards = [c for c in sorted_cards if not c.joker]
        joker_cards = [c for c in sorted_cards if c.joker]

        for i in range(len(non_joker_cards) - 3):
            for j in range(i + 4, len(non_joker_cards) + 1):
                potential_sequence = non_joker_cards[i:j]
                if self._is_valid_sequence(potential_sequence):
                    sequences.append(potential_sequence)

                if joker_cards:
                    for k in range(1, len(joker_cards) + 1):
                        extended_sequence = potential_sequence + joker_cards[:k]
                        if self._is_valid_sequence(extended_sequence):
                            sequences.append(extended_sequence)

        return sequences

    def _is_valid_sequence(self, cards):
        """
        Validates if a sequence is valid (consecutive cards, max 2 non-consecutive jokers).
        """
        if len(cards) < 4:
            return False

        card_values = Card.values
        joker_positions = [i for i, c in enumerate(cards) if c.joker]

        if len(joker_positions) > 2:
            return False

        if len(joker_positions) == 2:
            if joker_positions[1] - joker_positions[0] == 1:
                return False

        non_joker_cards = [c for c in cards if not c.joker]
        if len(non_joker_cards) < 2:
            return False

        non_joker_indices = [card_values.index(c.value) for c in non_joker_cards if c.value in card_values]

        if len(non_joker_indices) >= 2:
            min_idx = min(non_joker_indices)
            max_idx = max(non_joker_indices)
            expected_length = max_idx - min_idx + 1

            if expected_length == len(cards):
                return True

        return len(cards) == 4 and len([c for c in cards if not c.joker]) >= 3

    def _combine_plays(self, trios, sequences, min_trios=0, min_sequences=0, use_all=False):
        """
        Combines trios and sequences into valid play combinations.
        CRITICAL: Validates that no card is used in multiple plays (no duplicates).
        """
        valid_combinations = []

        def has_overlap(plays):
            all_cards = [c for play in plays for c in play]
            return len(all_cards) != len({c for c in all_cards})

        def groups_share_cards(group1, group2):
            return len({c for play in group1 for c in play} & {c for play in group2 for c in play}) > 0

        def has_distinct_trio_values(trio_plays):
            values = []
            for play in trio_plays:
                value = next((c.value for c in play if not c.joker), None)
                if value is None:
                    return False
                values.append(value)
            return len(set(values)) == len(values)

        if min_trios > 0 and min_sequences > 0:
            for trio_combo in combinations(trios, min_trios):
                if has_overlap(trio_combo):
                    continue
                if min_trios == 2 and min_sequences == 1 and not has_distinct_trio_values(trio_combo):
                    continue
                for seq_combo in combinations(sequences, min_sequences):
                    if has_overlap(seq_combo):
                        continue
                    if not groups_share_cards(trio_combo, seq_combo):
                        all_cards = [c for play in trio_combo for c in play] + [c for play in seq_combo for c in play]
                        if not use_all or len(all_cards) == len(self.playerHand):
                            valid_combinations.append(tuple(trio_combo) + tuple(seq_combo))

        elif min_trios > 0:
            for trio_combo in combinations(trios, min_trios):
                if not has_overlap(trio_combo):
                    valid_combinations.append(tuple(trio_combo))

        elif min_sequences > 0:
            for seq_combo in combinations(sequences, min_sequences):
                if not has_overlap(seq_combo):
                    valid_combinations.append(tuple(seq_combo))

        return valid_combinations

    def _plays_share_no_cards(self, trios, sequences):
        """
        Validates that no card is used in both trios and sequences.
        This prevents the same card (or Joker) from being used twice.
        Returns True if plays don't share any cards, False otherwise.
        """
        trio_cards = {c for play in trios for c in play}
        sequence_cards = {c for play in sequences for c in play}
        return not bool(trio_cards & sequence_cards)

    def _select_best_play(self, valid_plays, round_number):
        """
        Selects the best play from available options based on strategy.
        """
        if not valid_plays:
            return None

        scored_plays = []
        for play in valid_plays:
            score = self._score_play(play, round_number)
            scored_plays.append((score, play))

        scored_plays.sort(reverse=True, key=lambda x: x[0])
        return scored_plays[0][1]

    def _score_play(self, play, round_number):
        """
        Scores a potential play based on various factors.
        """
        score = 0.0

        plays = list(play)
        used_cards = [c for current_play in plays for c in current_play]
        remaining_cards = [c for c in self.playerHand if c not in used_cards]

        remaining_points = sum(self._get_card_point_value(c) for c in remaining_cards)
        score += (500 - remaining_points) / 100

        joker_count = sum(1 for c in used_cards if c.joker)
        score -= joker_count * 0.3

        num_plays = sum(len(current_play) for current_play in plays)
        score += num_plays * 0.2

        if round_number == 4:
            # Strongly prefer plays that use all cards in hand, since round 4 requires
            # a full hand dump with two trios and one sequence.
            if len(used_cards) == len(self.playerHand):
                score += 3.0
            else:
                score += (len(used_cards) / max(1, len(self.playerHand))) * 0.8

            trios = [current_play for current_play in plays if self._get_play_type(current_play) == 'trio']
            sequences = [current_play for current_play in plays if self._get_play_type(current_play) == 'sequence']
            if len(trios) == 2 and len(sequences) == 1:
                score += 1.5
                trio_values = {next((c.value for c in current_play if not c.joker), None) for current_play in trios}
                if len(trio_values) == 2:
                    score += 0.8
                else:
                    score -= 0.8
            else:
                score -= 1.0

        return score

    def _evaluate_card_usefulness(self, card):
        """
        Evaluates how useful a card is for current hand (0-1 scale).
        """
        usefulness = 0.0

        card_value = card.value
        card_type = card.type

        # When in round 2, prioritize same-suit consecutive cards (seguidillas)
        matching_value = sum(1 for c in self.playerHand if c.value == card_value and c != card)
        matching_type = sum(1 for c in self.playerHand if c.type == card_type and c != card)

        if self.current_round == 2:
            # Ignore trio-focused matching, prefer suits/connections
            usefulness += min(matching_type / 4, 0.7)
            # a joker is still valuable for sequences
            if card.joker:
                usefulness += 0.25
        elif self.current_round == 4:
            # Round 4: if the card is part of the best partial play, it's very useful.
            partial_cards = self._get_partial_play_cards()
            if card in partial_cards:
                usefulness += 0.8
            else:
                usefulness += min(matching_value / 3, 0.3)
                usefulness += min(matching_type / 4, 0.25)
            if card.joker:
                usefulness += 0.3
        else:
            usefulness += min(matching_value / 3, 0.4)
            usefulness += min(matching_type / 4, 0.35)
            if card.joker:
                usefulness += 0.25

        return min(usefulness, 1.0)

    def _evaluate_hand_completion(self):
        """
        Evaluates how close the hand is to completing a valid play (0-1 scale).
        """
        completion = 0.0

        trios = self._find_all_trios()
        sequences = self._find_all_sequences()

        # In round 2 only sequences (seguidillas) matter for going down
        if self.current_round == 2:
            completion += len(sequences) * 0.5
        elif self.current_round == 4:
            # Round 4: measure how many cards are part of the best partial play
            partial = self._find_best_partial_play()
            if partial:
                used = sum(len(p) for p in partial)
                completion = min(used / max(1, len(self.playerHand)), 1.0)
            else:
                completion += len(trios) * 0.15
                completion += len(sequences) * 0.15
        else:
            completion += len(trios) * 0.3
            completion += len(sequences) * 0.4

        return min(completion, 1.0)

    def _calculate_risk_factor(self, players_info):
        """
        Calculates risk factor based on opponent situations (0-1 scale).
        """
        if not players_info:
            return 0.0

        risk = 0.0

        for player_info in players_info:
            if player_info.get('hand_size', 0) <= 2:
                risk += 0.3

        return min(risk, 1.0)

    def _calculate_card_values(self):
        """
        Calculates strategic value of each card in hand.
        """
        card_values = {}

        for card in self.playerHand:
            value = 0.0

            matching_value = sum(1 for c in self.playerHand if c.value == card.value and c != card)
            matching_type = sum(1 for c in self.playerHand if c.type == card.type and c != card)

            # If target is round 2, increase weight for same-suit cards
            if self.current_round == 2:
                value += matching_type * 1.0
                value += matching_value * 0.1
            else:
                value += matching_value * 0.5
                value += matching_type * 0.3

            point_value = self._get_card_point_value(card)
            value += point_value / 20

            if card.joker:
                value += 2.0

            card_values[card] = value

        return card_values

    def _has_movable_joker(self, play):
        """
        Checks if a play contains a movable joker.
        """
        return any(c.joker for c in play)

    def _calculate_best_joker_position(self, play):
        """
        Calculates the best position for a joker in a sequence.
        """
        joker_pos = next((i for i, c in enumerate(play) if c.joker), None)

        if joker_pos is None:
            return None

        if joker_pos == 0 or joker_pos == len(play) - 1:
            other_pos = len(play) - 1 if joker_pos == 0 else 0
            return other_pos

        return None

    def _contains_joker(self, play):
        """
        Checks if a play contains any jokers.
        """
        return any(c.joker for c in play)

    def _find_substitutable_card(self, play):
        """
        Finds a card that can substitute a joker in a play.
        """
        for card in self.playerHand:
            if not card.joker and card not in play:
                if self._can_substitute_joker(card, play):
                    return card

        return None

    def _can_substitute_joker(self, card, play):
        """
        Checks if a card can substitute a joker in a play.
        """
        joker_positions = [i for i, c in enumerate(play) if c.joker]

        if not joker_positions:
            return False

        card_values = Card.values
        card_idx = card_values.index(card.value) if card.value in card_values else -1

        for pos in joker_positions:
            if pos == 0 or pos == len(play) - 1:
                return True

        return False

    def _find_joker_burn_pair(self):
        """
        Finds the best card to pair with a joker for burning.
        Returns both cards in the order expected by Player.discardCard.
        """
        jokers = [c for c in self.playerHand if c.joker]
        non_jokers = [c for c in self.playerHand if not c.joker]

        if not jokers or not non_jokers:
            return []

        card_values = self._calculate_card_values()
        worst_non_joker = min(non_jokers, key=lambda c: card_values.get(c, 0))

        return [jokers[0], worst_non_joker]

    def _get_card_point_value(self, card):
        """
        Returns the point value of a card according to game rules.
        """
        if card.joker:
            return 25
        elif card.value == 'A':
            return 15
        elif card.value in ['10', 'J', 'Q', 'K']:
            return 10
        else:
            return 5

    def learn_from_game(self, game_result):
        """
        Updates bot's learning patterns based on game result.
        game_result: dict with 'win', 'points_gained', 'plays_made', etc.
        """
        self.games_played += 1

        if game_result.get('win'):
            self.games_won += 1

        self.win_rate = self.games_won / self.games_played if self.games_played > 0 else 0.0

        self.game_history.append({
            'timestamp': datetime.now().isoformat(),
            'result': game_result,
            'win_rate': self.win_rate
        })

        if self.rl_enabled:
            self.rl_finalize_episode(game_result.get('win', False))

        self._update_strategy_weights(game_result)

    def _update_strategy_weights(self, game_result):
        """
        Updates strategy weights based on game performance.
        """
        if game_result.get('win'):
            self.strategy_weights['aggressive'] *= 1.05
            self.strategy_weights['balanced'] *= 1.02
        else:
            self.strategy_weights['conservative'] *= 1.03

        total = sum(self.strategy_weights.values())
        self.strategy_weights = {k: v/total for k, v in self.strategy_weights.items()}

    def save_model(self, filename='aibot_model.json'):
        """
        Saves bot's learned state to a file.
        """
        model_data = {
            'strategy_weights': self.strategy_weights,
            'learned_patterns': self.learned_patterns,
            'games_played': self.games_played,
            'games_won': self.games_won,
            'win_rate': self.win_rate,
            'game_history': self.game_history[-100:]
        }

        with open(filename, 'w') as f:
            json.dump(model_data, f, indent=2, default=str)

        if self.rl_enabled:
            rl_file = filename.replace('.json', '.pt')
            self.save_rl_model(rl_file)

    def load_model(self, filename='aibot_model.json'):
        """
        Loads bot's learned state from a file.
        """
        if not os.path.exists(filename):
            print(f"Model file {filename} not found. Starting with default weights.")
            return

        with open(filename, 'r') as f:
            model_data = json.load(f)

        self.strategy_weights = model_data.get('strategy_weights', self.strategy_weights)
        self.learned_patterns = model_data.get('learned_patterns', self.learned_patterns)
        self.games_played = model_data.get('games_played', 0)
        self.games_won = model_data.get('games_won', 0)
        self.win_rate = model_data.get('win_rate', 0.0)

        if self.rl_enabled:
            rl_file = filename.replace('.json', '.pt')
            self.initialize_rl(self.rl_state_dim or 47, self.rl_action_dim or 2, model_file=rl_file)
            if os.path.exists(rl_file):
                self.load_rl_model(rl_file)

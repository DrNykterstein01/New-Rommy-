from Round import Round
from Turn import drawCard, discardCard, refillDeck
from Card import Card
import random


class RummyEnv:
    # Action index is reused across phases.
    # phase 0 (draw): 0=discard, 1=deck, 2=deck fallback
    # phase 1 (play/down): 0=attempt bajar, 1=pass, 2=pass
    # phase 2 (discard): 0=low discard, 1=high discard, 2=burn joker if possible
    # Expanded action space: base 3 actions + encoded insertion actions
    # Base actions (0-2) kept for backward compatibility.
    # Insertion actions are encoded as: 3 + (play_idx * MAX_HAND_SLOTS * POS_COUNT) + (hand_slot * POS_COUNT) + pos
    # where pos: 0=start, 1=end
    MAX_TABLE_PLAYS = 8
    MAX_HAND_SLOTS = 13
    POS_COUNT = 2
    ACTION_SPACE = 3 + (MAX_TABLE_PLAYS * MAX_HAND_SLOTS * POS_COUNT)
    PHASE_DRAW = 0
    PHASE_PLAY = 1
    PHASE_DISCARD = 2

    def __init__(self, players, round_number=1, max_turns=200, target_points=500):
        self.players = players
        self.round_number = round_number
        self.max_turns = max_turns
        self.target_points = target_points
        self.round = None
        self.current_player_index = 0
        self.turn_phase = 0
        self.done = False
        self.turn_count = 0

    def reset(self):
        self.round = Round(self.players)
        for player in self.players:
            player.playerPoints = 0
            player.playerHand = []
            player.downHand = False
            player.isHand = False
            player.winner = False
            player.isSpectator = False
            player.cardDrawn = False
            player.canDiscard = True
            player.playerBuy = False
            player.playerPass = False
            player.playMade = []
            player.jugadas_bajadas = []
            player.current_round = self.round_number

        self.round.initDeck()
        self.round.dealCards()
        self.round.discardsAndTableDeck()
        self.current_player_index = 0
        self.turn_phase = 0
        self.done = False
        self.turn_count = 0

        return self._build_observation()

    def step(self, action):
        if self.done:
            return None, 0.0, True, {}

        player = self._current_player()
        if not getattr(player, 'rl_enabled', False):
            raise ValueError('RummyEnv.step() must be called when the current player is the RL agent.')

        reward = 0.0
        if self.turn_phase == 0:
            reward += self._apply_draw(player, action)
            self.turn_phase = 1
            next_state = self._build_observation()
            return next_state, reward, self.done, {'phase': 0}

        if self.turn_phase == 1:
            reward += self._apply_play(player, action)
            if len(player.playerHand) == 0:
                player.winner = True
                round_done = self._handle_round_completion(player)
                if self.done:
                    reward += 1.0
                    return self._build_observation(), reward, True, {'phase': 1, 'win': True}
                if round_done:
                    return self._build_observation(), reward + 0.5, False, {'phase': 1, 'round_end': True, 'round_winner': player.playerName, 'new_round': self.round_number}
            self.turn_phase = 2
            next_state = self._build_observation()
            return next_state, reward, self.done, {'phase': 1}

        if self.turn_phase == 2:
            reward += self._apply_discard(player, action)
            self.turn_count += 1
            if len(player.playerHand) == 0:
                player.winner = True
                round_done = self._handle_round_completion(player)
                if self.done:
                    reward += 1.0
                    return self._build_observation(), reward, True, {'phase': 2, 'win': True}
                if round_done:
                    return self._build_observation(), reward + 0.5, False, {'phase': 2, 'round_end': True, 'round_winner': player.playerName, 'new_round': self.round_number + 1 if self.round_number < 4 else 1}

            if self.turn_count >= self.max_turns:
                self.done = True
                return self._build_observation(), reward - 1.0, True, {'phase': 2, 'win': False}

            self._advance_player()
            self._simulate_until_rl_turn()
            next_state = self._build_observation()
            return next_state, reward, self.done, {'phase': 2, 'win': False}

    def _current_player(self):
        return self.players[self.current_player_index]

    def _build_observation(self):
        player = self._current_player()
        players_info = [{'hand_size': len(p.playerHand)} for p in self.players]
        discard_top = self.round.discards[-1] if self.round.discards else None
        return player.encode_state(discard_top, len(self.round.pile), players_info, self.round_number, self.turn_phase)

    def _apply_draw(self, player, action):
        discard_top = self.round.discards[-1] if self.round.discards else None
        if action == 0:
            if discard_top:
                drawCard(player, self.round, fromDiscards=True)
                player.playerHand = self.round.hands[player.playerId]
                player.cardDrawn = True
                print(f"[TURN] Ronda {self.round_number} | \n Jugador {player.playerName} tomó DEL DESCARTE: {discard_top}")
                print(f"[HAND] Mano de {player.playerName} tras tomar: {[str(c) for c in player.playerHand]}")
                return 0.15
            if len(self.round.pile) == 0:
                refillDeck(self.round)
            drawCard(player, self.round)
            player.playerHand = self.round.hands[player.playerId]
            player.cardDrawn = True
            print(f"[TURN] Ronda {self.round_number} | \n Jugador {player.playerName} tomó DEL MAZO")
            print(f"[HAND] Mano de {player.playerName} tras tomar: {[str(c) for c in player.playerHand]}")
            return -0.05

        if len(self.round.pile) == 0:
            refillDeck(self.round)

        self._offer_buy_cycle(player)
        drawCard(player, self.round)
        player.playerHand = self.round.hands[player.playerId]
        player.cardDrawn = True
        print(f"[TURN] Ronda {self.round_number} | \n Jugador {player.playerName} tomó DEL MAZO (fallback)")
        print(f"[HAND] Mano de {player.playerName} tras tomar: {[str(c) for c in player.playerHand]}")
        return 0.0

    def _offer_buy_cycle(self, current_player):
        discard_top = self.round.discards[-1] if self.round.discards else None
        if discard_top is None:
            return False

        num_players = len(self.players)
        for i in range(1, num_players):
            buyer = self.players[(self.current_player_index + i) % num_players]
            if buyer.isSpectator:
                continue
            buyer.playerBuy = buyer.decide_buy_card(discard_top, buyer.calculatePointsAI(), self.players)
            if buyer.playerBuy:
                buyer.buyCard(self.round)
                buyer.playerBuy = False
                return True

        return False

    def _apply_play(self, player, action):
        if not player.cardDrawn:
            return -0.3

        if player.downHand and action >= 3:
            table = self._collect_table_plays()
            base = 3
            rel = action - base
            per_play = self.MAX_HAND_SLOTS * self.POS_COUNT
            play_idx_rel = rel // per_play
            rem = rel % per_play
            hand_slot = rem // self.POS_COUNT
            pos_idx = rem % self.POS_COUNT

            if play_idx_rel < 0 or play_idx_rel >= len(table):
                return -0.2

            target = table[play_idx_rel]
            target_player = target['owner']
            target_index = target['play_index']

            if hand_slot < 0 or hand_slot >= len(player.playerHand):
                return -0.2
            card_to_insert = player.playerHand[hand_slot]
            position = 'start' if pos_idx == 0 else 'end'

            succeeded = player.insertCard(target_player, target_index, card_to_insert, position)
            if succeeded:
                print(f"[INSERT] Jugador {player.playerName} insertó {card_to_insert} en la jugada de {target_player.playerName} (idx {target_index}) en ronda {self.round_number}")
                if len(player.playerHand) == 0:
                    player.winner = True
                    round_done = self._handle_round_completion(player)
                    return 0.5 if round_done else 0.1
                return 0.1
            return -0.2

        if action == 0:
            if player.downHand:
                table = self._collect_table_plays()
                insertion = player.decide_insert_card([p['play'] for p in table])
                if not insertion:
                    return 0.0

                play_idx_rel, card_to_insert, position = insertion
                if play_idx_rel < 0 or play_idx_rel >= len(table):
                    return -0.2

                target = table[play_idx_rel]
                target_player = target['owner']
                target_index = target['play_index']

                succeeded = player.insertCard(target_player, target_index, card_to_insert, position)
                if succeeded:
                    print(f"[INSERT] Jugador {player.playerName} insertó {card_to_insert} en la jugada de {target_player.playerName} (idx {target_index}) en ronda {self.round_number}")
                    if len(player.playerHand) == 0:
                        player.winner = True
                        round_done = self._handle_round_completion(player)
                        return 0.5 if round_done else 0.1
                    return 0.1
                return -0.2

            play = player.decide_play_cards(self.round_number)
            if not play:
                return -0.4

            if not self._is_valid_down_play(player, play):
                return -0.4

            if self._execute_play(player, play):
                reward = 0.35
                if player.downHand:
                    reward += 0.25
                reward += 0.05 * (len(play) - 1)
                return reward

            return -0.3

        # Passing is valid, but if a valid bajar play exists then it should be penalized.
        if player.decide_play_cards(self.round_number):
            return -0.15
        return 0.0

        return 0.0

    def _execute_play(self, player, play):
        if not play:
            return False

        cards = []
        if isinstance(play, tuple):
            for segment in play:
                cards.extend(segment)
        elif isinstance(play, list):
            cards.extend(play)
        else:
            return False

        if any(card not in player.playerHand for card in cards):
            return False

        for card in cards:
            if card in player.playerHand:
                player.playerHand.remove(card)
            if card in self.round.hands.get(player.playerId, []):
                self.round.hands[player.playerId].remove(card)

        if isinstance(play, tuple):
            for segment in play:
                player.playMade.append(list(segment))
        else:
            player.playMade.append(play)
        player.downHand = True

        formatted_play = []
        if isinstance(play, tuple):
            formatted_play = [[str(c) for c in segment] for segment in play]
        else:
            formatted_play = [[str(c) for c in play]]

        print(f"[SE BAJOOOOOOOOOOOOOOOOOOOOOO] Jugador {player.playerName} se bajó en ronda {self.round_number} con: {formatted_play}")
        return True

    def _is_valid_down_play(self, player, play):
        if not play:
            return False

        if self.round_number == 1:
            if not isinstance(play, tuple) or len(play) != 2:
                return False
            trio, straight = play
            valid_trio = player.isValidTrioF(trio)
            valid_straight = player.isValidStraightF(straight) or player.isValidStraightFJoker(straight)
            return valid_trio and valid_straight

        if self.round_number == 2:
            if not isinstance(play, tuple) or len(play) != 2:
                return False
            straight1, straight2 = play
            valid1 = player.isValidStraightF(straight1) or player.isValidStraightFJoker(straight1)
            valid2 = player.isValidStraightF(straight2) or player.isValidStraightFJoker(straight2)
            return valid1 and valid2 and not self._plays_share_cards(straight1, straight2)

        if self.round_number == 3:
            if not isinstance(play, tuple) or len(play) != 3:
                return False
            trio1, trio2, trio3 = play
            if not (player.isValidTrioF(trio1) and player.isValidTrioF(trio2) and player.isValidTrioF(trio3)):
                return False
            values = [next((c.value for c in trio if not getattr(c, 'joker', False)), None) for trio in (trio1, trio2, trio3)]
            values = [v for v in values if v is not None]
            return len(values) == 3 and len(set(values)) == 3

        if self.round_number == 4:
            if not isinstance(play, tuple) or len(play) != 3:
                return False
            trio1, trio2, straight = play
            if not (player.isValidTrioF(trio1) and player.isValidTrioF(trio2)):
                return False
            valid_straight = player.isValidStraightF(straight) or player.isValidStraightFJoker(straight)
            if not valid_straight:
                return False
            total_cards = len(trio1) + len(trio2) + len(straight)
            return total_cards == len(player.playerHand)

        return False

    def _plays_share_cards(self, play1, play2):
        return bool(set(play1) & set(play2))

    def _apply_discard(self, player, action):
        if not player.cardDrawn:
            return -0.2

        if action == 0:
            card = self._choose_lowest_discard(player)
            base_reward = -0.02
        elif action == 1:
            card = self._choose_highest_discard(player)
            base_reward = 0.0
        elif action == 2:
            if player.downHand:
                joker_card = self._choose_lowest_discard(player, include_only_jokers=True)
                if joker_card:
                    pair_card = self._choose_lowest_discard(player, exclude_jokers=True)
                    if pair_card:
                        self._discard_cards(player, [joker_card, pair_card])
                        return 0.10
                card = self._choose_lowest_discard(player)
                base_reward = -0.05
            else:
                card = self._choose_lowest_discard(player)
                base_reward = -0.2
        else:
            card = self._choose_lowest_discard(player)
            base_reward = -0.05

        if card is None:
            return -0.2

        if getattr(card, 'joker', False) and not player.downHand:
            card = self._choose_lowest_discard(player, exclude_jokers=True)
            if card is None:
                return -0.2

        if getattr(card, 'joker', False) and player.downHand:
            pair_card = self._choose_lowest_discard(player, exclude_jokers=True)
            if pair_card:
                self._discard_cards(player, [card, pair_card])
                return 0.10

        self._discard_cards(player, [card])
        return base_reward - 0.01 * len(player.playerHand)

    def _choose_lowest_discard(self, player, exclude_jokers=False, include_only_jokers=False):
        if include_only_jokers:
            candidates = [c for c in player.playerHand if c.joker]
        else:
            candidates = [c for c in player.playerHand if not exclude_jokers or not c.joker]
        if not candidates:
            return None
        return min(candidates, key=self._card_value_for_discard)

    def _choose_highest_discard(self, player):
        candidates = [c for c in player.playerHand if not c.joker]
        if not candidates:
            candidates = player.playerHand[:]
        if not candidates:
            return None
        return max(candidates, key=self._card_value_for_discard)

    def _card_value_for_discard(self, card):
        if card.joker:
            return 100
        if card.value == 'A':
            return 14
        if card.value == 'K':
            return 13
        if card.value == 'Q':
            return 12
        if card.value == 'J':
            return 11
        return int(card.value)

    def _discard_cards(self, player, cards):
        for card in cards:
            if card in player.playerHand:
                player.playerHand.remove(card)
            if card in self.round.hands.get(player.playerId, []):
                self.round.hands[player.playerId].remove(card)
            if card not in self.round.discards:
                card.discarded_by = player.playerId
                self.round.discards.append(card)
        player.cardDrawn = False
        player.isHand = False
        print(f"[DISCARD] Jugador {player.playerName} descartó: {[str(c) for c in cards]} | Mano ahora: {[str(c) for c in player.playerHand]}")

    def _is_match_over(self):
        active_players = [p for p in self.players if not p.isSpectator]
        return len(active_players) <= 1

    def _find_first_active_player_index(self):
        for idx, player in enumerate(self.players):
            if not player.isSpectator:
                return idx
        return 0

    def _prepare_new_round(self):
        for player in self.players:
            if player.isSpectator:
                continue
            player.playerHand = []
            player.downHand = False
            player.isHand = False
            player.cardDrawn = False
            player.canDiscard = True
            player.playerBuy = False
            player.playerPass = False
            player.playMade = []
            player.jugadas_bajadas = []
            player.current_round = self.round_number

        self.round = Round(self.players)
        self.round.initDeck()
        self.round.dealCards()
        self.round.discardsAndTableDeck()
        self.current_player_index = self._find_first_active_player_index()
        self.turn_phase = 0
        self.turn_count = 0

    def _handle_round_completion(self, winner):
        if winner is None:
            return False
        print(f"[ROUND END] Ganador de ronda: {winner.playerName}")
        eliminated = []
        for player in self.players:
            if player is winner or player.isSpectator:
                continue
            pts = player.calculatePoints()
            print(f"[SCORES] Jugador {player.playerName} sumó {pts} puntos -> Total: {player.playerPoints}")
            if player.playerPoints >= self.target_points:
                eliminated.append(player)

        if eliminated:
            for p in eliminated:
                p.isSpectator = True
                print(f"[ELIMINATED] Jugador {p.playerName} eliminado con {p.playerPoints} puntos")
        else:
            print("[ELIMINATION] No se eliminó a ningún jugador en esta ronda")

        if self._is_match_over():
            self.done = True
            return True

        # advance to next round number and prepare tables
        self.round_number = 1 if self.round_number == 4 else self.round_number + 1
        print(f"[NEXT ROUND] Iniciando ronda {self.round_number}...")
        self._prepare_new_round()
        return True

    def _advance_player(self):
        num_players = len(self.players)
        for _ in range(num_players):
            self.current_player_index = (self.current_player_index + 1) % num_players
            if not self.players[self.current_player_index].isSpectator:
                break
        else:
            self.done = True
        self.turn_phase = 0

    def _simulate_until_rl_turn(self):
        while not self.done and not getattr(self._current_player(), 'rl_enabled', False):
            player = self._current_player()
            self._simulate_heuristic_turn(player)
            if len(player.playerHand) == 0:
                round_done = self._handle_round_completion(player)
                if self.done:
                    return
                if round_done:
                    continue
            self._advance_player()

    def _collect_table_plays(self):
        """Return a flat list of plays on table with metadata: {'owner': player, 'play_index': idx, 'play': play}"""
        table = []
        for owner in self.players:
            for idx, play in enumerate(owner.playMade):
                table.append({'owner': owner, 'play_index': idx, 'play': play})
        return table

    def _simulate_heuristic_turn(self, player):
        if player.isSpectator:
            return

        # Turn header for debugging
        discard_top = self.round.discards[-1] if self.round.discards else None
        print(f"\n[TURN] Ronda {self.round_number} | Jugador en turno: {player.playerName} | Tope descarte: {discard_top}")

        player.current_round = self.round_number
        discard_top = self.round.discards[-1] if self.round.discards else None
        draw_from_discard = player.decide_draw_source(discard_top, len(self.round.pile), [{'hand_size': len(p.playerHand)} for p in self.players])
        if draw_from_discard and discard_top:
            drawCard(player, self.round, fromDiscards=True)
            player.playerHand = self.round.hands[player.playerId]
            player.cardDrawn = True
            print(f"[TURN] {player.playerName} tomó DEL DESCARTE: {discard_top}")
            print(f"[HAND] Mano de {player.playerName} tras tomar: {[str(c) for c in player.playerHand]}")
        else:
            if len(self.round.pile) == 0:
                refillDeck(self.round)
            self._offer_buy_cycle(player)
            drawCard(player, self.round)
            player.playerHand = self.round.hands[player.playerId]
            player.cardDrawn = True
            print(f"[TURN] {player.playerName} tomó DEL MAZO")
            print(f"[HAND] Mano de {player.playerName} tras tomar: {[str(c) for c in player.playerHand]}")

        # Play phase: if already bajado, try insertion; otherwise try bajar
        if player.downHand:
            table = self._collect_table_plays()
            insertion = player.decide_insert_card([p['play'] for p in table])
            if insertion:
                idx_rel, card, pos = insertion
                if 0 <= idx_rel < len(table):
                    target = table[idx_rel]
                    targ_player = target['owner']
                    targ_index = target['play_index']
                    ok = player.insertCard(targ_player, targ_index, card, pos)
                    if ok:
                        print(f"[INSERT] Jugador {player.playerName} insertó {card} en la jugada de {targ_player.playerName}")
        else:
            play = player.decide_play_cards(self.round_number)
            if play and not player.downHand:
                self._execute_play(player, play)

        discard_choice = player.decide_discard()
        if discard_choice:
            if isinstance(discard_choice, list):
                self._discard_cards(player, discard_choice)
            else:
                self._discard_cards(player, [discard_choice])

        if len(player.playerHand) == 0:
            player.winner = True

    def render(self):
        return {
            'current_player': self._current_player().playerName,
            'hand_size': len(self._current_player().playerHand),
            'discard_top': str(self.round.discards[-1]) if self.round.discards else None,
            'pile_size': len(self.round.pile),
            'phase': self.turn_phase
        }

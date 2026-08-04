import random
from Turn import refillDeck, drawCard
def electionPhase(players, deck):
    print("Fase de Elección")
    active_players = [p for p in players if not p.isSpectator]
    if not active_players:
        return players # Casos raros donde todos sean espectadores

    availableCards = deck.drawInElectionPhase(len(active_players))  #Sacamos las Cartas para la fase de elección
    random.shuffle(availableCards)  #Mezclamos las Cartas que se van a elegir para que no estén en el mismo orden

    elections = {}  #Creamos un diccionario para almacenar las elecciones de los jugadores antes de la ronda
    for player, Card in zip(active_players, availableCards):
        elections[player] = Card  #Asignamos la Carta elegida a cada jugador
        print(f"{player} ha elegido la Carta: {Card}") #Indicamos qué Carta fue elegida

    #Con lo siguiente, se determinará el turno de la ronda para los jugadores dependiendo del valor numérico de la Carta que eligió cada uno
    order = sorted(
        elections.items(),
        key = lambda item: Card.values.index(item[1].value),
        reverse = True
    )
    playerOrder = [player for player, _ in order]  #Obtenemos el orden de los jugadores según sus elecciones
    
    # Agregar los espectadores al final de la lista para mantenerlos en el juego (aunque no jueguen)
    spectators = [p for p in players if p.isSpectator]
    playerOrder.extend(spectators)

    print("Orden de los jugadores:", playerOrder)
    return playerOrder
    #Devolvemos el orden de los jugadores para la ronda


def startRound(playersInOrder, screen): # Incluimos el atributo "screen" para la interfaz gráfica
    from Round import Round  #Importamos la clase Round aquí para evitar importaciones circulares
    roundInstance = Round(playersInOrder)  #Creamos una instancia de la clase Round
    roundInstance.initDeck()  #Inicializamos el mazo
    roundInstance.dealCards()  #Repartimos las cartas a los jugadores
    roundInstance.discardsAndTableDeck()  #Colocamos la primera carta en el montón de descartes
    roundInstance.showInitialState()  #Mostramos el estado inicial de la ronda

    return roundInstance, playersInOrder  #Devolvemos la instancia de la ronda y el orden de los jugadores

def mainGameLoop(screen, playersInOrder):
    """
    Lógica principal del juego:
      - Gestiona turnos.
      - Ofrece la carta del descarte a otros jugadores.
      - Controla compra, bajada, inserción y descarte.
    """
    #PRIMERO SE DECIDEN LOS TURNOS AL INICIAR LA RONDA. ES ALEATORIO DEBIDO A QUE YA NO HAY FASE DE ELECCIÓN.
    #EL PRIMER JUGADOR EN TURNO DEBE TOMAR UNA CARTA, YA SEA DEL MAZO O DEL DESCARTE. SI ELIGE TOMAR DEL DESCARTE,
    #NORMAL, AHÍ NO HAY PROBLEMA. PERO SI ELIGE TOMAR DEL MAZO, LOS DEMÁS JUGADORES DEBEN DECIDIR SI QUIEREN COMPRAR ESA CARTA O NO. 
    #SI ALGUNO DECIDE COMPRARLA, SE LA LLEVA Y EL JUGADOR EN TURNO TOMA LA CARTA DEL MAZO NORMALMENTE, EN UN PLAZO DE 7 SEGUNDOS. 
    #SI NINGUNO DECIDE COMPRARLA EN ESE TIEMPO, SIMPLEMENTE EL JUGADOR EN TURNO TOMA DEL MAZO Y SIGUE CON SU TURNO NORMAL.
    #UNA VEZ AHÍ, EL JUGADOR EN TURNO DEBE DECIDIR SI BAJARSE O NO, EN CASO DE TENER LA OPORTUNIDAD DE HACERLO.
    #SI ELIGE BAJARSE, COLOCARÁ LAS CARTAS SOBRE LA MESA. INDEPENDIENTEMENTE DE SI LO HACE O NO, DEBE
    #DESCARTAR UNA CARTA DESPUÉS.
    #A CONTINUACIÓN, SE LE PASA EL TURNO AL SIGUIENTE JUGADOR EN EL ORDEN DEL ARRAY, Y ASÍ SE SIGUE EL JUEGO
    #HASTA QUE ALGUIEN SE QUEDE SIN CARTAS. ES AHÍ DONDE TERMINA LA RONDA.
    roundObject = startRound(playersInOrder, screen)[0]
    currentRound = 1
    # Orden de jugadores fijo
    turn_order = playersInOrder[:]
    for p in turn_order:
        p.isHand = False
    #Aquí debería de leerse el orden de los jugadores según la fase de elección
    #turn_order.sort(key=lambda p: 0 if p.name == "Louis" else 1)
    discard_pile = roundObject.discards
    deck = roundObject.pile
    current_index = 0
    game_running = True
    plays_in_table = []  # Para almacenar las jugadas en la mesa, si es necesario para la IA

    # Estado inicial
    state = {
        "players": [],
        "deck_remaining": len(deck),
        "discard_top": discard_pile[-1] if discard_pile else None,
        "turn_order": [p.playerName for p in turn_order],
    }

    while game_running:
        players_info = [{'hand_size': len(p.playerHand)} for p in playersInOrder]
        current_player = turn_order[current_index]
        current_player.isHand = True
        current_player.cardDrawn = False
        current_player.drawn_from_discard_card = None
        print(f"\n-----------------TURNO DE {current_player.playerName}-------------------------")
        print(f"CARTAS DE {current_player.playerName}: {[str(c) for c in current_player.playerHand]}")
        print(f"CARTA DEL TOPE DEL DESCARTE: {roundObject.discards[-1] if roundObject.discards else None}")
        print(f"CARTAS RESTANTES EN PILE: {len(deck)}")
        print(f"SE ESTÁ JUGANDO LA RONDA NÚMERO {currentRound}")
        # Check if current player is AI
        if len(deck) == 0:
            refillDeck(roundObject)
            deck = roundObject.pile
        if hasattr(current_player, 'is_ai') and current_player.is_ai:
            # provide current round context to the AI so it can adapt strategy
            try:
                current_player.current_round = currentRound
            except Exception:
                pass

            initial_state = None
            if hasattr(current_player, 'rl_enabled') and current_player.rl_enabled:
                initial_state = current_player.encode_state(
                    discard_pile[-1] if discard_pile else None,
                    len(deck),
                    players_info,
                    currentRound
                )

            should_draw_discard = current_player.decide_draw_source(
                discard_pile[-1] if discard_pile else None,
                len(deck),
                players_info
            )
            #TENGO QUE SEGUIR ANALIZANDO LAS VALIDACIONES DE CADA PROCESO, PARA PODER
            #PROBAR DESPUÉS EL ENTRENAMIENTO DE LA IA Y VERIFICAR SI TODO VA EN ORDEN.
            #DE SER EL CASO, PASARÍA A IMPLEMENTARLO EN UI2
            if should_draw_discard and discard_pile:
                if not current_player.cardDrawn:
                    # Draw from discard
                    current_player.drawn_from_discard_card = drawCard(
                        current_player,
                        roundObject,
                        fromDiscards=True
                    )
                    current_player.playerHand = roundObject.hands[current_player.playerId]
                    print(f"EL JUGADOR {current_player.playerName} TOMÓ EL DESCARTEEEEE")
                    print(f"MANO DE ESE JUGADOR DESPUÉS DE TOMAR EL DESCARTE: {[str(c) for c in current_player.playerHand]}")
                    current_player.cardDrawn = True
                else:
                    print(f"EL JUGADOR {current_player.playerName} YA TOMÓ UNA CARTA ANTERIORMENTE")
            else:
                if not current_player.cardDrawn:
                    otherPlayers = [p for p in playersInOrder if p != current_player]
                    # Draw from deck
                    for i in range(len(otherPlayers)):
                        # give round context to other AIs evaluating buying
                        try:
                            otherPlayers[i].current_round = currentRound
                        except Exception:
                            pass
                        buyDecision = None
                        if len(roundObject.discards) > 0:
                            buyDecision = otherPlayers[i].decide_buy_card(roundObject.discards[-1], otherPlayers[i].calculatePointsAI(), playersInOrder)
                        if buyDecision:
                            current_player.canDiscard = False
                            if i == 0:

                                otherPlayers[i].buyCard(roundObject)
                                break
                            elif i == 1:
                                decision = otherPlayers[i-1].decide_buy_card(roundObject.discards[-1], otherPlayers[i-1].calculatePointsAI(), playersInOrder)
                                if decision:
                                    
                                    otherPlayers[i-1].buyCard(roundObject)
                                    break
                                else:
                                    
                                    otherPlayers[i].buyCard(roundObject)
                                    break
                            elif i == 2:
                                decision = otherPlayers[i-2].decide_buy_card(roundObject.discards[-1], otherPlayers[i-2].calculatePointsAI(), playersInOrder)
                                if decision:
                                    
                                    otherPlayers[i-2].buyCard(roundObject)
                                    break
                                else:
                                    decision2 = otherPlayers[i-1].decide_buy_card(roundObject.discards[-1], otherPlayers[i-1].calculatePointsAI(), playersInOrder)
                                    if decision2:
                                        
                                        otherPlayers[i-1].buyCard(roundObject)
                                        break
                                    else:
                                        
                                        otherPlayers[i].buyCard(roundObject)
                                        break
                            elif i == 3:
                                decision = otherPlayers[i-3].decide_buy_card(roundObject.discards[-1], otherPlayers[i-3].calculatePointsAI(), playersInOrder)
                                if decision:
                                    
                                    otherPlayers[i-3].buyCard(roundObject)
                                    break
                                else:
                                    decision2 = otherPlayers[i-2].decide_buy_card(roundObject.discards[-1], otherPlayers[i-2].calculatePointsAI(), playersInOrder)
                                    if decision2:
                                        
                                        otherPlayers[i-2].buyCard(roundObject)
                                        break
                                    else:
                                        decision3 = otherPlayers[i-1].decide_buy_card(roundObject.discards[-1], otherPlayers[i-1].calculatePointsAI(), playersInOrder)
                                        if decision3:
                                            
                                            otherPlayers[i-1].buyCard(roundObject)
                                            break
                                        else:
                                            
                                            otherPlayers[i].buyCard(roundObject)
                                            break
                            elif i == 4:
                                decision = otherPlayers[i-4].decide_buy_card(roundObject.discards[-1], otherPlayers[i-4].calculatePointsAI(), playersInOrder)
                                if decision:
                                    
                                    otherPlayers[i-4].buyCard(roundObject)
                                    break
                                else:
                                    decision2 = otherPlayers[i-3].decide_buy_card(roundObject.discards[-1], otherPlayers[i-3].calculatePointsAI(), playersInOrder)
                                    if decision2:
                                        
                                        otherPlayers[i-3].buyCard(roundObject)
                                        break
                                    else:
                                        decision3 = otherPlayers[i-2].decide_buy_card(roundObject.discards[-1], otherPlayers[i-2].calculatePointsAI(), playersInOrder)
                                        if decision3:
                                            
                                            otherPlayers[i-2].buyCard(roundObject)
                                            break
                                        else:
                                            decision4 = otherPlayers[i-1].decide_buy_card(roundObject.discards[-1], otherPlayers[i-1].calculatePointsAI(), playersInOrder)
                                            if decision4:
                                                
                                                otherPlayers[i-1].buyCard(roundObject)
                                                break
                                            else:
                                                
                                                otherPlayers[i].buyCard(roundObject)
                                                break
                            elif i == 5:
                                decision = otherPlayers[i-5].decide_buy_card(roundObject.discards[-1], otherPlayers[i-5].calculatePointsAI(), playersInOrder)
                                if decision:
                                    
                                    otherPlayers[i-5].buyCard(roundObject)
                                    break
                                else:
                                    decision2 = otherPlayers[i-4].decide_buy_card(roundObject.discards[-1], otherPlayers[i-4].calculatePointsAI(), playersInOrder)
                                    if decision2:
                                        
                                        otherPlayers[i-4].buyCard(roundObject)
                                        break
                                    else:
                                        decision3 = otherPlayers[i-3].decide_buy_card(roundObject.discards[-1], otherPlayers[i-3].calculatePointsAI(), playersInOrder)
                                        if decision3:
                                            
                                            otherPlayers[i-3].buyCard(roundObject)
                                            break
                                        else:
                                            decision4 = otherPlayers[i-2].decide_buy_card(roundObject.discards[-1], otherPlayers[i-2].calculatePointsAI(), playersInOrder)
                                            if decision4:
                                                
                                                otherPlayers[i-2].buyCard(roundObject)
                                                break
                                            else:
                                                decision5 = otherPlayers[i-1].decide_buy_card(roundObject.discards[-1], otherPlayers[i-1].calculatePointsAI(), playersInOrder)
                                                if decision5:
                                                    
                                                    otherPlayers[i-1].buyCard(roundObject)
                                                    break
                                                else:
                                                    
                                                    otherPlayers[i].buyCard(roundObject)
                                                    break
                            elif i == 6:
                                decision = otherPlayers[i-6].decide_buy_card(roundObject.discards[-1], otherPlayers[i-6].calculatePointsAI(), playersInOrder)
                                if decision:
                                    
                                    otherPlayers[i-6].buyCard(roundObject)
                                    break
                                else:
                                    decision2 = otherPlayers[i-5].decide_buy_card(roundObject.discards[-1], otherPlayers[i-5].calculatePointsAI(), playersInOrder)
                                    if decision2:
                                        
                                        otherPlayers[i-5].buyCard(roundObject)
                                        break
                                    else:
                                        decision3 = otherPlayers[i-4].decide_buy_card(roundObject.discards[-1], otherPlayers[i-4].calculatePointsAI(), playersInOrder)
                                        if decision3:
                                            
                                            otherPlayers[i-4].buyCard(roundObject)
                                            break
                                        else:
                                            decision4 = otherPlayers[i-3].decide_buy_card(roundObject.discards[-1], otherPlayers[i-3].calculatePointsAI(), playersInOrder)
                                            if decision4:
                                                
                                                otherPlayers[i-3].buyCard(roundObject)
                                                break
                                            else:
                                                decision5 = otherPlayers[i-2].decide_buy_card(roundObject.discards[-1], otherPlayers[i-2].calculatePointsAI(), playersInOrder)
                                                if decision5:
                                                    
                                                    otherPlayers[i-2].buyCard(roundObject)
                                                    break
                                                else:
                                                    decision6 = otherPlayers[i-1].decide_buy_card(roundObject.discards[-1], otherPlayers[i-1].calculatePointsAI(), playersInOrder)
                                                    if decision6:
                                                        
                                                        otherPlayers[i-1].buyCard(roundObject)
                                                        break
                                                    else:
                                                        
                                                        otherPlayers[i].buyCard(roundObject)
                                                        break
                            elif i == 7:
                                decision = otherPlayers[i-7].decide_buy_card(roundObject.discards[-1], otherPlayers[i-7].calculatePointsAI(), playersInOrder)
                                if decision:
                                    
                                    otherPlayers[i-7].buyCard(roundObject)
                                    break
                                else:
                                    decision2 = otherPlayers[i-6].decide_buy_card(roundObject.discards[-1], otherPlayers[i-6].calculatePointsAI(), playersInOrder)
                                    if decision2:
                                        
                                        otherPlayers[i-6].buyCard(roundObject)
                                        break
                                    else:
                                        decision3 = otherPlayers[i-5].decide_buy_card(roundObject.discards[-1], otherPlayers[i-5].calculatePointsAI(), playersInOrder)
                                        if decision3:
                                            
                                            otherPlayers[i-5].buyCard(roundObject)
                                            break
                                        else:
                                            decision4 = otherPlayers[i-4].decide_buy_card(roundObject.discards[-1], otherPlayers[i-4].calculatePointsAI(), playersInOrder)
                                            if decision4:
                                                
                                                otherPlayers[i-4].buyCard(roundObject)
                                                break
                                            else:
                                                decision5 = otherPlayers[i-3].decide_buy_card(roundObject.discards[-1], otherPlayers[i-3].calculatePointsAI(), playersInOrder)
                                                if decision5:
                                                    
                                                    otherPlayers[i-3].buyCard(roundObject)
                                                    break
                                                else:
                                                    decision6 = otherPlayers[i-2].decide_buy_card(roundObject.discards[-1], otherPlayers[i-2].calculatePointsAI(), playersInOrder)
                                                    if decision6:
                                                        
                                                        otherPlayers[i-2].buyCard(roundObject)
                                                        break
                                                    else:
                                                        decision7 = otherPlayers[i-1].decide_buy_card(roundObject.discards[-1], otherPlayers[i-1].calculatePointsAI(), playersInOrder)
                                                        if decision7:
                                                            
                                                            otherPlayers[i-1].buyCard(roundObject)
                                                            break
                                                        else:
                                                            
                                                            otherPlayers[i].buyCard(roundObject)
                                                            break
                        else:
                            print("NINGÚN JUGADOR COMPRÓ LA CARTA DEL DESCARTE")
                    if len(deck) == 0:
                        refillDeck(roundObject)
                        deck = roundObject.pile
                    drawCard(current_player, roundObject)
                    current_player.drawn_from_discard_card = None
                    print(f"EL JUGADOR {current_player.playerName} TOMÓ DEL MAZO NORMAAAAAAL")
                    current_player.playerHand = roundObject.hands[current_player.playerId]
                    print(f"MANO DE ESE JUGADOR DESPUÉS DE TOMAR UNA CARTA: {[str(c) for c in current_player.playerHand]}")
                    current_player.cardDrawn = True
                    current_player.canDiscard = True
                else:
                    print(f"EL JUGADOR {current_player.playerName} YA TOMÓ UNA CARTA ANTERIORMENTE")

            if initial_state is not None and hasattr(current_player, 'rl_enabled') and current_player.rl_enabled:
                next_state = current_player.encode_state(
                    discard_pile[-1] if discard_pile else None,
                    len(deck),
                    players_info,
                    currentRound
                )
                current_player.rl_record_draw_transition(next_state)
                                

            # Playing phase
            play = current_player.decide_play_cards(currentRound)
            if play and not current_player.downHand:
                # Execute the play on the board
                if not current_player.cardDrawn:
                # Si el jugador no ha tomado una carta, no puede jugar
                    print(f"{current_player.playerName} no ha tomado una carta y no puede jugar aún.")
                else:
                    if not hasattr(current_player, "jugadas_bajadas"):
                        current_player.jugadas_bajadas = []
                    if currentRound == 1:
                        seguidilla = play[1]
                        trio = play[0]
                        if not any(c.joker for c in seguidilla) and not current_player.isValidStraightF(seguidilla):
                            #print(f"LA SEGUIDILLA {[c for c in seguidilla]} NO ES VÁLIDA")
                            pass
                        elif any(c.joker for c in seguidilla) and not current_player.isValidStraightFJoker(seguidilla):
                            #print(f"LA SEGUIDILLA {[c for c in seguidilla]} CON JOKER NO ES VÁLIDA")
                            pass
                        elif not current_player.isValidTrioF(trio):
                            #print(f"EL TRÍO {[c for c in trio]} NO ES VÁLIDO")
                            pass
                        else:
                            if current_player.sortedStraight(seguidilla) == True: #DEBO QUITAR LO DE LAS ZONAS DE CARTAS Y EL VISUALHAND.
                                                                                    #CREO QUE LO MÁS INDICADO ES CAMBIARLO POR OTRAS COSAS. AHÍ VERÉ QUÉ SE LE HACE.
                                                                                    #SIMPLEMENTE TENGO QUE SEGUIR PROGRAMANDO ESTE CICLO DE JUEGO PARA QUE LA IA
                                                                                    #LO ENTIENDA PERFECTAMENTE :3
                                sortedStraights = seguidilla
                            else:
                                sortedStraights = current_player.sortedStraight(seguidilla)
                            current_player.jugadas_bajadas.append(trio)
                            current_player.jugadas_bajadas.append(sortedStraights)
                            for carta in trio + seguidilla:
                                if carta in current_player.playerHand:
                                    current_player.playerHand.remove(carta)
                            current_player.playMade.append(trio)
                            current_player.playMade.append(sortedStraights)
                            plays_in_table.append(trio) 
                            plays_in_table.append(sortedStraights) 
                            print(f"EL JUGADOR {current_player.playerName} SE BAJÓ CON LAS SIGUIENTES JUGADAS: {[[str(c) for c in play] for play in current_player.playMade]}")
                            #print(f"EL JUGADOR {current_player.playerName} SE BAJOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
                            current_player.downHand = True
                    elif currentRound == 2:
                        seguidilla1 = play[0]
                        seguidilla2 = play[1]
                        if not any(c.joker for c in seguidilla1) and not current_player.isValidStraightF(seguidilla1):
                            print(f"LA SEGUIDILLA 1 {[c for c in seguidilla1]} NO ES VÁLIDA")
                            pass
                        elif any(c.joker for c in seguidilla1) and not current_player.isValidStraightFJoker(seguidilla1):
                            print(f"LA SEGUIDILLA 1 {[c for c in seguidilla1]} CON JOKER NO ES VÁLIDA")
                            pass
                        elif not any(c.joker for c in seguidilla2) and not current_player.isValidStraightF(seguidilla2):
                            print(f"LA SEGUIDILLA 2 {[c for c in seguidilla2]} NO ES VÁLIDA")
                            pass
                        elif any(c.joker for c in seguidilla2) and not current_player.isValidStraightFJoker(seguidilla2):
                            print(f"LA SEGUIDILLA 2 {[c for c in seguidilla2]} CON JOKER NO ES VÁLIDA")
                            pass    
                        else:
                            if current_player.sortedStraight(seguidilla1) == True: #DEBO QUITAR LO DE LAS ZONAS DE CARTAS Y EL VISUALHAND.
                                                                                    #CREO QUE LO MÁS INDICADO ES CAMBIARLO POR OTRAS COSAS. AHÍ VERÉ QUÉ SE LE HACE.
                                                                                    #SIMPLEMENTE TENGO QUE SEGUIR PROGRAMANDO ESTE CICLO DE JUEGO PARA QUE LA IA
                                                                                    #LO ENTIENDA PERFECTAMENTE :3
                                sortedStraights1 = seguidilla1
                            else:
                                sortedStraights1 = current_player.sortedStraight(seguidilla)
                            if current_player.sortedStraight(seguidilla2) == True: #DEBO QUITAR LO DE LAS ZONAS DE CARTAS Y EL VISUALHAND.
                                                                                    #CREO QUE LO MÁS INDICADO ES CAMBIARLO POR OTRAS COSAS. AHÍ VERÉ QUÉ SE LE HACE.
                                                                                    #SIMPLEMENTE TENGO QUE SEGUIR PROGRAMANDO ESTE CICLO DE JUEGO PARA QUE LA IA
                                                                                    #LO ENTIENDA PERFECTAMENTE :3
                                sortedStraights2 = seguidilla2
                            else:
                                sortedStraights2 = current_player.sortedStraight(seguidilla2)
                            combined_check = sortedStraights1 + sortedStraights2
                            if current_player.isValidStraightF(combined_check, max_jokers= 4):
                                print("error, las dos seguidillas bajadas son una misma seguidilla partida en 2")
                            else:
                                current_player.jugadas_bajadas.append(sortedStraights1)
                                current_player.jugadas_bajadas.append(sortedStraights2)
                                for carta in sortedStraights1 + sortedStraights2:
                                    if carta in current_player.playerHand:
                                        current_player.playerHand.remove(carta)
                                current_player.playMade.append(sortedStraights2)
                                current_player.playMade.append(sortedStraights1)
                                plays_in_table.append(sortedStraights1) 
                                plays_in_table.append(sortedStraights2) 
                                print(f"EL JUGADOR {current_player.playerName} SE BAJÓ CON LAS SIGUIENTES JUGADAS: {[[str(c) for c in play] for play in current_player.playMade]}")
                                current_player.downHand = True
                    elif currentRound == 3:
                        trio1 = play[0]
                        trio2 = play[1]
                        trio3 = play[2]
                        if not current_player.isValidTrioF(trio1):
                            #print(f"EL TRIO 1 {[c for c in trio1]} NO ES VÁLIDO")
                            pass
                        elif not current_player.isValidTrioF(trio2):
                            #print(f"EL TRIO 2 {[c for c in trio2]} NO ES VÁLIDO")
                            pass
                        elif not current_player.isValidTrioF(trio3):
                            #print(f"EL TRIO 3 {[c for c in trio3]} NO ES VÁLIDO")
                            pass
                        else:
                            # Obtenemos el valor de la primera carta que NO sea joker en cada zona
                            # next() busca el primer elemento que cumpla la condición, devuelve None si no encuentra
                            v1 = next((c.value for c in trio1 if not getattr(c, "joker", False)), None)
                            v2 = next((c.value for c in trio2 if not getattr(c, "joker", False)), None)
                            v3 = next((c.value for c in trio3 if not getattr(c, "joker", False)), None)
                            
                            # Comparamos si hay duplicados
                            if v1 == v2 or v1 == v3 or v2 == v3:
                                print("ERROR: No puedes bajar dos o más tríos del mismo valor.")
                            else:
                                current_player.jugadas_bajadas.append(trio1)
                                current_player.jugadas_bajadas.append(trio2)
                                current_player.jugadas_bajadas.append(trio3)
                                for carta in trio1 + trio2 + trio3:
                                    if carta in current_player.playerHand:
                                        current_player.playerHand.remove(carta)
                                current_player.playMade.append(trio1)
                                current_player.playMade.append(trio2)
                                current_player.playMade.append(trio3)
                                plays_in_table.append(trio1)
                                plays_in_table.append(trio2)
                                plays_in_table.append(trio3)
                                
                                print(f"EL JUGADOR {current_player.playerName} SE BAJÓ CON LAS SIGUIENTES JUGADAS: {[[str(c) for c in play] for play in current_player.playMade]}")
                                current_player.downHand = True
                    elif currentRound == 4:
                        trio1 = play[0]
                        trio2 = play[1]
                        seguidilla = play[2]

                        if not current_player.isValidTrioF(trio1):
                            #print(f"EL TRIO 1 {[c for c in trio1]} NO ES VÁLIDO")
                            pass
                        elif not current_player.isValidTrioF(trio2):
                            #print(f"EL TRIO 2 {[c for c in trio2]} NO ES VÁLIDO")
                            pass
                        elif not any(c.joker for c in seguidilla) and not current_player.isValidStraightF(seguidilla):
                            #print(f"LA SEGUIDILLA {[c for c in seguidilla]} NO ES VÁLIDA")
                            pass
                        elif any(c.joker for c in seguidilla) and not current_player.isValidStraightFJoker(seguidilla):
                            #print(f"LA SEGUIDILLA {[c for c in seguidilla]} CON JOKER NO ES VÁLIDA")
                            pass
                        else:
                            v1 = next((c.value for c in trio1 if not getattr(c, "joker", False)), None)
                            v2 = next((c.value for c in trio2 if not getattr(c, "joker", False)), None)
                            
                            if v1 == v2:
                                print("ERROR: Los dos tríos deben ser de valores distintos.")
                            else:
                                complete = trio1 + trio2 + seguidilla
                                if len(complete) != len(current_player.playerHand):
                                    print("ERROR: En la cuarta ronda, debes bajarte con TODAS las cartas de tu mano")
                                else:
                                    if current_player.sortedStraight(seguidilla) == True: #DEBO QUITAR LO DE LAS ZONAS DE CARTAS Y EL VISUALHAND.
                                                                                                            #CREO QUE LO MÁS INDICADO ES CAMBIARLO POR OTRAS COSAS. AHÍ VERÉ QUÉ SE LE HACE.
                                                                                                            #SIMPLEMENTE TENGO QUE SEGUIR PROGRAMANDO ESTE CICLO DE JUEGO PARA QUE LA IA
                                                                                                            #LO ENTIENDA PERFECTAMENTE :3
                                        sortedStraights = seguidilla
                                    else:
                                        sortedStraights = current_player.sortedStraight(seguidilla)
                                    current_player.jugadas_bajadas.append(trio1)
                                    current_player.jugadas_bajadas.append(trio2)
                                    current_player.jugadas_bajadas.append(sortedStraights)
                                    for carta in trio1 + trio2 + sortedStraights:
                                        if carta in current_player.playerHand:
                                            current_player.playerHand.remove(carta)
                                    current_player.playMade.append(trio1)
                                    current_player.playMade.append(trio2)
                                    current_player.playMade.append(sortedStraights)
                                    plays_in_table.append(trio1)
                                    plays_in_table.append(trio2)
                                    plays_in_table.append(sortedStraights) 
                                    
                                    print(f"EL JUGADOR {current_player.playerName} SE BAJÓ CON LAS SIGUIENTES JUGADAS: {[[str(c) for c in play] for play in current_player.playMade]}")
                                    current_player.downHand = True

            # Insert phase
            if current_player.downHand and len(current_player.playerHand) > 0:
                play2 = current_player.decide_insert_card(plays_in_table)
                if play2 and current_player.cardDrawn:
                    #print(f"ÍNDICE INICIAL PARA INSERTAR: {play2[0]}")
                    targetPlayer = None
                    target_index = None
                    for i, p in enumerate(plays_in_table):
                        for player in playersInOrder:
                            if p in player.playMade and i == play2[0]:
                                targetPlayer = player
                                target_index = player.playMade.index(p)
                                break
                        if targetPlayer:
                            break
                        else:
                            continue
                    #print("targetPlayer de la inserción:", targetPlayer)
                    if targetPlayer is not None and target_index is not None:
                        #print(f"CARTA A INSERTAR: {play2[1]}")
                        jugada = current_player.insertCard(targetPlayer, target_index, play2[1], play2[2])
                        if not jugada or jugada == None:
                            print("LA INSERCIÓN NO FUE VÁLIDAAAAAAAAAAAAAAAAAAAAAAAA")
                        else:
                            print("LA INSERCIÓN SE EFECTÚO CORRECTAMENTE AL FIIIIIIIIIIIIIIIIIIN")
                
                play3 = current_player.decide_substitute_joker(plays_in_table)
                if play3 and current_player.cardDrawn and currentRound != 3:
                    targetPlayer2 = None
                    target_index2 = None
                    for p in plays_in_table:
                        for player in playersInOrder:
                            if p in player.playMade:
                                targetPlayer2 = player
                                target_index2 = player.playMade.index(p)
                                break
                        if targetPlayer2:
                            break
                    if targetPlayer2 is not None and target_index2 is not None:
                        current_player.insertCard(targetPlayer2, target_index2, play3[1], None, None)


            # Discard phase
            card_to_discard = current_player.decide_discard()
            if card_to_discard is None:
                card_to_discard = []
            elif not isinstance(card_to_discard, list):
                card_to_discard = [card_to_discard]

            # A card taken from the discard pile cannot be discarded in the
            # same turn. Keep a Joker burn valid when another legal pair exists.
            forbidden_card = getattr(current_player, "drawn_from_discard_card", None)
            if forbidden_card is not None and any(card is forbidden_card for card in card_to_discard):
                allowed_cards = [card for card in current_player.playerHand if card is not forbidden_card]
                if current_player.downHand:
                    allowed_jokers = [card for card in allowed_cards if card.joker]
                    allowed_non_jokers = [card for card in allowed_cards if not card.joker]
                    if allowed_jokers and allowed_non_jokers:
                        card_to_discard = [allowed_jokers[0], allowed_non_jokers[0]]
                    elif allowed_non_jokers:
                        card_to_discard = [allowed_non_jokers[0]]
                    else:
                        card_to_discard = []
                else:
                    allowed_non_jokers = [card for card in allowed_cards if not card.joker]
                    card_to_discard = [allowed_non_jokers[0]] if allowed_non_jokers else []

            if len(card_to_discard) >= 1 and not any(c is None for c in card_to_discard) and current_player.cardDrawn and len(current_player.playerHand) > 0 and current_player.isHand:
                current_player.discardCard(card_to_discard, roundObject)
                print(f"CARTAS RESTANTES DE {current_player.playerName} después de descartar: {[str(c) for c in current_player.playerHand]}")
                current_player.cardDrawn = False
                current_player.isHand = False
                current_player.drawn_from_discard_card = None
                roundObject.lastDiscardPlayer = current_player
            if len(current_player.playerHand) == 0:
                current_player.winner = True
                print(f"FIN DE LA RONDA {currentRound}. El ganador fue {current_player.playerName}")
                if currentRound == 4:
                    currentRound = 1
                else:
                    currentRound += 1
                print(f"INICIANDO LA RONDA NÚMERO {currentRound}...")

                # Score the hand that remained in the finished round before
                # dealing any cards for the next one.
                eliminated_players = []
                for p in playersInOrder[:]:
                    if not p.winner:
                        print(f"EL PERDEDOR {p.playerName} tenía {p.playerPoints} puntos")
                        p.calculatePoints()
                        print(f"AHORA TIENE {p.playerPoints} puntos")
                    p.playerHand = []
                    p.playerBuy = False
                    p.cardDrawn = False
                    p.downHand = False
                    p.playMade = []
                    p.jugadas_bajadas = []
                    p.winner = False
                    if p.playerPoints >= 500:
                        eliminated_players.append(p)
                        print(f"EL JUGADOR {p.playerName} HA SIDO ELIMINADo0o0O0o0o0O0o0o0O0o0O0o0O0O0oO!!! PUNTUACIÓN: {p.playerPoints}")
                    print(f"QUEDAN {len(playersInOrder)} JUGADORES EN LA PARTIDA!!!!")
                    print(f"Jugadores restantes en la partida: {[{p.playerName, p.playerPoints}]}")

                for p in eliminated_players:
                    playersInOrder.remove(p)

                if len(playersInOrder) > 1:
                    discard_pile = []
                    deck = []
                    plays_in_table = []
                    roundObject = startRound(playersInOrder, screen)[0]
                    discard_pile = roundObject.discards
                    deck = roundObject.pile
            if len(playersInOrder) == 1:
                print(f"TENEMOS UN GANADOR!!!!! El ganador de la partida es: {playersInOrder[0].playerName}!!!! FELICIDADES!!!")
                break

            if current_index == (len(playersInOrder) - 1):
                current_index = 0
            else:
                current_index += 1
                current_player = None
            

        # --- 1. Tomar carta ---
        # El jugador decide si tomar del descarte o del mazo.
        """if sourceAction == "discard":
            if discard_pile:
                drawCard(current_player, roundObject, fromDiscards=True, indexDiscards=roundObject.discards.index(discard_pile[-1]))
            else:
                print("El montón de descartes está vacío. No se puede tomar de ahí.")
                drawCard(current_player, roundObject)  # Tomar del mazo si el descarte está vacío
        elif sourceAction == "deck":
            drawCard(current_player, roundObject)

        # --- 2. Bajarse ---
        # El jugador decide si se baja o no.
        #la decision vendrá desde la interfaz. Cambiaré el input para que sea un parámetro del método
        #y reciba la acción del botón de bajarse si se pulsa. Sino, queda como None
        if sourceAction == "Bajarse":
            current_player.getOff(trio, seguidilla)

        for p in turn_order:
            if not p.isHand and p != current_player:
                respuesta = p.playerBuy
                if res
                if len(deck) == 0:
                                refillDeck(roundObject)puesta:
                    p.buyCard(roundObject)
                    break

        # --- Estado de depuración ---
        state["players"] = [{
            "name": p.playerName,
            "hand": [str(c) for c in p.playerHand],
            "down": getattr(p, "downHand", []),
            "isHand": p.isHand
        } for p in playersInOrder]
        state["deck_remaining"] = len(deck)
        state["discard_top"] = discard_pile[-1] if discard_pile else None

        # --- Siguiente jugador ---
        current_index = (current_index + 1) % len(turn_order)

        # Condición de salida temporal
        if len(deck) == 0:
            refillDeck(roundObject)

    return state"""
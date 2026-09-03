import pygame
import sys
import os
from ui import UIManager
from network import NetworkManager
from volumen import ControlVolumen


def resource_path(relative_path):
    """
    Devuelve la ruta absoluta a un recurso (imagen, sonido, fuente...),
    funcionando tanto en desarrollo normal como empaquetado con PyInstaller
    (--onefile o --onedir). PyInstaller extrae los archivos agregados con
    --add-data a una carpeta temporal indicada en sys._MEIPASS; fuera de un
    ejecutable empaquetado, sys._MEIPASS no existe y se usa la carpeta del
    propio script como base.
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def main():
    pygame.init()

    info = pygame.display.Info()
    SCREEN_WIDTH = min(info.current_w, 1920)
    SCREEN_HEIGHT = min(info.current_h, 1080)

    network_manager = NetworkManager()
    ui_manager = UIManager(SCREEN_WIDTH, SCREEN_HEIGHT, network_manager)

    pygame.mixer.init()
    pygame.mixer.music.load(resource_path("assets/sonido/musica_fondo.mp3"))
    pygame.mixer.music.play(-1)
    ctrl_volumen = ControlVolumen()

    running = True
    while running:
        result = ui_manager.handle_events()
        if result == "launch_ui2":
            if len(network_manager.connected_players) == 1:
                pygame.mixer.music.stop()

            import ui2

            bots_precargados = None
            if network_manager.is_host and getattr(network_manager, 'num_bots', 0) > 0:
                # Cargar los modelos de IA de los bots es lento y, sin esto,
                # deja la ventana en negro y en silencio mientras carga. En
                # vez de eso, mostramos una pantalla animada (imágenes con
                # fundido + música de espera) mientras la carga real ocurre
                # en un hilo aparte.
                import functools
                from loading_screen import mostrar_pantalla_carga

                pantalla_actual = pygame.display.get_surface()
                ancho_actual, alto_actual = pantalla_actual.get_size()
                cargar_bots = functools.partial(
                    ui2.cargar_bots_ia,
                    network_manager,
                    len(network_manager.connected_players)
                )

                if getattr(network_manager, 'easter_egg_gaster', False):
                    # Encuentro oculto: pantalla de carga propia (imágenes y
                    # música distintas a las de un duelo normal contra bots).
                    bots_precargados = mostrar_pantalla_carga(
                        pantalla_actual, ancho_actual, alto_actual, cargar_bots,
                        nombres_imagenes=["Gaster1.png", "Gaster2.png", "Gaster3.png", "Gaster4.png", "Gaster5.png", "Gaster6.png", "Gaster7.png"],
                        subcarpeta_imagenes="carga_gaster",
                        musica_relpath=os.path.join("assets", "sonido", "GasterLoading.mp3"),
                        texto_carga=""
                    )
                else:
                    bots_precargados = mostrar_pantalla_carga(pantalla_actual, ancho_actual, alto_actual, cargar_bots)

            if network_manager.is_host:
                jugadores = network_manager.connected_players
                print(f"Inicializando juego con {len(jugadores)}")
                network_manager.running = True

                ui2.main(network_manager, bots_precargados=bots_precargados)

                # ui2.py maneja su propia ventana (puede cambiar de tamaño,
                # entrar en pantalla completa, etc.), así que al volver acá
                # el ui_manager que ya teníamos puede haber quedado con un
                # tamaño/superficie desactualizados -eso es lo que causaba
                # que el menú se viera solo en una parte de la ventana y el
                # resto quedara con contenido viejo de la partida-. Se
                # recrea con el tamaño ACTUAL de la ventana para que quede
                # todo bien ajustado, con medidas relativas.
                ancho_actual, alto_actual = pygame.display.get_surface().get_size()
                ui_manager = UIManager(ancho_actual, alto_actual, network_manager)
                ui_manager.SCREEN.fill((0, 0, 0))
                pygame.display.flip()

                # Se limpia toda la configuración de bots/encuentro oculto
                # para que una partida normal posterior no arrastre nada de
                # esto (ni el flag de Gaster, ni bots de una sala anterior).
                network_manager.game_started = False
                network_manager.num_bots = 0
                network_manager.bot_duel_config = None
                network_manager.easter_egg_gaster = False
                continue
            else:
                network_manager.running = True

                ui2.main(network_manager)

                ancho_actual, alto_actual = pygame.display.get_surface().get_size()
                ui_manager = UIManager(ancho_actual, alto_actual, network_manager)
                ui_manager.SCREEN.fill((0, 0, 0))
                pygame.display.flip()

                network_manager.game_started = False
                network_manager.num_bots = 0
                network_manager.bot_duel_config = None
                network_manager.easter_egg_gaster = False
                continue

        elif result is False:
            running = False
        else:
            ui_manager.update()
            ctrl_volumen.actualizar_y_dibujar()


    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

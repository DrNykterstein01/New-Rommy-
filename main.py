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
     
    SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
    network_manager = NetworkManager()
    ui_manager = UIManager(SCREEN_WIDTH, SCREEN_HEIGHT, network_manager)

    pygame.mixer.init()  
    pygame.mixer.music.load(resource_path("assets/sonido/musica_fondo.mp3"))
    pygame.mixer.music.play(-1)
    ctrl_volumen=ControlVolumen()

    running = True
    while running:
        result = ui_manager.handle_events()
        if result == "launch_ui2":
            if len(network_manager.connected_players) == 1:
                pygame.mixer.music.stop()
            if network_manager.is_host:
                jugadores = network_manager.connected_players
                print(f"Inicializando juego con {len(jugadores)}")
                # Para verificar que el network_manager siga ejecutándose
                network_manager.running = True

                import ui2
                # Pasa el objeto network_manager que contiene el estado de la conexión
                ui2.main(network_manager)
                ui_manager.current_screen = "main"
                
                # Resetear estado para próxima partida
                network_manager.game_started = False
                continue
            else:
                # Para verificar que el network_manager siga ejecutándose
                network_manager.running = True
                
                import ui2
                # Pasa el objeto network_manager que contiene el estado de la conexión
                ui2.main(network_manager)
                ui_manager.current_screen = "main"
                
                # Resetear estado para próxima partida
                network_manager.game_started = False
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
{
    
}
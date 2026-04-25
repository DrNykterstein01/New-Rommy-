import pygame
import os
import threading
import pickle
import time
from network import NetworkManager
import sys

icon = pygame.image.load("assets/icon.png") 
pygame.display.set_icon(icon)
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("RUMMY 500")

class Button:
    def __init__(self, image, pos, text_input, font, base_color, hovering_color, size=(250, 100), scale_factor=1.1):
        self.image = image
        self.original_image = image
        self.x_pos = pos[0]
        self.y_pos = pos[1]
        self.font = font
        self.base_color = base_color
        self.hovering_color = hovering_color
        self.text_input = text_input
        self.base_size = size
        self.scale_factor = scale_factor
        self.current_size = list(size)
        self.is_hovering = False
        # Render inicial del texto
        try:
            self.text = self.font.render(self.text_input, True, pygame.Color(self.base_color))
        except Exception:
            self.text = self.font.render(self.text_input, True, (255,255,255))
        # Crear rect inicial coherente
        if self.image is not None:
            self.image = pygame.transform.scale(self.original_image, self.current_size)
            self.rect = self.image.get_rect(center=(self.x_pos, self.y_pos))
        else:
            self.rect = pygame.Rect(0, 0, *self.current_size)
            self.rect.center = (self.x_pos, self.y_pos)
        self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))

    def _current_rect(self):
        """Rect calculado a partir de current_size y posición (no usa self.rect antiguo)."""
        r = pygame.Rect(0, 0, int(self.current_size[0]), int(self.current_size[1]))
        r.center = (int(self.x_pos), int(self.y_pos))
        return r

    def update(self, screen):
        # Calcular tamaño objetivo según hover
        target_size = [int(self.base_size[0] * (self.scale_factor if self.is_hovering else 1)),
                       int(self.base_size[1] * (self.scale_factor if self.is_hovering else 1))]
        # Interpolación suave
        for i in range(2):
            if abs(self.current_size[i] - target_size[i]) > 1:
                self.current_size[i] += (target_size[i] - self.current_size[i]) * 0.2
            else:
                self.current_size[i] = target_size[i]

        # Dibujar (imagen o rect)
        if self.original_image is not None:
            scaled_image = pygame.transform.scale(self.original_image, [int(x) for x in self.current_size])
            scaled_rect = scaled_image.get_rect(center=(self.x_pos, self.y_pos))
            screen.blit(scaled_image, scaled_rect)
            self.rect = scaled_rect
        else:
            # rect basado en tamaño actual
            self.rect = self._current_rect()
            pygame.draw.rect(screen, (255,255,255), self.rect, border_radius=8)  # optional background
            pygame.draw.rect(screen, (100,100,100), self.rect, 2, border_radius=8)

        # Recalcular y dibujar texto centrado
        self.text_rect = self.text.get_rect(center=self.rect.center)
        screen.blit(self.text, self.text_rect)

    def checkForInput(self, position):
        # Usar rect actualizado para chequear colisión
        try:
            return self.rect.collidepoint(position)
        except Exception:
            return False

    def changeColor(self, position):
        # Actualiza el texto con color hover/base según colisión (sin depender de rect obsoleto)
        try:
            if self._current_rect().collidepoint(position):
                self.text = self.font.render(self.text_input, True, pygame.Color(self.hovering_color))
            else:
                self.text = self.font.render(self.text_input, True, pygame.Color(self.base_color))
        except Exception:
            # fallback por si los colores no son válidos
            if self._current_rect().collidepoint(position):
                self.text = self.font.render(self.text_input, True, (255,255,255))
            else:
                self.text = self.font.render(self.text_input, True, (200,200,200))

    def check_hover(self, position):
        # Actualizar estado de hover basándose en rect calculado
        was = self.is_hovering
        self.is_hovering = self._current_rect().collidepoint(position)
        if was != self.is_hovering:
            # actualizar color inmediatamente al entrar/salir
            self.changeColor(position)
# ===========================
# Clase para cajas de texto (reemplazada por la versión de uiMOD)
# ===========================
class InputBox:
    def __init__(self, x, y, w, h, font, text=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = pygame.Color("#e35d59")
        self.color_active = pygame.Color("#F9AA33")
        self.color = self.color_inactive
        self.text = text
        self.font = font
        self.txt_surface = font.render(text, True, pygame.Color("#000000"))
        self.active = False
        self.clock = None  # Inicializar el reloj como None

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Si el usuario hizo click dentro del rect, cambia el estado activo
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = self.color_active if self.active else self.color_inactive
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    # Señalar al llamador que se quiere enviar el texto (no borrar aquí)
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    # Añadir el carácter presionado
                    self.text += event.unicode
                # Volver a renderizar la surface del texto
                self.txt_surface = self.font.render(self.text, True, pygame.Color("#000000"))
        return False

    def update(self):
        width = max(200, self.txt_surface.get_width() + 10)
        self.rect.w = width
        # No usar self.clock ni lógica global aquí.
        # Sólo mantener la caja actualizada (la UI principal dibuja todo lo demás).
        return
        self.draw_background()

        # Dibuja el título siempre, sin importar el menú
        title_rect = self.titulo_img.get_rect(center=(self.SCREEN_WIDTH//2, int(self.SCREEN_HEIGHT*0.25)))
        self.SCREEN.blit(self.titulo_img, title_rect)

        # --- ACTUALIZAR INPUT BOXES SEGÚN LA PANTALLA ---
        if self.current_screen == "join":  
            #self.ip_input_box.update()
            #-----------------------------
            self.join_player_input_box.update()  # Actualiza el nuevo input
            #-------------------------------
            self.join_password_input_box.update()
        elif self.current_screen == "create":  
            self.host_input_box.update()          
            self.name_input_box.update()
            self.password_input_box.update()
            self.max_players_input_box.update()
        elif self.current_screen == "lobby":  
            #self.messages_input_box.update()
            self.message_input_box.update()

        # --- MANEJO DE CADA PANTALLA ---
        if self.current_screen == "main":  
            mouse_pos = self.draw_main_menu()
            for button in [self.JUGAR_BUTTON, self.REGLAS_BUTTON, self.SALIR_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "play":  
            mouse_pos = self.draw_play_menu()
            for button in [self.UNIRSE_BUTTON, self.CREAR_BUTTON, self.PLAY_BACK]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "join":  
            mouse_pos = self.draw_join_menu()
            for button in [self.JOIN_IP_BUTTON, self.JOIN_REFREHS_BUTTON, self.JOIN_BACK_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "create":  
            mouse_pos = self.draw_create_menu()
            for button in [self.CREATE_GAME_BUTTON, self.CREATE_BACK_BUTTON]:
                button.check_hover(mouse_pos)
        
        elif self.current_screen == "lobby":  
            mouse_pos = self.draw_lobby()
            for button in [self.SEND_MS_BUTTON, self.PLAY_GAME_BUTTON, self.LOBBY_BACK_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "play_game":  
            mouse_pos = self.draw_play_game()
            #for button in [self.SEND_MS_BUTTON, self.PLAY_GAME_BUTTON, self.LOBBY_BACK_BUTTON]:
            #    button.check_hover(mouse_pos)

        pygame.display.update()
        return True

    def draw(self, screen):
        pygame.draw.rect(screen, pygame.Color("#FFFFFF"), self.rect, border_radius=12)
        pygame.draw.rect(screen, self.color, self.rect, 2, border_radius=12)
        screen.blit(self.txt_surface, (self.rect.x + 8, self.rect.y + (self.rect.h - self.txt_surface.get_height())//2))

# ===========================
# Clase que maneja la interfaz
# ===========================
class   UIManager:
    def __init__(self, screen_width, screen_height, network_manager):
        # Dimensiones de la pantalla
        self.SCREEN_WIDTH = screen_width
        self.SCREEN_HEIGHT = screen_height
        
        # Manager de red (para conectar con el servidor, enviar/recibir datos)
        self.network_manager = network_manager
        
        # Crear ventana de Pygame con las dimensiones dadas
        self.SCREEN = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
        
        # Título de la ventana        
        pygame.display.set_caption("Menu Principal")
        
        # Cargar todos los assets (imágenes, botones, etc.)
        self.load_assets()
        
        # Pantalla actual (puede ser "main", "settings", etc.)
        self.current_screen = "main"
        
        # Reloj para controlar FPS y timing
        self.clock = pygame.time.Clock()
        
        # Guardar tiempo actual para calcular deltas
        self.last_time = pygame.time.get_ticks()
        
        # Inicializar componentes de la UI (botones, cajas de texto, etc.)
        self.init_components()

        self.servers = []      #Lista de servidores encontrados
        self.selectedServer = None  #ALmacena el servidor selecionado
        self.isSeletedServer = False #Fija el servidor seleccionado
        self.server_dropdown_open = False  # Controla si el modal de servidores está abierto
        self.server_dropdown_scroll = 0   # Scroll offset para la lista de servidores
        self._last_discover_time = 0      # Timestamp de la última búsqueda de servidores
        self._discover_interval = 8000    # Intervalo en ms para re-buscar servidores automáticamente
        self.response = None #Resuesta de conexion para el jugador
        self.is_hovered = None
        self.messages = []    #Mensajes para el Chat
        self.chatLock = threading.Lock() 
        self.playGamePlayer = False
        #-----------------------------------
        self.wrong_password_until = 0
        self.fullserver_until = 0
        self.no_server_until = 0
        self.countdown_active = False      # Indica si el conteo regresivo está activo
        self.countdown_start_time = 0      # Tiempo de inicio del conteo (en ms)
        self.countdown_duration = 5        # Duración del conteo en segundos

        click_path = os.path.join("assets", "sonido", "click.wav")
        self.click_sound = pygame.mixer.Sound(click_path)      
        #------------------------------------


    def load_assets(self):
        assets_path = os.path.join(os.getcwd(), "assets")  # Ruta a la carpeta de assets

        # Guardar ruta de la fuente pixelada y tamaño global pequeño
        self.global_font_size = 18  # <-- tamaño pequeño uniforme (ajusta si quieres más/menos)
        self.pixel_font_path = os.path.join(assets_path, "PressStart2P-Regular.ttf")

        # Intentar precargar la fuente pixelada (con tamaño global)
        try:
            self.pixel_font = pygame.font.Font(self.pixel_font_path, self.global_font_size)
        except Exception:
            self.pixel_font = None
            print("Advertencia: No se pudo cargar la fuente pixelada. Usando fuente por defecto.")
        try:
            conectar_path = os.path.join(os.getcwd(), "assets", "conectar.png")
            self.conectar_img = pygame.image.load(conectar_path).convert_alpha()        
        except Exception:
            self.conectar_img = None
        # Guardar las imágenes originales para poder re-escalarlas al cambiar el tamaño de la ventana
        self.titulo_img_original = pygame.image.load(os.path.join(assets_path, "titulo.png")).convert_alpha()
        self.fondo_img_original = pygame.image.load(os.path.join(assets_path, "fondo.png")).convert()

        # Imagen de fondo/rectángulo estilo cuadro usado en uiMOD (cuadro.png)
        self.cuadro_img = pygame.image.load(os.path.join(assets_path, "cuadro.png")).convert_alpha()

        self.jugar_img = pygame.image.load(os.path.join(assets_path, "jugar_button.png")).convert_alpha()  # Botón Jugar
        self.reglas_img = pygame.image.load(os.path.join(assets_path, "reglas_button.png")).convert_alpha()  # Botón Reglas
        self.salir_img = pygame.image.load(os.path.join(assets_path, "salir_button.png")).convert_alpha()  # Botón Salir
        self.unirse_img = pygame.image.load(os.path.join(assets_path, "unirse_button.png")).convert_alpha()  # Botón Unirse
        self.actualizar_img = pygame.image.load(os.path.join(assets_path, "refreshButtom.png")).convert_alpha()  # Botón Actualizar
        self.crear_img = pygame.image.load(os.path.join(assets_path, "crear_button.png")).convert_alpha()  # Botón Crear
        self.volver_img = pygame.image.load(os.path.join(assets_path, "volver_button.png")).convert_alpha()  # Botón Volver
        self.iniciar_juego_img = pygame.image.load(os.path.join(assets_path, "iniciar_juego_button.png")).convert_alpha()  # Botón iniciar juego

        self.animacion_fondo_img = pygame.image.load(os.path.join(assets_path, "animacion_fondo.png")).convert_alpha()  # Fondo animado
        self.animacion_fondo_img = pygame.transform.scale(self.animacion_fondo_img, (1000, 800))  # Escalar animación
        self.pos_izquierda = (40, 120)  # Posición animación izquierda
        self.pos_derecha = (1230, 120)  # Posición animación derecha
        self.angulo_izquierda = 0  # Ángulo inicial izquierda
        self.angulo_derecha = 0  # Ángulo inicial derecha

        # Crear una superficie (imagen) con el texto de los créditos usando la fuente cargada (o fallback)
        try:
            font_for_credits = self.pixel_font if self.pixel_font else pygame.font.SysFont("Arial", self.global_font_size)
            self.credits_surface = font_for_credits.render(
                "Proyecto realizado por el Equipo 1",
                True,
                "#d7fcd4"
            )
        except Exception:
            self.credits_surface = pygame.font.SysFont(None, self.global_font_size).render("Proyecto realizado por el Equipo 1", True, "#d7fcd4")
    # Función para obtener una fuente personalizada o de respaldo
    def get_font(self, size):
        try:
            # Intentar cargar una fuente incluida en assets (si existe)
            font_path = os.path.join(os.getcwd(), "assets", "pixel_font.ttf")
            return pygame.font.Font(font_path, size)
        except:
            return pygame.font.SysFont(None, size)

    # Función para inicializar todos los botones y elementos de la interfaz
    def init_components(self):

        self.crear_partida_img = pygame.image.load("assets/crear_button.png").convert_alpha()
        self.crear_partida_img_scaled = pygame.transform.scale(self.crear_partida_img, (120, 40))  # Tamaño pequeño
        self.crear_partida_img_rect = self.crear_partida_img_scaled.get_rect()

        # Cargar imagen de enviar mensaje
        try:
            self.send_img = pygame.image.load(os.path.join("assets", "enviar_mensaje.png")).convert_alpha()
        except Exception:
            self.send_img = None

        # Dimensiones de referencia para el diseño original (1280x720)
        self.REF_W = 1280
        self.REF_H = 720

        # Construir todos los botones con posiciones relativas
        self._build_buttons()

        # Ajustar la posicion de los creditos
        self.credits_x_pos = self.SCREEN_WIDTH
        self.credits_y_pos = int(self.SCREEN_HEIGHT * 0.95)

        self.init_input_boxes()

    def _sx(self, x):
        """Escala una coordenada X absoluta (basada en 1280) al ancho actual."""
        return int(x * self.SCREEN_WIDTH / self.REF_W)

    def _sy(self, y):
        """Escala una coordenada Y absoluta (basada en 720) al alto actual."""
        return int(y * self.SCREEN_HEIGHT / self.REF_H)

    def _sw(self, w):
        """Escala un ancho absoluto al ancho actual."""
        return int(w * self.SCREEN_WIDTH / self.REF_W)

    def _sh(self, h):
        """Escala un alto absoluto al alto actual."""
        return int(h * self.SCREEN_HEIGHT / self.REF_H)

    def _build_buttons(self):
        """Construye/reconstruye todos los botones con posiciones relativas a la pantalla actual."""
        W = self.SCREEN_WIDTH
        H = self.SCREEN_HEIGHT

        # Se escalan las imágenes originales basándose en la resolución actual de la pantalla
        self.titulo_img = pygame.transform.scale(self.titulo_img_original, (int(W * 0.5), int(H * 0.35)))
        self.fondo_img = pygame.transform.scale(self.fondo_img_original, (W, H))

        # Botón "JUGAR"
        self.JUGAR_BUTTON = Button(
            image=self.jugar_img,
            pos=(W // 2, int(H * 0.55)),
            text_input="",
            font=self.get_font(self._sw(75)),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._sw(400), self._sh(110))
        )

        # Botón "REGLAS"
        self.REGLAS_BUTTON = Button(
            image=self.reglas_img,
            pos=(W // 2 - self._sw(180), int(H * 0.75)),
            text_input="",
            font=self.get_font(self._sw(75)),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._sw(300), self._sh(90))
        )

        # Botón "SALIR"
        self.SALIR_BUTTON = Button(
            image=self.salir_img,
            pos=(W // 2 + self._sw(180), int(H * 0.75)),
            text_input="",
            font=self.get_font(self._sw(75)),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._sw(300), self._sh(90))
        )

        # Botón "UNIRSE"
        self.UNIRSE_BUTTON = Button(
            image=self.unirse_img,
            pos=(W // 2 - self._sw(150), self._sy(420)),
            text_input="",
            font=self.get_font(self._sw(50)),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._sw(250), self._sh(100))
        )

        # Botón "CREAR"
        self.CREAR_BUTTON = Button(
            image=self.crear_img,
            pos=(W // 2 + self._sw(150), self._sy(420)),
            text_input="",
            font=self.get_font(self._sw(50)),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._sw(250), self._sh(100))
        )

        # Botón "VOLVER" en pantalla de juego
        self.PLAY_BACK = Button(
            image=self.volver_img,
            pos=(W // 2, int(H * 0.75)),
            text_input="",
            font=self.get_font(self._sw(75)),
            base_color="White",
            hovering_color="Green"
        )

        # Fuente pequeña para botones secundarios
        small_font = self.get_font(self._sw(30))

        # Botón para conectar por IP en el menú Join
        join_btn_size = (self._sw(120), self._sh(40))
        join_img = getattr(self, "conectar_img", None)
        self.JOIN_IP_BUTTON = Button(
            image=join_img,
            pos=(W // 2 + self._sw(180), H // 2),
            text_input="",
            font=self.get_font(self._sw(20)),
            base_color="#d7fcd4",
            hovering_color="White",
            size=join_btn_size
        )

        # Botón "VOLVER" en menú de unirse
        self.JOIN_BACK_BUTTON = Button(
            image=self.volver_img,
            pos=(W // 2 + self._sw(150), int(H * 0.85)),
            text_input="",
            font=self.get_font(self._sw(75)),
            base_color="White",
            hovering_color="Green"
        )

        # Botón "ACTUALIZAR" en menú de unirse
        self.JOIN_REFREHS_BUTTON = Button(
            image=self.actualizar_img,
            pos=(W // 2 - self._sw(150), int(H * 0.85)),
            text_input="",
            font=self.get_font(self._sw(75)),
            base_color="White",
            hovering_color="Green"
        )

        # Botón "Crear Partida"
        font_btn = self.get_font(self._sw(22))
        crear_size = (self._sw(120), self._sh(40))
        self.CREATE_GAME_BUTTON = Button(
            image=self.crear_partida_img,
            pos=(W // 2, H // 2),
            text_input="",
            font=font_btn,
            base_color="#2ecc71",
            hovering_color="#4cd964",
            size=crear_size,
            scale_factor=1.12
        )
        self.CREATE_GAME_BUTTON.current_size = list(crear_size)
        self.CREATE_GAME_BUTTON.base_size = crear_size

        # Botón "VOLVER" en menú de crear partida
        self.CREATE_BACK_BUTTON = Button(
            image=self.volver_img,
            pos=(W // 2, int(H * 0.85)),
            text_input="",
            font=self.get_font(self._sw(75)),
            base_color="White",
            hovering_color="Green"
        )

        # Botón "INICIAR PARTIDA" en pantalla de Lobby
        self.PLAY_GAME_BUTTON = Button(
            image=self.iniciar_juego_img,
            pos=(W // 2 - self._sw(150), int(H * 0.85)),
            text_input="",
            font=self.get_font(self._sw(75)),
            base_color="White",
            hovering_color="Green"
        )

        # Botón "VOLVER" en menú lobby
        self.LOBBY_BACK_BUTTON = Button(
            image=self.volver_img,
            pos=(W // 2 + self._sw(150), int(H * 0.85)),
            text_input="",
            font=self.get_font(self._sw(75)),
            base_color="White",
            hovering_color="Green"
        )

        # Botón "enviar mensaje" en menu lobby
        crear_size = (self._sw(120), self._sh(40))
        self.SEND_MS_BUTTON = Button(
            image=self.send_img,
            pos=(W // 2, self._sy(530)),
            text_input="",
            font=small_font,
            base_color="#d7fcd4",
            hovering_color="White",
            size=crear_size
        )

    def recalc_layout(self, new_width, new_height):
        """Recalcula todo el layout cuando la ventana cambia de tamaño."""
        self.SCREEN_WIDTH = new_width
        self.SCREEN_HEIGHT = new_height
        self.SCREEN = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)

        # Reconstruir botones con nuevas posiciones
        self._build_buttons()

        # Reajustar créditos
        self.credits_x_pos = new_width
        self.credits_y_pos = int(new_height * 0.95)

        # Reajustar animaciones de fondo
        self.pos_izquierda = (self._sx(40), self._sy(120))
        self.pos_derecha = (new_width - self._sx(40), self._sy(120))

        # Reescalar animación de fondo
        self.animacion_fondo_img = pygame.image.load(os.path.join(os.getcwd(), "assets", "animacion_fondo.png")).convert_alpha()
        self.animacion_fondo_img = pygame.transform.scale(self.animacion_fondo_img, (self._sw(1000), self._sh(800)))

    def init_input_boxes(self):
        smaller_font = self.get_font(33)
        self.text_color = pygame.Color("#d7fcd4")
        self.messages_text = smaller_font.render("Chat:", True, self.text_color)
        self.message_text = smaller_font.render("Mensaje:", True, self.text_color)
        self.label_font = smaller_font
        font = self.get_font(38)
        self.host_input_box = InputBox(0, 0, 300, 40, font, text="")
        self.name_input_box = InputBox(0, 0, 300, 40, smaller_font)
        self.password_input_box = InputBox(0, 0, 300, 40, smaller_font)
        self.max_players_input_box = InputBox(0, 0, 300, 40, smaller_font)

        self.join_player_input_box = InputBox(0, 0, 300, 40, smaller_font)
        self.join_password_input_box = InputBox(0, 0, 300, 40, smaller_font)

        self.message_input_box = InputBox(0, 0, 300, 40, smaller_font)

    def update_animation(self, delta_time):
        # Aumenta el ángulo de las imágenes giratorias (animación de los lados)
        self.angulo_izquierda = (self.angulo_izquierda + 50 * delta_time) % 360
        self.angulo_derecha = (self.angulo_derecha + 50 * delta_time) % 360

        # Mueve los créditos hacia la izquierda
        self.credits_x_pos -= 100 * delta_time
        # Si los créditos salen de la pantalla, reinicia la posición (efecto bucle infinito)
        if self.credits_x_pos < -self.credits_surface.get_width():
            self.credits_x_pos = self.SCREEN_WIDTH


    def draw_background(self):
        # Dibuja la imagen de fondo en toda la pantalla
        self.SCREEN.blit(self.fondo_img, (0, 0))

        # Rota la animación de la izquierda según el ángulo actual
        rotada_izquierda = pygame.transform.rotate(self.animacion_fondo_img, self.angulo_izquierda)
        rect_izquierda = rotada_izquierda.get_rect(center=self.pos_izquierda)  # Mantiene centrada la animación
        self.SCREEN.blit(rotada_izquierda, rect_izquierda)  # Dibuja la animación girada en la pantalla

        # Rota la animación de la derecha según el ángulo actual
        rotada_derecha = pygame.transform.rotate(self.animacion_fondo_img, self.angulo_derecha)
        rect_derecha = rotada_derecha.get_rect(center=self.pos_derecha)  # Mantiene centrada la animación
        self.SCREEN.blit(rotada_derecha, rect_derecha)  # Dibuja la animación girada en la pantalla

        # Dibuja los créditos que se mueven en la parte inferior
        self.SCREEN.blit(self.credits_surface, (self.credits_x_pos, self.credits_y_pos))


    def draw_main_menu(self):
        # Calcula la posición del título (centrado arriba de la pantalla)
        title_rect = self.titulo_img.get_rect(center=(self.SCREEN_WIDTH//2, int(self.SCREEN_HEIGHT*0.25)))
        self.SCREEN.blit(self.titulo_img, title_rect)  # Dibuja la imagen del título

        # Obtiene la posición actual del mouse
        MENU_MOUSE_POS = pygame.mouse.get_pos()

        # Actualiza los botones principales (Jugar, Reglas, Salir)
        for button in [self.JUGAR_BUTTON, self.REGLAS_BUTTON, self.SALIR_BUTTON]:
            button.check_hover(MENU_MOUSE_POS)  # Revisa si el mouse está encima (hover)
            button.update(self.SCREEN)  # Dibuja el botón en pantalla
        
        return MENU_MOUSE_POS  # Devuelve la posición del mouse para detectar clicks

    def draw_play_menu(self):
        # Obtiene la posición actual del mouse
        MENU_MOUSE_POS = pygame.mouse.get_pos()

        # Actualiza los botones del menú "Jugar" (Unirse, Crear, Volver)
        for button in [self.UNIRSE_BUTTON, self.CREAR_BUTTON, self.PLAY_BACK]:
            button.check_hover(MENU_MOUSE_POS)  # Revisa si el mouse está encima (hover)
            button.update(self.SCREEN)  # Dibuja el botón en pantalla

        return MENU_MOUSE_POS  # Devuelve la posición del mouse para detectar clicks

    def draw_join_menu(self):
        # Actualizar la lista de servidores automáticamente cada _discover_interval ms
        now = pygame.time.get_ticks()
        if now - self._last_discover_time > self._discover_interval:
            self._last_discover_time = now
            self.network_manager.discoverServers()
        self.servers = self.network_manager.servers
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        smaller_font = self.get_font(self._sw(20))

        # Usamos exactamente el mismo recuadro y posición que draw_create_menu (relativo)
        box_width = self._sw(600)
        box_height = self._sh(280)
        box_x = self.SCREEN_WIDTH // 2 - box_width // 2
        box_y = self.SCREEN_HEIGHT // 2 - box_height // 2 + self._sh(60)

        # Dibuja el mismo recuadro usando cuadro.png escalado
        cuadro_surf = pygame.transform.scale(self.cuadro_img, (box_width, box_height))
        self.SCREEN.blit(cuadro_surf, (box_x, box_y))

        # --- Layout centrado (labels + inputs como en crear) ---
        label_w = self._sw(180)
        input_w = self._sw(360)
        gap = self._sw(12)
        content_total_w = label_w + gap + input_w
        base_x = box_x + (box_width - content_total_w) // 2 + self._sw(20)
        label_x = base_x
        input_x = base_x + label_w + gap

        # Dibuja el rectángulo para el campo de Nombre de la sala (menos ancho y más delgado)
        # Dejamos espacio a la derecha para la flecha del dropdown
        arrow_w = self._sw(36)
        rectNameServer = pygame.Rect(input_x, box_y + self._sh(43), input_w - self._sw(160) - arrow_w, self._sh(36))
        # Rect de la flecha dropdown (a la derecha del campo)
        self.server_arrow_rect = pygame.Rect(rectNameServer.right + self._sw(4), box_y + self._sh(43), arrow_w, self._sh(36))
        self.is_hovered = rectNameServer.collidepoint(MENU_MOUSE_POS) or self.server_arrow_rect.collidepoint(MENU_MOUSE_POS)

        # Estado visual: seleccionado > hover > predeterminado (blanco)
        if getattr(self, "isSeletedServer", False):
            border_color = (46, 204, 113)   # verde cuando está seleccionado
            fill_color = (240, 255, 240)    # fondo suave cuando seleccionado (opcional)
        elif self.is_hovered:
            border_color = (150, 150, 150)  # gris al pasar el mouse
            fill_color = (255, 255, 255)    # fondo blanco en hover
        else:
            border_color = (200, 200, 200)  # borde gris por defecto
            fill_color = (255, 255, 255)    # FONDO PREDETERMINADO BLANCO

        # dibujar fondo y borde con esquinas ovaladas
        pygame.draw.rect(self.SCREEN, fill_color, rectNameServer, border_radius=12)
        pygame.draw.rect(self.SCREEN, border_color, rectNameServer, 2, border_radius=12)

        # Dibujar botón de flecha dropdown
        arrow_hover = self.server_arrow_rect.collidepoint(MENU_MOUSE_POS)
        arrow_fill = (220, 220, 220) if arrow_hover or self.server_dropdown_open else (240, 240, 240)
        arrow_border = (100, 100, 100) if arrow_hover or self.server_dropdown_open else (180, 180, 180)
        pygame.draw.rect(self.SCREEN, arrow_fill, self.server_arrow_rect, border_radius=8)
        pygame.draw.rect(self.SCREEN, arrow_border, self.server_arrow_rect, 2, border_radius=8)
        # Dibujar triángulo (flecha hacia abajo o arriba)
        arrow_cx = self.server_arrow_rect.centerx
        arrow_cy = self.server_arrow_rect.centery
        arrow_size = 8
        if self.server_dropdown_open:
            # Flecha hacia arriba
            pts = [(arrow_cx - arrow_size, arrow_cy + 3), (arrow_cx + arrow_size, arrow_cy + 3), (arrow_cx, arrow_cy - arrow_size + 3)]
        else:
            # Flecha hacia abajo
            pts = [(arrow_cx - arrow_size, arrow_cy - 3), (arrow_cx + arrow_size, arrow_cy - 3), (arrow_cx, arrow_cy + arrow_size - 3)]
        pygame.draw.polygon(self.SCREEN, (80, 80, 80), pts)

        # Información del servidor seleccionado (centrada sobre los inputs)
        # Verificar que el servidor seleccionado siga en la lista
        if self.selectedServer:
            still_exists = any(
                s.get('name') == self.selectedServer.get('name') and s.get('ip') == self.selectedServer.get('ip')
                for s in self.servers
            ) if self.servers else False
            if not still_exists and self.servers:
                self.selectedServer = self.servers[0]
                self.isSeletedServer = True
            elif not still_exists:
                self.selectedServer = None
                self.isSeletedServer = False

        # Mostrar información del servidor en el campo de texto
        # Actualizar datos del servidor seleccionado desde la lista más reciente
        if self.selectedServer and self.servers:
            for s in self.servers:
                if s.get('name') == self.selectedServer.get('name') and s.get('ip') == self.selectedServer.get('ip'):
                    self.selectedServer['currentPlayers'] = s.get('currentPlayers', self.selectedServer.get('currentPlayers', 0))
                    break

        if self.selectedServer:
            server_text = smaller_font.render(f"{self.selectedServer['name']}: Jugadores {self.selectedServer['currentPlayers']}/{self.selectedServer['max_players']}", True, (0, 0, 0))
            server_rect = server_text.get_rect(center=rectNameServer.center)
            self.SCREEN.blit(server_text, server_rect)
        elif self.servers:
            server_text = smaller_font.render(f"{self.servers[0]['name']}: Jugadores {self.servers[0]['currentPlayers']}/{self.servers[0]['max_players']}", True, (0, 0, 0))
            server_rect = server_text.get_rect(center=rectNameServer.center)
            self.SCREEN.blit(server_text, server_rect)
        else:
            noServers = smaller_font.render("No hay Salas :( ", True, (0,0,0))
            noServers_rect = noServers.get_rect(center=rectNameServer.center)
            self.SCREEN.blit(noServers, noServers_rect)

        # --- MODAL DE LISTA DE SERVIDORES ---
        if self.server_dropdown_open and self.servers:
            self._draw_server_dropdown_modal(box_x, box_y, box_width, input_x, rectNameServer, smaller_font, MENU_MOUSE_POS)

        now = pygame.time.get_ticks()
        # mover a la derecha respecto al centro del input
        msg_x = input_x + input_w // 2 + self._sw(70)
        msg_y = box_y + self._sh(150)

        # Normalizar respuesta y comprobar timeouts
        resp = (getattr(self, "response", "") or "").strip()
        resp_l = resp.lower()



        show = False
        color = (255, 255, 255)
        linea1 = linea2 = None

        if (getattr(self, "wrong_password_until", 0) > now) or ("wrong" in resp_l) or ("contrase" in resp_l):
            linea1 = "Contraseña"
            linea2 = "Incorrecta"
            show = True
        elif (getattr(self, "fullserver_until", 0) > now) or ("full" in resp_l) or ("sala llena" in resp_l) or ("llena" in resp_l):
            linea1 = "Sala"
            linea2 = "Llena"
            show = True
        elif (getattr(self, "no_server_until", 0) > now) or ("no ha seleccionado" in resp_l) or ("seleccion" in resp_l) or ("no server" in resp_l):
            linea1 = "Seleccione"
            linea2 = "un servidor"
            show = True

        if show and linea1:
            surf1 = smaller_font.render(linea1, True, color)
            surf2 = smaller_font.render(linea2, True, color)
            rect1 = surf1.get_rect(center=(msg_x, msg_y))
            rect2 = surf2.get_rect(center=(msg_x, msg_y + surf1.get_height() + 4))

            # Sin fondo: sólo dibujar los textos (no se sobreescribe nada detrás)
            self.SCREEN.blit(surf1, rect1.topleft)
            self.SCREEN.blit(surf2, rect2.topleft)
        # Etiqueta para el campo de Nombre Sala (alineada a la izquierda del input, pero todo centrado)
        ip_label = smaller_font.render("Nombre Sala:", True, "#d7fcd4")
        ip_label_rect = ip_label.get_rect()
        ip_label_rect.centery = box_y + self._sh(35) + self._sh(24)
        ip_label_rect.right = input_x - self._sw(8)
        self.SCREEN.blit(ip_label, ip_label_rect)

        # Etiqueta y caja para Nombre Jugador (nuevo) centradas en el bloque
        player_label = smaller_font.render("Nombre del Jugador:", True, "#d7fcd4")
        player_label_rect = player_label.get_rect()
        player_label_rect.right = input_x - self._sw(8)
        player_label_rect.centery = box_y + self._sh(110)
        self.SCREEN.blit(player_label, player_label_rect)
        self.join_player_input_box.draw(self.SCREEN)
        self.join_player_input_box.rect.topleft = (input_x, box_y + self._sh(90))
        self.join_player_input_box.rect.size = (input_w, self._sh(40))

        # Etiqueta y caja para Contraseña centradas en el bloque
        pw_label = smaller_font.render("Contraseña:", True, "#d7fcd4")
        pw_label_rect = pw_label.get_rect()
        pw_label_rect.right = input_x - self._sw(8)
        pw_label_rect.centery = box_y + self._sh(160)
        self.SCREEN.blit(pw_label, pw_label_rect)
        self.join_password_input_box.draw(self.SCREEN)
        self.join_password_input_box.rect.topleft = (input_x, box_y + self._sh(140))
        self.join_password_input_box.rect.size = (input_w, self._sh(40))

        # Mantener la posición del botón de conectar centrada respecto al bloque (sin cambiar lógica)
        if hasattr(self, "JOIN_IP_BUTTON") and self.JOIN_IP_BUTTON:
            # Colocar el botón justo debajo del campo de contraseña
            gap = self._sh(12)
            btn_w, btn_h = self.JOIN_IP_BUTTON.rect.size
            pwd_top = box_y + self._sh(140)
            pwd_h = self._sh(40)
            btn_x = rectNameServer.centerx
            btn_y = pwd_top + pwd_h + gap + btn_h // 2
            self.JOIN_IP_BUTTON.rect.center = (btn_x - self._sw(30), btn_y)
            # mantener x_pos/y_pos usados por la lógica de dibujo si existen
            try:
                self.JOIN_IP_BUTTON.x_pos, self.JOIN_IP_BUTTON.y_pos = self.JOIN_IP_BUTTON.rect.center
            except Exception:
                pass
            self.JOIN_IP_BUTTON.check_hover(MENU_MOUSE_POS)
            self.JOIN_IP_BUTTON.update(self.SCREEN)
       # Botón actualizar y volver (mantener sus posiciones relativas, sólo dibujados)
        self.JOIN_REFREHS_BUTTON.check_hover(MENU_MOUSE_POS)
        self.JOIN_REFREHS_BUTTON.update(self.SCREEN)

        # Botón volver
        self.JOIN_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
        self.JOIN_BACK_BUTTON.update(self.SCREEN)

        return MENU_MOUSE_POS

    def _draw_server_dropdown_modal(self, box_x, box_y, box_width, input_x, rectNameServer, font, mouse_pos):
        """Dibuja el modal desplegable con la lista de servidores disponibles."""
        modal_w = rectNameServer.width + self._sw(40)
        modal_h = min(len(self.servers) * self._sh(40) + self._sh(16), self._sh(200))
        modal_x = rectNameServer.x
        modal_y = rectNameServer.bottom + self._sh(4)

        # Fondo del modal con cuadro.png escalado
        cuadro_modal = pygame.transform.scale(self.cuadro_img, (modal_w, modal_h))
        self.SCREEN.blit(cuadro_modal, (modal_x, modal_y))

        # Borde del modal
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(self.SCREEN, (180, 180, 180), modal_rect, 2, border_radius=12)

        # Guardar rects de cada servidor para detectar clicks
        self._server_item_rects = []

        # Clip para que los items no salgan del modal
        clip_prev = self.SCREEN.get_clip()
        self.SCREEN.set_clip(modal_rect)

        for i, server in enumerate(self.servers):
            item_y = modal_y + self._sh(8) + i * self._sh(40) - self.server_dropdown_scroll
            item_rect = pygame.Rect(modal_x + self._sw(4), item_y, modal_w - self._sw(8), self._sh(36))

            if item_y + self._sh(36) < modal_y or item_y > modal_y + modal_h:
                self._server_item_rects.append(None)
                continue

            is_hover = item_rect.collidepoint(mouse_pos)
            is_selected = (self.selectedServer is not None and
                          self.selectedServer.get('name') == server.get('name') and
                          self.selectedServer.get('ip') == server.get('ip'))

            if is_selected:
                pygame.draw.rect(self.SCREEN, (200, 240, 200), item_rect, border_radius=8)
                pygame.draw.rect(self.SCREEN, (46, 204, 113), item_rect, 2, border_radius=8)
            elif is_hover:
                pygame.draw.rect(self.SCREEN, (230, 230, 230), item_rect, border_radius=8)
                pygame.draw.rect(self.SCREEN, (150, 150, 150), item_rect, 1, border_radius=8)
            else:
                pygame.draw.rect(self.SCREEN, (255, 255, 255), item_rect, border_radius=8)

            server_label = f"{server['name']}: {server['currentPlayers']}/{server['max_players']}"
            text_surf = font.render(server_label, True, (0, 0, 0))
            text_rect = text_surf.get_rect(midleft=(item_rect.x + self._sw(10), item_rect.centery))
            self.SCREEN.blit(text_surf, text_rect)

            self._server_item_rects.append(item_rect)

        self.SCREEN.set_clip(clip_prev)

    def draw_create_menu(self):
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        box_width = self._sw(700)
        box_height = self._sh(400)
        box_x = (self.SCREEN_WIDTH // 2 - box_width // 2)
        box_y = self.SCREEN_HEIGHT // 2 - box_height // 2 
    
        cuadro_surf = pygame.transform.scale(self.cuadro_img, (box_width, box_height))
        self.SCREEN.blit(cuadro_surf, (box_x, box_y))

        # Inputs y labels alineados y centrados
        campos = [
            ("Nombre de la Sala:", self.host_input_box),
            ("Nombre del Jugador:", self.name_input_box),
            ("Contraseña:", self.password_input_box),
            ("Cantidad de Jugadores:", self.max_players_input_box)
        ]
        total_inputs = len(campos)
        input_w, input_h = self._sw(250), self._sh(40)
        label_gap = self._sw(10)
        vertical_gap = self._sh(10)
        total_height = total_inputs * input_h + (total_inputs - 1) * vertical_gap
        start_y = box_y + (box_height - total_height) // 2

        # Usar una fuente local más grande solo para las etiquetas de "Crear sala"
        create_label_font = self.get_font(self._sw(27))
        for idx, (label_text, input_box) in enumerate(campos):
            input_x = box_x + (box_width - input_w) // 2 + self._sw(90)
            input_y = start_y + idx * (input_h + vertical_gap) - self._sh(35)
            label_surf = create_label_font.render(label_text, True, self.text_color)
            label_rect = label_surf.get_rect()
            label_rect.centery = input_y + input_h // 2
            label_rect.right = input_x - label_gap
            input_box.rect.topleft = (input_x, input_y)
            input_box.rect.size = (input_w, input_h)
            self.SCREEN.blit(label_surf, label_rect)
            input_box.draw(self.SCREEN)

        # Botón "Crear partida" (debajo de los inputs)
        btn_x = box_x + box_width // 2
        btn_y = start_y + total_height + self._sh(20)
        self.CREATE_GAME_BUTTON.x_pos, self.CREATE_GAME_BUTTON.y_pos = btn_x, btn_y
        try:
            self.CREATE_GAME_BUTTON.rect.center = (btn_x, btn_y)
        except Exception:
            pass
        self.CREATE_GAME_BUTTON.check_hover(MENU_MOUSE_POS)
        self.CREATE_GAME_BUTTON.update(self.SCREEN)

        # Botón "Volver" (debajo del cuadro de creación de sala)
        back_x = box_x + box_width // 2
        back_y = box_y + box_height + self._sh(20)
        self.CREATE_BACK_BUTTON.x_pos, self.CREATE_BACK_BUTTON.y_pos = back_x, back_y
        try:
            self.CREATE_BACK_BUTTON.rect.center = (back_x, back_y)
        except Exception:
            pass
        self.CREATE_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
        self.CREATE_BACK_BUTTON.update(self.SCREEN)

        return MENU_MOUSE_POS
    def draw_lobby(self):
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        smaller_font = self.get_font(self._sw(20))

        # Tamaño y posición del recuadro (centrado, relativo)
        box_width = self._sw(750)
        box_height = self._sh(350)
        box_x = (self.SCREEN_WIDTH - box_width) // 2
        box_y = (self.SCREEN_HEIGHT - box_height) // 2 + self._sh(20)

        # Dibujar fondo del recuadro
        lobby_h = box_height + self._sh(80)
        cuadro_surf = pygame.transform.scale(self.cuadro_img, (box_width, lobby_h))
        self.SCREEN.blit(cuadro_surf, (box_x - self._sw(30), box_y - self._sh(20)))

        # Área de chat (centrada en el recuadro)
        padding = self._sw(24)
        inner_w = box_width - padding * 2
        chat_w = int(inner_w * 0.45)
        chat_h = self._sh(120)

        # Desplazamiento extra para bajar chat e inputs un poco más abajo del cuadro
        extra_offset = self._sh(30)
        chat_rect = pygame.Rect(box_x + (box_width - chat_w) // 2, box_y + self._sh(52) + extra_offset, chat_w, chat_h)
        # Chat con esquinas ovaladas
        pygame.draw.rect(self.SCREEN, (255, 255, 255), chat_rect, border_radius=12)
        pygame.draw.rect(self.SCREEN, (180, 180, 180), chat_rect, 2, border_radius=12)
        # Mostrar últimos mensajes dentro del chat
        y_offset = chat_rect.y + self._sh(8)
        with self.chatLock:
            recentMsg = list(self.network_manager.messagesServer)[-6:]
        for msg in recentMsg:
            rendered = smaller_font.render(msg, True, (0, 0, 0))
            if rendered.get_width() > chat_rect.w - self._sw(14):
                max_chars = max(8, int(len(msg) * (chat_rect.w - self._sw(14)) / max(1, rendered.get_width())) - 3)
                msg = msg[:max_chars] + "..."
                rendered = smaller_font.render(msg, True, (0, 0, 0))
            self.SCREEN.blit(rendered, (chat_rect.x + self._sw(8), y_offset))
            y_offset += rendered.get_height() + self._sh(6)

        # -------------------------
        # Texto de servidor y cantidad de jugadores:
        if getattr(self.network_manager, "currentServer", None):
            server_text = f"Sala: {self.network_manager.currentServer.get('name','')}  Jugadores: {self.network_manager.currentServer.get('currentPlayers',0)}/{self.network_manager.currentServer.get('max_players',0)}"
        elif getattr(self, "selectedServer", None):
            server_text = f"Conectado a: {self.selectedServer.get('name','')}  Jugadores: {self.selectedServer.get('currentPlayers',0)}/{self.selectedServer.get('max_players',0)}"
        else:
            server_text = "Lobby"
        server_font = self.get_font(self._sw(28))
        server_surf = server_font.render(server_text, True, "#d7fcd4")
        server_rect = server_surf.get_rect(midbottom=(chat_rect.centerx, chat_rect.top - self._sh(6)))
        self.SCREEN.blit(server_surf, server_rect)
        # -------------------------

        # Caja para escribir mensaje (debajo del chat, centrada)
        row_h = self._sh(44)
        input_w = min(self._sw(360), inner_w - self._sw(40)) - self._sw(80)
        msg_box_x = chat_rect.x
        msg_box_y = chat_rect.bottom + self._sh(18)
        self.message_input_box.rect.topleft = (msg_box_x, msg_box_y)
        self.message_input_box.rect.size = (input_w, row_h)
        self.message_input_box.draw(self.SCREEN)

        # Etiqueta "CHAT:" a la izquierda del recuadro de chat (alineada verticalmente)
        chat_label = self.messages_text  # creado en init_input_boxes
        chat_label_pos = (chat_rect.left - chat_label.get_width() - self._sw(12), chat_rect.centery - chat_label.get_height() // 2)
        # Dibujar sólo la etiqueta "CHAT:" (sin duplicar el texto del servidor)
        self.SCREEN.blit(chat_label, chat_label_pos)

        # Etiqueta "Mensaje:" pegada al lado IZQUIERDO del input de mensaje (alineada verticalmente)
        message_label = self.message_text  # creado en init_input_boxes
        msg_label_pos = (self.message_input_box.rect.left - message_label.get_width() - self._sw(12), self.message_input_box.rect.centery - message_label.get_height() // 2)
        self.SCREEN.blit(message_label, msg_label_pos)

        # Botón enviar mensaje: a la derecha del input de mensaje
        self.SEND_MS_BUTTON.rect.center = (self.message_input_box.rect.right + max(self._sw(48), self.SEND_MS_BUTTON.rect.width//2 + self._sw(10)),
                                        self.message_input_box.rect.centery)
        self.SEND_MS_BUTTON.check_hover(MENU_MOUSE_POS)
        self.SEND_MS_BUTTON.update(self.SCREEN)

        # ---------------------------------------------------------------------
        # CONTROL DE VISIBILIDAD/ACTIVACIÓN DEL BOTÓN PLAY (evitar rectos fantasmas)
        play_active = False
        if getattr(self.network_manager, "is_host", False):
            play_active = self.network_manager.canStartGame()
        elif getattr(self, "playGamePlayer", False) and not self.countdown_active:
            # Solo mostrar botón a no-host si NO está activo el conteo regresivo
            play_active = True

        center_x = self.SCREEN_WIDTH // 2
        offset = self._sw(120)
        btn_y = box_y + lobby_h - self._sh(36)

        if play_active:
            self.PLAY_GAME_BUTTON.rect.center = (center_x - offset, btn_y)
            self.PLAY_GAME_BUTTON.check_hover(MENU_MOUSE_POS)
            self.PLAY_GAME_BUTTON.update(self.SCREEN)
        else:
            try:
                self.PLAY_GAME_BUTTON.rect.topleft = (-9999, -9999)
            except Exception:
                pass

        # Ocultar botón de volver durante el conteo regresivo
        if not self.countdown_active:
            self.LOBBY_BACK_BUTTON.rect.center = (center_x + offset, btn_y)
            self.LOBBY_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
            self.LOBBY_BACK_BUTTON.update(self.SCREEN)
        else:
            try:
                self.LOBBY_BACK_BUTTON.rect.topleft = (-9999, -9999)
            except Exception:
                pass
        # ---------------------------------------------------------------------

        # Comprobar inicio de UI2 desde mensajes recibidos
        result = self.process_received_messages()
        if result == "launch_ui2" and not self.network_manager.is_host:
            # Jugadores no-host: NO mostrar botón, solo activar conteo regresivo
            # (el conteo ya se activa en process_received_messages al detectar START_GAME)
            pass
        elif result == "launch_ui2":
            self.playGamePlayer = True

        # --- CONTEO REGRESIVO PARA JUGADORES NO-HOST ---
        if self.countdown_active and not self.network_manager.is_host:
            elapsed = (pygame.time.get_ticks() - self.countdown_start_time) / 1000.0
            remaining = max(0, self.countdown_duration - elapsed)
            # Mostrar 5, 4, 3, 2, 1 y luego "YA!"
            count_num = int(remaining) if remaining > 0 else 0

            # Overlay semitransparente
            overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.SCREEN.blit(overlay, (0, 0))

            # Texto del conteo
            countdown_font = self.get_font(72)
            label_font = self.get_font(36)

            label_surf = label_font.render("Comenzando en", True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=(self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 60))
            self.SCREEN.blit(label_surf, label_rect)

            if count_num > 0:
                num_surf = countdown_font.render(str(count_num), True, (46, 204, 113))
            else:
                num_surf = countdown_font.render("YA!", True, (46, 204, 113))
            num_rect = num_surf.get_rect(center=(self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 + 20))
            self.SCREEN.blit(num_surf, num_rect)

            # Cuando termina el conteo, lanzar ui2 directamente
            if remaining <= 0:
                self.countdown_active = False
                self._launch_ui2_flag = True

        return MENU_MOUSE_POS

    def options(self):
        pygame.display.set_caption("Opciones")
        # Texto completo de reglas (se puede ajustar)
        game_rules = """Rummy 500
Objetivo: Ser el último jugador con menos de 500 puntos.

Jugadores: 2 - 13

Mazo: 52 cartas + 1 Joker.

Cómo ganar: El último jugador en acumular menos de 500 puntos gana la partida.
Cómo perder: El primer jugador en alcanzar o superar los 500 puntos es eliminado.
Combinaciones:
• Trío: Tres cartas del mismo valor (ej: QC, QD, QP).
• Seguidilla: Cuatro cartas consecutivas del mismo palo (ej: 7T, 8T, 9T, 10T).

Rondas de Juego:
1. Trío y Seguidilla
2. Dos Seguidillas
3. Tres Tríos
4. Una Seguidilla y Dos Tríos (Ronda Completa): Para finalizar esta ronda, el jugador debe descartar las diez cartas (la seguidilla de cuatro y los dos tríos) en un solo turno.

Puntuación:
• Cartas 2 - 9: 5 puntos
• Cartas 10 - K: 10 puntos
• As: 15 puntos
• Joker: 25 puntos

Desarrollo del Juego:
1. Inicio: Cada jugador recibe 10 cartas. Se coloca una carta boca arriba del mazo en el centro de la mesa para iniciar el descarte. Se designa un jugador como MANO.

2. Turno del MANO: Para la siguiente ronda, el rol de MANO pasa al jugador a la izquierda del MANO actual.


3. Primera Toma de la Carta Central: Solo el jugador MANO tiene la primera oportunidad de tomar la carta boca arriba del centro. Si decide tomarla, debe descartar una carta de su mano para mantener un total de 10 cartas. Si el MANO no toma la carta central, se pasa a la siguiente fase de toma.
4. Segunda Oportunidad de Toma de la Carta Central: Si el MANO no tomó la carta central, los demás jugadores, en orden hacia la izquierda del MANO, tienen la oportunidad de tomarla. El primer jugador que la tome debe robar una carta adicional del mazo como penalización, quedando con 12 cartas. Si nadie toma la carta central en esta segunda oportunidad, la carta se QUEMA y se descarta, quedando fuera de juego.
5. Turno Regular del Jugador: Después de la fase de toma de la carta central (haya sido tomada o quemada), y durante el resto de su turno, cada jugador puede realizar una de las siguientes acciones:
o Tomar la carta superior del mazo boca abajo (solo si no agarró la carta boca arriba o si agarra como penalización).
o Bajarse: Mostrar sobre la mesa las combinaciones de cartas requeridas para la ronda actual (tríos o seguidillas). Se puede usar un Joker para completar una combinación. Un Joker ya bajado puede ser reemplazado por la carta que representa y utilizado en otra combinación propia.
o Agregar cartas: Añadir cartas válidas a sus propias combinaciones ya bajadas (antes de descartar).
o Descartar: Colocar una carta boca arriba en el centro de la mesa para finalizar su turno.
6. Fin de la Ronda: Una ronda termina cuando un jugador se queda sin cartas al bajar todas sus combinaciones requeridas (y descartar si es necesario). El jugador que se quedó sin cartas será el primero en actuar en la siguiente ronda.
7. Puntuación de la Ronda: Los jugadores que no lograron bajarse suman los puntos de las cartas que aún tienen en su mano.
8. Fin de la Partida: El juego continúa a lo largo de las cuatro rondas. El ganador es el jugador con la menor puntuación total al final de las cuatro rondas, o el último jugador que no haya alcanzado o superado los 500 puntos."""
        # crear la caja de reglas dentro de Options (usa la clase anidada)
        box_w, box_h = 600 , 300
        box_x = self.SCREEN_WIDTH // 2 - box_w // 2
        box_y = 140

        rules_box = self.RulesTextBox(box_x + 20, box_y + 20, box_w - 40, box_h - 40, self.get_font(30), game_rules)

        # Crear botón VOLVER una sola vez y posicionarlo dentro del contenedor
        options_back = Button(
            image=self.volver_img,                    # usar asset de botón "volver"
            pos=(self.SCREEN_WIDTH//2, box_y + box_h + 40),
            text_input="",                            # sin texto (solo imagen)
            font=self.get_font(50),
            base_color="White",
            hovering_color="Green",
            size=(250, 110)                            # tamaño del botón (ajusta si es necesario)
        )

        while True:  # Bucle principal de la pantalla de opciones
            delta_time = self.clock.tick(60) / 1000.0  # Controla FPS y calcula delta_time
            self.update_animation(delta_time)  # Actualiza la animación de fondo

            # Captura eventos una sola vez y pásalos a la caja de reglas
            events = pygame.event.get()

            # Manejo eventos globales
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                #Cuando la ventana cambia de tamaño, volvemos a calcular la posición y el tamaño de la caja de reglas y del botón "volver" para que todo se adapte.
                elif event.type == pygame.VIDEORESIZE:
                    self.SCREEN_WIDTH, self.SCREEN_HEIGHT = event.size
                    self.SCREEN = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
                    # Reajustamos las posiciones y tamaños
                    box_w, box_h = int(self.SCREEN_WIDTH * 0.7), int(self.SCREEN_HEIGHT * 0.6)
                    box_x = self.SCREEN_WIDTH // 2 - box_w // 2
                    box_y = self.SCREEN_HEIGHT // 2 - box_h // 2
                    rules_box.rect.topleft = (box_x + 20, box_y + 20)
                    rules_box._wrap_lines()
                    options_back.x_pos = self.SCREEN_WIDTH // 2
                    options_back.y_pos = box_y + box_h + 40

            # Dibuja fondo y contenedor
            self.draw_background()
            # Contenedor centrado (fondo oscuro)
            #self.SCREEN.fill((50, 50, 50), (self.SCREEN_WIDTH//2 - box_w//2, box_y, box_w, box_h))
            # Dibujar contenedor usando cuadro.png escalado en vez de rect gris
            cuadro_surf = pygame.transform.scale(self.cuadro_img, (box_w + 100, box_h + 100))
            self.SCREEN.blit(cuadro_surf, (self.SCREEN_WIDTH//2 - box_w//2 - 60, box_y - 50))

            # Título
            options_text = self.get_font(45).render("Reglas de Rummy 500", True, "White")
            options_rect = options_text.get_rect(center=(self.SCREEN_WIDTH//2, 100))
            # Fondo gris detrás del texto (margen horizontal y vertical)
            bg_rect = options_rect.inflate(40, 18)  # ajusta el padding si quieres más/menos espacio
            pygame.draw.rect(self.SCREEN, (80, 80, 80), bg_rect, border_radius=6)
            
            self.SCREEN.blit(options_text, options_rect)

            # Actualizar y dibujar la caja de reglas (usa clipping para que el texto no salga)
            rules_box.update(events)
            rules_box.draw(self.SCREEN)

            # Botón VOLVER
            mouse_pos = pygame.mouse.get_pos()
            options_back.check_hover(mouse_pos)
            options_back.update(self.SCREEN)

            # detectar click en VOLVER
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if options_back.checkForInput(mouse_pos):
                        return

            pygame.display.update()

    def lanzar_juego_ui2(self):
        import ui2
        #pygame.quit()  # Cierra la ventana actual de Pygame
        ui2.main()     # Lanza el juego principal de ui2.py
        self.SCREEN = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Menu Principal")
    
    def play_click(self):
        self.click_sound.play()
    

    def handle_events(self):

        if not pygame.get_init():
            return False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.VIDEORESIZE:
                self.recalc_layout(event.w, event.h)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                if self.current_screen == "create":
                    if self.crear_partida_img_rect.collidepoint(mouse_pos):
                        nameSala = self.host_input_box.text
                        nameHost = self.name_input_box.text
                        password = self.password_input_box.text
                        if nameHost == "":
                            nameHost = "Host"
                        if nameSala == "":
                            nameSala= "Sala1"
                        try:
                            max_players = int(self.max_players_input_box.text)
                        except:
                            max_players = 7
                        exito = self.network_manager.start_server(nameHost, password, max_players,nameSala)
                        print("Servidor creado" if exito else "Error al crear servidor")
                        self.current_screen = "lobby"
            if event.type == pygame.MOUSEBUTTONDOWN:  # Si se hace clic con el mouse
                if self.current_screen == "main":  # Si estamos en el menú principal
                    if self.JUGAR_BUTTON.checkForInput(event.pos):  # Clic en "JUGAR"
                        self.play_click()
                        self.current_screen = "play"  # Cambia a la pantalla de jugar
                    elif self.REGLAS_BUTTON.checkForInput(event.pos):  # Clic en "REGLAS"
                        self.play_click()
                        self.options()  # Abre la pantalla de opciones/reglas
                    elif self.SALIR_BUTTON.checkForInput(event.pos):  # Clic en "SALIR"
                        self.play_click()
                        return False  # Sale del juego

                elif self.current_screen == "play":  # Si estamos en el menú de "jugar"
                    if self.PLAY_BACK.checkForInput(event.pos):  # Botón "volver"
                        self.play_click()
                        self.current_screen = "main"  # Regresa al menú principal
                    elif self.UNIRSE_BUTTON.checkForInput(event.pos):  # Botón "unirse"
                        self.play_click()
                        self.servers = self.network_manager.discoverServers()
                        self.response = ''
                        self.current_screen = "join"  # Cambia a la pantalla de unirse
                    elif self.CREAR_BUTTON.checkForInput(event.pos):  # Botón "crear"
                        self.play_click()
                        self.current_screen = "create"  # Cambia a la pantalla de crear partida

                elif self.current_screen == "join":  # Si estamos en la pantalla de unirse
                    # Click en la flecha del dropdown: abrir/cerrar modal
                    if hasattr(self, 'server_arrow_rect') and self.server_arrow_rect.collidepoint(event.pos):
                        self.server_dropdown_open = not self.server_dropdown_open
                        self.server_dropdown_scroll = 0
                    # Click en un item del modal de servidores
                    elif self.server_dropdown_open and hasattr(self, '_server_item_rects'):
                        clicked_item = False
                        for i, item_rect in enumerate(self._server_item_rects):
                            if item_rect and item_rect.collidepoint(event.pos):
                                self.selectedServer = self.servers[i]
                                self.isSeletedServer = True
                                self.server_dropdown_open = False
                                clicked_item = True
                                print(f"Servidor seleccionado: {self.selectedServer['name']}")
                                break
                        if not clicked_item:
                            # Click fuera del modal: cerrarlo
                            self.server_dropdown_open = False
                    # Click en el campo de nombre de sala (sin flecha): también abre el dropdown
                    elif event.button == 1 and self.is_hovered and not self.server_dropdown_open:
                        if self.servers:
                            self.server_dropdown_open = True
                            self.server_dropdown_scroll = 0
                    # Cerrar dropdown si se hace click en cualquier otro lado
                    elif self.server_dropdown_open:
                        self.server_dropdown_open = False

                    if self.JOIN_BACK_BUTTON.checkForInput(event.pos):  # Botón "volver"
                        self.play_click()
                        self.current_screen = "play"  # Regresa al menú de jugar
                        self.response = ''
                        self.server_dropdown_open = False
                    elif self.JOIN_REFREHS_BUTTON.checkForInput(event.pos): # Botón Actualizar
                        self.play_click()
                        self.servers = self.network_manager.discoverServers()
                        self.response = ''
                        self.server_dropdown_open = False
                    elif self.JOIN_IP_BUTTON.checkForInput(event.pos):  # Botón "conectar"
                        password = self.join_password_input_box.text  # Obtiene la contraseña
                        # Usar selectedServer si existe, si no usar el primero
                        target_server = self.selectedServer if self.selectedServer else (self.servers[0] if self.servers else None)
                        if target_server:
                            target_server['password'] = password
                            if self.join_player_input_box.text != "":
                                playerName = self.join_player_input_box.text
                            else:
                                playerName = f"Jugador {target_server['currentPlayers']}"
                            target_server['playerName'] = playerName
                            pygame.display.update()
                            print(f"Esto esta en el Server {self.servers}")
                        if self.selectedServer:
                            acep, resp = self.network_manager.connectToServer(self.selectedServer)
                            if acep:
                                self.selectedServer['currentPlayers'] += 1
                                print(f"Info de connectToServer  {(acep,resp)}")
                                print("ClaveCorrecta.... Probando")
                                self.current_screen = "lobby"
                            elif acep==False:
                                resp_norm = (resp or "").strip().lower()
                                if "contrase" in resp_norm or "wrong" in resp_norm:
                                    self.response = "wrongPassword"
                                    self.wrong_password_until = pygame.time.get_ticks() + 2000
                                    print("Contraseña incorrecta")
                                elif "full" in resp_norm or "llena" in resp_norm or "servidor" in resp_norm:
                                    self.response = "fullserver"
                                    self.fullserver_until = pygame.time.get_ticks() + 2000
                                    print("La sala está llena (detectada por keyword)")
                                else:
                                    self.response = resp or ""
                                    self.fullserver_until = pygame.time.get_ticks() + 2000
                                    print(f"Respuesta no esperada al conectar: {resp}")
                        else:
                            self.response = "No ha seleccionado una sala"
                            self.no_server_until = pygame.time.get_ticks() + 2000
                            print("No ha seleccionado una sala")

                elif self.current_screen == "create":  # Si estamos en la pantalla de crear
                    if self.CREATE_BACK_BUTTON.checkForInput(event.pos):  # Botón "volver"
                        self.current_screen = "play"  # Regresa al menú de jugar
                    elif self.CREATE_GAME_BUTTON.checkForInput(event.pos):  # Botón "crear partida"
                        nameSala= self.host_input_box.text  # Nombre de la sala
                        nameHost = self.name_input_box.text  # Nombre de la partida
                        if nameHost == "":
                            nameHost = "Host"
                        if nameSala == "":
                            nameSala= "Sala1"
                        password = self.password_input_box.text  # Contraseña
                        try:
                            max_players = int(self.max_players_input_box.text)  # Convierte jugadores a número
                        except:  # Si no se escribe un número válido
                            max_players = 7  # Valor por defecto
                        # Intenta crear el servidor
                        exito = self.network_manager.start_server(nameHost, password, max_players,nameSala)
                        print("Servidor creado" if exito else "Error al crear servidor")
                        print(self.network_manager.host,self.network_manager.gameName)
                        self.current_screen = "lobby"  # Cambia a la pantalla lobby
                
                elif self.current_screen == "lobby":  # Si estamos en la pantalla de lobby
                    if self.LOBBY_BACK_BUTTON.checkForInput(event.pos):
                        self.current_screen = "play"
                        self.network_manager.connected_players.clear()
                        self.network_manager.stop()
                        self.network_manager.stop_broadcast()
                        
                        if self.selectedServer:
                            self.selectedServer.clear()
                        #    self.selectedServer['currentPlayers'] = len(self.network_manager.connected_players)
                        print(f"Servidor cerrado...")
                    elif self.PLAY_GAME_BUTTON.checkForInput(event.pos):
                        #++++++++++++++++++++++++++++++++++++++++
                        if self.network_manager.is_host:
                            if self.network_manager.canStartGame():
                                # Hay minimo 2 jugadores conectados

                                # Envía la señal a todos los clientes game_started = True
                                self.network_manager.startGame()
                                self.network_manager.stop_broadcast()
                                print("Cerrada la transmision de la informacion del servido. Juego iniciado")

                            else:
                                print("Se necesitan al menos dos jugadores")
                        else:
                            msg = self.network_manager.get_msgStartGame()
                            print(f"Lo que esta en el msg del lobby PLAY_BUTTON {msg}")
                            if msg == "launch_ui2":

                                return "launch_ui2"
                        #+++++++++++++++++++++++++++++++++++++++++
                        return "launch_ui2"  # <-- Indica al main que debe lanzar ui2.py
                    elif self.SEND_MS_BUTTON.checkForInput(event.pos):  # Botón "enviar mensaje"
                        msg = self.message_input_box.text.strip()
                        if msg:
                            # Enviando mensajes del servidor/jugador
                            if self.network_manager.server:
                                formattedMsg = f"{self.network_manager.playerName}: {msg}" 
                                with self.chatLock:
                                    self.network_manager.messagesServer.append(f"Tú: {msg}")
                                    print(f"en la lista de mensajes: {self.messages}")
                                
                                # Transmitiendo a todos los jugadores
                                self.network_manager.broadcast_message(formattedMsg)

                            if self.network_manager.player:
                                success = self.network_manager.sendData(("chat_messages",msg))
                                if success:
                                    formattedMsg = f"Tú: {msg}"
                                    with self.chatLock:
                                        self.network_manager.messagesServer.append(formattedMsg)

                            # Limpiar caja de texto
                            self.message_input_box.text = ""
                            self.message_input_box.txt_surface = self.get_font(20).render("", True, (0,0,0))
                                
                        #self.messages.append(self.message_input_box.text)  # mensaje 
                        print(f" Mensajes: {self.messages}")

            # Scroll en el modal de servidores
            if self.current_screen == "join" and self.server_dropdown_open:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                    max_scroll = max(0, len(self.servers) * 40 - 184)
                    if event.button == 4:
                        self.server_dropdown_scroll = max(0, self.server_dropdown_scroll - 40)
                    elif event.button == 5:
                        self.server_dropdown_scroll = min(max_scroll, self.server_dropdown_scroll + 40)

            # Manejo de inputs de texto dependiendo de la pantalla
            if self.current_screen == "join":  
                self.join_player_input_box.handle_event(event)  # Maneja el nuevo input
                self.join_password_input_box.handle_event(event)  # Campo de contraseña
            elif self.current_screen == "create":
                self.host_input_box.handle_event(event)      # Campo Host (¡agregado!)
                self.name_input_box.handle_event(event)  # Campo de nombre
                self.password_input_box.handle_event(event)  # Campo de contraseña
                self.max_players_input_box.handle_event(event)  # Campo de jugadores
            elif self.current_screen == "lobby":
                # Pasar el evento al input y, si es ENTER mientras está activo, enviar mensaje
                self.message_input_box.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and getattr(self.message_input_box, "active", False):
                    msg = self.message_input_box.text.strip()
                    if msg:
                        if getattr(self.network_manager, "server", False):
                            formattedMsg = f"{self.network_manager.playerName}: {msg}"
                            with self.chatLock:
                                self.network_manager.messagesServer.append(f"Tú: {msg}")
                        try:
                            self.network_manager.broadcast_message(formattedMsg)
                        except Exception:
                            pass
                        if getattr(self.network_manager, "player", False):
                            try:
                                success = self.network_manager.sendData(("chat_messages", msg))
                            except Exception:
                                success = False
                            if success:
                                formattedMsg = f"Tú: {msg}"
                                with self.chatLock:
                                    self.network_manager.messagesServer.append(formattedMsg)
                        # limpiar input
                        self.message_input_box.text = ""
                        self.message_input_box.txt_surface = self.get_font(20).render("", True, (0,0,0))
                        print(f" Mensajes: {self.messages}")
        self.process_received_messages()

        # Verificar si el conteo regresivo terminó y se debe lanzar ui2
        if getattr(self, '_launch_ui2_flag', False):
            self._launch_ui2_flag = False
            return "launch_ui2"

        return True  # Si nada fuerza salida, el loop sigue
    
    def process_received_messages(self):
        """Procesa los mensajes recividos de la red"""
        if hasattr(self.network_manager,'receivedData') and self.network_manager.receivedData:
            with self.network_manager.lock:
                data = self.network_manager.receivedData
                self.network_manager.receivedData = None  # Limpiar despues de procesar

            print(f"Procesando mensaje recibido en Ui.py:")
            if type(data)==dict:
                print(f"TIPO: {data.get("type")}")
            elif type(data)==str:
                print(f"TIPO: CHAT")
            
            # Si es un mensaje para iniciar partida
            if isinstance(data,dict) and data.get("type") == "START_GAME":
                print("Comenzando el juego - activando conteo regresivo")
                if not self.network_manager.is_host:
                    # Jugadores no-host: iniciar conteo regresivo y NO mostrar botón
                    self.countdown_active = True
                    self.countdown_start_time = pygame.time.get_ticks()
                    # No retornar "launch_ui2" aquí; el conteo regresivo se encargará
                    return None
                return "launch_ui2"
                        
            # Si es la lista de jugadores
            if isinstance(data,dict) and data.get("players"):
                print("Recibiendo lista de jugadores")
                players = data.get("players")
                return players

            # Si es un mensaje de chat (string que empieza con "Host:" o "Jugador")
            if isinstance(data, str) and ":" in data:
                with self.chatLock:
                    # Solo agregar si no es un mensaje duplicado del propio usuario
                    if not (data.startswith("Tú:") or (self.network_manager.is_host and data.startswith(f"{self.network_manager.playerName}:"))):
                        self.network_manager.messagesServer.append(data)
                        # Mantener solo los últimos 20 mensajes
                        if len(self.network_manager.messagesServer) > 20:
                            self.network_manager.messagesServer = self.network_manager.messagesServer[-20:]            
                
            elif isinstance(data, tuple):
                # Procesar otros tipos de mensajes estructurados
                pass


    def update(self):
        delta_time = self.clock.tick(60) / 1000.0  
        self.update_animation(delta_time)

        # Dibuja fondo y animaciones
        self.draw_background()

        # Dibuja el título siempre, sin importar el menú
        title_rect = self.titulo_img.get_rect(center=(self.SCREEN_WIDTH//2, int(self.SCREEN_HEIGHT*0.25)))
        self.SCREEN.blit(self.titulo_img, title_rect)

        # --- ACTUALIZAR INPUT BOXES SEGÚN LA PANTALLA ---
        if self.current_screen == "join":  
            #self.ip_input_box.update()
            #-----------------------------
            self.join_player_input_box.update()  # Actualiza el nuevo input
            #-------------------------------
            self.join_password_input_box.update()
        elif self.current_screen == "create":  
            self.host_input_box.update()          
            self.name_input_box.update()
            self.password_input_box.update()
            self.max_players_input_box.update()
        elif self.current_screen == "lobby":  
            #self.messages_input_box.update()
            self.message_input_box.update()

        # --- MANEJO DE CADA PANTALLA ---
        if self.current_screen == "main":  
            mouse_pos = self.draw_main_menu()
            for button in [self.JUGAR_BUTTON, self.REGLAS_BUTTON, self.SALIR_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "play":  
            mouse_pos = self.draw_play_menu()
            for button in [self.UNIRSE_BUTTON, self.CREAR_BUTTON, self.PLAY_BACK]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "join":  
            mouse_pos = self.draw_join_menu()
            for button in [self.JOIN_IP_BUTTON, self.JOIN_REFREHS_BUTTON, self.JOIN_BACK_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "create":  
            mouse_pos = self.draw_create_menu()
            for button in [self.CREATE_GAME_BUTTON, self.CREATE_BACK_BUTTON]:
                button.check_hover(mouse_pos)
        
        elif self.current_screen == "lobby":  
            mouse_pos = self.draw_lobby()
            for button in [self.SEND_MS_BUTTON, self.PLAY_GAME_BUTTON, self.LOBBY_BACK_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "play_game":  
            mouse_pos = self.draw_play_game()
            #for button in [self.SEND_MS_BUTTON, self.PLAY_GAME_BUTTON, self.LOBBY_BACK_BUTTON]:
            #    button.check_hover(mouse_pos)

        pygame.display.update()
        return True

    class RulesTextBox:
        def __init__(self, x, y, w, h, font, text):
            self.rect = pygame.Rect(x, y, w, h)
            self.font = font  # fuente más grande pasada desde options()
            self.text = text
            self.lines = []
            self._wrap_lines()
            self.scroll_offset = 0
            # Interlineado ligeramente mayor para mejorar lectura
            self.line_height = int(self.font.get_height() * 1.35)

        def _wrap_lines(self):
            # Romper en párrafos para insertar líneas vacías entre párrafos
            paragraphs = self.text.split("\n\n")
            wrapped = []
            max_width = self.rect.w - 20
            for para in paragraphs:
                words = para.split()
                if not words:
                    wrapped.append("")  # párrafo vacío
                    continue
                line = words[0]
                for word in words[1:]:
                    test_line = f"{line} {word}"
                    if self.font.size(test_line)[0] > max_width:
                        wrapped.append(line)
                        line = word
                    else:
                        line = test_line
                if line:
                    wrapped.append(line)
                # línea en blanco como separador de párrafos
                wrapped.append("")
            # eliminar último separador si existe
            if wrapped and wrapped[-1] == "":
                wrapped.pop()
            self.lines = wrapped

        def update(self, events):
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.rect.collidepoint(event.pos):
                        if event.button == 4:  # Scroll up
                            self.scroll_offset = max(self.scroll_offset - self.line_height, 0)
                        elif event.button == 5:  # Scroll down
                            max_offset = max(0, len(self.lines) * self.line_height - self.rect.h + 20)
                            self.scroll_offset = min(self.scroll_offset + self.line_height, max_offset)

        def draw(self, screen):
            # Dibujar borde del contenedor
            pygame.draw.rect(screen, (150, 150, 150), self.rect, 2, border_radius=12)
            # Clip para asegurar que el texto no salga del recuadro
            clip_rect = screen.get_clip()
            screen.set_clip(self.rect)
            y = self.rect.y + 10 - self.scroll_offset
            for line in self.lines:
                # Dibujar líneas vacías como espacio extra
                if line == "":
                    y += int(self.line_height * 0.6)
                else:
                    rendered = self.font.render(line, True, (255, 255, 255))
                    if y + rendered.get_height() > self.rect.y and y < self.rect.y + self.rect.h:
                        screen.blit(rendered, (self.rect.x + 10, y))
                    y += self.line_height
                # Si ya pasó el área visible, puede romper antes (ligera optimización)
                if y > self.rect.y + self.rect.h + self.line_height:
                    break
            screen.set_clip(clip_rect)


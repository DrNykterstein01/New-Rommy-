import pygame
import os
import threading
import pickle
import time
from network import NetworkManager
import sys


def resource_path(relative_path):
    """
    Devuelve la ruta absoluta a un recurso (imagen, sonido, fuente...),
    funcionando tanto en desarrollo normal como empaquetado con PyInstaller
    (--onefile o --onedir). Ver la misma función en main.py para más detalle.
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


icon = pygame.image.load(resource_path("assets/icon.png"))
pygame.display.set_icon(icon)
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("RUMMY 500")

# Resolución de referencia para el escalado relativo
REF_WIDTH = 1280
REF_HEIGHT = 720

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
        try:
            self.text = self.font.render(self.text_input, True, pygame.Color(self.base_color))
        except Exception:
            self.text = self.font.render(self.text_input, True, (255,255,255))
        if self.image is not None:
            self.image = pygame.transform.scale(self.original_image, self.current_size)
            self.rect = self.image.get_rect(center=(self.x_pos, self.y_pos))
        else:
            self.rect = pygame.Rect(0, 0, *self.current_size)
            self.rect.center = (self.x_pos, self.y_pos)
        self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))

    def _current_rect(self):
        r = pygame.Rect(0, 0, int(self.current_size[0]), int(self.current_size[1]))
        r.center = (int(self.x_pos), int(self.y_pos))
        return r

    def update(self, screen):
        target_size = [int(self.base_size[0] * (self.scale_factor if self.is_hovering else 1)),
                       int(self.base_size[1] * (self.scale_factor if self.is_hovering else 1))]
        for i in range(2):
            if abs(self.current_size[i] - target_size[i]) > 1:
                self.current_size[i] += (target_size[i] - self.current_size[i]) * 0.2
            else:
                self.current_size[i] = target_size[i]

        if self.original_image is not None:
            scaled_image = pygame.transform.scale(self.original_image, [int(x) for x in self.current_size])
            scaled_rect = scaled_image.get_rect(center=(self.x_pos, self.y_pos))
            screen.blit(scaled_image, scaled_rect)
            self.rect = scaled_rect
        else:
            self.rect = self._current_rect()
            pygame.draw.rect(screen, (255,255,255), self.rect, border_radius=8)
            pygame.draw.rect(screen, (100,100,100), self.rect, 2, border_radius=8)

        self.text_rect = self.text.get_rect(center=self.rect.center)
        screen.blit(self.text, self.text_rect)

    def checkForInput(self, position):
        try:
            return self.rect.collidepoint(position)
        except Exception:
            return False

    def changeColor(self, position):
        try:
            if self._current_rect().collidepoint(position):
                self.text = self.font.render(self.text_input, True, pygame.Color(self.hovering_color))
            else:
                self.text = self.font.render(self.text_input, True, pygame.Color(self.base_color))
        except Exception:
            if self._current_rect().collidepoint(position):
                self.text = self.font.render(self.text_input, True, (255,255,255))
            else:
                self.text = self.font.render(self.text_input, True, (200,200,200))

    def check_hover(self, position):
        was = self.is_hovering
        self.is_hovering = self._current_rect().collidepoint(position)
        if was != self.is_hovering:
            self.changeColor(position)

class InputBox:
    def __init__(self, x, y, w, h, font, text=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.base_width = w
        self.color_inactive = pygame.Color("#e35d59")
        self.color_active = pygame.Color("#F9AA33")
        self.color = self.color_inactive
        self.text = text
        self.font = font
        self.padding_x = 8
        self.txt_surface = font.render(text, True, pygame.Color("#000000"))
        self.active = False
        self.clock = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = self.color_active if self.active else self.color_inactive

        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    temp_text = self.text
                    return temp_text

                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]

                else:
                    if event.unicode:
                        self.text += event.unicode

                self.txt_surface = self.font.render(self.text, True, (0, 0, 0))

        return None

    def update(self):
        self.rect.w = self.base_width
        return

    def draw(self, screen):
        pygame.draw.rect(screen, pygame.Color("#FFFFFF"), self.rect, border_radius=12)
        pygame.draw.rect(screen, self.color, self.rect, 2, border_radius=12)
        inner_w = max(0, self.rect.w - (self.padding_x * 2))
        visible_text = self.text
        while visible_text and self.font.size(visible_text)[0] > inner_w:
            visible_text = visible_text[1:]

        text_surf = self.font.render(visible_text, True, (0, 0, 0))
        old_clip = screen.get_clip()
        screen.set_clip(self.rect)
        screen.blit(
            text_surf,
            (self.rect.x + self.padding_x, self.rect.y + (self.rect.h - text_surf.get_height()) // 2),
        )
        screen.set_clip(old_clip)

class UIManager:
    def __init__(self, screen_width, screen_height, network_manager):
        self.SCREEN_WIDTH = screen_width
        self.SCREEN_HEIGHT = screen_height
        self.SCALE = min(screen_width / REF_WIDTH, screen_height / REF_HEIGHT)
        self.ASSETS_PATH = resource_path("assets")
        self.FONT_FILE = os.path.join(self.ASSETS_PATH, "PressStart2P-Regular.ttf")
        self.cacheDeFuentes = {}
        self.network_manager = network_manager

        self.SCREEN = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Menu Principal")

        self.load_assets()
        self.current_screen = "main"
        self.clock = pygame.time.Clock()
        self.last_time = pygame.time.get_ticks()
        self.init_components()

        self.servers = []      #Lista de servidores encontrados
        self.selectedServer = None  #ALmacena el servidor selecionado
        self.isSeletedServer = False #Fija el servidor seleccionado
        self.response = None #Resuesta de conexion para el jugador
        self.is_hovered = None
        self.messages = []    #Mensajes para el Chat
        self.chatLock = threading.Lock() 
        self.playGamePlayer = False
        #-----------------------------------
        # Navegador de salas (menú "server_list"): índice del servidor
        # tocado dentro del navegador (aún no confirmado con "Seleccionar"),
        # y el timestamp hasta el cual se muestra la alerta de "debes hacer
        # click en una sala primero".
        self.selected_server_index = None
        self.server_list_alert_until = 0
        self.wrong_password_until = 0
        self.fullserver_until = 0         
        self.no_server_until = 0  
        self.invalid_players_until = 0

        click_path = resource_path(os.path.join("assets", "sonido", "click.wav"))
        self.click_sound = pygame.mixer.Sound(click_path)

    def _s(self, val):
        """Escala un valor en píxeles según el factor de escala actual."""
        return int(val * self.SCALE)

    def load_assets(self):
        assets_path = resource_path("assets")
        self.global_font_size = self._s(18)
        self.pixel_font_path = os.path.join(assets_path, "PressStart2P-Regular.ttf")

        try:
            self.pixel_font = pygame.font.Font(self.pixel_font_path, self.global_font_size)
        except Exception:
            self.pixel_font = None
            print("Advertencia: No se pudo cargar la fuente pixelada. Usando fuente por defecto.")
        try:
            conectar_path = resource_path(os.path.join("assets", "conectar_btn.png"))
            self.conectar_img = pygame.image.load(conectar_path).convert_alpha()
        except Exception:
            self.conectar_img = None

        # --- Sala de Bots: assets opcionales (el usuario los agregará luego). ---
        # Botón "Sala de Bots" (mismo estilo que los demás botones del menú).
        # Ruta esperada: assets/sala_de_bots.png
        try:
            self.salabots_img = pygame.image.load(resource_path("assets/sala_de_bots.png")).convert_alpha()
        except Exception:
            self.salabots_img = None
        # Fondo exclusivo de la pantalla "Sala de Bots".
        # Ruta esperada: assets/bots_fondo.png
        try:
            self.bots_fondo_img_original = pygame.image.load(resource_path("assets/sala_de_bots_bg.jpg")).convert()
        except Exception:
            self.bots_fondo_img_original = None
        # Caras de cada bot, mostradas dentro de su recuadro.
        # Rutas esperadas: assets/louisbot_face.png y assets/genibot_face.png
        try:
            self.louisbot_face_img = pygame.image.load(resource_path("assets/louisbot.png")).convert_alpha()
        except Exception:
            self.louisbot_face_img = None
        try:
            self.genibot_face_img = pygame.image.load(resource_path("assets/genibot.png")).convert_alpha()
        except Exception:
            self.genibot_face_img = None

        self.titulo_img_original = pygame.image.load(os.path.join(assets_path, "titulo.png")).convert_alpha()
        self.fondo_img_original = pygame.image.load(os.path.join(assets_path, "fondo.png")).convert()
        self.cuadro_img = pygame.image.load(os.path.join(assets_path, "cuadro.png")).convert_alpha()
        self.cuadro_bot_img = pygame.image.load(os.path.join(assets_path, "cuadro_bot.png")).convert_alpha()
        self.jugar_img = pygame.image.load(os.path.join(assets_path, "jugar_btn.png")).convert_alpha()
        self.reglas_img = pygame.image.load(os.path.join(assets_path, "reglas_btn.png")).convert_alpha()
        self.salir_img = pygame.image.load(os.path.join(assets_path, "salir_btn.png")).convert_alpha()
        self.unirse_img = pygame.image.load(os.path.join(assets_path, "unirse_btn.png")).convert_alpha()
        self.actualizar_img = pygame.image.load(os.path.join(assets_path, "actualizar_btn.png")).convert_alpha()
        self.crear_img = pygame.image.load(os.path.join(assets_path, "crear_btn.png")).convert_alpha()
        self.volver_img = pygame.image.load(os.path.join(assets_path, "volver_btn.png")).convert_alpha()
        self.iniciar_juego_img = pygame.image.load(os.path.join(assets_path, "iniciar_btn.png")).convert_alpha()
        self.animacion_fondo_img = pygame.image.load(os.path.join(assets_path, "animacion_fondo.png")).convert_alpha()
        self.animacion_fondo_img = pygame.transform.scale(self.animacion_fondo_img, (self._s(1000), self._s(800)))
        self.pos_izquierda = (self._s(40), self._s(120))
        self.pos_derecha = (self._s(1230), self._s(120))
        self.angulo_izquierda = 0
        self.angulo_derecha = 0

        try:
            font_for_credits = self.pixel_font if self.pixel_font else pygame.font.SysFont("Arial", self.global_font_size)
            self.credits_surface = font_for_credits.render(
                "Proyecto realizado por el Equipo 1",
                True,
                "#d7fcd4"
            )
        except Exception:
            self.credits_surface = pygame.font.SysFont(None, self.global_font_size).render("Proyecto realizado por el Equipo 1", True, "#d7fcd4")

    def get_font(self, size):
        scaled_size = max(8, int(size * self.SCALE))
        if scaled_size in self.cacheDeFuentes:
            return self.cacheDeFuentes[scaled_size]
        try:
            font_path = resource_path(os.path.join("assets", "pixel.ttf"))
            f = pygame.font.Font(font_path, scaled_size)
        except:
            f = pygame.font.SysFont("arial", scaled_size)
        self.cacheDeFuentes[scaled_size] = f
        return f

    def init_components(self):
        self.crear_partida_img = pygame.image.load(resource_path("assets/crear_button.png")).convert_alpha()
        self.crear_partida_img_scaled = pygame.transform.scale(self.crear_partida_img, (self._s(120), self._s(40)))
        self.crear_partida_img_rect = self.crear_partida_img_scaled.get_rect()

        self.titulo_img = pygame.transform.scale(self.titulo_img_original, (int(self.SCREEN_WIDTH * 0.5), int(self.SCREEN_HEIGHT * 0.35)))
        self.fondo_img = pygame.transform.scale(self.fondo_img_original, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        if getattr(self, "bots_fondo_img_original", None) is not None:
            self.bots_fondo_img = pygame.transform.scale(self.bots_fondo_img_original, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        else:
            self.bots_fondo_img = None

        self.JUGAR_BUTTON = Button(
            image=self.jugar_img,
            pos=(self.SCREEN_WIDTH//2, int(self.SCREEN_HEIGHT*0.55)),
            text_input="",
            font=self.get_font(75),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._s(400), self._s(110))
        )

        self.REGLAS_BUTTON = Button(
            image=self.reglas_img,
            pos=(self.SCREEN_WIDTH//2 - self._s(180), int(self.SCREEN_HEIGHT*0.75)),
            text_input="",
            font=self.get_font(75),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._s(300), self._s(90))
        )

        self.SALIR_BUTTON = Button(
            image=self.salir_img,
            pos=(self.SCREEN_WIDTH//2 + self._s(180), int(self.SCREEN_HEIGHT*0.75)),
            text_input="",
            font=self.get_font(75),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._s(300), self._s(90))
        )

        self.UNIRSE_BUTTON = Button(
            image=self.unirse_img,
            pos=(self.SCREEN_WIDTH//2 - self._s(150), int(self.SCREEN_HEIGHT*0.58)),
            text_input="",
            font=self.get_font(50),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._s(250), self._s(100))
        )

        self.CREAR_BUTTON = Button(
            image=self.crear_img,
            pos=(self.SCREEN_WIDTH//2 + self._s(150), int(self.SCREEN_HEIGHT*0.58)),
            text_input="",
            font=self.get_font(50),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._s(250), self._s(100))
        )

        self.SALA_BOTS_BUTTON = Button(
            image=self.salabots_img,
            pos=(self.SCREEN_WIDTH//2, int(self.SCREEN_HEIGHT*0.70)),
            text_input="" if self.salabots_img else "Sala de Bots",
            font=self.get_font(40),
            base_color="#d7fcd4",
            hovering_color="White",
            size=(self._s(260), self._s(85))
        )

        self.PLAY_BACK = Button(
            image=self.volver_img,
            pos=(self.SCREEN_WIDTH//2, self.SCREEN_HEIGHT * 0.85),
            text_input="",
            font=self.get_font(75),
            base_color="White",
            hovering_color="Green"
        )

        self.BOT_ROOM_BACK_BUTTON = Button(
            image=self.volver_img,
            pos=(self.SCREEN_WIDTH//2, int(self.SCREEN_HEIGHT * 0.90)),
            text_input="",
            font=self.get_font(75),
            base_color="White",
            hovering_color="Green",
            size=(self._s(220), self._s(80))
        )

        small_font = self.get_font(30)

        join_btn_size = getattr(self, "crear_partida_img_scaled", None).get_size() if hasattr(self, "crear_partida_img_scaled") else (self._s(120), self._s(40))
        join_img = getattr(self, "conectar_img", None)
        self.JOIN_IP_BUTTON = Button(
            image=join_img,
            pos=(self.SCREEN_WIDTH//2 + self._s(180), self.SCREEN_HEIGHT//2),
            text_input="",
            font=self.get_font(20),
            base_color="#d7fcd4",
            hovering_color="White",
            size=join_btn_size
        )

        self.JOIN_BACK_BUTTON = Button(
            image=self.volver_img,
            pos=(self.SCREEN_WIDTH//2 + self._s(150), self.SCREEN_HEIGHT * 0.85),
            text_input="",
            font=self.get_font(75),
            base_color="White",
            hovering_color="Green"
        )

        self.JOIN_REFREHS_BUTTON = Button(
            image=self.actualizar_img,
            pos=(self.SCREEN_WIDTH//2 - self._s(150), self.SCREEN_HEIGHT * 0.85),
            text_input="",
            font=self.get_font(75),
            base_color="White",
            hovering_color="Green"
        )

        # Botones del navegador de salas ("server_list"): mismo diseño que
        # los botones ya existentes (reutiliza volver_img y conectar_img).
        self.SERVER_LIST_BACK_BUTTON = Button(
            image=self.volver_img,
            pos=(self.SCREEN_WIDTH//2 - 100, self.SCREEN_HEIGHT * 0.85),
            text_input="",
            font=self.get_font(75),
            base_color="White",
            hovering_color="Green"
        )
        self.SERVER_LIST_SELECT_BUTTON = Button(
            image=getattr(self, "conectar_img", None),
            pos=(self.SCREEN_WIDTH//2 + 100, self.SCREEN_HEIGHT * 0.85),
            text_input="Seleccionar" if not getattr(self, "conectar_img", None) else "",
            font=self.get_font(20),
            base_color="#d7fcd4",
            hovering_color="White",
            size=join_btn_size
        )

        # Botón "Crear Partida"
        font_btn = self.get_font(22)
        crear_size = self.crear_partida_img_scaled.get_size() if hasattr(self, "crear_partida_img_scaled") else (self._s(160), self._s(44))
        self.CREATE_GAME_BUTTON = Button(
            image=self.crear_partida_img,
            pos=(self.SCREEN_WIDTH//2, self.SCREEN_HEIGHT//2),
            text_input="",
            font=font_btn,
            base_color="#2ecc71",
            hovering_color="#4cd964",
            size=crear_size,
            scale_factor=1.12
        )
        self.CREATE_GAME_BUTTON.current_size = list(crear_size)
        self.CREATE_GAME_BUTTON.base_size = crear_size

        self.CREATE_BACK_BUTTON = Button(
            image=self.volver_img,
            pos=(self.SCREEN_WIDTH//2, self.SCREEN_HEIGHT * 0.85),
            text_input="",
            font=self.get_font(75),
            base_color="White",
            hovering_color="Green"
        )

        self.PLAY_GAME_BUTTON = Button(
            image=self.iniciar_juego_img,
            pos=(self.SCREEN_WIDTH//2 - self._s(150), self.SCREEN_HEIGHT * 0.85),
            text_input="",
            font=self.get_font(75),
            base_color="White",
            hovering_color="Green"
        )

        self.LOBBY_BACK_BUTTON = Button(
            image=self.volver_img,
            pos=(self.SCREEN_WIDTH//2 + self._s(150), self.SCREEN_HEIGHT * 0.85),
            text_input="",
            font=self.get_font(75),
            base_color="White",
            hovering_color="Green"
        )

        try:
            send_img = pygame.image.load(resource_path(os.path.join("assets", "enviar_mensaje.png"))).convert_alpha()
        except Exception:
            send_img = None
        crear_size = self.crear_partida_img_scaled.get_size() if hasattr(self, "crear_partida_img_scaled") else (self._s(120), self._s(40))

        self.show_chat = False

        import os
        try:
            tamano_icono = (self._s(150), self._s(150))
            self.chat_img_normal = pygame.image.load(resource_path(os.path.join("assets", "chat_normal.png"))).convert_alpha()
            self.chat_img_normal = pygame.transform.scale(self.chat_img_normal, tamano_icono)
            self.chat_img_notif = pygame.image.load(resource_path(os.path.join("assets", "chat_notif.png"))).convert_alpha()
            self.chat_img_notif = pygame.transform.scale(self.chat_img_notif, tamano_icono)
        except Exception as e:
            print("Error cargando las imágenes del chat:", e)
            self.chat_img_normal = None
            self.chat_img_notif = None

        self.TOGGLE_CHAT_BUTTON = Button(
            image=self.chat_img_normal,
            pos=(0, 0),
            text_input="",
            font=self.get_font(18),
            base_color="#FFFFFF",
            hovering_color="#d7fcd4",
            size=tamano_icono
        )
        self.messages_text = self.get_font(15).render("Chat:", True, "#b68f40")
        self.message_text = self.get_font(15).render("Msj:", True, "#b68f40")

        self.message_input_box = InputBox(0, 0, self._s(300), self._s(40), font=self.get_font(20))

        self.SEND_MS_BUTTON = Button(
            image=None,
            pos=(0, 0),
            text_input="Enviar",
            font=self.get_font(20),
            base_color="#2ecc71",
            hovering_color="White",
            size=(self._s(100), self._s(40))
        )
        self.credits_x_pos = self.SCREEN_WIDTH
        self.credits_y_pos = int(self.SCREEN_HEIGHT * 0.95)

        self.init_input_boxes()

    def init_input_boxes(self):
        smaller_font = self.get_font(33)
        self.text_color = pygame.Color("#d7fcd4")
        self.messages_text = smaller_font.render("Chat:", True, self.text_color)
        self.message_text = smaller_font.render("Mensaje:", True, self.text_color)
        self.label_font = smaller_font
        font = self.get_font(38)
        ib_w = self._s(300)
        ib_h = self._s(40)
        self.host_input_box = InputBox(0, 0, ib_w, ib_h, font, text="")
        self.name_input_box = InputBox(0, 0, ib_w, ib_h, smaller_font)
        self.password_input_box = InputBox(0, 0, ib_w, ib_h, smaller_font)
        self.max_players_input_box = InputBox(0, 0, ib_w, ib_h, smaller_font)
        self.num_bots_input_box = InputBox(0, 0, ib_w, ib_h, smaller_font, text="")
        self.join_player_input_box = InputBox(0, 0, ib_w, ib_h, smaller_font)
        self.join_password_input_box = InputBox(0, 0, ib_w, ib_h, smaller_font)
        # Conexión manual por IP: para cuando el descubrimiento automático
        # (broadcast UDP) no llega, típicamente porque se está jugando por
        # una VPN tipo Hamachi en vez de la misma LAN física. El puerto es
        # opcional -si se deja vacío, se usa el puerto TCP por defecto-.
        self.join_ip_manual_input = InputBox(0, 0, ib_w, ib_h, smaller_font)
        self.join_port_manual_input = InputBox(0, 0, ib_w, ib_h, smaller_font)
        self.message_input_box = InputBox(0, 0, ib_w, ib_h, smaller_font)
        self.bot_room_name_input = InputBox(0, 0, ib_w, ib_h, smaller_font)

    def update_animation(self, delta_time):
        self.angulo_izquierda = (self.angulo_izquierda + 50 * delta_time) % 360
        self.angulo_derecha = (self.angulo_derecha + 50 * delta_time) % 360
        self.credits_x_pos -= 100 * delta_time
        if self.credits_x_pos < -self.credits_surface.get_width():
            self.credits_x_pos = self.SCREEN_WIDTH

    def draw_background(self):
        self.SCREEN.blit(self.fondo_img, (0, 0))
        rotada_izquierda = pygame.transform.rotate(self.animacion_fondo_img, self.angulo_izquierda)
        rect_izquierda = rotada_izquierda.get_rect(center=self.pos_izquierda)
        self.SCREEN.blit(rotada_izquierda, rect_izquierda)
        rotada_derecha = pygame.transform.rotate(self.animacion_fondo_img, self.angulo_derecha)
        rect_derecha = rotada_derecha.get_rect(center=self.pos_derecha)
        self.SCREEN.blit(rotada_derecha, rect_derecha)
        self.SCREEN.blit(self.credits_surface, (self.credits_x_pos, self.credits_y_pos))

    def draw_main_menu(self):
        title_rect = self.titulo_img.get_rect(center=(self.SCREEN_WIDTH//2, int(self.SCREEN_HEIGHT*0.25)))
        self.SCREEN.blit(self.titulo_img, title_rect)
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        for button in [self.JUGAR_BUTTON, self.REGLAS_BUTTON, self.SALIR_BUTTON]:
            button.check_hover(MENU_MOUSE_POS)
            button.update(self.SCREEN)
        return MENU_MOUSE_POS

    def draw_play_menu(self):
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        for button in [self.UNIRSE_BUTTON, self.CREAR_BUTTON, self.SALA_BOTS_BUTTON, self.PLAY_BACK]:
            button.check_hover(MENU_MOUSE_POS)
            button.update(self.SCREEN)
        return MENU_MOUSE_POS

    def draw_bot_room_background(self):
        """Fondo exclusivo de la pantalla 'Sala de Bots' (sin el título del menú principal)."""
        if getattr(self, "bots_fondo_img", None) is not None:
            self.SCREEN.blit(self.bots_fondo_img, (0, 0))
        else:
            # Sin asset propio todavía: usamos el fondo genérico como respaldo.
            self.SCREEN.blit(self.fondo_img, (0, 0))

    def draw_bot_room_menu(self):
        MENU_MOUSE_POS = pygame.mouse.get_pos()

        # --- Título "Sala de Bots" ---
        title_font = self.get_font(55)
        title_surf = title_font.render("Sala de Bots", True, "#d7fcd4")
        title_rect = title_surf.get_rect(center=(self.SCREEN_WIDTH // 2, int(self.SCREEN_HEIGHT * 0.12)))
        self.SCREEN.blit(title_surf, title_rect)

        # --- Barra de input para el nombre del jugador ---
        label_font = self.get_font(24)
        label_surf = label_font.render("Tu nombre:", True, "#d7fcd4")
        ib_w, ib_h = self._s(320), self._s(44)
        input_x = self.SCREEN_WIDTH // 2 - ib_w // 2
        input_y = int(self.SCREEN_HEIGHT * 0.22)
        self.bot_room_name_input.rect.x = input_x
        self.bot_room_name_input.rect.y = input_y
        self.bot_room_name_input.rect.w = ib_w
        self.bot_room_name_input.rect.h = ib_h
        label_rect = label_surf.get_rect(midbottom=(self.SCREEN_WIDTH // 2, input_y - self._s(8)))
        self.SCREEN.blit(label_surf, label_rect)
        self.bot_room_name_input.draw(self.SCREEN)

        # --- Recuadros de selección de bot (LouisBot / GeniBot) ---
        frame_w, frame_h = self._s(220), self._s(230)
        gap = self._s(120)
        center_y = int(self.SCREEN_HEIGHT * 0.58)
        louis_center = (self.SCREEN_WIDTH // 2 - gap // 2 - frame_w // 2, center_y)
        gen_center = (self.SCREEN_WIDTH // 2 + gap // 2 + frame_w // 2, center_y)

        name_font = self.get_font(26)

        self.bot_room_louis_rect = pygame.Rect(0, 0, frame_w, frame_h)
        self.bot_room_louis_rect.center = louis_center
        self.bot_room_gen_rect = pygame.Rect(0, 0, frame_w, frame_h)
        self.bot_room_gen_rect.center = gen_center

        for rect, face_img, label in (
            (self.bot_room_louis_rect, getattr(self, "louisbot_face_img", None), "LouisBot"),
            (self.bot_room_gen_rect, getattr(self, "genibot_face_img", None), "GeniBot"),
        ):
            hovering = rect.collidepoint(MENU_MOUSE_POS)

            # Marco (reutiliza el mismo asset "cuadro" usado en otras pantallas).
            if getattr(self, "cuadro_bot_img", None) is not None:
                cuadro_surf = pygame.transform.scale(self.cuadro_bot_img, (rect.w, rect.h))
                self.SCREEN.blit(cuadro_surf, rect)
            else:
                pygame.draw.rect(self.SCREEN, (40, 40, 40), rect, border_radius=12)

            border_color = (255, 255, 255) if hovering else (150, 150, 150)
            pygame.draw.rect(self.SCREEN, border_color, rect, 3, border_radius=12)

            # Cara del bot, centrada dentro del recuadro (si el asset existe).
            if face_img is not None:
                pad = self._s(18)
                inner_w, inner_h = rect.w - pad * 2, rect.h - pad * 2
                face_scaled = pygame.transform.smoothscale(face_img, (inner_w, inner_h))
                face_rect = face_scaled.get_rect(center=rect.center)
                self.SCREEN.blit(face_scaled, face_rect)
            else:
                placeholder = name_font.render("?", True, (200, 200, 200))
                self.SCREEN.blit(placeholder, placeholder.get_rect(center=rect.center))

            # Ligero "levantamiento" visual al pasar el mouse por encima.
            if hovering:
                glow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                glow.fill((255, 255, 255, 25))
                self.SCREEN.blit(glow, rect)

            label_surf = name_font.render(label, True, "#d7fcd4")
            label_rect = label_surf.get_rect(midtop=(rect.centerx, rect.bottom + self._s(10)))
            self.SCREEN.blit(label_surf, label_rect)

        self.BOT_ROOM_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
        self.BOT_ROOM_BACK_BUTTON.update(self.SCREEN)

        return MENU_MOUSE_POS

    def confirm_bot_duel(self, bot_display_name):
        """Modal de confirmación '¿Enfrentarse a {bot}?' (mismo estilo que confirm_exit)."""
        clock = pygame.time.Clock()
        try:
            snapshot = self.SCREEN.copy()
        except Exception:
            snapshot = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))

        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))

        w, h = self._s(560), self._s(260)
        x = (self.SCREEN_WIDTH - w) // 2
        y = (self.SCREEN_HEIGHT - h) // 2
        modal_rect = pygame.Rect(x, y, w, h)

        btn_w, btn_h = self._s(130), self._s(50)
        btn_si = pygame.Rect(x + self._s(80), y + self._s(160), btn_w, btn_h)
        btn_no = pygame.Rect(x + w - btn_w - self._s(80), y + self._s(160), btn_w, btn_h)

        font_title = self.get_font(34)
        font_text = self.get_font(20)

        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return False
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if btn_si.collidepoint(ev.pos):
                        return True
                    if btn_no.collidepoint(ev.pos):
                        return False

            self.SCREEN.blit(snapshot, (0, 0))
            self.SCREEN.blit(overlay, (0, 0))

            pygame.draw.rect(self.SCREEN, (40, 40, 40), modal_rect, border_radius=12)
            pygame.draw.rect(self.SCREEN, (60, 140, 220), modal_rect, 3, border_radius=12)

            title = font_title.render(f"¿Enfrentarse a {bot_display_name}?", True, (255, 255, 255))
            title = title if title.get_width() <= w - self._s(40) else font_text.render(f"¿Enfrentarse a {bot_display_name}?", True, (255, 255, 255))
            self.SCREEN.blit(title, (x + (w - title.get_width()) // 2, y + self._s(40)))

            pygame.draw.rect(self.SCREEN, (50, 180, 50), btn_si, border_radius=8)
            lbl_si = font_text.render("SÍ", True, (255, 255, 255))
            self.SCREEN.blit(lbl_si, lbl_si.get_rect(center=btn_si.center))

            pygame.draw.rect(self.SCREEN, (180, 50, 50), btn_no, border_radius=8)
            lbl_no = font_text.render("NO", True, (255, 255, 255))
            self.SCREEN.blit(lbl_no, lbl_no.get_rect(center=btn_no.center))

            pygame.display.flip()
            clock.tick(60)

    def draw_join_menu(self):
        self.servers = self.network_manager.servers
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        smaller_font = self.get_font(20)

        box_width = self._s(600)
        box_height = self._s(360)
        box_x = self.SCREEN_WIDTH // 2 - box_width // 2
        box_y = self.SCREEN_HEIGHT // 2 - box_height // 2 + self._s(40)

        cuadro_surf = pygame.transform.scale(self.cuadro_img, (box_width, box_height))
        self.SCREEN.blit(cuadro_surf, (box_x, box_y))

        label_w = self._s(180)
        input_w = self._s(360)
        gap = self._s(12)
        content_total_w = label_w + gap + input_w
        base_x = box_x + (box_width - content_total_w) // 2 + self._s(20)
        label_x = base_x
        input_x = base_x + label_w + gap

        rectNameServer = pygame.Rect(input_x, box_y + self._s(43), input_w - self._s(160), self._s(36))
        self.is_hovered = rectNameServer.collidepoint(MENU_MOUSE_POS)

        if getattr(self, "isSeletedServer", False):
            border_color = (46, 204, 113)
            fill_color = (240, 255, 240)
        elif self.is_hovered:
            border_color = (150, 150, 150)
            fill_color = (255, 255, 255)
        else:
            border_color = (200, 200, 200)
            fill_color = (255, 255, 255)

        pygame.draw.rect(self.SCREEN, fill_color, rectNameServer, border_radius=12)
        pygame.draw.rect(self.SCREEN, border_color, rectNameServer, 2, border_radius=12)

        if self.servers:
            server_text = smaller_font.render(f"{self.servers[0]['name']}: Jugadores {self.servers[0]['currentPlayers']}/{self.servers[0]['max_players']}", True, (0, 0, 0))
            server_rect = server_text.get_rect(center=rectNameServer.center)
            self.SCREEN.blit(server_text, server_rect)
        else:
            noServers = smaller_font.render("No hay Salas :( ", True, (0,0,0))
            noServers_rect = noServers.get_rect(center=rectNameServer.center)
            self.SCREEN.blit(noServers, noServers_rect)

        now = pygame.time.get_ticks()
        msg_x = input_x + input_w // 2 + self._s(70)
        msg_y = box_y + self._s(75)

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
            self.SCREEN.blit(surf1, rect1.topleft)
            self.SCREEN.blit(surf2, rect2.topleft)

        ip_label = smaller_font.render("Nombre Sala:", True, "#d7fcd4")
        ip_label_rect = ip_label.get_rect()
        ip_label_rect.centery = box_y + self._s(35) + self._s(24)
        ip_label_rect.right = input_x - self._s(8)
        self.SCREEN.blit(ip_label, ip_label_rect)

        player_label = smaller_font.render("Nombre del Jugador:", True, "#d7fcd4")
        player_label_rect = player_label.get_rect()
        player_label_rect.right = input_x - self._s(8)
        player_label_rect.centery = box_y + self._s(110)
        self.SCREEN.blit(player_label, player_label_rect)
        self.join_player_input_box.draw(self.SCREEN)
        self.join_player_input_box.rect.topleft = (input_x, box_y + self._s(90))
        self.join_player_input_box.rect.size = (input_w, self._s(40))

        pw_label = smaller_font.render("Contraseña:", True, "#d7fcd4")
        pw_label_rect = pw_label.get_rect()
        pw_label_rect.right = input_x - self._s(8)
        pw_label_rect.centery = box_y + self._s(160)
        self.SCREEN.blit(pw_label, pw_label_rect)
        self.join_password_input_box.draw(self.SCREEN)
        self.join_password_input_box.rect.topleft = (input_x, box_y + self._s(140))
        self.join_password_input_box.rect.size = (input_w, self._s(40))

        # --- Conexión manual por IP (para VPN tipo Hamachi, donde el
        # descubrimiento automático por broadcast no cruza la red virtual). ---
        separador_y = box_y + self._s(195)
        pygame.draw.line(
            self.SCREEN, (120, 120, 120),
            (box_x + self._s(30), separador_y), (box_x + box_width - self._s(30), separador_y), 1
        )
        manual_hint = self.get_font(14).render("¿Jugando por Hamachi u otra VPN? Conéctate directo por IP:", True, "#a0a0a0")
        manual_hint_rect = manual_hint.get_rect(centerx=box_x + box_width // 2, y=separador_y + self._s(6))
        self.SCREEN.blit(manual_hint, manual_hint_rect)

        ip_manual_label = smaller_font.render("IP:", True, "#d7fcd4")
        ip_manual_label_rect = ip_manual_label.get_rect()
        ip_manual_label_rect.right = input_x - self._s(8)
        ip_manual_label_rect.centery = box_y + self._s(258)
        self.SCREEN.blit(ip_manual_label, ip_manual_label_rect)
        self.join_ip_manual_input.draw(self.SCREEN)
        self.join_ip_manual_input.rect.topleft = (input_x, box_y + self._s(238))
        self.join_ip_manual_input.rect.size = (int(input_w * 0.65), self._s(40))

        port_manual_label = smaller_font.render("Puerto:", True, "#d7fcd4")
        port_x = input_x + int(input_w * 0.65) + self._s(10)
        port_manual_label_rect = port_manual_label.get_rect()
        port_manual_label_rect.right = port_x + self._s(60)
        port_manual_label_rect.centery = box_y + self._s(258)
        self.SCREEN.blit(port_manual_label, port_manual_label_rect)
        self.join_port_manual_input.draw(self.SCREEN)
        self.join_port_manual_input.rect.topleft = (port_x + self._s(65), box_y + self._s(238))
        self.join_port_manual_input.rect.size = (int(input_w * 0.35) - self._s(65), self._s(40))
        

        if hasattr(self, "JOIN_IP_BUTTON") and self.JOIN_IP_BUTTON:
            gap_btn = self._s(12)
            btn_w, btn_h = self.JOIN_IP_BUTTON.rect.size
            pwd_top = box_y + self._s(238)
            pwd_h = self._s(40)
            btn_x = rectNameServer.centerx
            btn_y = pwd_top + pwd_h + gap_btn + btn_h // 2
            self.JOIN_IP_BUTTON.rect.center = (btn_x - self._s(30), btn_y)
            try:
                self.JOIN_IP_BUTTON.x_pos, self.JOIN_IP_BUTTON.y_pos = self.JOIN_IP_BUTTON.rect.center
            except Exception:
                pass
            self.JOIN_IP_BUTTON.check_hover(MENU_MOUSE_POS)
            self.JOIN_IP_BUTTON.update(self.SCREEN)

        self.JOIN_REFREHS_BUTTON.check_hover(MENU_MOUSE_POS)
        self.JOIN_REFREHS_BUTTON.update(self.SCREEN)
        self.JOIN_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
        self.JOIN_BACK_BUTTON.update(self.SCREEN)

        return MENU_MOUSE_POS

    def draw_server_list_menu(self):
        """
        Navegador de salas: misma ventanita (cuadro.png) y el mismo estilo de
        barra que ya se usa en draw_join_menu para el recuadro de la sala,
        pero listando TODAS las salas encontradas en la red, cada una en su
        propio recuadro (uno debajo del otro), clicable, con botones
        "Volver" y "Seleccionar" debajo.

        OJO: network_manager.discoverServers() es asíncrono -lanza un hilo
        que escucha broadcasts UDP durante unos segundos y va llenando
        network_manager.servers poco a poco-, así que esta función tiene que
        releer esa lista EN VIVO cada frame (igual que ya hace
        draw_join_menu) para que las salas vayan apareciendo a medida que se
        descubren, en vez de quedarse pegada en la lista vacía del instante
        en que se abrió el menú.
        """
        self.servers = self.network_manager.servers
        MENU_MOUSE_POS = pygame.mouse.get_pos()

        # Medidas relativas a la resolución de pantalla actual (no valores
        # fijos en píxeles), para que se vea bien sin importar el tamaño de
        # ventana de quien lo abra.
        font_size = max(14, int(self.SCREEN_HEIGHT * 0.0225))
        smaller_font = self.get_font(font_size)

        box_width = int(self.SCREEN_WIDTH * 0.47)
        max_visible = 6
        bar_h = max(32, int(self.SCREEN_HEIGHT * 0.05))
        bar_gap = max(6, int(self.SCREEN_HEIGHT * 0.012))
        list_top_pad = int(self.SCREEN_HEIGHT * 0.09)
        list_bottom_pad = int(self.SCREEN_HEIGHT * 0.05)

        cantidad_a_mostrar = max(1, min(len(self.servers), max_visible)) if self.servers else 1
        box_height = list_top_pad + cantidad_a_mostrar * bar_h + max(0, cantidad_a_mostrar - 1) * bar_gap + list_bottom_pad
        box_height = max(box_height, int(self.SCREEN_HEIGHT * 0.32))  # nunca más chica que el mínimo original

        box_x = self.SCREEN_WIDTH // 2 - box_width // 2
        box_y = self.SCREEN_HEIGHT // 2 - box_height // 2 + int(self.SCREEN_HEIGHT * 0.08)

        cuadro_surf = pygame.transform.scale(self.cuadro_img, (box_width, box_height))
        self.SCREEN.blit(cuadro_surf, (box_x, box_y))

        titulo = smaller_font.render("Salas disponibles", True, "#d7fcd4")
        titulo_rect = titulo.get_rect(centerx=box_x + box_width // 2, y=box_y + int(self.SCREEN_HEIGHT * 0.018))
        self.SCREEN.blit(titulo, titulo_rect)

        # Área de la lista, centrada dentro de la ventanita.
        list_w = int(box_width * 0.8)
        list_x = box_x + (box_width - list_w) // 2
        list_y = box_y + list_top_pad

        self.server_list_bar_rects = []  # se recalcula cada frame, usado por el click handler

        if not self.servers:
            noServers = smaller_font.render("Buscando salas en la red...", True, "#d7fcd4")
            noServers_rect = noServers.get_rect(center=(box_x + box_width // 2, box_y + box_height // 2))
            self.SCREEN.blit(noServers, noServers_rect)
        else:
            # Un recuadro POR CADA sala encontrada, uno debajo del otro (hasta
            # max_visible a la vez; si hay más, se muestran las primeras).
            for i, server in enumerate(self.servers[:max_visible]):
                bar_rect = pygame.Rect(list_x, list_y + i * (bar_h + bar_gap), list_w, bar_h)
                self.server_list_bar_rects.append(bar_rect)

                is_hover = bar_rect.collidepoint(MENU_MOUSE_POS)
                is_selected = (self.selected_server_index == i)

                if is_selected:
                    border_color = (46, 204, 113)   # verde: igual que la selección en draw_join_menu
                    fill_color = (240, 255, 240)
                elif is_hover:
                    border_color = (150, 150, 150)
                    fill_color = (255, 255, 255)
                else:
                    border_color = (200, 200, 200)
                    fill_color = (255, 255, 255)

                pygame.draw.rect(self.SCREEN, fill_color, bar_rect, border_radius=12)
                pygame.draw.rect(self.SCREEN, border_color, bar_rect, 2, border_radius=12)

                texto = f"Sala: {server.get('name', '?')}, jugadores: {server.get('currentPlayers', '?')}/{server.get('max_players', '?')}"
                texto_surf = smaller_font.render(texto, True, (0, 0, 0))
                texto_rect = texto_surf.get_rect(center=bar_rect.center)
                self.SCREEN.blit(texto_surf, texto_rect)

        # Alerta: "debes hacer click en una sala y luego en seleccionar"
        now = pygame.time.get_ticks()
        if getattr(self, "server_list_alert_until", 0) > now:
            alerta = smaller_font.render("Debes hacer click en una sala y luego en seleccionar", True, (255, 120, 120))
            alerta_rect = alerta.get_rect(center=(box_x + box_width // 2, list_y + max_visible * (bar_h + bar_gap) + 8))
            self.SCREEN.blit(alerta, alerta_rect)

        # Botones Volver / Seleccionar (mismo diseño que los demás menús),
        # reposicionados justo debajo de la ventanita -que ahora puede
        # cambiar de alto según cuántas salas haya-.
        btn_y = box_y + box_height + int(self.SCREEN_HEIGHT * 0.06)
        self.SERVER_LIST_BACK_BUTTON.x_pos = self.SCREEN_WIDTH // 2 - int(self.SCREEN_WIDTH * 0.08)
        self.SERVER_LIST_BACK_BUTTON.y_pos = btn_y
        self.SERVER_LIST_SELECT_BUTTON.x_pos = self.SCREEN_WIDTH // 2 + int(self.SCREEN_WIDTH * 0.08)
        self.SERVER_LIST_SELECT_BUTTON.y_pos = btn_y

        self.SERVER_LIST_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
        self.SERVER_LIST_BACK_BUTTON.update(self.SCREEN)
        self.SERVER_LIST_SELECT_BUTTON.check_hover(MENU_MOUSE_POS)
        self.SERVER_LIST_SELECT_BUTTON.update(self.SCREEN)

        return MENU_MOUSE_POS

    def draw_create_menu(self):
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        box_width = self._s(700)
        box_height = self._s(400)
        box_x = (self.SCREEN_WIDTH // 2 - box_width // 2)
        box_y = self.SCREEN_HEIGHT // 2 - box_height // 2

        cuadro_surf = pygame.transform.scale(self.cuadro_img, (box_width, box_height))
        self.SCREEN.blit(cuadro_surf, (box_x, box_y))

        campos = [
            ("Nombre de la Sala:", self.host_input_box),
            ("Nombre del Jugador:", self.name_input_box),
            ("Contraseña:", self.password_input_box),
            ("Cantidad de Jugadores:", self.max_players_input_box),
            ("Cantidad de Bots:", self.num_bots_input_box)
        ]
        total_inputs = len(campos)
        input_w, input_h = self._s(250), self._s(40)
        label_gap = self._s(10)
        vertical_gap = self._s(10)
        total_height = total_inputs * input_h + (total_inputs - 1) * vertical_gap
        start_y = box_y + (box_height - total_height) // 2

        create_label_font = self.get_font(27)
        for idx, (label_text, input_box) in enumerate(campos):
            input_x = box_x + (box_width - input_w) // 2 + self._s(90)
            input_y = start_y + idx * (input_h + vertical_gap) - self._s(35)
            label_surf = create_label_font.render(label_text, True, self.text_color)
            label_rect = label_surf.get_rect()
            label_rect.centery = input_y + input_h // 2
            label_rect.right = input_x - label_gap
            input_box.rect.topleft = (input_x, input_y)
            input_box.rect.size = (input_w, input_h)
            self.SCREEN.blit(label_surf, label_rect)
            input_box.draw(self.SCREEN)

        btn_x = box_x + box_width // 2
        btn_y = start_y + total_height + self._s(20)
        self.CREATE_GAME_BUTTON.x_pos, self.CREATE_GAME_BUTTON.y_pos = btn_x, btn_y
        try:
            self.CREATE_GAME_BUTTON.rect.center = (btn_x, btn_y)
        except Exception:
            pass
        self.CREATE_GAME_BUTTON.check_hover(MENU_MOUSE_POS)
        self.CREATE_GAME_BUTTON.update(self.SCREEN)

        back_x = box_x + box_width // 2
        back_y = box_y + box_height + self._s(20)
        self.CREATE_BACK_BUTTON.x_pos, self.CREATE_BACK_BUTTON.y_pos = back_x, back_y
        try:
            self.CREATE_BACK_BUTTON.rect.center = (back_x, back_y)
        except Exception:
            pass
        self.CREATE_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
        self.CREATE_BACK_BUTTON.update(self.SCREEN)

        now = pygame.time.get_ticks()
        if getattr(self, "invalid_players_until", 0) > now:
            warn_font = self.get_font(16)
            warn_text = "Debe elegir entre 2 y 7 jugadores"
            warn_surf = warn_font.render(warn_text, True, (35, 35, 35))
            warn_rect = warn_surf.get_rect(center=(box_x + box_width // 2, btn_y + self._s(42)))
            bg_rect = warn_rect.inflate(self._s(20), self._s(12))
            pygame.draw.rect(self.SCREEN, (255, 244, 214), bg_rect, border_radius=10)
            pygame.draw.rect(self.SCREEN, (210, 160, 70), bg_rect, 2, border_radius=10)
            self.SCREEN.blit(warn_surf, warn_rect)

        return MENU_MOUSE_POS

    def draw_lobby(self):
        MENU_MOUSE_POS = pygame.mouse.get_pos()
        smaller_font = self.get_font(20)

        box_width = self._s(800)
        if getattr(self, "show_chat", False):
            box_height = self._s(500)
            lobby_h = box_height + self._s(80)
        else:
            box_height = self._s(340)
            lobby_h = box_height + self._s(80)

        box_x = (self.SCREEN_WIDTH - box_width) // 2
        box_y = (self.SCREEN_HEIGHT - lobby_h) // 2 + self._s(20)

        cuadro_surf = pygame.transform.scale(self.cuadro_img, (box_width, lobby_h))
        self.SCREEN.blit(cuadro_surf, (box_x - self._s(30), box_y - self._s(20)))

        server_name = ""
        current_p = 0
        max_p = 0
        if getattr(self.network_manager, "currentServer", None):
            server_name = self.network_manager.currentServer.get('name','')
            current_p = self.network_manager.currentServer.get('currentPlayers',0)
            max_p = self.network_manager.currentServer.get('max_players',0)
        elif getattr(self, "selectedServer", None):
            server_name = self.selectedServer.get('name','')
            current_p = self.selectedServer.get('currentPlayers',0)
            max_p = self.selectedServer.get('max_players',0)

        info_font = self.get_font(24)
        sala_surf = info_font.render(f"Sala de espera: {server_name}", True, "#e6c371")
        color_jugadores = "#2ecc71" if current_p >= 2 else "#e74c3c"
        jugadores_surf = info_font.render(f"Jugadores: {current_p}/{max_p}", True, color_jugadores)

        y_textos = box_y + self._s(40)
        self.SCREEN.blit(sala_surf, (box_x + self._s(60), y_textos))
        self.SCREEN.blit(jugadores_surf, (box_x + box_width - jugadores_surf.get_width() - self._s(60), y_textos))

        cantidad_actual = 0
        if hasattr(self, "network_manager"):
            msg_server = getattr(self.network_manager, "messagesServer", [])
            if msg_server is not None:
                cantidad_actual = len(msg_server)

        if not hasattr(self, "mensajes_guardados"):
            self.mensajes_guardados = cantidad_actual
            self.tiene_notificacion = False

        if not getattr(self, "show_chat", False) and cantidad_actual > self.mensajes_guardados:
            self.tiene_notificacion = True

        if getattr(self, "show_chat", False):
            self.tiene_notificacion = False
            self.mensajes_guardados = cantidad_actual

        if hasattr(self, "TOGGLE_CHAT_BUTTON"):
            if getattr(self, "tiene_notificacion", False):
                if getattr(self, "chat_img_notif", None) is not None:
                    self.TOGGLE_CHAT_BUTTON.original_image = self.chat_img_notif
            else:
                if getattr(self, "chat_img_normal", None) is not None:
                    self.TOGGLE_CHAT_BUTTON.original_image = self.chat_img_normal
            self.TOGGLE_CHAT_BUTTON.check_hover(MENU_MOUSE_POS)
            self.TOGGLE_CHAT_BUTTON.update(self.SCREEN)

        chat_x = self.SCREEN_WIDTH // 2
        chat_y = y_textos + self._s(80)
        self.TOGGLE_CHAT_BUTTON.x_pos = chat_x
        self.TOGGLE_CHAT_BUTTON.y_pos = chat_y
        self.TOGGLE_CHAT_BUTTON.rect.center = (chat_x, chat_y)
        if hasattr(self.TOGGLE_CHAT_BUTTON, "text_rect"):
            self.TOGGLE_CHAT_BUTTON.text_rect.center = (chat_x, chat_y)

        self.TOGGLE_CHAT_BUTTON.text_input = ""
        if hasattr(self.TOGGLE_CHAT_BUTTON, "text"):
            self.TOGGLE_CHAT_BUTTON.text = self.get_font(18).render("", True, "#FFFFFF")

        self.TOGGLE_CHAT_BUTTON.changeColor(MENU_MOUSE_POS)
        self.TOGGLE_CHAT_BUTTON.check_hover(MENU_MOUSE_POS)

        if getattr(self, "tiene_notificacion", False) and getattr(self, "chat_img_notif", None) is not None:
            self.TOGGLE_CHAT_BUTTON.image = self.chat_img_notif
        elif getattr(self, "chat_img_normal", None) is not None:
            self.TOGGLE_CHAT_BUTTON.image = self.chat_img_normal

        self.TOGGLE_CHAT_BUTTON.update(self.SCREEN)

        if getattr(self, "show_chat", False):
            padding = self._s(24)
            inner_w = box_width - padding * 2
            chat_w = int(inner_w * 0.65)
            chat_h = self._s(180)

            chat_rect = pygame.Rect(box_x + (box_width - chat_w) // 2, self.TOGGLE_CHAT_BUTTON.rect.bottom + self._s(15), chat_w, chat_h)
            pygame.draw.rect(self.SCREEN, (245, 245, 245), chat_rect, border_radius=15)
            pygame.draw.rect(self.SCREEN, (150, 150, 150), chat_rect, 3, border_radius=15)

            y_offset = chat_rect.y + self._s(10)
            with self.chatLock:
                recentMsg = list(self.network_manager.messagesServer)[-8:]
            for msg in recentMsg:
                rendered = smaller_font.render(msg, True, (30, 30, 30))
                if rendered.get_width() > chat_rect.w - self._s(20):
                    max_chars = max(8, int(len(msg) * (chat_rect.w - self._s(20)) / max(1, rendered.get_width())) - 3)
                    msg = msg[:max_chars] + "..."
                    rendered = smaller_font.render(msg, True, (30, 30, 30))
                self.SCREEN.blit(rendered, (chat_rect.x + self._s(10), y_offset))
                y_offset += rendered.get_height() + 6

            row_h = self._s(44)
            input_w = min(self._s(360), inner_w - self._s(40)) - self._s(80)
            msg_box_x = chat_rect.x
            msg_box_y = chat_rect.bottom + self._s(15)
            self.message_input_box.rect.topleft = (msg_box_x, msg_box_y)
            self.message_input_box.rect.size = (input_w, row_h)
            self.message_input_box.draw(self.SCREEN)

            chat_label_pos = (chat_rect.left - self.messages_text.get_width() - self._s(12), chat_rect.centery - self.messages_text.get_height() // 2)
            self.SCREEN.blit(self.messages_text, chat_label_pos)

            msg_label_pos = (self.message_input_box.rect.left - self.message_text.get_width() - self._s(12), self.message_input_box.rect.centery - self.message_text.get_height() // 2)
            self.SCREEN.blit(self.message_text, msg_label_pos)

            send_x = self.message_input_box.rect.right + max(self._s(48), self.SEND_MS_BUTTON.rect.width//2 + self._s(10))
            send_y = self.message_input_box.rect.centery
            self.SEND_MS_BUTTON.x_pos = send_x
            self.SEND_MS_BUTTON.y_pos = send_y
            self.SEND_MS_BUTTON.rect.center = (send_x, send_y)
            if hasattr(self.SEND_MS_BUTTON, "text_rect"):
                self.SEND_MS_BUTTON.text_rect.center = (send_x, send_y)
            self.SEND_MS_BUTTON.check_hover(MENU_MOUSE_POS)
            self.SEND_MS_BUTTON.update(self.SCREEN)
        else:
            self.SEND_MS_BUTTON.x_pos = -9999
            self.SEND_MS_BUTTON.y_pos = -9999
            self.SEND_MS_BUTTON.rect.topleft = (-9999, -9999)
            if hasattr(self.SEND_MS_BUTTON, "text_rect"):
                self.SEND_MS_BUTTON.text_rect.topleft = (-9999, -9999)
            self.message_input_box.rect.topleft = (-9999, -9999)

        play_active = False
        if getattr(self.network_manager, "is_host", False):
            play_active = self.network_manager.canStartGame()
        elif getattr(self, "playGamePlayer", False):
            play_active = True

        center_x = self.SCREEN_WIDTH // 2
        offset = self._s(180)
        btn_y = box_y + lobby_h - self._s(60)

        if play_active:
            self.PLAY_GAME_BUTTON.x_pos = center_x - offset
            self.PLAY_GAME_BUTTON.y_pos = btn_y
            self.PLAY_GAME_BUTTON.rect.center = (self.PLAY_GAME_BUTTON.x_pos, self.PLAY_GAME_BUTTON.y_pos)
            if hasattr(self.PLAY_GAME_BUTTON, "text_rect"):
                self.PLAY_GAME_BUTTON.text_rect.center = self.PLAY_GAME_BUTTON.rect.center
            self.PLAY_GAME_BUTTON.check_hover(MENU_MOUSE_POS)
            self.PLAY_GAME_BUTTON.update(self.SCREEN)
        else:
            self.PLAY_GAME_BUTTON.x_pos = -9999
            self.PLAY_GAME_BUTTON.y_pos = -9999
            self.PLAY_GAME_BUTTON.rect.topleft = (-9999, -9999)
            if hasattr(self.PLAY_GAME_BUTTON, "text_rect"):
                self.PLAY_GAME_BUTTON.text_rect.topleft = (-9999, -9999)

        self.LOBBY_BACK_BUTTON.x_pos = center_x + offset
        self.LOBBY_BACK_BUTTON.y_pos = btn_y
        self.LOBBY_BACK_BUTTON.rect.center = (self.LOBBY_BACK_BUTTON.x_pos, self.LOBBY_BACK_BUTTON.y_pos)
        if hasattr(self.LOBBY_BACK_BUTTON, "text_rect"):
            self.LOBBY_BACK_BUTTON.text_rect.center = self.LOBBY_BACK_BUTTON.rect.center
        self.LOBBY_BACK_BUTTON.check_hover(MENU_MOUSE_POS)
        self.LOBBY_BACK_BUTTON.update(self.SCREEN)

        try:
            self.avisoDeConexion(getattr(self.network_manager, 'mensaje', ''), getattr(self.network_manager, 'tiempoDelMensaje', 0))
        except Exception:
            pass

        return MENU_MOUSE_POS

    def lobbyMessage(self, text, max_chars = 40):
        words = text.split()
        if not words:
            return []
        lines = []
        cur = words[0]
        for w in words[1:]:
            if len(cur) + 1 + len(w) <= max_chars:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        return lines

    def get_game_font(self, size):
        scaled_size = max(8, int(size * self.SCALE))
        if scaled_size in self.cacheDeFuentes:
            return self.cacheDeFuentes[scaled_size]
        try:
            if os.path.exists(self.FONT_FILE):
                f = pygame.font.Font(self.FONT_FILE, scaled_size)
            else:
                f = pygame.font.SysFont("arial", scaled_size)
        except Exception:
            f = pygame.font.SysFont("arial", scaled_size)
        self.cacheDeFuentes[scaled_size] = f
        return f

    def avisoDeConexion(self, mensaje, tiempo):
        if not mensaje or not tiempo:
            return
        try:
            if time.time() - tiempo < 5:
                font_msg = self.get_game_font(18)
                lines = self.lobbyMessage(mensaje)
                line_h = font_msg.get_linesize()
                base_x = self.SCREEN_WIDTH // 2
                base_y = self.SCREEN_HEIGHT // 2 + self._s(160)
                total_h = line_h * len(lines)
                start_y = base_y - total_h // 2
                for i, line in enumerate(lines):
                    surf = font_msg.render(line, True, (255, 255, 255))
                    rect = surf.get_rect(center=(base_x, start_y + i * line_h))
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
                        self.SCREEN.blit(font_msg.render(line, True, (165, 42, 42)), (rect.x + dx, rect.y + dy))
                    self.SCREEN.blit(surf, rect)
        except Exception:
            return

    def options(self):
        pygame.display.set_caption("Opciones")
        game_rules = """Rummy 500
Objetivo: Ser el último jugador con menos de 500 puntos.

Jugadores: 2 - 13

Mazo: 52 cartas + 1 Joker.

Cómo ganar: El último jugador en acumular menos de 500 puntos gana la partida.
\nCómo perder: El primer jugador en alcanzar o superar los 500 puntos es eliminado.
\nCombinaciones:
\n• Trío: Tres cartas del mismo valor (ej: Q♦, Q♥, Q♠).
\n• Seguidilla: Cuatro cartas consecutivas del mismo palo (ej: 7♣, 8♣, 9♣, 10♣).

\nRondas de Juego:
\n1. Trío y Seguidilla
\n2. Dos Seguidillas
\n3. Tres Tríos
\n4. Una Seguidilla y Dos Tríos (Ronda Completa): Para finalizar esta ronda, el jugador debe descartar las diez cartas (la seguidilla de cuatro y los dos tríos) en un solo turno.

\nPuntuación:
\n• Cartas 2 - 9: 5 puntos
\n• Cartas 10 - K: 10 puntos
\n• As: 15 puntos
\n• Joker: 25 puntos

\nDesarrollo del Juego:
\n1. Inicio: Cada jugador recibe 10 cartas. Se coloca una carta boca arriba del mazo en el centro de la mesa para iniciar el descarte. Se designa un jugador como MANO.

\n2. Turno del MANO: Para la siguiente ronda, el rol de MANO pasa al jugador a la izquierda del MANO actual.


\n3. Primera Toma de la Carta Central: Solo el jugador MANO tiene la primera oportunidad de tomar la carta boca arriba del centro. Si decide tomarla, debe descartar una carta de su mano para mantener un total de 10 cartas. Si el MANO no toma la carta central, se pasa a la siguiente fase de toma.
\n4. Segunda Oportunidad de Toma de la Carta Central: Si el MANO no tomó la carta central, los demás jugadores, en orden hacia la izquierda del MANO, tienen la oportunidad de tomarla. El primer jugador que la tome debe robar una carta adicional del mazo como penalización, quedando con 12 cartas. Si nadie toma la carta central en esta segunda oportunidad, la carta se QUEMA y se descarta, quedando fuera de juego.
\n5. Turno Regular del Jugador: Después de la fase de toma de la carta central (haya sido tomada o quemada), y durante el resto de su turno, cada jugador puede realizar una de las siguientes acciones:
\n• Tomar la carta superior del mazo boca abajo (solo si no agarró la carta boca arriba o si agarra como penalización).
\n• Bajarse: Mostrar sobre la mesa las combinaciones de cartas requeridas para la ronda actual (tríos o seguidillas). Se puede usar un Joker para completar una combinación. Un Joker ya bajado puede ser reemplazado por la carta que representa y utilizado en otra combinación propia.
\n• Agregar cartas: Añadir cartas válidas a sus propias combinaciones ya bajadas (antes de descartar).
\n• Descartar: Colocar una carta boca arriba en el centro de la mesa para finalizar su turno.
\n6. Fin de la Ronda: Una ronda termina cuando un jugador se queda sin cartas al bajar todas sus combinaciones requeridas (y descartar si es necesario). El jugador que se quedó sin cartas será el primero en actuar en la siguiente ronda.
\n7. Puntuación de la Ronda: Los jugadores que no lograron bajarse suman los puntos de las cartas que aún tienen en su mano.
\n8. Fin de la Partida: El juego continúa a lo largo de las cuatro rondas. El ganador es el jugador con la menor puntuación total al final de las cuatro rondas, o el último jugador que no haya alcanzado o superado los 500 puntos."""
        box_w, box_h = self._s(600), self._s(300)
        box_x = self.SCREEN_WIDTH // 2 - box_w // 2
        box_y = self._s(140)

        rules_box = self.RulesTextBox(box_x + self._s(20), box_y + self._s(20), box_w - self._s(40), box_h - self._s(40), self.get_font(30), game_rules)

        options_back = Button(
            image=self.volver_img,
            pos=(self.SCREEN_WIDTH//2, box_y + box_h + self._s(40)),
            text_input="",
            font=self.get_font(50),
            base_color="White",
            hovering_color="Green",
            size=(self._s(250), self._s(110))
        )

        while True:
            delta_time = self.clock.tick(60) / 1000.0
            self.update_animation(delta_time)

            events = pygame.event.get()

            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.VIDEORESIZE:
                    self.SCREEN_WIDTH, self.SCREEN_HEIGHT = event.size
                    self.SCALE = min(self.SCREEN_WIDTH / REF_WIDTH, self.SCREEN_HEIGHT / REF_HEIGHT)
                    self.SCREEN = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
                    box_w, box_h = int(self.SCREEN_WIDTH * 0.7), int(self.SCREEN_HEIGHT * 0.6)
                    box_x = self.SCREEN_WIDTH // 2 - box_w // 2
                    box_y = self.SCREEN_HEIGHT // 2 - box_h // 2
                    rules_box.rect.topleft = (box_x + self._s(20), box_y + self._s(20))
                    rules_box._wrap_lines()
                    options_back.x_pos = self.SCREEN_WIDTH // 2
                    options_back.y_pos = box_y + box_h + self._s(40)

            self.draw_background()
            cuadro_surf = pygame.transform.scale(self.cuadro_img, (box_w + self._s(100), box_h + self._s(100)))
            self.SCREEN.blit(cuadro_surf, (self.SCREEN_WIDTH//2 - box_w//2 - self._s(60), box_y - self._s(50)))

            options_text = self.get_font(45).render("Reglas de Rummy 500", True, "White")
            options_rect = options_text.get_rect(center=(self.SCREEN_WIDTH//2, self._s(100)))
            bg_rect = options_rect.inflate(self._s(40), self._s(18))
            pygame.draw.rect(self.SCREEN, (80, 80, 80), bg_rect, border_radius=6)
            self.SCREEN.blit(options_text, options_rect)

            rules_box.update(events)
            rules_box.draw(self.SCREEN)

            mouse_pos = pygame.mouse.get_pos()
            options_back.check_hover(mouse_pos)
            options_back.update(self.SCREEN)

            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if options_back.checkForInput(mouse_pos):
                        return

            pygame.display.update()

    def lanzar_juego_ui2(self):
        import ui2
        ui2.main()
        self.SCREEN = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Menu Principal")

    def play_click(self):
        self.click_sound.play()

    def iniciar_duelo_bot(self, bot_name, model_file):
        """
        Arranca un duelo 1vs1 directo contra el bot elegido en la 'Sala de
        Bots': pide confirmación, y si se acepta, monta un servidor local
        (el propio jugador es el host) con exactamente ese bot como único
        rival, sin pasar por la pantalla de lobby.
        """
        if not self.confirm_bot_duel(bot_name):
            return None

        nombre_jugador = (self.bot_room_name_input.text or "").strip() or "Jugador"

        exito = self.network_manager.start_server(nombre_jugador, "", 2, f"Duelo vs {bot_name}")
        if not exito:
            print(f"[SALA DE BOTS] No se pudo iniciar el servidor local para el duelo contra {bot_name}.")
            return None

        self.network_manager.num_bots = 1
        self.network_manager.bot_duel_config = {"name": bot_name, "model_file": model_file}
        print(f"model_file cargado del bot: {str(model_file)}")

        if not self.network_manager.canStartGame():
            print("[SALA DE BOTS] No se pudo iniciar la partida (se necesitan al menos dos jugadores).")
            return None

        self.network_manager.startGame()
        self.network_manager.stop_broadcast()
        print(f"[SALA DE BOTS] Iniciando duelo 1vs1: {nombre_jugador} vs {bot_name}")

        time.sleep(1.2)
        return "launch_ui2"

    def handle_events(self):
        if not pygame.get_init():
            return False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.confirm_exit():
                    return False
                else:
                    continue

            if event.type == pygame.VIDEORESIZE:
                self.SCREEN_WIDTH, self.SCREEN_HEIGHT = event.size
                self.SCALE = min(self.SCREEN_WIDTH / REF_WIDTH, self.SCREEN_HEIGHT / REF_HEIGHT)
                self.SCREEN = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
                self.fondo_img = pygame.transform.scale(self.fondo_img_original, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
                self.titulo_img = pygame.transform.scale(self.titulo_img_original, (int(self.SCREEN_WIDTH * 0.5), int(self.SCREEN_HEIGHT * 0.35)))
                self.animacion_fondo_img = pygame.transform.scale(self.animacion_fondo_img, (self._s(1000), self._s(800)))
                self.pos_izquierda = (self._s(40), self._s(120))
                self.pos_derecha = (self._s(1230), self._s(120))
                self.init_components()

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
                        except Exception:
                            max_players = None
                        if max_players is None or max_players < 2 or max_players > 7:
                            self.invalid_players_until = pygame.time.get_ticks() + 2500
                            continue
                        exito = self.network_manager.start_server(nameHost, password, max_players,nameSala)
                        print("Servidor creado" if exito else "Error al crear servidor")
                        self.current_screen = "lobby"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.current_screen == "main":
                    if self.JUGAR_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.current_screen = "play"
                    elif self.REGLAS_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.options()
                    elif self.SALIR_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        if self.confirm_exit():
                            return False
                        else:
                            continue

                elif self.current_screen == "play":
                    if self.PLAY_BACK.checkForInput(event.pos):
                        self.play_click()
                        self.current_screen = "main"
                    elif self.UNIRSE_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.servers = self.network_manager.discoverServers()
                        self.response = ''
                        self.current_screen = "join"
                    elif self.CREAR_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.current_screen = "create"
                    elif self.SALA_BOTS_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load(resource_path(os.path.join(self.ASSETS_PATH, "sonido", "apocalypse.mp3")))
                        pygame.mixer.music.play(-1)
                        self.current_screen = "bot_room"

                elif self.current_screen == "bot_room":
                    if self.BOT_ROOM_BACK_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.current_screen = "play"
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load(resource_path(os.path.join(self.ASSETS_PATH, "sonido", "musica_fondo.mp3")))
                        pygame.mixer.music.play(-1)
                    elif getattr(self, "bot_room_louis_rect", None) and self.bot_room_louis_rect.collidepoint(event.pos):
                        self.play_click()
                        resultado = self.iniciar_duelo_bot("LouisBot", "LouisBot.pt")
                        if resultado == "launch_ui2":
                            return "launch_ui2"
                    elif getattr(self, "bot_room_gen_rect", None) and self.bot_room_gen_rect.collidepoint(event.pos):
                        self.play_click()
                        resultado = self.iniciar_duelo_bot("GeniBot", "GeniBot.pt")
                        if resultado == "launch_ui2":
                            return "launch_ui2"

                elif self.current_screen == "join":
                    if event.button == 1 and self.is_hovered:
                        self.play_click()
                        # discoverServers() es asíncrono (lanza un hilo y
                        # devuelve None de inmediato); la lista real se lee
                        # en vivo desde network_manager.servers cada frame
                        # dentro de draw_server_list_menu, así que aquí solo
                        # se dispara la búsqueda, sin sobreescribir self.servers.
                        self.network_manager.discoverServers()
                        # El índice tocado dentro del navegador siempre arranca
                        # limpio; no preselecciona la sala ya confirmada, para
                        # que el usuario deba tocarla de nuevo y confirmar con
                        # "Seleccionar" (evita seleccionar sin querer la
                        # sala anterior si la lista cambió).
                        self.selected_server_index = None
                        self.current_screen = "server_list"
                    if self.JOIN_BACK_BUTTON.checkForInput(event.pos):  # Botón "volver"
                        self.play_click()
                        self.current_screen = "play"  # Regresa al menú de jugar
                        self.response = ''
                    elif self.JOIN_REFREHS_BUTTON.checkForInput(event.pos): # Botón Actualizar
                        self.play_click()
                        self.servers = self.network_manager.discoverServers()
                        self.response = ''
                    elif self.JOIN_IP_BUTTON.checkForInput(event.pos):  # Botón "conectar"
                        password = self.join_password_input_box.text  # Obtiene la contraseña
                        playerName = self.join_player_input_box.text or "Jugador"

                        ip_manual = self.join_ip_manual_input.text.strip()
                        objetivo = None
                        if ip_manual:
                            # Conexión manual: no depende de haber elegido una
                            # sala en el navegador -pensado para cuando el
                            # descubrimiento automático no cruza la red (p.
                            # ej. jugando por Hamachi u otra VPN en vez de la
                            # misma LAN física)-. El puerto es opcional: si
                            # se deja vacío, se usa el puerto TCP por defecto.
                            puerto_texto = self.join_port_manual_input.text.strip()
                            try:
                                puerto_manual = int(puerto_texto) if puerto_texto else self.network_manager.config.TCP_PORT
                            except ValueError:
                                puerto_manual = self.network_manager.config.TCP_PORT
                            objetivo = {
                                "ip": ip_manual,
                                "port": puerto_manual,
                                "name": "Conexión manual",
                                "password": password,
                                "playerName": playerName,
                                "currentPlayers": 0,
                                "max_players": 0,
                            }
                        elif self.selectedServer:
                            objetivo = self.selectedServer
                            objetivo['password'] = password
                            if self.join_player_input_box.text != "":
                                playerName = self.join_player_input_box.text  
                            else:  
                                playerName = f"Jugador {self.selectedServer['currentPlayers']}"  # Valor por defecto
                            objetivo['playerName'] = playerName
                            pygame.display.update()
                            print(f"Esto esta en el Server {objetivo}")

                        if objetivo:
                            acep, resp = self.network_manager.connectToServer(objetivo)
                            if acep:
                                objetivo['currentPlayers'] = objetivo.get('currentPlayers', 0) + 1
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
                                    # fallback: guardar texto original para debug y mostrar mensaje genérico
                                    self.response = resp or ""
                                    self.fullserver_until = pygame.time.get_ticks() + 2000
                                    print(f"Respuesta no esperada al conectar: {resp}")
                        else:
                            self.response = "No ha seleccionado una sala"
                            self.no_server_until = pygame.time.get_ticks() + 2000
                            print("No ha seleccionado una sala")

                elif self.current_screen == "server_list":  # Navegador de salas
                    if event.button == 1:
                        for i, bar_rect in enumerate(getattr(self, "server_list_bar_rects", [])):
                            if bar_rect.collidepoint(event.pos):
                                self.play_click()
                                self.selected_server_index = i
                                break
                    if self.SERVER_LIST_BACK_BUTTON.checkForInput(event.pos):  # Botón "volver"
                        self.play_click()
                        self.current_screen = "join"  # Regresa a la ventanita anterior sin seleccionar nada
                    elif self.SERVER_LIST_SELECT_BUTTON.checkForInput(event.pos):  # Botón "seleccionar"
                        self.play_click()
                        if self.selected_server_index is None or self.selected_server_index >= len(self.servers):
                            self.server_list_alert_until = pygame.time.get_ticks() + 2500
                        else:
                            self.selectedServer = self.servers[self.selected_server_index]
                            self.isSeletedServer = True
                            self.current_screen = "join"  # Vuelve a la ventanita de nombre/contraseña

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
                        password = self.password_input_box.text
                        try:
                            max_players = int(self.max_players_input_box.text)
                        except Exception:
                            max_players = None
                        if max_players is None or max_players < 2 or max_players > 7:
                            self.invalid_players_until = pygame.time.get_ticks() + 2500
                            continue
                        try:
                            num_bots = int(self.num_bots_input_box.text)
                        except Exception:
                            num_bots = 0
                        if num_bots < 0 or num_bots > 6:
                            self.invalid_players_until = pygame.time.get_ticks() + 2500
                            continue
                        exito = self.network_manager.start_server(nameHost, password, max_players,nameSala)
                        self.network_manager.num_bots = num_bots
                        print("Servidor creado" if exito else "Error al crear servidor")
                        print(self.network_manager.host,self.network_manager.gameName)
                        print(f"Bots configurados para esta sala: {num_bots}")
                        self.current_screen = "lobby"  # Cambia a la pantalla lobby
                
                elif self.current_screen == "lobby":  # Si estamos en la pantalla de lobby
                    
                    # --- NUEVO: CLICK EN EL BOTÓN MOSTRAR/OCULTAR CHAT ---
                    if hasattr(self, "TOGGLE_CHAT_BUTTON") and self.TOGGLE_CHAT_BUTTON.checkForInput(event.pos):
                        self.play_click()
                        self.show_chat = not getattr(self, "show_chat", False)
                        if self.show_chat and hasattr(self.network_manager, "clear_chat_notification"):
                            self.network_manager.clear_chat_notification()

                    elif self.LOBBY_BACK_BUTTON.checkForInput(event.pos):
                        self.current_screen = "play"
                        self.network_manager.connected_players.clear()
                        # leave_room() hace un reseteo COMPLETO (no solo cerrar
                        # sockets): limpia player_id, mensajes en cola,
                        # jugadores conectados, etc. Sin esto, unirse después
                        # a una sala DISTINTA podía arrastrar datos de esta
                        # sesión y comportarse como si siguiera conectado aquí.
                        self.network_manager.leave_room()
                        # No usar self.selectedServer.clear(): ese diccionario
                        # puede ser la MISMA referencia que sigue viva dentro
                        # de la lista de salas descubiertas, así que
                        # vaciarlo in-place podía afectar a otras partes que
                        # aún lo referenciaran. Basta con soltar la referencia.
                        self.selectedServer = None
                        self.isSeletedServer = False
                        self.selected_server_index = None
                        self.servers = []
                        print(f"Servidor cerrado...")
                    
                    elif self.PLAY_GAME_BUTTON.checkForInput(event.pos):
                        if self.network_manager.is_host:
                            if self.network_manager.canStartGame():
                                self.network_manager.startGame()
                                self.network_manager.stop_broadcast()
                                print("Cerrada la transmision de la informacion del servido. Juego iniciado")

                                import time
                                time.sleep(1.2)

                                return "launch_ui2"
                            else:
                                print("Se necesitan al menos dos jugadores")
                        else:
                            print("Esperando al host para iniciar el juego...")

                    elif getattr(self, "show_chat", False) and self.SEND_MS_BUTTON.checkForInput(event.pos):
                        msg = self.message_input_box.text.strip()
                        if msg:
                            self.network_manager.send_chat_message(msg)
                            self.message_input_box.text = ""
                            self.message_input_box.txt_surface = self.get_font(20).render("", True, (0,0,0))
                            if self.network_manager.player:
                                success = self.network_manager.sendData(("chat_messages",msg))
                                if success:
                                    formattedMsg = f"Tú: {msg}"
                                    with self.chatLock:
                                        self.network_manager.messagesServer.append(formattedMsg)

            if self.current_screen == "join":
                self.join_player_input_box.handle_event(event)
                self.join_password_input_box.handle_event(event)
                self.join_port_manual_input.handle_event(event)
                self.join_ip_manual_input.handle_event(event)
            elif self.current_screen == "create":
                self.host_input_box.handle_event(event)
                self.name_input_box.handle_event(event)
                self.password_input_box.handle_event(event)
                self.max_players_input_box.handle_event(event)
                self.num_bots_input_box.handle_event(event)
            elif self.current_screen == "lobby" and getattr(self, "show_chat", False):
                self.message_input_box.handle_event(event)
            elif self.current_screen == "bot_room":
                self.bot_room_name_input.handle_event(event)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and getattr(self.message_input_box, "active", False) and getattr(self, "show_chat", False):
                    msg = self.message_input_box.text.strip()
                    if msg != "":
                        self.network_manager.send_chat_message(msg)
                        self.message_input_box.text = ""
                        self.message_input_box.txt_surface = self.get_font(20).render("", True, (0,0,0))
                        if getattr(self.network_manager, "player", False):
                            try:
                                success = self.network_manager.sendData(("chat_messages", msg))
                            except Exception:
                                success = False
                            if success:
                                formattedMsg = f"Tú: {msg}"
                                with self.chatLock:
                                    self.network_manager.messagesServer.append(formattedMsg)
                        self.message_input_box.text = ""
                        self.message_input_box.txt_surface = self.get_font(20).render("", True, (0,0,0))

        process_message = self.process_received_messages()
        if process_message == "launch_ui2":
            return process_message
        return True

    def process_received_messages(self):
        if hasattr(self.network_manager,'receivedData') and self.network_manager.receivedData:
            with self.network_manager.lock:
                data = self.network_manager.receivedData
                self.network_manager.receivedData = None

            if isinstance(data,dict) and data.get("type") == "START_GAME":
                return "launch_ui2"

            if isinstance(data,dict) and data.get("players"):
                players = data.get("players")
                return players

            if isinstance(data, str) and ":" in data:
                with self.chatLock:
                    if not (data.startswith("Tú:") or (self.network_manager.is_host and data.startswith(f"{self.network_manager.playerName}:"))):
                        self.network_manager.messagesServer.append(data)
                        if len(self.network_manager.messagesServer) > 20:
                            self.network_manager.messagesServer = self.network_manager.messagesServer[-20:]

    def update(self):
        delta_time = self.clock.tick(60) / 1000.0
        self.update_animation(delta_time)

        if self.current_screen == "bot_room":
            # Pantalla con fondo propio: no dibujamos el fondo/título del menú principal.
            self.draw_bot_room_background()
        else:
            self.draw_background()
            title_rect = self.titulo_img.get_rect(center=(self.SCREEN_WIDTH//2, int(self.SCREEN_HEIGHT*0.25)))
            self.SCREEN.blit(self.titulo_img, title_rect)

        if self.current_screen == "join":
            self.join_player_input_box.update()
            self.join_password_input_box.update()
        elif self.current_screen == "create":
            self.host_input_box.update()
            self.name_input_box.update()
            self.password_input_box.update()
            self.max_players_input_box.update()
            self.num_bots_input_box.update()
        elif self.current_screen == "lobby":
            self.message_input_box.update()
        elif self.current_screen == "bot_room":
            self.bot_room_name_input.update()

        if self.current_screen == "main":
            mouse_pos = self.draw_main_menu()
            for button in [self.JUGAR_BUTTON, self.REGLAS_BUTTON, self.SALIR_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "play":
            mouse_pos = self.draw_play_menu()
            for button in [self.UNIRSE_BUTTON, self.CREAR_BUTTON, self.SALA_BOTS_BUTTON, self.PLAY_BACK]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "join":
            mouse_pos = self.draw_join_menu()
            for button in [self.JOIN_IP_BUTTON, self.JOIN_REFREHS_BUTTON, self.JOIN_BACK_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "server_list":
            mouse_pos = self.draw_server_list_menu()
            for button in [self.SERVER_LIST_BACK_BUTTON, self.SERVER_LIST_SELECT_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "create":  
            mouse_pos = self.draw_create_menu()
            for button in [self.CREATE_GAME_BUTTON, self.CREATE_BACK_BUTTON]:
                button.check_hover(mouse_pos)

        elif self.current_screen == "lobby":
            mouse_pos = self.draw_lobby()

        elif self.current_screen == "bot_room":
            mouse_pos = self.draw_bot_room_menu()
            self.BOT_ROOM_BACK_BUTTON.check_hover(mouse_pos)

        pygame.display.update()
        return True

    class RulesTextBox:
        def __init__(self, x, y, w, h, font, text):
            self.rect = pygame.Rect(x, y, w, h)
            self.font = font
            self.text = text
            self.lines = []
            self._wrap_lines()
            self.scroll_offset = 0
            self.line_height = int(self.font.get_height() * 1.35)

        def _wrap_lines(self):
            paragraphs = self.text.split("\n\n")
            wrapped = []
            max_width = self.rect.w - 20
            for para in paragraphs:
                words = para.split()
                if not words:
                    wrapped.append("")
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
                wrapped.append("")
            if wrapped and wrapped[-1] == "":
                wrapped.pop()
            self.lines = wrapped

        def update(self, events):
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.rect.collidepoint(event.pos):
                        if event.button == 4:
                            self.scroll_offset = max(self.scroll_offset - self.line_height, 0)
                        elif event.button == 5:
                            max_offset = max(0, len(self.lines) * self.line_height - self.rect.h + 20)
                            self.scroll_offset = min(self.scroll_offset + self.line_height, max_offset)

        def draw(self, screen):
            pygame.draw.rect(screen, (150, 150, 150), self.rect, 2, border_radius=12)
            clip_rect = screen.get_clip()
            screen.set_clip(self.rect)
            y = self.rect.y + 10 - self.scroll_offset
            for line in self.lines:
                if line == "":
                    y += int(self.line_height * 0.6)
                else:
                    rendered = self.font.render(line, True, (255, 255, 255))
                    if y + rendered.get_height() > self.rect.y and y < self.rect.y + self.rect.h:
                        screen.blit(rendered, (self.rect.x + 10, y))
                    y += self.line_height
                if y > self.rect.y + self.rect.h + self.line_height:
                    break
            screen.set_clip(clip_rect)

    def confirm_exit(self):
        clock = pygame.time.Clock()
        try:
            snapshot = self.SCREEN.copy()
        except:
            snapshot = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))

        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))

        w, h = self._s(560), self._s(260)
        x = (self.SCREEN_WIDTH - w) // 2
        y = (self.SCREEN_HEIGHT - h) // 2
        modal_rect = pygame.Rect(x, y, w, h)

        btn_w, btn_h = self._s(130), self._s(50)
        btn_si = pygame.Rect(x + self._s(80), y + self._s(160), btn_w, btn_h)
        btn_no = pygame.Rect(x + w - btn_w - self._s(80), y + self._s(160), btn_w, btn_h)

        font_title = self.get_font(38)
        font_text = self.get_font(20)

        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return False
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if btn_si.collidepoint(ev.pos):
                        return True
                    if btn_no.collidepoint(ev.pos):
                        return False

            self.SCREEN.blit(snapshot, (0, 0))
            self.SCREEN.blit(overlay, (0, 0))

            pygame.draw.rect(self.SCREEN, (40, 40, 40), modal_rect, border_radius=12)
            pygame.draw.rect(self.SCREEN, (200, 50, 50), modal_rect, 3, border_radius=12)

            title = font_title.render("¿SALIR?", True, (255, 255, 255))
            self.SCREEN.blit(title, (x + (w - title.get_width())//2, y + self._s(30)))

            info = font_text.render("¿Seguro quieres salir?", True, (200, 200, 200))
            self.SCREEN.blit(info, (x + (w - info.get_width())//2, y + self._s(95)))

            pygame.draw.rect(self.SCREEN, (50, 180, 50), btn_si, border_radius=8)
            lbl_si = font_text.render("SÍ", True, (255, 255, 255))
            self.SCREEN.blit(lbl_si, lbl_si.get_rect(center=btn_si.center))

            pygame.draw.rect(self.SCREEN, (180, 50, 50), btn_no, border_radius=8)
            lbl_no = font_text.render("NO", True, (255, 255, 255))
            self.SCREEN.blit(lbl_no, lbl_no.get_rect(center=btn_no.center))

            pygame.display.flip()
            clock.tick(60)

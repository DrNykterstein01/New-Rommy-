"""
Pantalla de carga que se muestra mientras se cargan los modelos de IA de
los bots antes de iniciar una partida (ui2.main()). Sin esto, cargar los
modelos entrenados (.pt) deja la ventana en negro y en silencio unos
segundos, lo cual no se ve nada bien.

Muestra:
- Un fondo que va alternando entre varias imágenes relacionadas al Rummy,
  con un fundido (fade) suave entre una y la siguiente.
- Un texto centrado: "Cargando modelos de IA, la partida empezará en breve".
- Música de fondo ("espera.mp3") mientras dura la carga.

La carga real de los modelos ocurre en un hilo aparte (la función que se le
pase en `worker_fn`); este módulo solo se encarga de animar la pantalla en
el hilo principal (las llamadas a pygame.display deben hacerse siempre
desde el hilo principal) hasta que ese hilo termine, y le devuelve a quien
lo llamó el resultado de `worker_fn`.
"""

import os
import sys
import threading
import pygame


def resource_path(relative_path):
    """Misma lógica que en main.py / ui2.py: soporta ejecutarse empaquetado
    con PyInstaller (sys._MEIPASS) o directamente desde el código fuente."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# Nombres de archivo esperados para las 5 imágenes de fondo de la pantalla
# de carga. El usuario los coloca en assets/carga_ia/.
NOMBRES_IMAGENES_CARGA = [
    "rummy1.jpg",
    "rummy2.jpg",
    "rummy3.jpg",
    "rummy4.jpg",
    "rummy5.jpg",
]

# Cuánto tiempo (en segundos) se muestra cada imagen antes de empezar a
# desvanecerse hacia la siguiente, y cuánto dura ese desvanecimiento.
TIEMPO_POR_IMAGEN = 3.2
DURACION_FADE = 1.1

TEXTO_CARGA = "Cargando modelos de Idtedijezia Adtifizial, la partida empezará en breve"


def _cargar_imagenes_fondo(screen_width, screen_height):
    """Carga y escala las imágenes de fondo disponibles. Si falta alguna
    (o todas), simplemente se ignora -se anima con las que sí existan-,
    y si no hay ninguna se usa un fondo sólido como respaldo."""
    imagenes = []
    for nombre in NOMBRES_IMAGENES_CARGA:
        ruta = resource_path(os.path.join("assets", "pantalla_carga", nombre))
        try:
            img = pygame.image.load(ruta).convert()
            img = pygame.transform.scale(img, (screen_width, screen_height))
            imagenes.append(img)
        except Exception as e:
            print(f"[CARGA IA] No se pudo cargar '{nombre}' ({e}), se omite.")
    return imagenes


def _reproducir_musica_espera():
    try:
        ruta_musica = resource_path(os.path.join("assets", "sonido", "espera.mp3"))
        pygame.mixer.music.load(ruta_musica)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print(f"[CARGA IA] No se pudo reproducir 'espera.mp3' ({e}).")


def mostrar_pantalla_carga(screen, screen_width, screen_height, worker_fn):
    """
    Muestra la animación de carga en `screen` mientras `worker_fn` corre en
    un hilo aparte, y devuelve lo que `worker_fn` haya retornado.

    `worker_fn` debe ser una función sin argumentos (usar functools.partial
    o una lambda si necesita parámetros) que NO haga llamadas a pygame.display
    (esas deben quedar siempre en el hilo principal).
    """
    resultado = {}
    excepcion = {}

    def _correr_worker():
        try:
            resultado["valor"] = worker_fn()
        except Exception as e:
            excepcion["error"] = e

    hilo = threading.Thread(target=_correr_worker, daemon=True)
    hilo.start()

    if not pygame.mixer.get_init():
        pygame.mixer.init()
    _reproducir_musica_espera()

    imagenes = _cargar_imagenes_fondo(screen_width, screen_height)

    try:
        font_path = resource_path(os.path.join("assets", "pixel.ttf"))
        fuente = pygame.font.Font(font_path, max(18, int(screen_height * 0.035)))
    except Exception:
        fuente = pygame.font.SysFont("arial", max(18, int(screen_height * 0.035)))

    texto_surf = fuente.render(TEXTO_CARGA, True, (255, 255, 255))

    clock = pygame.time.Clock()
    indice_actual = 0
    tiempo_acumulado = 0.0

    # Puntos suspensivos animados, para reforzar la sensación de "sigue
    # trabajando" incluso si la carga real tarda bastante.
    puntos_tiempo = 0.0
    puntos_cantidad = 0

    while hilo.is_alive():
        dt = clock.tick(60) / 1000.0
        tiempo_acumulado += dt
        puntos_tiempo += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # No cerramos la app acá (la carga sigue en segundo plano);
                # simplemente ignoramos el intento de cierre hasta que
                # termine, para no dejar el hilo de carga huérfano.
                pass
            elif event.type == pygame.VIDEORESIZE:
                screen_width, screen_height = event.size
                screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
                imagenes = _cargar_imagenes_fondo(screen_width, screen_height)

        # --- Fondo con transición (fade) entre imágenes ---
        if imagenes:
            n = len(imagenes)
            ciclo = TIEMPO_POR_IMAGEN + DURACION_FADE
            indice_actual = int(tiempo_acumulado // ciclo) % n
            t_en_ciclo = tiempo_acumulado % ciclo
            img_actual = imagenes[indice_actual]
            screen.blit(img_actual, (0, 0))

            if t_en_ciclo > TIEMPO_POR_IMAGEN:
                progreso = (t_en_ciclo - TIEMPO_POR_IMAGEN) / DURACION_FADE
                progreso = max(0.0, min(1.0, progreso))
                img_siguiente = imagenes[(indice_actual + 1) % n]
                img_siguiente = img_siguiente.copy()
                img_siguiente.set_alpha(int(255 * progreso))
                screen.blit(img_siguiente, (0, 0))
        else:
            screen.fill((15, 15, 20))

        # --- Overlay oscuro semitransparente para que el texto se lea bien ---
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 110))
        screen.blit(overlay, (0, 0))

        # --- Texto centrado, con puntos suspensivos animados ---
        if puntos_tiempo >= 0.45:
            puntos_tiempo = 0.0
            puntos_cantidad = (puntos_cantidad + 1) % 4
        texto_final = TEXTO_CARGA + ("." * puntos_cantidad)
        texto_surf = fuente.render(texto_final, True, (255, 255, 255))
        texto_rect = texto_surf.get_rect(center=(screen_width // 2, int(screen_height * 0.88)))

        fondo_texto = pygame.Surface((texto_rect.w + 40, texto_rect.h + 24), pygame.SRCALPHA)
        fondo_texto.fill((0, 0, 0, 140))
        fondo_texto_rect = fondo_texto.get_rect(center=texto_rect.center)
        screen.blit(fondo_texto, fondo_texto_rect)
        screen.blit(texto_surf, texto_rect)

        pygame.display.update()

    pygame.mixer.music.stop()

    if "error" in excepcion:
        raise excepcion["error"]
    return resultado.get("valor")

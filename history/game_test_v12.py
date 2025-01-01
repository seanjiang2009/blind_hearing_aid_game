from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import time as t
import mss
import numpy
import os
import numpy as np
from scipy import ndimage
import threading
import pygame

# Game Settings
game_section_duration = 120
obstacle_num = 100
max_range_threshold = 300

# Initialize pygame mixer
pygame.init()
pygame.mixer.init(channels=6)

# Sound Settings
sound_folder = "music_3"  # Update this folder to your correct path
left_sound = pygame.mixer.Sound(os.path.join(sound_folder, "quincys_shaker_1M_far_left.mp3"))
center_up_sound = pygame.mixer.Sound(os.path.join(sound_folder, "string_chords_1M_center.mp3"))
center_mid_sound = pygame.mixer.Sound(os.path.join(sound_folder, "string_chords_1M_center.mp3"))
center_down_sound = pygame.mixer.Sound(os.path.join(sound_folder, "Electric_bass_center_bottom.mp3"))
right_sound = pygame.mixer.Sound(os.path.join(sound_folder, "bennys_drums_1M_far_right.mp3"))
crash_sound = pygame.mixer.Sound(os.path.join(sound_folder, "lose.mp3"))

# Channel Setup
left_channel = pygame.mixer.Channel(0)
center_up_channel = pygame.mixer.Channel(1)
center_mid_channel = pygame.mixer.Channel(2)
center_down_channel = pygame.mixer.Channel(3)
right_channel = pygame.mixer.Channel(4)
crash_channel = pygame.mixer.Channel(5)

# Play sounds on their channels and loop them
left_channel.play(left_sound, loops=-1)
center_up_channel.play(center_up_sound, loops=-1)
center_mid_channel.play(center_mid_sound, loops=-1)
center_down_channel.play(center_down_sound, loops=-1)
right_channel.play(right_sound, loops=-1)
crash_channel.play(crash_sound, loops=-1)

# Set all volumes to 0 initially
left_channel.set_volume(0)
center_up_channel.set_volume(0)
center_mid_channel.set_volume(0)
center_down_channel.set_volume(0)
right_channel.set_volume(0)
crash_channel.set_volume(0)

# Audio refresh rate
audio_refresh_rate = 0.3

# Ursina App Setup
app = Ursina()
application.vsync = False
application.time_scale = 0.5

start_time = t.time()
player = FirstPersonController()
player.cursor.visible = False
player.speed = 10
player.start_position = Vec3(0, 0, 0)
player.collider = BoxCollider(player, size=(1, 2, 1))
player.position = player.start_position

# Window Settings
window.position = (0, 0)
window.size = (1910, 1070)

# Screen Capture Monitor
monitor = {"top": window.position[1], "left": window.position[0], "width": window.size[0], "height": window.size[1]}

# Depth Map Shader
# Depth Map Shader

depth_map_shader = Shader(language=Shader.GLSL, vertex='''
    #version 120

    attribute vec4 p3d_Vertex;
    uniform mat4 p3d_ModelViewProjectionMatrix;

    varying float depth;

    void main() {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
        depth = 1 - gl_Position.z / 50;
    }
''', fragment='''
    #version 120

    varying float depth;

    void main() {
        gl_FragColor = vec4(1.0 - depth, 0.0, depth, 1.0); // Map depth to red and blue channels
    }
''')
# Entities
floor = Entity(model='plane', scale=(100, 1, 100), texture='white_cube', collider='box', color=color.black, shader=depth_map_shader)
walls = [Entity(model='cube', scale=(100, 50, 1), position=Vec3(0, 2.5, 50), collider='cube', color=color.black, shader=depth_map_shader),
         Entity(model='cube', scale=(100, 50, 1), position=Vec3(0, 2.5, -50), collider='cube', color=color.black, shader=depth_map_shader),
         Entity(model='cube', scale=(1, 50, 100), position=Vec3(50, 2.5, 0), collider='cube', color=color.black, shader=depth_map_shader),
         Entity(model='cube', scale=(1, 50, 100), position=Vec3(-50, 2.5, 0), collider='cube', color=color.black, shader=depth_map_shader)]

obstacles = [Entity(model='cube', scale=(2, random.randint(5, 20), 2), position=Vec3(random.randint(-48, 48), 1, random.randint(-48, 48)), collider='box', color=color.blue) for _ in range(obstacle_num)]

for obstacle in obstacles:
    obstacle.shader = depth_map_shader

# Restart Game
def restart_game():
    global start_time
    player.position = player.start_position
    start_time = t.time()

# Depth Processing
def get_depth_from_image(depth_image, threshold=100):
    resampled = ndimage.zoom(depth_image, (64 / depth_image.shape[0], 48 / depth_image.shape[1]), order=0)
    portions = {
        "left": resampled[:, :21],
        "center_up": resampled[:16, 21:42],
        "center_mid": resampled[16:32, 21:42],
        "center_down": resampled[32:, 21:42],
        "right": resampled[:, 42:]
    }
    factor = 255
    means = {}
    for key, portion in portions.items():
        mean = np.mean(portion)
        means[key] = max(0, (10 ** (1 - mean / factor) - 1) / 10) if mean < threshold else 0
    return means

# Update Logic
def update():
    global start_time
    section_time = t.time() - start_time
    if held_keys['q']:
        application.quit()
    if section_time > game_section_duration:
        restart_game()
    for wall in walls + obstacles:
        if player.intersects(wall).hit:
            crash_channel.set_volume(1)
            t.sleep(0.5)  # Slight delay for crash sound
            crash_channel.set_volume(0)
            restart_game()

# Depth-to-Audio Thread
def depth_to_audio_thread():
    while True:
        with mss.mss() as sct:
            img = numpy.array(sct.grab(monitor))
            depths = get_depth_from_image(img[:, :, 2])
            left_channel.set_volume(depths["left"])
            center_up_channel.set_volume(depths["center_up"])
            center_mid_channel.set_volume(depths["center_mid"])
            center_down_channel.set_volume(depths["center_down"])
            right_channel.set_volume(depths["right"])
            t.sleep(audio_refresh_rate)

threading.Thread(target=depth_to_audio_thread, daemon=True).start()

app.run()
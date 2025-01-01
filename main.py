# Import necessary modules
from ursina import *  # Ursina game engine
from ursina.prefabs.first_person_controller import FirstPersonController  # First-person controller prefab
import random  # For generating random positions and scales
import time as t  # For tracking game time
import mss  # For screen capturing
import numpy  # For processing image data
import os  # For file path handling
import numpy as np  # For advanced mathematical and array operations
from scipy import ndimage  # For image processing
import threading  # For running threads
import pygame  # For handling sounds

# Game configuration variables
game_section_duration = 120  # Duration of each game section in seconds
obstacle_num = 100  # Number of obstacles
max_range_threshold = 300  # Threshold for depth values

# Initialize pygame for audio
pygame.init()
pygame.mixer.init(channels=7)  # Initialize 7 audio channels

# Sound files for the game
sound_folder = "music_3"  # Folder containing audio files
far_left_sound = pygame.mixer.Sound(os.path.join(sound_folder, "quincys_shaker_1M_far_left.mp3"))
#center_sound = pygame.mixer.Sound(os.path.join(sound_folder, "string_chords_1M_center.mp3"))
far_right_sound = pygame.mixer.Sound(os.path.join(sound_folder, "bennys_drums_1M_far_right.mp3"))
#center_up_sound = pygame.mixer.Sound(os.path.join(sound_folder, "string_chords_1M_center.mp3"))
center_down_sound = pygame.mixer.Sound(os.path.join(sound_folder, "Electric_bass_center_bottom.mp3"))
center_mid_sound = pygame.mixer.Sound(os.path.join(sound_folder, "string_chords_1M_center.mp3"))
left_sound = pygame.mixer.Sound(os.path.join(sound_folder, "quincys_shaker_1M_left.mp3"))
right_sound = pygame.mixer.Sound(os.path.join(sound_folder, "bennys_drums_1M_right.mp3"))
crash_sound = pygame.mixer.Sound(os.path.join(sound_folder, "lose.mp3"))  # Sound for collisions


# Assign channels for each sound
left_channel = pygame.mixer.Channel(0)
#center_channel = pygame.mixer.Channel(1)
far_left_channel = pygame.mixer.Channel(1)
right_channel = pygame.mixer.Channel(2)
far_right_channel = pygame.mixer.Channel(3)
#center_up_channel = pygame.mixer.Channel(3)
center_down_channel = pygame.mixer.Channel(4)
center_mid_channel = pygame.mixer.Channel(5)
crash_channel = pygame.mixer.Channel(6)

# Play background sounds on loop
left_channel.play(left_sound, loops=-1)
far_left_channel.play(far_left_sound, loops=-1)
#center_channel.play(center_sound, loops=-1)
right_channel.play(right_sound, loops=-1)
far_right_channel.play(far_right_sound, loops=-1)
#center_up_channel.play(center_up_sound, loops=-1)
center_down_channel.play(center_down_sound, loops=-1)
center_mid_channel.play(center_mid_sound, loops=-1)

# Mute all channels initially
left_channel.set_volume(0)
far_left_channel.set_volume(0)
#center_channel.set_volume(0)
right_channel.set_volume(0)
far_right_channel.set_volume(0)
#center_up_channel.set_volume(0)
center_down_channel.set_volume(0)
center_mid_channel.set_volume(0)

# Audio refresh rate in seconds
audio_refresh_rate = 0.3

# Initialize the Ursina app
app = Ursina()
application.vsync = False  # Disable vertical sync for better performance
application.time_scale = 0.5  # Slow down the game

# Track game start time
start_time = t.time()

# Create a first-person player
player = FirstPersonController()
player.cursor.visible = False  # Hide the cursor
player.speed = 10  # Movement speed
player.start_position = Vec3(0, 0, 0)  # Initial position
player.collider = BoxCollider(player, size=(1, 2, 1))  # Collider for the player
player.position = player.start_position

# Configure window size and position
window.position = (0, 0)
window.size = (1280, 960)  # Fullscreen resolution
monitor = {"top": window.position[0], "left": window.position[1], "width": window.size[0], "height": window.size[1]}

# Shader for depth mapping
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

# Create floor and walls with shaders
floor = Entity(model='plane', scale=(100, 1, 100), texture='white_cube', collider='box', color=color.black, shader=depth_map_shader)
walls = [
    Entity(model='cube', scale=(100, 50, 1), position=Vec3(0, 2.5, 50), collider='cube', color=color.black, shader=depth_map_shader),
    Entity(model='cube', scale=(100, 50, 1), position=Vec3(0, 2.5, -50), collider='cube', color=color.black, shader=depth_map_shader),
    Entity(model='cube', scale=(1, 50, 100), position=Vec3(50, 2.5, 0), collider='cube', color=color.black, shader=depth_map_shader),
    Entity(model='cube', scale=(1, 50, 100), position=Vec3(-50, 2.5, 0), collider='cube', color=color.black, shader=depth_map_shader),
]

# Generate obstacles randomly within the game area
obstacles = [Entity(model='cube', scale=(2, random.randint(5, 20), 2), position=Vec3(random.randint(-48, 48), 1, random.randint(-48, 48)), collider='box', color=color.blue) for _ in range(obstacle_num)]
for obstacle in obstacles:
    obstacle.shader = depth_map_shader

# Function to restart the game
def restart_game():
    global start_time
    player.position = player.start_position  # Reset player position
    start_time = t.time()  # Reset game start time

# Process depth image into audio channels
def get_depth_from_image(depth_image, threshold=100):
    resampled_depth_image = ndimage.zoom(depth_image, (64 / depth_image.shape[0], 48 / depth_image.shape[1]), order=0)
    # Divide the depth image into sections for spatial sound processing
    far_left = resampled_depth_image[:, :10]
    left = resampled_depth_image[:, 10:21]
    #center_up = resampled_depth_image[:16, 21:42]
    center_mid = resampled_depth_image[:32, 21:42]
    center_down = resampled_depth_image[32:, 21:41]
    right = resampled_depth_image[:, 41:52]
    far_right = resampled_depth_image[:, 52:]

    # Normalize depth values and compute volumes for audio channels
    factor = 255
    def compute_mean(section):
        mean = np.mean(section)
        if mean < threshold:
            mean = 1 - mean / factor
        else:
            mean = 0
        return (10**mean - 1) / 10

    return compute_mean(far_left), compute_mean(left), compute_mean(center_mid), compute_mean(center_down), compute_mean(right), compute_mean(far_right)

# Main game update function
def update():
    global start_time
    section_time = t.time() - start_time
    if held_keys['q']:
        application.quit()  # Exit the game
    if section_time > game_section_duration:
        restart_game()
    # Collision detection
    for wall in walls:
        if player.intersects(wall).hit:
            crash_channel.play(crash_sound)
            restart_game()
    for obstacle in obstacles:
        if player.intersects(obstacle).hit:
            crash_channel.play(crash_sound)
            restart_game()

# Background thread for depth-to-audio processing
def depth_to_audio_thread():
    while True:
        with mss.mss() as sct:
            img = numpy.array(sct.grab(monitor))
            far_left, left, center_mid, center_down, right, far_right = get_depth_from_image(img[:, :, 2])
            far_left_channel.set_volume(far_left)
            left_channel.set_volume(left)
            #center_up_channel.set_volume(center_up)
            center_mid_channel.set_volume(center_mid)
            center_down_channel.set_volume(center_down)
            right_channel.set_volume(right)
            far_right_channel.set_volume(far_right)
            time.sleep(audio_refresh_rate)

# Start the audio thread
threading.Thread(target=depth_to_audio_thread, daemon=True).start()

# Run the game
app.run()
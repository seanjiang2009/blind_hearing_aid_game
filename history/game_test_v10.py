from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import time as t
import mss
import numpy
import os
import numpy as np
from scipy import ndimage
from pydub import AudioSegment #conda install pyAudio
from pydub.playback import play
import threading
import pygame

game_section_duration = 120
obstacle_num = 100
max_range_threshold = 300

pygame.init()
pygame.mixer.init(channels=7)

# sound_folder = "Y:\\Local_Documents\\python_code\\blindsensor\music"
# left_sound = pygame.mixer.Sound(os.path.join(sound_folder, "piano.mp3"))
# center_sound = pygame.mixer.Sound(os.path.join(sound_folder, "choir.mp3"))
# right_sound = pygame.mixer.Sound(os.path.join(sound_folder, "harp.mp3"))
# center_up_sound = pygame.mixer.Sound(os.path.join(sound_folder, "piano.mp3"))
# center_down_sound = pygame.mixer.Sound(os.path.join(sound_folder, "bass.mp3"))
# center_mid_sound = pygame.mixer.Sound(os.path.join(sound_folder, "choir.mp3"))
# crash_sound = pygame.mixer.Sound(os.path.join(sound_folder, "drum.mp3"))

sound_folder = "music2"
left_sound = pygame.mixer.Sound(os.path.join(sound_folder, "left.mp3"))
center_sound = pygame.mixer.Sound(os.path.join(sound_folder, "mid_drum.mp3"))
right_sound = pygame.mixer.Sound(os.path.join(sound_folder, "right.mp3"))
center_up_sound = pygame.mixer.Sound(os.path.join(sound_folder, "mid_guitar.mp3"))
center_down_sound = pygame.mixer.Sound(os.path.join(sound_folder, "mid_bottom.mp3"))
center_mid_sound = pygame.mixer.Sound(os.path.join(sound_folder, "mid_drum.mp3"))
crash_sound = pygame.mixer.Sound(os.path.join(sound_folder, "lose.mp3"))

left_channel = pygame.mixer.Channel(0)
center_channel = pygame.mixer.Channel(1)
right_channel = pygame.mixer.Channel(2)
center_up_channel = pygame.mixer.Channel(3)
center_down_channel = pygame.mixer.Channel(4)
center_mid_channel = pygame.mixer.Channel(5)
crash_channel = pygame.mixer.Channel(6)

left_channel.play(left_sound, loops=-1)
center_channel.play(center_sound, loops=-1)
right_channel.play(right_sound, loops=-1)
center_up_channel.play(center_up_sound, loops=-1)
center_down_channel.play(center_down_sound, loops=-1)
center_mid_channel.play(center_mid_sound, loops=-1)

left_channel.set_volume(0)
center_channel.set_volume(0)
right_channel.set_volume(0)
center_up_channel.set_volume(0)
center_down_channel.set_volume(0)
center_mid_channel.set_volume(0)


audio_refresh_rate = 0.3

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





window.position = (0, 0)
#window.size = (640, 480)
window.size = (1910, 1070)


monitor = {"top": window.position[0], "left": window.position[1], \
           "width": window.size[0], "height": window.size[1]}

depth_map_shader = Shader(language=Shader.GLSL, vertex='''
            #version 140
            
            in vec4 p3d_Vertex;
            in vec2 p3d_MultiTexCoord0;

            uniform mat4 p3d_ModelViewProjectionMatrix;

            out float depth;

            void main() {
                gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
                depth = 1 - gl_Position.z / 50;
            }
        ''', fragment='''
            #version 140
            
            in float depth;
            
            void main() {
                gl_FragColor = vec4(1-depth, 0, depth, 1.0);
            }
        ''')




floor = Entity(model='plane', scale=(100, 1, 100), texture='white_cube', collider='box', color=color.black, shader = depth_map_shader)
walls = [Entity(model='cube', scale=(100, 50, 1), position=Vec3(0, 2.5, 50), collider='cube', color=color.black, shader = depth_map_shader),
    Entity(model='cube', scale=(100, 50, 1), position=Vec3(0, 2.5, -50), collider='cube', color=color.black, shader = depth_map_shader),
    Entity(model='cube', scale=(1, 50, 100), position=Vec3(50, 2.5, 0), collider='cube', color=color.black, shader = depth_map_shader),
    Entity(model='cube', scale=(1, 50, 100), position=Vec3(-50, 2.5, 0), collider='cube', color=color.black, shader = depth_map_shader)]

obstacles = [Entity(model='cube', scale=(2, random.randint(5, 20), 2), position=Vec3(random.randint(-48, 48), 1, random.randint(-48, 48)), collider='box', color=color.blue) for _ in range(obstacle_num)]


for obstacle in obstacles:
    obstacle.shader = depth_map_shader


def restart_game():
    global start_time, obstacles
    player.position = player.start_position
    start_time = t.time()
    #obstacles = [Entity(model='cube', scale=(2, 20, 2), position=Vec3(random.randint(-48, 48), 1, random.randint(-48, 48)), collider='box', color=color.blue) for _ in range(30)]

def get_depth_from_image(depth_image, threshold=100):
    resampled_depth_image = ndimage.zoom(depth_image, (64 / depth_image.shape[0], 48 / depth_image.shape[1]), order=0)
    resampled_depth_image = resampled_depth_image

    # Divide the resampled image into left, center, and right portions
    left = resampled_depth_image[:, :21]
    center_up = resampled_depth_image[:16, 21:42]
    center_mid = resampled_depth_image[16:32, 21:42]
    center_down = resampled_depth_image[32:, 21:42]
    right = resampled_depth_image[:, 42:]

    # Calculate the median depth values for each portion
    factor = 255
    left_mean = np.mean(left)
    if left_mean < threshold:
        left_mean = 1- np.mean(left)/factor
    else:
        left_mean = 0
    
    left_mean = (10**left_mean-1)/10

    center_up_mean = np.mean(center_up)
    if center_up_mean < threshold:
        center_up_mean = 1- np.mean(center_up)/factor
    else:
        center_up_mean = 0
    center_up_mean = (10**center_up_mean-1)/10

    center_mid_mean = np.mean(center_mid)
    if center_mid_mean < threshold:
        center_mid_mean = 1- np.mean(center_mid)/factor
    else:
        center_mid_mean = 0

    center_mid_mean = (10**center_mid_mean-1)/10

    center_down_mean = np.mean(center_down)
    if center_down_mean < threshold:
        center_down_mean = 1-np.mean(center_down)/factor
    else:
        center_down_mean = 0
    
    center_down_mean = (10**center_down_mean-1)/10

    right_mean = np.mean(right)
    if right_mean < threshold:
        right_mean = 1-np.mean(right)/factor
    else:
        right_mean = 0

    right_mean = (10**right_mean-1)/10
    
    return left_mean, center_up_mean, center_mid_mean, center_down_mean, right_mean



def limit_mouse_horizontal():
    mouse.y = 0

counter = 0
def update():
    global counter
    counter += 1
    global start_time, obstacles
    section_time = t.time() - start_time 

    #limit_mouse_horizontal()

    if held_keys['q']:
        application.quit()
    
    if section_time > game_section_duration:
        restart_game()
        print(f"Time's up! Your score is: {player.position.distance(player.start_position)}")


    for wall in walls:
        if player.intersects(wall).hit:
            print("hit wall")
            play(crash_sound)
            restart_game()
        wall.shader = depth_map_shader

    for obstacle in obstacles:
        if player.intersects(obstacle).hit:
            print("hit obstacle")
            play(crash_sound)
            restart_game()
        obstacle.shader = depth_map_shader


    floor.shader = depth_map_shader



def depth_to_audio_thread():
    global start_time
    section_time = t.time() - start_time
    while True:
        with mss.mss() as sct:
            #Get raw pixels from the screen, save it to a Numpy array
            img = numpy.array(sct.grab(monitor))
            #print(img.shape)
            left_mean, center_up_mean, center_mid_mean, center_down_mean, right_mean = get_depth_from_image(img[:, :, 2])
            print(left_mean, center_up_mean, center_mid_mean, center_down_mean, right_mean)
            left_channel.set_volume(left_mean)
            center_up_channel.set_volume(center_up_mean)
            center_mid_channel.set_volume(center_mid_mean)
            center_down_channel.set_volume(center_down_mean)
            right_channel.set_volume(right_mean)

            #depth_to_audio(img[:, :, 2], threshold=max_range_threshold)

            if held_keys['p']:
                break
            if section_time > game_section_duration:
                break

            # Display the picture
            #cv2.imshow("image", img)
            time.sleep(audio_refresh_rate)

threading.Thread(target=depth_to_audio_thread).start()

app.run()

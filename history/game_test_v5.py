from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import time as t
import cv2
import mss
import numpy

import os
import numpy as np
from scipy import ndimage
from pydub import AudioSegment
from pydub.playback import play
import pyrealsense2 as rs
import threading

game_section_duration = 120


sound_folder = "sound"
left_sound = AudioSegment.from_mp3(os.path.join(sound_folder, "left.mp3"))
center_sound = AudioSegment.from_mp3(os.path.join(sound_folder, "center.mp3"))
right_sound = AudioSegment.from_mp3(os.path.join(sound_folder, "right.mp3"))
print(left_sound)



start_time = t.time()
player = FirstPersonController()
player.cursor.visible = False
player.speed = 10
player.start_position = Vec3(0, 0, 0)
player.collider = BoxCollider(player, size=(1, 2, 1))
player.position = player.start_position


app = Ursina()
application.vsync = False 
application.time_scale = 0.5

window.position = (0, 0)
window.size = (640, 480)


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

obstacles = [Entity(model='cube', scale=(2, 20, 2), position=Vec3(random.randint(-48, 48), 1, random.randint(-48, 48)), collider='box', color=color.blue) for _ in range(30)]


for obstacle in obstacles:
    obstacle.shader = depth_map_shader


def restart_game():
    global start_time, obstacles
    player.position = player.start_position
    start_time = t.time()
    #obstacles = [Entity(model='cube', scale=(2, 20, 2), position=Vec3(random.randint(-48, 48), 1, random.randint(-48, 48)), collider='box', color=color.blue) for _ in range(30)]



def depth_to_audio(depth_image, threshold=4000):
    global left_sound, center_sound, right_sound
    # Resample the depth image to 64x48 using nearest-neighbor sampling (order=0)
    resampled_depth_image = ndimage.zoom(depth_image, (64 / depth_image.shape[0], 48 / depth_image.shape[1]), order=0)
    resampled_depth_image = resampled_depth_image

    # Divide the resampled image into left, center, and right portions
    left = resampled_depth_image[:, :21]
    center = resampled_depth_image[:, 21:42]
    right = resampled_depth_image[:, 42:]

    # Calculate the median depth values for each portion
    left_median = np.mean(left)
    center_median = np.mean(center)
    right_median = np.mean(right)
    print(left_median, center_median, right_median)

    # Create an empty stereo AudioSegment to mix the sounds
    silent_mono = AudioSegment.silent(duration=max(len(left_sound), len(center_sound), len(right_sound)))
    mixed_audio = silent_mono.set_channels(2)

    # Define a function to convert depth to volume in dB
    def depth_to_volume(depth, max_depth, min_volume=-60, max_volume=0):
        return np.interp(depth, (0, max_depth), (max_volume, min_volume))

    # Set the volume for each sound proportional to the median depth value, pan them, and mix them
    if left_median < threshold:
        left_volume = depth_to_volume(left_median, threshold)
        left_sound_out = left_sound + left_volume
        left_sound_out = left_sound.pan(-1)  # Pan fully to the left
        mixed_audio = mixed_audio.overlay(left_sound_out)

    if center_median < threshold:
        center_volume = depth_to_volume(center_median, threshold)
        center_sound_out = center_sound + center_volume
        center_sound_out = center_sound.pan(0)  # Pan to the center
        mixed_audio = mixed_audio.overlay(center_sound_out)

    if right_median < threshold:
        right_volume = depth_to_volume(right_median, threshold)
        right_sound_out = right_sound + right_volume
        right_sound_out = right_sound.pan(1)  # Pan fully to the right
        mixed_audio = mixed_audio.overlay(right_sound_out)

    # Play the mixed audio
    play(mixed_audio)


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
        application.quit()
        print(f"Time's up! Your score is: {player.position.distance(player.start_position)}")


    for wall in walls:
        if player.intersects(wall).hit:
            print("hit wall")
            restart_game()
        wall.shader = depth_map_shader

    for obstacle in obstacles:
        if player.intersects(obstacle).hit:
            print("hit obstacle")
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
            print(img.shape)
            depth_to_audio(img[:, :, 2], threshold=100)

            if held_keys['q']:
                break
            if section_time > game_section_duration:
                break

            # Display the picture
            #cv2.imshow("image", img)
            time.sleep(0.2)

threading.Thread(target=depth_to_audio_thread).start()

app.run()

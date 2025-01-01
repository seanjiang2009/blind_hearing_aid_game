from pathlib import Path
import random
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import numpy as np

app = Ursina()

# Load the custom depth shader
#depth_shader = Shader(language=Shader.GLSL, vertex=Path('depth_shader.glsl').read_text())

depth_shader = Shader(language=Shader.GLSL, vertex='''
    #version 140
    
    in vec4 p3d_Vertex;
    in vec2 p3d_MultiTexCoord0;

    uniform mat4 p3d_ModelViewProjectionMatrix;

    out float depth;

    void main() {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
        depth = 1 - gl_Position.z / 100;
    }
''', fragment='''
    #version 140
    
    in float depth;
    
    void main() {
        gl_FragColor = vec4(depth, depth, depth, 1.0);
    }
''')


# Set the far plane distance
far_plane = 1000.0
max_distance = 100.0

# Game settings (e.g., window settings)

# Floor with custom depth shader
floor = Entity(model='plane', scale=(100, 1, 100), color=color.gray, texture='white_cube', collider='box', shader=depth_shader)
walls = [Entity(model='cube', scale=(100, 5, 1), position=Vec3(0, 2.5, 50), collider='box', color=color.black),
            Entity(model='cube', scale=(100, 5, 1), position=Vec3(0, 2.5, -50), collider='box', color=color.black),
            Entity(model='cube', scale=(1, 5, 100), position=Vec3(50, 2.5, 0), collider='box', color=color.black),
            Entity(model='cube', scale=(1, 5, 100), position=Vec3(-50, 2.5, 0), collider='box', color=color.black)]

# Player
player = FirstPersonController()
player.cursor.visible = False
player.collider = BoxCollider(player, size=(1, 2, 1))
player.speed = 10

# Obstacles with custom depth shader
num_obstacles = 50
obstacles = []

for i in range(num_obstacles):
    obstacle = Entity(
        model='cube',
        scale=(1, random.uniform(1, 5), 1),
        position=(random.uniform(-50, 50), random.uniform(0.5, 2.5), random.uniform(-50, 50)),
        color=color.random_color(),
        collider='box',
        shader=depth_shader
    )
    obstacles.append(obstacle)

# Record and lose conditions

def update():
    global record

    # Linear interpolation between red and blue colors
    
    for obstacle in obstacles:
        # distance = np.linalg.norm(player.position - obstacle.position)
        # t = np.clip(distance / max_distance, 0, 1)  # Clamp the value between 0 and 1
        # obstacle.color = color.rgb(t, 0, 1-t)*255
        obstacle.shader = depth_shader

    for wall in walls:
        # distance = np.linalg.norm(player.position - wall.position)
        # t = np.clip(distance / max_distance, 0, 1)
        # wall.color = color.rgb(t, 0, 1-t)*255
        wall.shader = depth_shader
    
    floor.shader   = depth_shader
            
    # (Existing code in the update function)

    
# Set the far plane distance for the camera
camera.far = far_plane

app.run()

from render3 import Render
import sys
import time
import pygame
from OpenGL.GL import *


class App():
    def __init__(self, model_name):
        self.name = 'App'
        self.render = Render(filename=model_name)
        self.running = True

    def run(self):
        self.render.run()

if __name__ == '__main__':
    model_name: str = 'resources/INRIA_MUSIS.stl' if (len(sys.argv) < 2) else sys.argv[1]
    app = App(model_name)
    app.run()

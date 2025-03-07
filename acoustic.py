"""
The Acoustic Class handles all the pyroomacoustics functions 
necessary for simulating sound in a given environment.
"""

import pyroomacoustics as pra
import numpy as np

class Acoustic():
    def __init__(self):
        self.sample_rate = 44100
        self.speed_of_sound = 343.0
        return
    
    def simulate(self):
        return 0
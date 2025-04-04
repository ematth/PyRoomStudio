"""
The Acoustic Class handles all the pyroomacoustics functions 
necessary for simulating sound in a given environment.
"""

import pyroomacoustics as pra
import numpy as np
import pymesh

class Acoustic(pra.room.Room):

    def build_stl():
        """
        Build the room from an STL file.
        """
        pass


    def build_obj(filename: str):
        """
        Build the room from an OBJ file.
        """
        mesh = pymesh.load_mesh(filename)
        material = pra.Material(energy_absorption=0.2, scattering=0.1)
        ntriang, nvec, npts = mesh
        size_reduc_factor = 100  # to get a realistic room size (not 3km)

        # create one wall per triangle
        walls = []
        for w in range(ntriang):
            walls.append(
                pra.wall_factory(
                    mesh.faces[w].T / size_reduc_factor,
                    material.energy_absorption["coeffs"],
                    material.scattering["coeffs"],
            )
        )

        room = (
            pra.Room(
                walls,
                fs=16000,
                max_order=3,
                ray_tracing=True,
                air_absorption=True,
            )
            .add_source([0.0, 0.0, 0.0])   
        )

        room.plot(img_order=1)
        plt.show()


    def __init__(self, filename: str):
        pra.room.Room.__init__(self)
        self.sample_rate = 44100
        self.speed_of_sound = 343.0

        self.build_obj(filename)
    
    def simulate(self):
        return 0
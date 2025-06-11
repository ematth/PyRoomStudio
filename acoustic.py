"""
The Acoustic Class handles all the pyroomacoustics functions 
necessary for simulating sound in a given environment.
"""

import pyroomacoustics as pra
import numpy as np
from scipy.io import wavfile

SIZE_REDUCTION_FACTOR = 700.0  # to get a realistic room size (not 3km)

class Acoustic(pra.room.Room):

    def __init__(self):
        self.sample_rate = 44100
        self.speed_of_sound = 343.0

    def simulate(self, walls_from_render, room_center, model_vertices):
        material = pra.Material(energy_absorption=0.2, scattering=0.1)

        # create one wall per triangle from the renderer's grouped walls
        walls = []
        for wall_info in walls_from_render:
            for tri_idx in wall_info['triangles']:
                # Get the vertices for this triangle
                triangle_verts = model_vertices[tri_idx*3 : tri_idx*3+3]

                # pra.wall_factory expects vertices in shape (3, N)
                # and they should be scaled down.
                if triangle_verts.shape[0] < 3:
                    continue

                pra_vertices = triangle_verts.T / SIZE_REDUCTION_FACTOR
                
                walls.append(
                    pra.wall_factory(
                        pra_vertices,
                        material.energy_absorption["coeffs"],
                        material.scattering["coeffs"],
                    )
                )

        fs, signal = wavfile.read('sounds/piano.wav')
        signal = signal.astype(np.float32) / 32768.0  # required.

        cent = room_center / SIZE_REDUCTION_FACTOR
        print('Room center: ', cent)

        room = (
            pra.Room(
                walls,
                fs=fs,
                max_order=3,
                ray_tracing=True,
                air_absorption=True,
            )
            .add_source(cent, signal=signal)
            .add_microphone_array(np.c_[cent + np.array([0, 2, 0]), cent + np.array([0, -2, 0])])
        )
        
        # Set the number of rays manually to avoid calculation errors
        room.set_ray_tracing(n_rays=10000)

        print('Room volume: ', room.volume)

        # compute the rir
        print('Image source model')
        room.image_source_model()
        print('Ray tracing')
        room.ray_tracing()
        print('Compute RIR')
        room.compute_rir()
        room.plot_rir()

        print('simulate room')
        room.simulate()

        # show the room
        # room.plot(img_order=1)
        # plt.show()

        print(f'Shapes:\n Original:{signal.shape}\n Simulation:{room.mic_array.signals.shape}')

        wavfile.write(filename='sounds/output.wav', rate=fs, data=room.mic_array.signals[0, :])
"""
The Acoustic Class handles all the pyroomacoustics functions 
necessary for simulating sound in a given environment.
"""

import pyroomacoustics as pra
import numpy as np
from scipy.io import wavfile

SIZE_REDUCTION_FACTOR = 700.0  # to get a realistic room size (not 3km)

def compute_volumetric_center(stl_mesh):
    """
    Computes the volumetric center (centroid) of a closed triangular mesh.
    This assumes that the mesh is watertight.
    
    Parameters:
      stl_mesh (mesh.Mesh): The mesh object created using numpy-stl.
      
    Returns:
      np.ndarray: The 3D coordinates of the volumetric center.
    """
    total_volume = 0.0
    centroid_sum = np.zeros(3)

    # Iterate over each triangle in the mesh.
    for triangle in stl_mesh.vectors:
        # Unpack triangle vertices
        v0, v1, v2 = triangle

        # Compute the signed volume of the tetrahedron defined by (0, v0, v1, v2)
        # Using scalar triple product formula: V = dot(v0, cross(v1, v2)) / 6.
        tetra_volume = np.dot(v0, np.cross(v1, v2)) / 6.0

        # The centroid of the tetrahedron (including the origin 0,0,0) is given by:
        # (0 + v0 + v1 + v2) / 4 which simplifies to (v0 + v1 + v2) / 4.
        tetra_centroid = (v0 + v1 + v2) / 4.0

        centroid_sum += tetra_centroid * tetra_volume
        total_volume += tetra_volume

    # A quick sanity check: if total_volume is nearly zero, your mesh might not be closed.
    if np.isclose(total_volume, 0):
        raise ValueError("Calculated volume is zero; ensure the STL mesh is closed and valid.")

    # The overall centroid is the weighted average of the tetrahedron centroids.
    volumetric_center = centroid_sum / total_volume
    return volumetric_center / SIZE_REDUCTION_FACTOR


class Acoustic(pra.room.Room):


    def __init__(self, filename: str):
        self.filename = filename
        self.sample_rate = 44100
        self.speed_of_sound = 343.0


    def simulate(self):
        from stl import mesh
        material = pra.Material(energy_absorption=0.2, scattering=0.1)

        # with numpy-stl
        the_mesh = mesh.Mesh.from_file(self.filename)
        ntriang, nvec, npts = the_mesh.vectors.shape

        # create one wall per triangle
        walls = []
        for w in range(ntriang):
            walls.append(
                pra.wall_factory(
                    the_mesh.vectors[w].T / SIZE_REDUCTION_FACTOR,
                    material.energy_absorption["coeffs"],
                    material.scattering["coeffs"],
                )
            )

        fs, signal = wavfile.read('sounds/piano.wav')
        signal = signal.astype(np.float32)/32768.0 # required.

        print('Room center: ', cent := compute_volumetric_center(the_mesh))

        room = (
            pra.Room(
                walls,
                fs=fs,
                max_order=3,
                ray_tracing=True,
                air_absorption=True,
            )
            .add_source(cent, signal=signal)
            .add_microphone_array(np.c_[cent + [0, 2, 0], cent + [0, -2, 0]])
        )

        print('Room volume: ', room.volume)

        # compute the rir
        print('Image source model')
        room.image_source_model()
        print('Ray tracing')
        room.ray_tracing()
        print('Compute RIR')
        room.compute_rir()
        
        print('saving file...')
        print(f'Shapes:\n Original:{signal.shape}\n Simulation:{room.mic_array.signals}')
        #wavfile.write(filename='sounds/output.wav', rate=fs, data=room.mic_array.signals[0,:])
        print('file saved')
"""
Random demo file for room acoustic simulation on an STL file.

References:
https://github.com/LCAV/pyroomacoustics/blob/master/notebooks/pyroomacoustics_demo.ipynb
https://github.com/LCAV/pyroomacoustics/blob/master/examples/room_from_stl.py
"""

import argparse
import os
from pathlib import Path
from scipy.io import wavfile
from scipy.signal import fftconvolve

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits import mplot3d

import pyroomacoustics as pra

try:
    from stl import mesh
except ImportError as err:
    print(
        "The numpy-stl package is required for this example. "
        "Install it with `pip install numpy-stl`"
    )
    raise err

default_stl_path = Path(__file__).parent / "resources/INRIA_MUSIS.stl"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Basic room from STL file example")
    parser.add_argument(
        "--file", type=str, default=default_stl_path, help="Path to STL file"
    )
    args = parser.parse_args()

    material = pra.Material(energy_absorption=0.2, scattering=0.1)

    # with numpy-stl
    the_mesh = mesh.Mesh.from_file(args.file)
    ntriang, nvec, npts = the_mesh.vectors.shape
    size_reduc_factor = 500.0  # to get a realistic room size (not 3km)

    # create one wall per triangle
    walls = []
    for w in range(ntriang):
        walls.append(
            pra.wall_factory(
                the_mesh.vectors[w].T / size_reduc_factor,
                material.energy_absorption["coeffs"],
                material.scattering["coeffs"],
            )
        )

    fs, signal = wavfile.read('sounds/piano.wav')
    signal = signal.astype(np.float32)/32768.0 # required.

    room = (
        pra.Room(
            walls,
            fs=fs,
            max_order=3,
            ray_tracing=True,
            air_absorption=True,
        )
        .add_source([-2.0, 2.0, 1.8], signal=signal)
        .add_microphone_array(np.c_[[-6.5, 8.5, 3 + 0.1], [-6.5, 8.1, 3 + 0.1]])
    )

    # compute the rir
    room.image_source_model()
    room.ray_tracing()
    room.compute_rir()
    room.plot_rir()

    room.simulate()

    # show the room
    room.plot(img_order=1)
    plt.show()

    print(f'Shapes:\n Original:{signal.shape}\n Simulation:{room.mic_array.signals.shape}')

    wavfile.write(filename='sounds/output.wav', rate=fs, data=room.mic_array.signals[0,:])

    plt.plot(np.abs(signal), label='Original')
    plt.plot(np.abs(room.mic_array.signals[0, :]), label='Simulated')
    plt.title('Signal comparison')
    plt.legend()
    plt.show()
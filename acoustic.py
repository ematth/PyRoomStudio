"""
The Acoustic Class handles all the pyroomacoustics functions 
necessary for simulating sound in a given environment.
"""

import pyroomacoustics as pra
import numpy as np
from scipy.io import wavfile
from scipy import signal
import os
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

SIZE_REDUCTION_FACTOR = 700.0  # to get a realistic room size (not 3km)

# Configurable sound source file - change this to use different audio for simulation
SOUND_SOURCE_FILE = 'sounds/sources/test_sound.wav'

class Acoustic(pra.room.Room):

    def __init__(self):
        self.sample_rate = 44100
        self.speed_of_sound = 343.0
    
    def generate_spectrogram_comparison(self, original_file, output_file, sample_rate, output_dir):
        """
        Generate side-by-side spectrograms comparing original and simulated audio.
        
        Args:
            original_file: Path to original audio file
            output_file: Path to simulated audio file
            sample_rate: Sample rate of the audio
            output_dir: Directory to save the spectrogram image
            
        Returns:
            str: Path to the generated spectrogram image
        """
        # Load audio files
        fs_orig, original = wavfile.read(original_file)
        fs_out, simulated = wavfile.read(output_file)
        
        # Convert to float and mono if needed
        if original.dtype == np.int16:
            original = original.astype(np.float32) / 32768.0
        if simulated.dtype == np.int16:
            simulated = simulated.astype(np.float32) / 32768.0
        
        # Ensure mono
        if original.ndim > 1:
            original = original[:, 0]
        if simulated.ndim > 1:
            simulated = simulated[:, 0]
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Generate spectrograms
        # Use shorter segments for better frequency resolution
        nperseg = min(1024, len(original) // 4)
        
        # Original audio spectrogram
        f_orig, t_orig, Sxx_orig = signal.spectrogram(
            original, fs_orig, nperseg=nperseg, 
            window='hann', scaling='density'
        )
        ax1.pcolormesh(t_orig, f_orig, 10 * np.log10(Sxx_orig + 1e-10), 
                       shading='gouraud', cmap='viridis')
        ax1.set_ylabel('Frequency [Hz]')
        ax1.set_xlabel('Time [s]')
        ax1.set_title('Original Audio Spectrogram')
        ax1.set_ylim([0, min(8000, fs_orig // 2)])  # Show up to 8kHz or Nyquist
        
        # Simulated audio spectrogram
        f_sim, t_sim, Sxx_sim = signal.spectrogram(
            simulated, fs_out, nperseg=nperseg,
            window='hann', scaling='density'
        )
        ax2.pcolormesh(t_sim, f_sim, 10 * np.log10(Sxx_sim + 1e-10), 
                       shading='gouraud', cmap='viridis')
        ax2.set_ylabel('Frequency [Hz]')
        ax2.set_xlabel('Time [s]')
        ax2.set_title('Simulated Audio Spectrogram (with Room Acoustics)')
        ax2.set_ylim([0, min(8000, fs_out // 2)])  # Show up to 8kHz or Nyquist
        
        # Add colorbar
        plt.tight_layout()
        
        # Save figure
        spectrogram_file = os.path.join(output_dir, 'spectrogram_comparison.png')
        plt.savefig(spectrogram_file, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return spectrogram_file

    def simulate(self, walls_from_render, room_center, model_vertices, scale_factor=None):
        """
        Simulate acoustics in the given room geometry.
        
        Args:
            walls_from_render: List of wall dictionaries with triangle indices
            room_center: Center point of the room (numpy array)
            model_vertices: Flattened vertex array from the 3D model
            scale_factor: Optional scale factor for the model. If None, uses SIZE_REDUCTION_FACTOR
            
        Returns:
            str: Path to the output audio file
            
        Raises:
            FileNotFoundError: If the sound source file doesn't exist
            ValueError: If the room geometry is invalid
        """
        # Use provided scale factor or default to SIZE_REDUCTION_FACTOR
        if scale_factor is None:
            scale_factor = 1.0 / SIZE_REDUCTION_FACTOR
            print(f"Using default scale factor: 1/{SIZE_REDUCTION_FACTOR}")
        else:
            print(f"Using custom scale factor: {scale_factor}")
        # Validate sound source file exists
        if not os.path.exists(SOUND_SOURCE_FILE):
            raise FileNotFoundError(
                f"Sound source file not found: {SOUND_SOURCE_FILE}\n"
                f"Please ensure the file exists or update SOUND_SOURCE_FILE in acoustic.py"
            )
        
        # Validate input geometry
        if not walls_from_render or len(walls_from_render) == 0:
            raise ValueError("No walls provided for acoustic simulation")
        
        if len(model_vertices) == 0:
            raise ValueError("No vertices provided for acoustic simulation")
        
        material = pra.Material(energy_absorption=0.2, scattering=0.1)

        # create one wall per triangle from the renderer's grouped walls
        walls = []
        triangles_processed = 0
        for wall_info in walls_from_render:
            for tri_idx in wall_info['triangles']:
                # Get the vertices for this triangle
                triangle_verts = model_vertices[tri_idx*3 : tri_idx*3+3]

                # pra.wall_factory expects vertices in shape (3, N)
                # and they should be scaled down.
                if triangle_verts.shape[0] < 3:
                    print(f"  Warning: Skipping triangle {tri_idx} - insufficient vertices")
                    continue

                pra_vertices = triangle_verts.T * scale_factor
                triangles_processed += 1
                
                walls.append(
                    pra.wall_factory(
                        pra_vertices,
                        material.energy_absorption["coeffs"],
                        material.scattering["coeffs"],
                    )
                )
        
        print(f'Created {len(walls)} walls from {triangles_processed} triangles')
        
        if len(walls) == 0:
            raise ValueError("No valid walls created from the 3D model")

        fs, signal = wavfile.read(SOUND_SOURCE_FILE)
        signal = signal.astype(np.float32) / 32768.0  # required.
        
        # Ensure signal is mono (1D array)
        if signal.ndim > 1:
            signal = signal[:, 0]  # Take first channel if stereo
        
        cent = room_center * scale_factor
        print('Room center: ', cent)

        # Create microphone positions (two mics separated along Y axis)
        # TODO: make this a single microphone
        mic1_pos = cent + np.array([0, 2, 0]) * scale_factor
        mic2_pos = cent + np.array([0, -2, 0]) * scale_factor
        mic_array = np.c_[mic1_pos, mic2_pos]
        
        print(f'Microphone array shape: {mic_array.shape}')
        print(f'Signal shape: {signal.shape}')

        room = (
            pra.Room(
                walls,
                fs=fs,
                max_order=3,
                ray_tracing=True,
                air_absorption=True,
            )
            .add_source(cent, signal=signal)
            .add_microphone_array(mic_array)
        )
        
        # Set the number of rays manually to avoid calculation errors
        room.set_ray_tracing(n_rays=1000)

        print('Room volume: ', room.volume)
        
        # Validate room was created successfully
        if room.volume <= 0:
            raise ValueError("Invalid room geometry: room volume is zero or negative")
        
        # Check if volume is suspiciously small (less than 1 cubic unit after scaling)
        if room.volume < 1e-3:
            print(f"WARNING: Room volume is very small ({room.volume:.2e} cubic units)")
            print("This may indicate an open mesh (e.g., pyramid without bottom face)")
            print("PyRoomAcoustics requires closed meshes for proper simulation")

        try:
            # compute the rir
            print('Image source model')
            room.image_source_model()
            
            print('Ray tracing')
            room.ray_tracing()
            
            print('Compute RIR')
            room.compute_rir()
            
            print('Plotting RIR')
            room.plot_rir()

            print('Simulating room acoustics')
            room.simulate()
        except (ValueError, IndexError, ZeroDivisionError) as e:
            # These errors often indicate geometry problems
            raise ValueError(
                f"Room geometry is invalid for acoustic simulation: {str(e)}\n"
                f"Possible causes:\n"
                f"  - Mesh is not closed (has holes or open faces)\n"
                f"  - Mesh is too small or too complex\n"
                f"  - Try using a closed mesh like a box or room with all faces"
            ) from e
        except Exception as e:
            raise RuntimeError(f"PyRoomAcoustics simulation failed: {str(e)}") from e

        # show the room
        # room.plot(img_order=1)
        # plt.show()

        print(f'Shapes:\n Original:{signal.shape}\n Simulation:{room.mic_array.signals.shape}')

        # Validate simulation output
        if room.mic_array.signals is None or len(room.mic_array.signals) == 0:
            raise RuntimeError("Simulation produced no audio output")
        
        # Get the simulated signal from the first microphone
        simulated_signal = room.mic_array.signals[0, :]
        
        # Normalize the signal to prevent clipping
        # The simulated signal is in float format, normalize to [-1, 1] range
        max_val = np.abs(simulated_signal).max()
        if max_val > 0:
            simulated_signal = simulated_signal / max_val * 0.95  # Leave some headroom
        
        # Convert from float32 [-1, 1] to int16 [-32768, 32767] for WAV file
        simulated_signal_int16 = np.int16(simulated_signal * 32767)
        
        print(f'Audio stats: min={simulated_signal_int16.min()}, max={simulated_signal_int16.max()}, length={len(simulated_signal_int16)}')
        
        # Ensure output directory exists
        output_dir = 'sounds/simulations'
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create output directory: {output_dir}") from e
        
        output_file = os.path.join(output_dir, 'output.wav')
        
        try:
            wavfile.write(filename=output_file, rate=fs, data=simulated_signal_int16)
        except Exception as e:
            raise RuntimeError(f"Failed to write output audio file: {output_file}") from e
            
        print(f'Saved simulated audio to: {output_file}')
        print(f'Sample rate: {fs} Hz, Duration: {len(simulated_signal_int16)/fs:.2f} seconds')
        
        # Generate spectrogram comparison
        try:
            spectrogram_file = self.generate_spectrogram_comparison(
                SOUND_SOURCE_FILE, output_file, fs, output_dir
            )
            print(f'Saved spectrogram comparison to: {spectrogram_file}')
        except Exception as e:
            print(f'Warning: Failed to generate spectrogram: {e}')
        
        return output_file
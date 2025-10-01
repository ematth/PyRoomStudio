<!------------------------------------------------------------------->

# PyRoomStudio

**Authors:**

William (Zhiwen) Chen (willc@illinois.edu), *project manager*

Evan M. Matthews (evanmm3@illinois.edu), *lead programmer*

**PyRoomStudio** (PRS) is a graphical application for rendering and analyzing acoustical properties of 3D spaces via meshes. The projects internals function on [pyroomacoustics](https://github.com/LCAV/pyroomacoustics), a library for testing and simulating acoustics algorithms written by Robin Scheibler. 

<!------------------------------------------------------------------->

## Setup

1. Clone the repository

    ```
    $ git clone https://github.com/ematth/3DARRE.git
    ```

2. Setup your virtual environment (venv) and install necessary packages

    ```
    $ python3 -m venv venv
    $ source venv/bin/activate
    (venv) $ pip install -r requirements.txt
    ```
3. Open the existing rendering GUI:

    ```
    $ python3 panda3D/main.py
    ```

If everything is setup correctly, you will see a spinning rendering of a potted plant 🪴

<!------------------------------------------------------------------->

## Controls

- **AWSD** control camera movement on the XY-plane.

- **Up and Down Arrows** control camera zoom on the object.

<!------------------------------------------------------------------->


## Credits/Licenses

[Pyroomacoustics](https://github.com/LCAV/pyroomacoustics): Copyright (c)2014-2017, EPFL-LCAV

[panda3d](https://github.com/panda3d/panda3d): Copyright (c) 2008, Carnegie Mellon University.


<!------------------------------------------------------------------->

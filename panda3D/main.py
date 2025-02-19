from direct.showbase.ShowBase import ShowBase, loadPrcFileData
from panda3d.core import Vec3, TextureStage
import math, sys, simplepbr, os.path as path

# Enable the assimp loader so that .obj files can be loaded.
loadPrcFileData("", "load-file-type p3assimp")

class MyApp(ShowBase):

    def load_obj(self, filename) -> None:
        """Load a model from a .obj file.

        Args:
            filename (str): file name
        """
        try:
            self.model = self.loader.loadModel(filename)
            self.model.reparentTo(self.render)
            self.model.setPos(0, 50, 0)
            self.model.setScale(0.1)
            self.model.setHpr(0, 90, 0)
        except:
            print('Unable to load model. Please make sure that the model file exists.')

        # Set up a texture stage to apply the texture to the model.
        if path.exists(f"{filename[:-8]}_diffuse.png"):
            try:
                diffuse=self.loader.loadTexture(f"{filename[:-8]}_diffuse.png")
                normal=self.loader.loadTexture(f"{filename[:-8]}_normal.png")
            except:
                print("PNG texture issue")
                sys.exit()
        elif path.exists(f"{filename[:-4]}_c.tga"):
            try:
                diffuse=self.loader.loadTexture(f"{filename[:-4]}_c.tga")
                normal = self.loader.loadTexture(f"{filename[:-4]}_n.tga")
            except:
                print("TGA texture issue")
                sys.exit()

        # set textures
        self.model.setTexture(diffuse, 1)
        normal_stage = TextureStage("normal_stage")
        normal_stage.setMode(TextureStage.MNormal)
        self.model.setTexture(normal_stage, normal, 1)

    
    def load_stl(self, filename) -> None:
        """Load a model from a .stl file.

        Args:
            filename (str): file name
        """
        return NotImplemented
    

    def load_fbx(self, filename) -> None:
        """Load a model from a .fbx file.

        Args:
            filename (str): file name
        """
        return NotImplemented


    def model_loader(self, filename) -> None:
        """Match the file extension and load the model accordingly.

        Args:
            filename (str): name of the model file.
        """
        print(filename[-4:]) 
        match filename[-4:]:
            case '.obj':
                self.load_obj(filename)
            case '.stl':
                self.load_stl(filename)
            case '.fbx':
                self.load_fbx(filename)
            case _:
                print('Invalid file format. Only .obj files are supported.')
                sys.exit()


    def __init__(self, filename) -> None:
        ShowBase.__init__(self)

        simplepbr.init()

        self.setFrameRateMeter(True)
        self.frameRateMeter.setUpdateInterval(0.1)

        # Disable default mouse camera control.
        self.disableMouse()

        # Load the model.
        self.model_loader(filename)
        
        # Set up orbit parameters so the camera rotates around the model.
        # The orbit target is the model's position.
        self.target = self.model.getPos()
        self.orbitAngle = 180    # horizontal angle (degrees)
        self.pitchAngle = 20     # vertical angle (degrees)
        self.cameraDistance = 10 # distance from the target

        # Define movement speeds.
        self.rotateSpeed = 60    # degrees per second for rotation
        self.zoomSpeed = 10      # units per second for zooming
        self.panSpeed = 10       # units per second for panning

        # Set up state for key controls.
        self.keyMap = {
            "w": False,   # Zoom in
            "a": False,   # Pan left
            "s": False,   # Zoom out
            "d": False,   # Pan right
            "arrow_left": False,  # Rotate horizontally (orbit)
            "arrow_right": False, # Rotate horizontally (orbit)
            "arrow_up": False,    # Increase pitch (rotate upward)
            "arrow_down": False   # Decrease pitch (rotate downward)
        }
        for key in self.keyMap.keys():
            self.accept(key, self.setKey, [key, True])
            self.accept(key + "-up", self.setKey, [key, False])

        # Add the update task.
        self.taskMgr.add(self.updateTask, "updateTask")
        
        # Initialize camera position.
        self.updateCameraPosition()


    def setKey(self, key, value):
        self.keyMap[key] = value


    def updateTask(self, task):
        dt = globalClock.getDt()

        # Adjust orbit rotation using the arrow keys.
        if self.keyMap["arrow_left"]:
            self.orbitAngle += self.rotateSpeed * dt
        if self.keyMap["arrow_right"]:
            self.orbitAngle -= self.rotateSpeed * dt
        if self.keyMap["arrow_up"]:
            # Clamp the pitch angle to avoid flipping.
            self.pitchAngle = min(self.pitchAngle + self.rotateSpeed * dt, 85)
        if self.keyMap["arrow_down"]:
            self.pitchAngle = max(self.pitchAngle - self.rotateSpeed * dt, 5)

        # Use W/S to zoom in/out.
        if self.keyMap["w"]:
            self.cameraDistance = max(self.cameraDistance - self.zoomSpeed * dt, 5)
        if self.keyMap["s"]:
            self.cameraDistance += self.zoomSpeed * dt

        # Update the camera's position based on the new parameters.
        self.updateCameraPosition()
        return task.cont


    def updateCameraPosition(self) -> Vec3:
        """Update the camera's position based on the current orbit parameters.

        Returns:
            Vec3: length-3 vector of the new camera position.
        """
        # Convert angles from degrees to radians.
        radOrbit = math.radians(self.orbitAngle)
        radPitch = math.radians(self.pitchAngle)
        
        # Calculate the offset using spherical coordinates.
        offsetX = self.cameraDistance * math.sin(radOrbit) * math.cos(radPitch)
        offsetY = self.cameraDistance * math.cos(radOrbit) * math.cos(radPitch)
        offsetZ = self.cameraDistance * math.sin(radPitch)
        
        # Set the new camera position relative to the target.
        newPos = self.target + Vec3(offsetX, offsetY, offsetZ)
        self.camera.setPos(newPos)
        self.camera.lookAt(self.target)
        return newPos

if __name__ == "__main__":

    # Default loaded model to the cottage, but can be changed via command line.
    model_name: str = 'resources/cottage_obj.obj' if (len(sys.argv) < 2) else sys.argv[1]

    app = MyApp(filename=model_name)
    app.run()
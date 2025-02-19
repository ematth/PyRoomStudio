from direct.showbase.ShowBase import ShowBase, loadPrcFileData
from panda3d.core import Vec3, TextureStage
import math, sys, simplepbr

# Enable the assimp loader so that .obj files can be loaded.
loadPrcFileData("", "load-file-type p3assimp")

class MyApp(ShowBase):

    def load_obj(self, filename):
        # Load the .obj model. Change the file path as needed.
        try:
            self.model = self.loader.loadModel(filename)
            self.model.reparentTo(self.render)
            self.model.setPos(0, 50, 0)
            self.model.setScale(0.1)
            self.model.setHpr(0, 90, 0)
        except:
            print('Unable to load model. Please make sure that the model file exists.')

        # Set up a texture stage to apply the texture to the model.
        try:
            diffuse=self.loader.loadTexture(f"{filename[:-8]}_diffuse.png")
            normal=self.loader.loadTexture(f"{filename[:-8]}_normal.png")
        except:
            print(f"{filename[:-8]}_diffuse.png")
            print('Texture files not found. Please make sure that the texture files are in the same directory as the model file.')
            sys.exit()
        self.model.setTexture(diffuse, 1)

        normal_stage = TextureStage("normal_stage")
        normal_stage.setMode(TextureStage.MNormal)
        self.model.setTexture(normal_stage, normal, 1)


    def model_loader(self, filename):
        match filename[-4:]:
            case '.obj':
                self.load_obj(filename)
            case _:
                print('Invalid file format. Only .obj files are supported.')
                sys.exit()


    def __init__(self, filename) -> None:
        ShowBase.__init__(self)

        simplepbr.init()

        # Disable default mouse camera control.
        self.disableMouse()

        # Load the model.
        self.model_loader(filename)
        
        # Set up orbit parameters so the camera rotates around the model.
        # The orbit target is the model's position.
        self.target = self.model.getPos()
        self.orbitAngle = 180    # horizontal angle (degrees)
        self.pitchAngle = 20     # vertical angle (degrees)
        self.cameraDistance = 30 # distance from the target

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

        # # Use A/D to pan the target point sideways.
        # # This moves the center point around which the camera orbits.
        # if self.keyMap["a"]:
        #     self.target -= self.camera.getQuat(self.render).getRight() * self.panSpeed * dt
        # if self.keyMap["d"]:
        #     self.target += self.camera.getQuat(self.render).getRight() * self.panSpeed * dt

        # Update the camera's position based on the new parameters.
        self.updateCameraPosition()
        return task.cont

    def updateCameraPosition(self):
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

if __name__ == "__main__":

    app = MyApp(filename=sys.argv[1])
    app.run()
"""
The Render Class processes all visual elements of the application by 
rendering meshes relative to the intended acoustics simulations.
"""


from direct.showbase.ShowBase import ShowBase, loadPrcFileData
from panda3d.core import Vec3, TextureStage, Point3, TextNode
import math, sys, simplepbr, os.path as path
from direct.gui.OnscreenText import OnscreenText

# Enable the assimp loader so that .obj files can be loaded.
loadPrcFileData("", "load-file-type p3assimp")

class Render(ShowBase):

    def load_obj(self, filename) -> None:
        """Load a model from a .obj file.

        Args:
            filename (str): file name
        """
        try:
            self.model = self.loader.loadModel(filename)
            self.model.reparentTo(self.render)
            # self.model.setPos(0, 50, 0)
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
        else:
            print(path.exists(f"{filename[:-8]}_diffuse.png"))
            print(f"{filename[:-8]}_diffuse.png")
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

        # Load the model.
        self.model_loader(filename)
        
        # Disable the default camera control system
        self.disableMouse()
        
        # Set up camera parameters
        self.camera_distance = 5.0       # Distance from camera to object
        self.min_distance = 3.0          # Minimum zoom distance
        self.max_distance = 15.0         # Maximum zoom distance
        self.camera_heading = 0.0        # Horizontal rotation angle
        self.camera_pitch = 0.0          # Vertical rotation angle
        self.min_pitch = 0.0           # Limit looking down
        self.max_pitch = 85.0            # Limit looking up
        
        # Initialize mouse state tracking
        self.mouse_x = 0
        self.mouse_y = 0
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.mouse_button_1 = False
        
        # Set up mouse event handlers
        self.accept("mouse1", self.on_mouse_down)
        self.accept("mouse1-up", self.on_mouse_up)
        self.accept("wheel_up", self.on_wheel_up)
        self.accept("wheel_down", self.on_wheel_down)


        # Add the update task.
        self.taskMgr.add(self.update_camera, "UpdateCameraTask")

        # Create onscreen text for camera stats
        self.heading_text = OnscreenText(
            text="Heading: 0.0°",
            pos=(-1.3, 0.7),
            scale=0.07,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )
        
        self.pitch_text = OnscreenText(
            text="Pitch: 0.0°",
            pos=(-1.3, 0.6),
            scale=0.07,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )
        
        # Initialize camera position.
        self.update_camera_position()

    def on_mouse_down(self):
        """Handler for mouse button down event"""
        if self.mouseWatcherNode.hasMouse():
            # Get current mouse position
            self.last_mouse_x = self.mouseWatcherNode.getMouseX()
            self.last_mouse_y = self.mouseWatcherNode.getMouseY()
            self.mouse_button_1 = True
    
    def on_mouse_up(self):
        """Handler for mouse button up event"""
        self.mouse_button_1 = False
    
    def on_wheel_up(self):
        """Handler for mouse wheel up (zoom in)"""
        self.camera_distance = max(self.min_distance, self.camera_distance - 0.5)
        self.update_camera_position()
    
    def on_wheel_down(self):
        """Handler for mouse wheel down (zoom out)"""
        self.camera_distance = min(self.max_distance, self.camera_distance + 0.5)
        self.update_camera_position()
    
    def update_camera(self, task):
        """Task to update camera based on mouse input"""
        if self.mouse_button_1 and self.mouseWatcherNode.hasMouse():
            # Get current mouse position
            mouse_x = self.mouseWatcherNode.getMouseX()
            mouse_y = self.mouseWatcherNode.getMouseY()
            
            # Calculate the mouse movement
            dx = mouse_x - self.last_mouse_x
            dy = mouse_y - self.last_mouse_y
            
            # Update camera angles (scale the movement for better control)
            self.camera_heading -= dx * 100.0
            self.camera_pitch += dy * 100.0
            
            # Clamp the pitch to prevent flipping
            self.camera_pitch = min(max(self.camera_pitch, self.min_pitch), self.max_pitch)
            
            # Store current mouse position for next frame
            self.last_mouse_x = mouse_x
            self.last_mouse_y = mouse_y
            
            # Update the camera position
            self.update_camera_position()

            self.update_stats_display()
        
        return task.cont
    
    def update_stats_display(self):
        """Update the onscreen text with current camera stats"""
        self.heading_text.setText(f"Heading: {self.camera_heading:.1f}°")
        self.pitch_text.setText(f"Pitch: {self.camera_pitch:.1f}°")
    
    def update_camera_position(self):
        """Update camera position based on current angles and distance"""
        # Convert angles to radians
        heading_rad = math.radians(self.camera_heading)
        pitch_rad = math.radians(self.camera_pitch)
        
        # Calculate camera position using spherical coordinates
        x = self.camera_distance * math.sin(heading_rad) * math.cos(pitch_rad)
        y = -self.camera_distance * math.cos(heading_rad) * math.cos(pitch_rad)
        z = self.camera_distance * math.sin(pitch_rad)
        
        # Update camera position and make it look at the model
        self.camera.setPos(x, y, z)
        self.camera.lookAt(Point3(0, 0, 0))
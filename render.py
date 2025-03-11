"""
The Render Class processes all visual elements of the application by 
rendering meshes relative to the intended acoustics simulations.
"""


from direct.showbase.ShowBase import ShowBase, loadPrcFileData
from panda3d.core import *
import math, sys, simplepbr, os.path as path
from direct.gui.OnscreenText import OnscreenText

# Enable the assimp loader so that .obj files can be loaded.
loadPrcFileData("", "load-file-type p3assimp")

class Render(ShowBase):

    def load_base(self, name) -> None:
        """Loads a file from a default described in Panda3D

        Args:
            name (_type_): name of the object, i.e. teapot, etc.
            options: teapot, jack, ripple, box, frowney, environment, 
            cmtt12, cmss12, cmr12, camera, shuttle_controls, yup-axis, zup-axis.
        """
        try:
            self.model = self.loader.loadModel(name)
            self.model.reparentTo(self.render)
            self.model.setPos(0, 0, -0.5)
            self.model.setScale(0.5)
            # self.model.setHpr(0, 90, 0)
            self.model.setTransparency(TransparencyAttrib.MAlpha)
            # self.model.setAlphaScale(0.8)

        except:
            print('Unable to load model. Please make sure that the model type exists.')

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


    def model_loader(self, filename) -> None:
        """Match the file extension and load the model accordingly.

        Args:
            filename (str): name of the model file.
        """
        match filename[-4:] == '.obj':
            case True:
                self.load_obj(filename)
            case False:
                self.load_base(filename)
            case _:
                print('Invalid file format. Only .obj files are supported.')
                sys.exit()

    def create_floor(self):
        """Create a floor grid beneath the teapot"""
        # Create a CardMaker to make a flat card
        cm = CardMaker('floor')
        cm.setFrame(-10, 10, -10, 10)  # 20x20 unit floor
        
        # Create the floor and attach it to the scene
        floor = self.render.attachNewNode(cm.generate())
        floor.setP(-90)  # Rotate it to be horizontal (pitch -90 degrees)
        floor.setZ(-0.5)  # Position slightly below the origin to avoid z-fighting
        floor.setColor(0.5, 1.0, 0.5, 1)  # Set the color to light gray


    def axes_indicator(self) -> None:
        """Renders axes indicator to bottom corner of the screen"""
        corner = self.aspect2d.attachNewNode("corner of screen")
        corner.setPos(-1.2, 0, -0.9)
        self.axis = self.loader.loadModel("zup-axis")
        self.axis.setScale(0.025)
        self.axis.reparentTo(corner)

    def axisTask(self, task):
        self.axis.setHpr(self.camera.getHpr())
        return task.cont


    def __init__(self, filename) -> None:
        ShowBase.__init__(self)

        simplepbr.init()

        self.setFrameRateMeter(True)
        self.frameRateMeter.setUpdateInterval(0.1)

        # Set background color
        self.setBackgroundColor(0.1, 0.1, 0.2)

        # Load the model and floor
        # self.create_floor()
        self.axes_indicator()
        self.model_loader(filename)

        # Set up lighting
        self.setup_lighting()
        
        # Disable the default camera control system
        self.disableMouse()
        
        # Set up camera parameters
        self.camera_distance = 10.0       # Distance from camera to object
        self.min_distance = 0.0          # Minimum zoom distance
        self.max_distance = 15.0         # Maximum zoom distance
        self.camera_heading = 35.0        # Horizontal rotation angle
        self.camera_pitch = 35.0          # Vertical rotation angle
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
        self.accept("escape", sys.exit)

        # Add the update task.
        self.taskMgr.add(self.update_camera, "UpdateCameraTask")
        self.taskMgr.add(self.axisTask, "axisTask")

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

    def setup_lighting(self):
        """Set up basic scene lighting"""
        # Add ambient light
        ambient_light = AmbientLight("ambient")
        ambient_light.setColor(Vec4(0.3, 0.3, 0.3, 1))
        ambient_np = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_np)
        
        # Add directional light (key light)
        main_light = DirectionalLight("main_light")
        main_light.setColor(Vec4(0.8, 0.8, 0.8, 1))
        main_light_np = self.render.attachNewNode(main_light)
        main_light_np.setHpr(45, -30, 0)
        self.render.setLight(main_light_np)
        
        # Add another directional light for fill
        fill_light = DirectionalLight("fill_light")
        fill_light.setColor(Vec4(0.4, 0.4, 0.5, 1))
        fill_light_np = self.render.attachNewNode(fill_light)
        fill_light_np.setHpr(-45, 20, 0)
        self.render.setLight(fill_light_np)

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

            self.camera_heading = self.camera_heading % 360.0
            
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
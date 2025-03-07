from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight
from panda3d.core import Vec4, Point3
import math

class OrbitCameraDemo(ShowBase):
    def __init__(self):
        # Initialize the ShowBase class (the foundation of any Panda3D app)
        ShowBase.__init__(self)
        
        # Set a dark blue background
        self.setBackgroundColor(0.1, 0.1, 0.2)
        
        # Disable the default camera control system
        self.disableMouse()
        
        # Set up camera parameters
        self.camera_distance = 5.0       # Distance from camera to object
        self.min_distance = 3.0          # Minimum zoom distance
        self.max_distance = 15.0         # Maximum zoom distance
        self.camera_heading = 0.0        # Horizontal rotation angle
        self.camera_pitch = 0.0          # Vertical rotation angle
        self.min_pitch = -85.0           # Limit looking down
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
        
        # Load the object to render (using Panda3D's built-in teapot model)
        self.model = self.loader.loadModel("teapot")
        self.model.reparentTo(self.render)
        self.model.setScale(0.5)
        
        # Set up lighting
        self.setup_lighting()
        
        # Add the camera control task
        self.taskMgr.add(self.update_camera, "UpdateCameraTask")
        
        # Update camera position initially
        self.update_camera_position()
        
        # Add instructions text
        self.add_instructions()
    
    def add_instructions(self):
        """Add on-screen instructions for camera controls"""
        instructions = """
        Camera Controls:
        - Left Mouse Button + Drag: Rotate camera
        - Mouse Wheel: Zoom in/out
        """
        # self.instructions_text = self.addText(instructions, pos=(-1.3, 0.9), scale=0.07)
        # self.instructions_text.setFg((1, 1, 1, 1))
    
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
            
            # Clamp the pitch to prevent flipping
            self.camera_pitch = min(max(self.camera_pitch, self.min_pitch), self.max_pitch)
            
            # Store current mouse position for next frame
            self.last_mouse_x = mouse_x
            self.last_mouse_y = mouse_y
            
            # Update the camera position
            self.update_camera_position()
        
        return task.cont
    
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

# Run the application
app = OrbitCameraDemo()
app.run()
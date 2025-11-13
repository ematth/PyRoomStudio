"""
Main application class for the 3D Architecture GUI
"""
import pygame
from typing import List
from OpenGL.GL import *
from OpenGL.GLU import *

from .constants import Colors
from .base_components import GUIComponent, TextButton, ImageButton
from .menu_components import MenuBar
from .panel_components import LibraryPanel, PropertyPanel, AssetsPanel


class MainApplication:
    """Main application class that demonstrates all GUI components"""
    
    def __init__(self, width: int = 1200, height: int = 800):
        self.width = width
        self.height = height
        
        # Set up OpenGL context
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        
        self.screen = pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF)
        pygame.display.set_caption("PyRoomStudio")
        
        # Basic OpenGL setup - will be configured properly by Render3 class
        # Don't set up OpenGL state here to avoid conflicts
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Initialize 3D renderer
        self.renderer = None
        self.viewport_rect = None
        self.init_3d_renderer()
        
        # Sound source file for acoustic simulation
        self.sound_source_file = None  # Will use default if None
        
        # Initialize GUI components
        self.init_gui()
    
    def init_3d_renderer(self):
        """Initialize the 3D renderer - starts empty"""
        # Define viewport area (where 3D content will be rendered)
        self.viewport_rect = pygame.Rect(200, 90, self.width - 400, self.height - 220)
        
        # Start with no 3D model loaded
        self.renderer = None
        print("3D viewport initialized - no model loaded")
    
    def load_stl_file(self, filepath: str):
        """Load an STL file into the 3D renderer"""
        try:
            # Clear any existing renderer and assets first
            print("Clearing previous renderer and assets...")
            
            # Clear OpenGL state if we have an existing renderer
            if self.renderer:
                print("Previous renderer found, clearing OpenGL state...")
                try:
                    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                    
                    # Reset matrices
                    glMatrixMode(GL_PROJECTION)
                    glLoadIdentity()
                    glMatrixMode(GL_MODELVIEW)
                    glLoadIdentity()
                except Exception as gl_error:
                    print(f"OpenGL cleanup error (ignoring): {gl_error}")
            else:
                print("No previous renderer found")
            
            self.renderer = None
            
            # Clear assets panel
            for component in self.components:
                if isinstance(component, AssetsPanel):
                    component.clear_surfaces()
                    break
            
            # Import Render class and create new renderer
            from render import Render
            print(f"Loading new 3D model: {filepath}")
            print(f"Viewport rect: {self.viewport_rect}")
            print(f"Window height: {self.height}")
            
            self.renderer = Render(filepath, self.viewport_rect, self.height)
            print(f"Successfully created renderer for: {filepath}")
            print(f"Renderer model has {len(self.renderer.model.vectors)} triangles")
            
            # Connect renderer to PropertyPanel for scale control
            self.connect_renderer_to_property_panel()
            
            # Extract surface information and populate assets panel
            self.populate_assets_from_renderer(filepath)
            
            return True
        except Exception as e:
            print(f"Error loading 3D model {filepath}: {e}")
            import traceback
            traceback.print_exc()
            self.renderer = None
            return False
    
    def connect_renderer_to_property_panel(self):
        """Connect the renderer to the property panel for scale control"""
        if not self.renderer:
            return
        
        # Find the property panel
        property_panel = None
        for component in self.components:
            if isinstance(component, PropertyPanel):
                property_panel = component
                break
        
        if property_panel:
            # Set the renderer reference in the property panel
            property_panel.set_renderer(self.renderer)
            print(f"Connected renderer to property panel (scale: {self.renderer.model_scale_factor:.2f}x)")
        else:
            print("Warning: Property panel not found")
    
    def populate_assets_from_renderer(self, filepath: str):
        """Extract surface information from the renderer and populate the assets panel"""
        if not self.renderer:
            print("No renderer available for asset population")
            return
        
        try:
            # Debug: Check if renderer has surface information
            print(f"Renderer has {len(self.renderer.surface_colors)} surface colors")
            
            # Get surface information from the renderer
            surfaces = []
            
            for i, surface_color in enumerate(self.renderer.surface_colors):
                print(f"Surface {i}: {surface_color}")
                
                # Convert from float (0-1) to int (0-255) for display
                if all(isinstance(c, float) for c in surface_color):
                    display_color = tuple(int(c * 255) for c in surface_color[:3])  # Take only RGB, ignore alpha if present
                else:
                    display_color = tuple(surface_color[:3])  # Take only RGB
                
                surface_name = f"Surface {i+1}"
                surfaces.append((surface_name, display_color, i))
                print(f"Added surface: {surface_name} with color {display_color}")
            
            print(f"Total surfaces to add: {len(surfaces)}")
            
            # Find the assets panel and populate it
            assets_panel = None
            for component in self.components:
                if isinstance(component, AssetsPanel):
                    assets_panel = component
                    break
            
            if assets_panel:
                print("Found assets panel, adding surfaces...")
                assets_panel.add_stl_surfaces(filepath, surfaces)
                print("Surfaces added to assets panel")
            else:
                print("ERROR: Assets panel not found!")
                    
        except Exception as e:
            print(f"Error populating assets panel: {e}")
            import traceback
            traceback.print_exc()
    
    def open_stl_file_dialog(self):
        """Open a file dialog to select an STL file"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            # Create a temporary root window (hidden)
            root = tk.Tk()
            root.withdraw()  # Hide the root window
            
            # Open file dialog
            filepath = filedialog.askopenfilename(
                title="Open STL File",
                filetypes=[
                    ("STL files", "*.stl"),
                    ("All files", "*.*")
                ]
            )
            
            # Clean up the temporary window
            root.destroy()
            
            if filepath:
                return self.load_stl_file(filepath)
            return False
            
        except ImportError:
            print("tkinter not available - cannot open file dialog")
            return False
        except Exception as e:
            print(f"Error opening file dialog: {e}")
            return False
    
    def init_gui(self):
        """Initialize all GUI components"""
        self.components: List[GUIComponent] = []
        
        # Menu bar at the very top
        self.menu_bar = MenuBar(0, 0, self.width, 25)
        
        # Add Settings menu
        settings_menu = [
            ("Preferences", self.on_preferences, "Future feature!", False),
            ("Display Settings", self.on_display_settings, "Future feature!", False),
            ("Audio Settings", self.on_audio_settings, "Future feature!", False),
            ("Keyboard Shortcuts", self.on_keyboard_shortcuts, "Future feature!", False),
        ]
        self.menu_bar.add_menu("Settings", settings_menu)
        
        # Add File menu
        file_menu = [
            ("New Project", self.on_new_project, None, True),  # Enabled
            ("Open Project", self.on_open_project, None, True),  # Enabled
            ("Save Project", self.on_save_project, "Future feature!", False),
            ("Save As...", self.on_save_as, "Future feature!", False),
            ("Import...", self.on_import, "Future feature!", False),
            ("Export...", self.on_export, "Future feature!", False),
            ("Recent Projects", self.on_recent_projects, "Future feature!", False),
            ("Exit", self.on_exit, None, True),  # Enabled
        ]
        self.menu_bar.add_menu("File", file_menu)
        
        # Add Edit menu
        edit_menu = [
            ("Undo", self.on_undo, "Future feature!", False),
            ("Redo", self.on_redo, "Future feature!", False),
            ("Cut", self.on_cut, "Future feature!", False),
            ("Copy", self.on_copy, "Future feature!", False),
            ("Paste", self.on_paste, "Future feature!", False),
            ("Delete", self.on_delete, "Future feature!", False),
            ("Select All", self.on_select_all, "Future feature!", False),
            ("Find", self.on_find, "Future feature!", False),
        ]
        self.menu_bar.add_menu("Edit", edit_menu)
        
        self.components.append(self.menu_bar)
        
        # Top toolbar buttons (moved down to accommodate menu bar)
        toolbar_y = 30  # Moved down from 10
        button_width = 60
        button_height = 50
        button_spacing = 5
        start_x = 50
        
        # Create toolbar buttons using the asset images
        toolbar_buttons = [
            ("Move", "assets/button_move.png", self.on_move_click),
            ("Copy", "assets/button_copy.png", self.on_copy_click),
            ("Cut", "assets/button_cut.png", self.on_cut_click),
            ("Paste", "assets/button_paste.png", self.on_paste_click),
            ("Delete", "assets/button_delete.png", self.on_delete_click),
            ("Measure", "assets/button_measure.png", self.on_measure_click),
        ]
        
        for i, (name, image_path, callback) in enumerate(toolbar_buttons):
            x = start_x + i * (button_width + button_spacing)
            button = ImageButton(x, toolbar_y, button_width, button_height, image_path, callback, tooltip="Future feature!")
            button.enabled = False  # Disable all toolbar buttons
            self.components.append(button)
        
        # Left panel - Library (using new LibraryPanel)
        panel_y = 90  # Moved down from 80
        library_panel = LibraryPanel(10, panel_y, 180, 500)
        self.components.append(library_panel)
        
        # Right panels - Property and Assets (split into two)
        right_panel_x = self.width - 200
        
        # Property panel (top half) - needs more height for all elements
        property_height = 320  # Increased to fit all elements including toggles
        property_panel = PropertyPanel(right_panel_x, panel_y, 190, property_height)
        self.components.append(property_panel)
        
        # Assets panel (bottom half) - expanded downwards
        assets_y = panel_y + property_height + 20  # More spacing between panels
        assets_height = 280  # Expanded height for more surface visibility
        assets_panel = AssetsPanel(right_panel_x, assets_y, 190, assets_height)
        self.components.append(assets_panel)
        
        # Bottom toolbar
        bottom_buttons = [
            ("Import Room", self.on_import_room, None, True),  # Enabled - same as File -> Open Project
            ("Import Sound", self.on_import_sound, None, True),  # Enabled
            ("Place Listener", self.on_place_listener, "Future feature!", False),
            ("Render", self.on_render, None, True)  # Enabled
        ]
        
        button_width = 100
        total_width = len(bottom_buttons) * button_width + (len(bottom_buttons) - 1) * 10
        start_x = (self.width - total_width) // 2
        
        for i, (text, callback, tooltip, enabled) in enumerate(bottom_buttons):
            x = start_x + i * (button_width + 10)
            button = TextButton(x, self.height - 40, button_width, 30, text, callback=callback, tooltip=tooltip)
            button.enabled = enabled
            self.components.append(button)
    
    # Menu callback methods
    def on_preferences(self): print("Preferences")
    def on_display_settings(self): print("Display Settings")
    def on_audio_settings(self): print("Audio Settings")
    def on_keyboard_shortcuts(self): print("Keyboard Shortcuts")
    
    def on_new_project(self): 
        print("New Project")
        # Clear the current 3D model
        self.renderer = None
        
        # Clear the assets panel
        for component in self.components:
            if isinstance(component, AssetsPanel):
                component.clear_surfaces()
                break
        
        print("Cleared 3D model and assets")
    
    def on_open_project(self): 
        print("Opening STL file...")
        if self.open_stl_file_dialog():
            print("STL file loaded successfully")
        else:
            print("No file selected or failed to load")
    def on_save_project(self): print("Save Project")
    def on_save_as(self): print("Save As...")
    def on_import(self): print("Import...")
    def on_export(self): print("Export...")
    def on_recent_projects(self): print("Recent Projects")
    def on_exit(self): 
        print("Exit")
        self.running = False
    
    def on_undo(self): print("Undo")
    def on_redo(self): print("Redo")
    def on_cut(self): print("Cut")
    def on_copy(self): print("Copy")
    def on_paste(self): print("Paste")
    def on_delete(self): print("Delete")
    def on_select_all(self): print("Select All")
    def on_find(self): print("Find")
    
    # Toolbar callback methods
    def on_move_click(self): print("Move tool selected")
    def on_copy_click(self): print("Copy tool selected")
    def on_cut_click(self): print("Cut tool selected") 
    def on_paste_click(self): print("Paste tool selected")
    def on_delete_click(self): print("Delete tool selected")
    def on_measure_click(self): print("Measure tool selected")
    
    # Panel callback methods
    def on_library_item_select(self, item): print(f"Library item selected: {item}")
    
    def on_import_room(self):
        """Import a 3D room model (same as File -> Open Project)"""
        print("Opening STL file...")
        if self.open_stl_file_dialog():
            print("STL file loaded successfully")
        else:
            print("No file selected or failed to load")
    
    def on_import_sound(self):
        """Open a file dialog to select a sound source for acoustic simulation"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            # Create a temporary root window (hidden)
            root = tk.Tk()
            root.withdraw()  # Hide the root window
            
            # Open file dialog for audio files
            filepath = filedialog.askopenfilename(
                title="Select Sound Source File",
                filetypes=[
                    ("Audio files", "*.wav *.mp3 *.flac *.ogg"),
                    ("WAV files", "*.wav"),
                    ("All files", "*.*")
                ],
                initialdir="sounds/sources"
            )
            
            # Clean up the temporary window
            root.destroy()
            
            if filepath:
                self.sound_source_file = filepath
                print(f"Sound source selected: {filepath}")
                # Update window title to show loaded sound
                sound_name = filepath.split('/')[-1].split('\\')[-1]
                pygame.display.set_caption(f"PyRoomStudio - Sound: {sound_name}")
                return True
            else:
                print("No sound file selected")
                return False
            
        except ImportError:
            print("tkinter not available - cannot open file dialog")
            return False
        except Exception as e:
            print(f"Error opening sound file dialog: {e}")
            return False
    
    def on_place_listener(self): print("Place listener")
    
    def on_render(self):
        """Trigger acoustic simulation using the loaded 3D model"""
        print("=" * 60)
        print("Starting Acoustic Simulation...")
        print("=" * 60)
        
        # Check if 3D model is loaded
        if not self.renderer:
            print("ERROR: No 3D model loaded. Please load an STL file first.")
            print("Use File → Open Project to load a model.")
            return
        
        try:
            # Update window title to show simulation in progress
            pygame.display.set_caption("PyRoomStudio - Simulating...")
            
            # Extract necessary data from the renderer
            print("Extracting geometry data from 3D model...")
            walls = self.renderer.get_walls_for_acoustic()
            room_center = self.renderer.get_room_center()
            model_vertices = self.renderer.get_model_vertices()
            
            print(f"  - Found {len(walls)} surfaces")
            print(f"  - Room center: {room_center}")
            print(f"  - Total vertices: {len(model_vertices)}")
            
            # Import and create acoustic simulator
            from acoustic import Acoustic
            print("\nInitializing acoustic simulator...")
            acoustic = Acoustic()
            
            # Get the current scale factor from the renderer
            scale_factor = self.renderer.model_scale_factor
            print(f"Using scale factor from renderer: {scale_factor:.4f}x")
            
            # Run the simulation with custom sound source if loaded
            print("Running PyRoomAcoustics simulation...")
            if self.sound_source_file:
                print(f"Using custom sound source: {self.sound_source_file}")
            else:
                print("Using default sound source")
            print("(This may take a few moments...)")
            output_file = acoustic.simulate(walls, room_center, model_vertices, scale_factor, self.sound_source_file)
            
            # Restore window title (keep sound name if loaded)
            if self.sound_source_file:
                sound_name = self.sound_source_file.split('/')[-1].split('\\')[-1]
                pygame.display.set_caption(f"PyRoomStudio - Sound: {sound_name}")
            else:
                pygame.display.set_caption("PyRoomStudio")
            
            # Print success message
            print("\n" + "=" * 60)
            print("SIMULATION COMPLETE!")
            print("=" * 60)
            print(f"Output saved to: {output_file}")
            print("You can now play this file to hear the simulated acoustics.")
            print("=" * 60)
            
        except FileNotFoundError as e:
            print(f"\nERROR: File not found - {e}")
            print("Make sure the sound source file exists in the sounds/sources/ directory.")
            pygame.display.set_caption("PyRoomStudio")
            
        except ValueError as e:
            print(f"\nERROR: Invalid input - {e}")
            print("The 3D model geometry may be invalid for acoustic simulation.")
            pygame.display.set_caption("PyRoomStudio")
            
        except RuntimeError as e:
            print(f"\nERROR: Simulation error - {e}")
            print("The acoustic simulation encountered an error.")
            pygame.display.set_caption("PyRoomStudio")
            
        except Exception as e:
            print(f"\nERROR: Unexpected error - {e}")
            import traceback
            traceback.print_exc()
            pygame.display.set_caption("PyRoomStudio")
            print("Please check the error message above for details.")
    
    def handle_events(self):
        """Handle all pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # Check if event is in 3D viewport area or is a mouse wheel event
            viewport_event = False
            if self.viewport_rect and self.renderer:
                # Mouse wheel events don't have 'pos' attribute, so handle them separately
                if event.type == pygame.MOUSEWHEEL:
                    mouse_pos = pygame.mouse.get_pos()
                    if self.viewport_rect.collidepoint(mouse_pos):
                        viewport_event = True
                        self.renderer.check_keybinds(event)
                # Handle other mouse events with position
                elif hasattr(event, 'pos'):
                    if self.viewport_rect.collidepoint(event.pos):
                        viewport_event = True
                        # Route event to 3D renderer
                        self.renderer.check_keybinds(event)
            
            # Let GUI components handle events (if not consumed by 3D viewport)
            if not viewport_event:
                for component in self.components:
                    if component.handle_event(event):
                        break  # Stop processing if event was consumed
            
            # Handle keyboard events for 3D renderer (not position-dependent)
            if event.type == pygame.KEYDOWN and self.renderer:
                self.renderer.check_keybinds(event)
    
    def update(self, dt: float):
        """Update all components"""
        for component in self.components:
            component.update(dt)
        
        # Update surface colors in assets panel if 3D model is loaded
        self.sync_surface_colors()
    
    def sync_surface_colors(self):
        """Synchronize surface colors between 3D renderer and assets panel"""
        if not self.renderer:
            return
        
        try:
            # Find the assets panel
            assets_panel = None
            for component in self.components:
                if isinstance(component, AssetsPanel):
                    assets_panel = component
                    break
            
            if not assets_panel:
                return
            
            # Update each surface color
            for i, surface_color in enumerate(self.renderer.surface_colors):
                # Convert from float (0-1) to int (0-255) for display
                if all(isinstance(c, float) for c in surface_color):
                    display_color = tuple(int(c * 255) for c in surface_color[:3])
                else:
                    display_color = tuple(surface_color[:3])
                
                assets_panel.update_surface_color(i, display_color)
                
        except Exception as e:
            # Silently handle errors to avoid spam in console
            pass
    
    def draw(self):
        """Draw everything with mixed OpenGL 3D and 2D GUI"""
        # Clear the screen
        glClearColor(1.0, 1.0, 1.0, 1.0)  # White background
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Render 3D scene first (if renderer is available)
        if self.renderer:
            try:
                self.renderer.draw_scene()
            except Exception as e:
                print(f"Error drawing 3D scene: {e}")
                import traceback
                traceback.print_exc()
        
        # Switch to 2D rendering for GUI
        self.setup_2d_rendering()
        
        # Create a pygame surface for 2D GUI rendering
        gui_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        gui_surface.fill((0, 0, 0, 0))  # Transparent background
        
        # Draw placeholder if no 3D model is loaded
        if not self.renderer:
            placeholder_surface = self.draw_placeholder_viewport()
            gui_surface.blit(placeholder_surface, (self.viewport_rect.x, self.viewport_rect.y))
        
        # Draw all GUI components on the surface (without any dropdowns)
        for component in self.components:
            if isinstance(component, MenuBar):
                component.draw_base(gui_surface)
            elif isinstance(component, PropertyPanel):
                component.draw_base(gui_surface)
            else:
                component.draw(gui_surface)
        
        # Draw all dropdowns last (on top of everything)
        for component in self.components:
            if isinstance(component, MenuBar):
                component.draw_dropdowns(gui_surface)
            elif isinstance(component, PropertyPanel):
                component.draw_dropdowns(gui_surface)
        
        # Draw all tooltips last (on top of everything including dropdowns)
        self.draw_all_tooltips(gui_surface)
        
        # Blit the GUI surface to OpenGL
        self.blit_surface_to_opengl(gui_surface)
        
        pygame.display.flip()
    
    def draw_all_tooltips(self, surface: pygame.Surface):
        """Draw tooltips for all components, ensuring they render on top of everything"""
        for component in self.components:
            self._draw_component_tooltips(component, surface)
    
    def _draw_component_tooltips(self, component, surface: pygame.Surface):
        """Recursively draw tooltips for a component and its children"""
        # Draw tooltip for this component
        if hasattr(component, 'draw_tooltip'):
            component.draw_tooltip(surface)
        
        # Draw tooltips for child components
        if hasattr(component, 'components'):
            for child in component.components:
                self._draw_component_tooltips(child, surface)
        
        # Special handling for panels with galleries
        if isinstance(component, LibraryPanel):
            galleries = component.sound_galleries if component.active_tab == "SOUND" else component.material_galleries
            for gallery in galleries:
                self._draw_component_tooltips(gallery, surface)
        
        if isinstance(component, AssetsPanel):
            for gallery in component.galleries:
                self._draw_component_tooltips(gallery, surface)
        
        # Handle gallery image items
        if hasattr(component, 'image_items'):
            for item in component.image_items:
                self._draw_component_tooltips(item, surface)
        
        # Handle gallery surface items
        if hasattr(component, 'surface_items'):
            for item in component.surface_items:
                self._draw_component_tooltips(item, surface)
        
        # Handle radio button groups
        if hasattr(component, 'radio_buttons'):
            for radio in component.radio_buttons:
                self._draw_component_tooltips(radio, surface)
        
        # Handle menu bar dropdown items
        if isinstance(component, MenuBar) and hasattr(component, 'dropdown_items'):
            for item in component.dropdown_items:
                self._draw_component_tooltips(item, surface)
    
    def draw_placeholder_viewport(self):
        """Draw a placeholder when 3D renderer is not available"""
        # Use pygame surface for better text rendering
        placeholder_surface = pygame.Surface((self.viewport_rect.width, self.viewport_rect.height))
        placeholder_surface.fill(Colors.LIGHT_GRAY)
        
        # Draw border
        pygame.draw.rect(placeholder_surface, Colors.DARK_GRAY, 
                        pygame.Rect(0, 0, self.viewport_rect.width, self.viewport_rect.height), 2)
        
        # Draw message text
        font = pygame.font.Font(None, 24)
        text_lines = [
            "No 3D Model Loaded",
            "",
            "File → Open Project",
            "to load an STL file"
        ]
        
        total_text_height = len(text_lines) * 30
        start_y = (self.viewport_rect.height - total_text_height) // 2
        
        for i, line in enumerate(text_lines):
            if line:  # Skip empty lines
                text_surface = font.render(line, True, Colors.DARK_GRAY)
                text_rect = text_surface.get_rect()
                text_rect.centerx = self.viewport_rect.width // 2
                text_rect.y = start_y + i * 30
                placeholder_surface.blit(text_surface, text_rect)
        
        return placeholder_surface
    
    def setup_2d_rendering(self):
        """Set up OpenGL for 2D GUI rendering"""
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    def blit_surface_to_opengl(self, surface):
        """Convert pygame surface to OpenGL texture and render it"""
        # Convert surface to string data
        w, h = surface.get_size()
        raw = pygame.image.tostring(surface, 'RGBA')
        
        # Create and bind texture
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, raw)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        # Enable texturing and render
        glEnable(GL_TEXTURE_2D)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, 0)
        glTexCoord2f(1, 0); glVertex2f(w, 0)
        glTexCoord2f(1, 1); glVertex2f(w, h)
        glTexCoord2f(0, 1); glVertex2f(0, h)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        
        # Clean up
        glDeleteTextures([texture_id])
        
        # Restore matrices
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_DEPTH_TEST)
    
    def run(self):
        """Main game loop"""
        while self.running:
            dt = self.clock.tick(60) / 1000.0  # Delta time in seconds
            
            self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()

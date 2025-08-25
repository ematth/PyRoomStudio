import pygame
from pygame.locals import *
import pygame_gui
import sys
import os
from render3 import Render3
from pygame_gui.elements import (UIButton, UIPanel, UITextBox, UILabel, 
                                 UIHorizontalSlider, UITextEntryLine, UIImage)

class GUI:
    def __init__(self, width=1280, height=720):
        pygame.init()
        self.width = width
        self.height = height
        self.window_surface = pygame.display.set_mode((width, height), pygame.RESIZABLE | DOUBLEBUF | OPENGL)
        pygame.display.set_caption('3D ARRE')

        self.ui_manager = pygame_gui.UIManager((width, height))
        
        self.background = pygame.Surface((width, height))
        self.background.fill(self.ui_manager.get_theme().get_colour('dark_bg'))
        
        self.setup_ui()

        # Initialize the 3D renderer in the central view
        self.view_3d_rect = pygame.Rect(200, 60, self.width - 450, self.height - 60)
        model_name: str = 'resources/prism_star_5.stl' if (len(sys.argv) < 2) else sys.argv[1]
        self.renderer = Render3(model_name, self.view_3d_rect, self.height)

        self.running = True
        self.clock = pygame.time.Clock()

    def load_icon(self, path, size=(60, 60), color=(200, 200, 200)):
        if os.path.exists(path):
            return pygame.image.load(path)
        else:
            print(f"Warning: Icon not found at {path}. Creating a placeholder.")
            placeholder = pygame.Surface(size)
            placeholder.fill(color)
            return placeholder

    def setup_ui(self):
        # Top toolbar
        self.toolbar_panel = UIPanel(relative_rect=pygame.Rect(0, 0, self.width, 60),
                                      starting_height=1,
                                      manager=self.ui_manager)
        
        self.render_button = UIButton(relative_rect=pygame.Rect(10, 10, 100, 40),
                                        text='Render',
                                        manager=self.ui_manager,
                                        container=self.toolbar_panel)
                                        
        self.import_room_button = UIButton(relative_rect=pygame.Rect(120, 10, 120, 40),
                                           text='Import Room',
                                           manager=self.ui_manager,
                                           container=self.toolbar_panel)

        self.place_sound_button = UIButton(relative_rect=pygame.Rect(250, 10, 120, 40),
                                           text='Place Sound',
                                           manager=self.ui_manager,
                                           container=self.toolbar_panel)

        self.place_listener_button = UIButton(relative_rect=pygame.Rect(380, 10, 120, 40),
                                              text='Place Listener',
                                              manager=self.ui_manager,
                                              container=self.toolbar_panel)

        # Left library panel
        self.library_panel = UIPanel(relative_rect=pygame.Rect(0, 60, 200, self.height - 60),
                                      starting_height=1,
                                      manager=self.ui_manager)

        self.sound_button = UIButton(relative_rect=pygame.Rect(10, 10, 80, 30),
                                      text='SOUND',
                                      manager=self.ui_manager,
                                      container=self.library_panel)

        self.material_button = UIButton(relative_rect=pygame.Rect(100, 10, 80, 30),
                                         text='MATERIAL',
                                         manager=self.ui_manager,
                                         container=self.library_panel)
        
        # --- Sound Library Content ---
        self.sound_library_content = UIPanel(relative_rect=pygame.Rect(0, 50, 180, self.library_panel.relative_rect.height - 60),
                                              manager=self.ui_manager, container=self.library_panel, visible=True)
        
        UILabel(relative_rect=pygame.Rect(10, 0, 100, 20), text='- Voices', 
                manager=self.ui_manager, container=self.sound_library_content)

        # Voice icons
        icon_size = (60, 60)
        self.adult_male_icon = UIImage(relative_rect=pygame.Rect(10, 30, *icon_size), 
                                       image_surface=self.load_icon('resources/icons/adult_male.png', icon_size, (255, 0, 0)), 
                                       manager=self.ui_manager, container=self.sound_library_content)
        self.adult_female_icon = UIImage(relative_rect=pygame.Rect(80, 30, *icon_size), 
                                         image_surface=self.load_icon('resources/icons/adult_female.png', icon_size, (0, 0, 255)), 
                                         manager=self.ui_manager, container=self.sound_library_content)
        self.young_boy_icon = UIImage(relative_rect=pygame.Rect(10, 100, *icon_size), 
                                      image_surface=self.load_icon('resources/icons/young_boy.png', icon_size, (0, 255, 0)), 
                                      manager=self.ui_manager, container=self.sound_library_content)
        self.young_girl_icon = UIImage(relative_rect=pygame.Rect(80, 100, *icon_size), 
                                       image_surface=self.load_icon('resources/icons/young_girl.png', icon_size, (255, 255, 0)), 
                                       manager=self.ui_manager, container=self.sound_library_content)

        # Collapsible sections
        UIButton(relative_rect=pygame.Rect(10, 170, 150, 20), text='+ HVAC', 
                 manager=self.ui_manager, container=self.sound_library_content)
        UIButton(relative_rect=pygame.Rect(10, 200, 150, 20), text='+ Electronics', 
                 manager=self.ui_manager, container=self.sound_library_content)
        UIButton(relative_rect=pygame.Rect(10, 230, 150, 20), text='+ Custom', 
                 manager=self.ui_manager, container=self.sound_library_content)

        # --- Material Library Content (Initially Hidden) ---
        self.material_library_content = UIPanel(relative_rect=pygame.Rect(0, 50, 180, self.library_panel.relative_rect.height - 60),
                                                manager=self.ui_manager, container=self.library_panel, visible=False)
        UILabel(relative_rect=pygame.Rect(10, 0, 100, 20), text='- Materials',
                manager=self.ui_manager, container=self.material_library_content)

        # Right inspector panel
        self.inspector_panel = UIPanel(relative_rect=pygame.Rect(self.width - 250, 0, 250, self.height),
                                       starting_height=1,
                                       manager=self.ui_manager)
                                       
        self.sound_label = UILabel(relative_rect=pygame.Rect(10, 10, 230, 20),
                                   text='Sound',
                                   manager=self.ui_manager,
                                   container=self.inspector_panel)
                                   
        self.volume_label = UILabel(relative_rect=pygame.Rect(10, 40, 100, 20),
                                    text='Volume',
                                    manager=self.ui_manager,
                                    container=self.inspector_panel)
                                    
        self.volume_slider = UIHorizontalSlider(relative_rect=pygame.Rect(10, 60, 230, 20),
                                                start_value=50,
                                                value_range=(0, 100),
                                                manager=self.ui_manager,
                                                container=self.inspector_panel)

        self.location_label = UILabel(relative_rect=pygame.Rect(10, 90, 100, 20),
                                      text='Location',
                                      manager=self.ui_manager,
                                      container=self.inspector_panel)

        self.x_entry = UITextEntryLine(relative_rect=pygame.Rect(10, 120, 50, 30),
                                       manager=self.ui_manager,
                                       container=self.inspector_panel)
        self.y_entry = UITextEntryLine(relative_rect=pygame.Rect(70, 120, 50, 30),
                                       manager=self.ui_manager,
                                       container=self.inspector_panel)
        self.z_entry = UITextEntryLine(relative_rect=pygame.Rect(130, 120, 50, 30),
                                       manager=self.ui_manager,
                                       container=self.inspector_panel)
                                       
        # Assets Panel
        self.assets_panel = UIPanel(relative_rect=pygame.Rect(self.width - 250, 300, 250, self.height - 300),
                                     starting_height=1,
                                     manager=self.ui_manager)
        
        self.assets_label = UILabel(relative_rect=pygame.Rect(10, 10, 100, 20),
                                    text='ASSETS',
                                    manager=self.ui_manager,
                                    container=self.assets_panel)

    def run(self):
        while self.running:
            time_delta = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.file_menu_button:
                        # Placeholder for file menu functionality
                        print("File menu clicked")
                    if event.ui_element == self.sound_button:
                        self.sound_library_content.show()
                        self.material_library_content.hide()
                    if event.ui_element == self.material_button:
                        self.sound_library_content.hide()
                        self.material_library_content.show()
                
                # Pass mouse events to the renderer only if the mouse is over the 3D view
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
                    if self.view_3d_rect.collidepoint(event.pos):
                        self.renderer.check_keybinds(event)
                else:
                    self.renderer.check_keybinds(event)

                self.ui_manager.process_events(event)

            self.ui_manager.update(time_delta)
            
            self.window_surface.blit(self.background, (0, 0))

            # Draw the 3D scene
            self.renderer.draw_scene()

            # Draw the UI on top
            self.ui_manager.draw_ui(self.window_surface)

            pygame.display.flip()

        pygame.quit()

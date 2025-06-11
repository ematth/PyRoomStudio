from render2 import Render
from acoustic import Acoustic
import sys
import time
import pygame
from OpenGL.GL import *

class App():
    def __init__(self, model_name):
        self.name = 'App'
        self.model = None
        self.acoustic = Acoustic()
        self.render = Render(filename=model_name, acoustic=self.acoustic)
        self.running = True

    def run(self):
        """Main application loop"""
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        self.render.mouse_down = True
                        self.render.last_mouse_pos = pygame.mouse.get_pos()
                        # Handle click for highlighting
                        self.render.handle_click(pygame.mouse.get_pos())
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.render.mouse_down = False
                elif event.type == pygame.MOUSEWHEEL:
                    # Zoom in/out
                    if event.y > 0:
                        self.render.camera_distance = max(self.render.min_distance, 
                                                        self.render.camera_distance - 0.5)
                    else:
                        self.render.camera_distance = min(self.render.max_distance, 
                                                        self.render.camera_distance + 0.5)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_p:
                        print("Starting acoustic simulation...")
                        self.acoustic.simulate(self.render.walls, self.render.center, self.render.model['vertices'])
                        print("Acoustic simulation finished.")
                    elif event.key == pygame.K_f:
                        self.render.flip_model_x()

            # Handle mouse movement for camera rotation
            if self.render.mouse_down and self.render.last_mouse_pos:
                current_pos = pygame.mouse.get_pos()
                dx = current_pos[0] - self.render.last_mouse_pos[0]
                dy = current_pos[1] - self.render.last_mouse_pos[1]
                
                self.render.camera_heading -= dx * 0.5
                self.render.camera_pitch += dy * 0.5
                self.render.camera_pitch = min(max(self.render.camera_pitch, self.render.min_pitch), 
                                             self.render.max_pitch)
                
                self.render.last_mouse_pos = current_pos

            # Clear the screen and depth buffer
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            # Update camera and draw scene
            self.render.update_camera()
            self.render.draw_model()
            # self.render.draw_axes()
            
            # Draw the stats (text) on top of the 3D scene
            self.render.draw_stats()
            
            # Update the display
            pygame.display.flip()
            pygame.time.wait(10)

        pygame.quit()

if __name__ == '__main__':
    model_name: str = 'resources/INRIA_MUSIS.stl' if (len(sys.argv) < 2) else sys.argv[1]
    app = App(model_name)
    app.run()

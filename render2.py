"""
The Render2 Class processes all visual elements of the application using PyGame and PyOpenGL
to render meshes relative to the intended acoustics simulations.
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from stl import mesh
import math
import sys
from acoustic import Acoustic
import collections

# Constants for camera control
CAMERA_DIST = 5.0      # Distance from camera to object
MIN_DIST = 1.0         # Minimum zoom distance
MAX_DIST = 5.0         # Maximum zoom distance
CAMERA_HEADING = 35.0  # Horizontal rotation angle
CAMERA_PITCH = 35.0    # Vertical rotation angle
MIN_PITCH = 0.0        # Limit looking down
MAX_PITCH = 85.0       # Limit looking up

class Render:
    def __init__(self, filename, acoustic: Acoustic, width=800, height=600):
        """Initialize the renderer with PyGame and OpenGL"""
        pygame.init()
        self.width = width
        self.height = height
        self.display = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("3D Model Viewer")
        
        # Set up OpenGL
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Set up the viewport
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (width/height), 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)
        
        # Set white background
        glClearColor(1.0, 1.0, 1.0, 1.0)
        
        # Initialize camera parameters
        self.camera_distance = CAMERA_DIST
        self.camera_heading = CAMERA_HEADING
        self.camera_pitch = CAMERA_PITCH
        self.min_distance = MIN_DIST
        self.max_distance = MAX_DIST
        self.min_pitch = MIN_PITCH
        self.max_pitch = MAX_PITCH
        
        # Mouse control variables
        self.mouse_down = False
        self.last_mouse_pos = None
        
        # Load the model
        self.center, self.volume = self.compute_volumetric_properties(filename)
        self.ratio = (self.volume / 1000 / 7500)
        self.model = self.load_model(filename)
        
        # Process the model to find walls
        self.walls = self.find_walls()
        self._calculate_2d_layout()
        
        # Generate unique colors for each wall
        self.wall_colors = self.generate_wall_colors(len(self.walls))
        
        # Store acoustic reference
        self.acoustic = acoustic
        
        # Set up lighting
        self.setup_lighting()
        
        # Initialize font for text rendering
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)
        
        # Initialize model rotation state
        self.model_rotation_x = 0.0
        self.view_mode = '3D' # '3D' or '2D'

    def compute_volumetric_properties(self, filename: str) -> tuple[np.ndarray, float]:
        """Computes the volumetric center (centroid) of a closed triangular mesh."""
        stl_mesh = mesh.Mesh.from_file(filename)
        
        total_volume = 0.0
        centroid_sum = np.zeros(3)
        
        for triangle in stl_mesh.vectors:
            v0, v1, v2 = triangle
            tetra_volume = np.dot(v0, np.cross(v1, v2)) / 6.0
            tetra_centroid = (v0 + v1 + v2) / 4.0
            
            centroid_sum += tetra_centroid * tetra_volume
            total_volume += tetra_volume
            
        if np.isclose(total_volume, 0):
            raise ValueError("Calculated volume is zero; ensure the STL mesh is closed and valid.")
            
        volumetric_center = centroid_sum / total_volume
        return volumetric_center, total_volume

    def load_model(self, filename):
        """Load a 3D model from file"""
        if filename.endswith('.stl'):
            stl_mesh = mesh.Mesh.from_file(filename)
            vertices = stl_mesh.vectors.reshape(-1, 3)
            normals = stl_mesh.normals
            return {'vertices': vertices, 'normals': normals}
        else:
            raise ValueError("Only .stl files are supported")

    def setup_lighting(self):
        """Set up scene lighting"""
        # Ambient light
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        
        # Main light
        glLightfv(GL_LIGHT0, GL_POSITION, [1, 1, 1, 0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])

    def update_camera(self):
        """Update camera position based on current angles and distance"""
        glLoadIdentity()
        
        # Convert angles to radians
        heading_rad = math.radians(self.camera_heading)
        pitch_rad = math.radians(self.camera_pitch)
        
        # Calculate camera position using spherical coordinates
        x = self.camera_distance * math.sin(heading_rad) * math.cos(pitch_rad)
        y = -self.camera_distance * math.cos(heading_rad) * math.cos(pitch_rad)
        z = self.camera_distance * math.sin(pitch_rad)
        
        gluLookAt(x, y, z, 0, 0, 0, 0, 0, 1)

    def get_ray_from_mouse(self, mouse_pos):
        """Convert mouse position to a ray in world space"""
        # Get viewport and modelview/projection matrices
        viewport = glGetIntegerv(GL_VIEWPORT)
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        
        # Convert mouse position to normalized device coordinates
        x = mouse_pos[0]
        y = viewport[3] - mouse_pos[1]  # Flip y coordinate
        
        # Get near and far points in world space
        near = gluUnProject(x, y, 0.0, modelview, projection, viewport)
        far = gluUnProject(x, y, 1.0, modelview, projection, viewport)
        
        # Calculate ray direction
        ray_dir = np.array(far) - np.array(near)
        ray_dir = ray_dir / np.linalg.norm(ray_dir)
        
        return np.array(near), ray_dir

    def check_triangle_intersection(self, ray_origin, ray_dir, triangle):
        """Check if ray intersects with triangle using Möller–Trumbore algorithm"""
        v0, v1, v2 = triangle
        
        # Calculate edges
        edge1 = v1 - v0
        edge2 = v2 - v0
        
        # Calculate determinant
        h = np.cross(ray_dir, edge2)
        a = np.dot(edge1, h)
        
        if abs(a) < 1e-6:
            return None  # Ray is parallel to triangle
            
        f = 1.0 / a
        s = ray_origin - v0
        u = f * np.dot(s, h)
        
        if u < 0.0 or u > 1.0:
            return None
            
        q = np.cross(s, edge1)
        v = f * np.dot(ray_dir, q)
        
        if v < 0.0 or u + v > 1.0:
            return None
            
        t = f * np.dot(edge2, q)
        
        if t > 1e-6:
            return t
            
        return None

    def find_walls(self):
        """Groups connected, coplanar triangles into a single wall."""
        walls = []
        processed_triangles = set()
        for i in range(len(self.model['normals'])):
            if i in processed_triangles:
                continue
            
            wall_triangles = self.find_connected_coplanar_triangles(i)
            walls.append({
                'triangles': list(wall_triangles),
                'normal': self.model['normals'][i],
            })
            processed_triangles.update(wall_triangles)
        return walls

    def find_connected_coplanar_triangles(self, start_triangle_idx):
        """Finds all triangles connected to the start triangle that are on the same plane."""
        connected = set()
        to_check = {start_triangle_idx}

        start_normal = self.model['normals'][start_triangle_idx]
        start_vertex = self.model['vertices'][start_triangle_idx * 3]
        TOLERANCE = 1e-2 

        while to_check:
            current_idx = to_check.pop()
            if current_idx in connected:
                continue
            
            connected.add(current_idx)
            
            v_current_set = {tuple(v) for v in self.model['vertices'][current_idx*3 : (current_idx*3)+3]}

            for other_idx in range(len(self.model['normals'])):
                if other_idx in connected or other_idx in to_check:
                    continue
                
                v_other_set = {tuple(v) for v in self.model['vertices'][other_idx*3 : (other_idx*3)+3]}
                if len(v_current_set.intersection(v_other_set)) >= 2:
                    is_coplanar = True
                    for i in range(3):
                        ov = self.model['vertices'][other_idx * 3 + i]
                        distance = abs(np.dot(ov - start_vertex, start_normal))
                        if distance > TOLERANCE:
                            is_coplanar = False
                            break
                    
                    if is_coplanar:
                        to_check.add(other_idx)
        
        return connected

    def generate_wall_colors(self, num_walls):
        """Generate visually distinct colors for walls using HSV color space"""
        colors = []
        golden_ratio = 0.618033988749895  # Golden ratio conjugate
        saturation = 0.7  # Slightly less saturated for better visibility
        value = 0.95  # Bright but not full brightness
        
        for i in range(num_walls):
            # Use golden ratio to generate evenly distributed hues
            hue = (i * golden_ratio) % 1.0
            
            # Convert HSV to RGB
            h = hue * 6
            c = value * saturation
            x = c * (1 - abs(h % 2 - 1))
            m = value - c
            
            if h < 1:
                r, g, b = c, x, 0
            elif h < 2:
                r, g, b = x, c, 0
            elif h < 3:
                r, g, b = 0, c, x
            elif h < 4:
                r, g, b = 0, x, c
            elif h < 5:
                r, g, b = x, 0, c
            else:
                r, g, b = c, 0, x
            
            # Add the monochromatic component and alpha
            colors.append([r + m, g + m, b + m, 0.7])  # 0.7 alpha for transparency
        
        return colors

    def _calculate_2d_layout(self):
        """
        Calculates a 2D layout by "unfolding" the model. Adjacents walls
        are placed next to each other.
        """
        self.wall_2d_layouts = []
        if not self.walls:
            return

        # 1. For each wall, compute its local 2D projection and 3D boundary edges
        for i, wall in enumerate(self.walls):
            # Project 3D triangles to a local 2D plane
            normal = wall['normal']
            if abs(normal[0]) > 0.1 or abs(normal[1]) > 0.1:
                u_axis = np.array([-normal[1], normal[0], 0])
            else:
                u_axis = np.array([0, -normal[2], normal[1]])
            u_axis = u_axis / np.linalg.norm(u_axis)
            v_axis = np.cross(normal, u_axis)

            vtx_3d_to_2d = {}
            for tri_idx in wall['triangles']:
                for vert_3d in self.model['vertices'][tri_idx*3 : tri_idx*3+3]:
                    v_tuple = tuple(vert_3d)
                    if v_tuple not in vtx_3d_to_2d:
                        x_2d = np.dot(vert_3d, u_axis)
                        y_2d = np.dot(vert_3d, v_axis)
                        vtx_3d_to_2d[v_tuple] = np.array([x_2d, y_2d])
            
            wall['vtx_3d_to_2d'] = vtx_3d_to_2d
            
            # Find 3D boundary edges using frequency count
            edges_3d = {}
            for tri_idx in wall['triangles']:
                v = [tuple(vert) for vert in self.model['vertices'][tri_idx*3 : tri_idx*3+3]]
                wall_edges = [tuple(sorted((v[0], v[1]))), tuple(sorted((v[1], v[2]))), tuple(sorted((v[2], v[0])))]
                for edge in wall_edges:
                    edges_3d[edge] = edges_3d.get(edge, 0) + 1
            wall['boundary_edges_3d'] = {edge for edge, count in edges_3d.items() if count == 1}

        # 2. Create a simple horizontal layout for the walls
        current_x = 0
        for wall in self.walls:
            if 'vtx_3d_to_2d' not in wall or not wall['vtx_3d_to_2d']:
                self.wall_2d_layouts.append(None)
                continue

            all_2d_verts = list(wall['vtx_3d_to_2d'].values())
            min_xy = np.min(all_2d_verts, axis=0)
            max_xy = np.max(all_2d_verts, axis=0)

            offset = -min_xy
            normalized_triangles_2d = []
            for tri_idx in wall['triangles']:
                tri_2d = []
                for v_3d in self.model['vertices'][tri_idx*3:tri_idx*3+3]:
                    v_tuple = tuple(v_3d)
                    v_2d = wall['vtx_3d_to_2d'][v_tuple] + offset
                    tri_2d.append(v_2d)
                normalized_triangles_2d.append(tri_2d)
            
            layout_info = {
                'width': max_xy[0] - min_xy[0],
                'height': max_xy[1] - min_xy[1],
                'triangles_2d': normalized_triangles_2d,
                'pos_x': current_x,
                'pos_y': 0,
            }
            self.wall_2d_layouts.append(layout_info)
            current_x += layout_info['width'] + 50

    def draw_model(self):
        """Dispatches to the correct drawing method based on the view mode."""
        if self.view_mode == '3D':
            self.draw_model_3d()
        else:
            self.draw_model_2d()

    def draw_model_3d(self):
        """Draw the loaded 3D model."""
        glPushMatrix()
        
        glDisable(GL_LIGHTING)
        
        # Scale and center the model
        scale = 1/self.ratio
        glScalef(scale, scale, scale)
        center = self.center
        glTranslatef(-center[0], -center[1], -center[2])
        
        # Apply X-axis rotation
        glRotatef(self.model_rotation_x, 1, 0, 0)

        all_triangles = []
        for wall_idx, wall in enumerate(self.walls):
            for tri_idx in wall['triangles']:
                all_triangles.append({'tri_idx': tri_idx, 'wall_idx': wall_idx})

        camera_pos = np.array([0, 0, 0]) 
        for tri_info in all_triangles:
            vertices = self.model['vertices'][tri_info['tri_idx']*3 : tri_info['tri_idx']*3+3]
            avg_z = np.mean([np.linalg.norm(np.array(v) - camera_pos) for v in vertices])
            tri_info['depth'] = avg_z
        
        sorted_triangles = sorted(all_triangles, key=lambda x: -x['depth'])

        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(1.0, 1.0) 

        glBegin(GL_TRIANGLES)
        for tri_info in sorted_triangles:
            wall_idx, tri_idx = tri_info['wall_idx'], tri_info['tri_idx']
            glColor4fv(self.wall_colors[wall_idx])
            for vertex in self.model['vertices'][tri_idx*3 : tri_idx*3+3]:
                glVertex3fv(vertex)
        glEnd()

        glDisable(GL_POLYGON_OFFSET_FILL)

        glLineWidth(2.0)
        glColor4f(0.0, 0.0, 0.0, 1.0) 
        
        glBegin(GL_LINES)
        for wall in self.walls:
            edges = {}
            for tri_idx in wall['triangles']:
                v = [tuple(vert) for vert in self.model['vertices'][tri_idx*3 : tri_idx*3+3]]
                wall_edges = [tuple(sorted((v[0], v[1]))), tuple(sorted((v[1], v[2]))), tuple(sorted((v[2], v[0])))]
                for edge in wall_edges:
                    edges[edge] = edges.get(edge, 0) + 1
            
            for edge, count in edges.items():
                if count == 1:
                    glVertex3fv(edge[0])
                    glVertex3fv(edge[1])
        glEnd()
        
        glEnable(GL_LIGHTING)
        glPopMatrix()

    def draw_model_2d(self):
        """Draws the 2D unfolded layout of the walls."""
        # This is a placeholder. The full implementation is complex.
        # For now, it will draw the simple horizontal layout.
        glPushMatrix()
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        
        total_width = sum(layout['width'] + 50 for layout in self.wall_2d_layouts if layout)
        max_height = max((layout['height'] for layout in self.wall_2d_layouts if layout), default=1)
        gluOrtho2D(-50, total_width, -50, max_height + 50)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        
        for i, layout_info in enumerate(self.wall_2d_layouts):
            if not layout_info: continue
            
            glPushMatrix()
            glTranslatef(layout_info['pos_x'], layout_info['pos_y'], 0)
            
            glColor4fv(self.wall_colors[i])
            glBegin(GL_TRIANGLES)
            for tri_2d in layout_info['triangles_2d']:
                for vert_2d in tri_2d:
                    glVertex2fv(vert_2d)
            glEnd()

            glPopMatrix()

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        glPopMatrix()

    def draw_axes(self):
        """Draw coordinate axes"""
        glPushMatrix()
        glBegin(GL_LINES)
        
        # X axis (red)
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(1, 0, 0)
        
        # Y axis (green)
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 1, 0)
        
        # Z axis (blue)
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 1)
        
        glEnd()
        glPopMatrix()

    def draw_stats(self):
        """Draw camera statistics on screen"""
        if self.view_mode == '2D':
            return
            
        # Create text surfaces with black color for better visibility on white background
        heading_text = f"Heading: {self.camera_heading%360:.1f}°"
        pitch_text = f"Pitch: {self.camera_pitch:.1f}°"
        
        heading_surface = self.font.render(heading_text, True, (0, 0, 0))
        pitch_surface = self.font.render(pitch_text, True, (0, 0, 0))
        
        # Switch to 2D rendering mode
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Disable depth testing and lighting for 2D rendering
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        
        # Enable blending for text
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Convert PyGame surface to OpenGL texture
        heading_data = pygame.image.tostring(heading_surface, "RGBA", True)
        pitch_data = pygame.image.tostring(pitch_surface, "RGBA", True)
        
        # Create and bind textures
        heading_texture = glGenTextures(1)
        pitch_texture = glGenTextures(1)
        
        # Upload heading texture
        glBindTexture(GL_TEXTURE_2D, heading_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, heading_surface.get_width(), heading_surface.get_height(), 
                    0, GL_RGBA, GL_UNSIGNED_BYTE, heading_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        
        # Upload pitch texture
        glBindTexture(GL_TEXTURE_2D, pitch_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, pitch_surface.get_width(), pitch_surface.get_height(), 
                    0, GL_RGBA, GL_UNSIGNED_BYTE, pitch_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        
        # Enable texturing
        glEnable(GL_TEXTURE_2D)
        
        # Draw heading text (flipped texture coordinates to fix upside-down text)
        glBindTexture(GL_TEXTURE_2D, heading_texture)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(20, 20)
        glTexCoord2f(1, 1); glVertex2f(20 + heading_surface.get_width(), 20)
        glTexCoord2f(1, 0); glVertex2f(20 + heading_surface.get_width(), 20 + heading_surface.get_height())
        glTexCoord2f(0, 0); glVertex2f(20, 20 + heading_surface.get_height())
        glEnd()
        
        # Draw pitch text (flipped texture coordinates to fix upside-down text)
        glBindTexture(GL_TEXTURE_2D, pitch_texture)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(20, 60)
        glTexCoord2f(1, 1); glVertex2f(20 + pitch_surface.get_width(), 60)
        glTexCoord2f(1, 0); glVertex2f(20 + pitch_surface.get_width(), 60 + pitch_surface.get_height())
        glTexCoord2f(0, 0); glVertex2f(20, 60 + pitch_surface.get_height())
        glEnd()
        
        # Clean up
        glDeleteTextures([heading_texture, pitch_texture])
        glDisable(GL_TEXTURE_2D)
        
        # Restore OpenGL state
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

    def flip_model_x(self):
        """Flip the model 90 degrees around the X axis"""
        self.model_rotation_x = (self.model_rotation_x + 90) % 360 

    def toggle_view_mode(self):
        """Toggles between 3D and 2D layout view."""
        if self.view_mode == '3D':
            self.view_mode = '2D'
        else:
            self.view_mode = '3D' 
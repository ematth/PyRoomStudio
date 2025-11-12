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
import random
from PIL import Image

class Render:
    def __init__(self, filename, view_rect, window_height):
        self.view_rect = view_rect
        self.window_height = window_height
        self.width = view_rect.width
        self.height = view_rect.height
        
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)  # Enable blending for transparency
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)  # Standard alpha blending
        glEnable(GL_TEXTURE_2D)  # Enable texturing
        glClearColor(1.0, 1.0, 1.0, 1.0) # This will be cleared over by the GUI background

        self.model = mesh.Mesh.from_file(filename)
        self.center, self.size = self.compute_center_and_size()
        
        # Scale factor for model (1.0 = original size)
        self.model_scale_factor = 1.0
        self.original_size = self.size  # Store unscaled size
        self.original_center = self.center.copy()
        
        # Auto-normalize the model to realistic room size
        self.auto_normalize_scale()
        
        # Set up projection with dynamic clipping planes based on scaled model size
        self.update_projection()
        
        # Note: camera distances are set by auto_normalize_scale via set_scale_factor
        self.camera_heading = 35.0  # degrees
        self.camera_pitch = 35.0    # degrees
        self.mouse_down = False
        self.last_mouse_pos = None
        self.mouse_down_pos = None  # Track where mouse was pressed
        self.transparent_mode = False  # Track transparency state

        # The following is no longer needed since GUI now controls the main loop
        # self.running = True

        # Load texture
        self.texture_id = self.load_texture("cat.png")

        # Build edge map for feature/boundary edge detection
        self.feature_edges = self.compute_feature_edges(angle_threshold_degrees=10)

        # Group triangles into surfaces
        self.surfaces = self.group_triangles_into_surfaces()
        self.default_surface_color = [0.6, 0.8, 1.0]
        self.surface_colors = [self.default_surface_color[:] for _ in self.surfaces]
        self.surface_materials = [None for _ in self.surfaces]  # None = no texture, True = textured
        # Map triangle index to surface index
        self.triangle_to_surface = {}
        for surf_idx, surf in enumerate(self.surfaces):
            for tri_idx in surf:
                self.triangle_to_surface[tri_idx] = surf_idx

    def load_texture(self, filename):
        """Load a texture from file and return the OpenGL texture ID"""
        try:
            image = Image.open(filename)
            image = image.transpose(Image.FLIP_TOP_BOTTOM)  # OpenGL expects bottom-left origin
            
            # Convert to RGB if it's not already
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Ensure power-of-2 dimensions for better compatibility
            width, height = image.size
            if not (width & (width - 1) == 0) or not (height & (height - 1) == 0):
                # Resize to nearest power of 2
                new_width = 2 ** (width - 1).bit_length()
                new_height = 2 ** (height - 1).bit_length()
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"Resized texture to {new_width}x{new_height} for better compatibility")
            
            image_data = image.tobytes()
            
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.width, image.height, 0, GL_RGB, GL_UNSIGNED_BYTE, image_data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glGenerateMipmap(GL_TEXTURE_2D)
            
            print(f"Successfully loaded texture: {filename} ({image.width}x{image.height})")
            return texture_id
        except Exception as e:
            print(f"Error loading texture {filename}: {e}")
            return None

    def get_texture_coords_from_normal(self, vertex, normal, surface_bounds=None):
        """Calculate texture coordinates based on surface normal direction"""
        # Normalize the normal vector
        normal = normal / np.linalg.norm(normal)
        
        # Use world coordinates directly for more predictable mapping
        # This avoids the complex normal-based coordinate system that was causing issues
        
        # Get the dominant axis of the normal to determine the mapping plane
        abs_normal = np.abs(normal)
        dominant_axis = np.argmax(abs_normal)
        
        if dominant_axis == 0:  # Normal mostly in X direction
            # Map using Y and Z coordinates
            tex_x = vertex[1]  # Y coordinate
            tex_y = vertex[2]  # Z coordinate
        elif dominant_axis == 1:  # Normal mostly in Y direction
            # Map using X and Z coordinates
            tex_x = vertex[0]  # X coordinate
            tex_y = vertex[2]  # Z coordinate
        else:  # Normal mostly in Z direction (dominant_axis == 2)
            # Map using X and Y coordinates
            tex_x = vertex[0]  # X coordinate
            tex_y = vertex[1]  # Y coordinate
        
        # If we have surface bounds, normalize to the surface extent
        if surface_bounds:
            min_x, max_x, min_y, max_y = surface_bounds
            range_x = max_x - min_x
            range_y = max_y - min_y
            
            # Normalize coordinates
            if range_x > 0:
                tex_x = (tex_x - min_x) / range_x
            else:
                tex_x = 0.5
            if range_y > 0:
                tex_y = (tex_y - min_y) / range_y
            else:
                tex_y = 0.5
        else:
            # Fallback to simple mapping if no bounds provided
            # Scale and center the coordinates
            tex_x = tex_x * 0.1 + 0.5  # Scale down and center
            tex_y = tex_y * 0.1 + 0.5  # Scale down and center
        
        # Ensure coordinates are within [0, 1] range
        tex_x = max(0.0, min(1.0, tex_x))
        tex_y = max(0.0, min(1.0, tex_y))
        
        return [tex_x, tex_y]

    def random_color(self):
        return [random.uniform(0.2, 0.9), random.uniform(0.2, 0.9), random.uniform(0.2, 0.9)]

    def group_triangles_into_surfaces(self):
        # Use BFS to group triangles connected without crossing a feature edge
        triangles = self.model.vectors
        n_tris = len(triangles)
        edge_to_triangles = {}
        for tri_idx, tri in enumerate(triangles):
            for i in range(3):
                v1 = tuple(tri[i])
                v2 = tuple(tri[(i+1)%3])
                edge = tuple(sorted([v1, v2]))
                if edge not in edge_to_triangles:
                    edge_to_triangles[edge] = []
                edge_to_triangles[edge].append(tri_idx)
        visited = [False] * n_tris
        surfaces = []
        for tri_idx in range(n_tris):
            if visited[tri_idx]:
                continue
            # Start a new surface
            surface = set()
            queue = [tri_idx]
            while queue:
                t = queue.pop()
                if visited[t]:
                    continue
                visited[t] = True
                surface.add(t)
                tri = triangles[t]
                for i in range(3):
                    v1 = tuple(tri[i])
                    v2 = tuple(tri[(i+1)%3])
                    edge = tuple(sorted([v1, v2]))
                    if edge in self.feature_edges:
                        continue  # Don't cross feature edge
                    # Add neighboring triangle sharing this edge
                    for neighbor in edge_to_triangles[edge]:
                        if not visited[neighbor]:
                            queue.append(neighbor)
            surfaces.append(surface)
        return surfaces

    def compute_center_and_size(self):
        min_ = np.min(self.model.vectors.reshape(-1, 3), axis=0)
        max_ = np.max(self.model.vectors.reshape(-1, 3), axis=0)
        center = (min_ + max_) / 2
        size = np.linalg.norm(max_ - min_)
        return center, size

    def compute_feature_edges(self, angle_threshold_degrees=30):
        # Map edges to the triangles that share them
        edge_to_triangles = {}
        triangles = self.model.vectors
        normals = self.model.normals
        for tri_idx, tri in enumerate(triangles):
            for i in range(3):
                v1 = tuple(tri[i])
                v2 = tuple(tri[(i+1)%3])
                edge = tuple(sorted([v1, v2]))
                if edge not in edge_to_triangles:
                    edge_to_triangles[edge] = []
                edge_to_triangles[edge].append(tri_idx)
        feature_edges = set()
        threshold_rad = np.radians(angle_threshold_degrees)
        for edge, tris in edge_to_triangles.items():
            if len(tris) == 1:
                # Boundary edge
                feature_edges.add(edge)
            elif len(tris) == 2:
                n1 = normals[tris[0]]
                n2 = normals[tris[1]]
                angle = np.arccos(np.clip(np.dot(n1, n2) / (np.linalg.norm(n1) * np.linalg.norm(n2)), -1.0, 1.0))
                if angle > threshold_rad:
                    feature_edges.add(edge)
        return feature_edges

    def update_camera(self):
        glLoadIdentity()
        heading_rad = np.radians(self.camera_heading)
        pitch_rad = np.radians(self.camera_pitch)
        x = self.camera_distance * np.sin(heading_rad) * np.cos(pitch_rad)
        y = -self.camera_distance * np.cos(heading_rad) * np.cos(pitch_rad)
        z = self.camera_distance * np.sin(pitch_rad)
        gluLookAt(x, y, z, 0, 0, 0, 0, 0, 1)

    def get_ray_from_mouse(self, mouse_pos):
        viewport = glGetIntegerv(GL_VIEWPORT)
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        x = mouse_pos[0]
        y = viewport[3] - mouse_pos[1]
        near = gluUnProject(x, y, 0.0, modelview, projection, viewport)
        far = gluUnProject(x, y, 1.0, modelview, projection, viewport)
        ray_origin = np.array(near)
        ray_dir = np.array(far) - np.array(near)
        ray_dir = ray_dir / np.linalg.norm(ray_dir)
        return ray_origin, ray_dir

    def ray_triangle_intersect(self, ray_origin, ray_dir, triangle):
        # Möller–Trumbore intersection
        v0, v1, v2 = triangle
        eps = 1e-8
        edge1 = v1 - v0
        edge2 = v2 - v0
        h = np.cross(ray_dir, edge2)
        a = np.dot(edge1, h)
        if -eps < a < eps:
            return None  # Parallel
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
        if t > eps:
            return t
        return None

    def draw_measurement_grid(self):
        """
        Draw a measurement grid on the floor to show scale.
        Grid spacing is 1 meter in scaled space.
        """
        glPushMatrix()
        self.update_camera()
        
        # Apply same scaling as model
        glScalef(self.model_scale_factor, self.model_scale_factor, self.model_scale_factor)
        
        # Apply same translation as model to align the grid
        glTranslatef(-self.center[0], -self.center[1], -self.center[2])
        
        # Get model bounds to position grid appropriately
        min_ = np.min(self.model.vectors.reshape(-1, 3), axis=0)
        max_ = np.max(self.model.vectors.reshape(-1, 3), axis=0)
        
        # Position grid exactly at the bottom of the model (min Z)
        grid_z = min_[2]
        
        # Center the grid at the horizontal center of the model
        grid_center_x = (min_[0] + max_[0]) / 2
        grid_center_y = (min_[1] + max_[1]) / 2
        
        # Calculate grid extent - make it 1.5x the model size for better visibility
        model_extent_x = max_[0] - min_[0]
        model_extent_y = max_[1] - min_[1]
        grid_size = max(model_extent_x, model_extent_y) * 0.75
        
        # Grid spacing in original model units (will be scaled)
        # Since we want 1 meter spacing in real world, and model is scaled,
        # we need to calculate spacing in original units
        meter_in_original_units = 1.0 / self.model_scale_factor
        minor_spacing = meter_in_original_units  # 1 meter
        major_spacing = minor_spacing * 5  # 5 meters
        
        # Number of grid lines
        num_lines = int(grid_size / minor_spacing) + 1
        
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        
        # Draw grid lines
        for i in range(-num_lines, num_lines + 1):
            offset = i * minor_spacing
            
            # Determine if this is a major or minor line
            is_major = (i % 5 == 0)
            
            if is_major:
                glColor4f(0.4, 0.4, 0.4, 0.8)  # Darker for major lines
                glLineWidth(2)
            else:
                glColor4f(0.7, 0.7, 0.7, 0.5)  # Lighter for minor lines
                glLineWidth(1)
            
            # Lines parallel to X axis
            glBegin(GL_LINES)
            glVertex3f(grid_center_x - grid_size, grid_center_y + offset, grid_z)
            glVertex3f(grid_center_x + grid_size, grid_center_y + offset, grid_z)
            glEnd()
            
            # Lines parallel to Y axis
            glBegin(GL_LINES)
            glVertex3f(grid_center_x + offset, grid_center_y - grid_size, grid_z)
            glVertex3f(grid_center_x + offset, grid_center_y + grid_size, grid_z)
            glEnd()
        
        glPopMatrix()
    
    def draw_model(self):
        glPushMatrix()
        self.update_camera()
        
        # Apply model scaling
        glScalef(self.model_scale_factor, self.model_scale_factor, self.model_scale_factor)
        
        glTranslatef(-self.center[0], -self.center[1], -self.center[2])
        triangles = self.model.vectors
        normals = self.model.normals
        
        # Calculate surface bounds for textured surfaces
        surface_bounds = {}
        for surf_idx, material in enumerate(self.surface_materials):
            if material and self.texture_id:
                # Get all triangles in this surface
                surface_triangles = [tri_idx for tri_idx, s_idx in self.triangle_to_surface.items() if s_idx == surf_idx]
                
                # Calculate bounds using the same coordinate system as texture mapping
                if surface_triangles:
                    # Use the first triangle's normal as reference
                    ref_normal = normals[surface_triangles[0]]
                    ref_normal = ref_normal / np.linalg.norm(ref_normal)
                    
                    # Get the dominant axis of the normal
                    abs_normal = np.abs(ref_normal)
                    dominant_axis = np.argmax(abs_normal)
                    
                    # Project all vertices using the same method as texture mapping
                    tex_coords_x = []
                    tex_coords_y = []
                    for tri_idx in surface_triangles:
                        triangle = triangles[tri_idx]
                        for vertex in triangle:
                            if dominant_axis == 0:  # Normal mostly in X direction
                                tex_x = vertex[1]  # Y coordinate
                                tex_y = vertex[2]  # Z coordinate
                            elif dominant_axis == 1:  # Normal mostly in Y direction
                                tex_x = vertex[0]  # X coordinate
                                tex_y = vertex[2]  # Z coordinate
                            else:  # Normal mostly in Z direction
                                tex_x = vertex[0]  # X coordinate
                                tex_y = vertex[1]  # Y coordinate
                            tex_coords_x.append(tex_x)
                            tex_coords_y.append(tex_y)
                    
                    surface_bounds[surf_idx] = (min(tex_coords_x), max(tex_coords_x), 
                                               min(tex_coords_y), max(tex_coords_y))
        
        # Draw textured surfaces first
        for tri_idx, triangle in enumerate(triangles):
            surf_idx = self.triangle_to_surface[tri_idx]
            material = self.surface_materials[surf_idx]
            
            if material and self.texture_id:
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, self.texture_id)
                glColor4f(1.0, 1.0, 1.0, 0.3 if self.transparent_mode else 1.0)  # White for texture
                
                # Get the normal for this triangle
                normal = normals[tri_idx]
                
                # Get surface bounds for this surface
                bounds = surface_bounds.get(surf_idx)
                
                glBegin(GL_TRIANGLES)
                for i, vertex in enumerate(triangle):
                    # Project texture coordinates based on surface normal and bounds
                    tex_coords = self.get_texture_coords_from_normal(vertex, normal, bounds)
                    glTexCoord2f(tex_coords[0], tex_coords[1])
                    glVertex3fv(vertex)
                glEnd()
        
        # Draw non-textured surfaces
        for tri_idx, triangle in enumerate(triangles):
            surf_idx = self.triangle_to_surface[tri_idx]
            material = self.surface_materials[surf_idx]
            
            if not material:
                glDisable(GL_TEXTURE_2D)
                color = self.surface_colors[surf_idx]
                alpha = 0.3 if self.transparent_mode else 1.0
                glColor4f(color[0], color[1], color[2], alpha)
                
                glBegin(GL_TRIANGLES)
                for vertex in triangle:
                    glVertex3fv(vertex)
                glEnd()
        
        # Disable texturing for edges
        glDisable(GL_TEXTURE_2D)
        
        # Draw only feature/boundary edges in black
        glColor3f(0, 0, 0)
        glLineWidth(3)
        glBegin(GL_LINES)
        for v1, v2 in self.feature_edges:
            glVertex3fv(v1)
            glVertex3fv(v2)
        glEnd()
        glPopMatrix()

    def check_keybinds(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click - start drag or prepare for texture application
                self.mouse_down = True
                self.last_mouse_pos = event.pos
                self.mouse_down_pos = event.pos  # Remember where we pressed
            elif event.button == 3:  # Right click - change color immediately
                # Ensure OpenGL matrices are up-to-date for ray picking
                glPushMatrix()
                self.update_camera()
                glScalef(self.model_scale_factor, self.model_scale_factor, self.model_scale_factor)
                glTranslatef(-self.center[0], -self.center[1], -self.center[2])
                ray_origin, ray_dir = self.get_ray_from_mouse(event.pos)
                glPopMatrix()
                triangles = self.model.vectors
                min_t = float('inf')
                hit_tri = None
                for tri_idx, triangle in enumerate(triangles):
                    t = self.ray_triangle_intersect(ray_origin, ray_dir, triangle)
                    if t is not None and t < min_t:
                        min_t = t
                        hit_tri = tri_idx
                if hit_tri is not None:
                    surf_idx = self.triangle_to_surface[hit_tri]
                    self.surface_colors[surf_idx] = self.random_color()
                    self.surface_materials[surf_idx] = None  # Remove texture when changing color
                    print(f"Changed color of surface {surf_idx}")
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.mouse_down = False
                # Only apply texture if this was a click (not a drag)
                if self.mouse_down_pos is not None:
                    dx = event.pos[0] - self.mouse_down_pos[0]
                    dy = event.pos[1] - self.mouse_down_pos[1]
                    drag_distance = (dx*dx + dy*dy) ** 0.5
                    
                    # If mouse moved less than 5 pixels, treat as a click
                    if drag_distance < 5:
                        # Ensure OpenGL matrices are up-to-date for ray picking
                        glPushMatrix()
                        self.update_camera()
                        glScalef(self.model_scale_factor, self.model_scale_factor, self.model_scale_factor)
                        glTranslatef(-self.center[0], -self.center[1], -self.center[2])
                        ray_origin, ray_dir = self.get_ray_from_mouse(event.pos)
                        glPopMatrix()
                        triangles = self.model.vectors
                        min_t = float('inf')
                        hit_tri = None
                        for tri_idx, triangle in enumerate(triangles):
                            t = self.ray_triangle_intersect(ray_origin, ray_dir, triangle)
                            if t is not None and t < min_t:
                                min_t = t
                                hit_tri = tri_idx
                        if hit_tri is not None:
                            surf_idx = self.triangle_to_surface[hit_tri]
                            self.surface_materials[surf_idx] = True  # Apply texture
                            print(f"Applied texture to surface {surf_idx} (texture_id: {self.texture_id})")
                
                self.mouse_down_pos = None  # Reset
        elif event.type == pygame.MOUSEMOTION:
            if self.mouse_down and self.last_mouse_pos:
                x, y = event.pos
                last_x, last_y = self.last_mouse_pos
                dx = x - last_x
                dy = y - last_y
                self.camera_heading -= dx * 0.5
                self.camera_pitch += dy * 0.5
                self.camera_pitch = max(-89, min(89, self.camera_pitch))
                self.last_mouse_pos = (x, y)
        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                self.camera_distance = max(self.min_distance, self.camera_distance - 0.1 * self.size)
            else:
                self.camera_distance = min(self.max_distance, self.camera_distance + 0.1 * self.size)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_t:
                self.transparent_mode = not self.transparent_mode
                print(f"Transparency mode: {'ON' if self.transparent_mode else 'OFF'}")
            elif event.key == pygame.K_r:
                # Reset all surfaces to default
                self.surface_colors = [self.default_surface_color[:] for _ in self.surfaces]
                self.surface_materials = [None for _ in self.surfaces]
                print("Reset all surfaces to default")

    def draw_scene(self):
        # Save current OpenGL state to avoid interfering with pygame_gui rendering
        glPushAttrib(GL_VIEWPORT_BIT | GL_SCISSOR_BIT)
        
        # Set the viewport to the correct sub-region of the window
        glEnable(GL_SCISSOR_TEST)
        glScissor(self.view_rect.x, self.window_height - self.view_rect.y - self.view_rect.height, self.view_rect.width, self.view_rect.height)
        glViewport(self.view_rect.x, self.window_height - self.view_rect.y - self.view_rect.height, self.view_rect.width, self.view_rect.height)
        
        # This method will be called by the GUI class to render the 3D model
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Draw measurement grid first (behind the model)
        self.draw_measurement_grid()
        
        # Draw the 3D model
        self.draw_model()
        
        glDisable(GL_SCISSOR_TEST)
        
        # Restore OpenGL state
        glPopAttrib()
        
    def run(self):
        # The main loop is now controlled by the GUI class
        # This method is no longer needed and can be removed or left empty
        pass
        # self.running = True
        # clock = pygame.time.Clock()
        # while self.running:
        #     for event in pygame.event.get():
        #         self.check_keybinds(event)
        #     glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        #     self.draw_model()
        #     pygame.display.flip()
        #     clock.tick(60)
        # pygame.quit()
    
    def get_walls_for_acoustic(self):
        """
        Return wall information for acoustic simulation.
        Returns a list of dictionaries, each containing triangle indices for a surface.
        """
        walls = []
        for surface in self.surfaces:
            walls.append({
                'triangles': list(surface)
            })
        return walls
    
    def get_room_center(self):
        """Return the center point of the 3D model"""
        return self.center.copy()
    
    def get_model_vertices(self):
        """
        Return flattened vertex array for acoustic simulation.
        Returns vertices in the format expected by acoustic simulation.
        """
        # self.model.vectors is shape (n_triangles, 3, 3)
        # Flatten to (n_triangles * 3, 3) for vertex-by-vertex access
        return self.model.vectors.reshape(-1, 3)
    
    def update_projection(self):
        """
        Update the projection matrix with appropriate clipping planes
        based on the current model scale.
        """
        scaled_size = self.original_size * self.model_scale_factor
        
        # Calculate clipping planes based on scaled size
        # Near plane: close enough to see details
        near_plane = 0.1
        # Far plane: far enough to see the entire model at max distance
        # Use 10x the max camera distance to ensure model never clips
        far_plane = max(100.0, self.max_distance * 10)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (self.width/self.height), near_plane, far_plane)
        glMatrixMode(GL_MODELVIEW)
        
        print(f"Updated projection: near={near_plane}, far={far_plane:.1f}")
    
    def set_scale_factor(self, factor):
        """
        Set the scale factor for the model.
        Updates camera distances to match the new scaled size.
        
        Args:
            factor: Scale multiplier (1.0 = original size)
        """
        self.model_scale_factor = factor
        scaled_size = self.original_size * factor
        
        # Update camera distances based on scaled size
        self.camera_distance = 2.5 * scaled_size
        self.min_distance = 0.2 * scaled_size
        self.max_distance = 5 * scaled_size
        
        # Update projection clipping planes for the new scale
        self.update_projection()
        
        print(f"Scale factor set to {factor:.2f}x (model size: {scaled_size:.2f} units)")
    
    def get_real_world_dimensions(self):
        """
        Get the real-world dimensions of the model in meters.
        Returns (width, height, depth) tuple.
        """
        min_ = np.min(self.model.vectors.reshape(-1, 3), axis=0)
        max_ = np.max(self.model.vectors.reshape(-1, 3), axis=0)
        dimensions = (max_ - min_) * self.model_scale_factor
        return dimensions
    
    def get_real_world_size(self):
        """
        Get the diagonal size of the model in scaled units.
        Returns the size as a single float value.
        """
        return self.original_size * self.model_scale_factor
    
    def auto_normalize_scale(self):
        """
        Automatically calculate and apply a scale factor to normalize the model
        to realistic room dimensions (typically 2-10 meters).
        
        Returns:
            float: The calculated scale factor
        """
        # Target size range for typical rooms (in meters)
        TARGET_SIZE = 6.0  # meters (diagonal)
        
        # If the original size is very large (>1000 units), assume it's in mm or similar
        # and scale it down. This matches the SIZE_REDUCTION_FACTOR used in acoustic.py
        if self.original_size > 1000:
            # Scale down by dividing by 700 to get realistic room size
            scale_factor = 1.0 / 700.0
        elif self.original_size < 1.0:
            # If model is very small, scale it up
            scale_factor = TARGET_SIZE / self.original_size
        else:
            # Model is already in a reasonable range, just normalize to target
            scale_factor = TARGET_SIZE / self.original_size
        
        # Apply the calculated scale factor
        self.set_scale_factor(scale_factor)
        
        print(f"Auto-normalized model: {self.original_size:.2f} -> {self.get_real_world_size():.2f} units")
        
        return scale_factor
    
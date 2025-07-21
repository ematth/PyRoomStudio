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

class Render:
    def __init__(self, filename, width=800, height=600):
        pygame.init()
        self.width = width
        self.height = height
        self.display = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("STL Viewer")

        glEnable(GL_DEPTH_TEST)
        glClearColor(1.0, 1.0, 1.0, 1.0)

        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (width/height), 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

        self.model = mesh.Mesh.from_file(filename)
        self.center, self.size = self.compute_center_and_size()
        self.camera_distance = 2.5 * self.size
        self.min_distance = 0.2 * self.size
        self.max_distance = 5 * self.size
        self.camera_heading = 35.0  # degrees
        self.camera_pitch = 35.0    # degrees
        self.mouse_down = False
        self.last_mouse_pos = None

        # Build edge map for feature/boundary edge detection
        self.feature_edges = self.compute_feature_edges(angle_threshold_degrees=30)

        # Group triangles into surfaces
        self.surfaces = self.group_triangles_into_surfaces()
        self.default_surface_color = [0.6, 0.8, 1.0]
        self.surface_colors = [self.default_surface_color[:] for _ in self.surfaces]
        # Map triangle index to surface index
        self.triangle_to_surface = {}
        for surf_idx, surf in enumerate(self.surfaces):
            for tri_idx in surf:
                self.triangle_to_surface[tri_idx] = surf_idx

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

    def draw_model(self):
        glPushMatrix()
        self.update_camera()
        glTranslatef(-self.center[0], -self.center[1], -self.center[2])
        triangles = self.model.vectors
        for tri_idx, triangle in enumerate(triangles):
            surf_idx = self.triangle_to_surface[tri_idx]
            color = self.surface_colors[surf_idx]
            glColor3fv(color)
            glBegin(GL_TRIANGLES)
            for vertex in triangle:
                glVertex3fv(vertex)
            glEnd()
        # Draw only feature/boundary edges in black
        glColor3f(0, 0, 0)
        glLineWidth(3)
        glBegin(GL_LINES)
        for v1, v2 in self.feature_edges:
            glVertex3fv(v1)
            glVertex3fv(v2)
        glEnd()
        glPopMatrix()

    def run(self):
        running = True
        clock = pygame.time.Clock()
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.mouse_down = True
                        self.last_mouse_pos = pygame.mouse.get_pos()
                        # Ensure OpenGL matrices are up-to-date for ray picking
                        glPushMatrix()
                        self.update_camera()
                        glTranslatef(-self.center[0], -self.center[1], -self.center[2])
                        ray_origin, ray_dir = self.get_ray_from_mouse(self.last_mouse_pos)
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
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.mouse_down = False
                elif event.type == pygame.MOUSEMOTION:
                    if self.mouse_down and self.last_mouse_pos:
                        x, y = pygame.mouse.get_pos()
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
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.draw_model()
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()
    
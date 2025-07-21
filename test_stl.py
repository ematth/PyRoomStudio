import open3d as o3d
import sys

if __name__ == "__main__":
    mesh = o3d.io.read_triangle_mesh(f"resources/{sys.argv[1]}.stl")
    mesh = mesh.compute_vertex_normals()
    o3d.visualization.draw_geometries([mesh], window_name="STL", left=1000, top=200, width=800, height=650)
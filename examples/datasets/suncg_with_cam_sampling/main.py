from src.utility.CameraUtility import CameraUtility
from src.utility.MathUtility import MathUtility
from src.utility.SetupUtility import SetupUtility
SetupUtility.setup([])

from src.utility.sampler.SuncgPointInRoomSampler import SuncgPointInRoomSampler
from src.utility.LabelIdMapping import LabelIdMapping
from src.utility.MeshObjectUtility import MeshObject
from src.utility.MaterialLoaderUtility import MaterialLoaderUtility
from src.utility.SegMapRendererUtility import SegMapRendererUtility

from src.utility.Utility import Utility
from src.utility.camera.CameraValidation import CameraValidation
from src.utility.loader.SuncgLoader import SuncgLoader
from src.utility.lighting.SuncgLighting import SuncgLighting

from src.utility.WriterUtility import WriterUtility
from src.utility.Initializer import Initializer

from src.utility.RendererUtility import RendererUtility
import numpy as np

import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('house', help="Path to the house.json file of the SUNCG scene to load")
parser.add_argument('output_dir', nargs='?', default="examples/datasets/suncg_with_cam_sampling/output", help="Path to where the final files, will be saved")
args = parser.parse_args()

Initializer.init()

# load the objects into the scene
label_mapping = LabelIdMapping.from_csv(Utility.resolve_path(os.path.join('resources', 'id_mappings', 'nyu_idset.csv')))
objs = SuncgLoader.load(args.house, label_mapping)

# makes Suncg objects emit light
SuncgLighting.light()

# Init sampler for sampling locations inside the loaded suncg house
point_sampler = SuncgPointInRoomSampler(objs)
# Init bvh tree containing all mesh objects
bvh_tree = MeshObject.create_bvh_tree_multi_objects([o for o in objs if isinstance(o, MeshObject)])

poses = 0
tries = 0
while tries < 10000 and poses < 5:
    # Sample point inside house
    height = np.random.uniform(0.5, 2)
    location, _ = point_sampler.sample(height)
    # Sample rotation (fix around X and Y axis)
    euler_rotation = np.random.uniform([1.2217, 0, 0], [1.2217, 0, 6.283185307])
    cam2world_matrix = MathUtility.build_transformation_mat(location, euler_rotation)

    # Check that obstacles are at least 1 meter away from the camera and make sure the view interesting enough
    if CameraValidation.perform_obstacle_in_view_check(cam2world_matrix, {"min": 1.0}, bvh_tree) and CameraValidation.scene_coverage_score(cam2world_matrix) > 0.4:
        CameraUtility.add_camera_pose(cam2world_matrix)
        poses += 1
    tries += 1

# activate normal and distance rendering
RendererUtility.enable_normals_output()
RendererUtility.enable_distance_output()
MaterialLoaderUtility.add_alpha_channel_to_textures(blurry_edges=True)

# render the whole pipeline
data = RendererUtility.render()

data.update(SegMapRendererUtility.render(Utility.get_temporary_directory(), Utility.get_temporary_directory(), "class"))

# write the data to a .hdf5 container
WriterUtility.save_to_hdf5(args.output_dir, data)

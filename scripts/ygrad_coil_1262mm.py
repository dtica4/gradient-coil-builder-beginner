# System imports
import sys
import numpy as np

# Logging
import logging

# Local imports
from pyCoilGen.pyCoilGen_release import pyCoilGen
from pyCoilGen.sub_functions.constants import DEBUG_BASIC, DEBUG_VERBOSE

if __name__ == '__main__':
    log = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)

    arg_dict = {
        'field_shape_function': 'y',
        'target_gradient_strength': 0.9,
        'coil_mesh': 'create cylinder mesh',
        'cylinder_mesh_parameter_list': [0.35, 0.0631, 30, 30, 0, 0, 1, 0],  # 126.2 mm diameter
        'target_region_radius': 0.04,
        'secondary_target_weight': 0.5,
        'target_region_resolution': 10,
        'levels': 20,
        'pot_offset_factor': 0.25,
        'interconnection_cut_width': 0.013,
        'normal_shift_length': 0.003,
        'normal_shift_smooth_factors': [4, 6, 4],
        'iteration_num_mesh_refinement': 1,
        'set_roi_into_mesh_center': True,
        'force_cut_selection': ['high'],
        'make_cylindrical_pcb': True,
        'conductor_cross_section_width': 0.0013,
        'conductor_cross_section_height': 0.0013,
        'fasthenry_bin': r'C:\Program Files (x86)\FastFieldSolvers\FastHenry2\FastHenry2.exe',
        'cross_sectional_points': np.array([np.sin(np.linspace(0, 2 * np.pi, 10)),
                                            np.cos(np.linspace(0, 2 * np.pi, 10))]) * 0.0013,
        'tikhonov_reg_factor': 300,
        'smooth_factor': 5,
        'output_directory': 'images',
        'CAD_filename': './{project}_wire_{part_index}_{field_function}.stl',  # wire only, written to examples/
        'project_name': 'ygrad_coil_1262mm',
        'persistence_dir': 'debug',
        'debug': DEBUG_BASIC,
    }

    result = pyCoilGen(log, arg_dict)
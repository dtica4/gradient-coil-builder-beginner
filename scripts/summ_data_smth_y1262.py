import os
import numpy as np
import trimesh
import matplotlib.pyplot as plt
from pyCoilGen.helpers.persistence import load
import pyCoilGen.plotting as pcg_plt

# --- STEP export via OCP (OpenCascade) -------------------------------------
# pip install cadquery-ocp   (or the smaller cadquery-ocp-novtk, no VTK dep)
try:
    from OCP.gp import gp_Pnt
    from OCP.TColgp import TColgp_HArray1OfPnt as _ArrCls
    from OCP.GeomAPI import GeomAPI_Interpolate
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.STEPControl import STEPControl_Writer, STEPControl_StepModelType
    def _make_array(n):
        return _ArrCls(1, n)
except ImportError:
    from OCP.OCP import gp, collections, GeomAPI, BRepBuilderAPI, STEPControl
    gp_Pnt = gp.gp_Pnt
    GeomAPI_Interpolate = GeomAPI.GeomAPI_Interpolate
    BRepBuilderAPI_MakeEdge = BRepBuilderAPI.BRepBuilderAPI_MakeEdge
    STEPControl_Writer = STEPControl.STEPControl_Writer
    STEPControl_StepModelType = STEPControl.STEPControl_StepModelType
    def _make_array(n):
        return collections.HArray1_gp_Pnt(1, n)


def export_step_curve(points_xyz, step_path, tol_mm=1e-6):
    """Write a single B-spline curve through points_xyz (n,3) to a STEP file.
    Uses interpolation (curve passes exactly through every point) rather
    than least-squares approximation - the latter can take minutes on a
    ~5000-point path with sharp kinks (jumper-wire reversals) and was
    hanging for exactly that reason."""
    n = len(points_xyz)
    arr = _make_array(n)
    for idx, (x, y, z) in enumerate(points_xyz, start=1):
        arr.SetValue(idx, gp_Pnt(float(x), float(y), float(z)))
    interp = GeomAPI_Interpolate(arr, False, tol_mm)
    interp.Perform()
    if not interp.IsDone():
        return False
    curve = interp.Curve()
    edge = BRepBuilderAPI_MakeEdge(curve).Edge()
    writer = STEPControl_Writer()
    writer.Transfer(edge, STEPControl_StepModelType.STEPControl_AsIs)
    status = writer.Write(step_path)
    return "Done" in str(status) or "RetDone" in str(status)


#which = 'ygrad_coil_12887mm_hireg'
#which = 'xgrad_coil_116mm'
#which = 'zgrad_coil_13239mm_360len'
which = 'ygrad_coil_1262mm'
#which = 'ygrad_coil_12335mm'
#which = 'xgrad_coil_1176mm'
#which = 'ygrad_coil_1252mm'


solution = load('debug', which, 'final')

# --- Achieved gradient efficiency ---
coords = solution.target_field.coords
b_per_1A = np.asarray(solution.solution_errors.combined_field_layout_per1Amp)
bz = b_per_1A[2] if b_per_1A.ndim == 2 else b_per_1A

axis_map = {'x': 0, 'y': 1, 'z': 2}
gradient_axis = solution.input_args.field_shape_function
axis_index = axis_map[gradient_axis]

coord = coords[axis_index]
slope, offset = np.polyfit(coord, bz, 1)

target_eff = solution.input_args.target_gradient_strength
coil_radius_m = solution.input_args.cylinder_mesh_parameter_list[1]
coil_diameter_mm = coil_radius_m * 2 * 1000

print(f"Gradient axis:        {gradient_axis}")
print(f"Achieved efficiency: {slope * 1000:.4f} mT/m/A   (target: {target_eff})")
print(f"Coil diameter:       {coil_diameter_mm:.1f} mm")

# --- Visualization setup (moved up so save_dir is available below) ---
save_dir = solution.input_args.output_directory
os.makedirs(save_dir, exist_ok=True)
coil_solutions = [solution]

# --- Coil physical length (from the actual wire path geometry) ---
project_name = solution.input_args.project_name
wire_stl_path = f"./{project_name}_wire_0_{gradient_axis}.stl"

wire_mesh = trimesh.load(wire_stl_path)
bounds = wire_mesh.bounds
length_m = bounds[1][2] - bounds[0][2]

print(f"Coil length (wire extent): {length_m * 1000:.1f} mm")
print(f"Swept 3D wire STL (original coil): {wire_stl_path}")

# --- Precise outer diameter of the physical coil (from the actual STL mesh) ---
# coil_diameter_mm (above) is the DESIGN diameter - i.e. the radius the wire's
# CENTERLINE follows. The physical wire tube extends further out than that,
# by roughly half the conductor cross-section, plus normal_shift_length extra
# at return-path sections. Rather than approximate that, read it straight off
# the actual swept STL surface, which already has the true geometry baked in.
verts = wire_mesh.vertices  # (n,3), metres - same coordinate frame as wire_path
radial_dist = np.sqrt(verts[:, 0]**2 + verts[:, 1]**2)
outer_radius_m = radial_dist.max()
outer_diameter_mm = outer_radius_m * 2 * 1000

print(f"\nDesign (centerline) diameter: {coil_diameter_mm:.2f} mm")
print(f"True outer diameter (from STL surface): {outer_diameter_mm:.2f} mm")
print(f"Extra radial reach beyond design radius: {(outer_radius_m - coil_radius_m)*1000:.3f} mm")

# --- Electrical properties (resistance / inductance) ---
wire_points_m = solution.coil_parts[0].wire_path.v.T  # (n,3) metres, x,y,z - needed below

resistance = solution.coil_parts[0].coil_resistance  # pyCoilGen's own estimate: solid conductor, generic copper
inductance = solution.coil_parts[0].coil_inductance  # geometry-only - valid regardless of wire construction

print(f"\nCoil resistance (pyCoilGen, solid-conductor estimate): {resistance} ohm")
print(f"Coil inductance:        {inductance} H")

# --- More accurate resistance using the actual litz wire's datasheet rating ---
# pyCoilGen's resistance above assumes a solid conductor of the given
# cross-section with generic copper resistivity - it doesn't know this is
# litz wire (400 strands x 0.05mm, 0.589 mm^2). The manufacturer's measured
# DC resistance per metre already captures the real stranded construction,
# so multiplying that by the ACTUAL total wire path length (not the bounding
# box length above, which is only the axial extent) gives a more trustworthy
# real-world resistance than reconstructing it from strand geometry.
LITZ_DC_RES_PER_M_MIN = 0.0264  # ohm/m, from datasheet
LITZ_DC_RES_PER_M_MAX = 0.0345  # ohm/m, from datasheet

total_wire_length_m = np.sum(np.linalg.norm(np.diff(wire_points_m, axis=0), axis=1))

resistance_litz_min = total_wire_length_m * LITZ_DC_RES_PER_M_MIN
resistance_litz_max = total_wire_length_m * LITZ_DC_RES_PER_M_MAX

print(f"\nTotal wire path length (actual, not bounding box): {total_wire_length_m:.4f} m")
print(f"Coil resistance (litz wire, datasheet-based): {resistance_litz_min:.4f} - {resistance_litz_max:.4f} ohm")

# --- Voltage and power at a given operating current, using the litz-based resistance ---
current_A = 5.0   # <-- set this to your actual planned operating current

voltage_V_pycoilgen = current_A * resistance
power_W_pycoilgen = current_A**2 * resistance

voltage_V_litz_min = current_A * resistance_litz_min
voltage_V_litz_max = current_A * resistance_litz_max
power_W_litz_min = current_A**2 * resistance_litz_min
power_W_litz_max = current_A**2 * resistance_litz_max

print(f"\nAt {current_A} A operating current:")
print(f"  Voltage (pyCoilGen estimate):  {voltage_V_pycoilgen:.4f} V")
print(f"  Voltage (litz, datasheet):     {voltage_V_litz_min:.4f} - {voltage_V_litz_max:.4f} V")
print(f"  Power (pyCoilGen estimate):    {power_W_pycoilgen:.4f} W")
print(f"  Power (litz, datasheet):       {power_W_litz_min:.4f} - {power_W_litz_max:.4f} W")
print(f"  Resulting gradient:            {slope * 1000 * current_A:.4f} mT/m")

# --- Export the raw wire-path centreline points (cylindrical) to a text file ---
# In millimetres: SolidWorks' default document units are mm, and a raw number
# like 0.0626 (metres) would be read as 0.0626 mm - making the whole coil
# look microscopic. Converting to mm here so the imported size is correct.
wire_points_mm = wire_points_m * 1000.0

points_txt_path = f"./{project_name}_wire_points_{gradient_axis}.txt"
np.savetxt(points_txt_path, wire_points_mm, fmt="%.6f", delimiter="\t",
           header="x_mm\ty_mm\tz_mm", comments="")
print(f"\nWire centreline points ({wire_points_mm.shape[0]} pts, mm) written to: {points_txt_path}")

# --- Unwrap the cylindrical wire path into a flat pattern -----------------
# Single global unwrap. The third column is the REAL radial standoff
# (r - R_nominal) rather than an artificial 0 - this already reflects the
# true 3D geometry (including the normal_shift return-path standoff), so
# crossing wires are naturally separated without any extra fixing.
# Uses wire_points_m (metres) for the actual unwrap math, then converts the
# result to millimetres before writing - same reasoning as above.
x, y, z = wire_points_m[:, 0], wire_points_m[:, 1], wire_points_m[:, 2]

r = np.sqrt(x**2 + y**2)
R_nominal = np.median(r)

theta = np.arctan2(y, x)
theta_unwrapped = np.unwrap(theta)
s = R_nominal * (theta_unwrapped - theta_unwrapped[0])

z_flat = r - R_nominal  # real radial standoff, not an artificial fix

flat_pattern_m = np.column_stack([s, z, z_flat])       # metres
flat_pattern_mm = flat_pattern_m * 1000.0              # millimetres, for SolidWorks

# Decimate before export: the raw path is heavily oversampled (thousands of
# points along an already-smooth curve), and feeding all of them into a
# SolidWorks curve makes every downstream operation (sweep, re-export, etc.)
# slow. Keeping every Nth point preserves the shape - it's not removing any
# real detail, just redundant sampling - while cutting the point count a lot.
DECIMATE_EVERY = 5   # try 5 first; raise to 10 if SolidWorks is still heavy
flat_pattern_mm_export = flat_pattern_mm[::DECIMATE_EVERY]
if not np.array_equal(flat_pattern_mm_export[-1], flat_pattern_mm[-1]):
    flat_pattern_mm_export = np.vstack([flat_pattern_mm_export, flat_pattern_mm[-1]])

flat_txt_path = f"./{project_name}_unwrapped_points_{gradient_axis}.txt"
with open(flat_txt_path, 'w') as f:
    f.write("arc_length_mm\theight_mm\tz_flat_mm\n")
    for row in flat_pattern_mm_export:
        f.write(f"{row[0]:.6f}\t{row[1]:.6f}\t{row[2]:.6f}\n")

print(f"\nExported {len(flat_pattern_mm_export)} points (mm, decimated from {len(flat_pattern_mm)}) to {flat_txt_path}")
print(f"Radial offset range: {z_flat.min()*1000:.3f} mm to {z_flat.max()*1000:.3f} mm")

step_path = f"./{project_name}_unwrapped_{gradient_axis}.step"
step_ok = export_step_curve(flat_pattern_mm_export, step_path)
print(f"Flat pattern STEP (mm): {step_path}  (write ok: {step_ok})")

# --- Error-metric plots, split into three figures -------------------------
# Same 9 plots and the same calculations as pyCoilGen's
# plot_various_error_metrics, but drawn as three separate 1x3 figures (one
# row each), so titles and axis labels never overlap.
def plot_error_metrics_split(solution, title, save_dir=None, dpi=150):
    # Font sizes for this figure (change these to adjust the text)
    suptitle_size = 12      # big title at the top of each figure
    cbar_label_size = 11    # colorbar title (the unit, e.g. "%" or "mT/A")
    cbar_tick_size = 10     # colorbar numbers

    errors = solution.solution_errors
    layout_c = errors.combined_field_layout_per1Amp[2] * 1000.
    sf_c = errors.sf_b_field_1A[:, 2] * 1000.
    loops_c = errors.combined_field_loops[2]
    target_c = errors.target_field_1A.b[2] * 1000.
    target_c = target_c / (np.max(np.abs(target_c)) * np.max(np.abs(sf_c)))
    pos = solution.target_field.coords
    ma_t = np.max(np.abs(target_c))

    panels = [
        (target_c, 'Target Bz', 'mT/A'),
        (sf_c, 'Bz by stream function', 'mT/A'),
        (layout_c, 'Layout Bz', 'mT/A'),
        (loops_c, 'Unconnected contour Bz', 'mT/A'),
        (abs(sf_c - target_c) / ma_t * 100, 'Relative error: stream function vs. target', '%'),
        (abs(layout_c - target_c) / ma_t * 100, 'Relative error: layout vs. target', '%'),
        (abs(layout_c - sf_c) / np.max(np.abs(sf_c)) * 100, 'Relative error: layout vs. stream function', '%'),
        (abs(loops_c - target_c) / ma_t * 100, 'Relative error: unconnected contours vs. target', '%'),
        (abs(loops_c - layout_c) / np.max(np.abs(layout_c)) * 100, 'Difference: unconnected contours vs. final layout', '%'),
    ]

    figures = [(panels[0:3], 1, 3, (16, 5.5), 'part1'),
               (panels[3:6], 1, 3, (16, 5.5), 'part2'),
               (panels[6:9], 1, 3, (16, 5.5), 'part3')]
    for group, nrows, ncols, size, tag in figures:
        fig = plt.figure(figsize=size)
        fig.suptitle(f'{title} - error metrics ({tag[-1]} of 3)', fontsize=suptitle_size)
        for k, (values, name, unit) in enumerate(group, start=1):
            ax = fig.add_subplot(nrows, ncols, k, projection='3d')
            sc = ax.scatter(pos[0], pos[1], pos[2], c=values, s=120, cmap='viridis')
            ax.set_title(name)
            ax.set_xlabel('x [m]')
            ax.set_ylabel('y [m]')
            ax.set_zlabel('z [m]')
            cb = fig.colorbar(sc, ax=ax, pad=0.12, shrink=0.7)
            cb.set_label(unit, fontsize=cbar_label_size)
            cb.ax.tick_params(labelsize=cbar_tick_size)
        fig.tight_layout(rect=[0, 0, 1, 0.95])
        if save_dir is not None:
            fig.savefig(f'{save_dir}/plot_errors_{title}_{tag}.png', dpi=dpi)


# --- Visualization ---
# Font sizes for all plots below. The colorbar sizes are set separately
# inside plot_error_metrics_split.
plt.rcParams.update({
    'font.size': 7,
    'axes.titlesize': 13,   # titles of the individual graphs
    'axes.labelsize': 9,    # x [m], y [m], z [m]
    'xtick.labelsize': 7,   # tick numbers on the 3D axes
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
})
plot_error_metrics_split(solution, which, save_dir=save_dir, dpi=150)
pcg_plt.plot_2D_contours_with_sf(coil_solutions, 0, f'{which} 2D', save_dir=save_dir, dpi=150)
pcg_plt.plot_3D_contours_with_sf(coil_solutions, 0, f'{which} 3D', save_dir=save_dir, dpi=150)

plt.show()
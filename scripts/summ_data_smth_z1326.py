import os
import numpy as np
import trimesh
import matplotlib.pyplot as plt
from pyCoilGen.helpers.persistence import load
import pyCoilGen.plotting as pcg_plt
from shapely.geometry import LineString
from shapely.strtree import STRtree

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


try:
    from OCP.TopoDS import TopoDS_Compound
    from OCP.BRep import BRep_Builder
except ImportError:
    from OCP.OCP import TopoDS, BRep
    TopoDS_Compound = TopoDS.TopoDS_Compound
    BRep_Builder = BRep.BRep_Builder


def export_step_curves(list_of_points_xyz, step_path, tol_mm=1e-6):
    """Like export_step_curve, but for a list of separate point arrays -
    each becomes its own B-spline edge, all combined into one compound and
    written to a single STEP file. Used for the Z-coil, whose path must be
    split into separate turn-segments (see fold/break logic below) rather
    than treated as one continuous curve."""
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for points_xyz in list_of_points_xyz:
        n = len(points_xyz)
        if n < 2:
            continue
        arr = _make_array(n)
        for idx, (x, y, z) in enumerate(points_xyz, start=1):
            arr.SetValue(idx, gp_Pnt(float(x), float(y), float(z)))
        interp = GeomAPI_Interpolate(arr, False, tol_mm)
        interp.Perform()
        if not interp.IsDone():
            continue
        curve = interp.Curve()
        edge = BRepBuilderAPI_MakeEdge(curve).Edge()
        builder.Add(compound, edge)
    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_StepModelType.STEPControl_AsIs)
    status = writer.Write(step_path)
    return "Done" in str(status) or "RetDone" in str(status)


def verify_crossing_clearance(flat_2d, z_flat_m, min_clearance_m=0.001, adjacent_skip=3):
    """Finds every genuine 2D crossing in the (s, z) flat projection and
    checks the REAL radial standoff (z_flat) at each one - reports how many
    crossings exist and how many have less than min_clearance_m of actual
    3D separation. Does NOT modify any geometry - this is a verification
    pass only, since altering the real standoff data without engineering
    justification would be worse than leaving a genuine problem visible.
    adjacent_skip widens the "same point" exclusion beyond immediate
    neighbours, since consecutive points on a dense path can be extremely
    close together without being a real crossing."""
    n = len(flat_2d)
    segs = [LineString([flat_2d[k], flat_2d[k + 1]]) for k in range(n - 1)]
    tree = STRtree(segs)
    found = {}
    for i, seg in enumerate(segs):
        for j in tree.query(seg):
            j = int(j)
            if abs(j - i) <= adjacent_skip:
                continue
            key = (min(i, j), max(i, j))
            if key in found:
                continue
            if segs[i].crosses(segs[j]):
                pt = segs[i].intersection(segs[j])
                found[key] = (pt.x, pt.y)

    under_clearance = []
    for (i, j), _xy in found.items():
        zi = z_flat_m[i]
        zj = z_flat_m[j]
        clearance = abs(zi - zj)
        if clearance < min_clearance_m:
            under_clearance.append((i, j, clearance))
    return len(found), under_clearance


#which = 'ygrad_coil_12887mm_hireg'
#which = 'xgrad_coil_116mm'
#which = 'zgrad_coil_13239mm_360len'
which = 'zgrad_coil_1326mm'
#which = 'ygrad_coil_1262mm'
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

# --- Unwrap the Z-coil into a flat, folded pattern -------------------------
# The Z-coil winds around the cylinder MANY times (double-helix, not a single
# ~180 deg lobe like X/Y), so a cumulative "unroll everything" unwrap would
# stretch the flat pattern out to many times the circumference - not what's
# wanted. Instead: fold every turn onto ONE revolution's width by using the
# raw wrapped angle (atan2 already wraps to (-pi,pi], so skip np.unwrap
# entirely), and split the path into separate segments wherever it crosses
# the +-180 deg seam - otherwise a single curve would draw a spurious line
# jumping straight across the whole plot at every turn.
x, y, z = wire_points_m[:, 0], wire_points_m[:, 1], wire_points_m[:, 2]

r = np.sqrt(x**2 + y**2)
R_nominal = np.median(r)

theta_raw = np.arctan2(y, x)          # wrapped, in (-pi, pi] - NOT unwrapped
s_local = R_nominal * theta_raw       # folded arc position, one-revolution wide
z_flat = r - R_nominal                # real radial standoff (same as x/y coils)

def moving_average(arr, window=5):
    """Centered moving average with edge padding - removes the single-point
    jitter/reversals present in the raw path, which otherwise make
    GeomAPI_Interpolate produce large erroneous loops (confirmed via
    diagnosis: ~44 of the path's local reversals were single-point blips,
    not genuine turn structure)."""
    if len(arr) < window:
        return arr.copy()
    pad = window // 2
    padded = np.pad(arr, (pad, pad), mode='edge')
    kernel = np.ones(window) / window
    return np.convolve(padded, kernel, mode='valid')


# Split into contiguous segments at BOTH the +-180deg wraparound seam AND
# every s=0 crossing. Wraparound-only splitting let a turn's tail bleed
# across into the neighbouring quadrant (since a turn can cross s=0 without
# ever reaching +-180deg), which showed up as curves visually merging/
# converging into each other - confirmed fixed by adding this second cut.
dtheta = np.diff(theta_raw)
wraparound_breaks = np.where(np.abs(dtheta) > np.pi)[0]
sign_s = np.sign(s_local)
zero_cross_breaks = np.where(np.diff(sign_s) != 0)[0]
all_breaks = np.unique(np.concatenate([wraparound_breaks, zero_cross_breaks]))
bounds = [0] + list(all_breaks + 1) + [len(theta_raw)]
segments_idx = [(bounds[i], bounds[i + 1] - 1) for i in range(len(bounds) - 1)]
segments_idx = [(a, b) for a, b in segments_idx if b - a >= 4]  # drop tiny slivers
print(f"\nZ-coil path split into {len(segments_idx)} turn-segments "
      f"(wraparound seam + s=0 crossings)")

# quadrant labels, for the review plot only (split by s=0 and by the coil's
# axial centre/reversal point) - matches the 1/2/3/4 layout you referenced
z_center = (z.max() + z.min()) / 2.0
quad = np.zeros(len(x), dtype=int)
quad[(s_local >= 0) & (z >= z_center)] = 2  # top-right
quad[(s_local < 0)  & (z >= z_center)] = 1  # top-left
quad[(s_local < 0)  & (z < z_center)]  = 3  # bottom-left
quad[(s_local >= 0) & (z < z_center)]  = 4  # bottom-right

# --- verify real 3D clearance at every genuine 2D crossing -----------------
# This coil is a double-helix: one winding pass, then a reversal winding
# back over roughly the same z-range the other way. That means (unlike X/Y)
# crossings between the two passes happen pervasively, not just at isolated
# jumpers - so the assumption that z_flat's real standoff is "probably
# enough" needs an actual check here, not just an assumption.
flat_2d_m = np.column_stack([s_local, z])  # metres, for the crossing check
n_crossings, under_clearance = verify_crossing_clearance(flat_2d_m, z_flat, min_clearance_m=0.001)
print(f"\nCrossing-clearance check: {n_crossings} genuine 2D crossings found")
if under_clearance:
    worst = min(c for _, _, c in under_clearance)
    print(f"  WARNING: {len(under_clearance)} of these have < 1mm real 3D separation "
          f"(worst case: {worst*1000:.4f} mm) - these are potential real collisions, "
          f"not just a flat-pattern artifact. Worth checking the actual pyCoilGen "
          f"solution (e.g. normal_shift_length) rather than patching the exported curve.")
else:
    print(f"  All {n_crossings} crossings have >= 1mm real separation - looks safe to manufacture.")

# --- review plot: check this BEFORE trusting the exported files ---
fig, ax = plt.subplots(figsize=(10, 6))
colors = {1: 'red', 2: 'blue', 3: 'green', 4: 'orange'}
for qi, c in colors.items():
    mask = quad == qi
    ax.plot(s_local[mask] * 1000, z[mask] * 1000, '.', color=c, markersize=1, label=f'{qi}')
ax.axvline(0, color='gray', linestyle='--')
ax.axhline(z_center * 1000, color='gray', linestyle='--')
ax.set_xlabel('folded arc position s (mm)')
ax.set_ylabel('height z (mm)')
ax.set_title(f'{project_name} - folded flat pattern, quadrant split')
ax.legend(markerscale=8)
preview_path = f"./{project_name}_flat_preview_{gradient_axis}.png"
try:
    plt.savefig(preview_path, dpi=130)
    print(f"Review plot saved to: {preview_path}  <-- check this looks right before using the STEP/TXT below")
except OSError as e:
    print(f"WARNING: could not save preview plot ({e}). Likely the PNG file is open "
          f"elsewhere - close it and rerun if you want this plot. Continuing on to the "
          f"STEP export below regardless, since that's the important output.")

# --- Each turn-segment becomes its own REAL curve (not a straight line) ---
# Confirmed working: smooth away the single-point jitter first (otherwise
# GeomAPI_Interpolate loops wildly trying to hit every noisy point exactly),
# then interpolate through the smoothed points. Because every segment is
# now cut at s=0 too, none of them can bleed into the neighbouring quadrant.
turn_curves_mm = []
segment_quadrant = []
for (i0, i1) in segments_idx:
    s_seg = moving_average(s_local[i0:i1 + 1], window=5)
    z_seg = moving_average(z[i0:i1 + 1], window=5)
    zf_seg = moving_average(z_flat[i0:i1 + 1], window=5)
    turn_curves_mm.append(np.column_stack([s_seg, z_seg, zf_seg]) * 1000.0)
    mid = (i0 + i1) // 2
    segment_quadrant.append(int(quad[mid]))

total_pts_before = len(x)
total_pts_after = sum(len(s) for s in turn_curves_mm)

flat_txt_path = f"./{project_name}_unwrapped_points_{gradient_axis}.txt"
with open(flat_txt_path, 'w') as f:
    f.write("arc_length_mm\theight_mm\tz_flat_mm\tsegment_id\tquadrant\n")
    for seg_id, (seg, q) in enumerate(zip(turn_curves_mm, segment_quadrant)):
        for row in seg:
            f.write(f"{row[0]:.6f}\t{row[1]:.6f}\t{row[2]:.6f}\t{seg_id}\t{q}\n")
print(f"Exported {total_pts_after} points (mm, smoothed, from {total_pts_before} raw, "
      f"{len(turn_curves_mm)} turn-curves) to {flat_txt_path}")
print(f"Radial offset range: {z_flat.min()*1000:.3f} mm to {z_flat.max()*1000:.3f} mm")

# --- STEP: 4 separate files, one per quadrant - each containing that
# quadrant's real turn-curves as independent, non-overlapping edges ---
for q in [1, 2, 3, 4]:
    segs_for_q = [seg for seg, sq in zip(turn_curves_mm, segment_quadrant) if sq == q]
    step_path_q = f"./{project_name}_unwrapped_{gradient_axis}_section{q}.step"
    step_ok_q = export_step_curves(segs_for_q, step_path_q)
    print(f"Section {q} STEP (mm, {len(segs_for_q)} curves): {step_path_q}  (write ok: {step_ok_q})")

# --- STEP: all 4 quadrants combined into ONE file -------------------------
# Same curves as the 4 section files above, just not split apart - every
# turn-curve across all quadrants as independent edges in a single compound.
combined_step_path = f"./{project_name}_unwrapped_{gradient_axis}_all.step"
combined_ok = export_step_curves(turn_curves_mm, combined_step_path)
print(f"Combined STEP (mm, all {len(turn_curves_mm)} curves, 4 quadrants): "
      f"{combined_step_path}  (write ok: {combined_ok})")

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
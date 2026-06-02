#!/usr/bin/env python3
"""
verify_reconstruction.py
========================
Reconstruct a 3D model from the captured 2D images and score it against the
original ("truth") model. Handles colorful objects (e.g. the LEGO tower):

  GEOMETRY  -> shape-from-silhouette voxel carving (visual hull) from the
               alpha channels, using the exact camera matrices in cameras.json.
  COLOR     -> the hull surface is meshed (marching cubes), then each vertex is
               colored by back-projecting it into the views where it is
               front-facing and inside the silhouette, averaging the captured
               RGB (a.k.a. view-dependent texture baked to per-vertex color).

METRICS (metrics.json)
  Geometry : IoU, volumetric precision/recall (completeness),
             Chamfer & Hausdorff distance (+ % of bounding diagonal),
             surface F-score @ tau.
  Color    : RMSE between reconstructed and true surface color, and the
             fraction of surface within a color tolerance ("color accuracy").

USAGE
  python verify_reconstruction.py --shots shots/ --out recon/ --res 128
  python verify_reconstruction.py --selftest --out selftest_out/   # no browser/GPU needed

INSTALL
  pip install numpy scipy scikit-image pillow
"""

import argparse
import json
import math
import os

import numpy as np

FOV_DEG, NEAR, FAR = 45.0, 0.1, 100.0


# ---------------------------------------------------------------------------
# matrix / camera helpers
# ---------------------------------------------------------------------------
def mat_from_elements(e):
    """Three.js stores matrices column-major; recover the 4x4 as M = reshape.T."""
    return np.array(e, float).reshape(4, 4).T


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])      # matches Three.js makeRotationY


def look_at_view(eye, target, up=(0, 1, 0)):
    eye = np.asarray(eye, float); target = np.asarray(target, float); up = np.asarray(up, float)
    z = eye - target; z /= np.linalg.norm(z)
    x = np.cross(up, z); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.column_stack([x, y, z])
    V = np.eye(4); V[:3, :3] = R.T; V[:3, 3] = -R.T @ eye
    return V


def perspective(aspect=1.0, fov_deg=FOV_DEG, near=NEAR, far=FAR):
    f = 1.0 / math.tan(math.radians(fov_deg) / 2)
    P = np.zeros((4, 4))
    P[0, 0] = f / aspect; P[1, 1] = f
    P[2, 2] = -(far + near) / (far - near); P[2, 3] = -2 * far * near / (far - near)
    P[3, 2] = -1.0
    return P


def eye_from_view(center, base_radius, az_deg, el_deg, zoom):
    phi = np.clip(np.radians(90 - el_deg), 0.02, np.pi - 0.02)
    theta = np.radians(az_deg)
    r = base_radius / zoom
    return np.asarray(center, float) + r * np.array(
        [np.sin(phi) * np.sin(theta), np.cos(phi), np.sin(phi) * np.cos(theta)])


def project(points, P, V):
    homog = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    clip = homog @ (P @ V).T
    w = clip[:, 3]
    with np.errstate(divide="ignore", invalid="ignore"):
        ndc = clip[:, :3] / w[:, None]
    return ndc, w


def to_pixels(ndc, W, H):
    px = (ndc[:, 0] * 0.5 + 0.5) * W
    py = (1 - (ndc[:, 1] * 0.5 + 0.5)) * H            # flip Y for image coords
    return np.floor(px).astype(int), np.floor(py).astype(int)


# ---------------------------------------------------------------------------
# carving (visual hull)
# ---------------------------------------------------------------------------
def consistent_with_view(points, P, V, mask):
    """A view can only DISPROVE a voxel: carve iff it projects onto a background
    pixel inside the frame. Out-of-frame = no information (keep)."""
    H, W = mask.shape
    ndc, w = project(points, P, V)
    ix, iy = to_pixels(ndc, W, H)
    in_bounds = (w > 0) & (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
    fg = np.zeros(len(points), bool)
    fg[in_bounds] = mask[iy[in_bounds], ix[in_bounds]]
    return ~(in_bounds & ~fg)


def make_grid(center, half, res):
    lin = np.linspace(-half, half, res)
    gx, gy, gz = np.meshgrid(lin, lin, lin, indexing="ij")
    centers = np.stack([gx + center[0], gy + center[1], gz + center[2]], -1).reshape(-1, 3)
    return centers, 2 * half / (res - 1), np.asarray(center) - half


def carve(centers, views, load_mask):
    occ = np.ones(len(centers), bool)
    for cam in views:
        occ &= consistent_with_view(centers, mat_from_elements(cam["projection"]),
                                    mat_from_elements(cam["view"]), load_mask(cam))
    return occ


def _carve_worker(payload):
    centers, _, _ = make_grid(payload["center"], payload["half"], payload["res"])
    load_mask, _ = loaders(payload["shots"])
    return carve(centers, payload["views"], load_mask)


def carve_parallel(views, center, half, res, shots, jobs):
    """Carve in parallel by splitting the VIEWS across processes (each carves all
    voxels for its views), then AND the partial hulls. Uses all the lab CPUs."""
    if jobs <= 1 or len(views) <= 1:
        centers, _, _ = make_grid(center, half, res)
        return carve(centers, views, loaders(shots)[0])
    import multiprocessing as mp
    n = min(jobs, len(views))
    payloads = [{"center": np.asarray(center), "half": half, "res": res,
                 "shots": shots, "views": views[i::n]} for i in range(n)]
    with mp.Pool(n) as pool:
        parts = pool.map(_carve_worker, payloads)
    occ = parts[0].copy()
    for p in parts[1:]:
        occ &= p
    return occ


# ---------------------------------------------------------------------------
# ground truth
# ---------------------------------------------------------------------------
def truth_occupancy(centers, model):
    """Returns (occupied_bool, colors_or_None) on the voxel grid."""
    Minv = np.linalg.inv(mat_from_elements(model["worldMatrix"]))
    local = (np.concatenate([centers, np.ones((len(centers), 1))], 1) @ Minv.T)[:, :3]

    if model["type"] == "legoTower":
        occ = np.zeros(len(centers), bool)
        colors = np.zeros((len(centers), 3))
        for b in model["bricks"]:
            c = np.array(b["center"]); h = np.array(b["half"])
            p = (rot_y(-b["rotY"]) @ (local - c).T).T          # into brick-local frame
            inside = np.all(np.abs(p) <= h, axis=1)
            occ |= inside
            colors[inside] = b["color"]
        return occ, colors

    if model["type"] == "torusKnot":                            # kept for back-compat
        from scipy.spatial import cKDTree
        u = np.linspace(0, 2 * np.pi * model.get("p", 2), 6000, endpoint=False)
        quOverP = (model.get("q", 3) / model.get("p", 2)) * u
        cs = np.cos(quOverP); r = model.get("radius", 1.0)
        curve = np.stack([r * (2 + cs) * 0.5 * np.cos(u),
                          r * (2 + cs) * 0.5 * np.sin(u),
                          r * np.sin(quOverP) * 0.5], 1)
        d, _ = cKDTree(curve).query(local)
        return d <= model.get("tube", 0.32), None

    raise ValueError(f"unknown model type: {model['type']}")


def _contains_worker(payload):
    import trimesh
    centers, _, _ = make_grid(payload["center"], payload["half"], payload["res"])
    pts = centers[payload["idx"]]
    mesh = trimesh.load(payload["mesh"], force="mesh")
    lo, hi = mesh.bounds
    inb = np.all((pts >= lo) & (pts <= hi), axis=1)
    out = np.zeros(len(pts), bool)
    if inb.any():
        out[inb] = mesh.contains(pts[inb])
    return payload["idx"], out


def truth_from_mesh(centers, mesh_path, center, half, res, jobs=1):
    """Voxelize an arbitrary mesh (.glb/.gltf/.obj/.stl/.ply) as ground truth, on
    the SAME grid as the reconstruction. Solid occupancy via inside-tests (split
    across CPUs when jobs>1); color from the mesh's vertex colors / material when
    available. Best on watertight meshes."""
    import trimesh
    occ = np.zeros(len(centers), bool)
    if jobs <= 1:
        mesh = trimesh.load(mesh_path, force="mesh")
        lo, hi = mesh.bounds
        inb = np.all((centers >= lo) & (centers <= hi), axis=1)
        if inb.any():
            occ[inb] = mesh.contains(centers[inb])
    else:
        import multiprocessing as mp
        chunks = np.array_split(np.arange(len(centers)), min(jobs, 48))
        payloads = [{"center": np.asarray(center), "half": half, "res": res,
                     "mesh": mesh_path, "idx": c} for c in chunks]
        with mp.Pool(min(jobs, len(payloads))) as pool:
            for idx, out in pool.map(_contains_worker, payloads):
                occ[idx] = out
    # color (serial; fast)
    colors = None
    try:
        mesh = trimesh.load(mesh_path, force="mesh")
        vis, vcol = mesh.visual, None
        if hasattr(vis, "vertex_colors") and len(np.asarray(vis.vertex_colors)) == len(mesh.vertices):
            vcol = np.asarray(vis.vertex_colors)[:, :3] / 255.0
        elif hasattr(vis, "to_color"):
            cc = np.asarray(vis.to_color().vertex_colors)
            if len(cc) == len(mesh.vertices):
                vcol = cc[:, :3] / 255.0
        if vcol is not None and occ.any():
            from scipy.spatial import cKDTree
            _, idx = cKDTree(mesh.vertices).query(centers[occ])
            colors = np.zeros((len(centers), 3)); colors[occ] = vcol[idx]
    except Exception:
        colors = None
    return occ, colors


# ---------------------------------------------------------------------------
# meshing + coloring
# ---------------------------------------------------------------------------
def vol_to_mesh(occ, voxel, origin, res):
    from skimage import measure
    grid = occ.reshape(res, res, res).astype(np.float32)
    if grid.min() == grid.max():
        return None, None, None
    v, f, n, _ = measure.marching_cubes(grid, level=0.5, spacing=(voxel,) * 3)
    return v + origin, f, n


def orient_outward(verts, normals, center):
    flip = np.sum(normals * (verts - center), axis=1) < 0
    normals[flip] = -normals[flip]
    return normals


def color_vertices(verts, normals, views, load_rgb, load_mask, eps):
    """Per-vertex color from its single most head-on foreground view (a
    best-view texture). Picking one sharp view avoids the muddy averaging that
    blends adjacent brick colors at seams."""
    best_w = np.zeros(len(verts))
    col = np.full((len(verts), 3), 0.6)
    for cam in views:
        P = mat_from_elements(cam["projection"]); V = mat_from_elements(cam["view"])
        cam_pos = np.linalg.inv(V)[:3, 3]
        rgb, mask = load_rgb(cam), load_mask(cam)
        H, W = mask.shape
        ndc, w = project(verts, P, V)
        ix, iy = to_pixels(ndc, W, H)
        inb = (w > 0) & (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
        fg = np.zeros(len(verts), bool); fg[inb] = mask[iy[inb], ix[inb]]
        vdir = cam_pos[None, :] - verts
        vdir /= np.linalg.norm(vdir, axis=1, keepdims=True) + 1e-9
        facing = np.sum(normals * vdir, axis=1)
        wgt = np.where(fg & (facing > 0), facing, 0.0)
        better = wgt > best_w
        samp = np.zeros((len(verts), 3)); samp[fg] = rgb[iy[fg], ix[fg]]
        col[better] = samp[better]; best_w[better] = wgt[better]
    return np.clip(col, 0, 1)


def write_ply(path, verts, faces, colors=None):
    with open(path, "w") as fh:
        fh.write("ply\nformat ascii 1.0\n")
        fh.write(f"element vertex {len(verts)}\n"
                 "property float x\nproperty float y\nproperty float z\n")
        if colors is not None:
            fh.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        fh.write(f"element face {len(faces)}\n"
                 "property list uchar int vertex_indices\nend_header\n")
        if colors is not None:
            c = (np.clip(colors, 0, 1) * 255).astype(int)
            for v, cc in zip(verts, c):
                fh.write(f"{v[0]:.5f} {v[1]:.5f} {v[2]:.5f} {cc[0]} {cc[1]} {cc[2]}\n")
        else:
            np.savetxt(fh, verts, fmt="%.5f")
        np.savetxt(fh, np.c_[np.full(len(faces), 3), faces], fmt="%d")


# ---------------------------------------------------------------------------
# self-test dataset (simulates the browser capture, in color)
# ---------------------------------------------------------------------------
def selftest_model():
    palette = [[0.77, 0.16, 0.10], [0.0, 0.33, 0.75], [0.95, 0.80, 0.21],
               [0.14, 0.47, 0.25], [1, 1, 1], [1.0, 0.54, 0.09], [0.62, 0.36, 0.70]]
    STUD, BRICK_H = 0.8, 0.95
    seed = [7]
    def rnd():
        seed[0] = (seed[0] * 1103515245 + 12345) & 0x7fffffff
        return seed[0] / 0x7fffffff
    bricks, y = [], 0.0
    for k in range(10):
        nx = 4 if rnd() > 0.5 else 2
        rotY = k * 0.5 + (rnd() - 0.5) * 0.3
        cx = math.cos(k * 0.6) * 0.5 + (rnd() - 0.5) * 0.35
        cz = math.sin(k * 0.6) * 0.5 + (rnd() - 0.5) * 0.35
        y += BRICK_H
        bricks.append({"center": [cx, y, cz], "half": [nx * STUD / 2, BRICK_H / 2, STUD],
                       "rotY": rotY, "color": palette[k % len(palette)]})
    # bounds from the 8 rotated corners of each brick
    pts = []
    for b in bricks:
        c, h = np.array(b["center"]), np.array(b["half"])
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    pts.append(c + rot_y(b["rotY"]) @ (h * np.array([sx, sy, sz])))
    pts = np.array(pts); center = (pts.min(0) + pts.max(0)) / 2
    boundR = 0.5 * np.linalg.norm(pts.max(0) - pts.min(0))
    return {"type": "legoTower", "center": center.tolist(), "halfSize": boundR * 1.05,
            "baseRadius": boundR / math.sin(math.radians(FOV_DEG) / 2) * 1.08,
            "bricks": bricks, "worldMatrix": list(np.eye(4).T.flatten())}


def render_truth_view(occ_pts, occ_col, P, V, W, H):
    """Z-buffered color splat of the truth voxels -> (rgb, alpha)."""
    from scipy import ndimage
    ndc, w = project(occ_pts, P, V)
    ix, iy = to_pixels(ndc, W, H)
    ok = (w > 0) & (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
    order = np.argsort(w[ok])[::-1]                      # far -> near (near drawn last, wins)
    ys, xs, cs = iy[ok][order], ix[ok][order], occ_col[ok][order]
    color = np.zeros((H, W, 3)); alpha = np.zeros((H, W), bool)
    color[ys, xs] = cs; alpha[ys, xs] = True
    filled = ndimage.binary_fill_holes(ndimage.binary_closing(alpha, iterations=2))
    idx = ndimage.distance_transform_edt(~alpha, return_distances=False, return_indices=True)
    color = np.where(filled[..., None], color[tuple(idx)], 0.0)
    return color, filled


def selftest_dataset(out_dir, n_az=16, elevations=(-15, 25), img=620, res=96):
    from PIL import Image
    model = selftest_model()
    centers, voxel, origin = make_grid(model["center"], model["halfSize"], res)
    occ, col = truth_occupancy(centers, model)
    occ_pts, occ_col = centers[occ], col[occ]

    views = []
    for i in range(n_az):
        az = 360.0 * i / n_az
        for el in elevations:
            eye = eye_from_view(model["center"], model["baseRadius"], az, el, 1.0)
            V, P = look_at_view(eye, model["center"]), perspective(1.0)
            rgb, alpha = render_truth_view(occ_pts, occ_col, P, V, img, img)
            rgba = np.zeros((img, img, 4), np.uint8)
            rgba[..., :3] = (rgb * 255).astype(np.uint8)
            rgba[..., 3] = alpha.astype(np.uint8) * 255
            fname = f"view_tt{i:03d}_el{int(el):+03d}.png"
            Image.fromarray(rgba, "RGBA").save(os.path.join(out_dir, fname))
            views.append({"az": az, "el": el, "file": fname,
                          "projection": list(P.T.flatten()), "view": list(V.T.flatten())})
    json.dump({"model": model, "views": views},
              open(os.path.join(out_dir, "cameras.json"), "w"), indent=2)


# ---------------------------------------------------------------------------
def loaders(shots_dir):
    from PIL import Image
    cache = {}
    def arr(cam):
        if cam["file"] not in cache:
            cache[cam["file"]] = np.asarray(Image.open(os.path.join(shots_dir, cam["file"]))
                                            .convert("RGBA"), float) / 255.0
        return cache[cam["file"]]
    return (lambda cam: arr(cam)[..., 3] > 0.5,          # mask loader
            lambda cam: arr(cam)[..., :3])               # rgb loader


def main():
    ap = argparse.ArgumentParser(description="Reconstruct (with color) and score vs truth.")
    ap.add_argument("--shots", help="folder with cameras.json + images")
    ap.add_argument("--selftest", action="store_true", help="fabricate data and run end-to-end")
    ap.add_argument("--out", default="recon")
    ap.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 38),
                    help="CPU processes for carving + mesh inside-tests (default: all cores, max 38)")
    ap.add_argument("--truth-mesh", help="score against this mesh file (.glb/.obj/.stl/.ply) "
                    "instead of the analytic model in cameras.json")
    ap.add_argument("--res", type=int, default=96, help="voxel grid resolution per axis")
    ap.add_argument("--tau", type=float, default=0.15, help="surface F-score threshold (world units)")
    ap.add_argument("--ctol", type=float, default=0.30, help="color-accuracy tolerance (0..1 RGB dist)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    shots = args.shots
    if args.selftest:
        shots = os.path.join(args.out, "synthetic_shots"); os.makedirs(shots, exist_ok=True)
        print("Generating synthetic colored capture (simulating the browser)...")
        selftest_dataset(shots, res=args.res)
    if not shots:
        ap.error("provide --shots DIR or --selftest")

    data = json.load(open(os.path.join(shots, "cameras.json")))
    model, views = data["model"], data["views"]
    print(f"Loaded {len(views)} views; model = {model['type']}")

    center = np.array(model.get("center")) if model.get("center") is not None else None
    half = model.get("halfSize")
    if args.truth_mesh and (center is None or half is None):
        import trimesh
        b = trimesh.load(args.truth_mesh, force="mesh").bounds
        center = (b[0] + b[1]) / 2; half = 0.5 * np.linalg.norm(b[1] - b[0]) * 1.05
    if center is None:
        center = mat_from_elements(model["worldMatrix"])[:3, 3]
    if half is None:
        half = 2.0
    centers, voxel, origin = make_grid(center, half, args.res)
    load_mask, load_rgb = loaders(shots)

    print(f"Carving visual hull from silhouettes ({args.jobs} workers)...")
    hull = carve_parallel(views, center, half, args.res, shots, args.jobs)
    if args.truth_mesh:
        print(f"Voxelizing ground-truth mesh: {args.truth_mesh}")
        truth, truth_col = truth_from_mesh(centers, args.truth_mesh, center, half, args.res, args.jobs)
    else:
        print("Building analytic ground truth...")
        truth, truth_col = truth_occupancy(centers, model)

    # ---- geometry metrics ----
    inter, uni = int(np.sum(hull & truth)), int(np.sum(hull | truth))
    nh, nt = int(hull.sum()), int(truth.sum())
    m = {"voxels_reconstructed": nh, "voxels_truth": nt,
         "IoU": inter / uni if uni else 0.0,
         "precision_volumetric": inter / nh if nh else 0.0,
         "recall_completeness_volumetric": inter / nt if nt else 0.0,
         "grid_resolution": args.res, "voxel_size": voxel, "n_views": len(views)}

    print("Meshing + coloring reconstruction...")
    vh, fh, nh_norm = vol_to_mesh(hull, voxel, origin, args.res)
    vt, ft, nt_norm = vol_to_mesh(truth, voxel, origin, args.res)

    hull_colors = truth_colors = None
    if vh is not None:
        nh_norm = orient_outward(vh, nh_norm, center)
        hull_colors = color_vertices(vh, nh_norm, views, load_rgb, load_mask, voxel)
        write_ply(os.path.join(args.out, "reconstruction.ply"), vh, fh, hull_colors)
    if vt is not None:
        from scipy.spatial import cKDTree
        if truth_col is not None:
            _, ti = cKDTree(centers[truth]).query(vt)
            truth_colors = truth_col[truth][ti]
        write_ply(os.path.join(args.out, "truth.ply"), vt, ft, truth_colors)

    # ---- surface metrics (geometry + color) ----
    if vh is not None and vt is not None:
        from scipy.spatial import cKDTree
        treeT, treeH = cKDTree(vt), cKDTree(vh)
        dH, iH = treeT.query(vh)
        dT, _ = treeH.query(vt)
        diag = np.linalg.norm(vt.max(0) - vt.min(0))
        prec, rec = float(np.mean(dH < args.tau)), float(np.mean(dT < args.tau))
        m.update({
            "chamfer_distance": float(dH.mean() + dT.mean()),
            "chamfer_pct_of_diagonal": float((dH.mean() + dT.mean()) / diag * 100),
            "hausdorff_distance": float(max(dH.max(), dT.max())),
            "surface_precision_at_tau": prec, "surface_recall_at_tau": rec,
            "f_score_at_tau": (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0,
            "tau": args.tau,
        })
        if hull_colors is not None and truth_colors is not None:
            near = dH < args.tau
            if near.any():
                err = np.linalg.norm(hull_colors[near] - truth_colors[iH[near]], axis=1)
                m["color_rmse"] = float(np.sqrt(np.mean(err ** 2)))
                m["color_accuracy"] = float(np.mean(err < args.ctol))
                m["color_tolerance"] = args.ctol

    json.dump(m, open(os.path.join(args.out, "metrics.json"), "w"), indent=2)
    print("\n================ RECONSTRUCTION METRICS ================")
    for k, v in m.items():
        print(f"  {k:34s} {v:.4f}" if isinstance(v, float) else f"  {k:34s} {v}")
    print("========================================================")
    print(f"\nWrote metrics.json + colored reconstruction.ply / truth.ply to '{args.out}/'")


if __name__ == "__main__":
    main()

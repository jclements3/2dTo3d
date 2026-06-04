#!/usr/bin/env python3
"""
reconstruct_sketchfab.py -- visual-hull reconstruction of a Sketchfab model from
the transparent turntable captured by capture_sketchfab.py (--fixed-dist).

Builds the projection/view matrices from the recorded eye/target/fov, then reuses
the repo's carve -> marching-cubes -> best-view-color pipeline
(verify_reconstruction.py) to produce a COLORED high-resolution mesh.  No ground
truth is needed (this is reconstruct-only), so no metrics are computed.

    python reconstruct_sketchfab.py --shots recon_shots --out recon --res 256 --jobs 36
"""
import argparse, json, os, math
import numpy as np
import verify_reconstruction as vr


# --- strict visual-hull carve --------------------------------------------------
# The repo's default KEEPS voxels that project out of frame (so framed/zoomed views
# mix safely).  Here every view fully contains the model, so we use the stricter
# rule: a voxel survives only if it lands on FOREGROUND and IN-FRAME in *every*
# view.  Out-of-frame = carve.  This removes the grid-corner bloat.
def _clean_mask_loader(shots):
    """LEAN mask loader: reads ONLY the alpha channel as a compact bool array
    (not a float64 RGBA image -> ~25x less memory) and keeps the largest
    connected component (drops the Sketchfab watermark).  Bounded cache."""
    from scipy import ndimage
    from PIL import Image
    cache = {}
    def load(cam):
        f = cam["file"]
        if f not in cache:
            a = np.asarray(Image.open(os.path.join(shots, f)).split()[-1])  # alpha, uint8
            m = a > 127
            lbl, n = ndimage.label(m)
            if n > 1:
                sizes = ndimage.sum(m, lbl, range(1, n + 1))
                m = lbl == (1 + int(np.argmax(sizes)))
            cache[f] = m
        return cache[f]
    return load


def _vote_worker(payload):
    centers, _, _ = vr.make_grid(payload["center"], payload["half"], payload["res"])
    load_mask = _clean_mask_loader(payload["shots"])
    votes = np.zeros(len(centers), np.int32)      # foreground & in-frame count
    for cam in payload["views"]:
        P = vr.mat_from_elements(cam["projection"]); V = vr.mat_from_elements(cam["view"])
        mask = load_mask(cam); H, W = mask.shape
        ndc, w = vr.project(centers, P, V); ix, iy = vr.to_pixels(ndc, W, H)
        inb = (w > 0) & (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
        fg = np.zeros(len(centers), bool); fg[inb] = mask[iy[inb], ix[inb]]
        votes += fg
    return votes


def vote_carve_parallel(views, center, half, res, shots, jobs, frac):
    """Keep voxels seen as foreground in >= frac of views (frac=1.0 -> strict hull;
    slightly below 1.0 tolerates pose noise / minor self-occlusion)."""
    import multiprocessing as mp
    n = max(1, min(jobs, len(views)))
    if n == 1:
        votes = _vote_worker({"center": center, "half": half, "res": res,
                              "shots": shots, "views": views})
    else:
        payloads = [{"center": np.asarray(center), "half": half, "res": res,
                     "shots": shots, "views": views[i::n]} for i in range(n)]
        with mp.Pool(n) as pool:
            votes = sum(pool.map(_vote_worker, payloads))
    need = math.ceil(frac * len(views) - 1e-9)
    return votes >= need


def build_views(data):
    """Attach column-major projection/view (the format mat_from_elements expects)
    to each captured view, from its eye/target/up/fov."""
    views = []
    for c in data["views"]:
        W, H = c["width"], c["height"]
        P = vr.perspective(aspect=W / H, fov_deg=c["fov_deg"], near=0.01, far=1e5)
        V = vr.look_at_view(c["eye"], c["target"], c.get("up", (0, 1, 0)))
        views.append({"file": c["file"],
                      "projection": list(P.T.flatten()),   # reshape(4,4).T -> P
                      "view":       list(V.T.flatten())})
    return views


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default="recon_shots")
    ap.add_argument("--out", default="recon")
    ap.add_argument("--res", type=int, default=256, help="voxel grid resolution per axis")
    ap.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 38))
    ap.add_argument("--pad", type=float, default=1.12, help="grid half = measured_extent * pad")
    ap.add_argument("--half", type=float, default=0.0, help="override grid half-extent (world units)")
    ap.add_argument("--vote", type=float, default=1.0,
                    help="keep voxels foreground in >= this fraction of views (1.0 = strict)")
    ap.add_argument("--only-el", default="", help="comma list of elevations to use (e.g. -20,0,20)")
    ap.add_argument("--target-h", type=float, default=0.0, help="scale mesh to this height (mm)")
    ap.add_argument("--target-w", type=float, default=0.0, help="left-right width (mm)")
    ap.add_argument("--target-exw", type=float, default=0.0, help="front-back extreme width (mm)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    data = json.load(open(os.path.join(args.shots, "cameras.json")))
    if args.only_el:
        keep = set(float(x) for x in args.only_el.split(","))
        data["views"] = [c for c in data["views"] if float(c["el"]) in keep]
        print(f"filtered to elevations {sorted(keep)}: {len(data['views'])} views")
    # drop stale-read / outlier poses: the read-back direction must roughly match
    # the intended (az,el) direction, else the camera reading was bad.
    def intended_dir(c):
        ar = math.radians(c["az"]); er = math.radians(c["el"])
        return np.array([math.cos(er)*math.sin(ar), math.sin(er), math.cos(er)*math.cos(ar)])
    good = []
    for c in data["views"]:
        e = np.array(c["eye"], float); t = np.array(c["target"], float)
        d = e - t; d = d/ (np.linalg.norm(d)+1e-9)
        if float(d @ intended_dir(c)) >= 0.92:
            good.append(c)
    print(f"pose-sanity: kept {len(good)}/{len(data['views'])} views")
    data["views"] = good
    views = build_views(data)
    center = np.asarray(data["center"], float)
    # Measure the model's TRUE half-extent from the silhouettes (the Sketchfab
    # model_radius is the wrong scale).  A silhouette of pixel height h in an H-px
    # frame at distance d, fov f, spans world height (h/H)*2*d*tan(f/2); half of the
    # largest such span (over all views) bounds the model.  + safety margin.
    if args.half > 0:
        half = args.half
    else:
        load_mask = _clean_mask_loader(args.shots)
        ext = 0.0
        for c in data["views"]:
            m = load_mask(c)
            ys, xs = np.where(m)
            if not len(xs):
                continue
            d = c["dist"]; t = math.tan(math.radians(c["fov_deg"]) / 2)
            ev = (ys.max() - ys.min()) / m.shape[0] * d * t      # half-height (world)
            eh = (xs.max() - xs.min()) / m.shape[1] * d * t * (m.shape[1] / m.shape[0])
            ext = max(ext, ev, eh)
        half = ext * args.pad
    print(f"{len(views)} views | center={center} | half={half:.3f} (measured) "
          f"| res={args.res} | jobs={args.jobs}", flush=True)

    print(f"carving visual hull (vote>={args.vote}, out-of-frame = carve) ...", flush=True)
    occ = vote_carve_parallel(views, center, half, args.res, args.shots, args.jobs, args.vote)
    print(f"  occupied voxels: {int(occ.sum())} / {len(occ)} ({100*occ.mean():.2f}%)", flush=True)

    _, voxel, origin = vr.make_grid(center, half, args.res)
    verts, faces, normals = vr.vol_to_mesh(occ, voxel, origin, args.res)
    if verts is None:
        raise SystemExit("empty hull -- check poses/masks")
    normals = vr.orient_outward(verts, normals, center)
    print(f"  mesh: {len(verts)} verts, {len(faces)} faces", flush=True)

    # scale to the target real-world dimensions (mm).  Y(up)->height; the larger
    # horizontal extent -> ExW (front-back); the smaller -> width (left-right).
    if args.target_h > 0:
        verts = verts - verts.mean(0)
        ext = verts.max(0) - verts.min(0)              # [x,y,z] extents
        horiz = [0, 2] if ext[0] >= ext[2] else [2, 0]  # [bigger, smaller] horizontal axis idx
        s = np.ones(3)
        s[1]        = args.target_h   / ext[1]
        s[horiz[0]] = (args.target_exw or args.target_h) / ext[horiz[0]]
        s[horiz[1]] = (args.target_w   or args.target_h) / ext[horiz[1]]
        verts = verts * s
        print(f"  scaled to mm: extents now {np.round(verts.max(0)-verts.min(0),1)} "
              f"(target H={args.target_h} ExW={args.target_exw} W={args.target_w})", flush=True)

    print("coloring (best-view back-projection) ...", flush=True)
    load_mask = _clean_mask_loader(args.shots); _, load_rgb = vr.loaders(args.shots)
    colors = vr.color_vertices(verts, normals, views, load_rgb, load_mask, eps=1e-6)

    ply = os.path.join(args.out, "harp_reconstruction.ply")
    vr.write_ply(ply, verts, faces, colors)
    print(f"  wrote {ply}", flush=True)

    # also export OBJ + GLB (vertex colors) for general 3D tools
    try:
        import trimesh
        m = trimesh.Trimesh(vertices=verts, faces=faces,
                            vertex_colors=(np.clip(colors, 0, 1) * 255).astype(np.uint8),
                            process=False)
        m.export(os.path.join(args.out, "harp_reconstruction.glb"))
        m.export(os.path.join(args.out, "harp_reconstruction.obj"))
        print(f"  wrote harp_reconstruction.glb / .obj  (watertight={m.is_watertight}, "
              f"bounds={np.round(m.extents,3)})", flush=True)
    except Exception as e:
        print(f"  (trimesh export skipped: {e})", flush=True)

    json.dump({"n_views": len(views), "res": args.res,
               "occupied_voxels": int(occ.sum()), "verts": len(verts), "faces": len(faces)},
              open(os.path.join(args.out, "recon_info.json"), "w"), indent=1)


if __name__ == "__main__":
    main()

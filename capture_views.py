#!/usr/bin/env python3
"""
capture_views.py - capture views of a 3D model for documentation / reconstruction.

TWO MODES
  --url   <URL>    capture a LIVE WebGL page (the served viewer). Drives the
                   page's window.viewerAPI, saves transparent RGBA PNGs (alpha =
                   silhouette, RGB = color) and cameras.json (exact matrices).
  --model <FILE>   render a local mesh offline with PyVista (.glb/.obj/.stl/...).

LAB DEFAULTS (GPU Ubuntu box): hardware GPU rendering, high-res PORTRAIT frames.
If Chromium misbehaves on the GPU box, switch engine with `--browser firefox`
(or use a system build with `--channel chromium`).

INSTALL
  url mode :  pip install playwright && playwright install chromium
              # firefox fallback:  playwright install firefox
  model mode: pip install pyvista

EXAMPLES
  # lab GPU box: high-res portrait dense turntable from a Web3D URL
  python capture_views.py --url http://localhost:8000/3d-viewer.html --out shots/ \
      --turntable 48 --elev -20,10,40

  # if chromium has GPU issues, use firefox instead:
  python capture_views.py --url <URL> --out shots/ --turntable 48 --browser firefox
"""

import argparse
import json
import math
import os
import sys

PERSPECTIVES = {"front": (0, 0), "rear": (180, 0), "right": (90, 0), "left": (270, 0),
                "top": (0, 90), "bottom": (0, -90), "iso": (45, 35)}
ZOOMS = [1.0, 1.5, 2.2]
VIEWS = [{"label": name, "az": az, "el": el, "zoom": z}
         for name, (az, el) in PERSPECTIVES.items() for z in ZOOMS]


def build_turntable(n_az, elevations, zoom=1.0):
    views = []
    for i in range(n_az):
        az = round(360.0 * i / n_az, 2)
        for el in elevations:
            views.append({"label": f"tt{i:03d}e{int(el):+03d}", "az": az, "el": el, "zoom": zoom})
    return views


def view_tag(v):
    az = int(round(v["az"])) % 360
    el = int(round(v["el"]))
    el_s = f"el{el:02d}" if el >= 0 else f"elm{abs(el):02d}"
    return f"{v['label']}_az{az:03d}_{el_s}_z{int(round(v['zoom']*100)):03d}"


# ===========================================================================
# URL MODE (headless browser -> live WebGL page)
# ===========================================================================
def launch_browser(pw, browser, gpu, channel):
    """Launch the chosen engine. GPU on = hardware rendering; off = SwiftShader
    software (works anywhere but slower). Firefox/WebKit are fallbacks for boxes
    where headless Chromium has GPU trouble."""
    if browser == "chromium":
        if gpu:                                   # use the real GPU (lab default)
            args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-gpu-blocklist",
                    "--use-gl=egl", "--enable-gpu-rasterization"]
        else:                                     # portable software fallback
            args = ["--no-sandbox", "--disable-dev-shm-usage",
                    "--use-gl=angle", "--use-angle=swiftshader"]
        kw = {"headless": True, "args": args}
        if channel:
            kw["channel"] = channel               # e.g. "chromium" / "chrome" (system build)
        return pw.chromium.launch(**kw)
    if browser == "firefox":
        return pw.firefox.launch(headless=True, firefox_user_prefs={
            "webgl.force-enabled": True, "webgl.disabled": False, "gfx.webrender.all": True})
    return pw.webkit.launch(headless=True)


def _capture_slice(payload):
    """Capture one slice of views with its own browser (also usable in a Pool)."""
    from playwright.sync_api import sync_playwright
    W, H = payload["size"]
    cams, model_info = [], None
    with sync_playwright() as pw:
        b = launch_browser(pw, payload["browser"], payload["gpu"], payload["channel"])
        page = b.new_page(viewport={"width": W, "height": H},
                          device_scale_factor=payload["scale"])
        page.goto(payload["url"], wait_until="load")
        page.wait_for_function("window.viewerAPI && window.viewerAPI.ready", timeout=30000)
        page.evaluate("window.viewerAPI.setCaptureMode(true)")
        if payload["want_model"]:
            model_info = page.evaluate("window.viewerAPI.getModelInfo()")
        for v in payload["views"]:
            page.evaluate("([a,e,z]) => window.viewerAPI.setView(a,e,z)", [v["az"], v["el"], v["zoom"]])
            page.wait_for_timeout(payload["wait"])
            mats = page.evaluate("window.viewerAPI.getMatrices()")
            fname = f"view_{view_tag(v)}.png"
            page.screenshot(path=os.path.join(payload["out"], fname), omit_background=True)
            cams.append({**v, "file": fname, "projection": mats["projection"], "view": mats["view"]})
        b.close()
    return cams, model_info


def capture_from_url(url, out_dir, size, scale, wait_ms, views, browser, gpu, channel, jobs):
    base = dict(url=url, out=out_dir, size=size, scale=scale, wait=wait_ms,
                browser=browser, gpu=gpu, channel=channel)
    if jobs <= 1 or len(views) <= 1:
        cams, model_info = _capture_slice({**base, "views": views, "want_model": True})
    else:
        import multiprocessing as mp
        n = min(jobs, len(views))
        payloads = [{**base, "views": views[i::n], "want_model": (i == 0)} for i in range(n)]
        cams, model_info = [], None
        with mp.Pool(n) as pool:
            for c, mi in pool.map(_capture_slice, payloads):
                cams += c
                model_info = model_info or mi
    print(f"  captured {len(cams)} views with {browser} (gpu={gpu})")
    with open(os.path.join(out_dir, "cameras.json"), "w") as f:
        json.dump({"model": model_info, "views": cams}, f, indent=2)
    print("  saved cameras.json (ground-truth poses + model definition)")
    return [({k: c[k] for k in ("label", "az", "el", "zoom")}, c["file"]) for c in cams]


# ===========================================================================
# MODEL MODE (offline PyVista render of a local mesh file)
# ===========================================================================
def up_vector(axis):
    return {"x": (1.0, 0, 0), "y": (0, 1.0, 0), "z": (0, 0, 1.0)}[axis]


def orbit_position(focal, distance, az_deg, el_deg, up):
    import numpy as np
    up = np.array(up, float); up /= np.linalg.norm(up)
    ref = np.array([1.0, 0, 0]) if abs(up[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(up, ref); e1 /= np.linalg.norm(e1)
    e2 = np.cross(up, e1)
    az, el = math.radians(az_deg), math.radians(el_deg)
    direction = math.cos(el) * (math.cos(az) * e1 + math.sin(az) * e2) + math.sin(el) * up
    return focal + distance * direction, (up if abs(el_deg) < 88 else -(math.cos(az) * e1 + math.sin(az) * e2))


def capture_from_model(model_path, out_dir, size, up_axis, bg, transparent, color, views):
    import numpy as np
    import pyvista as pv
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        try:
            pv.start_xvfb()
        except Exception:
            print("Note: headless with no xvfb - try `xvfb-run python ...`", file=sys.stderr)
    plotter = pv.Plotter(off_screen=True, window_size=list(size))
    if not transparent:
        plotter.set_background(bg)
    try:
        plotter.enable_anti_aliasing("ssaa")
    except Exception:
        pass
    ext = os.path.splitext(model_path)[1].lower()
    if ext in (".glb", ".gltf"):
        plotter.import_gltf(model_path)
    else:
        plotter.add_mesh(pv.read(model_path), color=color, smooth_shading=True,
                         specular=0.3, specular_power=15)
    xmin, xmax, ymin, ymax, zmin, zmax = plotter.bounds
    focal = np.array([(xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2])
    radius = max(0.5 * math.sqrt((xmax-xmin)**2 + (ymax-ymin)**2 + (zmax-zmin)**2), 1e-6)
    up = up_vector(up_axis)
    records = []
    for v in views:
        pos, vup = orbit_position(focal, radius * 3.0, v["az"], v["el"], up)
        plotter.camera_position = [tuple(pos), tuple(focal), tuple(vup)]
        plotter.reset_camera(); plotter.camera.zoom(v["zoom"]); plotter.render()
        fname = f"view_{view_tag(v)}.png"
        plotter.screenshot(os.path.join(out_dir, fname), transparent_background=transparent)
        print(f"  saved {fname}")
        records.append((v, fname))
    plotter.close()
    return records


# ===========================================================================
def write_snippets(out_dir, records):
    md_blocks, tex = [], []
    for v, fname in records:
        cap = (f"{v['label'].capitalize()} - azimuth {v['az']}deg, "
               f"elevation {v['el']}deg, zoom {v['zoom']:g}x")
        md_blocks.append(f"![{cap}]({fname})\n\n*{cap}*")
        tex += [r"\begin{figure}[htbp]", r"  \centering",
                f"  \\includegraphics[width=0.6\\textwidth]{{{fname}}}",
                f"  \\caption{{{v['label'].capitalize()} --- azimuth ${v['az']}^\\circ$, "
                f"elevation ${v['el']}^\\circ$, zoom ${v['zoom']:g}\\times$.}}",
                f"  \\label{{fig:{view_tag(v).replace('_','-')}}}", r"\end{figure}", ""]
    with open(os.path.join(out_dir, "captures.md"), "w") as f:
        f.write("\n\n".join(md_blocks) + "\n")
    with open(os.path.join(out_dir, "captures.tex"), "w") as f:
        f.write("\n".join(tex))


def main():
    ap = argparse.ArgumentParser(description="Capture standard documentation / reconstruction views.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="URL of the live WebGL viewer to capture")
    src.add_argument("--model", help="path to a local mesh file (offline render)")
    ap.add_argument("--out", default="shots", help="output directory")
    # high-res PORTRAIT by default (matches a tall model); aspect is handled automatically
    ap.add_argument("--size", nargs=2, type=int, default=[1080, 1620], metavar=("W", "H"),
                    help="image size in CSS px, portrait by default (default: 1080 1620)")
    # view set
    ap.add_argument("--turntable", type=int, metavar="N",
                    help="dense turntable of N azimuths (for reconstruction)")
    ap.add_argument("--elev", default="-20,10,40", help="turntable elevations (default: -20,10,40)")
    ap.add_argument("--tzoom", type=float, default=1.0, help="zoom for turntable views")
    # url mode / browser
    ap.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium",
                    help="rendering engine (use firefox if chromium has GPU issues)")
    ap.add_argument("--gpu", action=argparse.BooleanOptionalAction, default=True,
                    help="use the GPU for hardware rendering (default: on; --no-gpu for software)")
    ap.add_argument("--channel", default=None,
                    help="chromium channel/system build, e.g. 'chromium' or 'chrome'")
    ap.add_argument("--scale", type=int, default=2, help="device pixel ratio (default: 2 = hi-res)")
    ap.add_argument("--wait", type=int, default=180, help="ms to settle per view")
    ap.add_argument("--jobs", type=int, default=1,
                    help="parallel capture browsers (GPU is shared; 4-6 is plenty)")
    # model mode
    ap.add_argument("--up", default="z", choices=["x", "y", "z"], help="model up-axis")
    ap.add_argument("--bg", default="white", help="background (model mode)")
    ap.add_argument("--transparent", action="store_true", help="transparent bg (model mode)")
    ap.add_argument("--color", default="#c9ccd1", help="surface color (model mode)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    if args.turntable:
        elevations = [float(x) for x in args.elev.split(",")]
        views = build_turntable(args.turntable, elevations, args.tzoom)
        print(f"Turntable: {args.turntable} azimuths x {len(elevations)} elevations = {len(views)} views")
    else:
        views = VIEWS

    if args.url:
        print(f"Capturing live viewer: {args.url}  ({args.size[0]}x{args.size[1]} @ {args.scale}x)")
        records = capture_from_url(args.url, args.out, args.size, args.scale, args.wait, views,
                                   args.browser, args.gpu, args.channel, args.jobs)
    else:
        if not os.path.isfile(args.model):
            sys.exit(f"Model not found: {args.model}")
        print(f"Rendering model: {args.model}")
        records = capture_from_model(args.model, args.out, args.size, args.up,
                                     args.bg, args.transparent, args.color, views)

    write_snippets(args.out, records)
    print(f"\nDone - {len(records)} images + captures.md/.tex in '{args.out}/'")


if __name__ == "__main__":
    main()

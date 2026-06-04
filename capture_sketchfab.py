#!/usr/bin/env python3
"""
capture_sketchfab.py -- drive a Sketchfab embed via its Viewer API and grab
near-orthographic, transparent-background views for ANGLE/PROPORTION measurement
(not mesh reconstruction).

We place the camera ourselves (eye/target/up known exactly) and use a small FOV
+ large distance to approximate an orthographic projection, so angles measured in
the image are not distorted by perspective. Transparent background -> the alpha
channel is the exact silhouette.

Usage:
    python capture_sketchfab.py --uid 6e31140ec5dc4d7aa2e9c1286f2b4d25 --out model_shots/
"""
import argparse
import json
import math
import os
import sys
import time

VIEWER_JS = "https://static.sketchfab.com/api/sketchfab-viewer-1.12.1.js"

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;background:transparent;}}
#api-frame{{display:block;border:0;background:transparent;}}</style>
<script src="{viewer_js}"></script></head>
<body>
<iframe id="api-frame" width="{w}" height="{h}" allow="autoplay; fullscreen; xr-spatial-tracking"></iframe>
<script>
window.__ready=false; window.__api=null; window.__center=null; window.__r0=null; window.__fov0=null;
var iframe=document.getElementById('api-frame');
var client=new Sketchfab('1.12.1', iframe);
client.init('{uid}', {{
  success:function(api){{
    api.start();
    api.addEventListener('viewerready', function(){{
      window.__api=api;
      api.setBackground({{transparent:true}}, function(){{
       // kill vignette/bloom so transparent alpha is a clean silhouette
       api.setPostProcessing({{enable:false}}, function(){{
        api.getCameraLookAt(function(e,c){{
          var p=c.position, t=c.target;
          window.__center=t;
          window.__r0=Math.sqrt((p[0]-t[0])**2+(p[1]-t[1])**2+(p[2]-t[2])**2);
          api.getFov(function(e2,f){{ window.__fov0=f; window.__ready=true; }});
        }});
       }});
      }});
    }});
  }},
  error:function(){{ window.__error=true; }},
  autostart:1, preload:1, ui_controls:0, ui_infos:0, ui_inspector:0,
  ui_watermark:0, ui_stop:0, ui_help:0, ui_settings:0, ui_vr:0, ui_ar:0,
  ui_fullscreen:0, ui_annotations:0, ui_loading:0, ui_hint:0, ui_general:0,
  ui_theme:'dark', transparent:1, dnt:1, scrollwheel:0, autospin:0, max_texture_size:2048
}});
// Called by Python. Returns a promise (Playwright awaits it).
// Set the camera, let it settle, then READ BACK the pose Sketchfab actually
// used (it does not honor elevated positions exactly) so reconstruction uses
// true poses, not requested ones.
window.shoot=function(eye, target, fovDeg){{
  return new Promise(function(resolve){{
    var api=window.__api;
    api.setFov(fovDeg, function(){{
      api.setCameraLookAt(eye, target, 0, function(){{
        setTimeout(function(){{
          api.getCameraLookAt(function(e,c){{
            api.getFov(function(e2,f){{
              resolve({{position:c.position, target:c.target, fov:f}});
            }});
          }});
        }}, {settle});
      }});
    }});
  }});
}};
</script></body></html>"""


def look_at(eye, target, up=(0, 1, 0)):
    """Right-handed view matrix (row-major 4x4 as nested lists), GL convention."""
    e = [float(x) for x in eye]; t = [float(x) for x in target]
    f = [t[i] - e[i] for i in range(3)]
    fn = math.sqrt(sum(c * c for c in f)); f = [c / fn for c in f]
    s = [f[1]*up[2]-f[2]*up[1], f[2]*up[0]-f[0]*up[2], f[0]*up[1]-f[1]*up[0]]
    sn = math.sqrt(sum(c * c for c in s)); s = [c / sn for c in s]
    u = [s[1]*f[2]-s[2]*f[1], s[2]*f[0]-s[0]*f[2], s[0]*f[1]-s[1]*f[0]]
    return [
        [ s[0],  s[1],  s[2], -(s[0]*e[0]+s[1]*e[1]+s[2]*e[2])],
        [ u[0],  u[1],  u[2], -(u[0]*e[0]+u[1]*e[1]+u[2]*e[2])],
        [-f[0], -f[1], -f[2],  (f[0]*e[0]+f[1]*e[1]+f[2]*e[2])],
        [0, 0, 0, 1],
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uid", required=True)
    ap.add_argument("--out", default="model_shots")
    ap.add_argument("--w", type=int, default=1100)
    ap.add_argument("--h", type=int, default=1500)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--fov", type=float, default=5.0, help="capture FOV deg (small=near-ortho)")
    ap.add_argument("--az", default="0:360:15", help="start:stop:step degrees")
    ap.add_argument("--elev", default="0,20", help="comma list of elevations deg")
    ap.add_argument("--settle", type=int, default=450, help="ms to settle per view")
    ap.add_argument("--fixed-dist", action="store_true",
                    help="skip per-view auto-frame; use one fixed distance (for reconstruction)")
    ap.add_argument("--margin", type=float, default=1.45,
                    help="framing margin for --fixed-dist (model fills 1/margin of frame)")
    ap.add_argument("--abs-dist", type=float, default=0.0,
                    help="absolute camera distance (overrides --fixed-dist framing math)")
    ap.add_argument("--no-gpu", action="store_true")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright
    import http.server, socketserver, threading

    os.makedirs(args.out, exist_ok=True)
    a0, a1, da = (float(x) for x in args.az.split(":"))
    azs = [a0 + i * da for i in range(int(round((a1 - a0) / da)))]
    els = [float(x) for x in args.elev.split(",")]

    html = PAGE.format(viewer_js=VIEWER_JS, uid=args.uid, w=args.w, h=args.h,
                       settle=args.settle).encode()

    # Sketchfab embeds reject a null origin (about:blank / data:), so serve the
    # page over real http://localhost and navigate Playwright there.
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        def log_message(self, *a):
            pass
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    page_url = f"http://localhost:{port}/index.html"
    print(f"serving capture page at {page_url}", flush=True)

    # Real hardware WebGL (Sketchfab refuses software/SwiftShader) requires
    # Chromium's NEW headless mode + ANGLE-over-EGL to reach the NVIDIA GPU.
    gpu = ["--headless=new", "--use-gl=angle", "--use-angle=gl-egl",
           "--ignore-gpu-blocklist", "--enable-gpu"]
    sw = ["--headless=new", "--use-gl=angle", "--use-angle=swiftshader",
          "--enable-unsafe-swiftshader"]
    flags = ["--no-sandbox", "--disable-dev-shm-usage"] + (sw if args.no_gpu else gpu)

    cams = []
    with sync_playwright() as p:
        # headless=False + explicit --headless=new: Playwright must NOT inject the
        # old --headless flag, which would disable the GPU and break WebGL.
        browser = p.chromium.launch(headless=False, args=flags)
        page = browser.new_page(viewport={"width": args.w, "height": args.h},
                                device_scale_factor=args.scale)
        page.set_default_timeout(120000)
        page.on("console", lambda m: print(f"  [console] {m.text}", flush=True)
                if m.type in ("error", "warning") else None)
        page.goto(page_url, wait_until="load")
        print("waiting for Sketchfab viewerready ...", flush=True)
        page.wait_for_function("window.__ready === true || window.__error === true",
                               timeout=120000)
        if page.evaluate("!!window.__error"):
            print("ERROR: Sketchfab failed to init", file=sys.stderr); sys.exit(2)

        center = page.evaluate("window.__center")
        r0 = page.evaluate("window.__r0")
        fov0 = page.evaluate("window.__fov0")
        # model radius from initial auto-framing, then distance for our small FOV
        model_r = r0 * math.tan(math.radians(fov0) / 2.0)
        dist = model_r / math.tan(math.radians(args.fov) / 2.0) * 1.12
        print(f"center={center} r0={r0:.3f} fov0={fov0:.1f} model_r={model_r:.3f} "
              f"capture_dist={dist:.3f}", flush=True)

        import io
        import numpy as np
        from PIL import Image

        MARGIN = 0.07          # ignore outer 7% (Sketchfab corner UI lives there)
        TARGET_FILL = 0.86     # harp should span this fraction of the framed area

        def shoot_bytes(eye):
            # returns (actual_pose_read_back_from_sketchfab, png_bytes)
            pose = page.evaluate("([e,t,f])=>window.shoot(e,t,f)", [eye, center, args.fov])
            return pose, page.screenshot(omit_background=True)

        def alpha_bbox(png):
            im = np.array(Image.open(io.BytesIO(png)))
            a = im[:, :, 3]
            H, W = a.shape
            m = int(min(H, W) * MARGIN)
            inner = np.zeros_like(a, bool)
            inner[m:H-m, m:W-m] = True
            fg = (a > 200) & inner    # solid model only (ignore transparent halo)
            ys, xs = np.where(fg)
            if len(xs) == 0:
                return None
            return (xs.min(), xs.max(), ys.min(), ys.max(), W, H)

        # warm-up: the first few read-backs after viewer init are stale; throw away
        # a handful of shots so the real capture has settled, accurate poses.
        for _ in range(12):
            shoot_bytes([center[0], center[1], center[2] + dist])

        cur = dist          # warm-start: carry the converged distance between views
        for el in els:
            for az in azs:
                ar = math.radians(az); er = math.radians(el)
                d = [math.cos(er)*math.sin(ar), math.sin(er), math.cos(er)*math.cos(ar)]
                if args.fixed_dist:
                    # one consistent distance for all views (clean poses for carving)
                    cur = (args.abs_dist if args.abs_dist > 0 else
                           model_r / math.tan(math.radians(args.fov) / 2.0) * args.margin)
                    eye = [center[i] + cur * d[i] for i in range(3)]
                    pose, png = shoot_bytes(eye)
                else:
                    # auto-frame: adjust distance so the harp fills ~TARGET_FILL of height
                    # (cur warm-starts from the previous view -> 1-2 iterations each)
                    png = None
                    for _ in range(6):
                        eye = [center[i] + cur * d[i] for i in range(3)]
                        pose, png = shoot_bytes(eye)
                        bb = alpha_bbox(png)
                        if bb is None:
                            cur *= 1.6; continue       # nothing visible -> zoom out
                        x0, x1, y0, y1, W, H = bb
                        fill = max((y1 - y0) / H, (x1 - x0) / W)
                        if abs(fill - TARGET_FILL) < 0.07:
                            break
                        cur *= fill / TARGET_FILL       # near-ortho: size ~ 1/distance
                    eye = [center[i] + cur * d[i] for i in range(3)]
                name = f"view_el{int(el):+03d}_az{int(az) % 360:03d}.png"
                with open(os.path.join(args.out, name), "wb") as fh:
                    fh.write(png)
                # USE THE READ-BACK POSE (what Sketchfab actually rendered), but reject
                # stale/degenerate reads (zero-length or near-parallel to up) and fall
                # back to the requested pose (accurate for the fixed-distance orbit).
                e_a = pose["position"]; t_a = pose["target"]; f_a = pose["fov"]
                dv = [t_a[i] - e_a[i] for i in range(3)]
                dl = math.sqrt(sum(x * x for x in dv))
                intended = [d[i] for i in range(3)]                 # requested unit dir
                bad = (dl < 1e-4
                       or abs(dv[1] / dl) > 0.995                    # near-vertical glitch
                       or sum(-dv[i] / dl * intended[i] for i in range(3)) < 0.9)  # off intended
                if bad:
                    e_a, t_a, f_a = eye, list(center), args.fov
                cams.append({"file": name, "eye": e_a, "target": t_a,
                             "up": [0, 1, 0], "fov_deg": f_a,
                             "az": az, "el": el, "dist": cur,
                             "req_eye": eye,
                             "width": args.w * args.scale, "height": args.h * args.scale,
                             "view": look_at(e_a, t_a)})
                print(f"  shot {name} (req_d {cur:.1f}  actual_d "
                      f"{math.dist(e_a, t_a):.1f}  fov {f_a:.1f})", flush=True)
            # write cameras.json after each elevation ring (partial-safe on timeout)
            with open(os.path.join(args.out, "cameras.json"), "w") as f:
                json.dump({"uid": args.uid, "center": list(center), "model_radius": model_r,
                           "near_ortho_fov_deg": args.fov, "views": cams}, f, indent=1)
            print(f"  [saved cameras.json: {len(cams)} views]", flush=True)

        browser.close()

    with open(os.path.join(args.out, "cameras.json"), "w") as f:
        json.dump({"uid": args.uid, "center": list(center), "model_radius": model_r,
                   "near_ortho_fov_deg": args.fov, "views": cams}, f, indent=1)
    print(f"wrote {len(cams)} views + cameras.json to {args.out}/", flush=True)


if __name__ == "__main__":
    main()

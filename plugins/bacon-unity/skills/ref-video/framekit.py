"""framekit: measure reference videos / screenshots frame by frame.

Usage: py -I "<skill dir>/framekit.py" <command> ... --out DIR   (`<command> -h` for options; full path in every call)

Commands
  probe   V                         resolution, fps, duration, frame count, VFR check, gaps, real last frame
  sheet   V --t0 --t1 --step | --times     labelled contact sheet (PNG) of frames
  frames  V --times a,b | --burst t0,t1    full-resolution PNG per frame
  diff    V --t0 --t1 [--roi]       per-frame mean abs difference -> moving / still segments, change events
  mask    V --t0 --t1 --roi --lo r,g,b --hi r,g,b   color-mask presence + bbox per frame
  track   V --t0 --t1 --roi --method template|phase [--template PNG] [--scales a:b:s]   position / motion per frame
  color   SRC --roi --times a,b        median color (hex, spread, optional linear)
  compare A B [--roi]                side-by-side, overlay, abs diff of two images (video@t or PNG)
  fit     CSV --x col --y col --model linear|exp   least-squares fit + residuals

Rules
  * Every time is the container timestamp of the decoded frame (CAP_PROP_POS_MSEC), never frame/fps:
    LDPlayer screenrecord files are variable frame rate.
  * --roi x,y,w,h is in source pixels. Measure on full-resolution frames; sheets are for finding moments only.
  * Outputs: PNG / CSV / summary.json in --out (default ./framekit_out). Nothing is written next to the video.
    diff / mask print at most 20 segments; the summary json holds all of them.
Needs numpy, opencv (cv2), Pillow. No scipy.
Proven: 2026-10-21 on the known test videos listed in ref-video/SKILL.md (BC36 Scene_game.mp4 menu PLAY button vanishes
at frame 380 = 12.667 s via `mask`; UFD traffic_start_30s.mp4 VFR via `probe`; BCA27 video4.mp4 pan inertia via `track`).
"""
import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys

import cv2
import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ---------------------------------------------------------------- helpers

def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def parse_roi(s):
    if not s:
        return None
    x, y, w, h = (int(float(v)) for v in s.split(","))
    return x, y, w, h


def parse_list(s):
    return [float(v) for v in s.split(",") if v.strip()]


def crop(img, roi):
    if roi is None:
        return img
    x, y, w, h = roi
    return img[max(0, y):y + h, max(0, x):x + w]


def out_dir(args):
    d = args.out or "framekit_out"
    os.makedirs(d, exist_ok=True)
    return d


def write_json(d, name, obj):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return p


SEG_CAP = 20  # segments printed by diff / mask; all of them stay in the summary json


def capped_segments(summary, json_path):
    """Long noisy videos give hundreds of segments: print the first SEG_CAP, point at the json for the rest."""
    segs = summary.get("segments", [])
    if len(segs) <= SEG_CAP:
        return summary
    out = dict(summary, segments=segs[:SEG_CAP])
    out["segments_more"] = f"{len(segs) - SEG_CAP} more of {len(segs)} in {json_path}"
    return out


def write_csv(d, name, header, rows):
    p = os.path.join(d, name)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return p


class Video:
    def __init__(self, path):
        if not os.path.exists(path):
            sys.exit(f"not found: {path}")
        self.path = path
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            sys.exit(f"cannot open: {path}")
        self.w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 0.0
        self.count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.idx = -1

    def read(self):
        ok, frame = self.cap.read()
        if not ok:
            return None, None
        self.idx += 1
        return self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0, frame

    def seek(self, t):
        self.cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
        self.idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1

    def frame_at(self, t):
        """First decoded frame with timestamp >= t (exact, VFR-safe)."""
        self.seek(max(0.0, t - 0.5))
        last = (None, None, None)
        while True:
            ft, fr = self.read()
            if fr is None:
                return last
            last = (ft, fr, self.idx)
            if ft >= t - 1e-4:
                return last

    def frames(self, t0, t1):
        """Yield (index, t, frame) for every frame in [t0, t1]."""
        if t0 > 0:
            self.seek(max(0.0, t0 - 0.5))
        while True:
            ft, fr = self.read()
            if fr is None:
                return
            if ft < t0 - 1e-4:
                continue
            if t1 is not None and ft > t1 + 1e-4:
                return
            yield self.idx, ft, fr


def load_image(spec):
    """'file.png' or 'video.mp4@12.5' -> (BGR image, label)."""
    if "@" in spec and not os.path.exists(spec):
        path, t = spec.rsplit("@", 1)
        ft, fr, idx = Video(path).frame_at(float(t))
        if fr is None:
            sys.exit(f"no frame at {spec}")
        return fr, f"{os.path.basename(path)} t={ft:.3f}s f={idx}"
    img = cv2.imread(spec, cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"cannot read image: {spec}")
    return img, os.path.basename(spec)


def label(img, text):
    out = img.copy()
    scale = max(0.4, img.shape[1] / 640.0 * 0.6)
    th = max(1, int(scale * 2))
    (tw, tht), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, th)
    cv2.rectangle(out, (0, 0), (tw + 8, tht + 10), (0, 0, 0), -1)
    cv2.putText(out, text, (4, tht + 4), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 255, 255), th, cv2.LINE_AA)
    return out


def segments(series, thresh, min_dur):
    """series: list of (t, value). Returns segments of value > thresh ('active') and <= ('still')."""
    segs = []
    for t, v in series:
        state = "active" if v > thresh else "still"
        if segs and segs[-1]["state"] == state:
            segs[-1]["t1"] = t
        else:
            segs.append({"state": state, "t0": t, "t1": t})
    merged = []
    for s in segs:
        if merged and (s["t1"] - s["t0"]) < min_dur:
            merged[-1]["t1"] = s["t1"]
        elif merged and merged[-1]["state"] == s["state"]:
            merged[-1]["t1"] = s["t1"]
        else:
            merged.append(dict(s))
    for s in merged:
        s["dur"] = round(s["t1"] - s["t0"], 4)
        s["t0"], s["t1"] = round(s["t0"], 4), round(s["t1"], 4)
    return merged


# ---------------------------------------------------------------- commands

def cmd_probe(a):
    v = Video(a.video)
    info = {"file": a.video, "size_mb": round(os.path.getsize(a.video) / 1e6, 2), "width": v.w, "height": v.h,
            "fps_avg_header": round(v.fps, 3), "frame_count_header": v.count}
    ff = ffmpeg_exe()
    if ff:
        r = subprocess.run([ff, "-hide_banner", "-i", a.video], capture_output=True, text=True, errors="replace")
        info["ffmpeg"] = [l.strip() for l in r.stderr.splitlines() if "Duration" in l or "Stream" in l]
    ts, n = [], 0
    while True:
        ok = v.cap.grab()
        if not ok:
            break
        ts.append(v.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0)
        n += 1
    dts = np.diff(ts) if len(ts) > 1 else np.array([0.0])
    gaps = [(round(ts[i], 3), round(float(dts[i]), 3)) for i in range(len(dts)) if dts[i] > a.gap]
    info.update({
        "frames_decoded": n,
        "first_t": round(ts[0], 4) if ts else None,
        "last_t": round(ts[-1], 4) if ts else None,
        "fps_real": round((n - 1) / (ts[-1] - ts[0]), 3) if n > 1 and ts[-1] > ts[0] else None,
        "dt_min": round(float(dts.min()), 4), "dt_median": round(float(np.median(dts)), 4), "dt_max": round(float(dts.max()), 4),
        "vfr": bool(dts.max() - dts.min() > 0.25 * max(1e-6, float(np.median(dts)))),
        "gaps_over": a.gap, "gaps": gaps[:50], "gap_count": len(gaps),
    })
    d = out_dir(a)
    write_json(d, "probe.json", info)
    print(json.dumps(info, indent=2, ensure_ascii=False))


def sheet_times(a):
    if a.times:
        return parse_list(a.times)
    if a.windows:
        out = []
        for w in a.windows.split(","):
            t0, t1 = (float(x) for x in w.split("-"))
            out += list(np.arange(t0, t1 + 1e-9, a.step))
        return out
    if a.t0 is None or a.t1 is None or not a.step:
        sys.exit("sheet: give --times, or --t0 --t1 --step, or --windows with --step")
    return list(np.arange(a.t0, a.t1 + 1e-9, a.step))


def cmd_sheet(a):
    v = Video(a.video)
    roi = parse_roi(a.roi)
    times = sheet_times(a)
    if len(times) > a.max_tiles:
        sys.exit(f"{len(times)} tiles > --max-tiles {a.max_tiles}: use a bigger --step (coarse pass first)")
    tiles, meta = [], []
    for t in sorted(times):
        ft, fr, idx = v.frame_at(t)
        if fr is None:
            print(f"warn: no frame at {t:.3f}s (past the end)")
            continue
        img = crop(fr, roi)
        tiles.append(label(img, f"{ft:.3f}s f{idx}" if a.label == "both" else (f"{ft:.3f}s" if a.label == "t" else f"f{idx}")))
        meta.append({"requested": round(t, 4), "t": round(ft, 4), "frame": idx})
    if not tiles:
        sys.exit("no frames")
    cols = min(a.cols, len(tiles))
    tw = max(1, a.width // cols)
    th = int(tiles[0].shape[0] * tw / tiles[0].shape[1])
    rows = math.ceil(len(tiles) / cols)
    canvas = np.zeros((rows * th, cols * tw, 3), np.uint8)
    for i, im in enumerate(tiles):
        r, c = divmod(i, cols)
        canvas[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = cv2.resize(im, (tw, th), interpolation=cv2.INTER_AREA)
    d = out_dir(a)
    name = a.name or f"sheet_{times[0]:.2f}-{times[-1]:.2f}.png"
    cv2.imwrite(os.path.join(d, name), canvas)
    write_json(d, name.replace(".png", ".json"), {"video": a.video, "roi": roi, "tiles": meta})
    print(f"{os.path.join(d, name)}  ({len(tiles)} tiles, {cols} cols, tile {tw}x{th}; scaled: find moments here, measure on `frames`)")


def cmd_frames(a):
    v = Video(a.video)
    roi = parse_roi(a.roi)
    d = out_dir(a)
    rows = []
    if a.burst:
        t0, t1 = parse_list(a.burst)
        it = v.frames(t0, t1)
    else:
        if not a.times:
            sys.exit("frames: give --times or --burst")
        picked = [v.frame_at(t) for t in parse_list(a.times)]
        it = ((idx, ft, fr) for ft, fr, idx in picked if fr is not None)
    for idx, ft, fr in it:
        p = os.path.join(d, f"f_{ft:09.4f}s_{idx:06d}.png")
        cv2.imwrite(p, crop(fr, roi))
        rows.append((idx, round(ft, 4), p))
    write_csv(d, "frames.csv", ["frame", "t", "png"], rows)
    print(f"{len(rows)} frames -> {d}")


def cmd_diff(a):
    v = Video(a.video)
    roi = parse_roi(a.roi)
    prev, series, rows = None, [], []
    for idx, ft, fr in v.frames(a.t0, a.t1):
        g = cv2.cvtColor(crop(fr, roi), cv2.COLOR_BGR2GRAY)
        if a.down > 1:
            g = cv2.resize(g, (max(1, g.shape[1] // a.down), max(1, g.shape[0] // a.down)), interpolation=cv2.INTER_AREA)
        g = g.astype(np.float32)
        if prev is not None:
            val = float(np.mean(np.abs(g - prev)))
            series.append((ft, val))
            rows.append((idx, round(ft, 4), round(val, 4)))
        prev = g
    if not series:
        sys.exit("no frames in range")
    vals = np.array([s[1] for s in series])
    floor = float(np.percentile(vals, 10))
    thresh = a.thresh if a.thresh is not None else max(floor * 3.0, floor + 0.5)
    segs = segments(series, thresh, a.min_dur)
    d = out_dir(a)
    write_csv(d, "diff.csv", ["frame", "t", "mean_abs_diff"], rows)
    summary = {"video": a.video, "roi": roi, "down": a.down, "noise_floor_p10": round(floor, 4), "thresh": round(thresh, 4),
               "max": round(float(vals.max()), 4), "segments": segs}
    write_json(d, "diff_summary.json", summary)
    print(json.dumps(capped_segments(summary, os.path.join(d, "diff_summary.json")), indent=2))


def cmd_mask(a):
    v = Video(a.video)
    roi = parse_roi(a.roi)
    lo = np.array(parse_list(a.lo)[::-1], np.uint8)  # r,g,b -> b,g,r
    hi = np.array(parse_list(a.hi)[::-1], np.uint8)
    rows, series = [], []
    for idx, ft, fr in v.frames(a.t0, a.t1):
        m = cv2.inRange(crop(fr, roi), lo, hi)
        cols = np.where((m > 0).sum(axis=0) >= a.min_count)[0]
        rws = np.where((m > 0).sum(axis=1) >= a.min_count)[0]
        n = int((m > 0).sum())
        if len(cols) and len(rws):
            x0, x1, y0, y1 = int(cols[0]), int(cols[-1]), int(rws[0]), int(rws[-1])
            rows.append((idx, round(ft, 4), n, x0, y0, x1 - x0 + 1, y1 - y0 + 1))
        else:
            rows.append((idx, round(ft, 4), n, "", "", "", ""))
        series.append((ft, n))
    d = out_dir(a)
    write_csv(d, "mask.csv", ["frame", "t", "pixels", "x0", "y0", "w", "h"], rows)
    segs = segments(series, a.present, a.min_dur)
    for s in segs:
        s["state"] = "present" if s["state"] == "active" else "absent"
    write_json(d, "mask_summary.json", {"video": a.video, "roi": roi, "lo_rgb": a.lo, "hi_rgb": a.hi, "segments": segs})
    shown = capped_segments({"segments": segs}, os.path.join(d, "mask_summary.json"))
    print(json.dumps(shown if "segments_more" in shown else segs, indent=2))


def cmd_track(a):
    v = Video(a.video)
    roi = parse_roi(a.roi)
    rows = []
    if a.method == "template":
        if not a.template:
            sys.exit("track template: --template PNG (cut it from a frame with `frames --roi`)")
        tpl0 = cv2.imread(a.template, cv2.IMREAD_GRAYSCALE)
        s0, s1, ss = (float(x) for x in (a.scales or "1:1:1").split(":"))
        scales = np.arange(s0, s1 + 1e-9, ss) if ss > 0 else [1.0]
        ox, oy = (roi[0], roi[1]) if roi else (0, 0)
        for idx, ft, fr in v.frames(a.t0, a.t1):
            g = cv2.cvtColor(crop(fr, roi), cv2.COLOR_BGR2GRAY)
            best = (-2.0, 0, 0, 1.0)
            for s in scales:
                tpl = tpl0 if s == 1.0 else cv2.resize(tpl0, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
                if tpl.shape[0] > g.shape[0] or tpl.shape[1] > g.shape[1]:
                    continue
                r = cv2.matchTemplate(g, tpl, cv2.TM_CCOEFF_NORMED)
                _, mv, _, ml = cv2.minMaxLoc(r)
                if mv > best[0]:
                    best = (mv, ml[0], ml[1], s)
            mv, x, y, s = best
            th, tw = int(tpl0.shape[0] * s), int(tpl0.shape[1] * s)
            rows.append([idx, round(ft, 4), round(mv, 4), x + ox, y + oy, round(x + ox + tw / 2, 2), round(y + oy + th / 2, 2), round(s, 4)])
        header = ["frame", "t", "ncc", "x", "y", "cx", "cy", "scale"]
        xi, yi = 5, 6
    else:  # phase correlation between consecutive frames (sub-pixel shift of the ROI content)
        prev, cx, cy = None, 0.0, 0.0
        win = None
        for idx, ft, fr in v.frames(a.t0, a.t1):
            g = cv2.cvtColor(crop(fr, roi), cv2.COLOR_BGR2GRAY).astype(np.float32)
            if win is None:
                win = cv2.createHanningWindow((g.shape[1], g.shape[0]), cv2.CV_32F)
            if prev is not None:
                (dx, dy), resp = cv2.phaseCorrelate(prev, g, win)
                cx += dx
                cy += dy
                rows.append([idx, round(ft, 4), round(float(resp), 4), round(dx, 3), round(dy, 3), round(cx, 3), round(cy, 3)])
            prev = g
        header = ["frame", "t", "response", "dx", "dy", "cum_x", "cum_y"]
        xi, yi = 5, 6
    # velocity from real timestamps
    for i, r in enumerate(rows):
        if i == 0:
            r += ["", ""]
            continue
        dt = r[1] - rows[i - 1][1]
        r += [round((r[xi] - rows[i - 1][xi]) / dt, 2) if dt > 0 else "", round((r[yi] - rows[i - 1][yi]) / dt, 2) if dt > 0 else ""]
    header += ["vx_px_s", "vy_px_s"]
    d = out_dir(a)
    p = write_csv(d, f"track_{a.method}.csv", header, rows)
    if rows:
        print(f"{p}  ({len(rows)} rows; first {rows[0][:7]}, last {rows[-1][:7]})")


def cmd_color(a):
    roi = parse_roi(a.roi)
    imgs = []
    if a.times:
        v = Video(a.src)
        for t in parse_list(a.times):
            ft, fr, idx = v.frame_at(t)
            if fr is not None:
                imgs.append((f"t={ft:.3f}s f={idx}", fr))
    else:
        img, lab = load_image(a.src)
        imgs.append((lab, img))
    res, meds = [], []
    for lab, fr in imgs:
        px = crop(fr, roi).reshape(-1, 3).astype(np.float32)
        med = np.median(px, axis=0)[::-1]  # rgb
        q1, q3 = np.percentile(px, 25, axis=0)[::-1], np.percentile(px, 75, axis=0)[::-1]
        meds.append(med)
        e = {"src": lab, "rgb": [int(round(c)) for c in med], "hex": "#%02X%02X%02X" % tuple(int(round(c)) for c in med),
             "iqr": [int(round(c)) for c in (q3 - q1)]}
        if a.linear:
            e["linear"] = [round(((c / 255) / 12.92) if c / 255 <= 0.04045 else (((c / 255) + 0.055) / 1.055) ** 2.4, 5) for c in med]
        res.append(e)
    allm = np.median(np.array(meds), axis=0)
    out = {"roi": roi, "per_frame": res, "overall_rgb": [int(round(c)) for c in allm],
           "overall_hex": "#%02X%02X%02X" % tuple(int(round(c)) for c in allm),
           "spread_between_frames": [int(c) for c in (np.max(meds, axis=0) - np.min(meds, axis=0))]}
    write_json(out_dir(a), "color.json", out)
    print(json.dumps(out, indent=2))


def cmd_compare(a):
    A, la = load_image(a.a)
    B, lb = load_image(a.b)
    roi = parse_roi(a.roi)
    A2, B2 = crop(A, roi), crop(B, parse_roi(a.roi_b) if a.roi_b else roi)
    note = ""
    if A2.shape[:2] != B2.shape[:2]:
        note = f"B resized {B2.shape[1]}x{B2.shape[0]} -> {A2.shape[1]}x{A2.shape[0]}"
        B2 = cv2.resize(B2, (A2.shape[1], A2.shape[0]), interpolation=cv2.INTER_AREA)
    diff = cv2.absdiff(A2, B2)
    over = cv2.addWeighted(A2, 0.5, B2, 0.5, 0)
    side = np.hstack([label(A2, "A " + la), label(B2, "B " + lb)])
    d = out_dir(a)
    for n, im in (("compare_side.png", side), ("compare_overlay.png", over), ("compare_diff.png", diff)):
        cv2.imwrite(os.path.join(d, n), im)
    res = {"A": la, "B": lb, "roi": roi, "note": note, "mean_abs_diff": round(float(diff.mean()), 3),
           "mean_rgb_A": [round(float(c), 1) for c in A2.reshape(-1, 3).mean(0)[::-1]],
           "mean_rgb_B": [round(float(c), 1) for c in B2.reshape(-1, 3).mean(0)[::-1]]}
    if a.align:
        ga, gb = cv2.cvtColor(A, cv2.COLOR_BGR2GRAY), cv2.cvtColor(B2, cv2.COLOR_BGR2GRAY)
        if gb.shape[0] <= ga.shape[0] and gb.shape[1] <= ga.shape[1]:
            r = cv2.matchTemplate(ga, gb, cv2.TM_CCOEFF_NORMED)
            _, mv, _, ml = cv2.minMaxLoc(r)
            res["align_B_in_A"] = {"x": ml[0], "y": ml[1], "ncc": round(mv, 4),
                                   "offset_vs_roi": [ml[0] - (roi[0] if roi else 0), ml[1] - (roi[1] if roi else 0)]}
    write_json(d, "compare.json", res)
    print(json.dumps(res, indent=2, ensure_ascii=False))


def cmd_fit(a):
    with open(a.csv, encoding="utf-8") as f:
        rd = list(csv.DictReader(f))
    pts = [(float(r[a.x]), float(r[a.y])) for r in rd if r.get(a.x) not in ("", None) and r.get(a.y) not in ("", None)]
    x, y = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
    if a.model == "linear":
        k, b = np.polyfit(x, y, 1)
        pred = k * x + b
        res = {"model": "y = k*x + b", "k": float(k), "b": float(b)}
    else:
        m = y > 0
        k, lnA = np.polyfit(x[m], np.log(y[m]), 1)
        pred = np.exp(lnA) * np.exp(k * x)
        res = {"model": "y = A*exp(k*x)", "A": float(np.exp(lnA)), "k": float(k)}
    resid = y - pred
    res.update({"n": int(len(x)), "rmse": float(np.sqrt(np.mean(resid ** 2))), "max_abs_resid": float(np.max(np.abs(resid)))})
    write_json(out_dir(a), f"fit_{a.y}_vs_{a.x}.json", res)
    print(json.dumps(res, indent=2))


# ---------------------------------------------------------------- cli

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, *pos):
        s = sub.add_parser(name)
        for x in pos:
            s.add_argument(x)
        s.add_argument("--out")
        s.set_defaults(fn=fn)
        return s

    s = add("probe", cmd_probe, "video"); s.add_argument("--gap", type=float, default=0.1)
    s = add("sheet", cmd_sheet, "video")
    for k in ("--t0", "--t1", "--step"):
        s.add_argument(k, type=float)
    s.add_argument("--times"); s.add_argument("--windows"); s.add_argument("--roi")
    s.add_argument("--cols", type=int, default=5); s.add_argument("--width", type=int, default=1600)
    s.add_argument("--label", choices=["t", "frame", "both"], default="both"); s.add_argument("--name")
    s.add_argument("--max-tiles", type=int, default=60)
    s = add("frames", cmd_frames, "video"); s.add_argument("--times"); s.add_argument("--burst"); s.add_argument("--roi")
    s = add("diff", cmd_diff, "video")
    s.add_argument("--t0", type=float, default=0.0); s.add_argument("--t1", type=float); s.add_argument("--roi")
    s.add_argument("--down", type=int, default=4); s.add_argument("--thresh", type=float); s.add_argument("--min-dur", type=float, default=0.1)
    s = add("mask", cmd_mask, "video")
    s.add_argument("--t0", type=float, default=0.0); s.add_argument("--t1", type=float); s.add_argument("--roi")
    s.add_argument("--lo", required=True); s.add_argument("--hi", required=True)
    s.add_argument("--min-count", type=int, default=8); s.add_argument("--present", type=float, default=50)
    s.add_argument("--min-dur", type=float, default=0.05)
    s = add("track", cmd_track, "video")
    s.add_argument("--t0", type=float, default=0.0); s.add_argument("--t1", type=float); s.add_argument("--roi")
    s.add_argument("--method", choices=["template", "phase"], default="template")
    s.add_argument("--template"); s.add_argument("--scales")
    s = add("color", cmd_color, "src"); s.add_argument("--roi"); s.add_argument("--times"); s.add_argument("--linear", action="store_true")
    s = add("compare", cmd_compare, "a", "b"); s.add_argument("--roi"); s.add_argument("--roi-b"); s.add_argument("--align", action="store_true")
    s = add("fit", cmd_fit, "csv"); s.add_argument("--x", required=True); s.add_argument("--y", required=True)
    s.add_argument("--model", choices=["linear", "exp"], default="linear")

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

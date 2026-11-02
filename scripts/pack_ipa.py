#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inject the local web build into an unsigned shell .ipa.

Usage:
    python pack_ipa.py --shell AzerothSurvivors-unsigned.ipa \
                       --game  D:/wow-site \
                       --out   AzerothSurvivors.ipa

The shell ipa is produced by CI from the tiny placeholder www/ folder.
This script replaces the placeholder with the real game assets, so the
1.6 GB of data never has to travel through git or the build server.
"""
import argparse
import os
import shutil
import sys
import tempfile
import time
import zipfile

BOOT_PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "www", "index.html")


def find_app(payload_root):
    payload = os.path.join(payload_root, "Payload")
    if not os.path.isdir(payload):
        sys.exit("ERROR: no Payload/ directory in the shell ipa")
    for name in os.listdir(payload):
        if name.endswith(".app"):
            return os.path.join(payload, name)
    sys.exit("ERROR: no .app bundle inside Payload/")


def copy_tree(src, dst, on_progress=None):
    total = 0
    for root, _dirs, files in os.walk(src):
        total += len(files)
    done = 0
    copied_bytes = 0
    for root, _dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for f in files:
            s = os.path.join(root, f)
            d = os.path.join(target_dir, f)
            shutil.copy2(s, d)
            done += 1
            copied_bytes += os.path.getsize(s)
            if on_progress and (done % 500 == 0 or done == total):
                on_progress(done, total, copied_bytes)
    return done, copied_bytes


ALREADY_COMPRESSED = {
    ".mpq", ".zip", ".gz", ".7z", ".rar", ".wasm", ".ogg", ".mp3", ".wav",
    ".blp", ".jpg", ".jpeg", ".png", ".webp", ".ttf", ".otf", ".woff", ".woff2",
    ".mp4", ".webm", ".bin", ".dll", ".exe",
}


def zip_dir(src_root, out_path, on_progress=None):
    entries = []
    for root, _dirs, files in os.walk(src_root):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, src_root)
            entries.append((full, rel.replace(os.sep, "/")))
    total = len(entries)
    t0 = time.time()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=1,
                         allowZip64=True) as zf:
        for i, (full, rel) in enumerate(entries, 1):
            ext = os.path.splitext(full)[1].lower()
            method = zipfile.ZIP_STORED if ext in ALREADY_COMPRESSED else zipfile.ZIP_DEFLATED
            zf.write(full, rel, compress_type=method)
            if on_progress and (i % 2000 == 0 or i == total):
                on_progress(i, total, time.time() - t0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shell", required=True, help="unsigned shell ipa from CI")
    ap.add_argument("--game", required=True, help="path to the web build (D:/wow-site)")
    ap.add_argument("--out", required=True, help="output ipa path")
    args = ap.parse_args()

    for p in (args.shell, args.game):
        if not os.path.exists(p):
            sys.exit(f"ERROR: path not found: {p}")
    if not os.path.isfile(BOOT_PAGE):
        sys.exit(f"ERROR: boot page missing: {BOOT_PAGE}")

    work = tempfile.mkdtemp(prefix="azs_pack_")
    try:
        print(f"[1/5] 解压空壳 ipa ...")
        with zipfile.ZipFile(args.shell) as zf:
            zf.extractall(work)

        app = find_app(work)
        print(f"      app bundle: {os.path.basename(app)}")

        public = os.path.join(app, "public")
        if os.path.isdir(public):
            print("[2/5] 清空占位资源 ...")
            shutil.rmtree(public)
        os.makedirs(public, exist_ok=True)

        print("[3/5] 复制游戏资源（1.6 GB，需要几分钟）...")
        def cp_progress(done, total, nbytes):
            print(f"      {done}/{total} 文件  {nbytes/1048576:.0f} MB", flush=True)

        copy_tree(args.game, public, cp_progress)

        game_index = os.path.join(public, "index.html")
        if not os.path.isfile(game_index):
            sys.exit("ERROR: 游戏目录里没有 index.html")
        shutil.move(game_index, os.path.join(public, "game.html"))

        shutil.copy2(BOOT_PAGE, os.path.join(public, "index.html"))
        print("      已写入启动自检页 index.html，游戏入口改名为 game.html")

        print("[4/5] 重新打包 ipa ...")
        def zip_progress(done, total, secs):
            print(f"      {done}/{total} 条目  {secs:.0f}s", flush=True)

        out_tmp = args.out + ".tmp"
        zip_dir(work, out_tmp, zip_progress)
        if os.path.exists(args.out):
            os.remove(args.out)
        os.rename(out_tmp, args.out)

        size = os.path.getsize(args.out)
        print(f"[5/5] 完成: {args.out}  ({size/1048576:.0f} MB)")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()

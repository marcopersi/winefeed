#!/usr/bin/env python3
"""Materialize online-only Google Drive JSON files (download locally).

Reads every JSON in the archive (except already-localized IDealwine dirs),
forcing the file provider to cache them. Resumable: skips files that already
have local data blocks. Logs progress.
"""
import glob
import os
import threading
from concurrent.futures import ThreadPoolExecutor

ARCHIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/"
    "Meine Ablage/Wein/WeinAuktionspreise")

lock = threading.Lock()
done = 0
errors = 0
total = 0


def is_local(path):
    try:
        return os.stat(path).st_blocks > 0
    except OSError:
        return False


def materialize(f):
    global done, errors
    if is_local(f):
        return
    try:
        with open(f, "rb") as fh:
            fh.read()
        with lock:
            done += 1
            if done % 500 == 0:
                print(f"materialized {done}/{total} (errors={errors})",
                      flush=True)
    except Exception as e:
        with lock:
            errors += 1
            print(f"ERR {f}: {e}", flush=True)


def main():
    global total
    files = []
    for house in os.listdir(ARCHIVE):
        hdir = os.path.join(ARCHIVE, house)
        if not os.path.isdir(hdir):
            continue
        if house == "IDealwine":
            continue
        files.extend(glob.glob(os.path.join(hdir, "**", "*.json"),
                               recursive=True))
    files.sort()
    total = len(files)
    print(f"total files: {total}", flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(materialize, files))
    print(f"DONE materialized={done} total={total} errors={errors}", flush=True)


if __name__ == "__main__":
    main()

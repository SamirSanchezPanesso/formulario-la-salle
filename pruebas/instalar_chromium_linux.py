#!/usr/bin/env python3
"""Descarga oficial del Chromium utilizado, únicamente Linux x86_64."""
import argparse
import os
import platform
import stat
import urllib.request
import zipfile
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--destination',default='navegador')
args=parser.parse_args()
if platform.system()!='Linux' or platform.machine() not in ('x86_64','AMD64'):
    parser.error('Este helper requiere Linux x86_64. Use npx playwright install chromium en otros sistemas.')
destination=Path(args.destination).resolve()
destination.mkdir(parents=True,exist_ok=True)
archive=destination/'chrome-headless-shell-134.zip'
url='https://storage.googleapis.com/chrome-for-testing-public/134.0.6998.35/linux64/chrome-headless-shell-linux64.zip'
with urllib.request.urlopen(url,timeout=60) as source, archive.open('wb') as target:
    while data:=source.read(1024*1024): target.write(data)
with zipfile.ZipFile(archive) as source: source.extractall(destination)
executable=destination/'chrome-headless-shell-linux64'/'chrome-headless-shell'
executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
print(executable)

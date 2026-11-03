#!/usr/bin/env python3
"""Build the public live demo: XLRTE Mastery with the fictional learner Sam Beispiel, as a static page (GitHub Pages).

    python3 demo/build_site.py --out _site [--lang de]

Works on a throwaway copy of this folder (git-tracked files only), so your own data is never touched. Only fictional
demo data goes in. setup's own pipeline (pack build, demo history, cockpit render) does the rest.
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_PREFIX = (".github/", "installer/", "docs/media/")
BANNER = {
    "de": ("Live-Demo mit erfundenen Daten (Sam Beispiel). Nichts hier ist echt, nichts wird gespeichert.", "XLRTE Mastery installieren"),
    "en": ("Live demo with made-up data (Sam Beispiel). Nothing here is real, nothing is stored.", "Install XLRTE Mastery"),
}


def _tracked_files():
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], check=True, capture_output=True).stdout.decode("utf-8")
    return [f for f in out.split("\0") if f and not f.startswith(SKIP_PREFIX)]


def _copy_tree(dst):
    for rel in _tracked_files():
        src = os.path.join(ROOT, rel)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
            shutil.copy2(src, os.path.join(dst, rel))


def _clean(html, work, lang):
    html = html.replace(work + os.sep, "").replace(work, ".")
    html = re.sub(r'<img[^>]+src="(?:/|[A-Za-z]:\\)[^"]*"[^>]*>', "", html)            # leftover absolute image paths
    text, cta = BANNER.get(lang, BANNER["de"])
    bar = ('<div style="position:fixed;left:0;right:0;bottom:0;z-index:9998;background:#E4572E;color:#0E0E10;'
           'font:600 13px/1.4 system-ui,sans-serif;padding:8px 14px;text-align:center">%s · '
           '<a href="https://github.com/yslop/xlrte-mastery/releases/latest" style="color:#0E0E10">%s →</a></div>') % (text, cta)
    return html.replace("</body>", bar + "</body>", 1) if "</body>" in html else html + bar


def build(out, lang="de"):
    work = tempfile.mkdtemp(prefix="mastery-demo-")
    _copy_tree(work)
    sys.path.insert(0, os.path.join(work, "setup"))
    import xlrte_setup
    xlrte_setup.ROOT = work
    xlrte_setup.SETTINGS = os.path.join(work, "config", "settings.json")
    answers = {"name": "Sam Beispiel", "ui_language": lang, "exam": "pmp",
               "target_date": (datetime.date.today() + datetime.timedelta(days=90)).isoformat(), "demo": True}
    for m in xlrte_setup.save({"answers": answers, "ai": {"provider": "none"}, "privacy": {"local_only": True}}):
        print(m)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    page = os.path.join(work, "XLRTE_Cockpit.html")
    with open(page, encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(out, "XLRTE_Cockpit.html"), "w", encoding="utf-8") as f:
        f.write(_clean(html, work, lang))
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write('<!doctype html><meta charset="utf-8"><title>XLRTE Mastery · Live-Demo</title>'
                '<meta http-equiv="refresh" content="0; url=XLRTE_Cockpit.html"><a href="XLRTE_Cockpit.html">Mastery-Demo öffnen</a>')
    open(os.path.join(out, ".nojekyll"), "w").close()
    shutil.rmtree(work, ignore_errors=True)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the static live demo")
    ap.add_argument("--out", default=os.path.join(ROOT, "_site"))
    ap.add_argument("--lang", default="de", choices=["de", "en"])
    a = ap.parse_args(argv)
    print("Seiten:", build(os.path.abspath(a.out), a.lang))
    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUNDLE_DIR = DIST / "PATH_cost_effective_bundle"


def run_render(landscape: str | None, sdyd: float, sddc: float) -> None:
    cmd = [
        "python",
        "render_both_reports.py",
    ]
    if landscape:
        cmd.extend(["--landscape", landscape])
    cmd.extend(["--sdyd-threshold", str(sdyd), "--sddc-threshold", str(sddc)])
    subprocess.run(cmd, cwd=ROOT, check=True)


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def build_bundle() -> Path:
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    files_to_copy = [
        "README.md",
        "render_both_reports.py",
        "PATH_CE_Report_Universal.qmd",
        "PATH_CE_Report_Universal.html",
        "PATH_CE_Report_PDF.qmd",
        "PATH_CE_Report_PDF.pdf",
        "PATH_CE.py",
        "PATH_data_prep.py",
        "PATH_plot.py",
        "requirements.txt",
        "create_handoff_bundle.py",
    ]

    for rel in files_to_copy:
        src = ROOT / rel
        dst = BUNDLE_DIR / rel
        copy_if_exists(src, dst)

    # Bundle the static assets and generated download artifacts used by the reports.
    copy_if_exists(ROOT / "static", BUNDLE_DIR / "static")

    # Also include any top-level generated threshold caches that may be useful for offline review.
    for generated in ROOT.glob("*_threshold_analysis_results_generated.*"):
        copy_if_exists(generated, BUNDLE_DIR / generated.name)

    launch_server_bat = BUNDLE_DIR / "launch_report_server.bat"
    launch_server_bat.write_text(
        "@echo off\n"
        "cd /d %~dp0\n"
        "echo Starting local server on http://localhost:8000/PATH_CE_Report_Universal.html\n"
        "start http://localhost:8000/PATH_CE_Report_Universal.html\n"
        "python -m http.server 8000\n",
        encoding="utf-8",
    )

    readme_text = (
        "# PATH Cost Effective Bundle\n\n"
        "Open PATH_CE_Report_Universal.html for the interactive report, or PATH_CE_Report_PDF.pdf for the static PDF.\n"
        "Run launch_report_server.bat to serve the bundle locally on Windows.\n"
    )
    (BUNDLE_DIR / "BUNDLE_README.txt").write_text(readme_text, encoding="utf-8")

    return BUNDLE_DIR


def zip_bundle(bundle_dir: Path) -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    zip_base = DIST / "PATH_Report_viz_bundle"
    zip_path = shutil.make_archive(str(zip_base), "zip", root_dir=bundle_dir)
    return Path(zip_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render PATH cost-effective reports and create a shareable handoff bundle.")
    parser.add_argument("--landscape", default=None, help="Landscape name to render (auto-detect if omitted).")
    parser.add_argument("--sdyd-threshold", type=float, default=15)
    parser.add_argument("--sddc-threshold", type=float, default=33922)
    parser.add_argument("--skip-render", action="store_true", help="Package existing outputs without rerendering.")
    args = parser.parse_args()

    if not args.skip_render:
        run_render(landscape=args.landscape, sdyd=args.sdyd_threshold, sddc=args.sddc_threshold)

    bundle_dir = build_bundle()
    zip_path = zip_bundle(bundle_dir)

    print(f"Bundle directory: {bundle_dir}")
    print(f"Bundle zip: {zip_path}")
    print("For viewing sample report: run launch_report_server.bat in bundle directory.")


if __name__ == "__main__":
    main()

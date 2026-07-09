#!/usr/bin/env python3
"""Render both HTML and PDF PATH reports together, sharing computed threshold data."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Render PATH_CE_Report_Universal.qmd (HTML) and PATH_CE_Report_PDF.qmd (PDF) in sequence."
    )
    parser.add_argument(
        "--landscape",
        default=None,
        help="Landscape name (e.g., gatecreek, millcreek3). If not provided, auto-detects from workspace files.",
    )
    parser.add_argument(
        "--sdyd-threshold",
        type=float,
        default=15,
        help="Hillslope Sediment Yield threshold (tons/acre). Default: 15",
    )
    parser.add_argument(
        "--sddc-threshold",
        type=float,
        default=33922,
        help="Watershed Sediment Discharge threshold (tons). Default: 33922",
    )
    parser.add_argument(
        "--quarto",
        default="quarto",
        help="Quarto executable name/path. Default: quarto",
    )
    return parser.parse_args()


def render_report(qmd_file, landscape, sdyd_threshold, sddc_threshold, quarto_exe):
    """Render a single Quarto report with specified parameters."""
    cmd = [
        quarto_exe,
        "render",
        str(qmd_file),
        "-P",
        f"landscape={landscape}",
        "-P",
        f"sdyd_threshold={sdyd_threshold}",
        "-P",
        f"sddc_threshold={sddc_threshold}",
    ]
    env = os.environ.copy()
    env["PATH_REPORT_LANDSCAPE"] = str(landscape)
    env["PATH_REPORT_SDYD_THRESHOLD"] = str(sdyd_threshold)
    env["PATH_REPORT_SDDC_THRESHOLD"] = str(sddc_threshold)
    
    print(f"\n{'='*70}")
    print(f"Rendering: {qmd_file}")
    print(f"Landscape: {landscape}")
    print(f"Sdyd Threshold: {sdyd_threshold}, Sddc Threshold: {sddc_threshold}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*70}\n")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent, env=env)
    return result.returncode == 0


def main():
    args = parse_args()
    workspace = Path(__file__).parent
    
    # Auto-detect landscape if not provided
    landscape = args.landscape
    if not landscape:
        prefixes = []
        patterns = [
            "*_scenarios.hillslope_summaries.csv",
            "*_contrasts.out.csv",
            "*_hillslopes.parquet",
            "*_contrast_id_definitions.psv",
            "*_subcatchments.WGS.*",
            "*_channels.WGS.*",
        ]
        for pattern in patterns:
            for path in workspace.glob(pattern):
                prefix = path.name.split("_", 1)[0].strip()
                if prefix:
                    prefixes.append(prefix)
        
        if prefixes:
            landscape = max(set(prefixes), key=prefixes.count)
            print(f"Auto-detected landscape: {landscape}\n")
        else:
            print("ERROR: Could not auto-detect landscape from workspace files.")
            print("Please provide --landscape explicitly.")
            sys.exit(1)
    
    # Render HTML first (generates cached threshold data)
    html_ok = render_report(
        workspace / "PATH_CE_Report_Universal.qmd",
        landscape,
        args.sdyd_threshold,
        args.sddc_threshold,
        args.quarto,
    )
    
    if not html_ok:
        print("\nERROR: HTML report rendering failed. Aborting PDF render.")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("HTML report completed successfully. Cached threshold data available.")
    print("="*70)
    
    # Render PDF (reuses cached threshold data from HTML render)
    pdf_ok = render_report(
        workspace / "PATH_CE_Report_PDF.qmd",
        landscape,
        args.sdyd_threshold,
        args.sddc_threshold,
        args.quarto,
    )
    
    if not pdf_ok:
        print("\nERROR: PDF report rendering failed.")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("✓ Both reports rendered successfully!")
    print(f"  HTML: PATH_CE_Report_Universal.html")
    print(f"  PDF:  PATH_CE_Report_PDF.pdf")
    print("="*70)


if __name__ == "__main__":
    main()

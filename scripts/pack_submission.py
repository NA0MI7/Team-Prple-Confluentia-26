#!/usr/bin/env python3
"""
Package the final submission zip file strictly following Section 09 of the Hackathon specification.

Structure of <TeamName>.zip:
├── baseline-results/
│   └── gate.json
├── test-run-logs/
│   └── (3 model run directories)
├── sample-trajectories/
│   ├── success/
│   └── failure/
├── design-doc.pdf
└── deck.pdf
"""
import os
import sys
import zipfile
import argparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pack_submission(team_name="prple"):
    zip_filename = f"{team_name}.zip"
    zip_filepath = os.path.join(ROOT_DIR, zip_filename)
    
    print(f"Packaging submission archive: {zip_filename}...")
    
    # Required files and directories
    required_entries = [
        "baseline-results/gate.json",
        "design-doc.pdf",
        "deck.pdf",
    ]
    
    for req in required_entries:
        full_path = os.path.join(ROOT_DIR, req)
        if not os.path.isfile(full_path):
            print(f"ERROR: Missing required deliverable: {req}")
            sys.exit(1)
            
    with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add single files
        zipf.write(os.path.join(ROOT_DIR, "design-doc.pdf"), "design-doc.pdf")
        zipf.write(os.path.join(ROOT_DIR, "deck.pdf"), "deck.pdf")
        
        # Add baseline-results/
        for root, _, files in os.walk(os.path.join(ROOT_DIR, "baseline-results")):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, ROOT_DIR)
                zipf.write(full, rel)
                
        # Add test-run-logs/
        for root, _, files in os.walk(os.path.join(ROOT_DIR, "test-run-logs")):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, ROOT_DIR)
                zipf.write(full, rel)
                
        # Add sample-trajectories/
        for root, _, files in os.walk(os.path.join(ROOT_DIR, "sample-trajectories")):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, ROOT_DIR)
                zipf.write(full, rel)
                
    file_size_kb = os.path.getsize(zip_filepath) / 1024
    print(f"SUCCESS: Created {zip_filename} ({file_size_kb:.1f} KB)")
    print("Archive Contents:")
    with zipfile.ZipFile(zip_filepath, "r") as zipf:
        for name in sorted(zipf.namelist()):
            print(f"  {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Hackathon Submission Zip")
    parser.add_argument("--team", default="prple", help="Team name (default: prple)")
    args = parser.parse_args()
    pack_submission(args.team)

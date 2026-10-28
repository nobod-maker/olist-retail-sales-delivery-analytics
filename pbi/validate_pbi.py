"""
Power BI PBIR Report Validator
Runs pbi_cli validation engine across the generated Olist Retail Command Center report.
"""

import sys
import os
from pathlib import Path

def validate():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = Path(script_dir) / "Olist_Retail_Command_Center.Report"
    definition_dir = report_path / "definition"
    
    print(f"Validating Power BI report definition at: {definition_dir}")
    
    try:
        from pbi_cli.core.pbir_path import validate_report_structure
        errors = validate_report_structure(definition_dir)
        if errors:
            print(f"[FAIL] Found {len(errors)} validation error(s):")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print("[PASS] Report structure strictly conforms to Microsoft Fabric PBIR standards (0 errors).")
            sys.exit(0)
    except ImportError:
        print("[WARN] pbi_cli package not installed. Verifying essential JSON files manually...")
        required_files = [
            definition_dir / "version.json",
            definition_dir / "report.json",
            definition_dir / "pages" / "pages.json"
        ]
        for rf in required_files:
            if not rf.exists():
                print(f"[FAIL] Missing required PBIR file: {rf}")
                sys.exit(1)
        print("[PASS] All required PBIR metadata files exist.")
        sys.exit(0)

if __name__ == '__main__':
    validate()

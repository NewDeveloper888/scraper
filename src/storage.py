import json
from pathlib import Path
from pydantic import BaseModel

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def save_json_records(filename: str, records: list[BaseModel | dict]) -> None:
    """Save records idempotently to output directory in formatted JSON."""
    file_path = OUTPUT_DIR / filename
    serializable = [
        r.model_dump(mode="json") if isinstance(r, BaseModel) else r
        for r in records
    ]
    file_path.write_text(
        json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[STORED] {len(records)} records written to {file_path}")


def save_run_report(report_data: dict) -> None:
    """Write run telemetry and statistics to output/run-report.json."""
    file_path = OUTPUT_DIR / "run-report.json"
    file_path.write_text(
        json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[REPORT] Run report written to {file_path}")
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import tkinter as tk

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import IncomeTrackerApp


def build_sample_data(file_path: Path) -> None:
    data = {
        "schema_version": 3,
        "items": {
            "九转金丹": {"price": 0, "tag": "日常", "updated_at": "2026-04-11T14:00:00"},
            "五色旗盒": {"price": 250000, "tag": "杂项", "updated_at": "2026-04-11T14:00:00"},
            "修炼果": {"price": 650000, "tag": "日常", "updated_at": "2026-04-11T14:00:00"},
            "夜光珠": {"price": 780000, "tag": "五宝", "updated_at": "2026-04-11T14:00:00"},
            "定魂珠": {"price": 810000, "tag": "五宝", "updated_at": "2026-04-11T14:00:00"},
            "宝石": {"price": 90000, "tag": "打造", "updated_at": "2026-04-11T14:00:00"},
            "强化石": {"price": 110000, "tag": "打造", "updated_at": "2026-04-11T14:00:00"},
        },
        "exchange_rate": {"cash": 100.0, "coin": 15000000},
        "records": [
            {
                "id": "r1",
                "date": "2026-04-11",
                "time": "14:01:00",
                "created_at": "2026-04-11T14:01:00",
                "updated_at": "2026-04-11T14:01:00",
                "item_name": "九转金丹",
                "price_snapshot": 0,
                "quantity": 1,
                "subtotal": 0,
            },
            {
                "id": "r2",
                "date": "2026-04-11",
                "time": "14:05:00",
                "created_at": "2026-04-11T14:05:00",
                "updated_at": "2026-04-11T14:05:00",
                "item_name": "修炼果",
                "price_snapshot": 650000,
                "quantity": 2,
                "subtotal": 1300000,
            },
        ],
    }
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def assert_childs_fit(parent: tk.Misc, label: str) -> None:
    parent.update_idletasks()
    parent_height = parent.winfo_height()
    failures: list[str] = []
    for child in parent.winfo_children():
        bottom = child.winfo_y() + child.winfo_height()
        if bottom > parent_height:
            failures.append(
                f"{label}: child {child.winfo_class()} bottom={bottom} parent_height={parent_height}"
            )
    if failures:
        raise AssertionError("\n".join(failures))


def main() -> None:
    tmp_dir = Path(tempfile.mkdtemp(prefix="mhxy_ui_smoke_"))
    data_file = tmp_dir / "data.json"
    build_sample_data(data_file)
    os.environ["MHXY_INCOME_TRACKER_DATA_FILE"] = str(data_file)

    root = tk.Tk()
    app = IncomeTrackerApp(root)
    app.record_item_var.set("修炼果")
    app.quantity_var.set("2")
    root.update()
    root.update_idletasks()

    if app.quick_entry_panel is None:
        raise AssertionError("expected UI frames were not initialized")

    assert_childs_fit(app.quick_entry_panel, "quick_entry_panel")

    tab_heights = {button.winfo_height() for button in app.summary_tab_buttons.values()}
    if len(tab_heights) != 1:
        raise AssertionError(f"summary tab heights differ: {sorted(tab_heights)}")
    if not app.selected_price_var.get().startswith("单价："):
        raise AssertionError(f"price label unexpected: {app.selected_price_var.get()}")
    if "元" not in app.selected_today_cash_var.get():
        raise AssertionError(f"today cash missing: {app.selected_today_cash_var.get()}")
    if "元" not in app.today_summary_var.get():
        raise AssertionError(f"summary cash missing: {app.today_summary_var.get()}")

    print(
        "UI smoke passed: "
        f"quick_entry={app.quick_entry_panel.winfo_width()}x{app.quick_entry_panel.winfo_height()}, "
        f"tab_heights={sorted(tab_heights)}, "
        f"today_summary={app.today_summary_var.get()}"
    )
    root.destroy()


if __name__ == "__main__":
    main()

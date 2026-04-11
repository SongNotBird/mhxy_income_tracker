from __future__ import annotations

import csv
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    TK_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    tk = None
    filedialog = None
    messagebox = None
    ttk = None
    TK_IMPORT_ERROR = exc


APP_TITLE = "梦幻西游收益统计"
DEFAULT_WINDOW_WIDTH = 1320
DEFAULT_WINDOW_HEIGHT = 830
MANAGE_WINDOW_WIDTH = 920
MANAGE_WINDOW_HEIGHT = 640
PRESET_WINDOW_WIDTH = 760
PRESET_WINDOW_HEIGHT = 620
DATA_FILE_ENV = "MHXY_INCOME_TRACKER_DATA_FILE"
SCHEMA_VERSION = 3
PRESET_ITEMS = [
    {"name": "金柳露", "tag": "召唤兽", "note": "抓鬼/副本常见"},
    {"name": "超级金柳露", "tag": "召唤兽", "note": "活动/积分常见"},
    {"name": "月华露", "tag": "召唤兽", "note": "商人常收"},
    {"name": "炼妖石", "tag": "召唤兽", "note": "召唤兽培养"},
    {"name": "魔兽要诀", "tag": "召唤兽", "note": "副本/挖图常见"},
    {"name": "高级魔兽要诀", "tag": "召唤兽", "note": "高宝图/活动"},
    {"name": "强化石", "tag": "打造", "note": "商人常收"},
    {"name": "宝石", "tag": "打造", "note": "商人常收"},
    {"name": "星辉石", "tag": "打造", "note": "打造消耗"},
    {"name": "符石", "tag": "打造", "note": "副本/日常常见"},
    {"name": "藏宝图", "tag": "日常", "note": "日常流通"},
    {"name": "高级藏宝图", "tag": "活动", "note": "五宝兑换/挖图"},
    {"name": "摇钱树苗", "tag": "活动", "note": "消耗量大"},
    {"name": "修炼果", "tag": "日常", "note": "副本/活动常见"},
    {"name": "九转金丹", "tag": "日常", "note": "日常奖励"},
    {"name": "如意丹", "tag": "日常", "note": "商人常收"},
    {"name": "彩果", "tag": "活动", "note": "商人常收"},
    {"name": "特赦令牌", "tag": "活动", "note": "副本/五宝兑换"},
    {"name": "金刚石", "tag": "五宝", "note": "五宝"},
    {"name": "定魂珠", "tag": "五宝", "note": "五宝"},
    {"name": "龙鳞", "tag": "五宝", "note": "五宝"},
    {"name": "夜光珠", "tag": "五宝", "note": "五宝"},
    {"name": "避水珠", "tag": "五宝", "note": "五宝"},
]
APP_BG = "#efe6d2"
SURFACE_BG = "#f8f2e5"
CARD_BG = "#fffaf0"
HERO_BG = "#f6edd7"
FIELD_BG = "#fffdf8"
ACCENT_BLUE = "#3f6f78"
ACCENT_BLUE_HOVER = "#355f67"
ACCENT_GOLD = "#c58a2b"
ACCENT_GOLD_LIGHT = "#f8edd4"
ACCENT_JADE = "#4e8b63"
ACCENT_JADE_HOVER = "#407252"
BORDER_COLOR = "#c8b79b"
TEXT_COLOR = "#35271a"
MUTED_TEXT = "#6f6255"
SELECT_BG = "#f3e6bc"


def clamp_window_size(widget, width: int, height: int) -> tuple[int, int, int, int]:
    screen_width = widget.winfo_screenwidth()
    screen_height = widget.winfo_screenheight()
    final_width = min(width, max(960, screen_width - 80))
    final_height = min(height, max(680, screen_height - 110))
    pos_x = max(20, (screen_width - final_width) // 2)
    pos_y = max(20, (screen_height - final_height) // 2)
    return final_width, final_height, pos_x, pos_y


def get_data_file() -> Path:
    override = os.environ.get(DATA_FILE_ENV)
    if override:
        file_path = Path(override).expanduser()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            base_dir = Path(appdata)
        else:
            base_dir = Path.home() / "AppData" / "Roaming"
        data_dir = base_dir / "MHXYIncomeTracker"
    else:
        data_dir = Path.home() / ".mhxy_income_tracker"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "data.json"


DATA_FILE = get_data_file()


def current_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def format_number(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def format_coin(value: float) -> str:
    return f"{format_number(value)} 梦幻币"


def format_cash(value: float) -> str:
    return f"{format_number(value)} 元"


def format_time_label(value: str) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    return dt.strftime("%m-%d %H:%M")


def parse_positive_number(value: str, field_name: str) -> float:
    normalized = value.strip().replace(",", "")
    if not normalized:
        raise ValueError(f"{field_name}不能为空。")

    try:
        number = float(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name}必须是数字。") from exc

    if number <= 0:
        raise ValueError(f"{field_name}必须大于 0。")
    return number


def parse_positive_int(value: str, field_name: str) -> int:
    number = parse_positive_number(value, field_name)
    if not float(number).is_integer():
        raise ValueError(f"{field_name}必须是整数。")
    return int(number)


class DataStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.data = self._load()

    def _default_data(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "items": {},
            "exchange_rate": {
                "cash": 100.0,
                "coin": 15000000.0,
            },
            "records": [],
        }

    def _load(self) -> dict:
        if not self.file_path.exists():
            data = self._default_data()
            self._save(data)
            return data

        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
        except (json.JSONDecodeError, OSError):
            loaded = self._default_data()

        normalized = self._normalize_loaded_data(loaded)
        if normalized != loaded:
            self._save(normalized)
        return normalized

    def _normalize_loaded_data(self, loaded: dict) -> dict:
        version = int(loaded.get("schema_version", 1))
        if version >= 3:
            return self._normalize_v3_data(loaded)
        if version == 2:
            return self._migrate_v2_data(loaded)
        return self._migrate_legacy_data(loaded)

    def _normalize_v3_data(self, loaded: dict) -> dict:
        data = self._default_data()
        exchange_rate = loaded.get("exchange_rate", {})
        data["exchange_rate"]["cash"] = float(exchange_rate.get("cash", 100.0))
        data["exchange_rate"]["coin"] = float(exchange_rate.get("coin", 15000000.0))

        raw_items = loaded.get("items", {})
        normalized_items: Dict[str, dict] = {}
        if isinstance(raw_items, dict):
            for name, item in raw_items.items():
                item_name = str(name).strip()
                if not item_name:
                    continue
                if isinstance(item, dict):
                    price = float(item.get("price", 0))
                    tag = str(item.get("tag", "")).strip()
                    updated_at = str(item.get("updated_at", ""))
                else:
                    price = float(item)
                    tag = ""
                    updated_at = ""
                normalized_items[item_name] = {
                    "price": price,
                    "tag": tag,
                    "updated_at": updated_at,
                }
        data["items"] = normalized_items

        normalized_records: List[dict] = []
        for record in loaded.get("records", []):
            item_name = str(record.get("item_name", "")).strip()
            if not item_name:
                continue
            quantity = int(float(record.get("quantity", 0)))
            price_snapshot = float(
                record.get("price_snapshot", record.get("price", 0))
            )
            subtotal = float(record.get("subtotal", price_snapshot * quantity))
            created_at = str(record.get("created_at", ""))
            normalized_records.append(
                {
                    "id": str(record.get("id", uuid.uuid4().hex)),
                    "date": str(record.get("date", "")),
                    "time": str(record.get("time", "")),
                    "created_at": created_at,
                    "updated_at": str(record.get("updated_at", created_at)),
                    "item_name": item_name,
                    "price_snapshot": price_snapshot,
                    "quantity": quantity,
                    "subtotal": subtotal,
                }
            )

        data["records"] = normalized_records
        return data

    def _migrate_v2_data(self, loaded: dict) -> dict:
        data = self._default_data()
        exchange_rate = loaded.get("exchange_rate", {})
        data["exchange_rate"]["cash"] = float(exchange_rate.get("cash", 100.0))
        data["exchange_rate"]["coin"] = float(exchange_rate.get("coin", 15000000.0))

        raw_items = loaded.get("items", {})
        items: Dict[str, dict] = {}
        if isinstance(raw_items, dict):
            for name, item in raw_items.items():
                item_name = str(name).strip()
                if not item_name:
                    continue
                if isinstance(item, dict):
                    price = float(item.get("price", 0))
                    updated_at = str(item.get("updated_at", ""))
                else:
                    price = float(item)
                    updated_at = ""
                items[item_name] = {
                    "price": price,
                    "tag": "",
                    "updated_at": updated_at,
                }

        records: List[dict] = []
        for record in loaded.get("records", []):
            item_name = str(record.get("item_name", "")).strip()
            if not item_name:
                continue
            created_at = str(record.get("created_at", ""))
            records.append(
                {
                    "id": str(record.get("id", uuid.uuid4().hex)),
                    "date": str(record.get("date", "")),
                    "time": str(record.get("time", "")),
                    "created_at": created_at,
                    "updated_at": str(record.get("updated_at", created_at)),
                    "item_name": item_name,
                    "price_snapshot": float(
                        record.get("price_snapshot", record.get("price", 0))
                    ),
                    "quantity": int(float(record.get("quantity", 0))),
                    "subtotal": float(record.get("subtotal", 0)),
                }
            )

        data["items"] = items
        data["records"] = records
        return data

    def _migrate_legacy_data(self, loaded: dict) -> dict:
        data = self._default_data()
        exchange_rate = loaded.get("exchange_rate", {})
        data["exchange_rate"]["cash"] = float(exchange_rate.get("cash", 100.0))
        data["exchange_rate"]["coin"] = float(exchange_rate.get("coin", 1500.0)) * 10000

        legacy_records = loaded.get("records", [])
        normalized_records: List[dict] = []
        items: Dict[str, dict] = {}

        ordered_records = sorted(
            legacy_records,
            key=lambda item: str(
                item.get(
                    "created_at",
                    f"{item.get('date', '')}T{item.get('time', '')}",
                )
            ),
        )

        for record in ordered_records:
            item_name = str(record.get("item_name", "")).strip()
            if not item_name:
                continue

            quantity = int(float(record.get("quantity", 0)))
            price_snapshot = float(record.get("price", 0)) * 10000
            subtotal = float(record.get("subtotal", 0)) * 10000
            if subtotal <= 0:
                subtotal = price_snapshot * quantity

            created_at = str(record.get("created_at", ""))
            normalized_records.append(
                {
                    "id": str(record.get("id", uuid.uuid4().hex)),
                    "date": str(record.get("date", "")),
                    "time": str(record.get("time", "")),
                    "created_at": created_at,
                    "updated_at": created_at,
                    "item_name": item_name,
                    "price_snapshot": price_snapshot,
                    "quantity": quantity,
                    "subtotal": subtotal,
                }
            )
            items[item_name] = {
                "price": price_snapshot,
                "tag": "",
                "updated_at": created_at,
            }

        for item_name in loaded.get("item_names", []):
            normalized_name = str(item_name).strip()
            if not normalized_name:
                continue
            items.setdefault(
                normalized_name,
                {
                    "price": 0.0,
                    "tag": "",
                    "updated_at": "",
                },
            )

        data["items"] = items
        data["records"] = normalized_records
        return data

    def _save(self, data: Optional[dict] = None) -> None:
        if data is not None:
            self.data = data

        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=2)

    def get_items(self) -> List[dict]:
        items = []
        for item_name, item in self.data["items"].items():
            items.append(
                {
                    "name": item_name,
                    "price": float(item.get("price", 0)),
                    "tag": str(item.get("tag", "")).strip(),
                    "updated_at": str(item.get("updated_at", "")),
                }
            )
        return sorted(items, key=lambda item: item["name"])

    def get_item_names(self) -> List[str]:
        return [item["name"] for item in self.get_items()]

    def get_tags(self) -> List[str]:
        tags = sorted(
            {
                item["tag"]
                for item in self.get_items()
                if str(item.get("tag", "")).strip()
            }
        )
        return tags

    def get_item(self, item_name: str) -> Optional[dict]:
        normalized = item_name.strip()
        if not normalized:
            return None
        item = self.data["items"].get(normalized)
        if item is None:
            return None
        return {
            "name": normalized,
            "price": float(item.get("price", 0)),
            "tag": str(item.get("tag", "")).strip(),
            "updated_at": str(item.get("updated_at", "")),
        }

    def add_item(self, item_name: str, price: int, tag: str = "") -> None:
        normalized = item_name.strip()
        if normalized in self.data["items"]:
            raise ValueError("这个道具已经存在，请用“更新价格”。")

        self.data["items"][normalized] = {
            "price": int(price),
            "tag": tag.strip(),
            "updated_at": current_timestamp(),
        }
        self._save()

    def update_item(self, item_name: str, price: int, tag: str = "") -> None:
        normalized = item_name.strip()
        if normalized not in self.data["items"]:
            raise ValueError("这个道具不存在，请先新增。")

        self.data["items"][normalized]["price"] = int(price)
        self.data["items"][normalized]["tag"] = tag.strip()
        self.data["items"][normalized]["updated_at"] = current_timestamp()
        self._save()

    def get_available_preset_items(self) -> List[dict]:
        existing_names = set(self.data["items"])
        available: List[dict] = []
        for preset in PRESET_ITEMS:
            item_name = str(preset.get("name", "")).strip()
            if not item_name or item_name in existing_names:
                continue
            available.append(
                {
                    "name": item_name,
                    "tag": str(preset.get("tag", "")).strip(),
                    "note": str(preset.get("note", "")).strip(),
                }
            )
        return available

    def add_preset_item(self, item_name: str) -> dict:
        normalized = item_name.strip()
        if not normalized:
            raise ValueError("常用道具名不能为空。")
        if normalized in self.data["items"]:
            raise ValueError("这个道具已经在你的道具库里了。")

        preset = next(
            (
                item
                for item in PRESET_ITEMS
                if str(item.get("name", "")).strip() == normalized
            ),
            None,
        )
        if preset is None:
            raise ValueError("没找到这个常用道具模板。")

        self.data["items"][normalized] = {
            "price": 0,
            "tag": str(preset.get("tag", "")).strip(),
            "updated_at": current_timestamp(),
        }
        self._save()
        return {
            "name": normalized,
            "tag": str(preset.get("tag", "")).strip(),
            "note": str(preset.get("note", "")).strip(),
        }

    def get_exchange_rate(self) -> dict:
        return dict(self.data["exchange_rate"])

    def set_exchange_rate(self, cash: float, coin: int) -> None:
        self.data["exchange_rate"] = {
            "cash": cash,
            "coin": int(coin),
        }
        self._save()

    def get_records(self) -> List[dict]:
        return list(self.data["records"])

    def add_record(self, item_name: str, quantity: int) -> dict:
        item = self.get_item(item_name)
        if item is None:
            raise ValueError("请先在道具库中新增这个道具。")
        if item["price"] <= 0:
            raise ValueError("这个道具还没有有效单价，请先更新价格。")

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_price = int(item["price"])

        for record in reversed(self.data["records"]):
            if (
                str(record.get("date", "")) == today
                and str(record.get("item_name", "")).strip() == item["name"]
                and int(float(record.get("price_snapshot", 0))) == current_price
            ):
                record["quantity"] = int(record.get("quantity", 0)) + int(quantity)
                record["subtotal"] = float(record.get("subtotal", 0)) + current_price * int(
                    quantity
                )
                record["time"] = now.strftime("%H:%M:%S")
                record["updated_at"] = now.isoformat(timespec="seconds")
                self._save()
                return dict(record)

        record = {
            "id": uuid.uuid4().hex,
            "date": today,
            "time": now.strftime("%H:%M:%S"),
            "created_at": now.isoformat(timespec="seconds"),
            "updated_at": now.isoformat(timespec="seconds"),
            "item_name": item["name"],
            "price_snapshot": current_price,
            "quantity": int(quantity),
            "subtotal": current_price * int(quantity),
        }
        self.data["records"].append(record)
        self._save()
        return record

    def delete_record(self, record_id: str) -> bool:
        before_count = len(self.data["records"])
        self.data["records"] = [
            record for record in self.data["records"] if record.get("id") != record_id
        ]
        changed = len(self.data["records"]) != before_count
        if changed:
            self._save()
        return changed


class IncomeTrackerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.store = DataStore(DATA_FILE)

        self.record_item_var = tk.StringVar()
        self.quantity_var = tk.StringVar(value="1")
        self.manage_item_var = tk.StringVar()
        self.manage_price_var = tk.StringVar()
        self.manage_tag_var = tk.StringVar()
        self.filter_text_var = tk.StringVar()
        self.filter_tag_var = tk.StringVar(value="全部")
        self.preset_filter_var = tk.StringVar()
        self.cash_ratio_var = tk.StringVar()
        self.coin_ratio_var = tk.StringVar()
        self.selected_item_name_var = tk.StringVar(value="请先从左侧选择道具")
        self.selected_price_var = tk.StringVar(value="未选择道具")
        self.selected_tag_var = tk.StringVar(value="-")
        self.selected_today_qty_var = tk.StringVar(value="0")
        self.selected_today_coin_var = tk.StringVar(value="0 梦幻币")
        self.selected_estimated_coin_var = tk.StringVar(value="0 梦幻币")
        self.status_var = tk.StringVar(value="准备就绪")
        self.today_total_coin_var = tk.StringVar(value="0 梦幻币")
        self.today_total_cash_var = tk.StringVar(value="0 元")
        self.total_coin_var = tk.StringVar(value="0 梦幻币")
        self.total_cash_var = tk.StringVar(value="0 元")
        self.rate_hint_var = tk.StringVar(value="")
        self.trend_tip_var = tk.StringVar(value="最近 7 天按天统计梦幻币总额")

        self.today_record_ids: Dict[str, str] = {}
        self.latest_records_cache: List[dict] = []
        self.manage_window: Optional[tk.Toplevel] = None
        self.manage_tree: Optional[ttk.Treeview] = None
        self.preset_window: Optional[tk.Toplevel] = None
        self.preset_tree: Optional[ttk.Treeview] = None

        self._configure_window()
        self._build_ui()
        self._load_saved_state()
        self.refresh_views()

        self.record_item_var.trace_add("write", self._on_record_item_changed)
        self.quantity_var.trace_add("write", self._on_quantity_changed)
        self.filter_text_var.trace_add("write", self._on_catalog_filter_changed)
        self.filter_tag_var.trace_add("write", self._on_catalog_filter_changed)
        self.preset_filter_var.trace_add("write", self._on_preset_filter_changed)

    def _configure_window(self) -> None:
        self.root.title(APP_TITLE)
        width, height, pos_x, pos_y = clamp_window_size(
            self.root, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
        )
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        self.root.resizable(False, False)
        self.root.configure(bg=APP_BG)

        style = ttk.Style()
        available_themes = style.theme_names()
        if "clam" in available_themes:
            style.theme_use("clam")

        style.configure(
            ".",
            background=APP_BG,
            foreground=TEXT_COLOR,
            font=("Microsoft YaHei UI", 10),
        )
        style.configure("TFrame", background=APP_BG)
        style.configure("TLabel", background=SURFACE_BG, foreground=TEXT_COLOR)
        style.configure("App.TFrame", background=APP_BG)
        style.configure("Surface.TFrame", background=SURFACE_BG)
        style.configure(
            "Card.TFrame",
            background=CARD_BG,
            borderwidth=1,
            relief="solid",
            bordercolor=BORDER_COLOR,
            padding=14,
        )
        style.configure(
            "Hero.TFrame",
            background=HERO_BG,
            borderwidth=1,
            relief="solid",
            bordercolor=ACCENT_GOLD,
            padding=16,
        )
        style.configure(
            "Panel.TLabelframe",
            background=SURFACE_BG,
            borderwidth=1,
            relief="solid",
            bordercolor=BORDER_COLOR,
        )
        style.configure(
            "Panel.TLabelframe.Label",
            background=SURFACE_BG,
            foreground=TEXT_COLOR,
            font=("Microsoft YaHei UI", 11, "bold"),
        )
        style.configure(
            "Header.TLabel",
            background=APP_BG,
            foreground=TEXT_COLOR,
            font=("Microsoft YaHei UI", 24, "bold"),
        )
        style.configure(
            "HeaderSub.TLabel",
            background=APP_BG,
            foreground=MUTED_TEXT,
            font=("Microsoft YaHei UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=CARD_BG,
            foreground=MUTED_TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.configure(
            "HeroTitle.TLabel",
            background=HERO_BG,
            foreground=MUTED_TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.configure(
            "HeroName.TLabel",
            background=HERO_BG,
            foreground=ACCENT_BLUE,
            font=("Microsoft YaHei UI", 20, "bold"),
        )
        style.configure(
            "HeroPrice.TLabel",
            background=HERO_BG,
            foreground=ACCENT_JADE,
            font=("Microsoft YaHei UI", 18, "bold"),
        )
        style.configure(
            "BigValue.TLabel",
            background=CARD_BG,
            foreground=TEXT_COLOR,
            font=("Microsoft YaHei UI", 18, "bold"),
        )
        style.configure(
            "EstimateLabel.TLabel",
            background=ACCENT_GOLD_LIGHT,
            foreground="#93601c",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.configure(
            "EstimateValue.TLabel",
            background=ACCENT_GOLD_LIGHT,
            foreground="#b06b12",
            font=("Microsoft YaHei UI", 18, "bold"),
        )
        style.configure(
            "Subtle.TLabel",
            background=APP_BG,
            foreground=MUTED_TEXT,
            font=("Microsoft YaHei UI", 10),
        )
        style.configure(
            "CardSubtle.TLabel",
            background=CARD_BG,
            foreground=MUTED_TEXT,
            font=("Microsoft YaHei UI", 10),
        )
        style.configure(
            "Surface.TLabel",
            background=SURFACE_BG,
            foreground=TEXT_COLOR,
            font=("Microsoft YaHei UI", 10),
        )
        style.configure(
            "HeroSubtle.TLabel",
            background=HERO_BG,
            foreground=MUTED_TEXT,
            font=("Microsoft YaHei UI", 10),
        )
        style.configure(
            "Estimate.TFrame",
            background=ACCENT_GOLD_LIGHT,
            borderwidth=1,
            relief="solid",
            bordercolor=ACCENT_GOLD,
            padding=10,
        )
        style.configure(
            "TLabelframe",
            background=SURFACE_BG,
            bordercolor=BORDER_COLOR,
        )
        style.configure(
            "TLabelframe.Label",
            background=SURFACE_BG,
            foreground=TEXT_COLOR,
            font=("Microsoft YaHei UI", 11, "bold"),
        )
        style.configure(
            "TButton",
            background="#f4edde",
            foreground=TEXT_COLOR,
            bordercolor=BORDER_COLOR,
            focusthickness=0,
            focuscolor=FIELD_BG,
            padding=(10, 6),
            relief="solid",
        )
        style.map(
            "TButton",
            background=[("active", "#efe2c8")],
            bordercolor=[("active", ACCENT_GOLD)],
        )
        style.configure(
            "Primary.TButton",
            background=ACCENT_BLUE,
            foreground="#ffffff",
            bordercolor=ACCENT_BLUE,
            padding=(12, 7),
        )
        style.map(
            "Primary.TButton",
            background=[("active", ACCENT_BLUE_HOVER)],
            foreground=[("active", "#ffffff")],
        )
        style.configure(
            "Success.TButton",
            background=ACCENT_JADE,
            foreground="#ffffff",
            bordercolor=ACCENT_JADE,
            padding=(12, 7),
        )
        style.map(
            "Success.TButton",
            background=[("active", ACCENT_JADE_HOVER)],
            foreground=[("active", "#ffffff")],
        )
        style.configure(
            "Quick.TButton",
            background="#fff7e8",
            foreground="#704b1b",
            bordercolor=ACCENT_GOLD,
            padding=(8, 4),
        )
        style.map(
            "Quick.TButton",
            background=[("active", "#f6ead0")],
        )
        style.configure(
            "Treeview",
            background=FIELD_BG,
            fieldbackground=FIELD_BG,
            foreground=TEXT_COLOR,
            bordercolor=BORDER_COLOR,
            rowheight=30,
            relief="flat",
            borderwidth=1,
        )
        style.map(
            "Treeview",
            background=[("selected", SELECT_BG)],
            foreground=[("selected", TEXT_COLOR)],
        )
        style.configure(
            "Treeview.Heading",
            background="#ecdfc2",
            foreground="#5b4528",
            bordercolor=BORDER_COLOR,
            relief="flat",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#e1d1af")],
        )
        style.configure(
            "TEntry",
            fieldbackground=FIELD_BG,
            foreground=TEXT_COLOR,
            bordercolor=BORDER_COLOR,
            insertcolor=TEXT_COLOR,
        )
        style.configure(
            "TCombobox",
            fieldbackground=FIELD_BG,
            background=FIELD_BG,
            foreground=TEXT_COLOR,
            bordercolor=BORDER_COLOR,
            arrowcolor=ACCENT_BLUE,
        )
        style.configure("TNotebook", background=APP_BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#e7d9bc",
            foreground="#634d33",
            padding=(16, 8),
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#f7edd8"), ("active", "#f0e0be")],
            foreground=[("selected", TEXT_COLOR)],
        )

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=5)
        self.root.rowconfigure(3, weight=4)

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(20, 18, 20, 10), style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text=APP_TITLE,
            style="Header.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=f"数据保存位置：{DATA_FILE}",
            style="HeaderSub.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        toolbar = ttk.Frame(self.root, padding=(20, 0, 20, 10), style="App.TFrame")
        toolbar.grid(row=1, column=0, sticky="ew")
        self._build_toolbar(toolbar)

        main = ttk.Frame(self.root, padding=(20, 0, 20, 10), style="App.TFrame")
        main.grid(row=2, column=0, sticky="nsew")
        main.columnconfigure(0, weight=7)
        main.columnconfigure(1, weight=5)
        main.rowconfigure(0, weight=1)

        self._build_catalog_panel(main)
        self._build_quick_entry_panel(main)

        notebook = ttk.Notebook(self.root)
        notebook.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 10))

        today_tab = ttk.Frame(notebook, padding=14)
        total_tab = ttk.Frame(notebook, padding=14)
        trend_tab = ttk.Frame(notebook, padding=14)
        notebook.add(today_tab, text="当日记录")
        notebook.add(total_tab, text="总统计")
        notebook.add(trend_tab, text="收益趋势")

        self._build_today_table(today_tab)
        self._build_total_table(total_tab)
        self._build_trend_panel(trend_tab)

        footer = ttk.Frame(self.root, padding=(20, 0, 20, 18), style="App.TFrame")
        footer.grid(row=4, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Subtle.TLabel").grid(
            row=0, column=0, sticky="w"
        )

    def _build_toolbar(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(3, weight=1)

        ttk.Label(parent, text="搜索道具").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=self.filter_text_var).grid(
            row=0, column=1, sticky="ew", padx=(10, 16), pady=4
        )

        ttk.Label(parent, text="标签").grid(row=0, column=2, sticky="w", pady=4)
        self.filter_tag_combo = ttk.Combobox(
            parent,
            textvariable=self.filter_tag_var,
            state="readonly",
        )
        self.filter_tag_combo.grid(row=0, column=3, sticky="ew", padx=(10, 16), pady=4)

        ttk.Button(
            parent,
            text="道具价格管理",
            command=self.open_manage_window,
            style="Primary.TButton",
        ).grid(
            row=0, column=4, padx=(0, 8), pady=4
        )
        ttk.Button(
            parent,
            text="添加常用道具",
            command=self.open_preset_window,
            style="Success.TButton",
        ).grid(
            row=0, column=5, padx=(0, 8), pady=4
        )
        ttk.Button(parent, text="导出 CSV", command=self.export_report).grid(
            row=0, column=6, pady=4
        )

    def _build_catalog_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Labelframe(parent, text="每日道具列表", padding=14, style="Panel.TLabelframe")
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        ttk.Label(
            panel,
            text="主流程放这里：先点左边道具，再去右边输数量。价格和标签只在需要时打开“道具价格管理”调整。",
            style="Surface.TLabel",
            wraplength=620,
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        columns = ("item_name", "tag")
        self.item_tree = ttk.Treeview(
            panel,
            columns=columns,
            show="headings",
            height=18,
            selectmode="browse",
        )
        headers = {
            "item_name": "道具名",
            "tag": "标签",
        }
        widths = {
            "item_name": 360,
            "tag": 160,
        }
        for column in columns:
            self.item_tree.heading(column, text=headers[column])
            self.item_tree.column(column, width=widths[column], anchor="center")

        self.item_tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=self.item_tree.yview)
        self.item_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns")
        self.item_tree.bind("<<TreeviewSelect>>", self._on_item_tree_select)

    def _build_quick_entry_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Labelframe(parent, text="每日录入", padding=16, style="Panel.TLabelframe")
        panel.grid(row=0, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        hero = ttk.Frame(panel, style="Hero.TFrame")
        hero.grid(row=0, column=0, columnspan=2, sticky="ew")
        hero.columnconfigure(0, weight=1)
        ttk.Label(hero, text="当前选中道具", style="HeroTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            hero,
            textvariable=self.selected_item_name_var,
            style="HeroName.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(8, 6))
        ttk.Label(
            hero,
            textvariable=self.selected_price_var,
            style="HeroPrice.TLabel",
        ).grid(row=2, column=0, sticky="w")
        ttk.Label(
            hero,
            text="左边点一下物品，右边只输数量就行。",
            style="HeroSubtle.TLabel",
        ).grid(row=3, column=0, sticky="w", pady=(4, 0))

        info = ttk.Frame(panel, style="Card.TFrame")
        info.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        info.columnconfigure(1, weight=1)
        info.columnconfigure(3, weight=1)
        ttk.Label(info, text="标签", style="CardSubtle.TLabel").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Label(info, textvariable=self.selected_tag_var, style="BigValue.TLabel").grid(
            row=0, column=1, sticky="w", padx=(10, 14), pady=6
        )
        ttk.Label(info, text="今日已录数量", style="CardSubtle.TLabel").grid(row=0, column=2, sticky="w", pady=6)
        ttk.Label(info, textvariable=self.selected_today_qty_var, style="BigValue.TLabel").grid(
            row=0, column=3, sticky="w", padx=(10, 0), pady=6
        )
        ttk.Label(info, text="今日已录收益", style="CardSubtle.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Label(info, textvariable=self.selected_today_coin_var, style="BigValue.TLabel").grid(
            row=1, column=1, columnspan=3, sticky="w", padx=(10, 0), pady=6
        )

        qty_frame = ttk.Frame(panel, style="Card.TFrame")
        qty_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        qty_frame.columnconfigure(1, weight=1)
        qty_frame.columnconfigure(3, weight=1)
        ttk.Label(qty_frame, text="本次数量", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.quantity_entry = ttk.Entry(qty_frame, textvariable=self.quantity_var)
        self.quantity_entry.grid(row=0, column=1, sticky="ew", padx=(10, 12))
        self.quantity_entry.bind("<Return>", lambda _event: self.save_record())
        ttk.Label(qty_frame, text="本次预计收益", style="CardTitle.TLabel").grid(
            row=0, column=2, sticky="w"
        )
        estimate_card = ttk.Frame(qty_frame, style="Estimate.TFrame")
        estimate_card.grid(row=0, column=3, sticky="ew", padx=(10, 0))
        estimate_card.columnconfigure(0, weight=1)
        ttk.Label(estimate_card, text="自动计算", style="EstimateLabel.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            estimate_card,
            textvariable=self.selected_estimated_coin_var,
            style="EstimateValue.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        quick_buttons = ttk.Frame(qty_frame, style="Card.TFrame")
        quick_buttons.grid(row=1, column=0, columnspan=4, sticky="w", pady=(12, 0))
        for index, amount in enumerate((1, 2, 5, 10, 20, 50)):
            ttk.Button(
                quick_buttons,
                text=str(amount),
                command=lambda value=amount: self.set_quantity_value(value),
                style="Quick.TButton",
                width=5,
            ).grid(row=0, column=index, padx=(0 if index == 0 else 8, 0))

        action_row = ttk.Frame(panel, style="Surface.TFrame")
        action_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(
            action_row,
            text="保存本次收获",
            command=self.save_record,
            style="Primary.TButton",
        ).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(action_row, text="清空数量", command=self.clear_quantity).grid(
            row=0, column=1, padx=8
        )
        ttk.Button(
            action_row,
            text="删除选中当日记录",
            command=self.delete_selected_record,
        ).grid(row=0, column=2, padx=(8, 0))

        stat_wrap = ttk.Frame(panel, style="Surface.TFrame")
        stat_wrap.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        stat_wrap.columnconfigure(0, weight=1)
        stat_wrap.columnconfigure(1, weight=1)
        self._create_stat_card(stat_wrap, 0, 0, "当日总梦幻币", self.today_total_coin_var)
        self._create_stat_card(stat_wrap, 0, 1, "当日总收益", self.today_total_cash_var)
        self._create_stat_card(stat_wrap, 1, 0, "累计总梦幻币", self.total_coin_var)
        self._create_stat_card(stat_wrap, 1, 1, "累计总收益", self.total_cash_var)

        rate_frame = ttk.Frame(panel, style="Card.TFrame")
        rate_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        rate_frame.columnconfigure(1, weight=1)
        rate_frame.columnconfigure(3, weight=1)
        ttk.Label(rate_frame, text="人民币比例（元）", style="CardSubtle.TLabel").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(rate_frame, textvariable=self.cash_ratio_var).grid(
            row=0, column=1, sticky="ew", padx=(10, 16), pady=6
        )
        ttk.Label(rate_frame, text="梦幻币比例", style="CardSubtle.TLabel").grid(row=0, column=2, sticky="w", pady=6)
        ttk.Entry(rate_frame, textvariable=self.coin_ratio_var).grid(
            row=0, column=3, sticky="ew", padx=(10, 0), pady=6
        )
        ttk.Label(rate_frame, textvariable=self.rate_hint_var, style="CardSubtle.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )
        ttk.Button(rate_frame, text="保存比例", command=self.save_exchange_rate).grid(
            row=1, column=3, sticky="e", pady=(4, 0)
        )

    def _build_trend_panel(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        panel = ttk.Frame(parent, style="Card.TFrame")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        ttk.Label(panel, text="最近 7 天收益趋势", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(panel, textvariable=self.trend_tip_var, style="CardSubtle.TLabel").grid(
            row=1, column=0, sticky="w", pady=(6, 10)
        )
        self.trend_canvas = tk.Canvas(
            panel,
            height=240,
            bg="#ffffff",
            highlightthickness=0,
        )
        self.trend_canvas.grid(row=2, column=0, sticky="nsew")
        self.trend_canvas.bind(
            "<Configure>",
            lambda _event: self._refresh_trend_chart(self.latest_records_cache),
        )

    def open_manage_window(self) -> None:
        if self.manage_window is not None and self.manage_window.winfo_exists():
            self.manage_window.deiconify()
            self.manage_window.lift()
            self.manage_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        width, height, pos_x, pos_y = clamp_window_size(
            window, MANAGE_WINDOW_WIDTH, MANAGE_WINDOW_HEIGHT
        )
        window.title("道具价格管理")
        window.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        window.resizable(False, False)
        window.configure(bg=APP_BG)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)
        window.protocol("WM_DELETE_WINDOW", self._close_manage_window)
        self.manage_window = window

        form = ttk.Frame(window, padding=16, style="App.TFrame")
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure(1, weight=2)
        form.columnconfigure(3, weight=2)
        form.columnconfigure(5, weight=1)

        ttk.Label(
            form,
            text="这里只在你需要新增道具或改单价时使用，平时录入不用一直盯着这个窗口。",
            style="HeaderSub.TLabel",
        ).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 10))

        ttk.Label(form, text="道具名").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.manage_item_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 16), pady=6
        )
        ttk.Label(form, text="单价（梦幻币）").grid(row=1, column=2, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.manage_price_var).grid(
            row=1, column=3, sticky="ew", padx=(10, 16), pady=6
        )
        ttk.Label(form, text="标签").grid(row=1, column=4, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.manage_tag_var).grid(
            row=1, column=5, sticky="ew", pady=6
        )

        buttons = ttk.Frame(form, style="App.TFrame")
        buttons.grid(row=2, column=0, columnspan=6, sticky="w", pady=(6, 0))
        ttk.Button(buttons, text="新增道具", command=self.add_item, style="Primary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="更新价格", command=self.update_item).grid(row=0, column=1, padx=8)
        ttk.Button(buttons, text="添加常用道具", command=self.open_preset_window, style="Success.TButton").grid(
            row=0, column=2, padx=8
        )
        ttk.Button(buttons, text="关闭", command=self._close_manage_window).grid(
            row=0, column=3, padx=(8, 0)
        )

        table_frame = ttk.Frame(window, padding=(16, 0, 16, 16), style="App.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("item_name", "tag", "price", "updated_at")
        self.manage_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        headers = {
            "item_name": "道具名",
            "tag": "标签",
            "price": "当前单价（梦幻币）",
            "updated_at": "最近修改",
        }
        widths = {
            "item_name": 220,
            "tag": 120,
            "price": 170,
            "updated_at": 140,
        }
        for column in columns:
            self.manage_tree.heading(column, text=headers[column])
            self.manage_tree.column(column, width=widths[column], anchor="center")

        self.manage_tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.manage_tree.yview)
        self.manage_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        self.manage_tree.bind("<<TreeviewSelect>>", self._on_manage_tree_select)

        self._refresh_manage_tree()

    def _close_manage_window(self) -> None:
        if self.manage_window is not None and self.manage_window.winfo_exists():
            self.manage_window.destroy()
        self.manage_window = None
        self.manage_tree = None

    def open_preset_window(self) -> None:
        if not self.store.get_available_preset_items():
            messagebox.showinfo("提示", "常用道具已经都加进你的道具库了。")
            return

        if self.preset_window is not None and self.preset_window.winfo_exists():
            self._refresh_preset_tree()
            self.preset_window.deiconify()
            self.preset_window.lift()
            self.preset_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        width, height, pos_x, pos_y = clamp_window_size(
            window, PRESET_WINDOW_WIDTH, PRESET_WINDOW_HEIGHT
        )
        window.title("添加常用道具")
        window.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        window.resizable(False, False)
        window.configure(bg=APP_BG)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)
        window.protocol("WM_DELETE_WINDOW", self._close_preset_window)
        self.preset_window = window
        self.preset_filter_var.set("")

        top = ttk.Frame(window, padding=16, style="App.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(
            top,
            text="这里只列常见流通道具，而且只显示你还没加入自己道具库的那些。",
            style="HeaderSub.TLabel",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Label(top, text="搜索").grid(row=1, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.preset_filter_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 12)
        )
        ttk.Button(top, text="清空", command=lambda: self.preset_filter_var.set("")).grid(
            row=1, column=2, sticky="e"
        )

        body = ttk.Frame(window, padding=(16, 0, 16, 16), style="App.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        columns = ("item_name", "tag", "note")
        self.preset_tree = ttk.Treeview(
            body,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        headers = {
            "item_name": "常用道具",
            "tag": "标签",
            "note": "常见来源",
        }
        widths = {
            "item_name": 240,
            "tag": 110,
            "note": 260,
        }
        for column in columns:
            self.preset_tree.heading(column, text=headers[column])
            self.preset_tree.column(column, width=widths[column], anchor="center")

        self.preset_tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.preset_tree.yview)
        self.preset_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        self.preset_tree.bind("<Double-1>", self._on_preset_tree_double_click)

        action_row = ttk.Frame(window, padding=(16, 0, 16, 16), style="App.TFrame")
        action_row.grid(row=2, column=0, sticky="ew")
        ttk.Button(
            action_row,
            text="加入道具库",
            command=self.add_selected_preset_item,
            style="Primary.TButton",
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(action_row, text="关闭", command=self._close_preset_window).grid(
            row=0, column=1
        )

        self._refresh_preset_tree()

    def _close_preset_window(self) -> None:
        if self.preset_window is not None and self.preset_window.winfo_exists():
            self.preset_window.destroy()
        self.preset_window = None
        self.preset_tree = None

    def _preset_matches_filter(self, preset: dict) -> bool:
        search_text = self.preset_filter_var.get().strip().lower()
        if not search_text:
            return True
        return any(
            search_text in str(preset.get(key, "")).lower()
            for key in ("name", "tag", "note")
        )

    def _refresh_preset_tree(self) -> None:
        if self.preset_tree is None:
            return

        for item_id in self.preset_tree.get_children():
            self.preset_tree.delete(item_id)

        for preset in self.store.get_available_preset_items():
            if not self._preset_matches_filter(preset):
                continue
            self.preset_tree.insert(
                "",
                tk.END,
                values=(
                    preset["name"],
                    preset["tag"] or "-",
                    preset["note"] or "-",
                ),
            )

    def _on_preset_filter_changed(self, *_args) -> None:
        self._refresh_preset_tree()

    def _on_preset_tree_double_click(self, _event) -> None:
        self.add_selected_preset_item()

    def add_selected_preset_item(self) -> None:
        if self.preset_tree is None:
            return

        selection = self.preset_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选中一个常用道具。")
            return

        values = self.preset_tree.item(selection[0], "values")
        if not values:
            return

        item_name = str(values[0]).strip()
        try:
            preset = self.store.add_preset_item(item_name)
        except ValueError as error:
            messagebox.showerror("操作失败", str(error))
            return

        self.manage_item_var.set(preset["name"])
        self.manage_price_var.set("")
        self.manage_tag_var.set(preset["tag"])
        self.record_item_var.set(preset["name"])
        self.refresh_views()
        self._refresh_preset_tree()
        self.status_var.set(
            f"已加入常用道具：{preset['name']}，请再给它补一个单价。"
        )

        if not self.store.get_available_preset_items():
            self._close_preset_window()

    def _refresh_manage_tree(self) -> None:
        if self.manage_tree is None or not self.manage_tree.winfo_exists():
            return
        current_item = self.manage_item_var.get().strip()
        selected_row = None

        for item_id in self.manage_tree.get_children():
            self.manage_tree.delete(item_id)

        for item in self.store.get_items():
            price_label = "未设置" if item["price"] <= 0 else format_number(item["price"])
            row_id = self.manage_tree.insert(
                "",
                tk.END,
                values=(
                    item["name"],
                    item["tag"] or "-",
                    price_label,
                    format_time_label(item["updated_at"]),
                ),
            )
            if item["name"] == current_item:
                selected_row = row_id

        if selected_row is not None:
            self.manage_tree.selection_set(selected_row)
            self.manage_tree.focus(selected_row)

    def _on_manage_tree_select(self, _event) -> None:
        if self.manage_tree is None:
            return
        selection = self.manage_tree.selection()
        if not selection:
            return

        values = self.manage_tree.item(selection[0], "values")
        if not values:
            return

        item_name = str(values[0])
        item = self.store.get_item(item_name)
        if item is None:
            return

        self.manage_item_var.set(item["name"])
        self.manage_price_var.set("" if item["price"] <= 0 else format_number(item["price"]))
        self.manage_tag_var.set(item["tag"])

    def _build_item_manage_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Labelframe(parent, text="道具库与价格管理", padding=14)
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        panel.columnconfigure(1, weight=2)
        panel.columnconfigure(3, weight=2)
        panel.columnconfigure(5, weight=1)
        panel.rowconfigure(4, weight=1)

        ttk.Label(
            panel,
            text="对标参考工具补了道具库浏览、标签分类和搜索筛选，方便你快速找到常用道具。",
            style="Subtle.TLabel",
            wraplength=560,
        ).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 10))

        ttk.Label(panel, text="搜索").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(panel, textvariable=self.filter_text_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 16), pady=6
        )

        ttk.Label(panel, text="标签筛选").grid(row=1, column=2, sticky="w", pady=6)
        self.filter_tag_combo = ttk.Combobox(
            panel,
            textvariable=self.filter_tag_var,
            state="readonly",
        )
        self.filter_tag_combo.grid(
            row=1, column=3, sticky="ew", padx=(10, 16), pady=6
        )
        ttk.Button(panel, text="清空筛选", command=self.clear_catalog_filters).grid(
            row=1, column=4, columnspan=2, sticky="ew", pady=6
        )

        ttk.Label(panel, text="道具名").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(panel, textvariable=self.manage_item_var).grid(
            row=2, column=1, sticky="ew", padx=(10, 16), pady=6
        )

        ttk.Label(panel, text="单价（梦幻币）").grid(row=2, column=2, sticky="w", pady=6)
        ttk.Entry(panel, textvariable=self.manage_price_var).grid(
            row=2, column=3, sticky="ew", padx=(10, 16), pady=6
        )

        ttk.Label(panel, text="标签").grid(row=2, column=4, sticky="w", pady=6)
        ttk.Entry(panel, textvariable=self.manage_tag_var).grid(
            row=2, column=5, sticky="ew", pady=6
        )

        button_row = ttk.Frame(panel)
        button_row.grid(row=3, column=0, columnspan=6, sticky="ew", pady=(4, 10))
        ttk.Button(button_row, text="新增道具", command=self.add_item).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(button_row, text="更新价格", command=self.update_item).grid(
            row=0, column=1, padx=8
        )
        ttk.Button(
            button_row,
            text="载入选中道具",
            command=self.load_selected_item_to_form,
        ).grid(row=0, column=2, padx=8)
        ttk.Button(
            button_row,
            text="添加常用道具",
            command=self.import_preset_items,
        ).grid(row=0, column=3, padx=(8, 0))

        columns = ("item_name", "tag", "price", "updated_at")
        self.item_tree = ttk.Treeview(
            panel,
            columns=columns,
            show="headings",
            height=10,
            selectmode="browse",
        )
        headers = {
            "item_name": "道具名",
            "tag": "标签",
            "price": "当前单价（梦幻币）",
            "updated_at": "最近修改",
        }
        widths = {
            "item_name": 180,
            "tag": 110,
            "price": 150,
            "updated_at": 120,
        }
        for column in columns:
            self.item_tree.heading(column, text=headers[column])
            self.item_tree.column(column, width=widths[column], anchor="center")

        self.item_tree.grid(row=4, column=0, columnspan=6, sticky="nsew")
        scroll = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=self.item_tree.yview)
        self.item_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=4, column=6, sticky="ns")
        self.item_tree.bind("<<TreeviewSelect>>", self._on_item_tree_select)

    def _build_summary_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent)
        panel.grid(row=0, column=2, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

        self._create_stat_card(panel, 0, 0, "当日总梦幻币", self.today_total_coin_var)
        self._create_stat_card(panel, 0, 1, "当日总收益", self.today_total_cash_var)
        self._create_stat_card(panel, 1, 0, "累计总梦幻币", self.total_coin_var)
        self._create_stat_card(panel, 1, 1, "累计总收益", self.total_cash_var)

        rate_frame = ttk.Frame(panel, style="Card.TFrame")
        rate_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        ttk.Label(rate_frame, text="当前换算比例", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(rate_frame, textvariable=self.rate_hint_var).grid(
            row=1, column=0, sticky="w", pady=(8, 10)
        )
        ttk.Button(rate_frame, text="导出 CSV（Excel 可打开）", command=self.export_report).grid(
            row=2, column=0, sticky="w"
        )

        trend_frame = ttk.Frame(panel, style="Card.TFrame")
        trend_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        trend_frame.columnconfigure(0, weight=1)
        ttk.Label(trend_frame, text="最近 7 天收益趋势", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(trend_frame, textvariable=self.trend_tip_var, style="Subtle.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 10)
        )
        self.trend_canvas = tk.Canvas(
            trend_frame,
            height=200,
            bg="#ffffff",
            highlightthickness=0,
        )
        self.trend_canvas.grid(row=2, column=0, sticky="ew")
        self.trend_canvas.bind(
            "<Configure>",
            lambda _event: self._refresh_trend_chart(self.latest_records_cache),
        )

    def _create_stat_card(
        self,
        parent: ttk.Frame,
        row: int,
        column: int,
        title: str,
        value_var: tk.StringVar,
    ) -> None:
        card = ttk.Frame(parent, style="Card.TFrame")
        card.grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=(0 if column == 0 else 12, 0),
            pady=(0 if row == 0 else 12, 0),
        )
        parent.rowconfigure(row, weight=1)

        ttk.Label(card, text=title, style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(card, textvariable=value_var, style="BigValue.TLabel").grid(
            row=1, column=0, sticky="w", pady=(10, 0)
        )

    def _build_today_table(self, parent: ttk.Labelframe) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        columns = ("time", "item_name", "tag", "price", "quantity", "subtotal")
        self.today_tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=16,
            selectmode="browse",
        )
        headers = {
            "time": "最后记录时间",
            "item_name": "道具名",
            "tag": "标签",
            "price": "单价（梦幻币）",
            "quantity": "数量",
            "subtotal": "小计（梦幻币）",
        }
        widths = {
            "time": 120,
            "item_name": 150,
            "tag": 90,
            "price": 130,
            "quantity": 70,
            "subtotal": 140,
        }
        for column in columns:
            self.today_tree.heading(column, text=headers[column])
            self.today_tree.column(column, width=widths[column], anchor="center")

        scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.today_tree.yview)
        self.today_tree.configure(yscrollcommand=scroll.set)
        self.today_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

    def _build_total_table(self, parent: ttk.Labelframe) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        columns = (
            "item_name",
            "tag",
            "quantity",
            "current_price",
            "total_coin",
            "total_cash",
        )
        self.total_tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=16,
            selectmode="browse",
        )
        headers = {
            "item_name": "道具名",
            "tag": "标签",
            "quantity": "累计数量",
            "current_price": "当前单价（梦幻币）",
            "total_coin": "累计梦幻币",
            "total_cash": "折合人民币（元）",
        }
        widths = {
            "item_name": 140,
            "tag": 90,
            "quantity": 80,
            "current_price": 130,
            "total_coin": 130,
            "total_cash": 130,
        }
        for column in columns:
            self.total_tree.heading(column, text=headers[column])
            self.total_tree.column(column, width=widths[column], anchor="center")

        scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.total_tree.yview)
        self.total_tree.configure(yscrollcommand=scroll.set)
        self.total_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

    def _load_saved_state(self) -> None:
        exchange_rate = self.store.get_exchange_rate()
        self.cash_ratio_var.set(format_number(exchange_rate.get("cash", 100.0)))
        self.coin_ratio_var.set(format_number(exchange_rate.get("coin", 15000000.0)))

    def _on_record_item_changed(self, *_args) -> None:
        self._refresh_selected_item_details(self.latest_records_cache)

    def _on_quantity_changed(self, *_args) -> None:
        self._refresh_selected_item_details(self.latest_records_cache)

    def _on_catalog_filter_changed(self, *_args) -> None:
        self._refresh_item_catalog()

    def _sort_records(self, records: List[dict]) -> List[dict]:
        return sorted(
            records,
            key=lambda item: str(item.get("updated_at", item.get("created_at", ""))),
        )

    def _item_matches_filter(self, item: dict) -> bool:
        search_text = self.filter_text_var.get().strip().lower()
        filter_tag = self.filter_tag_var.get().strip()

        name = item["name"].lower()
        tag = str(item.get("tag", "")).strip()

        matches_search = not search_text or search_text in name or search_text in tag.lower()
        matches_tag = filter_tag in ("", "全部") or tag == filter_tag
        return matches_search and matches_tag

    def _refresh_item_catalog(self) -> None:
        item_names = self.store.get_item_names()
        current_item = self.record_item_var.get()

        if current_item and current_item in item_names:
            pass
        elif item_names:
            self.record_item_var.set(item_names[0])
        else:
            self.record_item_var.set("")

        current_filter_tag = self.filter_tag_var.get().strip() or "全部"
        tag_values = ["全部"] + self.store.get_tags()
        self.filter_tag_combo["values"] = tag_values
        if current_filter_tag not in tag_values:
            self.filter_tag_var.set("全部")

        for item_id in self.item_tree.get_children():
            self.item_tree.delete(item_id)

        selected_row = None
        for item in self.store.get_items():
            if not self._item_matches_filter(item):
                continue
            row_id = self.item_tree.insert(
                "",
                tk.END,
                values=(
                    item["name"],
                    item["tag"] or "-",
                ),
            )
            if item["name"] == self.record_item_var.get():
                selected_row = row_id

        if selected_row is not None:
            self.item_tree.selection_set(selected_row)
            self.item_tree.focus(selected_row)

        self._refresh_manage_tree()
        self._refresh_preset_tree()

    def _refresh_selected_item_details(self, records: List[dict]) -> None:
        item = self.store.get_item(self.record_item_var.get())
        if item is None:
            self.selected_item_name_var.set("请先从左侧选择道具")
            self.selected_price_var.set("未选择道具")
            self.selected_tag_var.set("-")
            self.selected_today_qty_var.set("0")
            self.selected_today_coin_var.set("0 梦幻币")
            self.selected_estimated_coin_var.set("0 梦幻币")
            return

        self.selected_item_name_var.set(item["name"])
        if item["price"] <= 0:
            self.selected_price_var.set("未设置单价")
        else:
            self.selected_price_var.set(format_coin(item["price"]))
        self.selected_tag_var.set(item["tag"] or "-")

        today = datetime.now().strftime("%Y-%m-%d")
        today_qty = 0
        today_coin = 0.0
        for record in records:
            if (
                str(record.get("date", "")) == today
                and str(record.get("item_name", "")).strip() == item["name"]
            ):
                today_qty += int(record.get("quantity", 0))
                today_coin += float(record.get("subtotal", 0))

        self.selected_today_qty_var.set(format_number(today_qty))
        self.selected_today_coin_var.set(format_coin(today_coin))

        estimated_quantity_text = self.quantity_var.get().strip().replace(",", "")
        if item["price"] <= 0:
            self.selected_estimated_coin_var.set("未设置单价")
            return
        if not estimated_quantity_text:
            self.selected_estimated_coin_var.set("0 梦幻币")
            return

        try:
            estimated_quantity = int(estimated_quantity_text)
        except ValueError:
            self.selected_estimated_coin_var.set("数量无效")
            return

        if estimated_quantity <= 0:
            self.selected_estimated_coin_var.set("数量无效")
            return

        self.selected_estimated_coin_var.set(
            format_coin(item["price"] * estimated_quantity)
        )

    def clear_catalog_filters(self) -> None:
        self.filter_text_var.set("")
        self.filter_tag_var.set("全部")
        self.status_var.set("已清空道具库筛选条件。")

    def clear_quantity(self) -> None:
        self.quantity_var.set("1")
        self.status_var.set("已清空数量输入。")
        self.root.after_idle(self._focus_quantity_entry)

    def _focus_quantity_entry(self) -> None:
        if not hasattr(self, "quantity_entry"):
            return
        self.quantity_entry.focus_set()
        self.quantity_entry.selection_range(0, tk.END)

    def set_quantity_value(self, quantity: int) -> None:
        self.quantity_var.set(str(quantity))
        self.root.after_idle(self._focus_quantity_entry)

    def convert_coin_to_cash(self, coin_total: float) -> float:
        exchange_rate = self.store.get_exchange_rate()
        coin = float(exchange_rate.get("coin", 0))
        cash = float(exchange_rate.get("cash", 0))
        if coin <= 0 or cash <= 0:
            return 0.0
        return coin_total / coin * cash

    def save_exchange_rate(self) -> None:
        try:
            cash = parse_positive_number(self.cash_ratio_var.get(), "人民币比例")
            coin = parse_positive_int(self.coin_ratio_var.get(), "梦幻币比例")
        except ValueError as error:
            messagebox.showerror("输入错误", str(error))
            return

        self.store.set_exchange_rate(cash, coin)
        self.refresh_views()
        self.status_var.set("已保存人民币和梦幻币比例。")

    def import_preset_items(self) -> None:
        self.open_preset_window()

    def add_item(self) -> None:
        item_name = self.manage_item_var.get().strip()
        tag = self.manage_tag_var.get().strip()
        if not item_name:
            messagebox.showerror("输入错误", "道具名不能为空。")
            return

        try:
            price = parse_positive_int(self.manage_price_var.get(), "单价")
            self.store.add_item(item_name, price, tag)
        except ValueError as error:
            messagebox.showerror("输入错误", str(error))
            return

        self.record_item_var.set(item_name)
        self.quantity_var.set("1")
        self.refresh_views()
        self.status_var.set(
            f"已新增道具：{item_name}，单价 {format_coin(price)}，标签 {tag or '-'}。"
        )

    def update_item(self) -> None:
        item_name = self.manage_item_var.get().strip()
        tag = self.manage_tag_var.get().strip()
        if not item_name:
            messagebox.showerror("输入错误", "请先选择或输入要修改的道具名。")
            return

        try:
            price = parse_positive_int(self.manage_price_var.get(), "单价")
            self.store.update_item(item_name, price, tag)
        except ValueError as error:
            messagebox.showerror("输入错误", str(error))
            return

        self.record_item_var.set(item_name)
        self.refresh_views()
        self.status_var.set(
            f"已更新：{item_name} -> {format_coin(price)}，标签 {tag or '-'}。"
        )

    def load_selected_item_to_form(self) -> None:
        selection = self.item_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先在道具库里选中一个道具。")
            return

        values = self.item_tree.item(selection[0], "values")
        if not values:
            return

        item_name = str(values[0])
        item = self.store.get_item(item_name)
        if item is None:
            return

        self.manage_item_var.set(item["name"])
        self.manage_price_var.set("" if item["price"] <= 0 else format_number(item["price"]))
        self.manage_tag_var.set(item["tag"])
        self.record_item_var.set(item["name"])
        self.status_var.set(f"已载入道具：{item['name']}，输入数量后会自动计算本次价格。")
        self.root.after_idle(self._focus_quantity_entry)

    def _on_item_tree_select(self, _event) -> None:
        selection = self.item_tree.selection()
        if not selection:
            return
        values = self.item_tree.item(selection[0], "values")
        if not values:
            return

        item_name = str(values[0])
        item = self.store.get_item(item_name)
        if item is None:
            return

        self.manage_item_var.set(item["name"])
        self.manage_price_var.set("" if item["price"] <= 0 else format_number(item["price"]))
        self.manage_tag_var.set(item["tag"])
        self.record_item_var.set(item["name"])
        self.status_var.set(f"已选中道具：{item['name']}，输入数量后会自动计算本次价格。")
        self.root.after_idle(self._focus_quantity_entry)

    def save_record(self) -> None:
        item_name = self.record_item_var.get().strip()
        if not item_name:
            messagebox.showerror("输入错误", "请先选择道具。")
            return

        try:
            quantity = parse_positive_int(self.quantity_var.get(), "数量")
            cash = parse_positive_number(self.cash_ratio_var.get(), "人民币比例")
            coin = parse_positive_int(self.coin_ratio_var.get(), "梦幻币比例")
            self.store.set_exchange_rate(cash, coin)
            record = self.store.add_record(item_name, quantity)
        except ValueError as error:
            messagebox.showerror("输入错误", str(error))
            return

        self.refresh_views()
        self.status_var.set(
            f"已记录：{record['item_name']} +{quantity}，"
            f"当日累计 {record['quantity']}，小计 {format_coin(record['subtotal'])}。"
        )
        self.quantity_var.set("1")

    def delete_selected_record(self) -> None:
        selection = self.today_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一条当日记录。")
            return

        selected_id = selection[0]
        record_id = self.today_record_ids.get(selected_id)
        if not record_id:
            messagebox.showerror("删除失败", "没有找到这条记录。")
            return

        if not messagebox.askyesno("确认删除", "确定删除选中的当日记录吗？"):
            return

        deleted = self.store.delete_record(record_id)
        if not deleted:
            messagebox.showerror("删除失败", "记录不存在或已经被删除。")
            return

        self.refresh_views()
        self.status_var.set("已删除选中的当日记录。")

    def _build_total_summary_rows(self, records: List[dict]) -> List[dict]:
        summary: Dict[str, dict] = {}
        for record in records:
            item_name = str(record.get("item_name", "")).strip()
            if not item_name:
                continue

            item_summary = summary.setdefault(
                item_name,
                {
                    "quantity": 0,
                    "total_coin": 0.0,
                },
            )
            item_summary["quantity"] += int(record.get("quantity", 0))
            item_summary["total_coin"] += float(record.get("subtotal", 0))

        rows: List[dict] = []
        for item_name, item_summary in summary.items():
            item = self.store.get_item(item_name)
            current_price = item["price"] if item is not None else 0
            tag = item["tag"] if item is not None else ""
            total_coin = item_summary["total_coin"]
            rows.append(
                {
                    "item_name": item_name,
                    "tag": tag,
                    "quantity": item_summary["quantity"],
                    "current_price": current_price,
                    "total_coin": total_coin,
                    "total_cash": self.convert_coin_to_cash(total_coin),
                }
            )

        return sorted(rows, key=lambda row: row["total_coin"], reverse=True)

    def refresh_views(self) -> None:
        records = self._sort_records(self.store.get_records())
        self.latest_records_cache = records
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [record for record in records if record.get("date") == today]
        total_rows = self._build_total_summary_rows(records)

        self._refresh_item_catalog()
        self._refresh_selected_item_details(records)
        self._refresh_today_table(today_records)
        self._refresh_total_table(total_rows)
        self._refresh_summary(records, today_records)
        self._refresh_trend_chart(records)

    def _refresh_today_table(self, today_records: List[dict]) -> None:
        self.today_record_ids.clear()
        for item_id in self.today_tree.get_children():
            self.today_tree.delete(item_id)

        for record in today_records:
            item = self.store.get_item(str(record.get("item_name", "")))
            tag = item["tag"] if item is not None else ""
            tree_id = self.today_tree.insert(
                "",
                tk.END,
                values=(
                    record.get("time", ""),
                    record.get("item_name", ""),
                    tag or "-",
                    format_number(float(record.get("price_snapshot", 0))),
                    format_number(float(record.get("quantity", 0))),
                    format_number(float(record.get("subtotal", 0))),
                ),
            )
            self.today_record_ids[tree_id] = str(record.get("id", ""))

    def _refresh_total_table(self, rows: List[dict]) -> None:
        for item_id in self.total_tree.get_children():
            self.total_tree.delete(item_id)

        for row in rows:
            current_price_label = (
                "未设置" if float(row["current_price"]) <= 0 else format_number(row["current_price"])
            )
            self.total_tree.insert(
                "",
                tk.END,
                values=(
                    row["item_name"],
                    row["tag"] or "-",
                    format_number(row["quantity"]),
                    current_price_label,
                    format_number(row["total_coin"]),
                    format_number(row["total_cash"]),
                ),
            )

    def _refresh_summary(self, records: List[dict], today_records: List[dict]) -> None:
        today_total_coin = sum(float(record.get("subtotal", 0)) for record in today_records)
        total_coin = sum(float(record.get("subtotal", 0)) for record in records)
        today_total_cash = self.convert_coin_to_cash(today_total_coin)
        total_cash = self.convert_coin_to_cash(total_coin)

        exchange_rate = self.store.get_exchange_rate()
        self.today_total_coin_var.set(format_coin(today_total_coin))
        self.today_total_cash_var.set(format_cash(today_total_cash))
        self.total_coin_var.set(format_coin(total_coin))
        self.total_cash_var.set(format_cash(total_cash))
        self.rate_hint_var.set(
            f"{format_number(exchange_rate.get('cash', 0))} 元 = "
            f"{format_number(exchange_rate.get('coin', 0))} 梦幻币"
        )

    def _refresh_trend_chart(self, records: List[dict]) -> None:
        if not hasattr(self, "trend_canvas"):
            return

        canvas = self.trend_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 420)
        height = max(canvas.winfo_height(), 200)
        padding_left = 26
        padding_right = 18
        padding_top = 24
        padding_bottom = 38
        chart_width = width - padding_left - padding_right
        chart_height = height - padding_top - padding_bottom

        day_labels: List[str] = []
        totals_by_day: Dict[str, float] = {}
        for offset in range(6, -1, -1):
            day = (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")
            day_labels.append(day)
            totals_by_day[day] = 0.0

        for record in records:
            day = str(record.get("date", ""))
            if day in totals_by_day:
                totals_by_day[day] += float(record.get("subtotal", 0))

        values = [totals_by_day[day] for day in day_labels]
        max_value = max(values) if any(values) else 1.0
        slot_width = chart_width / len(day_labels)

        canvas.create_line(
            padding_left,
            height - padding_bottom,
            width - padding_right,
            height - padding_bottom,
            fill="#d8d8d8",
            width=1,
        )

        for index, day in enumerate(day_labels):
            value = values[index]
            x0 = padding_left + index * slot_width + 10
            x1 = padding_left + (index + 1) * slot_width - 10
            bar_height = 0 if value <= 0 else chart_height * (value / max_value)
            y1 = height - padding_bottom
            y0 = y1 - bar_height
            fill = "#f4a259" if index == len(day_labels) - 1 else "#6c8ef5"

            if value > 0:
                canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="")
                value_y = max(y0 - 10, 12)
                canvas.create_text(
                    (x0 + x1) / 2,
                    value_y,
                    text=format_number(value),
                    fill="#44506a",
                    font=("Microsoft YaHei UI", 9),
                )
            else:
                canvas.create_line(x0, y1 - 1, x1, y1 - 1, fill="#cfcfcf", width=4)

            canvas.create_text(
                (x0 + x1) / 2,
                height - 16,
                text=day[5:],
                fill="#666666",
                font=("Microsoft YaHei UI", 9),
            )

        total_7d = sum(values)
        self.trend_tip_var.set(
            f"最近 7 天总计 {format_coin(total_7d)}，今日高亮显示"
        )

    def export_report(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="导出统计报表",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
            initialfile=f"mhxy_report_{datetime.now().strftime('%Y%m%d')}.csv",
        )
        if not file_path:
            return

        records = self._sort_records(self.store.get_records())
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [record for record in records if record.get("date") == today]
        total_rows = self._build_total_summary_rows(records)

        with open(file_path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["导出时间", current_timestamp()])
            writer.writerow([])
            writer.writerow(["当日记录汇总"])
            writer.writerow(
                ["最后记录时间", "道具名", "标签", "单价（梦幻币）", "数量", "小计（梦幻币）"]
            )
            for record in today_records:
                item = self.store.get_item(str(record.get("item_name", "")))
                writer.writerow(
                    [
                        record.get("time", ""),
                        record.get("item_name", ""),
                        item["tag"] if item is not None and item["tag"] else "",
                        int(float(record.get("price_snapshot", 0))),
                        int(float(record.get("quantity", 0))),
                        int(float(record.get("subtotal", 0))),
                    ]
                )

            writer.writerow([])
            writer.writerow(["总统计"])
            writer.writerow(
                ["道具名", "标签", "累计数量", "当前单价（梦幻币）", "累计梦幻币", "折合人民币（元）"]
            )
            for row in total_rows:
                writer.writerow(
                    [
                        row["item_name"],
                        row["tag"],
                        row["quantity"],
                        int(row["current_price"]),
                        int(row["total_coin"]),
                        format_number(row["total_cash"]),
                    ]
                )

        self.status_var.set(f"已导出报表：{file_path}")


def main() -> None:
    if TK_IMPORT_ERROR is not None:
        raise RuntimeError(
            "当前 Python 环境缺少 tkinter，无法启动桌面界面。"
            "请在 Windows 上使用官方 Python 运行，或直接打包成 exe。"
        ) from TK_IMPORT_ERROR

    root = tk.Tk()
    IncomeTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

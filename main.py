from __future__ import annotations

import json
import os
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
    TK_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    tk = None
    messagebox = None
    ttk = None
    TK_IMPORT_ERROR = exc


APP_TITLE = "梦幻西游收益统计"
WINDOW_SIZE = "1220x760"


def get_data_dir() -> Path:
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
    return data_dir


DATA_DIR = get_data_dir()
DATA_FILE = DATA_DIR / "data.json"


class DataStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.data = self._load()

    def _default_data(self) -> dict:
        return {
            "item_names": [],
            "exchange_rate": {
                "cash": 100.0,
                "coin": 1000.0,
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
            self._save(loaded)

        data = self._default_data()
        data.update(loaded)
        data["exchange_rate"].update(loaded.get("exchange_rate", {}))
        return data

    def _save(self, data: dict | None = None) -> None:
        if data is not None:
            self.data = data

        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=2)

    def get_item_names(self) -> list[str]:
        return list(self.data["item_names"])

    def add_item_name(self, item_name: str) -> None:
        normalized = item_name.strip()
        if not normalized:
            return
        if normalized not in self.data["item_names"]:
            self.data["item_names"].append(normalized)
            self._save()

    def get_exchange_rate(self) -> dict:
        return dict(self.data["exchange_rate"])

    def set_exchange_rate(self, cash: float, coin: float) -> None:
        self.data["exchange_rate"] = {
            "cash": cash,
            "coin": coin,
        }
        self._save()

    def get_records(self) -> list[dict]:
        return list(self.data["records"])

    def add_record(self, item_name: str, price: float, quantity: float) -> None:
        now = datetime.now()
        record = {
            "id": uuid.uuid4().hex,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "created_at": now.isoformat(timespec="seconds"),
            "item_name": item_name.strip(),
            "price": price,
            "quantity": quantity,
            "subtotal": price * quantity,
        }
        self.data["records"].append(record)
        self._save()

    def delete_record(self, record_id: str) -> bool:
        before_count = len(self.data["records"])
        self.data["records"] = [
            record for record in self.data["records"] if record.get("id") != record_id
        ]
        changed = len(self.data["records"]) != before_count
        if changed:
            self._save()
        return changed


def format_number(value: float) -> str:
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def parse_positive_number(value: str, field_name: str) -> float:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name}不能为空。")

    try:
        number = float(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name}必须是数字。") from exc

    if number <= 0:
        raise ValueError(f"{field_name}必须大于 0。")
    return number


class IncomeTrackerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.store = DataStore(DATA_FILE)

        self.item_name_var = tk.StringVar()
        self.price_var = tk.StringVar()
        self.quantity_var = tk.StringVar(value="1")
        self.cash_ratio_var = tk.StringVar()
        self.coin_ratio_var = tk.StringVar()
        self.status_var = tk.StringVar(value="准备就绪")
        self.today_total_coin_var = tk.StringVar(value="0 万梦幻币")
        self.today_total_cash_var = tk.StringVar(value="0 元")
        self.total_coin_var = tk.StringVar(value="0 万梦幻币")
        self.total_cash_var = tk.StringVar(value="0 元")
        self.rate_hint_var = tk.StringVar(value="")

        self.today_record_ids: dict[str, str] = {}

        self._configure_window()
        self._build_ui()
        self._load_saved_state()
        self.refresh_views()

    def _configure_window(self) -> None:
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(1100, 700)

        style = ttk.Style()
        available_themes = style.theme_names()
        if "clam" in available_themes:
            style.theme_use("clam")

        style.configure("Card.TFrame", padding=14)
        style.configure("CardTitle.TLabel", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("BigValue.TLabel", font=("Microsoft YaHei UI", 16, "bold"))
        style.configure("Subtle.TLabel", foreground="#666666")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(20, 18, 20, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text=APP_TITLE,
            font=("Microsoft YaHei UI", 20, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=f"数据保存位置：{DATA_FILE}",
            style="Subtle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        top = ttk.Frame(self.root, padding=(20, 0, 20, 10))
        top.grid(row=1, column=0, sticky="ew")
        top.columnconfigure(0, weight=7)
        top.columnconfigure(1, weight=5)

        self._build_input_panel(top)
        self._build_summary_panel(top)

        content = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        content.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))

        today_frame = ttk.Labelframe(content, text="当日记录", padding=14)
        total_frame = ttk.Labelframe(content, text="总统计", padding=14)
        content.add(today_frame, weight=7)
        content.add(total_frame, weight=6)

        self._build_today_table(today_frame)
        self._build_total_table(total_frame)

        footer = ttk.Frame(self.root, padding=(20, 0, 20, 18))
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Subtle.TLabel").grid(
            row=0, column=0, sticky="w"
        )

    def _build_input_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Labelframe(parent, text="录入区", padding=14)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        panel.columnconfigure(1, weight=1)
        panel.columnconfigure(3, weight=1)

        ttk.Label(panel, text="道具名").grid(row=0, column=0, sticky="w", pady=6)
        self.item_name_combo = ttk.Combobox(
            panel,
            textvariable=self.item_name_var,
            state="normal",
        )
        self.item_name_combo.grid(row=0, column=1, sticky="ew", padx=(10, 16), pady=6)

        ttk.Label(panel, text="单价（万梦幻币）").grid(
            row=0, column=2, sticky="w", pady=6
        )
        ttk.Entry(panel, textvariable=self.price_var).grid(
            row=0, column=3, sticky="ew", padx=(10, 0), pady=6
        )

        ttk.Label(panel, text="数量").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(panel, textvariable=self.quantity_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 16), pady=6
        )

        ttk.Label(panel, text="人民币比例（元）").grid(
            row=1, column=2, sticky="w", pady=6
        )
        ttk.Entry(panel, textvariable=self.cash_ratio_var).grid(
            row=1, column=3, sticky="ew", padx=(10, 0), pady=6
        )

        ttk.Label(panel, text="梦幻币比例（万）").grid(
            row=2, column=0, sticky="w", pady=6
        )
        ttk.Entry(panel, textvariable=self.coin_ratio_var).grid(
            row=2, column=1, sticky="ew", padx=(10, 16), pady=6
        )

        ttk.Label(
            panel,
            text="比例示例：100 元 = 1500 万梦幻币",
            style="Subtle.TLabel",
        ).grid(row=2, column=2, columnspan=2, sticky="w", pady=6)

        button_row = ttk.Frame(panel)
        button_row.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 4))
        button_row.columnconfigure(4, weight=1)

        ttk.Button(button_row, text="保存记录", command=self.save_record).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(button_row, text="仅保存比例", command=self.save_exchange_rate).grid(
            row=0, column=1, padx=8
        )
        ttk.Button(button_row, text="清空输入", command=self.clear_inputs).grid(
            row=0, column=2, padx=8
        )
        ttk.Button(
            button_row,
            text="删除选中当日记录",
            command=self.delete_selected_record,
        ).grid(row=0, column=3, padx=(8, 0))

    def _build_summary_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent)
        panel.grid(row=0, column=1, sticky="nsew")
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
            row=1, column=0, sticky="w", pady=(8, 0)
        )

    def _create_stat_card(
        self, parent: ttk.Frame, row: int, column: int, title: str, value_var: tk.StringVar
    ) -> None:
        card = ttk.Frame(parent, style="Card.TFrame")
        card.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 12, 0), pady=(0 if row == 0 else 12, 0))
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

        columns = ("time", "item_name", "price", "quantity", "subtotal")
        self.today_tree = ttk.Treeview(parent, columns=columns, show="headings", height=16)
        headers = {
            "time": "时间",
            "item_name": "道具名",
            "price": "单价（万）",
            "quantity": "数量",
            "subtotal": "小计（万）",
        }
        widths = {
            "time": 120,
            "item_name": 220,
            "price": 120,
            "quantity": 100,
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

        columns = ("item_name", "quantity", "latest_price", "total_coin", "total_cash")
        self.total_tree = ttk.Treeview(parent, columns=columns, show="headings", height=16)
        headers = {
            "item_name": "道具名",
            "quantity": "累计数量",
            "latest_price": "最近单价（万）",
            "total_coin": "累计梦幻币（万）",
            "total_cash": "折合人民币（元）",
        }
        widths = {
            "item_name": 220,
            "quantity": 120,
            "latest_price": 140,
            "total_coin": 150,
            "total_cash": 150,
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
        self.coin_ratio_var.set(format_number(exchange_rate.get("coin", 1000.0)))
        self.item_name_combo["values"] = self.store.get_item_names()

    def clear_inputs(self) -> None:
        self.price_var.set("")
        self.quantity_var.set("1")
        self.status_var.set("已清空单价和数量输入。")

    def convert_coin_to_cash(self, coin_total: float) -> float:
        exchange_rate = self.store.get_exchange_rate()
        coin = exchange_rate.get("coin", 0)
        cash = exchange_rate.get("cash", 0)
        if coin <= 0 or cash <= 0:
            return 0.0
        return coin_total / coin * cash

    def save_exchange_rate(self) -> None:
        try:
            cash = parse_positive_number(self.cash_ratio_var.get(), "人民币比例")
            coin = parse_positive_number(self.coin_ratio_var.get(), "梦幻币比例")
        except ValueError as error:
            messagebox.showerror("输入错误", str(error))
            return

        self.store.set_exchange_rate(cash, coin)
        self.refresh_views()
        self.status_var.set("已保存换算比例。")

    def save_record(self) -> None:
        item_name = self.item_name_var.get().strip()
        if not item_name:
            messagebox.showerror("输入错误", "道具名不能为空。")
            return

        try:
            price = parse_positive_number(self.price_var.get(), "单价")
            quantity = parse_positive_number(self.quantity_var.get(), "数量")
            cash = parse_positive_number(self.cash_ratio_var.get(), "人民币比例")
            coin = parse_positive_number(self.coin_ratio_var.get(), "梦幻币比例")
        except ValueError as error:
            messagebox.showerror("输入错误", str(error))
            return

        self.store.add_item_name(item_name)
        self.store.set_exchange_rate(cash, coin)
        self.store.add_record(item_name=item_name, price=price, quantity=quantity)
        self.item_name_combo["values"] = self.store.get_item_names()
        self.refresh_views()

        subtotal = price * quantity
        self.status_var.set(
            f"已保存：{item_name}，数量 {format_number(quantity)}，"
            f"小计 {format_number(subtotal)} 万梦幻币。"
        )
        self.price_var.set("")
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

    def refresh_views(self) -> None:
        records = sorted(
            self.store.get_records(),
            key=lambda item: item.get("created_at", ""),
        )
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [record for record in records if record.get("date") == today]

        self._refresh_today_table(today_records)
        self._refresh_total_table(records)
        self._refresh_summary(records, today_records)

    def _refresh_today_table(self, today_records: list[dict]) -> None:
        self.today_record_ids.clear()
        for item in self.today_tree.get_children():
            self.today_tree.delete(item)

        for record in today_records:
            tree_id = self.today_tree.insert(
                "",
                tk.END,
                values=(
                    record.get("time", ""),
                    record.get("item_name", ""),
                    format_number(float(record.get("price", 0))),
                    format_number(float(record.get("quantity", 0))),
                    format_number(float(record.get("subtotal", 0))),
                ),
            )
            self.today_record_ids[tree_id] = record.get("id", "")

    def _refresh_total_table(self, records: list[dict]) -> None:
        for item in self.total_tree.get_children():
            self.total_tree.delete(item)

        summary: dict[str, dict] = defaultdict(
            lambda: {
                "quantity": 0.0,
                "latest_price": 0.0,
                "total_coin": 0.0,
                "latest_at": "",
            }
        )

        for record in records:
            item_name = str(record.get("item_name", "")).strip()
            if not item_name:
                continue

            quantity = float(record.get("quantity", 0))
            price = float(record.get("price", 0))
            subtotal = float(record.get("subtotal", 0))
            created_at = str(record.get("created_at", ""))

            summary[item_name]["quantity"] += quantity
            summary[item_name]["total_coin"] += subtotal
            if created_at >= summary[item_name]["latest_at"]:
                summary[item_name]["latest_at"] = created_at
                summary[item_name]["latest_price"] = price

        ordered_items = sorted(
            summary.items(),
            key=lambda pair: pair[1]["total_coin"],
            reverse=True,
        )

        for item_name, item_summary in ordered_items:
            total_coin = item_summary["total_coin"]
            total_cash = self.convert_coin_to_cash(total_coin)
            self.total_tree.insert(
                "",
                tk.END,
                values=(
                    item_name,
                    format_number(item_summary["quantity"]),
                    format_number(item_summary["latest_price"]),
                    format_number(total_coin),
                    format_number(total_cash),
                ),
            )

    def _refresh_summary(self, records: list[dict], today_records: list[dict]) -> None:
        today_total_coin = sum(float(record.get("subtotal", 0)) for record in today_records)
        total_coin = sum(float(record.get("subtotal", 0)) for record in records)
        today_total_cash = self.convert_coin_to_cash(today_total_coin)
        total_cash = self.convert_coin_to_cash(total_coin)

        exchange_rate = self.store.get_exchange_rate()
        self.today_total_coin_var.set(f"{format_number(today_total_coin)} 万梦幻币")
        self.today_total_cash_var.set(f"{format_number(today_total_cash)} 元")
        self.total_coin_var.set(f"{format_number(total_coin)} 万梦幻币")
        self.total_cash_var.set(f"{format_number(total_cash)} 元")
        self.rate_hint_var.set(
            f"{format_number(exchange_rate.get('cash', 0))} 元 = "
            f"{format_number(exchange_rate.get('coin', 0))} 万梦幻币"
        )


def main() -> None:
    if TK_IMPORT_ERROR is not None:
        raise RuntimeError(
            "当前 Python 环境缺少 tkinter，无法启动桌面界面。"
            "请在 Windows 上使用官方 Python 运行，或直接打包成 exe。"
        ) from TK_IMPORT_ERROR

    root = tk.Tk()
    app = IncomeTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

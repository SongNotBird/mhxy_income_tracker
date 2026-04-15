#!/usr/bin/env python3
"""Tkinter GUI for the screen region clicker."""

from __future__ import annotations

import queue
import os
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, NamedTuple

import pyautogui

from screen_clicker import Box, MatchResult, Point, find_template, load_template, region_origin, screenshot_region, should_click


class WatchConfig(NamedTuple):
    region: Box | None
    template: Path
    threshold: float
    interval: float
    cooldown: float
    click_mode: str
    click_x: int
    click_y: int
    dry_run: bool
    repeat: bool
    once: bool


def default_templates_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "ScreenRegionClicker" / "templates"
    return Path.home() / ".screen_region_clicker" / "templates"


class RegionSelectionOverlay(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk,
        on_done: Callable[[Box | None], None],
        prompt: str = "拖动选择区域，松开鼠标确认；按 Esc 取消",
    ) -> None:
        super().__init__(parent)
        self.on_done = on_done
        self.start_root: Point | None = None
        self.start_canvas: Point | None = None
        self.rect_id: int | None = None

        width = parent.winfo_screenwidth()
        height = parent.winfo_screenheight()
        self.geometry(f"{width}x{height}+0+0")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.32)
        self.configure(bg="black")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_text(
            width // 2,
            32,
            text=prompt,
            fill="white",
            font=("Microsoft YaHei UI", 15, "bold"),
        )

        self.canvas.bind("<ButtonPress-1>", self._start)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._finish)
        self.bind("<Escape>", self._cancel)
        self.focus_force()
        self.grab_set()

    def _start(self, event: tk.Event) -> None:
        self.start_root = Point(event.x_root, event.y_root)
        self.start_canvas = Point(event.x, event.y)
        self.rect_id = self.canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="#45d6a3",
            width=3,
        )

    def _drag(self, event: tk.Event) -> None:
        if self.start_canvas is None or self.rect_id is None:
            return
        self.canvas.coords(self.rect_id, self.start_canvas.x, self.start_canvas.y, event.x, event.y)

    def _finish(self, event: tk.Event) -> None:
        if self.start_root is None:
            self._complete(None)
            return

        left = min(self.start_root.x, event.x_root)
        top = min(self.start_root.y, event.y_root)
        right = max(self.start_root.x, event.x_root)
        bottom = max(self.start_root.y, event.y_root)
        width = right - left
        height = bottom - top

        if width < 5 or height < 5:
            self._complete(None)
            return

        self._complete(Box(left, top, width, height))

    def _cancel(self, _event: tk.Event | None = None) -> None:
        self._complete(None)

    def _complete(self, region: Box | None) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        self.on_done(region)


class PointCaptureOverlay(tk.Toplevel):
    def __init__(self, parent: tk.Tk, on_done: Callable[[Point | None], None]) -> None:
        super().__init__(parent)
        self.on_done = on_done

        width = parent.winfo_screenwidth()
        height = parent.winfo_screenheight()
        self.geometry(f"{width}x{height}+0+0")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.22)
        self.configure(bg="black")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_text(
            width // 2,
            32,
            text="点击备用固定坐标；按 Esc 取消",
            fill="white",
            font=("Microsoft YaHei UI", 15, "bold"),
        )

        self.canvas.bind("<ButtonPress-1>", self._capture)
        self.bind("<Escape>", self._cancel)
        self.focus_force()
        self.grab_set()

    def _capture(self, event: tk.Event) -> None:
        self._complete(Point(event.x_root, event.y_root))

    def _cancel(self, _event: tk.Event | None = None) -> None:
        self._complete(None)

    def _complete(self, point: Point | None) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        self.on_done(point)


class ScreenClickerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("屏幕区域自动点击")
        self.minsize(720, 560)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.status_queue: queue.Queue[str] = queue.Queue()

        self.template_path = tk.StringVar()
        self.region_x = tk.StringVar(value="100")
        self.region_y = tk.StringVar(value="200")
        self.region_w = tk.StringVar(value="500")
        self.region_h = tk.StringVar(value="300")
        self.full_screen_search = tk.BooleanVar(value=True)
        self.threshold = tk.StringVar(value="0.88")
        self.interval = tk.StringVar(value="0.25")
        self.cooldown = tk.StringVar(value="3")
        self.click_mode = tk.StringVar(value="center")
        self.click_x = tk.StringVar(value="900")
        self.click_y = tk.StringVar(value="650")
        self.dry_run = tk.BooleanVar(value=True)
        self.repeat = tk.BooleanVar(value=False)
        self.once = tk.BooleanVar(value=False)
        self.position_text = tk.StringVar(value="鼠标坐标：X=0 Y=0")
        self.status_text = tk.StringVar(value="未开始")

        self._build_ui()
        self._schedule_position_update()
        self._drain_logs()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)

        template_frame = ttk.LabelFrame(root, text="模板图片", padding=10)
        template_frame.grid(row=0, column=0, sticky="ew")
        template_frame.columnconfigure(0, weight=1)
        ttk.Entry(template_frame, textvariable=self.template_path).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(template_frame, text="选择图片", command=self._choose_template).grid(row=0, column=1)
        ttk.Button(template_frame, text="截取目标样式", command=self._capture_template_from_screen).grid(
            row=0, column=2, padx=(8, 0)
        )

        region_frame = ttk.LabelFrame(root, text="搜索范围", padding=10)
        region_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(
            region_frame,
            text="全屏搜索目标图片（推荐，窗口漂移也能找）",
            variable=self.full_screen_search,
        ).grid(row=0, column=0, columnspan=8, sticky="w")
        for index, (label, var) in enumerate(
            (("X", self.region_x), ("Y", self.region_y), ("宽", self.region_w), ("高", self.region_h))
        ):
            ttk.Label(region_frame, text=label).grid(row=1, column=index * 2, sticky="w", pady=(10, 0))
            ttk.Entry(region_frame, textvariable=var, width=9).grid(
                row=1, column=index * 2 + 1, padx=(4, 14), pady=(10, 0)
            )
        ttk.Button(region_frame, text="拖动限制搜索范围", command=self._select_region).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )

        settings_frame = ttk.LabelFrame(root, text="识别设置", padding=10)
        settings_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for index, (label, var) in enumerate(
            (("匹配阈值", self.threshold), ("检测间隔秒", self.interval), ("点击冷却秒", self.cooldown))
        ):
            ttk.Label(settings_frame, text=label).grid(row=0, column=index * 2, sticky="w")
            ttk.Entry(settings_frame, textvariable=var, width=10).grid(row=0, column=index * 2 + 1, padx=(4, 18))

        click_frame = ttk.LabelFrame(root, text="点击位置", padding=10)
        click_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Radiobutton(click_frame, text="匹配图片中心（推荐）", variable=self.click_mode, value="center").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Radiobutton(click_frame, text="图片内偏移", variable=self.click_mode, value="offset").grid(
            row=0, column=1, sticky="w", padx=(16, 0)
        )
        ttk.Radiobutton(click_frame, text="固定坐标（备用）", variable=self.click_mode, value="absolute").grid(
            row=0, column=2, sticky="w", padx=(16, 0)
        )
        ttk.Label(click_frame, text="X / 偏移X").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(click_frame, textvariable=self.click_x, width=10).grid(row=1, column=1, sticky="w", pady=(10, 0))
        ttk.Label(click_frame, text="Y / 偏移Y").grid(row=1, column=2, sticky="w", pady=(10, 0))
        ttk.Entry(click_frame, textvariable=self.click_y, width=10).grid(row=1, column=3, sticky="w", pady=(10, 0))
        ttk.Button(click_frame, text="记录固定坐标", command=self._capture_click_point).grid(
            row=1, column=4, sticky="w", padx=(16, 0), pady=(10, 0)
        )

        option_frame = ttk.Frame(root)
        option_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(option_frame, text="测试模式，不点击", variable=self.dry_run).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(option_frame, text="持续出现时重复点击", variable=self.repeat).grid(
            row=0, column=1, sticky="w", padx=(18, 0)
        )
        ttk.Checkbutton(option_frame, text="点击一次后停止", variable=self.once).grid(
            row=0, column=2, sticky="w", padx=(18, 0)
        )

        status_frame = ttk.Frame(root)
        status_frame.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        status_frame.columnconfigure(1, weight=1)
        ttk.Label(status_frame, textvariable=self.position_text).grid(row=0, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.status_text).grid(row=0, column=1, sticky="e")

        button_frame = ttk.Frame(root)
        button_frame.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        self.start_button = ttk.Button(button_frame, text="开始监控", command=self._start)
        self.start_button.grid(row=0, column=0)
        self.stop_button = ttk.Button(button_frame, text="停止", command=self._stop, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(8, 0))
        ttk.Button(button_frame, text="测试匹配一次", command=self._test_once).grid(row=0, column=2, padx=(8, 0))

        log_frame = ttk.LabelFrame(root, text="日志", padding=8)
        log_frame.grid(row=7, column=0, sticky="nsew", pady=(10, 0))
        root.rowconfigure(7, weight=1)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _choose_template(self) -> None:
        filename = filedialog.askopenfilename(
            title="选择模板图片",
            filetypes=(("图片文件", "*.png;*.jpg;*.jpeg;*.bmp"), ("所有文件", "*.*")),
        )
        if filename:
            self.template_path.set(filename)

    def _hide_for_overlay(self, callback: Callable[[], None]) -> None:
        self.withdraw()
        self.after(250, callback)

    def _restore_after_overlay(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _select_region(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("正在监控", "请先停止监控，再重新选择区域。")
            return

        def open_overlay() -> None:
            RegionSelectionOverlay(
                self,
                self._apply_selected_region,
                prompt="拖动限制搜索范围，松开鼠标确认；按 Esc 取消",
            )

        self._hide_for_overlay(open_overlay)

    def _apply_selected_region(self, region: Box | None) -> None:
        self._restore_after_overlay()
        if region is None:
            self._log("已取消选择监控区域")
            self.status_text.set("已取消选择区域")
            return

        self.region_x.set(str(region.x))
        self.region_y.set(str(region.y))
        self.region_w.set(str(region.width))
        self.region_h.set(str(region.height))
        self.full_screen_search.set(False)
        self._log(f"已限制搜索范围：x={region.x}, y={region.y}, 宽={region.width}, 高={region.height}")
        self.status_text.set("已限制搜索范围")

    def _capture_template_from_screen(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("正在监控", "请先停止监控，再重新截取目标样式。")
            return

        def open_overlay() -> None:
            RegionSelectionOverlay(
                self,
                self._save_template_region,
                prompt="拖动框选要识别的按钮或界面样式，松开鼠标保存；按 Esc 取消",
            )

        self._hide_for_overlay(open_overlay)

    def _save_template_region(self, region: Box | None) -> None:
        if region is None:
            self._restore_after_overlay()
            self._log("已取消截取目标样式")
            self.status_text.set("已取消截取目标样式")
            return

        def save() -> None:
            try:
                output_dir = default_templates_dir()
                output_dir.mkdir(parents=True, exist_ok=True)
                output = output_dir / f"target_{time.strftime('%Y%m%d_%H%M%S')}.png"
                image = pyautogui.screenshot(region=region)
                image.save(output)
                self.template_path.set(str(output))
                self.click_mode.set("center")
                self.full_screen_search.set(True)
                self._log(f"已截取目标样式：{output}")
                self.status_text.set("已截取目标样式")
            except Exception as exc:
                self._log(f"截取目标样式失败：{exc}")
                self.status_text.set("截取目标样式失败")
            finally:
                self._restore_after_overlay()

        self.after(150, save)

    def _capture_click_point(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("正在监控", "请先停止监控，再重新记录固定坐标。")
            return

        def open_overlay() -> None:
            PointCaptureOverlay(self, self._apply_click_point)

        self._hide_for_overlay(open_overlay)

    def _apply_click_point(self, point: Point | None) -> None:
        self._restore_after_overlay()
        if point is None:
            self._log("已取消记录固定坐标")
            self.status_text.set("已取消记录坐标")
            return

        self.click_mode.set("absolute")
        self.click_x.set(str(point.x))
        self.click_y.set(str(point.y))
        self._log(f"已记录固定坐标：({point.x},{point.y})")
        self.status_text.set("已记录固定坐标")

    def _schedule_position_update(self) -> None:
        try:
            x, y = pyautogui.position()
            self.position_text.set(f"鼠标坐标：X={x} Y={y}")
        except Exception as exc:
            self.position_text.set(f"鼠标坐标读取失败：{exc}")
        self.after(200, self._schedule_position_update)

    def _log(self, message: str) -> None:
        now = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{now}] {message}")

    def _set_status(self, message: str) -> None:
        self.status_queue.put(message)

    def _drain_logs(self) -> None:
        while True:
            try:
                status = self.status_queue.get_nowait()
            except queue.Empty:
                break
            self.status_text.set(status)

        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        self.after(100, self._drain_logs)

    def _read_config(self) -> WatchConfig:
        template = Path(self.template_path.get().strip()).expanduser()
        if not template.is_file():
            raise ValueError("请选择有效的模板图片")

        region = None
        if not self.full_screen_search.get():
            region = Box(
                int(self.region_x.get()),
                int(self.region_y.get()),
                int(self.region_w.get()),
                int(self.region_h.get()),
            )
            if region.width <= 0 or region.height <= 0:
                raise ValueError("搜索范围宽高必须大于 0")

        threshold = float(self.threshold.get())
        interval = float(self.interval.get())
        cooldown = float(self.cooldown.get())
        if not 0 <= threshold <= 1:
            raise ValueError("匹配阈值必须在 0 到 1 之间")
        if interval <= 0 or cooldown < 0:
            raise ValueError("检测间隔必须大于 0，点击冷却不能小于 0")

        click_mode = self.click_mode.get()
        click_x = int(self.click_x.get() or 0) if click_mode != "center" else 0
        click_y = int(self.click_y.get() or 0) if click_mode != "center" else 0

        return WatchConfig(
            region=region,
            template=template,
            threshold=threshold,
            interval=interval,
            cooldown=cooldown,
            click_mode=click_mode,
            click_x=click_x,
            click_y=click_y,
            dry_run=self.dry_run.get(),
            repeat=self.repeat.get(),
            once=self.once.get(),
        )

    def _click_point(self, config: WatchConfig, match: MatchResult) -> Point:
        origin = region_origin(config.region)
        if config.click_mode == "center":
            template_width, template_height = match.size
            return Point(
                origin.x + match.top_left.x + template_width // 2,
                origin.y + match.top_left.y + template_height // 2,
            )
        if config.click_mode == "offset":
            return Point(
                origin.x + match.top_left.x + config.click_x,
                origin.y + match.top_left.y + config.click_y,
            )
        return Point(config.click_x, config.click_y)

    def _test_once(self) -> None:
        try:
            config = self._read_config()
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        def run() -> None:
            try:
                template = load_template(config.template)
                match = find_template(screenshot_region(config.region), template)
                origin = region_origin(config.region)
                top_left = Point(origin.x + match.top_left.x, origin.y + match.top_left.y)
                self._log(f"测试匹配 score={match.score:.3f}，模板左上角=({top_left.x},{top_left.y})")
                self._set_status(f"测试完成 score={match.score:.3f}")
            except Exception as exc:
                self._log(f"测试失败：{exc}")
                self._set_status("测试失败")

        threading.Thread(target=run, daemon=True).start()

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        try:
            config = self._read_config()
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        self.stop_event.clear()
        self.worker = threading.Thread(target=self._watch_loop, args=(config,), daemon=True)
        self.worker.start()
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.status_text.set("监控中")

    def _stop(self) -> None:
        self.stop_event.set()
        self.status_text.set("正在停止")

    def _watch_loop(self, config: WatchConfig) -> None:
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = True
        already_seen = False
        last_click_at = 0.0
        last_report_at = 0.0

        try:
            template = load_template(config.template)
            search_label = (
                "全屏"
                if config.region is None
                else f"({config.region.x},{config.region.y},{config.region.width},{config.region.height})"
            )
            self._log(
                f"开始搜索目标图片，范围={search_label}，"
                f"阈值={config.threshold:.2f}"
            )
            while not self.stop_event.is_set():
                match = find_template(screenshot_region(config.region), template)
                matched = match.score >= config.threshold
                now = time.monotonic()

                if should_click(matched, already_seen, config.repeat, last_click_at, config.cooldown):
                    click_point = self._click_point(config, match)
                    origin = region_origin(config.region)
                    top_left = Point(origin.x + match.top_left.x, origin.y + match.top_left.y)
                    self._log(f"匹配成功 score={match.score:.3f}，模板左上角=({top_left.x},{top_left.y})")
                    if config.dry_run:
                        self._log("测试模式：不移动鼠标、不点击")
                    else:
                        pyautogui.moveTo(click_point.x, click_point.y, duration=0.05)
                        pyautogui.click()
                        self._log(f"已点击 ({click_point.x},{click_point.y})")
                    last_click_at = time.monotonic()
                    if config.once:
                        break

                already_seen = matched
                if now - last_report_at >= 2:
                    self._set_status(f"监控中 score={match.score:.3f}")
                    last_report_at = now
                self.stop_event.wait(config.interval)
        except pyautogui.FailSafeException:
            self._log("已触发急停：鼠标移动到了屏幕左上角")
        except Exception as exc:
            self._log(f"监控失败：{exc}")
        finally:
            self.after(0, self._mark_stopped)

    def _mark_stopped(self) -> None:
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.status_text.set("已停止")
        self._log("已停止")


def main() -> int:
    app = ScreenClickerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

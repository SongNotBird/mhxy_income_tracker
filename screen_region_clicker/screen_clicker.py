#!/usr/bin/env python3
"""Watch a screen region and click when a template image appears."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, NamedTuple

try:
    import cv2
    import numpy as np
    import pyautogui
except ModuleNotFoundError as exc:
    print(
        "缺少依赖，请先运行：\n"
        "  cd /Users/qinliuyu/Documents/小工具/screen_region_clicker\n"
        "  python3 -m venv .venv\n"
        "  source .venv/bin/activate\n"
        "  pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


class Box(NamedTuple):
    x: int
    y: int
    width: int
    height: int


class Point(NamedTuple):
    x: int
    y: int


class MatchResult(NamedTuple):
    score: float
    top_left: Point
    size: tuple[int, int]


def parse_ints(value: str, expected: int, label: str) -> tuple[int, ...]:
    try:
        parts = tuple(int(item.strip()) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{label} 必须是逗号分隔的整数") from exc

    if len(parts) != expected:
        raise argparse.ArgumentTypeError(f"{label} 需要 {expected} 个数字")
    return parts


def parse_box(value: str) -> Box:
    x, y, width, height = parse_ints(value, 4, "区域")
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("区域宽高必须大于 0")
    return Box(x, y, width, height)


def parse_point(value: str) -> Point:
    x, y = parse_ints(value, 2, "坐标")
    return Point(x, y)


def screenshot_region(region: Box | None) -> np.ndarray:
    screenshot = pyautogui.screenshot(region=region)
    return np.asarray(screenshot)


def load_template(path: Path) -> np.ndarray:
    template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise SystemExit(f"无法读取模板图片：{path}")
    return template


def find_template(region_image: np.ndarray, template: np.ndarray) -> MatchResult:
    gray = cv2.cvtColor(region_image, cv2.COLOR_RGB2GRAY)
    template_height, template_width = template.shape[:2]
    image_height, image_width = gray.shape[:2]

    if template_width > image_width or template_height > image_height:
        raise SystemExit("模板图片不能大于监控区域，请缩小模板或增大 --region")

    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_score, _, max_location = cv2.minMaxLoc(result)
    return MatchResult(
        score=float(max_score),
        top_left=Point(max_location[0], max_location[1]),
        size=(template_width, template_height),
    )


def resolve_click_point(args: argparse.Namespace, region: Box, match: MatchResult) -> Point | None:
    if args.click is not None:
        return args.click

    if args.click_offset is not None:
        return Point(
            region.x + match.top_left.x + args.click_offset.x,
            region.y + match.top_left.y + args.click_offset.y,
        )

    if args.click_center:
        template_width, template_height = match.size
        return Point(
            region.x + match.top_left.x + template_width // 2,
            region.y + match.top_left.y + template_height // 2,
        )

    return None


def print_status(message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def command_position(args: argparse.Namespace) -> int:
    print("移动鼠标查看坐标，按 Ctrl+C 停止。", flush=True)
    try:
        while True:
            x, y = pyautogui.position()
            sys.stdout.write(f"\rX={x:<5} Y={y:<5}")
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print()
        return 0


def command_capture(args: argparse.Namespace) -> int:
    region = args.region
    output = args.out.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    image = pyautogui.screenshot(region=region)
    image.save(output)
    print(f"已保存：{output}")
    print(f"图片尺寸：{image.size[0]}x{image.size[1]}")
    return 0


def should_click(matched: bool, already_seen: bool, repeat: bool, last_click_at: float, cooldown: float) -> bool:
    if not matched:
        return False
    if repeat and time.monotonic() - last_click_at >= cooldown:
        return True
    return not already_seen and time.monotonic() - last_click_at >= cooldown


def command_watch(args: argparse.Namespace) -> int:
    region = args.region
    template = load_template(args.template.expanduser().resolve())

    if not 0 <= args.threshold <= 1:
        raise SystemExit("--threshold 必须在 0 到 1 之间")
    if args.interval <= 0 or args.cooldown < 0:
        raise SystemExit("--interval 必须大于 0，--cooldown 不能小于 0")

    click_point_hint = resolve_click_point(
        args,
        region,
        MatchResult(score=0.0, top_left=Point(0, 0), size=(template.shape[1], template.shape[0])),
    )
    if click_point_hint is None and not args.dry_run:
        raise SystemExit("请指定 --click、--click-offset 或 --click-center 其中之一")

    pyautogui.PAUSE = 0
    pyautogui.FAILSAFE = not args.no_failsafe

    print_status(
        f"开始监控区域 x={region.x}, y={region.y}, w={region.width}, h={region.height}；"
        f"阈值={args.threshold:.2f}；按 Ctrl+C 停止"
    )

    already_seen = False
    last_click_at = 0.0
    last_report_at = 0.0

    try:
        while True:
            region_image = screenshot_region(region)
            match = find_template(region_image, template)
            matched = match.score >= args.threshold

            if should_click(matched, already_seen, args.repeat, last_click_at, args.cooldown):
                click_point = resolve_click_point(args, region, match)
                top_left_abs = Point(region.x + match.top_left.x, region.y + match.top_left.y)
                print_status(
                    f"匹配成功 score={match.score:.3f}，模板左上角=({top_left_abs.x},{top_left_abs.y})"
                )

                if args.dry_run:
                    print_status("dry-run 模式：不移动鼠标、不点击")
                else:
                    assert click_point is not None
                    if args.pre_click_delay > 0:
                        time.sleep(args.pre_click_delay)
                    pyautogui.moveTo(click_point.x, click_point.y, duration=args.move_duration)
                    pyautogui.click(button=args.button)
                    print_status(f"已点击 ({click_point.x},{click_point.y})")

                last_click_at = time.monotonic()
                if args.once:
                    return 0

            already_seen = matched

            if args.verbose:
                now = time.monotonic()
                if now - last_report_at >= args.report_interval:
                    print_status(f"当前最高匹配 score={match.score:.3f}")
                    last_report_at = now

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print_status("已停止")
        return 0


def add_click_options(parser: argparse.ArgumentParser) -> None:
    click_group = parser.add_mutually_exclusive_group()
    click_group.add_argument(
        "--click",
        type=parse_point,
        metavar="X,Y",
        help="点击绝对屏幕坐标，例如 900,650",
    )
    click_group.add_argument(
        "--click-offset",
        type=parse_point,
        metavar="DX,DY",
        help="点击模板左上角的相对偏移，例如 120,40",
    )
    click_group.add_argument(
        "--click-center",
        action="store_true",
        help="点击匹配到的模板中心点",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="监控屏幕指定区域，匹配到模板界面后自动点击。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pos_parser = subparsers.add_parser("pos", help="持续显示当前鼠标坐标")
    pos_parser.add_argument("--interval", type=float, default=0.2, help="刷新间隔秒数")
    pos_parser.set_defaults(func=command_position)

    capture_parser = subparsers.add_parser("capture", help="截取模板图片或调试截图")
    capture_parser.add_argument("--region", type=parse_box, help="截图区域：X,Y,W,H；不填则截全屏")
    capture_parser.add_argument("--out", type=Path, required=True, help="输出图片路径")
    capture_parser.set_defaults(func=command_capture)

    watch_parser = subparsers.add_parser("watch", help="监控区域并在匹配时点击")
    watch_parser.add_argument("--region", type=parse_box, required=True, help="监控区域：X,Y,W,H")
    watch_parser.add_argument("--template", type=Path, required=True, help="目标界面的模板图片")
    watch_parser.add_argument("--threshold", type=float, default=0.88, help="匹配阈值，建议 0.80-0.95")
    watch_parser.add_argument("--interval", type=float, default=0.25, help="每次检测间隔秒数")
    watch_parser.add_argument("--cooldown", type=float, default=3.0, help="两次点击之间的最短间隔秒数")
    watch_parser.add_argument("--once", action="store_true", help="点击一次后退出")
    watch_parser.add_argument("--repeat", action="store_true", help="目标持续存在时也按冷却时间重复点击")
    watch_parser.add_argument("--dry-run", action="store_true", help="只打印匹配结果，不点击")
    watch_parser.add_argument("--pre-click-delay", type=float, default=0.0, help="匹配成功后点击前等待秒数")
    watch_parser.add_argument("--move-duration", type=float, default=0.05, help="鼠标移动耗时秒数")
    watch_parser.add_argument("--button", choices=("left", "right", "middle"), default="left", help="点击按键")
    watch_parser.add_argument("--no-failsafe", action="store_true", help="关闭 pyautogui 左上角急停")
    watch_parser.add_argument("--verbose", action="store_true", help="定期打印当前匹配分数")
    watch_parser.add_argument("--report-interval", type=float, default=2.0, help="verbose 输出间隔秒数")
    add_click_options(watch_parser)
    watch_parser.set_defaults(func=command_watch)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

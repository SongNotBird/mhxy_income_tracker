from __future__ import annotations

from typing import NamedTuple


class Box(NamedTuple):
    x: int
    y: int
    width: int
    height: int


class Point(NamedTuple):
    x: int
    y: int


def format_monitor_label(index: int, bounds: Box) -> str:
    return f"屏幕 {index + 1} ({bounds.width}x{bounds.height}, X={bounds.x}, Y={bounds.y})"


def clamp_point_to_bounds(point: Point, bounds: Box) -> Point:
    return Point(
        min(max(point.x, bounds.x), bounds.x + bounds.width),
        min(max(point.y, bounds.y), bounds.y + bounds.height),
    )


def box_within(inner: Box, outer: Box) -> bool:
    return (
        inner.x >= outer.x
        and inner.y >= outer.y
        and inner.x + inner.width <= outer.x + outer.width
        and inner.y + inner.height <= outer.y + outer.height
    )


def fitted_preview_size(image_size: tuple[int, int], max_size: tuple[int, int]) -> tuple[int, int]:
    image_width, image_height = image_size
    max_width, max_height = max_size
    scale = min(max_width / image_width, max_height / image_height, 1.0)
    return max(1, int(image_width * scale)), max(1, int(image_height * scale))


def clamp_preview_point(point: Point, preview_size: tuple[int, int]) -> Point:
    preview_width, preview_height = preview_size
    return Point(
        min(max(point.x, 0), preview_width),
        min(max(point.y, 0), preview_height),
    )


def preview_to_screen_point(point: Point, bounds: Box, preview_size: tuple[int, int]) -> Point:
    preview_width, preview_height = preview_size
    preview_point = clamp_preview_point(point, preview_size)
    x_ratio = preview_point.x / preview_width
    y_ratio = preview_point.y / preview_height
    return Point(
        bounds.x + round(bounds.width * x_ratio),
        bounds.y + round(bounds.height * y_ratio),
    )


def preview_to_screen_box(start: Point, end: Point, bounds: Box, preview_size: tuple[int, int]) -> Box:
    start_screen = preview_to_screen_point(start, bounds, preview_size)
    end_screen = preview_to_screen_point(end, bounds, preview_size)
    left = min(start_screen.x, end_screen.x)
    top = min(start_screen.y, end_screen.y)
    right = max(start_screen.x, end_screen.x)
    bottom = max(start_screen.y, end_screen.y)
    return Box(left, top, right - left, bottom - top)

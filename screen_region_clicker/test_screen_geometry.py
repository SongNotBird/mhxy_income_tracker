from __future__ import annotations

import unittest

from screen_geometry import (
    Box,
    Point,
    box_within,
    fitted_preview_size,
    format_monitor_label,
    preview_to_screen_box,
    preview_to_screen_point,
)


class ScreenGeometryTests(unittest.TestCase):
    def test_monitor_labels_keep_screen_origins(self) -> None:
        monitors = [
            Box(0, 0, 1920, 1080),
            Box(1920, 0, 2560, 1440),
            Box(-1280, 120, 1280, 1024),
        ]

        self.assertEqual(format_monitor_label(0, monitors[0]), "屏幕 1 (1920x1080, X=0, Y=0)")
        self.assertEqual(format_monitor_label(1, monitors[1]), "屏幕 2 (2560x1440, X=1920, Y=0)")
        self.assertEqual(format_monitor_label(2, monitors[2]), "屏幕 3 (1280x1024, X=-1280, Y=120)")

    def test_preview_point_maps_to_selected_screen_origin(self) -> None:
        preview_size = (640, 360)

        self.assertEqual(
            preview_to_screen_point(Point(320, 180), Box(0, 0, 1920, 1080), preview_size),
            Point(960, 540),
        )
        self.assertEqual(
            preview_to_screen_point(Point(320, 180), Box(1920, 0, 2560, 1440), preview_size),
            Point(3200, 720),
        )
        self.assertEqual(
            preview_to_screen_point(Point(320, 180), Box(-1280, 120, 1280, 1024), preview_size),
            Point(-640, 632),
        )

    def test_preview_box_maps_to_distinct_screens(self) -> None:
        preview_size = (1000, 500)
        start = Point(100, 50)
        end = Point(400, 250)

        primary = preview_to_screen_box(start, end, Box(0, 0, 1920, 1080), preview_size)
        right = preview_to_screen_box(start, end, Box(1920, 0, 2560, 1440), preview_size)
        left = preview_to_screen_box(start, end, Box(-1280, 120, 1280, 1024), preview_size)

        self.assertEqual(primary, Box(192, 108, 576, 432))
        self.assertEqual(right, Box(2176, 144, 768, 576))
        self.assertEqual(left, Box(-1152, 222, 384, 410))

        self.assertNotEqual(primary.x, right.x)
        self.assertNotEqual(primary.x, left.x)

    def test_preview_points_are_clamped_to_selected_screen(self) -> None:
        bounds = Box(1920, 0, 2560, 1440)
        preview_size = (640, 360)

        self.assertEqual(preview_to_screen_point(Point(-50, -20), bounds, preview_size), Point(1920, 0))
        self.assertEqual(preview_to_screen_point(Point(700, 400), bounds, preview_size), Point(4480, 1440))

    def test_region_validation_uses_selected_screen(self) -> None:
        selected = Box(1920, 0, 2560, 1440)

        self.assertTrue(box_within(Box(2000, 100, 500, 300), selected))
        self.assertFalse(box_within(Box(100, 100, 500, 300), selected))
        self.assertFalse(box_within(Box(4400, 100, 500, 300), selected))

    def test_preview_size_preserves_ratio(self) -> None:
        self.assertEqual(fitted_preview_size((2560, 1440), (1200, 760)), (1200, 675))
        self.assertEqual(fitted_preview_size((800, 600), (1200, 760)), (800, 600))


if __name__ == "__main__":
    unittest.main()

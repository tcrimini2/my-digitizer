import unittest
import io

from PIL import Image

from digitizer import (
    calibration_is_valid,
    csv_bytes,
    data_to_pixel,
    draw_view,
    load_uploaded_image,
    new_calibration,
    new_dataset,
    pixel_to_data,
)


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.calibration = {
            "origin": (100.0, 400.0),
            "x_reference": (300.0, 380.0),
            "y_reference": (120.0, 200.0),
        }
        self.axis_values = {"x": (0.0, 10.0), "y": (0.0, 20.0)}
        self.scales = {"x": "Linear", "y": "Linear"}

    def test_round_trip_accounts_for_rotated_axes(self):
        pixel = data_to_pixel(4.0, 12.0, self.calibration, self.axis_values, self.scales)
        self.assertAlmostEqual(pixel[0], 192.0)
        self.assertAlmostEqual(pixel[1], 272.0)
        values = pixel_to_data(pixel, self.calibration, self.axis_values, self.scales)
        self.assertAlmostEqual(values[0], 4.0)
        self.assertAlmostEqual(values[1], 12.0)

    def test_logarithmic_calibration_and_conversion(self):
        axis_values = {"x": (1.0, 100.0), "y": (0.1, 10.0)}
        scales = {"x": "Logarithmic", "y": "Logarithmic"}
        self.assertTrue(calibration_is_valid(self.calibration, axis_values, scales))
        pixel = data_to_pixel(10.0, 1.0, self.calibration, axis_values, scales)
        values = pixel_to_data(pixel, self.calibration, axis_values, scales)
        self.assertAlmostEqual(values[0], 10.0)
        self.assertAlmostEqual(values[1], 1.0)

    def test_logarithmic_calibration_rejects_zero_values(self):
        scales = {"x": "Logarithmic", "y": "Linear"}
        self.assertFalse(calibration_is_valid(self.calibration, self.axis_values, scales))

    def test_collinear_calibration_is_invalid(self):
        calibration = {
            "origin": (0.0, 0.0),
            "x_reference": (1.0, 1.0),
            "y_reference": (2.0, 2.0),
        }
        self.assertFalse(calibration_is_valid(calibration, self.axis_values, self.scales))

    def test_csv_has_two_header_rows_and_aligned_datasets(self):
        datasets = [
            {
                "name": "First",
                "points": [(100.0, 400.0), (300.0, 380.0)],
            },
            {"name": "Second", "points": [(120.0, 200.0)]},
        ]
        result = csv_bytes(
            datasets,
            "Time",
            "Voltage",
            self.calibration,
            self.axis_values,
            self.scales,
        ).decode("utf-8-sig")
        self.assertEqual(
            result.splitlines(),
            [
                "First,,Second,",
                "Time,Voltage,Time,Voltage",
                "0,0,0,20",
                "10,0,,",
            ],
        )

    def test_grayscale_upload_is_converted_to_color(self):
        image = Image.new("L", (20, 10), color=128)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        loaded = load_uploaded_image(buffer.getvalue())
        self.assertEqual(loaded.mode, "RGB")
        self.assertEqual(loaded.size, (20, 10))

    def test_zoom_keeps_viewer_size_while_changing_crop(self):
        image = Image.new("RGB", (800, 400), color="white")
        calibration = new_calibration()
        normal_view, normal_crop = draw_view(image, [], calibration, 1, 50, 50, 1600)
        zoomed_view, zoomed_crop = draw_view(image, [], calibration, 2, 50, 50, 1600)
        self.assertEqual(normal_view.size, zoomed_view.size)
        self.assertNotEqual(normal_crop, zoomed_crop)

    def test_dataset_colors_do_not_repeat_after_initial_palette(self):
        colors = {new_dataset(number)["color"] for number in range(1, 12)}
        self.assertEqual(len(colors), 11)


if __name__ == "__main__":
    unittest.main()

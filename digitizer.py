import csv
import colorsys
import io
import math
from typing import Any, TypedDict

from PIL import Image, ImageDraw, ImageOps


class Calibration(TypedDict):
    origin: tuple[float, float] | None
    x_reference: tuple[float, float] | None
    y_reference: tuple[float, float] | None


class CompleteCalibration(TypedDict):
    origin: tuple[float, float]
    x_reference: tuple[float, float]
    y_reference: tuple[float, float]


COLORS = [
    "#E4572E",
    "#3977C5",
    "#2A9D70",
    "#8B5CF6",
    "#D18B00",
    "#D14D8B",
    "#168C9B",
    "#697386",
]


def new_calibration() -> Calibration:
    return {
        "origin": None,
        "x_reference": None,
        "y_reference": None,
    }


def get_complete_calibration(calibration: Calibration) -> CompleteCalibration | None:
    origin = calibration["origin"]
    x_reference = calibration["x_reference"]
    y_reference = calibration["y_reference"]
    if origin is None or x_reference is None or y_reference is None:
        return None
    return {
        "origin": origin,
        "x_reference": x_reference,
        "y_reference": y_reference,
    }


def set_calibration_point(
    calibration: Calibration, key: str, point: tuple[float, float]
) -> None:
    if key == "origin":
        calibration["origin"] = point
    elif key == "x_reference":
        calibration["x_reference"] = point
    elif key == "y_reference":
        calibration["y_reference"] = point
    else:
        raise ValueError(f"Unknown calibration point: {key}")


def new_dataset(number: int) -> dict[str, Any]:
    if number <= len(COLORS):
        color = COLORS[number - 1]
    else:
        hue = (0.137 + (number - len(COLORS) - 1) * 0.618033988749895) % 1
        red, green, blue = colorsys.hsv_to_rgb(hue, 0.78, 0.9)
        color = f"#{round(red * 255):02X}{round(green * 255):02X}{round(blue * 255):02X}"
    return {
        "id": f"dataset-{number}",
        "name": f"Dataset {number}",
        "color": color,
        "points": [],
        "revision": 0,
    }


def transformed_value(value: float, scale: str) -> float:
    if scale == "Logarithmic":
        if value <= 0:
            raise ValueError("Logarithmic axis calibration values must be positive.")
        return math.log10(value)
    return value


def data_to_pixel(
    x: float,
    y: float,
    calibration: CompleteCalibration,
    axis_values: dict[str, tuple[float, float]],
    scales: dict[str, str],
) -> tuple[float, float]:
    origin = calibration["origin"]
    x_reference = calibration["x_reference"]
    y_reference = calibration["y_reference"]
    x_axis = (x_reference[0] - origin[0], x_reference[1] - origin[1])
    y_axis = (y_reference[0] - origin[0], y_reference[1] - origin[1])
    determinant = x_axis[0] * y_axis[1] - x_axis[1] * y_axis[0]
    if math.isclose(determinant, 0.0, abs_tol=1e-10):
        raise ValueError("The calibration points must not lie on one straight line.")

    x0, x1 = (transformed_value(value, scales["x"]) for value in axis_values["x"])
    y0, y1 = (transformed_value(value, scales["y"]) for value in axis_values["y"])
    x_fraction = (transformed_value(x, scales["x"]) - x0) / (x1 - x0)
    y_fraction = (transformed_value(y, scales["y"]) - y0) / (y1 - y0)
    return (
        origin[0] + x_fraction * x_axis[0] + y_fraction * y_axis[0],
        origin[1] + x_fraction * x_axis[1] + y_fraction * y_axis[1],
    )


def pixel_to_data(
    pixel: tuple[float, float],
    calibration: CompleteCalibration,
    axis_values: dict[str, tuple[float, float]],
    scales: dict[str, str],
) -> tuple[float, float]:
    origin = calibration["origin"]
    x_reference = calibration["x_reference"]
    y_reference = calibration["y_reference"]
    x_axis = (x_reference[0] - origin[0], x_reference[1] - origin[1])
    y_axis = (y_reference[0] - origin[0], y_reference[1] - origin[1])
    determinant = x_axis[0] * y_axis[1] - x_axis[1] * y_axis[0]
    if math.isclose(determinant, 0.0, abs_tol=1e-10):
        raise ValueError("The calibration points must not lie on one straight line.")

    relative = (pixel[0] - origin[0], pixel[1] - origin[1])
    x_fraction = (relative[0] * y_axis[1] - relative[1] * y_axis[0]) / determinant
    y_fraction = (x_axis[0] * relative[1] - x_axis[1] * relative[0]) / determinant
    x0, x1 = (transformed_value(value, scales["x"]) for value in axis_values["x"])
    y0, y1 = (transformed_value(value, scales["y"]) for value in axis_values["y"])
    x_transformed = x0 + x_fraction * (x1 - x0)
    y_transformed = y0 + y_fraction * (y1 - y0)
    x = 10**x_transformed if scales["x"] == "Logarithmic" else x_transformed
    y = 10**y_transformed if scales["y"] == "Logarithmic" else y_transformed
    return x, y


def calibration_is_valid(
    calibration: Calibration,
    axis_values: dict[str, tuple[float, float]],
    scales: dict[str, str],
) -> bool:
    origin = calibration.get("origin")
    x_reference = calibration.get("x_reference")
    y_reference = calibration.get("y_reference")
    if origin is None or x_reference is None or y_reference is None:
        return False
    try:
        for axis in ("x", "y"):
            first, second = axis_values[axis]
            if not math.isfinite(first) or not math.isfinite(second):
                return False
            transformed_first = transformed_value(first, scales[axis])
            transformed_second = transformed_value(second, scales[axis])
            if math.isclose(transformed_first, transformed_second):
                return False
    except (ValueError, ZeroDivisionError):
        return False
    x_axis = (x_reference[0] - origin[0], x_reference[1] - origin[1])
    y_axis = (y_reference[0] - origin[0], y_reference[1] - origin[1])
    determinant = x_axis[0] * y_axis[1] - x_axis[1] * y_axis[0]
    return not math.isclose(determinant, 0.0, abs_tol=1e-10)


def csv_bytes(
    datasets: list[dict[str, Any]],
    x_label: str,
    y_label: str,
    calibration: CompleteCalibration,
    axis_values: dict[str, tuple[float, float]],
    scales: dict[str, str],
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([value for dataset in datasets for value in (dataset["name"], "")])
    writer.writerow([value for _ in datasets for value in (x_label, y_label)])
    data_rows = [
        [pixel_to_data(point, calibration, axis_values, scales) for point in dataset["points"]]
        for dataset in datasets
    ]
    for row_index in range(max((len(rows) for rows in data_rows), default=0)):
        row: list[str] = []
        for rows in data_rows:
            if row_index < len(rows):
                row.extend(format(value, ".12g") for value in rows[row_index])
            else:
                row.extend(("", ""))
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


def load_uploaded_image(uploaded_bytes: bytes) -> Image.Image:
    with Image.open(io.BytesIO(uploaded_bytes)) as source:
        source.seek(0)
        image = ImageOps.exif_transpose(source)
        return image.convert("RGB")


def draw_view(
    image: Image.Image,
    datasets: list[dict[str, Any]],
    calibration: Calibration,
    zoom: float,
    pan_x: int,
    pan_y: int,
    display_width: int,
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    image_width, image_height = image.size
    crop_width = max(1, round(image_width / zoom))
    crop_height = max(1, round(image_height / zoom))
    left = round((image_width - crop_width) * pan_x / 100)
    top = round((image_height - crop_height) * pan_y / 100)
    box = (left, top, left + crop_width, top + crop_height)
    view = image.crop(box)
    view_height = max(1, round(display_width * crop_height / crop_width))
    view = view.resize((display_width, view_height), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(view)
    scale_x = display_width / crop_width
    scale_y = view_height / crop_height
    radius = max(4, round(display_width / 180))

    for dataset in datasets:
        for x, y in dataset["points"]:
            view_x = round((x - left) * scale_x)
            view_y = round((y - top) * scale_y)
            if 0 <= view_x < display_width and 0 <= view_y < view_height:
                draw.ellipse(
                    (view_x - radius, view_y - radius, view_x + radius, view_y + radius),
                    fill=dataset["color"],
                    outline="white",
                    width=max(1, radius // 3),
                )

    marker_labels = (("origin", "O"), ("x_reference", "X"), ("y_reference", "Y"))
    for key, label in marker_labels:
        point = calibration.get(key)
        if point is None:
            continue
        view_x = round((point[0] - left) * scale_x)
        view_y = round((point[1] - top) * scale_y)
        if 0 <= view_x < display_width and 0 <= view_y < view_height:
            draw.ellipse(
                (view_x - radius, view_y - radius, view_x + radius, view_y + radius),
                fill="#111827",
                outline="white",
                width=max(1, radius // 3),
            )
            draw.text((view_x + radius + 2, view_y - radius - 2), label, fill="#111827")
    return view, box

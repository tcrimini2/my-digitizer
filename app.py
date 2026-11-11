import hashlib
import math

import pandas as pd
import streamlit as st
from PIL import UnidentifiedImageError
from streamlit_image_coordinates import streamlit_image_coordinates

from digitizer import (
    calibration_is_valid,
    csv_bytes,
    data_to_pixel,
    draw_view,
    get_complete_calibration,
    load_uploaded_image,
    new_calibration,
    new_dataset,
    pixel_to_data,
    set_calibration_point,
)


def delete_active_dataset() -> None:
    active_id = st.session_state.active_dataset
    st.session_state.datasets = [
        dataset
        for dataset in st.session_state.datasets
        if dataset["id"] != active_id
    ]
    st.session_state.active_dataset = st.session_state.datasets[0]["id"]

st.set_page_config(page_title="Plot Digitizer", page_icon="📈", layout="wide")
st.title("Plot Digitizer")
st.caption("Calibrate a graph image, click its data points, and export the digitized values.")

if "datasets" not in st.session_state:
    st.session_state.datasets = [new_dataset(1)]
    st.session_state.next_dataset_number = 2
    st.session_state.active_dataset = "dataset-1"
    st.session_state.calibration = new_calibration()
    st.session_state.calibration_mode = None
    st.session_state.last_click_event = None
    st.session_state.image_id = None
    st.session_state.image_bytes = None

with st.sidebar:
    st.header("1. Graph image")
    uploaded_file = st.file_uploader(
        "Upload a graph",
        type=["png", "jpg", "jpeg", "gif", "tif", "tiff"],
        help="PNG, JPEG, GIF, and TIFF images are supported. The first frame of an animation is used.",
    )
    if uploaded_file is not None:
        uploaded_bytes = uploaded_file.getvalue()
        image_id = hashlib.sha256(uploaded_bytes).hexdigest()
        if image_id != st.session_state.image_id:
            try:
                load_uploaded_image(uploaded_bytes)
            except (UnidentifiedImageError, OSError, ValueError) as error:
                st.error(f"Could not read this image: {error}")
                st.stop()
            st.session_state.image_id = image_id
            st.session_state.image_bytes = uploaded_bytes
            st.session_state.calibration = new_calibration()
            st.session_state.calibration_mode = None
            st.session_state.datasets = [new_dataset(1)]
            st.session_state.next_dataset_number = 2
            st.session_state.active_dataset = "dataset-1"
            st.session_state.last_click_event = None

    st.header("2. Axis settings")
    x_label = st.text_input("X-axis label", value="x", key="x_label")
    y_label = st.text_input("Y-axis label", value="y", key="y_label")
    x_scale = st.selectbox("X-axis scale", ["Linear", "Logarithmic"], key="x_scale")
    y_scale = st.selectbox("Y-axis scale", ["Linear", "Logarithmic"], key="y_scale")

    st.subheader("Calibration values")
    st.caption("Enter the values at the clicked axis intersection and reference ticks.")
    value_columns = st.columns(2)
    with value_columns[0]:
        x_at_origin = st.number_input("X at origin", value=0.0, key="x_at_origin")
        x_at_reference = st.number_input("X at X reference", value=1.0, key="x_at_reference")
    with value_columns[1]:
        y_at_origin = st.number_input("Y at origin", value=0.0, key="y_at_origin")
        y_at_reference = st.number_input("Y at Y reference", value=1.0, key="y_at_reference")

    st.header("3. Datasets")
    if st.button("Add dataset", use_container_width=True):
        number = st.session_state.next_dataset_number
        dataset = new_dataset(number)
        st.session_state.datasets.append(dataset)
        st.session_state.active_dataset = dataset["id"]
        st.session_state.next_dataset_number += 1

    dataset_ids = [dataset["id"] for dataset in st.session_state.datasets]
    if st.session_state.active_dataset not in dataset_ids:
        st.session_state.active_dataset = dataset_ids[0]
    st.selectbox(
        "Active dataset",
        dataset_ids,
        format_func=lambda dataset_id: next(
            dataset["name"] for dataset in st.session_state.datasets if dataset["id"] == dataset_id
        ),
        key="active_dataset",
    )
    active_dataset = next(
        dataset
        for dataset in st.session_state.datasets
        if dataset["id"] == st.session_state.active_dataset
    )
    active_dataset["name"] = st.text_input(
        "Dataset name",
        value=active_dataset["name"],
        key=f"name_{active_dataset['id']}",
    )
    if len(st.session_state.datasets) > 1:
        st.button(
            "Delete active dataset",
            use_container_width=True,
            on_click=delete_active_dataset,
        )

if st.session_state.image_bytes is None:
    st.info("Upload a graph image in the sidebar to get started.")
    st.stop()

try:
    source_image = load_uploaded_image(st.session_state.image_bytes)
except (UnidentifiedImageError, OSError, ValueError) as error:
    st.error(f"Could not read this image: {error}")
    st.stop()

calibration = st.session_state.calibration
axis_values = {
    "x": (x_at_origin, x_at_reference),
    "y": (y_at_origin, y_at_reference),
}
scales = {"x": x_scale, "y": y_scale}
calibrated = calibration_is_valid(calibration, axis_values, scales)

st.subheader("Calibrate the graph")
st.write(
    "Select each calibration target, then click its location in the image. "
    "Use the axis intersection for the origin; the reference clicks should lie along their axes."
)
calibration_buttons = st.columns(4)
calibration_targets = [
    ("origin", "Set origin"),
    ("x_reference", "Set X reference"),
    ("y_reference", "Set Y reference"),
]
for column, (key, label) in zip(calibration_buttons, calibration_targets):
    with column:
        if st.button(label, type="primary" if st.session_state.calibration_mode == key else "secondary"):
            st.session_state.calibration_mode = key
with calibration_buttons[3]:
    if st.button("Reset calibration"):
        st.session_state.calibration = new_calibration()
        st.session_state.calibration_mode = None
        st.rerun()

if st.session_state.calibration_mode:
    target_label = dict(calibration_targets)[st.session_state.calibration_mode]
    st.info(f"Click the image to set the {target_label.lower()}.")
elif not calibrated:
    st.warning("Set all three calibration points and use distinct values for each axis.")
else:
    st.success("Calibration is ready. Click the image to add points to the active dataset.")

viewer_columns = st.columns([3, 1])
with viewer_columns[1]:
    zoom = st.slider("Zoom", min_value=1.0, max_value=5.0, value=1.0, step=0.25)
    display_width = st.slider("Viewer width (pixels)", 500, 1400, 1000, step=100)
    if zoom > 1:
        pan_x = st.slider("Pan horizontally", 0, 100, 50)
        pan_y = st.slider("Pan vertically", 0, 100, 50)
    else:
        pan_x = 50
        pan_y = 50

view_image, crop_box = draw_view(
    source_image,
    st.session_state.datasets,
    calibration,
    zoom,
    pan_x,
    pan_y,
    display_width,
)

with viewer_columns[0]:
    click_value = streamlit_image_coordinates(view_image, key="graph_click_area")

if click_value is not None:
    click_x = click_value.get("x")
    click_y = click_value.get("y")
    if click_x is not None and click_y is not None:
        event_id = click_value.get(
            "unix_time", click_value.get("time", click_value.get("timestamp"))
        )
        if event_id is None:
            event_id = (click_x, click_y, click_value.get("width"), click_value.get("height"))
        if event_id != st.session_state.last_click_event:
            component_width = click_value.get("width") or view_image.width
            component_height = click_value.get("height") or view_image.height
            left, top, right, bottom = crop_box
            image_point = (
                left + float(click_x) * (right - left) / component_width,
                top + float(click_y) * (bottom - top) / component_height,
            )
            st.session_state.last_click_event = event_id
            if st.session_state.calibration_mode:
                set_calibration_point(
                    calibration, st.session_state.calibration_mode, image_point
                )
                st.session_state.calibration_mode = None
                st.rerun()
            elif calibrated:
                active_dataset["points"].append(image_point)
                active_dataset["revision"] += 1
                st.rerun()
            else:
                st.warning("Calibrate the graph before adding data points.")

calibrated = calibration_is_valid(calibration, axis_values, scales)
complete_calibration = get_complete_calibration(calibration)
if calibrated and complete_calibration is not None:
    st.subheader("Digitized points")
    dataset_columns = st.columns([1, 1, 3])
    with dataset_columns[0]:
        if st.button("Undo last point", disabled=not active_dataset["points"]):
            active_dataset["points"].pop()
            active_dataset["revision"] += 1
            st.rerun()
    with dataset_columns[1]:
        st.write(f"{len(active_dataset['points'])} point(s) in {active_dataset['name']}")

    points = [
        pixel_to_data(point, complete_calibration, axis_values, scales)
        for point in active_dataset["points"]
    ]
    editor_data = pd.DataFrame(points, columns=["x", "y"])
    edited_data = st.data_editor(
        editor_data,
        key=f"points_{active_dataset['id']}_{active_dataset['revision']}",
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "x": st.column_config.NumberColumn(x_label, format="%.8g"),
            "y": st.column_config.NumberColumn(y_label, format="%.8g"),
        },
    )
    edited_points: list[tuple[float, float]] = []
    invalid_rows = False
    for row in edited_data.itertuples(index=False, name=None):
        if pd.isna(row[0]) or pd.isna(row[1]):
            continue
        try:
            edited_points.append(
                data_to_pixel(
                    float(row[0]),
                    float(row[1]),
                    complete_calibration,
                    axis_values,
                    scales,
                )
            )
        except ValueError as error:
            st.error(f"That table value cannot be used with the selected axis scales: {error}")
            invalid_rows = True
            break
    points_changed = len(edited_points) != len(active_dataset["points"]) or any(
        not math.isclose(old, new, rel_tol=0.0, abs_tol=1e-8)
        for old_point, new_point in zip(active_dataset["points"], edited_points)
        for old, new in zip(old_point, new_point)
    )
    if not invalid_rows and points_changed:
        active_dataset["points"] = edited_points
        active_dataset["revision"] += 1
        st.rerun()

    export = csv_bytes(
        st.session_state.datasets,
        x_label,
        y_label,
        complete_calibration,
        axis_values,
        scales,
    )
    st.download_button(
        "Download all datasets as CSV",
        data=export,
        file_name="digitized_data.csv",
        mime="text/csv",
    )

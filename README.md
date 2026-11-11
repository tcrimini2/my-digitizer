# Plot Digitizer

A single-page Streamlit app for extracting data from graph images. It supports PNG, JPEG, GIF, and TIFF uploads, linear or logarithmic axes, rotated/skewed axes, multiple colored datasets, undo/delete actions, zoom and pan, an editable data table, and CSV export.

## Run locally

Python 3.13 and 3.15 are tested. On Windows, create an isolated Python 3.15 environment, install the app dependencies into that environment, and run Streamlit with that same interpreter:

```bash
py -3.15 -m venv .venv315
.\.venv315\Scripts\python.exe -m pip install -r requirements.txt
.\.venv315\Scripts\python.exe -m streamlit run app.py
```

In VS Code, choose `.venv315\Scripts\python.exe` with **Python: Select Interpreter**. Installing dependencies into one Python installation does not install them into other interpreters.

Run the unit tests with:

```bash
.\.venv315\Scripts\python.exe -m unittest -v
```

The same commands work with another supported Python by creating its environment with that interpreter.

## Deploy to Streamlit Community Cloud

1. Push `app.py`, `digitizer.py`, `requirements.txt`, and this README to a GitHub repository.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app from that repository and select `app.py` as the entry point.
3. Wait for the app to finish building, then copy its public URL.
4. Upload both Python files (`app.py` and `digitizer.py`) to LEARN and paste the deployed app URL into the assignment comment box.

## Use

1. Upload a graph image in the sidebar.
2. Choose axis labels, scales, and the values at the axis intersection and reference ticks.
3. Set the origin, X reference, and Y reference by selecting each calibration button and clicking the corresponding location on the image.
4. The image automatically fits the viewer width after upload. Adjust **Zoom** to inspect details and use **Pan** to move around a zoomed image. Click the image to add points to the active dataset. Add, rename, select, or delete datasets in the sidebar.
5. Undo points or edit their values in the table; edited values update the image markers.
6. Download all datasets as CSV. Each dataset occupies two columns; the first row contains dataset names and the second row contains axis labels.

For logarithmic axes, all calibration values must be positive. Axis intersection and reference clicks do not need to be perfectly horizontal or vertical; the app accounts for rotation and skew during calibration.

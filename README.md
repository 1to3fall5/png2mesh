# PNG to 3D Mesh Tool

This is a tool that converts PNG images into 3D mesh models. It generates corresponding 3D models based on the transparency information of the images, and supports real-time preview and export functions.

## Features

- Import PNG images
- Adjustable transparency threshold
- Controllable mesh precision
- Real-time 3D preview
- Export OBJ format models
- Standalone executable program, no need to install dependencies

## Install Dependencies

If you want to run from source code, you need to install the following dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Run the program
2. Click the "Import PNG" button to select a PNG image
3. Adjust the transparency threshold and mesh precision using sliders
4. View the effect in the 3D preview window
5. Click "Export Model" to save as an OBJ file

## Packaging Instructions

Package as a standalone executable file using PyInstaller:

```bash
pyinstaller --onefile --windowed main.py
```
```

</rewritten_file>
# Telescope Camera Control

This application provides a GUI interface for controlling a telescope camera system with optional motor control functionality. The code has been structured to separate the motor control logic from the image processing and GUI components.

## Features

- Live camera feed with zoom capability
- Image stacking
- Exposure and gain control
- Threshold detection
- Level adjustment
- Optional motor control for RA and DEC axes

## File Structure

- `main.py`: Main application with GUI and image processing
- `motor_control.py`: Separate module for motor control functionality
- `temp/`: Directory for temporary image files
- `Pictures/`: Directory for saved stacked images

## Requirements

- Python 3.x
- OpenCV (cv2)
- NumPy
- Pillow (PIL)
- RPi.GPIO (for motor control)
- Tkinter

## Usage

### Basic Usage (No Motors)

```bash
python main.py
```

### With Motor Control

```bash
python main.py --motors
```

## GUI Components

1. Main Image Display
   - Shows live camera feed or stacked image
   - Click to set zoom position

2. Zoom Window
   - Shows detailed view of selected region
   - Threshold detection for star tracking

3. Control Panel
   - Exposure control
   - Gain adjustment
   - Stack controls (Reset, Save, Show Stack)
   - Image adjustment controls

## Motor Control

The motor control system is completely separated from the main application and can be enabled with the `--motors` flag. When enabled, it provides:

- RA (Right Ascension) motor control
- DEC (Declination) motor control
- Tracking capabilities
- Manual movement controls

The motor control system uses the Raspberry Pi GPIO pins:
- RA Motor: GPIO pins 6, 13, 19, 26
- DEC Motor: GPIO pins 12, 16, 20, 21

## Contributing

Feel free to submit issues and enhancement requests!
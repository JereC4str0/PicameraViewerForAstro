# main.py
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import cv2
import numpy as np
import subprocess
import threading
import time
import datetime
import argparse
from motor_control import MotorController

class TelescopeCamera:
    def __init__(self, use_motors=False):
        self.use_motors = use_motors
        if use_motors:
            self.motor_controller = MotorController()
        
        # Initialize camera parameters
        self.exp_sec = 0.25
        self.exp_mic_sec = int(self.exp_sec * 1000000)
        self.analog_gain = 16
        
        # Image processing parameters
        self.sensor_w = 4056
        self.sensor_h = 3040
        self.x_zoom_center = int(self.sensor_w/2)
        self.y_zoom_center = int(self.sensor_h/2)
        self.zoom_window_hw = 128
        
        # Camera state
        self.run_camera = 1
        self.capture = 2
        self.cap_read = 2
        self.image_ready = 0
        
        # Initialize image arrays
        self.frame_image = None
        self.stack_image = None
        self.stack_counter = 0
        self.stack_busy = 0
        
        # Image processing flags
        self.threshold_enabled = 0
        self.threshold_value = 128
        self.stack_show = 0
        self.level_adjust = 0
        self.dark_mode = 0
        
        # Setup initial camera configuration
        self._setup_camera()
        
        # Start camera threads
        self.capture_thread = threading.Thread(target=self._run_camera)
        self.convert_thread = threading.Thread(target=self._convert_raw)
        self.capture_thread.start()
        self.convert_thread.start()
        
        # Create GUI
        self._setup_gui()

    def _setup_camera(self):
        # Set DPC mode
        try:
            subprocess.check_call("sudo vcdbg set imx477_dpc 3", shell=True)
            print("DPC is Set")
        except:
            print("DPC is NOT Set")
            
        # Capture initial images
        self._capture_initial_images()

    def _capture_initial_images(self):
        raspistill = 'raspistill -md 3 -ex off -awb off -awbg 1.6,1.7 -drc off -st -t 60 -bm -r -n -q 70 '
        
        for i in range(1, 3):
            cmd = f"{raspistill} -o temp/capture{i}.jpg -ss {self.exp_mic_sec} -ag {self.analog_gain}"
            try:
                subprocess.check_call(cmd, shell=True)
                print(f"Pre Capture {i} at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                print("Capture Error")

    def _create_image_frame(self):
        self.image_frame = tk.Frame(self.window, width=1280, height=720)
        self.image_frame.grid(row=0, column=0, rowspan=3, padx=2, pady=2)
        
        # Main image display
        self.main_image_label = tk.Label(self.image_frame)
        self.main_image_label.grid(row=0, rowspan=10, column=1, columnspan=3)
        
        # Zoom window
        self.zoom_frame = tk.Frame(self.window, width=self.zoom_window_hw*2, height=self.zoom_window_hw*2)
        self.zoom_frame.grid(row=0, column=1, padx=2, pady=2)
        self.zoom_image_label = tk.Label(self.zoom_frame)
        self.zoom_image_label.grid(row=0, column=0, columnspan=4)

    def _create_control_frame(self):
        self.control_frame = tk.Frame(self.window)
        self.control_frame.grid(row=1, column=1, padx=2, pady=2)
        
        # Exposure controls
        self._create_exposure_controls()
        
        # Stack controls
        self._create_stack_controls()
        
        # Image adjustment controls
        self._create_adjustment_controls()

    def _create_exposure_controls(self):
        # Exposure time control
        exp_frame = tk.LabelFrame(self.control_frame, text="Exposure")
        exp_frame.pack(fill="x", padx=5, pady=5)
        
        self.exp_scale = tk.Scale(exp_frame, from_=-8, to=5, resolution=0.5,
                                 orient="horizontal", command=self._change_exposure)
        self.exp_scale.set(-2)
        self.exp_scale.pack(fill="x")
        
        # Analog gain control
        gain_frame = tk.LabelFrame(self.control_frame, text="Gain")
        gain_frame.pack(fill="x", padx=5, pady=5)
        
        self.gain_scale = tk.Scale(gain_frame, from_=1, to=16,
                                  orient="horizontal", command=self._change_gain)
        self.gain_scale.set(self.analog_gain)
        self.gain_scale.pack(fill="x")

    def _create_stack_controls(self):
        stack_frame = tk.LabelFrame(self.control_frame, text="Stack Controls")
        stack_frame.pack(fill="x", padx=5, pady=5)
        
        # Stack counter
        self.stack_counter_var = tk.StringVar(value="0")
        tk.Label(stack_frame, textvariable=self.stack_counter_var).pack()
        
        # Stack controls
        controls_frame = tk.Frame(stack_frame)
        controls_frame.pack(fill="x")
        
        tk.Button(controls_frame, text="Reset", command=self._reset_stack).pack(side="left", expand=True)
        tk.Button(controls_frame, text="Save", command=self._save_stack).pack(side="left", expand=True)
        tk.Button(controls_frame, text="Show Stack", command=self._toggle_stack_show).pack(side="left", expand=True)

    def _create_adjustment_controls(self):
        adj_frame = tk.LabelFrame(self.control_frame, text="Image Adjustments")
        adj_frame.pack(fill="x", padx=5, pady=5)
        
        # Threshold controls
        self.threshold_scale = tk.Scale(adj_frame, from_=10, to=250,
                                      orient="horizontal", command=self._change_threshold)
        self.threshold_scale.set(self.threshold_value)
        self.threshold_scale.pack(fill="x")
        
        # Level adjustment controls
        self.level_button = tk.Button(adj_frame, text="Level Adjust", command=self._toggle_level_adjust)
        self.level_button.pack(fill="x")

    def _change_exposure(self, value):
        self.exp_sec = 2 ** float(value)
        self.exp_mic_sec = int(self.exp_sec * 1000000)

    def _change_gain(self, value):
        self.analog_gain = int(value)

    def _change_threshold(self, value):
        self.threshold_value = int(value)
        if self.threshold_enabled:
            self.run_zoom_update = 1

    def _toggle_level_adjust(self):
        self.level_adjust = not self.level_adjust
        self.run_display_update = 1

    def _reset_stack(self):
        self.stack_busy = 1
        self.stack_image = np.zeros_like(self.frame_image, dtype=np.float32)
        self.stack_counter = 0
        self.stack_counter_var.set(str(self.stack_counter))
        self.stack_busy = 0

    def _save_stack(self):
        if self.stack_counter == 0:
            return
            
        self.stack_busy = 1
        timestamp = time.strftime("%Y%m%d%H%M%S")
        filename = f"Pictures/PCIM{timestamp}.tif"
        
        # Normalize and save
        save_image = self.stack_image / self.stack_counter
        cv2.imwrite(filename, save_image)
        
        print(f'Stacked Image Saved at {timestamp}')
        self.stack_busy = 0
        self._reset_stack()

    def _toggle_stack_show(self):
        self.stack_show = not self.stack_show
        self.run_display_update = 1

    def _update_display(self):
        if not hasattr(self, 'frame_image') or self.frame_image is None:
            return
            
        # Prepare image for display
        if self.stack_show and self.stack_counter > 0:
            display_image = self.stack_image / self.stack_counter
        else:
            display_image = self.frame_image.copy()
            
        # Apply level adjustment if enabled
        if self.level_adjust:
            display_image = self._apply_level_adjustment(display_image)
            
        # Scale for display
        display_image = np.clip(display_image / 16, 0, 255).astype(np.uint8)
        display_image = cv2.resize(display_image, (int(self.sensor_w/5), int(self.sensor_h/5)))
        
        # Convert to RGB for display
        rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        
        # Update the image in the GUI
        img = Image.fromarray(rgb_image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.main_image_label.imgtk = imgtk
        self.main_image_label.configure(image=imgtk)

    def _update_zoom(self):
        if not hasattr(self, 'frame_image') or self.frame_image is None:
            return
            
        # Extract zoom region
        y1 = self.y_zoom_center - self.zoom_window_hw
        y2 = self.y_zoom_center + self.zoom_window_hw
        x1 = self.x_zoom_center - self.zoom_window_hw
        x2 = self.x_zoom_center + self.zoom_window_hw
        
        zoom_image = self.frame_image[y1:y2, x1:x2]
        zoom_image = (zoom_image / 16).clip(2, 255).astype(np.uint8)
        
        if self.threshold_enabled:
            zoom_image = cv2.cvtColor(zoom_image, cv2.COLOR_BGR2GRAY)
            _, zoom_image = cv2.threshold(zoom_image, self.threshold_value, 255, cv2.THRESH_BINARY)
        
        # Convert to RGB for display
        if len(zoom_image.shape) == 2:  # Grayscale
            zoom_image = cv2.cvtColor(zoom_image, cv2.COLOR_GRAY2RGB)
        else:
            zoom_image = cv2.cvtColor(zoom_image, cv2.COLOR_BGR2RGB)
            
        # Update the zoom window
        img = Image.fromarray(zoom_image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.zoom_image_label.imgtk = imgtk
        self.zoom_image_label.configure(image=imgtk)

    def _apply_level_adjustment(self, image):
        # Implement level adjustment logic here
        return image

    def _on_closing(self):
        self.run_camera = 0
        self.run_display_update = 0
        
        # Stop all threads
        self.capture_thread.join()
        self.convert_thread.join()
        self.display_thread.join()
        
        if self.use_motors:
            self.motor_controller.stop()
        
        self.window.destroy()

def main():
    parser = argparse.ArgumentParser(description='Telescope Camera Control')
    parser.add_argument('--motors', action='store_true',
                       help='Enable motor control functionality')
    args = parser.parse_args()
    
    app = TelescopeCamera(use_motors=args.motors)

if __name__ == "__main__":
    main()
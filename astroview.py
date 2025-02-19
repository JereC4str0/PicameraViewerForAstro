# main.py
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import cv2
import numpy as np
import threading
import time
import datetime
import argparse
import os
from camera_control import CameraController
from motor_control import MotorController

class TelescopeCamera:
    def __init__(self, use_motors=False):
        # Create required directories
        os.makedirs("temp", exist_ok=True)
        os.makedirs("Pictures", exist_ok=True)
        
        self.use_motors = use_motors
        if use_motors:
            self.motor_controller = MotorController()
        
        # Initialize camera
        self.camera = CameraController()
        
        # Image processing parameters
        self.sensor_w = 4056
        self.sensor_h = 3040
        self.x_zoom_center = int(self.sensor_w/2)
        self.y_zoom_center = int(self.sensor_h/2)
        self.zoom_window_hw = 128
        
        # Control flags
        self.run_camera = True
        self.threshold_enabled = False
        self.threshold_value = 128
        self.dark_mode = False
        self.level_adjust = False
        self.stack_show = False
        
        # Stack parameters
        self.stack_image = None
        self.stack_counter = 0
        self.max_stack = 64
        self.stack_busy = False
        
        # Display parameters
        self.brightness = 1.0
        self.contrast = 1.0
        self.display_zoom = 1
        
        # Setup GUI
        self.window = tk.Tk()
        self.window.title("Telescope Camera Control")
        self.window.configure(background='#222222')
        self._setup_gui()
        
        # Start processing threads
        self.start_threads()
        
        # Configure window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.window.mainloop()

    def _setup_gui(self):
        """Create the main GUI layout"""
        # Main image frame
        self.image_frame = ttk.Frame(self.window)
        self.image_frame.grid(row=0, column=0, padx=5, pady=5)
        
        self.main_image = ttk.Label(self.image_frame)
        self.main_image.grid(row=0, column=1)
        self.main_image.bind('<Button-1>', self._on_image_click)
        
        # Zoom window
        self.zoom_frame = ttk.LabelFrame(self.window, text="Zoom")
        self.zoom_frame.grid(row=0, column=1, padx=5, pady=5, sticky="n")
        
        self.zoom_image = ttk.Label(self.zoom_frame)
        self.zoom_image.pack()
        
        # Control panel
        self.control_frame = ttk.LabelFrame(self.window, text="Controls")
        self.control_frame.grid(row=0, column=2, padx=5, pady=5, sticky="n")
        
        self._create_exposure_controls()
        self._create_stack_controls()
        self._create_image_controls()

    def _create_exposure_controls(self):
        """Create exposure and gain controls"""
        exp_frame = ttk.LabelFrame(self.control_frame, text="Exposure")
        exp_frame.pack(fill="x", padx=5, pady=5)
        
        # Exposure control
        ttk.Label(exp_frame, text="Exposure (s):").pack()
        self.exp_scale = ttk.Scale(exp_frame, from_=-8, to=5, orient="horizontal",
                                 command=self._change_exposure)
        self.exp_scale.set(-2)  # Default 0.25s
        self.exp_scale.pack(fill="x")
        
        # Gain control
        ttk.Label(exp_frame, text="Gain:").pack()
        self.gain_scale = ttk.Scale(exp_frame, from_=1, to=16, orient="horizontal",
                                  command=self._change_gain)
        self.gain_scale.set(1)
        self.gain_scale.pack(fill="x")

    def _create_stack_controls(self):
        """Create stacking controls"""
        stack_frame = ttk.LabelFrame(self.control_frame, text="Stack Control")
        stack_frame.pack(fill="x", padx=5, pady=5)
        
        # Stack counter display
        self.stack_counter_var = tk.StringVar(value="0")
        ttk.Label(stack_frame, textvariable=self.stack_counter_var).pack()
        
        # Stack controls
        ttk.Button(stack_frame, text="Reset Stack", command=self._reset_stack).pack(fill="x")
        ttk.Button(stack_frame, text="Save Stack", command=self._save_stack).pack(fill="x")
        ttk.Button(stack_frame, text="Show Stack", command=self._toggle_stack_show).pack(fill="x")
        
        # Max stack control
        ttk.Label(stack_frame, text="Max Stack:").pack()
        self.max_stack_scale = ttk.Scale(stack_frame, from_=1, to=128, orient="horizontal",
                                       command=lambda v: setattr(self, 'max_stack', int(v)))
        self.max_stack_scale.set(self.max_stack)
        self.max_stack_scale.pack(fill="x")

    def _create_image_controls(self):
        """Create image adjustment controls"""
        img_frame = ttk.LabelFrame(self.control_frame, text="Image Adjustments")
        img_frame.pack(fill="x", padx=5, pady=5)
        
        # Threshold controls
        ttk.Label(img_frame, text="Threshold:").pack()
        self.threshold_scale = ttk.Scale(img_frame, from_=0, to=255, orient="horizontal",
                                       command=lambda v: setattr(self, 'threshold_value', int(v)))
        self.threshold_scale.set(self.threshold_value)
        self.threshold_scale.pack(fill="x")
        
        threshold_button = ttk.Button(img_frame, text="Threshold Mode", command=self._toggle_threshold)
        threshold_button.pack(fill="x")
        
        # Dark frame controls
        ttk.Button(img_frame, text="Load Dark", command=self._load_dark_frame).pack(fill="x")
        dark_toggle = ttk.Checkbutton(img_frame, text="Use Dark", command=self._toggle_dark_mode)
        dark_toggle.pack(fill="x")
        
        # Level adjustment
        ttk.Label(img_frame, text="Brightness:").pack()
        self.brightness_scale = ttk.Scale(img_frame, from_=0.1, to=3.0, orient="horizontal",
                                        command=lambda v: setattr(self, 'brightness', float(v)))
        self.brightness_scale.set(1.0)
        self.brightness_scale.pack(fill="x")
        
        ttk.Label(img_frame, text="Contrast:").pack()
        self.contrast_scale = ttk.Scale(img_frame, from_=0.1, to=3.0, orient="horizontal",
                                      command=lambda v: setattr(self, 'contrast', float(v)))
        self.contrast_scale.set(1.0)
        self.contrast_scale.pack(fill="x")

    def start_threads(self):
        """Start the processing threads"""
        self.display_thread = threading.Thread(target=self._display_loop)
        self.display_thread.daemon = True
        self.display_thread.start()
        
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()

    def _capture_loop(self):
        """Main capture and processing loop"""
        while self.run_camera:
            try:
                # Get new frame
                frame_data = self.camera.get_latest_frame()
                if frame_data is None:
                    continue
                
                frame = frame_data['frame']
                
                # Apply dark frame if enabled
                if self.dark_mode and hasattr(self, 'dark_frame'):
                    frame = self.camera.apply_dark_frame(frame, self.dark_frame)
                
                # Handle stacking
                if not self.stack_busy and self.stack_counter < self.max_stack:
                    if self.stack_image is None:
                        self.stack_image = frame.astype(np.float32)
                    else:
                        self.stack_image += frame.astype(np.float32)
                    self.stack_counter += 1
                    self.stack_counter_var.set(str(self.stack_counter))
                
                # Store current frame
                self.current_frame = frame
                
            except Exception as e:
                print(f"Capture error: {e}")
                time.sleep(0.1)
                continue
            
            time.sleep(0.01)

    def _display_loop(self):
        """Display update loop"""
        while self.run_camera:
            try:
                self._update_main_display()
                self._update_zoom_display()
            except Exception as e:
                print(f"Display error: {e}")
            time.sleep(0.03)  # ~30 FPS

    def _update_main_display(self):
        """Update the main display"""
        if not hasattr(self, 'current_frame'):
            return
            
        # Prepare image for display
        if self.stack_show and self.stack_counter > 0:
            display_image = self.stack_image / self.stack_counter
        else:
            display_image = self.current_frame.copy()
        
        # Apply level adjustments
        display_image = cv2.convertScaleAbs(display_image, 
                                          alpha=self.contrast,
                                          beta=self.brightness * 128)
        
        # Resize for display
        display_image = cv2.resize(display_image, 
                                 (self.sensor_w//5, self.sensor_h//5))
        
        # Convert to PhotoImage
        image = Image.fromarray(cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(image=image)
        
        # Update display
        self.main_image.configure(image=photo)
        self.main_image.image = photo

    def _update_zoom_display(self):
        """Update the zoom window"""
        if not hasattr(self, 'current_frame'):
            return
            
        # Extract zoom region
        y1 = self.y_zoom_center - self.zoom_
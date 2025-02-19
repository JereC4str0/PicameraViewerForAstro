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

        if self.use_motors:
            self._create_motor_controls()

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
        
        self.threshold_button = ttk.Button(img_frame, text="Threshold Mode", 
                                         command=self._toggle_threshold)
        self.threshold_button.pack(fill="x")
        
        # Dark frame controls
        ttk.Button(img_frame, text="Load Dark", command=self._load_dark_frame).pack(fill="x")
        self.dark_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(img_frame, text="Use Dark", variable=self.dark_var,
                       command=self._toggle_dark_mode).pack(fill="x")
        
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

    def _create_motor_controls(self):
        """Create motor control panel"""
        motor_frame = ttk.LabelFrame(self.control_frame, text="Motor Control")
        motor_frame.pack(fill="x", padx=5, pady=5)
        
        # RA controls
        ra_frame = ttk.LabelFrame(motor_frame, text="RA")
        ra_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(ra_frame, text="Track", 
                  command=lambda: self.motor_controller.set_ra_direction(1)).pack(side="left")
        ttk.Button(ra_frame, text="Stop", 
                  command=lambda: self.motor_controller.set_ra_direction(0)).pack(side="left")
        ttk.Button(ra_frame, text="Reverse", 
                  command=lambda: self.motor_controller.set_ra_direction(-1)).pack(side="left")
        
        # DEC controls
        dec_frame = ttk.LabelFrame(motor_frame, text="DEC")
        dec_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(dec_frame, text="North", 
                  command=lambda: self.motor_controller.move_dec(0.5)).pack(side="left")
        ttk.Button(dec_frame, text="Stop", 
                  command=lambda: self.motor_controller.move_dec(0)).pack(side="left")
        ttk.Button(dec_frame, text="South", 
                  command=lambda: self.motor_controller.move_dec(-0.5)).pack(side="left")

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
        y1 = self.y_zoom_center - self.zoom_window_hw
        y2 = self.y_zoom_center + self.zoom_window_hw
        x1 = self.x_zoom_center - self.zoom_window_hw
        x2 = self.x_zoom_center + self.zoom_window_hw
        
        # Ensure coordinates are within bounds
        y1 = max(0, min(y1, self.sensor_h - 2*self.zoom_window_hw))
        y2 = min(self.sensor_h, y2)
        x1 = max(0, min(x1, self.sensor_w - 2*self.zoom_window_hw))
        x2 = min(self.sensor_w, x2)
        
        zoom_image = self.current_frame[y1:y2, x1:x2].copy()
        
        # Apply threshold if enabled
        if self.threshold_enabled:
            gray = cv2.cvtColor(zoom_image, cv2.COLOR_BGR2GRAY)
            _, zoom_image = cv2.threshold(gray, self.threshold_value, 255, cv2.THRESH_BINARY)
            zoom_image = cv2.cvtColor(zoom_image, cv2.COLOR_GRAY2BGR)
        
        # Resize for display
        zoom_image = cv2.resize(zoom_image, (256, 256))
        
        # Convert to PhotoImage
        image = Image.fromarray(cv2.cvtColor(zoom_image, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(image=image)
        
        # Update display
        self.zoom_image.configure(image=photo)
        self.zoom_image.image = photo

    def _change_exposure(self, value):
        """Change camera exposure time"""
        exp_sec = 2 ** float(value)
        self.camera.set_exposure_time(int(exp_sec * 1000000))

    def _change_gain(self, value):
        """Change camera gain"""
        self.camera.set_analog_gain(float(value))

    def _reset_stack(self):
        """Reset the image stack"""
        self.stack_busy = True
        self.stack_image = None
        self.stack_counter = 0
        self.stack_counter_var.set("0")
        self.stack_busy = False
    def _save_stack(self):
        """Save the current stack to file"""
        if self.stack_counter == 0 or self.stack_image is None:
            return
            
        self.stack_busy = True
        timestamp = time.strftime("%Y%m%d%H%M%S")
        filename = f"Pictures/PCIM{timestamp}.tif"
        
        # Normalize and save
        save_image = self.stack_image / self.stack_counter
        save_image = np.clip(save_image, 0, 65535).astype(np.uint16)
        cv2.imwrite(filename, save_image)
        
        print(f'Stacked Image Saved at {timestamp}')
        self._reset_stack()
        self.stack_busy = False

    def _toggle_stack_show(self):
        """Toggle stack display mode"""
        self.stack_show = not self.stack_show

    def _toggle_threshold(self):
        """Toggle threshold mode"""
        self.threshold_enabled = not self.threshold_enabled
        if self.threshold_enabled:
            self.threshold_button.configure(style='Accent.TButton')
        else:
            self.threshold_button.configure(style='TButton')

    def _toggle_dark_mode(self):
        """Toggle dark frame subtraction"""
        self.dark_mode = self.dark_var.get()

    def _load_dark_frame(self):
        """Load a dark frame from file"""
        filename = filedialog.askopenfilename(
            title="Select Dark Frame",
            filetypes=[("TIFF files", "*.tif"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.dark_frame = cv2.imread(filename, -1)
                print("Dark frame loaded successfully")
                self.dark_var.set(True)
                self._toggle_dark_mode()
            except Exception as e:
                print(f"Error loading dark frame: {e}")

    def _on_image_click(self, event):
        """Handle click on main image for zoom positioning"""
        if not hasattr(self, 'current_frame'):
            return
            
        # Calculate actual image coordinates from click position
        scale = 5  # Since we're displaying at 1/5 size
        x = int(event.x * scale)
        y = int(event.y * scale)
        
        # Update zoom center
        self.x_zoom_center = min(max(x, self.zoom_window_hw), 
                                self.sensor_w - self.zoom_window_hw)
        self.y_zoom_center = min(max(y, self.zoom_window_hw), 
                                self.sensor_h - self.zoom_window_hw)

    def _on_closing(self):
        """Clean up and close the application"""
        self.run_camera = False
        
        # Stop all threads
        if hasattr(self, 'capture_thread') and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
        if hasattr(self, 'display_thread') and self.display_thread.is_alive():
            self.display_thread.join(timeout=1.0)
        
        # Stop camera
        if hasattr(self, 'camera'):
            self.camera.stop()
        
        # Stop motors if enabled
        if self.use_motors and hasattr(self, 'motor_controller'):
            self.motor_controller.stop()
        
        # Close window
        self.window.destroy()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Telescope Camera Control')
    parser.add_argument('--motors', action='store_true',
                       help='Enable motor control functionality')
    args = parser.parse_args()
    
    app = TelescopeCamera(use_motors=args.motors)

if __name__ == "__main__":
    main()
            
      
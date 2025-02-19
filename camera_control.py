# camera_control.py
from picamera2 import Picamera2
import numpy as np
import time
import threading
from PIL import Image
import cv2

class CameraController:
    def __init__(self):
        self.picam2 = Picamera2()
        
        # Configure camera
        self._configure_camera()
        
        # Camera state
        self.running = True
        self.exposure_time = 250000  # 0.25 seconds in microseconds
        self.analog_gain = 1.0
        
        # Image buffers
        self.current_frame = None
        self.frame_ready = threading.Event()
        
        # Start camera
        self.picam2.start()
        
        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()

    def _configure_camera(self):
        # Get main camera config
        config = self.picam2.create_still_configuration(
            main={
                "size": (4056, 3040),  # Full resolution
                "format": "RGB888"
            },
            raw={
                "size": (4056, 3040),
                "format": "SRGGB10_CSI2P"  # 10-bit raw Bayer data
            }
        )

        # Configure camera with custom settings
        self.picam2.configure(config)
        
        # Set initial camera controls
        self.picam2.set_controls({
            "ExposureTime": self.exposure_time,
            "AnalogueGain": self.analog_gain,
            "AeEnable": False,  # Disable auto exposure
            "AwbEnable": False,  # Disable auto white balance
            "NoiseReductionMode": 0  # Disable noise reduction
        })

    def _capture_loop(self):
        while self.running:
            try:
                # Capture frame with current settings
                frame = self.picam2.capture_array("main")
                metadata = self.picam2.capture_metadata()
                
                self.current_frame = {
                    'frame': frame,
                    'metadata': metadata,
                    'timestamp': time.time()
                }
                
                # Signal that new frame is ready
                self.frame_ready.set()
            except Exception as e:
                print(f"Capture error: {e}")
                time.sleep(0.1)
                continue
            
            time.sleep(0.01)

    def get_latest_frame(self, wait=True):
        if wait:
            self.frame_ready.wait()
            self.frame_ready.clear()
        return self.current_frame

    def set_exposure_time(self, exposure_us):
        """Set exposure time in microseconds"""
        self.exposure_time = exposure_us
        self.picam2.set_controls({"ExposureTime": exposure_us})

    def set_analog_gain(self, gain):
        """Set analog gain (1.0 to 16.0)"""
        self.analog_gain = max(1.0, min(16.0, gain))
        self.picam2.set_controls({"AnalogueGain": self.analog_gain})

    def apply_dark_frame(self, frame, dark_frame):
        """Apply dark frame subtraction"""
        return np.clip(frame.astype(np.float32) - dark_frame.astype(np.float32), 0, 65535).astype(np.uint16)

    def stop(self):
        """Stop the camera and cleanup"""
        self.running = False
        if self.capture_thread.is_alive():
            self.capture_thread.join()
        self.picam2.stop()
        self.picam2.close()
# motor_control.py
import RPi.GPIO as GPIO
import time
import threading

class MotorController:
    def __init__(self):
        # Motor configuration constants
        self.STEP_PER_REV = 32
        self.RATIO_IN_GEAR = 64
        self.RATIO_OUT_GEAR = 4
        self.DEG_WARM = 4
        
        # Calculate steps and timing
        self.DEG_PER_STEP = self.DEG_WARM/(self.RATIO_OUT_GEAR * self.RATIO_IN_GEAR * self.STEP_PER_REV)
        self.DEG_PER_SEC = 360/(24 * 60 * 60)
        self.GUIDE_STEP = self.DEG_PER_STEP / self.DEG_PER_SEC

        # Motor state variables
        self.time_step1 = self.GUIDE_STEP
        self.time_step2 = 0.02
        self.forward_direction1 = 1
        self.loops_to_go2 = 0
        self.phase1 = 0
        self.phase2 = 0
        self.run_thread = 1

        # GPIO Setup
        GPIO.setmode(GPIO.BCM)
        # Motor 1 pins (RA)
        self.MOTOR1_PINS = [6, 13, 19, 26]
        # Motor 2 pins (DEC)
        self.MOTOR2_PINS = [12, 16, 20, 21]
        
        for pin in self.MOTOR1_PINS + self.MOTOR2_PINS:
            GPIO.setup(pin, GPIO.OUT)

        # Start motor control threads
        self.thread1 = threading.Thread(target=self._motor1_control)
        self.thread2 = threading.Thread(target=self._motor2_control)
        self.thread1.start()
        self.thread2.start()

    def _motor1_control(self):
        """Controls RA motor (motor 1)"""
        while self.run_thread:
            if self.forward_direction1 == 1:  # Positive value goes west
                if self.phase1 == 0:
                    GPIO.output(self.MOTOR1_PINS[0], 1)
                    GPIO.output(self.MOTOR1_PINS[1:], [0,0,0])
                    self.phase1 = 1
                elif self.phase1 == 1:
                    GPIO.output(self.MOTOR1_PINS[1], 1)
                    GPIO.output(self.MOTOR1_PINS[0], 0)
                    GPIO.output(self.MOTOR1_PINS[2:], [0,0])
                    self.phase1 = 2
                elif self.phase1 == 2:
                    GPIO.output(self.MOTOR1_PINS[2], 1)
                    GPIO.output(self.MOTOR1_PINS[:2], [0,0])
                    GPIO.output(self.MOTOR1_PINS[3], 0)
                    self.phase1 = 3
                elif self.phase1 == 3:
                    GPIO.output(self.MOTOR1_PINS[3], 1)
                    GPIO.output(self.MOTOR1_PINS[:3], [0,0,0])
                    self.phase1 = 0
            elif self.forward_direction1 == -1:
                if self.phase1 == 0:
                    GPIO.output(self.MOTOR1_PINS[0], 1)
                    GPIO.output(self.MOTOR1_PINS[1:], [0,0,0])
                    self.phase1 = 3
                elif self.phase1 == 3:
                    GPIO.output(self.MOTOR1_PINS[3], 1)
                    GPIO.output(self.MOTOR1_PINS[:3], [0,0,0])
                    self.phase1 = 2
                elif self.phase1 == 2:
                    GPIO.output(self.MOTOR1_PINS[2], 1)
                    GPIO.output(self.MOTOR1_PINS[:2], [0,0])
                    GPIO.output(self.MOTOR1_PINS[3], 0)
                    self.phase1 = 1
                elif self.phase1 == 1:
                    GPIO.output(self.MOTOR1_PINS[1], 1)
                    GPIO.output([self.MOTOR1_PINS[0]] + self.MOTOR1_PINS[2:], [0,0,0])
                    self.phase1 = 0
            time.sleep(self.time_step1)

    def _motor2_control(self):
        """Controls DEC motor (motor 2)"""
        while self.run_thread:
            if self.loops_to_go2 < 0:  # Negative value moves south
                if self.phase2 == 0:
                    GPIO.output(self.MOTOR2_PINS[0], 1)
                    GPIO.output(self.MOTOR2_PINS[1:], [0,0,0])
                    self.phase2 = 1
                elif self.phase2 == 1:
                    GPIO.output(self.MOTOR2_PINS[1], 1)
                    GPIO.output([self.MOTOR2_PINS[0]] + self.MOTOR2_PINS[2:], [0,0,0])
                    self.phase2 = 2
                elif self.phase2 == 2:
                    GPIO.output(self.MOTOR2_PINS[2], 1)
                    GPIO.output(self.MOTOR2_PINS[:2] + [self.MOTOR2_PINS[3]], [0,0,0])
                    self.phase2 = 3
                elif self.phase2 == 3:
                    GPIO.output(self.MOTOR2_PINS[3], 1)
                    GPIO.output(self.MOTOR2_PINS[:3], [0,0,0])
                    self.phase2 = 0
                self.loops_to_go2 += 1
            elif self.loops_to_go2 > 0:  # Positive value moves North
                if self.phase2 == 0:
                    GPIO.output(self.MOTOR2_PINS[0], 1)
                    GPIO.output(self.MOTOR2_PINS[1:], [0,0,0])
                    self.phase2 = 3
                elif self.phase2 == 3:
                    GPIO.output(self.MOTOR2_PINS[3], 1)
                    GPIO.output(self.MOTOR2_PINS[:3], [0,0,0])
                    self.phase2 = 2
                elif self.phase2 == 2:
                    GPIO.output(self.MOTOR2_PINS[2], 1)
                    GPIO.output(self.MOTOR2_PINS[:2] + [self.MOTOR2_PINS[3]], [0,0,0])
                    self.phase2 = 1
                elif self.phase2 == 1:
                    GPIO.output(self.MOTOR2_PINS[1], 1)
                    GPIO.output([self.MOTOR2_PINS[0]] + self.MOTOR2_PINS[2:], [0,0,0])
                    self.phase2 = 0
                self.loops_to_go2 -= 1
            time.sleep(self.time_step2)

    def set_ra_direction(self, direction):
        """Sets RA motor direction (1 for west, -1 for east)"""
        self.forward_direction1 = direction

    def set_ra_speed(self, time_step):
        """Sets RA motor speed via time step between phases"""
        self.time_step1 = time_step

    def move_dec(self, degrees):
        """Moves DEC motor by specified degrees (positive for north, negative for south)"""
        self.loops_to_go2 = int(float(degrees)/self.DEG_PER_STEP)

    def stop(self):
        """Stops all motor movement and cleans up GPIO"""
        self.run_thread = 0
        self.thread1.join()
        self.thread2.join()
        GPIO.cleanup()
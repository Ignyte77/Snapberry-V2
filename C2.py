import RPi.GPIO as GPIO
import subprocess
import time
import os
from datetime import datetime

# --- GPIO Configuration ---
BTN_PIN = 23
BUZZER_PIN = 25

GPIO.setmode(GPIO.BCM)
GPIO.setup(BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

video_process = None

def get_daily_folder():
    folder_name = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

def beep(duration, count=1, gap=0.05):
    for _ in range(count):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        if count > 1:
            time.sleep(gap)

def take_photo():
    folder = get_daily_folder()
    timestamp = datetime.now().strftime("%H%M%S")
    filename = os.path.join(folder, f"amaan_16mp_{timestamp}.jpg")
    
    # DSLR Style: Two fast beeps at the start
    beep(0.06, count=2) 
    print(f" Taking Photo: {filename}")
    
    # YOUR EXACT PHOTO COMMAND
    subprocess.run([
        "rpicam-still", 
        "--width", "4624", 
        "--height", "3472", 
        "--viewfinder-width", "1280", 
        "--viewfinder-height", "720", 
        "--quality", "100", 
        "--raw", 
        "--autofocus-mode", "auto", 
        "--timeout", "4000", 
        "--output", filename
    ])
    
    # One very fast beep when done
    beep(0.03)

def toggle_video():
    global video_process
    folder = get_daily_folder()
    timestamp = datetime.now().strftime("%H%M%S")
    filename = os.path.join(folder, f"video_{timestamp}.ts")

    if video_process is None:
        # START VIDEO: 2 Fast Beeps
        beep(0.1, count=2)
        print(f"🎥 Recording Started: {filename}")
        
        # FIXED GAIN & EV: Stops the high-ISO "noise"
        # Only AWB is automatic here.
        cmd = (
            f"rpicam-vid -t 0 --width 1440 --height 1080 --framerate 45 "
            f"--bitrate 35000000 --ev -0.5 --gain 1.5 --saturation 1.3 "
            f"--autofocus-mode manual --lens-position 3.2 "
            f"--denoise off --inline -o - | ffmpeg -y -r 45 -i - -c:v copy {filename}"
        )
        video_process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
    else:
        # STOP VIDEO: 1 Long Beep
        beep(0.4)
        print(" Recording Stopped.")
        os.killpg(os.getpgid(video_process.pid), 15)
        video_process = None

print(" C2 Rig Ready. Tap: Photo | Hold: Start Video | Tap: Stop Video")

try:
    while True:
        if GPIO.input(BTN_PIN) == GPIO.LOW:
            start_time = time.time()
            
            # Instant Stop logic for video
            if video_process is not None:
                toggle_video()
                while GPIO.input(BTN_PIN) == GPIO.LOW: time.sleep(0.05)
            else:
                # Idle: Determine Photo vs Video Start
                while GPIO.input(BTN_PIN) == GPIO.LOW:
                    time.sleep(0.05)
                
                duration = time.time() - start_time
                
                if duration < 0.8: 
                    take_photo()
                else: 
                    toggle_video()
                
        time.sleep(0.1)

except KeyboardInterrupt:
    GPIO.cleanup()

import time
import json
import threading
import requests
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD


GPIO.cleanup()


API_KEY       = "API-KEY"
DATABASE_URL  = "database-url"
USER_ID       = "firebase-user-id"
SERVO_PINS    = [18, 23]
OPEN_ANGLE    = 80
CLOSE_ANGLE   = 0

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Set up GPIO pins
for pin in SERVO_PINS:
    GPIO.setup(pin, GPIO.OUT)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Close Opened Ones Button
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Open All Button

LED_PINS = [7, 8]  
for pin in LED_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)  

lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,       
    port=1,              
    cols=16, rows=2,
    charmap='A00',       
)


servo_pwms = [GPIO.PWM(pin, 50) for pin in SERVO_PINS]
for pwm in servo_pwms:
    pwm.start(7.5) 
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)


shared_states = {}


last_dispensed = None
med_names_global = []
display_lock = threading.Lock()
def convert_to_12hr_format(time_str):
    try:
        if time_str:
            in_time = time.strptime(time_str, "%I:%M %p")  # AM/PM input format
            return time.strftime("%I:%M %p", in_time)
        else:
            return "N/A"
    except Exception as e:
        print(f"Time Conversion Error: {e}")
        return "Invalid"



def display_on_lcd(line1, line2=""):
    """Display messages on LCD with thread safety"""
    with display_lock:
        try:
            lcd.clear()
            lcd.write_string(line1[:16])  
            if line2:
                lcd.crlf()
                lcd.write_string(line2[:16])  
        except Exception as e:
            print(f"LCD Display Error: {e}")
def display_medications_cycle(med_names, med_times=None, dispensed_med=None):
    """Cycle through medication names and times on LCD"""
    if not med_names:
        display_on_lcd("No Medications", "Available")
        return

    if dispensed_med:
        disp_time = med_times.get(dispensed_med, "") if med_times else ""
        display_on_lcd("*** DISPENSED ***", f"{dispensed_med[:10]} {disp_time}")
        time.sleep(3)

    
    for i in range(0, len(med_names), 2):
        name1 = med_names[i]
        time1 = convert_to_12hr_format(med_times.get(name1, "")) if med_times else ""


        line1 = f"{name1[:10]} {time1[:8]}"

        if i + 1 < len(med_names):
            name2 = med_names[i + 1]
            time2 = convert_to_12hr_format(med_times.get(name2, "")) if med_times else ""

            line2 = f"{name2[:10]} {time2[:8]}"
        else:
            line2 = f"Total: {len(med_names)} meds"

        display_on_lcd(line1, line2)
        time.sleep(2)



def test_servo(pwm_index):
    """Test function to check if servo is responding between 0 and 80 degrees"""
    print(f"Testing servo on pin {SERVO_PINS[pwm_index]}")
    display_on_lcd("Testing Servo", f"Pin {SERVO_PINS[pwm_index]}")
    
    pwm = servo_pwms[pwm_index]
    
    print("Moving to 0 degrees")
    duty = 2.5  
    pwm.ChangeDutyCycle(duty)
    time.sleep(1)
    pwm.ChangeDutyCycle(0)
    time.sleep(1)

    print("Moving to 80 degrees")
    duty = (80 / 18.0) + 2.5  
    pwm.ChangeDutyCycle(duty)
    time.sleep(1)
    pwm.ChangeDutyCycle(0)
    
    print("Servo test complete")
    
def set_servo_angle(pwm, angle):
    
    pwm.ChangeDutyCycle(0)  
    time.sleep(0.1)
    duty = (angle / 18.0) + 2.5
    print(f"Setting servo to duty cycle: {duty}")
    pwm.ChangeDutyCycle(duty)
    time.sleep(1.0)  
    pwm.ChangeDutyCycle(0)  

def get_medications_from_door():
    url = f"{DATABASE_URL}/users/{USER_ID}/door.json?auth={API_KEY}"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json() or {}
    return list(data.keys())

def get_medication_times(med_names):
    med_times = {}
    for med_name in med_names:
        try:
            url = f"{DATABASE_URL}/users/{USER_ID}/medicationlist/{med_name}/timeIntervals/0/time.json?auth={API_KEY}"
            r = requests.get(url)
            r.raise_for_status()
            med_times[med_name] = r.json() or "No Time"
        except Exception as e:
            print(f"Error fetching time for {med_name}: {e}")
            med_times[med_name] = "Error"
    return med_times


def get_door_state(med_name):
    url = f"{DATABASE_URL}/users/{USER_ID}/door/{med_name}.json?auth={API_KEY}"
    r = requests.get(url)
    r.raise_for_status()
    state = bool(r.json())
    print("Fetched door state for", med_name, "=", state)
    return state

def set_door_state(med_name, state):
    # Check if medication still exists in Firebase
    check_url = f"{DATABASE_URL}/users/{USER_ID}/door/{med_name}.json?auth={API_KEY}"
    try:
        r = requests.get(check_url)
        r.raise_for_status()
        existing_data = r.json()
        
        if existing_data is None and state is False:
            print(f"Skipping update: {med_name} does not exist in DB. Not writing 'False'.")
            return  # Don't write anything if med is deleted

        put_url = check_url
        r = requests.put(put_url, data=json.dumps(state))
        r.raise_for_status()
        print("Set door state for", med_name, "to", state)

    except Exception as e:
        print(f"Error setting door state for {med_name}: {e}")

# Threads
def watch_med(med_name, pwm):
    global last_dispensed
    shared_states[med_name] = None
    while True:
        try:
            state = get_door_state(med_name)
            if state != shared_states[med_name]:
                angle = OPEN_ANGLE if state else CLOSE_ANGLE
                set_servo_angle(pwm, angle)
                print(f"Set {med_name} servo to {angle} degrees ({'open' if state else 'closed'})")
                shared_states[med_name] = state
                
                
                if state:  # If door is opened (dispensing)
                    last_dispensed = med_name
                    display_on_lcd("DISPENSING:", med_name[:16])
                    print(f"LCD: Displaying dispensed medication - {med_name}")
                else:  
                    display_on_lcd("CLOSED:", med_name[:16])
                
        except Exception as e:
            print(f"Error in watch thread for {med_name}: {e}")
            display_on_lcd("Error:", str(e)[:16])
        time.sleep(1)
def button_control(med_names):
    global last_dispensed
    while True:
        # CLOSE OPENED ONES: Button 17 (pull-up)
        if GPIO.input(17) == GPIO.LOW:
            print("Button 17 pressed - closing all opened servos to 0degrees")
            display_on_lcd("CLOSING ALL", "Opened Doors")
            
            closed_count = 0
            for i, (med_name, pwm) in enumerate(zip(med_names, servo_pwms)):
                if shared_states.get(med_name) == True:  
                    set_servo_angle(pwm, 0)
                    set_door_state(med_name, False)
                    shared_states[med_name] = False
                    if i < len(LED_PINS):
                        GPIO.output(LED_PINS[i], GPIO.LOW)
                        print(f"LED OFF for {med_name} (Pin {LED_PINS[i]})")
                    closed_count += 1
                    print(f"Closed {med_name}")
            
            display_on_lcd("CLOSED", f"{closed_count} doors")
            time.sleep(1)
            
            time.sleep(0.5)
            while GPIO.input(17) == GPIO.LOW:
                time.sleep(0.1)

        # OPEN ALL:Button 24 (pull-down)
        if GPIO.input(24) == GPIO.HIGH:
            print("Button 24 pressed - opening all servos to max 80degrees")
            display_on_lcd("OPENING ALL", "Doors to 80deg")
            
            for i, (med_name, pwm) in enumerate(zip(med_names, servo_pwms)):
                set_servo_angle(pwm, 80)
                shared_states[med_name] = True
                last_dispensed = med_name  
                if i < len(LED_PINS):
                    GPIO.output(LED_PINS[i], GPIO.HIGH)
                    print(f"LED ON for {med_name} (Pin {LED_PINS[i]})")
                display_on_lcd(f"Opening {i+1}/{len(med_names)}", med_name[:16])
                print(f"Opened {med_name} to 80")
                time.sleep(0.2)
            
            display_on_lcd("ALL OPENED", f"{len(med_names)} doors")
            time.sleep(1)
            
            time.sleep(0.5)
            
            while GPIO.input(24) == GPIO.HIGH:
                time.sleep(0.1)

        time.sleep(0.1)
        
        
def lcd_display_thread(med_times):
    global last_dispensed, med_names_global
    idle_counter = 0
    while True:
        try:
            if last_dispensed:
                display_medications_cycle(med_names_global, med_times, last_dispensed)
                last_dispensed = None
                idle_counter = 0
            else:
                idle_counter += 1
                if idle_counter > 10:
                    display_medications_cycle(med_names_global, med_times)
                    idle_counter = 0
        except Exception as e:
            print(f"LCD Display Thread Error: {e}")
            display_on_lcd("Display Error", str(e)[:16])
            time.sleep(1)
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        print("Initializing MediMate System...")
        display_on_lcd("MediMate System", "Initializing...")
        time.sleep(2)
        
        
        print("Running servo tests...")
        display_on_lcd("Testing Servos", "Please wait...")
        for i in range(len(SERVO_PINS)):
            test_servo(i)
            time.sleep(1)
        
       
        display_on_lcd("Loading", "Medications...")
        med_names_global = get_medications_from_door()
        print(f"Medications loaded: {med_names_global}")
        med_times_global = get_medication_times(med_names_global)

        display_on_lcd("Medications:", f"Found {len(med_names_global)}")
        time.sleep(2)
        
        if not med_names_global:
            display_on_lcd("No medications", "found in DB")
            time.sleep(5)
        
        
        for i, med_name in enumerate(med_names_global[:len(SERVO_PINS)]):
            threading.Thread(target=watch_med, args=(med_name, servo_pwms[i]), daemon=True).start()
            print(f"Started monitoring thread for {med_name}")
            display_on_lcd("Starting Monitor", med_name[:16])
            time.sleep(0.5)
        
        
        threading.Thread(target=button_control, args=(med_names_global[:len(SERVO_PINS)],), daemon=True).start()
        print("Button control thread started")
        
       
        threading.Thread(target=lcd_display_thread, daemon=True).start()
        print("LCD display thread started")

        threading.Thread(target=lcd_display_thread, args=(med_times_global,), daemon=True).start()
        display_on_lcd("System Ready", "Monitoring...")
        print("System fully initialized and ready")
        
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("Stopped by user")
        display_on_lcd("System Stopped", "By User")
    except Exception as e:
        print(f"System Error: {e}")
        display_on_lcd("System Error", str(e)[:16])
    finally:
        for pwm in servo_pwms:
            pwm.stop()
        GPIO.cleanup()
        display_on_lcd("System Off", "Goodbye!")
        time.sleep(2)
        lcd.clear()
        print("GPIO cleaned up")


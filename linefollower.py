from zumi.zumi import Zumi
import time

# --- IR-based Line Following Only ---
def linefollower_ir(zumi, threshold=100, turn_angle=50, reverse_duration=0.3):
    """
    Einfache IR-basierte Linienfolge ohne Ausgaben:
    - Beide Sensoren unter Threshold: Stop, Rückwärts, Drehkorrektur
    - Beide Sensoren über Threshold: Geradeaus
    - Nur rechter Sensor unter Threshold: Leicht rechts lenken
    - Nur linker Sensor unter Threshold: Leicht links lenken
    """
    ir = zumi.get_all_IR_data()
    br, bl = ir[1], ir[3]

    if br < threshold and bl < threshold:
        zumi.stop()
        time.sleep(0.1)
        zumi.reverse(speed=15, duration=reverse_duration)
        zumi.stop()
        time.sleep(0.1)
        if br < bl:
            zumi.turn_left(turn_angle)
        else:
            zumi.turn_right(turn_angle)
        zumi.stop()
    elif br > threshold and bl > threshold:
        zumi.control_motors(1, 16)
    elif br < threshold:
        zumi.control_motors(1, 0)
    elif bl < threshold:
        zumi.control_motors(0, 1)

# --- Hauptprogramm ohne Ausgaben ---
def main():
    zumi = Zumi()
    threshold = 100  # IR-Schwellenwert
    try:
        while True:
            linefollower_ir(zumi, threshold)
            time.sleep(0.02)
    except KeyboardInterrupt:
        zumi.stop()

if __name__ == "__main__":
    main()

from zumi.zumi import Zumi
import time

# --- IR-based Line Following with Correction ---
def linefollower_ir(zumi, threshold=100):
    """
    Fährt der Linie hinterher. Wenn beide Sensoren über der Linie (unter Threshold) sind,
    stoppt Zumi, fährt zurück und korrigiert seine Ausrichtung.
    """
    # IR-Sensorwerte einlesen (Index 1: bottom_right, Index 3: bottom_left)
    ir = zumi.get_all_IR_data()
    bottom_right, bottom_left = ir[1], ir[3]

    # 1) Über Linie (beide Sensoren < threshold) → Stop, Rückwärts, Korrektur
    if bottom_right < threshold and bottom_left < threshold:
        zumi.stop()
        time.sleep(0.1)
        zumi.reverse(speed=15, duration=0.3)
        zumi.stop()
        time.sleep(0.1)
        # Korrektur drehen: weg von tieferem Sensor
        if bottom_right < bottom_left:
            zumi.turn_left(50)
        else:
            zumi.turn_right(50)
        time.sleep(0.2)
        zumi.stop()

    # 2) Auf Linie (beide Sensoren > threshold) → Geradeaus
    elif bottom_right > threshold and bottom_left > threshold:
        zumi.control_motors(1, 16)

    # 3) Linie rechts (rechter Sensor < threshold) → Leicht nach rechts lenken
    elif bottom_right < threshold:
        zumi.control_motors(1, 0)

    # 4) Linie links (linker Sensor < threshold) → Leicht nach links lenken
    elif bottom_left < threshold:
        zumi.control_motors(0, 1)

# --- Hauptprogramm ---
def main():
    zumi = Zumi()
    threshold = 100  # IR-Schwellenwert für Linie

    try:
        print("Starte Linienfolge mit Korrektur. STRG+C zum Abbrechen.")
        while True:
            linefollower_ir(zumi, threshold)
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("Linienfolge beendet. Stoppe Zumi.")
        zumi.stop()

if __name__ == "__main__":
    main()

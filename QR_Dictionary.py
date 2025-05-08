if qr_code:
    command = qr_code.lower()
    print("✅ QR-Code erkannt:", command)

    def celebrate_action():
        if hasattr(screen, 'celebrate'):
            screen.celebrate()
        else:
            screen.happy()
        return True  # signalisiert break

    def angry_action():
        if hasattr(screen, 'angry'):
            screen.angry()
        else:
            zumi.stop()
        return True

    def happy_action():
        screen.happy()
        zumi.stop()
        return True

    def stop_action():
        zumi.stop()
        time.sleep(3)
        scan_qr()
        return True

    qr_actions = {
        "turn right": lambda: zumi.forward(15, 0.3),
        "turn left": lambda: zumi.turn_left(90),
        "left circle": lambda: left_roundabout(1),
        "right circle": lambda: right_roundabout(1),
        "zumi is happy today!": happy_action,
        "zumi is angry today!": angry_action,
        "zumi is celebrating today!": celebrate_action,
        "stop": stop_action,
    }

    # Aktion holen, ausführen, prüfen ob "break" nötig
    action = qr_actions.get(command)
    if action:
        should_break = action()
        if should_break:
            break

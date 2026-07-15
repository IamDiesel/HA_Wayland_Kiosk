import os
import time
import select
import evdev

class SleepHandlerCore:
    """
    Kapselt die Kern-Logik des Display-Timeouts und des Wake-up-Loops.
    Die interne Logik bleibt erhalten, aber unnötige Errno 22 Konsolen-Fehler
    werden nun sauber unterdrückt.
    """
    def __init__(self, config, devices, fds):
        self.config = config
        self.devices = devices
        self.fds = fds
        self.last_input_time = time.time()
        self.running = True

    def register_activity(self):
        self.last_input_time = time.time()

    def check_timeout(self):
        elapsed = time.time() - self.last_input_time
        if self.config.is_enabled and elapsed >= self.config.timeout:
            self._go_to_sleep()

    def _go_to_sleep(self):
        print("DEBUG: Timeout erreicht. Schalte Display aus...")
        for dev in self.devices:
            try:
                dev.grab()
            except OSError:
                pass # Ignoriert Geräte, die sich nicht sperren lassen (z.B. HDMI-Audio)
            except Exception as e:
                print(f"FEHLER beim Grab von {dev.name}: {e}")

        os.system("wlopm --off '*'")

        wakeup = False
        while not wakeup and self.running and self.config.is_enabled:
            r_wake, _, _ = select.select(self.fds.keys(), [], [], 1.0)
            for fd in r_wake:
                for event in self.fds[fd].read():
                    if event.type in [evdev.ecodes.EV_KEY, evdev.ecodes.EV_ABS, evdev.ecodes.EV_REL]:
                        print("DEBUG: Wakeup-Input erkannt.")
                        wakeup = True
                        break
                if wakeup:
                    break

        print("DEBUG: Schalte Display wieder ein...")
        os.system("wlopm --on '*'")
        time.sleep(0.5)

        for dev in self.devices:
            try:
                dev.ungrab()
            except OSError as e:
                if e.errno == 22:
                    pass # Errno 22 (Invalid argument) lautlos ignorieren
                else:
                    print(f"FEHLER beim Ungrab von {dev.name}: {e}")
            except Exception:
                pass

        self.last_input_time = time.time()
import evdev

class SwipeUpRecognizer:
    """
    Beobachtet den rohen evdev Event-Stream auf Multitouch-Eingaben.
    Erkennt einen 2-Finger-Swipe nach oben (Negative Y-Bewegung).
    Nutzt SYN_REPORT für Frame-genaue Auswertung.
    """
    def __init__(self, on_swipe_callback, swipe_threshold=-150):
        self.on_swipe_callback = on_swipe_callback
        # Negativer Wert = Bewegung nach oben.
        self.swipe_threshold = swipe_threshold
        
        self.slots = {}
        self.current_slot = 0
        self.triggered = False

    def process_event(self, event):
        """Wertet eingehende Events des Touchscreens aus."""
        
        # --- SYN_REPORT (Ende eines Hardware-Frames) ---
        if event.type == evdev.ecodes.EV_SYN and event.code == evdev.ecodes.SYN_REPORT:
            self._evaluate_swipe()
            return

        # --- ABSOLUTE ACHSEN (Multitouch Events) ---
        if event.type == evdev.ecodes.EV_ABS:
            # Slot wechseln
            if event.code == evdev.ecodes.ABS_MT_SLOT:
                self.current_slot = event.value
                if self.current_slot not in self.slots:
                    self.slots[self.current_slot] = {'active': False}

            # Tracking ID (Finger auflegen / anheben)
            elif event.code == evdev.ecodes.ABS_MT_TRACKING_ID:
                if self.current_slot not in self.slots:
                    self.slots[self.current_slot] = {}
                    
                if event.value == -1: # Finger angehoben
                    self.slots[self.current_slot]['active'] = False
                    # Reset Trigger, wenn alle Finger weg sind
                    if not any(s.get('active', False) for s in self.slots.values()):
                        self.triggered = False
                else: # Neuer Finger
                    self.slots[self.current_slot]['active'] = True
                    self.slots[self.current_slot]['start_y'] = None
                    self.slots[self.current_slot]['current_y'] = None

            # Y-Position aktualisieren
            elif event.code == evdev.ecodes.ABS_MT_POSITION_Y:
                if self.current_slot not in self.slots:
                    return
                
                y_val = event.value
                self.slots[self.current_slot]['current_y'] = y_val
                
                if self.slots[self.current_slot].get('start_y') is None:
                    self.slots[self.current_slot]['start_y'] = y_val

    def _evaluate_swipe(self):
        """Prüft die gesammelten Frame-Daten auf die Wischgeste."""
        if self.triggered:
            return

        active_slots = [s for s in self.slots.values() if s.get('active', False)]
        
        if len(active_slots) == 2:
            swipes = []
            for s in active_slots:
                if s.get('start_y') is not None and s.get('current_y') is not None:
                    swipes.append(s['current_y'] - s['start_y'])
            
            # Beide Finger müssen sich weiter als der Threshold nach oben bewegt haben
            if len(swipes) == 2 and all(dy < self.swipe_threshold for dy in swipes):
                print("DEBUG: 2-Finger Swipe UP erkannt!")
                self.triggered = True
                self.on_swipe_callback()
import json
import paho.mqtt.client as mqtt
import kiosk_credentials


class MqttController:
    # GEÄNDERT: Nimmt nun on_keyboard_close_callback entgegen
    # Füge on_keyboard_open_callback hinzu
    def __init__(self, config, on_interaction_callback, on_keyboard_close_callback=None,
                 on_keyboard_open_callback=None):
        self.config = config
        self.on_interaction = on_interaction_callback
        self.on_keyboard_close = on_keyboard_close_callback
        self.on_keyboard_open = on_keyboard_open_callback  # NEU

        self.base_topic = "kiosk/display"
        self.discovery_prefix = "homeassistant"
        self.node_id = "kiosk_pi"

        self.client = mqtt.Client()
        self.client.username_pw_set(kiosk_credentials.MQTT_USER, kiosk_credentials.MQTT_PASSWORD)
        self.client.will_set(f"{self.base_topic}/status", "offline", retain=True)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def connect(self):
        print(f"DEBUG: Verbinde zu MQTT Broker {kiosk_credentials.MQTT_BROKER_IP}...")
        self.client.connect(kiosk_credentials.MQTT_BROKER_IP, 1883, 60)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()

    def _publish_discovery(self):
        print("DEBUG: Sende MQTT Autodiscovery Payloads...")
        device_info = {
            "identifiers": [f"{self.node_id}_hardware"],
            "name": "Kiosk Display",
            "model": "Touch Kiosk Setup",
            "manufacturer": "Fuchsi Custom"
        }

        switch_config = {
            "name": "Kiosk Screensaver Aktiv",
            "unique_id": f"{self.node_id}_screensaver_enable",
            "state_topic": f"{self.base_topic}/enable/state",
            "command_topic": f"{self.base_topic}/enable/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "icon": "mdi:monitor-eye",
            "device": device_info
        }
        self.client.publish(f"{self.discovery_prefix}/switch/{self.node_id}/screensaver_enable/config",
                            json.dumps(switch_config), retain=True)

        timeout_config = {
            "name": "Kiosk Timeout Dauer",
            "unique_id": f"{self.node_id}_screensaver_duration",
            "state_topic": f"{self.base_topic}/timeout/state",
            "command_topic": f"{self.base_topic}/timeout/set",
            "min": 10,
            "max": 7200,
            "step": 10,
            "unit_of_measurement": "s",
            "icon": "mdi:timer-outline",
            "mode": "slider",
            "device": device_info
        }
        self.client.publish(f"{self.discovery_prefix}/number/{self.node_id}/screensaver_duration/config",
                            json.dumps(timeout_config), retain=True)

        height_config = {
            "name": "Kiosk Tastatur Höhe",
            "unique_id": f"{self.node_id}_keyboard_height",
            "state_topic": f"{self.base_topic}/keyboard_height/state",
            "command_topic": f"{self.base_topic}/keyboard_height/set",
            "min": 150,
            "max": 800,
            "step": 10,
            "unit_of_measurement": "px",
            "icon": "mdi:keyboard-outline",
            "mode": "slider",
            "device": device_info
        }
        self.client.publish(f"{self.discovery_prefix}/number/{self.node_id}/keyboard_height/config",
                            json.dumps(height_config), retain=True)

        # NEU: MQTT Button Entität zum Schließen der Tastatur
        close_btn_config = {
            "name": "Kiosk Tastatur schließen",
            "unique_id": f"{self.node_id}_keyboard_close",
            "command_topic": f"{self.base_topic}/keyboard/close",
            "payload_press": "PRESS",
            "icon": "mdi:keyboard-close",
            "device": device_info
        }
        self.client.publish(f"{self.discovery_prefix}/button/{self.node_id}/keyboard_close/config",
                            json.dumps(close_btn_config), retain=True)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("DEBUG: Erfolgreich mit MQTT Broker verbunden!")
            self.client.publish(f"{self.base_topic}/status", "online", retain=True)
            self._publish_discovery()

            self.client.subscribe(f"{self.base_topic}/enable/set")
            self.client.subscribe(f"{self.base_topic}/timeout/set")
            self.client.subscribe(f"{self.base_topic}/keyboard_height/set")
            self.client.subscribe(f"{self.base_topic}/keyboard/close")  # NEU
            self.client.subscribe(f"{self.base_topic}/keyboard/open")  # NEU

            self.client.publish(f"{self.base_topic}/enable/state", "ON" if self.config.is_enabled else "OFF",
                                retain=True)
            self.client.publish(f"{self.base_topic}/timeout/state", self.config.timeout, retain=True)
            self.client.publish(f"{self.base_topic}/keyboard_height/state", self.config.keyboard_height, retain=True)
        else:
            print(f"FEHLER: MQTT Verbindung fehlgeschlagen mit Code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"WARNUNG: Unerwarteter Verbindungsabbruch zu MQTT (Code: {rc}).")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        print(f"DEBUG: MQTT empfangen -> Topic: {topic} | Payload: {payload}")

        if topic == f"{self.base_topic}/enable/set":
            self.config.is_enabled = (payload == "ON")
            self.client.publish(f"{self.base_topic}/enable/state", payload, retain=True)
            if self.config.is_enabled: self.on_interaction()
            print(f"DEBUG: Status geändert auf {payload}")

        elif topic == f"{self.base_topic}/timeout/set":
            try:
                self.config.timeout = int(float(payload))
                self.client.publish(f"{self.base_topic}/timeout/state", self.config.timeout, retain=True)
                self.on_interaction()
                print(f"DEBUG: Timeout geändert auf {self.config.timeout}s")
            except ValueError:
                pass

        elif topic == f"{self.base_topic}/keyboard_height/set":
            try:
                self.config.keyboard_height = int(float(payload))
                self.client.publish(f"{self.base_topic}/keyboard_height/state", self.config.keyboard_height,
                                    retain=True)
                self.on_interaction()
                print(f"DEBUG: Tastatur-Höhe geändert auf {self.config.keyboard_height}px")
            except ValueError:
                pass

        # NEU: Reagiert auf den Klick des Home Assistant Buttons
        elif topic == f"{self.base_topic}/keyboard/close":
            if self.on_keyboard_close:
                self.on_keyboard_close()
            self.on_interaction()
            # NEU: Reaktion auf das Öffnen-Signal
        elif topic == f"{self.base_topic}/keyboard/open":
            if self.on_keyboard_open:
                self.on_keyboard_open()
            self.on_interaction()
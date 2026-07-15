console.log("Kiosk: Tastatur-Skript (v6 - LocalStorage) geladen.");

// 1. Wenn das Passwort in der URL steht, "brennen" wir das Zertifikat in den Browser
if (window.location.search.includes("kiosk_keyboard=true")) {
    localStorage.setItem("is_fuchsi_kiosk", "true");
    console.log("Kiosk: Passwort erkannt! Dieser Browser ist nun dauerhaft als Kiosk autorisiert.");
}

// 2. Wir prüfen nur noch das interne Zertifikat, unabhängig von der aktuellen URL
if (localStorage.getItem("is_fuchsi_kiosk") === "true") {
    console.log("Kiosk: Autorisierter Kiosk-Browser erkannt! Aktiviere Touch-Steuerung.");

    window.addEventListener("click", function(e) {
        const path = e.composedPath ? e.composedPath() : [];
        const isInput = path.some(el => 
            el.tagName === "INPUT" || 
            el.tagName === "TEXTAREA" || 
            el.tagName === "HA-TEXTFIELD" ||
            el.tagName === "HA-SELECTOR-TEXT"
        );

        try {
            const ha = document.querySelector("home-assistant");
            if (ha && ha.hass) {
                if (isInput) {
                    ha.hass.callService("mqtt", "publish", {
                        topic: "kiosk/display/keyboard/open",
                        payload: "PRESS"
                    });
                } else {
                    ha.hass.callService("mqtt", "publish", {
                        topic: "kiosk/display/keyboard/close",
                        payload: "PRESS"
                    });
                }
            }
        } catch (error) {
            console.error("Kiosk: Fehler beim Senden des MQTT-Befehls:", error);
        }
    }, true);
} else {
    console.log("Kiosk: Normaler Browser erkannt. Tastatur-Skript bleibt inaktiv.");
}
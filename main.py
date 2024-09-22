from kivy.app import App  # Importiert die Kivy App-Klasse
from kivy.uix.screenmanager import ScreenManager, Screen  # Importiert ScreenManager und Screen für die Verwaltung von Bildschirmen
from kivy.lang import Builder  # Importiert den Builder für das Laden von Kivy-Sprache (KV-Dateien)
import socket  # Importiert das Socket-Modul für Netzwerkverbindungen
import asyncio  # Importiert asyncio für asynchrone Programmierung
import threading  # Importiert threading für Multithreading
from kivy.clock import mainthread  # Importiert mainthread, um GUI-Updates im Hauptthread durchzuführen
from bleak import BleakScanner, BleakClient  # Importiert BleakScanner und BleakClient für Bluetooth-Kommunikation

Builder.load_file("main.kv")  # Lädt die KV-Datei mit der GUI-Definition

# Definiert die richtige UUID für die Bluetooth-Charakteristik
CHARACTERISTIC_UUID = "19b10000-e8f2-537e-4f6c-d104768a1214"  # Beispiel-UUID, ersetzen mit der richtigen

class LoginScreen(Screen):  # Definiert die LoginScreen-Klasse, die von Screen erbt
    def connect(self, instance):
        password = self.ids.password_input.text  # Liest das eingegebene Passwort
        if password == '1234':  # Überprüft, ob das Passwort korrekt ist
            self.ids.result_label.text = 'Anmeldung erfolgreich!'  # Setzt das Ergebnislabel auf Erfolgsnachricht
            self.manager.current = 'main'  # Wechselt zum Hauptbildschirm
        else:
            self.ids.result_label.text = 'Falscher Code eingegeben.'  # Setzt das Ergebnislabel auf Fehlermeldung

    def reset_password_input(self):
        self.ids.password_input.text = ''  # Setzt das Passwort-Eingabefeld zurückp

class MainScreen(Screen):  # Definiert die MainScreen-Klasse, die von Screen erbt
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.client_socket = None  # Initialisiert den Client-Socket auf None
        self.bt_client = None  # Initialisiert den Bluetooth-Client auf None
        self.devices = {}  # Initialisiert ein Dictionary für gefundene Bluetooth-Geräte
        self.device_address = None  # Initialisiert die Geräteadresse auf None

        # Deaktiviert einige GUI-Elemente standardmäßig
        self.ids.led_on_wifi_button.disabled = True
        self.ids.led_off_wifi_button.disabled = True
        self.ids.device_spinner.disabled = True
        self.ids.ip_address.bind(text=self.validate_ip_address)  # Verknüpft die Textänderung des IP-Adressfelds mit einer Validierungsfunktion

    def disconnect(self):
        # Reset der Login-Bildschirm-Eingaben und Labels
        login_screen = self.manager.get_screen('login')
        login_screen.ids.password_input.text = ''
        login_screen.ids.result_label.text = ''
        self.manager.current = 'login'  # Wechselt zurück zum Login-Bildschirm
        # Deaktiviert und setzt verschiedene GUI-Elemente zurück
        self.ids.led_on_wifi_button.disabled = True
        self.ids.led_off_wifi_button.disabled = True
        self.ids.scan_button.disabled = False
        self.ids.device_spinner.disabled = True
        self.ids.connect_button.disabled = True
        self.ids.led_on_button.disabled = True
        self.ids.led_off_button.disabled = True
        self.ids.ip_address.text = ''

    def get_ip_address(self):
        return self.ids.ip_address.text  # Gibt die eingegebene IP-Adresse zurück

    def validate_ip_address(self, instance, value):
        if self.is_valid_ip(value):  # Überprüft, ob die eingegebene IP-Adresse gültig ist
            self.ids.result_label_ip.text = 'IP-Adresse ist korrekt und verbunden!'  # Setzt das Ergebnislabel auf Erfolg
            self.ids.led_on_wifi_button.disabled = False  # Aktiviert den "LED ein" WiFi-Button
            self.ids.led_off_wifi_button.disabled = False  # Aktiviert den "LED aus" WiFi-Button
        else:
            self.ids.result_label_ip.text = 'Ungültige IP-Adresse eingegeben.'  # Setzt das Ergebnislabel auf Fehlermeldung
            self.ids.led_on_wifi_button.disabled = True  # Deaktiviert den "LED ein" WiFi-Button
            self.ids.led_off_wifi_button.disabled = True  # Deaktiviert den "LED aus" WiFi-Button

    def is_valid_ip(self, ip):
        # Überprüft, ob die IP-Adresse aus vier Teilen besteht und jeder Teil eine Zahl zwischen 0 und 255 ist
        parts = ip.split('.')
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            return True
        return False

    def turn_on_led(self):
        try:
            ip_address = self.get_ip_address()  # Ruft die IP-Adresse ab
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Erstellt einen TCP/IP-Socket
            self.client_socket.connect((ip_address, 12345))  # Verbindet sich mit dem Server an der angegebenen IP und Port
            self.client_socket.sendall(b'1')  # Sendet das Signal zum Einschalten der LED
            print("LED turned on via Wi-Fi")  # Gibt eine Erfolgsnachricht aus
            self.update_button_colors(wifi=True, state='on')  # Aktualisiert die Button-Farben
        except Exception as e:
            print(f"Error turning on LED via Wi-Fi: {e}")  # Gibt eine Fehlermeldung aus, wenn ein Fehler auftritt

    def turn_off_led(self):
        try:
            self.client_socket.sendall(b'0')  # Sendet das Signal zum Ausschalten der LED
            print("LED turned off via Wi-Fi")  # Gibt eine Erfolgsnachricht aus
            self.client_socket.close()  # Schließt die Socket-Verbindung
            self.update_button_colors(wifi=True, state='off')  # Aktualisiert die Button-Farben
        except Exception as e:
            print(f"Error turning off LED via Wi-Fi: {e}")  # Gibt eine Fehlermeldung aus, wenn ein Fehler auftritt

    def start_scan(self):
        self.ids.scan_button.disabled = True  # Deaktiviert den Scan-Button
        self.ids.device_spinner.disabled = True  # Deaktiviert den Gerätelisten-Spinner
        threading.Thread(target=self.run_asyncio_scan).start()  # Startet den Scan in einem neuen Thread

    def run_asyncio_scan(self):
        asyncio.run(self.do_scan())  # Führt den Scan asynchron aus

    async def do_scan(self):
        print("Scanning for Bluetooth devices...")  # Gibt eine Scan-Startmeldung aus
        try:
            devices = await BleakScanner.discover()  # Sucht nach Bluetooth-Geräten
            self.on_scan_complete(devices)  # Ruft die Funktion zur Verarbeitung der gefundenen Geräte auf
        except Exception as e:
            print(f"Error during scanning: {e}")  # Gibt eine Fehlermeldung aus, wenn ein Fehler auftritt
        finally:
            self.enable_scan_button()  # Aktiviert den Scan-Button wieder

    @mainthread
    def on_scan_complete(self, devices):
        # Speichert die gefundenen Geräte und aktiviert die entsprechende GUI-Elemente
        self.devices = {device.name: device.address for device in devices if device.name}
        self.ids.device_spinner.values = list(self.devices.keys())  # Aktualisiert die Geräteliste im Spinner
        self.ids.device_spinner.text = 'Select Device'  # Setzt den Spinner-Text zurück
        self.ids.device_spinner.disabled = False  # Aktiviert den Gerätelisten-Spinner
        self.ids.connect_button.disabled = False  # Aktiviert den Connect-Button
        print(f"Discovered devices: {self.devices}")  # Gibt die Liste der gefundenen Geräte aus

    @mainthread
    def enable_scan_button(self):
        self.ids.scan_button.disabled = False  # Aktiviert den Scan-Button

    def connect_device(self):
        selected_device = self.ids.device_spinner.text  # Liest das ausgewählte Gerät aus dem Spinner
        if selected_device in self.devices:
            self.device_address = self.devices[selected_device]  # Speichert die Adresse des ausgewählten Geräts
            threading.Thread(target=self.run_asyncio_connect).start()  # Startet die Verbindung in einem neuen Thread

    def run_asyncio_connect(self):
        asyncio.run(self.do_connect())  # Führt die Verbindung asynchron aus

    async def do_connect(self):
        print(f"Connecting to {self.device_address}...")  # Gibt eine Verbindungs-Startmeldung aus
        try:
            self.bt_client = BleakClient(self.device_address)  # Erstellt einen Bluetooth-Client für das ausgewählte Gerät
            await self.bt_client.connect()  # Verbindet sich mit dem Bluetooth-Gerät
            print(f"Connected to {self.device_address}")  # Gibt eine Erfolgsnachricht aus
            self.enable_led_control_buttons()  # Aktiviert die LED-Steuerungs-Buttons
        except Exception as e:
            print(f"Error connecting to {self.device_address}: {e}")  # Gibt eine Fehlermeldung aus, wenn ein Fehler auftritt

    @mainthread
    def enable_led_control_buttons(self):
        self.ids.led_on_button.disabled = False  # Aktiviert den "LED ein" Button
        self.ids.led_off_button.disabled = False  # Aktiviert den "LED aus" Button

    def control_led(self, state):
        if self.bt_client and self.bt_client.is_connected:  # Überprüft, ob der Bluetooth-Client verbunden ist
            threading.Thread(target=self.send_led_command, args=(state,)).start()  # Startet das Senden des LED-Kommandos in einem neuen Thread

    def send_led_command(self, state):
        asyncio.run(self.send_led_command_async(state))  # Führt das Senden des LED-Kommandos asynchron aus

    async def send_led_command_async(self, state):
        try:
            print(f"Sending command to Bluetooth device: {state}")  # Gibt das gesendete Kommando aus
            await self.bt_client.write_gatt_char(CHARACTERISTIC_UUID, bytearray([state]))  # Sendet das LED-Kommando an das Bluetooth-Gerät
            self.update_button_colors(wifi=False, state='on' if state == 1 else 'off')  # Aktualisiert die Button-Farben
        except Exception as e:
            print(f"Error sending command: {e}")  # Gibt eine Fehlermeldung aus, wenn ein Fehler auftritt

    def update_button_colors(self, wifi, state):
        default_color = (1, 1, 1, 1)  # Definiert die Standardfarbe für die Buttons (weiß)
        green_color = (0, 1, 0, 1)  # Definiert die Farbe für "ein" (grün)
        red_color = (1, 0, 0, 1)  # Definiert die Farbe für "aus" (rot)

        if wifi:
            if state == 'on':
                self.ids.led_on_wifi_button.background_color = green_color  # Setzt den "LED ein" WiFi-Button auf grün
                self.ids.led_off_wifi_button.background_color = default_color  # Setzt den "LED aus" WiFi-Button auf Standardfarbe
            else:
                self.ids.led_on_wifi_button.background_color = default_color  # Setzt den "LED ein" WiFi-Button auf Standardfarbe
                self.ids.led_off_wifi_button.background_color = red_color  # Setzt den "LED aus" WiFi-Button auf rot
        else:
            if state == 'on':
                self.ids.led_on_button.background_color = green_color  # Setzt den "LED ein" Button auf grün
                self.ids.led_off_button.background_color = default_color  # Setzt den "LED aus" Button auf Standardfarbe
            else:
                self.ids.led_on_button.background_color = default_color  # Setzt den "LED ein" Button auf Standardfarbe
                self.ids.led_off_button.background_color = red_color  # Setzt den "LED aus" Button auf rot

    def cleanup(self):
        """ Gibt die verwendeten Ressourcen frei """
        if self.client_socket:
            # Schließt den Socket des Clients, wenn er vorhanden ist
            self.client_socket.close()
            self.client_socket = None  # Setzt den Socket auf None
        if self.bt_client and self.bt_client.is_connected:
            # Trennt die Verbindung zum Bluetooth-Client, falls er verbunden ist
            asyncio.run(self.bt_client.disconnect())
            self.bt_client = None  # Setzt den Bluetooth-Client auf None


class MyArduinoAppApp(App):  # Definiert die Hauptanwendungsklasse, die von Kivy App erbt
    def build(self):
        sm = ScreenManager()  # Erstellt einen ScreenManager
        sm.add_widget(LoginScreen(name='login'))  # Fügt den LoginScreen hinzu
        sm.add_widget(MainScreen(name='main'))  # Fügt den MainScreen hinzu
        return sm  # Gibt den ScreenManager zurück

if __name__ == '__main__':
    MyArduinoAppApp().run()  # Startet die Kivy-Anwendung
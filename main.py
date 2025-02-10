from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
import socket
import asyncio
from bleak import BleakClient
from kivy.clock import Clock


Builder.load_file("main.kv")  # Lädt die Benutzeroberfläche (UI) aus der Datei "main.kv"

CHARACTERISTIC_UUID = "19b10002-e8f2-537e-4f6c-d104768a1214"  # Die UUID der BLE-Charakteristik, die für die Kommunikation mit dem Gerät verwendet wird


def run_in_loop(coro):
    loop = asyncio.get_running_loop()
    return loop.run_until_complete(coro)
# Führt eine asynchrone Funktion synchron aus.


class LoginScreen(Screen):
    def connect(self, instance):
        password = self.ids.password_input.text
        if password == '1234':
            self.ids.result_label.text = 'Anmeldung erfolgreich!'
            self.ids.result_label.color = (0, 0, 0, 1)  # Schwarzer Farbe
            self.manager.current = 'main'
        else:
            self.ids.result_label.text = 'Falscher Code eingegeben.'
            self.ids.result_label.color = (0, 0, 0, 1)  # Schwarzer Farbe

    def reset_password_input(self):
        self.ids.password_input.text = ''

    def quit_app(self):
        App.get_running_app().stop()


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.client_socket = None
        self.ids.ip_address.bind(text=self.validate_ip_address)
        self.bt_client = None
        self.device_address = "24:0A:C4:C3:DD:5A"



    def disconnect(self):
        login_screen = self.manager.get_screen('login')
        login_screen.ids.password_input.text = ''
        login_screen.ids.result_label.text = ''
        self.manager.current = 'login'
        self.ids.led_on_wifi_button.disabled = True
        self.ids.led_off_wifi_button.disabled = True
        self.ids.led_on_ble_button.disabled = True
        self.ids.led_off_ble_button.disabled = True
        self.ids.bluetooth_status_label.text = ''
        self.ids.result_label_ip.text = ''
        self.ids.ip_address.text = ''
        self.update_button_colors(wifi=True, state=None)
        self.update_button_colors(ble=True, state=None)

    def get_ip_address(self):
        return self.ids.ip_address.text  # Gibt die eingegebene IP-Adresse zurück

    def is_valid_ip(self, ip):
        parts = ip.split('.')
        # Überprüft, ob die IP-Adresse aus vier durch Punkte getrennten Teilen besteht.

        # Überprüft, ob es genau 4 Teile gibt und der letzte Teil 3 Ziffern enthält.
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            if 1 <= len(parts[3]) == 3:
                return True
        return False

        # Prüft, ob eine Verbindung zu einer bestimmten IP-Adresse und einem bestimmten Port möglich ist
    def is_reachable(self, ip, port=12345, timeout=1):
        try:
             # Erstellt einen Socket und versucht, eine Verbindung herzustellen
            with socket.create_connection((ip, port), timeout=timeout):
                return True  # Verbindung erfolgreich
        except (socket.timeout, socket.error):
            return False  # Verbindung fehlgeschlagen

    def validate_ip_address(self, instance, value):
        # Überprüft, ob die eingegebene IP-Adresse gültig ist
        if self.is_valid_ip(value):
            # Prüft, ob das Gerät unter dieser IP-Adresse erreichbar ist
            if self.is_reachable(value):
                self.ids.result_label_ip.text = 'IP-Adresse ist verbunden!'
                self.ids.led_on_wifi_button.disabled = False
                self.ids.led_off_wifi_button.disabled = False
                self.ids.disconnect_wifi_button.disabled = False
            else:
                self.ids.result_label_ip.text = 'IP-Adresse nicht erreichbar.'
                self.ids.led_on_wifi_button.disabled = True
                self.ids.led_off_wifi_button.disabled = True
                self.ids.disconnect_wifi_button.disabled = True
        else:
            self.ids.result_label_ip.text = 'IP-Adresse ungültig'  # Setzt das Ergebnis zurück, wenn die IP ungültig ist
            self.ids.led_on_wifi_button.disabled = True
            self.ids.led_off_wifi_button.disabled = True
            self.ids.disconnect_wifi_button.disabled = True



    def turn_on_led(self):
        try:
            ip_address = self.get_ip_address()  # Ruft die IP-Adresse ab
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Erstellt einen TCP/IP-Socket
            self.client_socket.connect(
                (ip_address, 12345))  # Verbindet sich mit dem Server an der angegebenen IP und Port
            self.client_socket.sendall(b'1')  # Sendet das Signal zum Einschalten der LED
            print("LED turned on via Wi-Fi")  # Gibt eine Erfolgsnachricht aus
            self.update_button_colors(wifi=True, state='on')  # Aktualisiert die Button-Farben
            self.ids.result_label_ip.text = 'LED ist an'
        except Exception as e:
            print(f"Error turning on LED via Wi-Fi: {e}")  # Gibt eine Fehlermeldung aus, wenn ein Fehler auftritt

    def turn_off_led(self):
        try:
            self.client_socket.sendall(b'0')  # Sendet das Signal zum Ausschalten der LED
            print("LED turned off via Wi-Fi")  # Gibt eine Erfolgsnachricht aus
            self.client_socket.close()  # Schließt die Socket-Verbindung
            self.update_button_colors(wifi=True, state='off')  # Aktualisiert die Button-Farben
            self.ids.result_label_ip.text = 'LED ist aus'
        except Exception as e:
            print(f"Error turning off LED via Wi-Fi: {e}")  # Gibt eine Fehlermeldung aus, wenn ein Fehler auftritt

    def disconnect_wifi(self):

        try:
            if self.client_socket:
                self.client_socket.close()  # Schließt die Wi-Fi-Verbindung
                self.client_socket = None
                print("Wi-Fi-Verbindung deaktiviert")

            else:
                print("Keine aktive Wi-Fi-Verbindung.")
                self.ids.result_label_ip.text = "Keine WLAN-Verbindung."
        except Exception as e:
            print(f"Fehler beim Trennen der Wi-Fi-Verbindung: {e}")
        finally:
            # Deaktiviert die Wi-Fi-bezogenen Buttons
            self.ids.led_on_wifi_button.disabled = True
            self.ids.led_off_wifi_button.disabled = True
            self.ids.disconnect_wifi_button.disabled = True
            self.ids.result_label_ip.text = ''
            self.ids.ip_address.text = ''
            self.ids.result_label_ip.text = "WLAN deaktiviert."
            self.update_button_colors(wifi=True, state=None)
    def start_connect_device(self):
        # Startet die Bluetooth-Verbindung
        asyncio.ensure_future(self.connect_device())

    async def connect_device(self):
        if self.device_address != "24:0A:C4:C3:DD:5A":
            print(f"Verbindung zu einer anderen Adresse verweigert: {self.device_address}")
            return

        print(f"Verbinde mit {self.device_address}...")
        self.ids.bluetooth_status_label.text = "BLE-Verbindung wird aufgebaut..."
        try:
            self.bt_client = BleakClient(self.device_address)
            await self.bt_client.connect()
            print(f"Verbunden mit {self.device_address}")
            Clock.schedule_once(lambda dt: self.enable_led_control_buttons())
            self.ids.bluetooth_status_label.text = "BLE verbunden."
        except Exception as e:
            print(f"Fehler beim Verbinden mit {self.device_address}: {e}")
            self.ids.bluetooth_status_label.text = "Verbindung fehlgeschlagen."

    def enable_led_control_buttons(self):
        # Aktiviert die LED-Tasten nach der Verbindung.
        self.ids.led_on_ble_button.disabled = False
        self.ids.led_off_ble_button.disabled = False
        self.ids.disconnect_button.disabled = False

    def control_led(self, state):
        # Ruft die asynchrone Funktion auf, um den LED-Befehl über Bluetooth zu senden.
        if self.bt_client and self.bt_client.is_connected:
            print(f"Versuche, den LED-Befehl zu senden: {state}")
            asyncio.ensure_future(self.send_led_command_async(state))  # Führt den Befehl asynchron aus
        else:
            print("Fehler: Das Bluetooth-Gerät ist nicht verbunden.")
            self.ids.bluetooth_status_label.text = "Fehler: BLE nicht verbunden"

    async def send_led_command_async(self, state):
        # Sendet einen Befehl an das BLE-Gerät, um die LED ein- oder auszuschalten.
        try:
            if not self.bt_client or not self.bt_client.is_connected:
                print("Fehler: Das Bluetooth-Gerät ist nicht verbunden.")
                self.ids.bluetooth_status_label.text = "Fehler: Keine Bluetooth-Verbindung"
                return

            print(f"Sende Befehl {state} an das Bluetooth-Gerät...")
            await self.bt_client.write_gatt_char(CHARACTERISTIC_UUID, bytearray([state]))

            # Aktualisierung der Benutzeroberfläche
            if state == 1:
                self.ids.bluetooth_status_label.text = "LED eingeschaltet"
                self.update_button_colors(ble=True, state='on')  # Aktualisierung der Farben
            else:
                self.ids.bluetooth_status_label.text = "LED ausgeschaltet"
                self.update_button_colors(ble=True, state='off')  # Aktualisierung der Farben

        except Exception as e:
            print(f"Fehler beim Senden des LED-Befehls: {e}")
            self.ids.bluetooth_status_label.text = f"Fehler: {e}"



    async def disconnect_device(self):
        # Bluetooth-Trennung.
        print("disconnect_device() wurde aufgerufen.")
        if self.bt_client and self.bt_client.is_connected:
            try:
                await self.bt_client.disconnect()
                print("BLE Trennung erfolgreich.")
            except Exception as e:
                print(f"Fehler beim BLE Trennen: {e}")
            finally:
                await self.reset_ble_client()
                Clock.schedule_once(lambda dt: self.reset_ui_after_disconnect())  # UI-Aktualisierung
                self.ids.bluetooth_status_label.text = "BLE erfolgreich getrennt."
                self.update_button_colors(ble=True, state=None)  # Setzt die Wi-Fi-Buttons auf Standard zurück
                self.update_button_colors(ble=False, state=None)
        else:
            print("Kein Gerät verbunden.")

    def disconnect_device_wrapper(self):
        # Ruft die Coroutine korrekt mit asyncio.create_task() auf.
        asyncio.ensure_future(self.disconnect_device())

    async def reset_ble_client(self):
        # Setzt den BLE-Client nach der Trennung zurück.
        if self.bt_client:
            await self.bt_client.disconnect()
        self.bt_client = None

    def reset_ui_after_disconnect(self):
        # Setzt die Benutzeroberfläche nach der Bluetooth-Trennung zurück.
        self.ids.disconnect_button.disabled = True  # Deaktiviert den Button nach der Trennung
        self.ids.led_on_ble_button.disabled = True
        self.ids.led_off_ble_button.disabled = True
        self.ids.bluetooth_status_label.text = "BLE Getrennt"

    def update_button_colors(self, wifi=None, ble=None, state=None):
        # Aktualisiert die Farben der Tasten entsprechend dem Zustand der LED
        default_color = (1, 1, 1, 1)
        green_color = (0, 1, 0, 1)
        red_color = (1, 0, 0, 1)

        if wifi:
            if state == 'on':
                self.ids.led_on_wifi_button.background_color = green_color
                self.ids.led_off_wifi_button.background_color = default_color
            elif state == 'off':
                self.ids.led_on_wifi_button.background_color = default_color
                self.ids.led_off_wifi_button.background_color = red_color
            else:
                self.ids.led_on_wifi_button.background_color = default_color
                self.ids.led_off_wifi_button.background_color = default_color

        if ble:
            if state == 'on':
                self.ids.led_on_ble_button.background_color = green_color
                self.ids.led_off_ble_button.background_color = default_color
            elif state == 'off':
                self.ids.led_on_ble_button.background_color = default_color
                self.ids.led_off_ble_button.background_color = red_color
            else:
                self.ids.led_on_ble_button.background_color = default_color
                self.ids.led_off_ble_button.background_color = default_color


class MKR_WiFi_1010_Steuerungs_AppApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainScreen(name='main'))
        return sm


async def main(app):
    await asyncio.gather(app.async_run("asyncio"))


if __name__ == '__main__':
    asyncio.run(main(MKR_WiFi_1010_Steuerungs_AppApp()))

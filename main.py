from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
import socket
import asyncio
from bleak import BleakClient
from kivy.clock import Clock  # Pour mettre à jour l'UI proprement

Builder.load_file("main.kv")

CHARACTERISTIC_UUID = "19b10002-e8f2-537e-4f6c-d104768a1214"

def run_in_loop(coro):
    """ Exécute une coroutine dans une boucle asyncio. """
    loop = asyncio.get_running_loop()
    return loop.run_until_complete(coro)

class LoginScreen(Screen):
    def connect(self, instance):
        password = self.ids.password_input.text
        if password == '1234':
            self.ids.result_label.text = 'Anmeldung erfolgreich!'
            self.manager.current = 'main'
        else:
            self.ids.result_label.text = 'Falscher Code eingegeben.'

    def reset_password_input(self):
        self.ids.password_input.text = ''

    def quit_app(self):
        App.get_running_app().stop()

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.client_socket = None
        self.bt_client = None
        self.device_address = "24:0A:C4:C3:DD:5A"
        self.ids.led_on_wifi_button.disabled = True
        self.ids.led_off_wifi_button.disabled = True
        self.ids.ip_address.bind(text=self.validate_ip_address)

    def disconnect(self):
        login_screen = self.manager.get_screen('login')
        login_screen.ids.password_input.text = ''
        login_screen.ids.result_label.text = ''
        self.manager.current = 'login'
        self.ids.led_on_wifi_button.disabled = True
        self.ids.led_off_wifi_button.disabled = True
        self.ids.led_on_button.disabled = True
        self.ids.led_off_button.disabled = True
        self.ids.bluetooth_status_label.text = ''
        self.ids.result_label_ip.text = ''
        self.ids.ip_address.text = ''

    def get_ip_address(self):
        return self.ids.ip_address.text  # Gibt die eingegebene IP-Adresse zurück

    def is_valid_ip(self, ip):
        # Überprüft, ob die IP-Adresse aus vier Teilen besteht und jeder Teil eine Zahl zwischen 0 und 255 ist
        parts = ip.split('.')
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            return True
        return False

    def validate_ip_address(self, instance, value):
        if self.is_valid_ip(value):  # Vérifie si le format de l'adresse IP est correct
            if self.is_reachable(value):  # Vérifie si l'appareil est connectable
                self.ids.result_label_ip.text = 'IP-Adresse ist korrekt und verbunden!'  # Adresse connectable
                self.ids.led_on_wifi_button.disabled = False  # Active les boutons WiFi
                self.ids.led_off_wifi_button.disabled = False
                self.ids.disconnect_wifi_button.disabled = False
            else:
                self.ids.result_label_ip.text = 'IP-Adresse ist korrekt, aber nicht erreichbar.'  # Adresse non connectable
                self.ids.led_on_wifi_button.disabled = True  # Désactive les boutons WiFi
                self.ids.led_off_wifi_button.disabled = True
                self.ids.disconnect_wifi_button.disabled = True
        else:
            self.ids.result_label_ip.text = 'Ungültige IP-Adresse eingegeben.'  # Adresse invalide
            self.ids.led_on_wifi_button.disabled = True
            self.ids.led_off_wifi_button.disabled = True
            self.ids.disconnect_wifi_button.disabled = True

    def is_reachable(self, ip, port=12345, timeout=2):

        try:
            # Création d'un socket et tentative de connexion
            with socket.create_connection((ip, port), timeout=timeout):
                return True  # La connexion a réussi
        except (socket.timeout, socket.error):
            return False  # La connexion a échoué



    def turn_on_led(self):
        try:
            ip_address = self.get_ip_address()  # Ruft die IP-Adresse ab
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Erstellt einen TCP/IP-Socket
            self.client_socket.connect((ip_address, 12345))  # Verbindet sich mit dem Server an der angegebenen IP und Port
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
                self.client_socket.close()  #
                self.client_socket = None
                print("Wi-Fi connection disabled")
                self.ids.result_label_ip.text = "WLAN deaktiviert."
            else:
                print("No active Wi-Fi connection.")
                self.ids.result_label_ip.text = "keine WLAN-Verbindung."
        except Exception as e:
            print(f"Error disconnecting Wi-Fi: {e}")
        finally:
            # Désactiver les boutons liés au Wi-Fi
            self.ids.led_on_wifi_button.disabled = True
            self.ids.led_off_wifi_button.disabled = True
            self.ids.disconnect_wifi_button.disabled = True  # Désactive le bouton Disconnect WiFi
            self.update_button_colors(wifi=True, state='off')

    def start_connect_device(self):
        """Démarre la connexion Bluetooth correctement."""
        asyncio.ensure_future(self.connect_device())


    async def connect_device(self):
        """Se connecte uniquement à l'Adresse MAC définie."""
        if self.device_address != "24:0A:C4:C3:DD:5A":
            print(f"Refus de connexion à une autre adresse : {self.device_address}")
            return
        print(f"Trying to connect to {self.device_address}...")
        asyncio.ensure_future(self.do_connect())

    async def do_connect(self):
        print(f"Connecting to {self.device_address}...")
        self.ids.bluetooth_status_label.text = "Connecting to Bluetooth device..."
        try:
            self.bt_client = BleakClient(self.device_address)
            await self.bt_client.connect()
            print(f"Connected to {self.device_address}")
            Clock.schedule_once(lambda dt: self.enable_led_control_buttons())  # Mise à jour UI
            self.ids.bluetooth_status_label.text = "Device connected successfully."
        except Exception as e:
            print(f"Error connecting to {self.device_address}: {e}")
            self.ids.bluetooth_status_label.text = "Connection failed."

    def enable_led_control_buttons(self):
        """Active les boutons LED après connexion."""
        self.ids.led_on_button.disabled = False
        self.ids.led_off_button.disabled = False
        self.ids.disconnect_button.disabled = False

    def control_led(self, state):
        """Appelle la fonction async pour envoyer la commande LED via Bluetooth."""
        if self.bt_client and self.bt_client.is_connected:
            print(f"Tentative d'envoi de la commande LED: {state}")
            asyncio.ensure_future(self.send_led_command_async(state))  # Exécute la commande en mode async
        else:
            print("Erreur : L'appareil Bluetooth n'est pas connecté.")
            self.ids.bluetooth_status_label.text = "Erreur : Appareil non connecté"


    async def send_led_command_async(self, state):
        """Envoie une commande au périphérique BLE pour allumer ou éteindre la LED."""
        try:
            if not self.bt_client or not self.bt_client.is_connected:
                print("Erreur : L'appareil Bluetooth n'est pas connecté.")
                self.ids.bluetooth_status_label.text = "Erreur : Pas de connexion Bluetooth"
                return  # Le return doit être ici, pas après.

            print(f"Envoi de la commande {state} à l'appareil Bluetooth...")
            await self.bt_client.write_gatt_char(CHARACTERISTIC_UUID, bytearray([state]))

            # Mise à jour de l'interface utilisateur
            if state == 1:
                self.ids.bluetooth_status_label.text = "LED allumée (Bluetooth)"
            else:
                self.ids.bluetooth_status_label.text = "LED éteinte (Bluetooth)"

        except Exception as e:
            print(f"Erreur lors de l'envoi de la commande LED : {e}")
            self.ids.bluetooth_status_label.text = f"Erreur : {e}"


    async def disconnect_device(self):
        """Déconnexion Bluetooth propre."""
        print("disconnect_device() called.")
        if self.bt_client and self.bt_client.is_connected:
            try:
                await self.bt_client.disconnect()
                print("Disconnection successful.")
            except Exception as e:
                print(f"Error during disconnection: {e}")
            finally:
                await self.reset_ble_client()
                Clock.schedule_once(lambda dt: self.reset_ui_after_disconnect())  # Mise à jour UI
                self.ids.bluetooth_status_label.text = "Device disconnected successfully."
        else:
            print("No device is connected.")

    async def reset_ble_client(self):
        """Réinitialise le client BLE après déconnexion."""
        if self.bt_client:
            await self.bt_client.disconnect()
        self.bt_client = None

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

    def reset_ui_after_disconnect(self):
        """Réinitialise l'interface après la déconnexion Bluetooth."""
        self.ids.disconnect_button.disabled = True  # ✅ Désactive le bouton après déconnexion
        self.ids.led_on_button.disabled = True
        self.ids.led_off_button.disabled = True
        self.ids.bluetooth_status_label.text = "Disconnected"
        
class MyArduinoAppApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainScreen(name='main'))
        return sm

async def main(app):
    await asyncio.gather(app.async_run("asyncio"))

if __name__ == '__main__':
    asyncio.run(main(MyArduinoAppApp()))

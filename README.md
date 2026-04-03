# Skaner Sieci

Aplikacja do monitorowania sieci lokalnej z graficznym interfejsem użytkownika (Tkinter).

## Funkcje

- **Wykrywanie urządzeń** — ping sweep całej podsieci, odczyt adresów MAC z tabeli ARP
- **Skanowanie portów** — sprawdzanie 23 popularnych usług (HTTP, HTTPS, SSH, RDP, SMB, FTP, VNC i inne)
- **Wykres obciążenia sieci** — live wykres download/upload dla całego interfejsu (ostatnie 60 sekund)
- **Wykresy latencji per urządzenie** — dwuklik na urządzenie otwiera okno z live wykresem ping (ms)
- **Automatyczny wybór interfejsu** — obsługa Wi-Fi i Ethernet

## Wymagania

- Windows 10 / 11
- Python 3.8+
- Uprawnienia administratora

## Instalacja

```bash
pip install psutil matplotlib
```

## Uruchomienie

Kliknij prawym przyciskiem `start.bat` → **Uruchom jako administrator**

lub ręcznie:

```bash
python main.py
```

## Instrukcja obsługi

Plik `instrukcja_obslugi.pdf` zawiera szczegółowy poradnik krok po kroku — od instalacji Pythona po obsługę wszystkich funkcji programu. Możesz też wygenerować go samodzielnie:

```bash
pip install fpdf2
python generuj_instrukcje.py
```

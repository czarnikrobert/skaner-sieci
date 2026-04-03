import tkinter as tk
from tkinter import ttk, simpledialog
import threading
import subprocess
import socket
import re
import time
import concurrent.futures
from collections import defaultdict, deque
from baza import BazaDanych

try:
    import psutil
    PSUTIL_DOSTEPNE = True
except ImportError:
    PSUTIL_DOSTEPNE = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_DOSTEPNE = True
except ImportError:
    MATPLOTLIB_DOSTEPNE = False

HISTORIA_MAX = 60  # sekund


# Popularne porty do skanowania: numer -> nazwa usługi
PORTY = {
    21:   "FTP",
    22:   "SSH",
    23:   "Telnet",
    25:   "SMTP",
    53:   "DNS",
    80:   "HTTP",
    110:  "POP3",
    139:  "NetBIOS",
    143:  "IMAP",
    443:  "HTTPS",
    445:  "SMB",
    554:  "RTSP",
    587:  "SMTP-SSL",
    631:  "IPP",
    993:  "IMAPS",
    995:  "POP3S",
    1883: "MQTT",
    3389: "RDP",
    5900: "VNC",
    7547: "TR-069",
    8080: "HTTP-alt",
    8443: "HTTPS-alt",
    9100: "Drukarka",
}


def pobierz_lokalny_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def ping(ip):
    try:
        wynik = subprocess.run(
            ["ping", "-n", "1", "-w", "400", ip],
            capture_output=True, timeout=2
        )
        return wynik.returncode == 0
    except Exception:
        return False


def sprawdz_port(ip, port, timeout=0.5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        wynik = s.connect_ex((ip, port))
        s.close()
        return wynik == 0
    except Exception:
        return False


def skanuj_porty(ip):
    """Zwraca listę otwartych portów dla podanego IP."""
    otwarte = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(sprawdz_port, ip, port): port for port in PORTY}
        for future in concurrent.futures.as_completed(futures):
            port = futures[future]
            if future.result():
                otwarte.append(port)
    return sorted(otwarte)


def czytaj_arp_cache():
    macs = {}
    try:
        wynik = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
        for linia in wynik.stdout.splitlines():
            dop = re.match(r"\s+(\d+\.\d+\.\d+\.\d+)\s+([\w-]{17})\s+", linia)
            if dop:
                ip = dop.group(1)
                mac = dop.group(2).replace("-", ":").upper()
                macs[ip] = mac
    except Exception:
        pass
    return macs


def rozwiaz_nazwe(ip):
    try:
        return socket.gethostbyaddr(ip)[0].split(".")[0]
    except Exception:
        return "Nieznane"


def pobierz_interfejsy_psutil():
    wynik = []
    if not PSUTIL_DOSTEPNE:
        return wynik
    try:
        adresy = psutil.net_if_addrs()
        statsy = psutil.net_if_stats()
        for nazwa, lista in adresy.items():
            for addr in lista:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    if statsy.get(nazwa) and statsy[nazwa].isup:
                        etykieta = f"{nazwa}  [{addr.address}]"
                        wynik.append((etykieta, nazwa, addr.address))
    except Exception:
        pass
    return wynik


class SkanerSieci:
    def __init__(self, root):
        self.root = root
        self.root.title("Skaner Sieci")
        self.root.geometry("1100x860")
        self.root.configure(bg="#0d1117")
        self.root.resizable(True, True)

        self.moj_ip = pobierz_lokalny_ip()
        self.prefix_sieci = ".".join(self.moj_ip.split(".")[:3])

        self.interfejsy = pobierz_interfejsy_psutil()
        self.wybrany_iface_var = tk.StringVar()
        self._aktywna_nazwa_iface = None

        for etykieta, nazwa, ip in self.interfejsy:
            if ip == self.moj_ip:
                self.wybrany_iface_var.set(etykieta)
                self._aktywna_nazwa_iface = nazwa
                break
        if not self.wybrany_iface_var.get() and self.interfejsy:
            self.wybrany_iface_var.set(self.interfejsy[0][0])
            self._aktywna_nazwa_iface = self.interfejsy[0][1]

        self._lock = threading.Lock()
        self.urzadzenia = {}  # ip -> {mac, nazwa, aktywny, porty, skanowanie_portow}

        self._prev_io = None
        self.predkosc_dl = 0
        self.predkosc_ul = 0
        self._skanowanie = False

        # Historia prędkości do wykresu
        self.historia_dl = deque([0] * HISTORIA_MAX, maxlen=HISTORIA_MAX)
        self.historia_ul = deque([0] * HISTORIA_MAX, maxlen=HISTORIA_MAX)

        # Otwarte okna per-urządzenie (ip -> Toplevel)
        self._okna_urzadzen = {}

        # Baza danych
        self.db = BazaDanych()

        # Poprzedni status urządzeń do wykrywania zmian (ip -> bool online)
        self._poprzedni_status = {}

        self._buduj_ui()
        self._dodaj_siebie()

        if not PSUTIL_DOSTEPNE:
            self._log("⚠  Brak psutil — uruchom: pip install psutil")

        self.root.after(300, self._uruchom_skan)
        self._petla_odswiezania()

    # ─── UI ───────────────────────────────────────────────────────────────────

    def _buduj_ui(self):
        # Pasek 1
        p1 = tk.Frame(self.root, bg="#161b22", pady=10)
        p1.pack(fill=tk.X)

        tk.Label(p1, text="Skaner Sieci", font=("Segoe UI", 15, "bold"),
                 bg="#161b22", fg="#58a6ff").pack(side=tk.LEFT, padx=20)
        tk.Label(p1, text="Interfejs:", bg="#161b22", fg="#8b949e",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(16, 4))

        etykiety = [e for e, _, __ in self.interfejsy] or ["Brak interfejsów"]
        self.combo = ttk.Combobox(p1, textvariable=self.wybrany_iface_var,
                                  values=etykiety, state="readonly", width=50,
                                  font=("Segoe UI", 9))
        self.combo.pack(side=tk.LEFT)
        self.combo.bind("<<ComboboxSelected>>", self._zmien_interfejs)

        # Pasek 2
        p2 = tk.Frame(self.root, bg="#161b22", pady=6)
        p2.pack(fill=tk.X)

        tk.Label(p2, text="Sieć:", bg="#161b22", fg="#8b949e",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(20, 4))

        self.subnet_var = tk.StringVar(value=self.prefix_sieci + ".0/24")
        tk.Entry(p2, textvariable=self.subnet_var, width=17,
                 bg="#21262d", fg="white", insertbackground="white",
                 font=("Consolas", 10), relief=tk.FLAT, bd=5).pack(side=tk.LEFT)

        self.btn_skan = tk.Button(p2, text="Skanuj sieć", command=self._uruchom_skan,
                                  bg="#238636", fg="white", font=("Segoe UI", 9, "bold"),
                                  relief=tk.FLAT, padx=12, cursor="hand2",
                                  activebackground="#2ea043")
        self.btn_skan.pack(side=tk.LEFT, padx=8)

        self.btn_porty = tk.Button(p2, text="Skanuj porty", command=self._uruchom_skan_portow,
                                   bg="#1f6feb", fg="white", font=("Segoe UI", 9, "bold"),
                                   relief=tk.FLAT, padx=12, cursor="hand2",
                                   activebackground="#388bfd")
        self.btn_porty.pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(p2, text="Wyczyść", command=self._wyczysc,
                  bg="#30363d", fg="#8b949e", font=("Segoe UI", 9),
                  relief=tk.FLAT, padx=10, cursor="hand2").pack(side=tk.LEFT)

        self.speed_var = tk.StringVar(value="")
        tk.Label(p2, textvariable=self.speed_var, bg="#161b22", fg="#3fb950",
                 font=("Consolas", 10, "bold")).pack(side=tk.RIGHT, padx=20)

        tk.Frame(self.root, bg="#30363d", height=1).pack(fill=tk.X)

        # Banner powiadomień (domyślnie ukryty)
        self._banner = tk.Frame(self.root, bg="#1f4e2e", pady=5)
        self._banner_label = tk.Label(self._banner, text="", bg="#1f4e2e", fg="#3fb950",
                                      font=("Segoe UI", 9, "bold"))
        self._banner_label.pack(side=tk.LEFT, padx=14)
        tk.Button(self._banner, text="x", bg="#1f4e2e", fg="#3fb950", relief=tk.FLAT,
                  font=("Segoe UI", 8), cursor="hand2",
                  command=self._ukryj_banner).pack(side=tk.RIGHT, padx=8)

        # Tabela
        glowny = tk.Frame(self.root, bg="#0d1117")
        glowny.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        styl = ttk.Style()
        styl.theme_use("clam")
        styl.configure("S.Treeview", background="#161b22", foreground="#c9d1d9",
                        fieldbackground="#161b22", rowheight=30, font=("Consolas", 10))
        styl.configure("S.Treeview.Heading", background="#21262d", foreground="#58a6ff",
                        font=("Segoe UI", 9, "bold"), relief=tk.FLAT)
        styl.map("S.Treeview", background=[("selected", "#1f6feb")],
                 foreground=[("selected", "white")])

        kolumny = ("ip", "mac", "nazwa", "porty", "status")
        self.tabela = ttk.Treeview(glowny, columns=kolumny, show="headings",
                                   style="S.Treeview", height=14)

        self.tabela.heading("ip",     text="Adres IP")
        self.tabela.heading("mac",    text="MAC")
        self.tabela.heading("nazwa",  text="Nazwa urządzenia")
        self.tabela.heading("porty",  text="Otwarte porty (usługi)")
        self.tabela.heading("status", text="Status")

        self.tabela.column("ip",     width=130, anchor=tk.W)
        self.tabela.column("mac",    width=145, anchor=tk.W)
        self.tabela.column("nazwa",  width=175, anchor=tk.W)
        self.tabela.column("porty",  width=420, anchor=tk.W)
        self.tabela.column("status", width=95,  anchor=tk.CENTER)

        scroll = ttk.Scrollbar(glowny, orient=tk.VERTICAL, command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll.set)
        self.tabela.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Dwuklik → szczegóły / prawy klik → menu
        self.tabela.bind("<Double-1>", self._pokaz_szczegoly)
        self.tabela.bind("<Button-3>", self._menu_kontekstowe)

        # Wykres
        self._buduj_wykres()

        # Log
        ramka_log = tk.Frame(self.root, bg="#161b22")
        ramka_log.pack(fill=tk.X, padx=12, pady=(0, 4))

        tk.Label(ramka_log, text="Log:", bg="#161b22", fg="#484f58",
                 font=("Segoe UI", 8)).pack(anchor=tk.W, padx=4)

        self.log_tekst = tk.Text(ramka_log, height=4, bg="#0d1117", fg="#484f58",
                                 font=("Consolas", 8), relief=tk.FLAT, state=tk.DISABLED)
        self.log_tekst.pack(fill=tk.X, padx=4, pady=(0, 4))

        # Dolny pasek
        dolny = tk.Frame(self.root, bg="#161b22", pady=5)
        dolny.pack(fill=tk.X)

        self.live_var = tk.StringVar(value="● LIVE")
        tk.Label(dolny, textvariable=self.live_var, bg="#161b22", fg="#3fb950",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=16)

        self.licznik_var = tk.StringVar(value="0 urządzeń")
        tk.Label(dolny, textvariable=self.licznik_var, bg="#161b22", fg="#8b949e",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)

        self.status_var = tk.StringVar(value="")
        tk.Label(dolny, textvariable=self.status_var, bg="#161b22", fg="#8b949e",
                 font=("Segoe UI", 9)).pack(side=tk.RIGHT, padx=16)

    # ─── Logika ───────────────────────────────────────────────────────────────

    def _log(self, tekst):
        def _zapis():
            self.log_tekst.configure(state=tk.NORMAL)
            self.log_tekst.insert(tk.END, tekst + "\n")
            self.log_tekst.see(tk.END)
            self.log_tekst.configure(state=tk.DISABLED)
        self.root.after(0, _zapis)

    def _zmien_interfejs(self, event=None):
        wybrana = self.wybrany_iface_var.get()
        for etykieta, nazwa, ip in self.interfejsy:
            if etykieta == wybrana:
                self._aktywna_nazwa_iface = nazwa
                self.moj_ip = ip
                self.prefix_sieci = ".".join(ip.split(".")[:3])
                self.subnet_var.set(self.prefix_sieci + ".0/24")
                self._log(f"Interfejs: {nazwa}  [{ip}]")
                break

    def _dodaj_siebie(self):
        try:
            nazwa = socket.gethostname()
        except Exception:
            nazwa = "Ten komputer"
        with self._lock:
            istniejacy = self.urzadzenia.get(self.moj_ip, {})
            self.urzadzenia[self.moj_ip] = {
                "mac": "—",
                "nazwa": f"{nazwa} ★",
                "aktywny": True,
                "porty": istniejacy.get("porty", None),
                "skanowanie_portow": istniejacy.get("skanowanie_portow", False),
            }

    def _uruchom_skan(self):
        if self._skanowanie:
            self._log("Skanowanie już trwa...")
            return
        self._skanowanie = True
        self.btn_skan.configure(text="Skanowanie...", state=tk.DISABLED, bg="#484f58")
        threading.Thread(target=self._skan_watek, daemon=True).start()

    def _skan_watek(self):
        try:
            prefix = self.prefix_sieci
            self._log(f"Ping sweep: {prefix}.1 – {prefix}.254")

            adresy = [f"{prefix}.{i}" for i in range(1, 255)]
            aktywne = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=80) as executor:
                futures = {executor.submit(ping, ip): ip for ip in adresy}
                for future in concurrent.futures.as_completed(futures):
                    ip = futures[future]
                    if future.result():
                        aktywne.append(ip)

            self._log(f"Ping: {len(aktywne)} aktywnych")
            macs = czytaj_arp_cache()
            self._log(f"ARP: {len(macs)} wpisów")

            znalezione = 0
            nowe_ip = []
            for ip in aktywne:
                mac = macs.get(ip, "—")

                # Sprawdź czy nowe (przed zapisem do DB)
                if self.db.czy_nowe(ip):
                    nowe_ip.append(ip)

                # Zapisz do DB i pobierz ewentualną własną nazwę
                self.db.zapisz_urzadzenie(ip, mac)
                nazwa_uzytkownika = self.db.pobierz_nazwe(ip)
                nazwa = nazwa_uzytkownika if nazwa_uzytkownika else rozwiaz_nazwe(ip)

                with self._lock:
                    if ip not in self.urzadzenia:
                        znalezione += 1
                    prev = self.urzadzenia.get(ip, {})
                    self.urzadzenia[ip] = {
                        "mac": mac,
                        "nazwa": nazwa,
                        "aktywny": True,
                        "porty": prev.get("porty", None),
                        "skanowanie_portow": prev.get("skanowanie_portow", False),
                    }

                # Historia: zapisz zdarzenie online jeśli status się zmienił
                if self._poprzedni_status.get(ip) is not True:
                    self.db.dodaj_zdarzenie(ip, "online")
                self._poprzedni_status[ip] = True

            with self._lock:
                for ip in list(self.urzadzenia.keys()):
                    if ip not in aktywne and ip != self.moj_ip:
                        self.urzadzenia[ip]["aktywny"] = False
                        # Historia: zapisz zdarzenie offline
                        if self._poprzedni_status.get(ip) is True:
                            self.db.dodaj_zdarzenie(ip, "offline")
                        self._poprzedni_status[ip] = False

            # Powiadom o nowych urządzeniach
            for ip in nowe_ip:
                self.root.after(0, lambda a=ip: self._powiadom(a))

            self._log(f"Gotowe: {len(self.urzadzenia)} urządzeń (+{znalezione} nowych)")
            self.root.after(0, lambda: self.status_var.set(
                f"Skan: {len(aktywne)} online  |  Mój IP: {self.moj_ip}"
            ))

        except Exception as e:
            self._log(f"BŁĄD: {e}")
        finally:
            self._skanowanie = False
            self.root.after(0, lambda: self.btn_skan.configure(
                text="Skanuj sieć", state=tk.NORMAL, bg="#238636"
            ))

    def _uruchom_skan_portow(self):
        with self._lock:
            ip_do_skanu = [
                ip for ip, dev in self.urzadzenia.items()
                if dev.get("aktywny") and not dev.get("skanowanie_portow")
            ]
        if not ip_do_skanu:
            self._log("Brak urządzeń do skanowania portów (najpierw skanuj sieć)")
            return
        self._log(f"Skanowanie portów: {len(ip_do_skanu)} urządzeń...")
        self.btn_porty.configure(text="Skanowanie...", state=tk.DISABLED, bg="#484f58")
        threading.Thread(target=self._skan_portow_watek,
                         args=(ip_do_skanu,), daemon=True).start()

    def _skan_portow_watek(self, lista_ip):
        ukonczone = 0
        for ip in lista_ip:
            with self._lock:
                self.urzadzenia.setdefault(ip, {})["skanowanie_portow"] = True

            self._log(f"  Porty: {ip}...")
            otwarte = skanuj_porty(ip)

            with self._lock:
                if ip in self.urzadzenia:
                    self.urzadzenia[ip]["porty"] = otwarte
                    self.urzadzenia[ip]["skanowanie_portow"] = False

            nazwy = ", ".join(f"{p}/{PORTY[p]}" for p in otwarte) if otwarte else "brak"
            self._log(f"  {ip}: {nazwy}")
            ukonczone += 1

        self._log(f"Porty gotowe: przeskanowano {ukonczone} urządzeń")
        self.root.after(0, lambda: self.btn_porty.configure(
            text="Skanuj porty", state=tk.NORMAL, bg="#1f6feb"
        ))

    def _wyczysc(self):
        with self._lock:
            self.urzadzenia.clear()
        self._poprzedni_status.clear()
        self._dodaj_siebie()
        self._log("Wyczyszczono")

    # ── Powiadomienia ─────────────────────────────────────────────────────────

    def _powiadom(self, ip: str):
        info = self.db.pobierz_info(ip)
        mac = info[0] if info else "—"
        tekst = f"Nowe urzadzenie w sieci:  {ip}  (MAC: {mac})"
        self._banner_label.configure(text=tekst)
        self._banner.pack(fill=tk.X, after=self.root.nametowidget(
            self.root.winfo_children()[2].winfo_name()  # po separatorze
        ) if False else self._banner)
        self._banner.pack(fill=tk.X)
        self._log(f"[!] Nowe urzadzenie: {ip}  MAC: {mac}")
        self.root.after(8000, self._ukryj_banner)

    def _ukryj_banner(self):
        self._banner.pack_forget()

    # ── Menu kontekstowe ──────────────────────────────────────────────────────

    def _menu_kontekstowe(self, event):
        wiersz = self.tabela.identify_row(event.y)
        if not wiersz:
            return
        self.tabela.selection_set(wiersz)
        ip = self.tabela.item(wiersz, "values")[0]

        menu = tk.Menu(self.root, tearoff=0, bg="#21262d", fg="white",
                       activebackground="#1f6feb", activeforeground="white",
                       relief=tk.FLAT, bd=0)
        menu.add_command(label=f"  {ip}", state=tk.DISABLED,
                         font=("Segoe UI", 8))
        menu.add_separator()
        menu.add_command(label="  Zmien nazwe",
                         command=lambda: self._zmien_nazwe(ip))
        menu.add_command(label="  Historia polaczen",
                         command=lambda: self._pokaz_historie(ip))
        menu.add_separator()
        menu.add_command(label="  Szczegoly i wykres latencji",
                         command=lambda: self._otworz_szczegoly_ip(ip))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _otworz_szczegoly_ip(self, ip):
        """Otwiera okno szczegółów bez zdarzenia kliknięcia."""
        class FakeEvent:
            pass
        self.tabela.selection_set(
            next((w for w in self.tabela.get_children()
                  if self.tabela.item(w, "values")[0] == ip), "")
        )
        self.tabela.focus(
            next((w for w in self.tabela.get_children()
                  if self.tabela.item(w, "values")[0] == ip), "")
        )
        self._pokaz_szczegoly(FakeEvent())

    # ── Zmiana nazwy ──────────────────────────────────────────────────────────

    def _zmien_nazwe(self, ip: str):
        aktualna = self.db.pobierz_nazwe(ip) or ""
        nowa = simpledialog.askstring(
            "Zmien nazwe",
            f"Nowa nazwa dla {ip}:",
            initialvalue=aktualna,
            parent=self.root,
        )
        if nowa is None:
            return  # anulowano
        nowa = nowa.strip()
        self.db.zapisz_nazwe(ip, nowa if nowa else "")
        with self._lock:
            if ip in self.urzadzenia:
                self.urzadzenia[ip]["nazwa"] = nowa if nowa else self.urzadzenia[ip]["nazwa"]
        self._log(f"Nazwa '{ip}' zmieniona na: {nowa or '(usunieta)'}")

    # ── Historia urządzenia ───────────────────────────────────────────────────

    def _pokaz_historie(self, ip: str):
        historia = self.db.pobierz_historie(ip, limit=60)
        info = self.db.pobierz_info(ip)

        okno = tk.Toplevel(self.root)
        okno.title(f"Historia — {ip}")
        okno.configure(bg="#0d1117")
        okno.geometry("480x480")
        okno.resizable(True, True)

        tk.Label(okno, text=f"Historia polaczen: {ip}",
                 font=("Consolas", 12, "bold"), bg="#0d1117", fg="#58a6ff").pack(pady=(14, 2))

        if info:
            _, nazwa_uz, pierwsza, ostatnia = info
            szczeg = f"Pierwsza wizyta: {pierwsza or '—'}   Ostatnia: {ostatnia or '—'}"
            tk.Label(okno, text=szczeg, bg="#0d1117", fg="#8b949e",
                     font=("Segoe UI", 8)).pack()

        tk.Frame(okno, bg="#30363d", height=1).pack(fill=tk.X, pady=8, padx=14)

        if not historia:
            tk.Label(okno, text="Brak zapisanej historii.",
                     bg="#0d1117", fg="#484f58", font=("Segoe UI", 10)).pack(pady=20)
        else:
            ramka = tk.Frame(okno, bg="#0d1117")
            ramka.pack(fill=tk.BOTH, expand=True, padx=14)

            scroll = tk.Scrollbar(ramka)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)

            lista = tk.Text(ramka, bg="#161b22", fg="#c9d1d9",
                            font=("Consolas", 9), relief=tk.FLAT,
                            state=tk.DISABLED, yscrollcommand=scroll.set)
            lista.pack(fill=tk.BOTH, expand=True)
            scroll.configure(command=lista.yview)

            lista.tag_configure("online",  foreground="#3fb950")
            lista.tag_configure("offline", foreground="#f85149")
            lista.tag_configure("czas",    foreground="#484f58")

            lista.configure(state=tk.NORMAL)
            for status, ts in historia:
                ikona = ">> ONLINE " if status == "online" else "   OFFLINE"
                tag = "online" if status == "online" else "offline"
                lista.insert(tk.END, ikona, tag)
                lista.insert(tk.END, f"   {ts}\n", "czas")
            lista.configure(state=tk.DISABLED)

        tk.Button(okno, text="Zamknij", command=okno.destroy,
                  bg="#30363d", fg="white", relief=tk.FLAT, padx=20,
                  cursor="hand2").pack(pady=10)

    def _pokaz_szczegoly(self, event):
        """Popup ze szczegółami i live wykresem latencji po dwukliknięciu wiersza."""
        zaznaczony = self.tabela.focus()
        if not zaznaczony:
            return
        wartosci = self.tabela.item(zaznaczony, "values")
        if not wartosci:
            return
        ip = wartosci[0]

        # Jeśli okno już otwarte — przenieś na wierzch
        if ip in self._okna_urzadzen:
            try:
                self._okna_urzadzen[ip].lift()
                return
            except tk.TclError:
                pass

        with self._lock:
            dev = self.urzadzenia.get(ip, {})

        okno = tk.Toplevel(self.root)
        okno.title(f"{ip}  —  {dev.get('nazwa', '—')}")
        okno.configure(bg="#0d1117")
        okno.geometry("620x540")
        okno.resizable(True, True)
        self._okna_urzadzen[ip] = okno
        okno.protocol("WM_DELETE_WINDOW", lambda: self._zamknij_okno(ip, okno))

        # Nagłówek
        tk.Label(okno, text=ip, font=("Consolas", 14, "bold"),
                 bg="#0d1117", fg="#58a6ff").pack(pady=(14, 2))
        tk.Label(okno, text=f"MAC: {dev.get('mac', '—')}   Nazwa: {dev.get('nazwa', '—')}",
                 bg="#0d1117", fg="#8b949e", font=("Segoe UI", 9)).pack()
        tk.Frame(okno, bg="#30363d", height=1).pack(fill=tk.X, pady=8, padx=14)

        # Porty
        ramka_porty = tk.Frame(okno, bg="#0d1117")
        ramka_porty.pack(fill=tk.X, padx=14)

        porty = dev.get("porty")
        if porty is None:
            tekst_portow = "Porty: nie zeskanowane (kliknij 'Skanuj porty' w głównym oknie)"
            kolor_portow = "#484f58"
        elif not porty:
            tekst_portow = "Porty: brak otwartych"
            kolor_portow = "#484f58"
        else:
            tekst_portow = "Porty: " + "  ".join(f"{p}/{PORTY.get(p,'?')}" for p in porty)
            kolor_portow = "#79c0ff"
        tk.Label(ramka_porty, text=tekst_portow, bg="#0d1117", fg=kolor_portow,
                 font=("Consolas", 9), wraplength=580, justify=tk.LEFT).pack(anchor=tk.W)

        tk.Frame(okno, bg="#30363d", height=1).pack(fill=tk.X, pady=8, padx=14)

        # Wykres latencji
        HIST = 30
        historia_rtt = deque([None] * HIST, maxlen=HIST)
        rtt_var = tk.StringVar(value="Ping: —")

        tk.Label(okno, textvariable=rtt_var, bg="#0d1117", fg="#3fb950",
                 font=("Consolas", 11, "bold")).pack()

        if MATPLOTLIB_DOSTEPNE:
            fig, ax = plt.subplots(figsize=(5.8, 2.5), dpi=90)
            fig.patch.set_facecolor("#0d1117")
            ax.set_facecolor("#161b22")

            xs = list(range(-HIST + 1, 1))
            linia_rtt, = ax.plot(xs, [0] * HIST, color="#3fb950", linewidth=1.5)
            kropki_timeout = ax.scatter([], [], color="#f85149", s=30, zorder=5)

            ax.set_xlim(-HIST + 1, 0)
            ax.set_ylim(0, 100)
            ax.set_xlabel("pomiary temu", color="#484f58", fontsize=7)
            ax.set_ylabel("ms", color="#484f58", fontsize=7)
            ax.tick_params(colors="#484f58", labelsize=7)
            for spine in ax.spines.values():
                spine.set_edgecolor("#30363d")
            ax.grid(True, color="#21262d", linewidth=0.5, linestyle="--")
            fig.tight_layout(pad=0.5)

            canvas_okna = FigureCanvasTkAgg(fig, master=okno)
            canvas_okna.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=14, pady=(4, 10))

            def aktualizuj_wykres_okna():
                try:
                    dane = list(historia_rtt)
                    wartosci_y = [v if v is not None else 0 for v in dane]
                    linia_rtt.set_ydata(wartosci_y)

                    # Czerwone kropki dla timeoutów
                    timeout_x = [xs[i] for i, v in enumerate(dane) if v is None]
                    timeout_y = [0] * len(timeout_x)
                    kropki_timeout.set_offsets(
                        list(zip(timeout_x, timeout_y)) if timeout_x else [[None, None]]
                    )

                    maks = max((v for v in dane if v is not None), default=100)
                    ax.set_ylim(0, max(maks * 1.3, 10))
                    canvas_okna.draw_idle()
                except Exception:
                    pass
        else:
            aktualizuj_wykres_okna = lambda: None

        # Wątek pingujący
        def ping_watek():
            while True:
                try:
                    if not okno.winfo_exists():
                        break
                except Exception:
                    break

                t0 = time.time()
                wynik = subprocess.run(
                    ["ping", "-n", "1", "-w", "2000", ip],
                    capture_output=True, timeout=3
                )
                elapsed_ms = (time.time() - t0) * 1000

                if wynik.returncode == 0:
                    # Wyciągnij RTT z outputu (polskie/angielskie Windows)
                    out = wynik.stdout.decode("cp852", errors="ignore")
                    dop = re.search(r'[Cc]zas[<=](\d+)\s*ms|[Tt]ime[<=](\d+)\s*ms', out)
                    rtt = int(dop.group(1) or dop.group(2)) if dop else int(elapsed_ms)
                    historia_rtt.append(rtt)
                    okno.after(0, lambda r=rtt: rtt_var.set(f"Ping: {r} ms"))
                else:
                    historia_rtt.append(None)
                    okno.after(0, lambda: rtt_var.set("Ping: timeout"))

                okno.after(0, aktualizuj_wykres_okna)
                time.sleep(3)

        threading.Thread(target=ping_watek, daemon=True).start()

    def _zamknij_okno(self, ip, okno):
        self._okna_urzadzen.pop(ip, None)
        try:
            okno.destroy()
        except Exception:
            pass

    # ─── Wykres ───────────────────────────────────────────────────────────────

    def _buduj_wykres(self):
        if not MATPLOTLIB_DOSTEPNE:
            ramka = tk.Frame(self.root, bg="#161b22", height=30)
            ramka.pack(fill=tk.X, padx=12)
            tk.Label(ramka, text="⚠  Brak matplotlib — pip install matplotlib",
                     bg="#161b22", fg="#f85149", font=("Segoe UI", 9)).pack(pady=6)
            self._wykres_canvas = None
            return

        ramka = tk.Frame(self.root, bg="#0d1117")
        ramka.pack(fill=tk.X, padx=12, pady=(0, 4))

        fig, self._ax = plt.subplots(figsize=(10, 2.2), dpi=90)
        fig.patch.set_facecolor("#0d1117")
        self._ax.set_facecolor("#161b22")

        xs = list(range(-HISTORIA_MAX + 1, 1))
        self._linia_dl, = self._ax.plot(xs, list(self.historia_dl),
                                        color="#58a6ff", linewidth=1.5, label="Download")
        self._linia_ul, = self._ax.plot(xs, list(self.historia_ul),
                                        color="#3fb950", linewidth=1.5, label="Upload")

        self._ax.set_xlim(-HISTORIA_MAX + 1, 0)
        self._ax.set_ylim(0, 1)
        self._ax.tick_params(colors="#484f58", labelsize=7)
        self._ax.xaxis.label.set_color("#484f58")
        for spine in self._ax.spines.values():
            spine.set_edgecolor("#30363d")
        self._ax.set_xlabel("sekundy temu", color="#484f58", fontsize=7)
        self._ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda v, _: self._fmt(v))
        )
        self._ax.grid(True, color="#21262d", linewidth=0.5, linestyle="--")
        self._ax.legend(loc="upper left", fontsize=7, framealpha=0,
                        labelcolor=["#58a6ff", "#3fb950"])
        fig.tight_layout(pad=0.4)

        self._wykres_canvas = FigureCanvasTkAgg(fig, master=ramka)
        self._wykres_canvas.get_tk_widget().pack(fill=tk.X)

    def _aktualizuj_wykres(self):
        if not MATPLOTLIB_DOSTEPNE or self._wykres_canvas is None:
            return
        try:
            dl_data = list(self.historia_dl)
            ul_data = list(self.historia_ul)
            xs = list(range(-HISTORIA_MAX + 1, 1))

            self._linia_dl.set_ydata(dl_data)
            self._linia_ul.set_ydata(ul_data)

            maks = max(max(dl_data), max(ul_data), 1024)
            self._ax.set_ylim(0, maks * 1.15)
            self._wykres_canvas.draw_idle()
        except Exception:
            pass

    # ─── Odświeżanie ──────────────────────────────────────────────────────────

    def _pobierz_predkosci(self):
        if not PSUTIL_DOSTEPNE:
            return
        try:
            io = psutil.net_io_counters(pernic=True)
            curr = io.get(self._aktywna_nazwa_iface) if self._aktywna_nazwa_iface else None
            if curr is None:
                curr = psutil.net_io_counters()
            if self._prev_io is not None:
                self.predkosc_dl = max(0, curr.bytes_recv - self._prev_io.bytes_recv)
                self.predkosc_ul = max(0, curr.bytes_sent - self._prev_io.bytes_sent)
            self._prev_io = curr
        except Exception:
            pass

    @staticmethod
    def _fmt(bps):
        if bps < 1024:
            return f"{bps} B/s"
        if bps < 1024 * 1024:
            return f"{bps / 1024:.1f} KB/s"
        return f"{bps / 1024 / 1024:.2f} MB/s"

    @staticmethod
    def _formatuj_porty(porty, skanowanie):
        if skanowanie:
            return "⏳ skanowanie..."
        if porty is None:
            return "—"
        if not porty:
            return "brak otwartych"
        return "  ".join(f"{p}/{PORTY.get(p, '?')}" for p in porty)

    def _petla_odswiezania(self):
        self._pobierz_predkosci()

        # Dodaj punkt do historii i odśwież wykres
        self.historia_dl.append(self.predkosc_dl)
        self.historia_ul.append(self.predkosc_ul)
        self._aktualizuj_wykres()

        if PSUTIL_DOSTEPNE:
            self.speed_var.set(f"⬇ {self._fmt(self.predkosc_dl)}   ⬆ {self._fmt(self.predkosc_ul)}")

        with self._lock:
            kopia = {ip: dict(dev) for ip, dev in self.urzadzenia.items()}

        def klucz(ip):
            aktywny = kopia[ip].get("aktywny", False)
            try:
                czesci = list(map(int, ip.split(".")))
            except Exception:
                czesci = [0, 0, 0, 0]
            return (0 if aktywny else 1, czesci)

        posortowane = sorted(kopia, key=klucz)

        for w in self.tabela.get_children():
            self.tabela.delete(w)

        for ip in posortowane:
            dev = kopia[ip]
            aktywny = dev.get("aktywny", False)
            status = "✓ Online" if aktywny else "Offline"
            tag = "online" if aktywny else "offline"
            # Własna nazwa z DB ma priorytet
            nazwa_db = self.db.pobierz_nazwe(ip)
            nazwa = nazwa_db if nazwa_db else dev.get("nazwa", "—")
            self.tabela.insert("", tk.END, tags=(tag,), values=(
                ip,
                dev.get("mac", "—"),
                nazwa,
                self._formatuj_porty(dev.get("porty"), dev.get("skanowanie_portow", False)),
                status,
            ))

        self.tabela.tag_configure("online",  foreground="#79c0ff")
        self.tabela.tag_configure("offline", foreground="#484f58")

        online = sum(1 for d in kopia.values() if d.get("aktywny"))
        self.licznik_var.set(f"{online} online  /  {len(kopia)} łącznie")
        self.live_var.set("○ LIVE" if self.live_var.get().startswith("●") else "● LIVE")

        self.root.after(1000, self._petla_odswiezania)


if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = SkanerSieci(root)
    root.mainloop()

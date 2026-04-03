"""
Uruchom: python generuj_instrukcje.py
Wymaga:  pip install fpdf2
Tworzy:  instrukcja_obslugi.pdf
"""

from fpdf import FPDF

FONTS     = "C:\\Windows\\Fonts\\"
C_HEADER  = (30,  80, 160)
C_DARK    = (30,  30,  30)
C_GRAY    = (110, 110, 110)
C_GREEN   = (20, 120,  50)
C_WARN    = (170,  70,   0)
C_BG      = (240, 245, 250)
C_CODE    = (30,  50, 110)
C_WHITE   = (255, 255, 255)


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.add_font("R",  fname=FONTS + "arial.ttf")
        self.add_font("R",  style="B", fname=FONTS + "arialbd.ttf")
        self.add_font("R",  style="I", fname=FONTS + "ariali.ttf")
        self.add_font("M",  fname=FONTS + "cour.ttf")
        self.add_font("M",  style="B", fname=FONTS + "courbd.ttf")
        self._szer = 210 - 20 - 20  # A4 minus marginesy

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("R", size=8)
        self.set_text_color(*C_GRAY)
        self.cell(0, 8, f"Skaner Sieci - Instrukcja obslugi  |  str. {self.page_no()}", align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*C_GRAY)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)
        self.set_text_color(*C_DARK)

    def footer(self):
        self.set_y(-12)
        self.set_font("R", size=7)
        self.set_text_color(*C_GRAY)
        self.cell(0, 8, "Skaner Sieci  *  instrukcja wygenerowana automatycznie", align="C")


def strona_tytulowa(pdf: PDF):
    pdf.add_page()
    pdf.ln(35)

    pdf.set_font("R", "B", 30)
    pdf.set_text_color(*C_HEADER)
    pdf.cell(0, 15, "Skaner Sieci", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("R", size=14)
    pdf.set_text_color(*C_GRAY)
    pdf.cell(0, 10, "Instrukcja instalacji i obslugi", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_draw_color(*C_HEADER)
    pdf.set_line_width(0.6)
    pdf.line(40, pdf.get_y(), pdf.w - 40, pdf.get_y())
    pdf.ln(14)

    pdf.set_font("R", size=10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(0, 7,
        "Program umozliwia skanowanie sieci lokalnej, wykrywanie podlaczonych urzadzen, "
        "sprawdzanie otwartych portow oraz monitorowanie obciazenia sieci w czasie "
        "rzeczywistym wraz z wykresami latencji dla kazdego urzadzenia.",
        align="C")
    pdf.ln(22)

    # Ramka wymagania
    y0 = pdf.get_y()
    pdf.set_fill_color(*C_BG)
    pdf.set_draw_color(*C_HEADER)
    pdf.set_line_width(0.3)
    pdf.rect(pdf.l_margin, y0, pdf._szer, 50, style="FD")
    pdf.ln(4)

    pdf.set_font("R", "B", 10)
    pdf.set_text_color(*C_HEADER)
    pdf.cell(0, 8, "Wymagania systemowe", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("R", size=9)
    pdf.set_text_color(*C_DARK)
    for w in [
        "System operacyjny: Windows 10 lub Windows 11 (64-bit)",
        "Python 3.8 lub nowszy  (python.org/downloads)",
        "Polaczenie z internetem (do pobrania bibliotek)",
        "Uprawnienia administratora (wymagane do skanowania sieci)",
    ]:
        pdf.cell(10)
        pdf.cell(0, 7, f"-  {w}", new_x="LMARGIN", new_y="NEXT")


def sekcja(pdf: PDF, numer: str, tytul: str):
    pdf.ln(6)
    pdf.set_fill_color(*C_HEADER)
    pdf.set_font("R", "B", 11)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(0, 9, f"  {numer}  {tytul}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_text_color(*C_DARK)


def krok(pdf: PDF, n: int, tekst: str):
    pdf.set_font("R", "B", 10)
    pdf.set_text_color(*C_HEADER)
    pdf.cell(7, 7, f"{n}.")
    pdf.set_font("R", size=10)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(pdf._szer - 7, 7, tekst)
    pdf.ln(1)


def blok_kodu(pdf: PDF, *linie):
    pdf.set_fill_color(*C_BG)
    pdf.set_draw_color(200, 215, 230)
    pdf.set_line_width(0.2)
    y0 = pdf.get_y()
    wys = len(linie) * 6 + 4
    pdf.rect(pdf.l_margin, y0, pdf._szer, wys, style="FD")
    pdf.ln(2)
    pdf.set_font("M", size=9)
    pdf.set_text_color(*C_CODE)
    for l in linie:
        pdf.cell(4)
        pdf.cell(0, 6, l, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("R", size=10)
    pdf.set_text_color(*C_DARK)
    pdf.ln(2)


def uwaga(pdf: PDF, tekst: str):
    pdf.set_font("R", "I", 9)
    pdf.set_text_color(*C_GREEN)
    pdf.cell(4)
    pdf.multi_cell(pdf._szer - 4, 6, f">> {tekst}")
    pdf.set_font("R", size=10)
    pdf.set_text_color(*C_DARK)
    pdf.ln(1)


def ostrzezenie(pdf: PDF, tekst: str):
    pdf.set_font("R", "B", 9)
    pdf.set_text_color(*C_WARN)
    pdf.cell(4)
    pdf.multi_cell(pdf._szer - 4, 6, f"[!] {tekst}")
    pdf.set_font("R", size=10)
    pdf.set_text_color(*C_DARK)
    pdf.ln(1)


def punkt(pdf: PDF, tekst: str, wciec: int = 8):
    pdf.set_font("R", size=9)
    pdf.set_text_color(*C_DARK)
    pdf.cell(wciec)
    pdf.multi_cell(pdf._szer - wciec, 6, f"- {tekst}")


def tresc(pdf: PDF):
    # ── 1. Python ─────────────────────────────────────────────────────────────
    pdf.add_page()
    sekcja(pdf, "1.", "Instalacja Python")

    krok(pdf, 1, "Wejdz na strone: https://www.python.org/downloads")
    krok(pdf, 2, 'Kliknij duzy przycisk "Download Python 3.x.x" - pobierze sie plik .exe')
    krok(pdf, 3, "Uruchom pobrany plik instalatora")
    krok(pdf, 4, 'WAZNE: Na pierwszym ekranie zaznacz opcje "Add Python to PATH" '
                 'przed kliknieciem Install Now')
    ostrzezenie(pdf, 'Bez zaznaczenia "Add Python to PATH" Python nie bedzie widoczny '
                     'w terminalu i program nie uruchomi sie.')
    krok(pdf, 5, 'Kliknij "Install Now" i poczekaj na zakonczenie instalacji')
    krok(pdf, 6, "Sprawdz instalacje - otworz terminal (Win + R, wpisz cmd, Enter):")
    blok_kodu(pdf, "python --version")
    uwaga(pdf, "Powinno pojawic sie np. Python 3.12.0  "
               "Jesli pojawia sie blad, zrestartuj komputer i sprobuj ponownie.")

    # ── 2. Pliki ───────────────────────────────────────────────────────────────
    sekcja(pdf, "2.", "Przygotowanie plikow programu")

    krok(pdf, 1, "Skopiuj folder skaner-sieci na docelowy komputer (np. na Pulpit)")
    krok(pdf, 2, "Upewnij sie ze folder zawiera nastepujace pliki:")
    blok_kodu(pdf,
        "skaner-sieci/",
        "    main.py               <- glowny program",
        "    requirements.txt      <- lista bibliotek",
        "    start.bat             <- plik uruchamiajacy",
    )

    # ── 3. Biblioteki ──────────────────────────────────────────────────────────
    sekcja(pdf, "3.", "Instalacja wymaganych bibliotek")

    krok(pdf, 1, "Otworz terminal jako Administrator:")
    for t in [
        "Nacisnij klawisz Windows",
        'Wpisz: cmd',
        'Na wyniku kliknij prawym przyciskiem mysz na "Wiersz polecenia"',
        'Wybierz "Uruchom jako administrator"',
        'Kliknij "Tak" w oknie UAC',
    ]:
        punkt(pdf, t)
    pdf.ln(2)

    krok(pdf, 2, "Przejdz do folderu z programem (zmien sciezke na swoja):")
    blok_kodu(pdf, 'cd "C:\\Users\\TwojaNazwa\\Desktop\\skaner-sieci"')

    krok(pdf, 3, "Zainstaluj wymagane biblioteki:")
    blok_kodu(pdf, "pip install psutil matplotlib")
    uwaga(pdf, "Instalacja moze trwac 1-2 minuty. Poczekaj az pojawi sie "
               '"Successfully installed..."')

    krok(pdf, 4, "Sprawdz poprawnosc instalacji:")
    blok_kodu(pdf, 'python -c "import psutil, matplotlib; print(OK)"')
    uwaga(pdf, "Powinno pojawic sie OK. Jesli jest blad - powtorz krok 3.")

    # ── 4. Uruchomienie ────────────────────────────────────────────────────────
    pdf.add_page()
    sekcja(pdf, "4.", "Uruchomienie programu")

    pdf.set_font("R", "B", 10)
    pdf.set_text_color(*C_DARK)
    pdf.cell(0, 8, "Metoda A - przez plik start.bat (zalecana)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    for i, t in enumerate([
        "Otworz folder skaner-sieci w Eksploratorze plikow",
        "Kliknij prawym przyciskiem mysz na plik start.bat",
        'Wybierz "Uruchom jako administrator"',
        'Kliknij "Tak" w oknie UAC',
    ], 1):
        krok(pdf, i, t)
    uwaga(pdf, "Plik start.bat automatycznie poprosi o uprawnienia i uruchomi program.")

    pdf.ln(3)
    pdf.set_font("R", "B", 10)
    pdf.set_text_color(*C_DARK)
    pdf.cell(0, 8, "Metoda B - recznie przez terminal", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    krok(pdf, 1, "Otworz terminal jako Administrator (patrz sekcja 3, krok 1)")
    krok(pdf, 2, "Przejdz do folderu z programem:")
    blok_kodu(pdf, 'cd "C:\\Users\\TwojaNazwa\\Desktop\\skaner-sieci"')
    krok(pdf, 3, "Uruchom program:")
    blok_kodu(pdf, "python main.py")
    ostrzezenie(pdf, "Program MUSI byc uruchamiany jako Administrator. "
                     "Bez uprawnien skanowanie sieci nie bedzie dzialac.")

    # ── 5. Obsługa ────────────────────────────────────────────────────────────
    sekcja(pdf, "5.", "Obsluga programu - pierwsze kroki")

    for i, t in enumerate([
        "Po uruchomieniu program automatycznie rozpocznie skanowanie sieci.",
        "Wybor interfejsu: z listy rozwijanej w gornej czesci okna wybierz interfejs "
        "z adresem 192.168.x.x - jesli korzystasz z Wi-Fi wybierz interfejs Wi-Fi, "
        "jesli z kabla - Ethernet.",
        'Kliknij przycisk "Skanuj siec" - program wyśle ping do 254 adresow w podsieci. '
        "Skanowanie trwa ok. 3-5 sekund.",
        "Po zakonczeniu w tabeli pojawia sie wszystkie aktywne urzadzenia z adresem IP, "
        "MAC i nazwa.",
        '(Opcjonalnie) Kliknij "Skanuj porty" - program sprawdzi otwarte uslugi sieciowe '
        "(HTTP, SSH, RDP, FTP itp.) na kazdym urzadzeniu. Trwa dluzej - kilkanascie "
        "sekund na urzadzenie.",
    ], 1):
        krok(pdf, i, t)

    # ── 6. Funkcje ────────────────────────────────────────────────────────────
    pdf.add_page()
    sekcja(pdf, "6.", "Opis funkcji programu")

    for nazwa, opis in [
        ("Tabela urzadzen",
         "Wyswietla wszystkie wykryte urzadzenia. Aktywne - kolor niebieski, "
         "nieaktywne - szary. Kolumny: IP, MAC, nazwa, otwarte porty, status."),
        ("Wykres obciazenia sieci",
         "Widoczny pod tabela. Pokazuje predkosc pobierania (niebieska linia) "
         "i wysylania (zielona linia) dla calego interfejsu. Historia 60 sekund."),
        ("Wykres latencji urzadzenia",
         "Dwuklik na urzadzenie w tabeli otwiera okno z live wykresem pingu (ms). "
         "Odswiezanie co 3 sekundy. Czerwone kropki = brak odpowiedzi (timeout). "
         "Mozna otworzyc wiele okien jednoczesnie - dla kazdego urzadzenia osobno."),
        ("Log",
         "Pasek na dole okna pokazuje biezace komunikaty: postep skanowania, "
         "liczbe znalezionych urzadzen, bledy."),
        ("Przycisk Wyczysc",
         "Usuwa liste urzadzen i pozwala zaczac od nowa."),
    ]:
        pdf.set_font("R", "B", 10)
        pdf.set_text_color(*C_HEADER)
        pdf.cell(0, 7, f"* {nazwa}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("R", size=9)
        pdf.set_text_color(*C_DARK)
        pdf.cell(6)
        pdf.multi_cell(pdf._szer - 6, 6, opis)
        pdf.ln(2)

    # ── 7. Problemy ───────────────────────────────────────────────────────────
    sekcja(pdf, "7.", "Rozwiazywanie problemow")

    for problem, rozwiazania in [
        ("Program nie wykrywa urzadzen",
         [
             "Upewnij sie ze wybrany interfejs ma adres 192.168.x.x",
             "Sprawdz czy program jest uruchomiony jako Administrator",
             "Sprawdz czy zapora Windows nie blokuje ICMP (ping): "
             "Panel sterowania -> Zapora Windows Defender -> Zaawansowane ustawienia",
         ]),
        ("Blad: 'python' is not recognized",
         [
             "Python nie jest dodany do PATH",
             "Odinstaluj Python i zainstaluj ponownie zaznaczajac 'Add Python to PATH'",
         ]),
        ("Blad: ModuleNotFoundError (psutil lub matplotlib)",
         [
             "Biblioteki nie zostaly zainstalowane",
             "Otworz terminal jako Admin i wpisz: pip install psutil matplotlib",
         ]),
        ("Wykres nie wyswietla sie",
         [
             "Sprawdz instalacje: python -c \"import matplotlib\"",
             "Jesli blad: pip install matplotlib",
         ]),
        ("Skanowanie portow trwa bardzo dlugo",
         [
             "To normalne - program sprawdza 23 porty na kazdym urzadzeniu",
             "Dla 10 urzadzen moze trwac 1-3 minuty",
             "Mozna korzystac z programu podczas skanowania portow",
         ]),
    ]:
        pdf.set_font("R", "B", 10)
        pdf.set_text_color(*C_WARN)
        pdf.cell(0, 8, f"Problem: {problem}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("R", size=9)
        pdf.set_text_color(*C_DARK)
        for r in rozwiazania:
            pdf.cell(8)
            pdf.multi_cell(pdf._szer - 8, 6, f"-> {r}")
        pdf.ln(3)


def main():
    pdf = PDF()
    pdf.set_title("Skaner Sieci - Instrukcja obslugi")
    strona_tytulowa(pdf)
    tresc(pdf)
    plik = "instrukcja_obslugi.pdf"
    pdf.output(plik)
    print(f"Gotowe! Zapisano: {plik}")


if __name__ == "__main__":
    main()

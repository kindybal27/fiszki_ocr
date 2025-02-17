from flask import Flask, request, send_file, render_template_string
import cv2
import easyocr
import os
import re
import nltk
from nltk.corpus import words
from io import BytesIO
import base64

nltk.download("words")
angielskie = set(words.words())     # słownik angielski z zamianą z listy na zbiór

# wczytywanie polskiego słownika z pliku z zamianą na zbiór (set)
def wczytaj_polskie():
    sciezka_slownik = "slownik.txt"
    if os.path.exists(sciezka_slownik):
        with open(sciezka_slownik, "r", encoding="utf-8") as plik_s:
            return set(plik_s.read().splitlines())
    return set()

polskie = wczytaj_polskie()

fiszki = Flask(__name__)        # inicjacja aplikacji
DO_ZAPISU = "uploaded"          # folder na przesłane pliki

czytnik = easyocr.Reader(['pl', 'en'], gpu=True)

def filtrowanie(tekst):             # funkcja do filtrowania tekstu
    oczyszczony_tekst = re.sub(r"[^a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s]", "", tekst)     # usuwanie znaków, które nie są literami ani spacjami
    slowa = oczyszczony_tekst.split()                                           # dzielenie tekstu na słowa

    slowa_filtrowane = [s for s in slowa if s.lower() in polskie or s.lower() in angielskie]        # zostawienie słów tylko z polskiego i angielskiego słownika

    slowa_filtrowane = [s for s in slowa_filtrowane if len(s) > 2]          # usunięcie słów, które są krótsze niż 3 znaki
    return " ".join(slowa_filtrowane)

@fiszki.route("/", methods=["GET", "POST"])             # strona w flask
def index():
    if request.method == "POST":
        if "plik" not in request.files:
            return "Brak pliku"
        
        plik = request.files["plik"]
        if plik.filename == "":
            return "Brak wybranego pliku"
        
        sciezka_plik = os.path.join(DO_ZAPISU, plik.filename)
        plik.save(sciezka_plik)

        obraz = cv2.imread(sciezka_plik)                        
        obraz_szary = cv2.cvtColor(obraz, cv2.COLOR_BGR2GRAY)           # konwersja na c-b

        wyniki = czytnik.readtext(obraz_szary)

        rozpoznany_tekst = "\n".join([filtrowanie(wynik[1]) for wynik in wyniki])           # łączenie wyników w tekst dzieląc nową linią

        # Rysowanie prostokątów wokół rozpoznanych fragmentów tekstu
        for (bbox, tekst, prob) in wyniki:
            (top_left, top_right, bottom_right, bottom_left) = bbox
            top_left = tuple(map(int, top_left))
            bottom_right = tuple(map(int, bottom_right))

            # Sprawdzenie, czy słowo jest w słowniku
            if tekst.lower() in polskie or tekst.lower() in angielskie:
                kolor = (0, 255, 0)  # Zielony dla słów w słowniku
            else:
                kolor = (0, 0, 255)  # Czerwony dla słów nieznanych

            cv2.rectangle(obraz, top_left, bottom_right, kolor, 2)

        # Zapisanie obrazu z zaznaczonymi fragmentami do pliku
        sciezka_wynikowa = os.path.join(DO_ZAPISU, "wynik_" + plik.filename)
        cv2.imwrite(sciezka_wynikowa, obraz)

        # Konwersja obrazu do formatu base64 do osadzenia w HTML
        with open(sciezka_wynikowa, "rb") as img_file:
            obraz_base64 = base64.b64encode(img_file.read()).decode('utf-8')

        # Zwrócenie strony z rozpoznanym tekstem i obrazem
        return render_template_string('''
            <!doctype html>
            <title>Wynik OCR</title>
            <h1>Rozpoznany tekst:</h1>
            <pre>{{ rozpoznany_tekst }}</pre>
            <h1>Obraz z zaznaczonymi fragmentami:</h1>
            <img src="data:image/jpeg;base64,{{ obraz_base64 }}" alt="Obraz z zaznaczonym tekstem">
            <br>
            <a href="/">Wróć do przesyłania</a>
        ''', rozpoznany_tekst=rozpoznany_tekst, obraz_base64=obraz_base64)
    
    return '''
        <!doctype html>
        <title>Fiszki OCR</title>
        <h1>Prześlij obraz do rozpoznania tekstu</h1>
        <form method="post" enctype="multipart/form-data">
          <input type="file" name="plik">
          <input type="submit" value="Prześlij">
        </form>
    '''

if __name__ == "__main__":
    fiszki.run(debug=True)
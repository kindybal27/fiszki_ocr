from flask import Flask, request
import cv2
import easyocr
import os
import re
import nltk
from nltk.corpus import words

nltk.download("words")
angielskie = set(words.words())     #slownik angielski z zamiana z listy na zbior

#wczytywanie polskiego slownika z pliku z zamiana na zbior (set)
def wczytaj_polskie():
    sciezka_slownik = "slownik.txt"
    if os.path.exists(sciezka_slownik):
        with open(sciezka_slownik, "r", encoding = "utf-8") as plik_s:
            return set(plik_s.read().splitlines())
    return set()

polskie = wczytaj_polskie()

fiszki = Flask(__name__)        #inicjacja apliakcji
DO_ZAPISU = "uploaded"          #folder na przeslane pliki

czytnik= easyocr.Reader(['pl', 'en'], gpu=True)

def filtrowanie(tekst):             #funkcja do filtrowania tekstu
    oczyszczony_tekst = re.sub(r"[^a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s]", "", tekst)     #usuwanie znakow ktore nie sa literami ani spacjami
    slowa = oczyszczony_tekst.split()                                           #dzielenie tekstu na slowa

    slowa_filtrowane = [s for s in slowa if s.lower() in polskie or s.lower() in angielskie]        #zostawienie slow tylko z polskiego i angielskiego slownika

    slowa_filtrowane = [s for s in slowa_filtrowane if len(s) > 2]          #usuniecie slow ktore sa krótsze od 3 znakow
    return " ".join(slowa_filtrowane)

@fiszki.route("/", methods=["GET", "POST"])             #strona w flask
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
        obraz_szary = cv2.cvtColor(obraz, cv2.COLOR_BGR2GRAY)           #konwersja na c-b

        wyniki = czytnik.readtext(obraz_szary)

        rozpoznany_tekst = "\n".join([filtrowanie(wynik[1]) for wynik in wyniki])           #laczenie wynikow w tekst dzielac nowa linia
        return f"<h4>Rozpoznany tekst:</h4><pre>{rozpoznany_tekst}</pre>"
    
    return '''
        <!doctype html>
        <title>Fiszki OCR</title>
        <form method="post" enctype="multipart/form-data">
          <input type="file" name="plik">
          <input type="submit" value="Prześlij">
        </form>
    '''

if __name__ == "__main__":
    fiszki.run(debug=True)

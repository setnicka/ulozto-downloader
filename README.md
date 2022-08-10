# Ulož.to downloader

Paralelní stahovač z [Ulož.to](http://ulozto.cz) inspirovaný
[Vžum](http://vzum.8u.cz/) (credits to Popcorn) s automatickým louskáním CAPTCHA
kódů pomocí TensorFlow modelu z projektu
[ulozto-captcha-breaker](https://github.com/JanPalasek/ulozto-captcha-breaker)
(credits to Jan Palasek).

Narozdíl od originálního Vžum je tato verze napsaná v Pythonu, dá se provozovat
jednoduše i na Linuxu a zdrojový kód je veřejně dostupný, což umožňuje další
forky a rozšíření do budoucna. Například by mohla vzniknout "serverová" verze
s webovým rozhraním.

**Nápady na další vylepšení (případně rovnou pull requesty) vítány :-)**

## Klíčové vlastnosti

* Sám pozná downloady, kde Ulož.to umožňuje stahovat bez CAPTCHA kódů
* Dokáže přečíst sám CAPTCHA kódy díky projektu
  [ulozto-captcha-breaker](https://github.com/JanPalasek/ulozto-captcha-breaker) (thx Jan Palasek)
  * Louská kódy pomocí natrénovaného TensorFlow modelu
* Download linky získává přes Tor, aby se vyhnul nové limitaci ze strany Uloz.to
* Umí opakovaně využít stejný stahovací link pro více částí
  * Ulož.to nyní (podzim 2020) umožňuje získat jen dva stahovací linky za
    minutu, ale stejný link je možné používat po dostahování původní části
    opakovaně pro stahování dalších částí
* Umí navazovat přerušená stahování (pokud se zachová stejný počet částí)
* Stahuje přímo do finálního souboru, jednotlivá stahování zapisují na správné
  místo v souboru (než program ohlásí dostahováno, je soubor neúplný)
* Konzolový status panel se statistikou úspěšnosti při získávání linků
* Celkový průběh staženo / okamžitá rychlost stahování ve druhém řádku status panelu (save progress monitor)
* Cache soubor download linků pro pokračování nebo opětovné stažení, po restartu se bez nového
  získávání download linků rovnou stahuje a nové download linky se získávají jen když jich není
  v cache souboru dostatek. Vytváří malý textový soubor `.ucache` jenž je možné použít znovu
  a stahovat maximální rychlostí ihned bez získávání linků. Tento soubor má malou velikost
  a lze ho např. sdílet. U velkých souborů (100ky MB) je platnost linku 48 hodin.

## Instalace

Nejjednodušší je využít verzi uveřejněnou na [PyPi](https://pypi.org/project/ulozto-downloader/):

```shell
$ pip3 install --upgrade ulozto-downloader
```

Toto by mělo instalovat i všechny dependence (včetně TensorFlow Lite pro
automatické louskání kódů).

### Instalace TORu

Program vyžaduje spustitelný tor, protože používá stem a očekává ho v `$PATH`.

* Na Linuxu stačí:

  ```shell
  $ sudo apt install tor
  # nebo...
  $ yum install tor
  # nebo podle vašeho balíčkovacího systému
  ```

* Na Windows lze instalovat [TorBrowser](https://www.torproject.org/download/)
  a dostat `tor.exe` do `%PATH%`

### Instalace TensorFlow Lite (automatické louskání CAPTCHA)

Mělo by se instaloval automaticky přes `pip`. Pokud se to nepovede,
postupujte podle instrukcí na stránce [TensorFlow Lite](https://www.tensorflow.org/lite/guide/python),
kde si buď instalujte balík do systému a nebo si stáhněte z odkazu správný Wheel
soubor podle své verze Pythonu (zjistíte zavoláním `python3 -V`).

### Instalace Tkinter (ruční opisování CAPTCHA)

Potřebujete na systému instalovaný Tkinter (bohužel není na PyPI, takže je
potřeba instalovat ručně).

Často už je instalovaný, ale pokud by náhodou nebyl, tak bývá v balíčku
`python3-tk` (případně následujte instrukce na
[webu Tk](https://tkdocs.com/tutorial/install.html)).

## Instalace na dalších platformách

### [Android - Termux](doc/install.md)

## Použití

Od verze 3.0 je v defaultu aktivované automatické louskání CAPTCHA kódů pomocí
TensorFlow. Pokud byste ho chtěli vypnout, použijte přepínač `--no-auto-captcha`.
Pro volbu počtu částí slouží přepínač `--parts N`.

```shell
$ ulozto-downloader --parts 50 "https://ulozto.cz/file/TKvQVDFBEhtL/debian-9-6-0-amd64-netinst-iso"
```

![Ukázka stahování](https://raw.githubusercontent.com/setnicka/ulozto-downloader/master/example-screenshot.png)

Při využití automatického louskání doporučuji využít velký počet částí, klidně
50 (spustíte `ulozto-downloader` a necháte ho pracovat, on si postupně louskne
další stahovací linky a postupně navyšuje počet najednou stahovaných částí).

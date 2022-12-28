# Ulož.to downloader

## Language disclaimer (English)

This is a parallel downloader from [Ulož.to](http://ulozto.cz) with automatic
CAPTCHA solving. This README is in Czech but the program itself and its help are
in English (try to run it with `--help` option).

When contributing to this project, please use English in the code. Issues and
pull request comments could be in Czech or English, I will discuss them
according to the thread language :)

---

## Úvod

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

Ulož.to downloader je napsaný v Pythonu a je distribuovaný v podobě zdrojových
kódů, které si každý může spustit, pokud má nainstalovaný Python. Předtím než
s čímkoliv začnete, ujistěte se prosím, že máte:

* **Nainstalovaný Python 3** – externí [návod na instalaci](https://naucse.python.cz/lessons/beginners/install/)
* Umíte **instalovat Python balíky pomocí příkazu `pip` nebo `pip3` v příkazové řádce**
  – malý externí [návod na Pip](https://ksp.mff.cuni.cz/encyklopedie/python-pip.html)

Protože Ulož.to downloader závisí na několika externích projektech, bude mimo
instalace samotného ulozto-downloaderu potřeba zajistit ještě několik dalších věcí:

* **TOR** pro získávání download linků z různých IP adres a vyhnutí se limitaci
* Jeden z:
  * **TensorFlow Lite** pro automatické louskání CAPTCHA kódů
  * **Tkinter** když budete používat ruční opisování CAPTCHA kódů

### Instalace TORu

Tor je program umožňující přistupovat na cílovou stránku přes jiné počítače a tím
obejít limitaci na počet stahovacích linků z jedné IP adresy.

Ulož.to downloader vyžaduje spustitelný příkaz `tor` (vnitřně používá stem)
a očekává tento příkaz v `$PATH`.

Na Linuxu:

```shell
sudo apt install tor
  # nebo...
yum install tor
  # nebo podle vašeho balíčkovacího systému
```

Na Windows lze instalovat [TorBrowser](https://www.torproject.org/download/)
a dostat `tor.exe` do `%PATH%`, tedy přidat do systémové proměnné `%PATH`
složku s `tor.exe` z instalace TorBrowseru (typicky `C:\Program Files\Tor Browser\Browser\TorBrowser\Tor`).

* Náhodný externí [návod na přidání do `%PATH%`](https://cz.moyens.net/windows/co-je-windows-path-a-jak-jej-pridavate-a-upravujete/).

### Instalace TensorFlow Lite (automatické louskání CAPTCHA)

TensorFlow Lite je balíček, který umožní spouštět na CAPTCHA obrázcích
natrénovanou neuronovou síť a tím je automaticky louskat.

Dá se použít buď odlehčený Python balíček `tflite-runtime`, nebo plnotučný
Python balíčku `tensorflow` (vydávání `tflite-runtime` se často opožďuje, proto
je často potřeba s novým Pythonem sáhnout po plnotučné verzi).

Oba balíky se dají instalovat přes Python instalátor `pip3`. Odlehčený
`tflite-runtime` se dá instalovat i společně s celým Ulož.to downloaderem, když
použijete při instalaci `ulozto-downloader[auto-captcha]`, nebo ručně
následujícím příkazem:

```shell
pip3 install tflite-runtime
```

**Verzi pro Windows** (nebo pokud vám instalace hází chybu) stáhněte z repozitáře
[pycoral](https://github.com/google-coral/pycoral/releases)

Pokud vám tato metoda nefunguje (instalace vypisuje "Could not find a version
that satisfies the requirement"), je potřeba instalovat plnotučný `tensorflow`
(pozor, zabere po instalaci asi 1GB):

```shell
pip3 install tensorflow
```

Pokud vám žádná z metod výše nefunguje, postupujte podle instrukcí na stránce
[TensorFlow Lite](https://www.tensorflow.org/lite/guide/python), kde si buď
instalujte balík do systému a nebo si stáhněte z odkazu správný Wheel soubor
podle své verze Pythonu (zjistíte zavoláním `python3 -V`).

### Instalace Tkinter (ruční opisování CAPTCHA)

Pokud se vám nepovede rozchodit TensorFlow Lite pro automatické louskání (nebo
chcete poměřit síly s natrénovaným modelem a louskat ručně), potřebujete na
systému instalovaný Tkinter na zobrazení okénka s obrázkem.

Bohužel není na PyPI, takže je potřeba instalovat ručně. Často už je instalovaný,
ale pokud by náhodou nebyl, tak bývá v balíčku `python3-tk` (případně následujte
instrukce na [webu Tk](https://tkdocs.com/tutorial/install.html)).

### Instalace Ulož.to downloaderu

Teď už byste měli mít vše připraveno. Stačí jen instalovat samotný Ulož.to
downloader.

Nejjednodušší je využít verzi uveřejněnou na [PyPI](https://pypi.org/project/ulozto-downloader/).
Pokud máte platformu, pro který existuje na PyPI validní balíček
[`tflite-runtime`](https://pypi.org/project/tflite-runtime/), můžete rovnou
instalovat speciální target s `[auto-captcha]` a ulehčit si tak instalaci
TensorFlow Lite.

```shell
pip3 install --upgrade ulozto-downloader
pip3 install --upgrade ulozto-downloader[auto-captcha]  # <-- doporučeno
```

## Instalace na dalších platformách

* [Android - Termux](doc/install.md#android---termux)
* [MacOS](doc/install.md#macos)

## Použití

Při zavolání s `-h` nebo `--help` vypíše Ulož.to downloader popis všech svých
přepínačů a nastavítek. Zde jsou vyjmenována základní nastavení, ale výčet není
rozhodně kompletní.

Od verze 3.1 je v defaultu aktivovaná autodetekce TensorFlow a pokud je instalované,
tak se použije pro automatické louskání louskání CAPTCHA kódů, jinak se vypisuje
ruční opisování. Pro vynucení chování můžete použít přepínače:

* `--auto-captcha` vynutí použití TensorFlow Lite
* `--manual-captcha` vynutí použití manuálního opisování

Pokud není dostupný žádný solver, lze stahovat jen soubory bez CAPTCHA.

Pro volbu počtu částí slouží přepínač `--parts N`, default je 20 částí. Ve
výchozím nastavení Ulož.to downloader zobrazuje pouze sumární stav. Pokud chcete
zobrazit stav stahování jednotlivých částí, použijte přepínač
`--parts-progress`.

```shell
ulozto-downloader --parts 30 --parts-progress "https://ulozto.cz/file/TKvQVDFBEhtL/debian-9-6-0-amd64-netinst-iso"
```

Lze specifikovat i **více URL ke stažení**, v takovém případě probíhá stahování
sekvenčně (po dostahování prvního se začne stahovat druhý atd.):

```shell
ulozto-downloader --parts 30 "https://ulozto.cz/file/TKvQVDFBEhtL/debian-9-6-0-amd64-netinst-iso" "https://ulozto.cz/file/YPivhc3Jyn9r/debian-live-11-1-0-amd64-mate-iso"
```

Pokud chcete ukládat log do souboru, použijte přepínač `--log <název souboru>`
(v defaultním nastavení se log neukládá).

![Ukázka stahování](https://raw.githubusercontent.com/setnicka/ulozto-downloader/master/example-screenshot.png)

Při využití automatického louskání doporučuji využít velký počet částí, klidně
50 (spustíte `ulozto-downloader` a necháte ho pracovat, on si postupně louskne
další stahovací linky a postupně navyšuje počet najednou stahovaných částí).

## Další návody a dokumentace

* [Vytvoření Windows EXE](doc/win_exe.md)

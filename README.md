# Ulož.to downloader

Paralelní stahovač z [Ulož.to](http://ulozto.cz) inspirovaný [Vžum](http://vzum.8u.cz/) (credits to Popcorn).

Narozdíl od originálního Vžum je tato verze napsaná v Pythonu, dá se provozovat jednoduše i na Linuxu a zdrojový kód je veřejně dostupný, což umožňuje další forky a rozšíření do budoucna. Například by mohla vzniknout "serverová" verze s webovým rozhraním.

**Nápady na další vylepšení (případně rovnou pull requesty) vítány :-)**

#### Disclaimer

Také existuje [jiná velmi podobná Pythoní verze](https://github.com/yaqwsx/utility/blob/master/vzum/vzum) vyvinutá Honzou Mrázkem. Dozvěděl jsem se o ní samozřejmě až po dopsání mojí verze při pátrání, kam bych mohl svoji verzi zveřejnit (vtipné je to, že na některé věci jsme zvolili velmi podobné postupy aneb konvergentní evoluce není kec :-D).

## Klíčové vlastnosti

* Sám pozná downloady, kde Ulož.to umožňuje stahovat bez CAPTCHA kódů
* Umí navazovat přerušená stahování (pokud se zachová stejný počet částí)
* Dokáže přečíst sám captcha kódy díky [tomuto projektu](https://github.com/JanPalasek/ulozto-captcha-breaker)
* Konzolový status panel

## Instalace

Nejjednodušší je využít verzi uveřejněnou na [PyPi](https://pypi.org/project/ulozto-downloader/):

```shell
pip3 install ulozto-downloader
```

## Použití

```shell
ulozto-downloader --parts 15 "https://ulozto.cz/file/TKvQVDFBEhtL/debian-9-6-0-amd64-netinst-iso"
```

Pro volbu manuálního či automatického čtení captcha kódů slouží přepínač *captcha* s hodnotami "m" či "a" (manuální je default).
Abychom nemuseli captcha kódy sami luštit, můžeme tedy zavolat například

```shell
ulozto-downloader --parts 15 "https://ulozto.cz/file/TKvQVDFBEhtL/debian-9-6-0-amd64-netinst-iso" --captcha "a"
```

## Requirements

* Python 3
* Pro automatické stahování vhodnou verzi [TensorflowLite Runtimu](https://www.tensorflow.org/lite/guide/python)
* Nějaké knihovny pro Python 3:
  * Tkinter (balík `python3-tk` na Debianu)
  * Pillow s ImageTK (balík `python3-pil.imagetk` na Debianu)

# Ulož.to downloader
Paralelní stahovač z [Ulož.to](http://ulozto.cz) inspirovaný [Vžum](http://vzum.8u.cz/) (credits to Popcorn).

Narozdíl od originálního Vžum je tato verze napsaná v Pythonu, dá se provozovat jednoduše i na Linuxu a zdrojový kód je veřejně dostupný, což umožňuje další forky a rozšíření do budoucna. Například by mohla vzniknout "serverová" verze s webovým rozhraním.

**Nápady na další vylepšení (případně rovnou pull requesty) vítány :-)**

#### Disclaimer

Také existuje [jiná velmi podobná Pythoní verze](https://github.com/yaqwsx/utility/blob/master/vzum/vzum) vyvinutá Honzou Mrázkem. Dozvěděl jsem se o ní samozřejmě až po dopsání mojí verze při pátrání, kam bych mohl svoji verzi zveřejnit (vtipné je to, že na některé věci jsme zvolili velmi podobné postupy aneb konvergentní evoluce není kec :-D).

## Klíčové vlastnosti
* Nevyžaduje opisování CAPTCHA kódů
* Umí navazovat přerušená stahování (pokud se zachová stejný počet částí)
* Konzolový status panel

## Použití
```
./ulozto_downloader.py --parts 15 'https://ulozto.cz/!TKvQVDFBEhtL/debian-9-6-0-amd64-netinst-iso'
```
* URL zadávejte v jednoduchých uvozovkách, protože obsahují nehezký znak `!`

## Requirements
* Python 3

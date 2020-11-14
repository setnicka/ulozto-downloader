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
* Umí opakovaně využít stejný stahovací link pro více částí
  * Ulož.to nyní (podzim 2020) umožňuje získat jen dva stahovací linky za
    minutu, ale stejný link je možné používat po dostahování původní části
    opakovaně pro stahování dalších částí
* Umí navazovat přerušená stahování (pokud se zachová stejný počet částí)
* Konzolový status panel

## Instalace

Nejjednodušší je využít verzi uveřejněnou na [PyPi](https://pypi.org/project/ulozto-downloader/):

```shell
pip3 install --upgrade ulozto-downloader
```

Toto zároveň instaluje i všechny potřebné dependence (včetně TensorFlow Lite
pro louskání CAPTCHA kódů).

## Použití
Pro volbu automatického čtení CAPTCHA kódů slouží přepínač `--auto-captcha`,
pro volbu počtu částí slouží přepínač `--parts N`.

```shell
ulozto-downloader --auto-captcha --parts 15 "https://ulozto.cz/file/TKvQVDFBEhtL/debian-9-6-0-amd64-netinst-iso"
```

Při využití automatického louskání doporučuji využít velký počet částí, klidně
50 (spustíte `ulozto-downloader` a necháte ho pracovat, on si jednou za minutu
louskne další dva stahovací linky a postupně navyšuje počet najednou stahovaných
částí).

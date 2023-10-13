## Android - Termux

1.) Stáhněte si aplikaci [Termux](https://termux.com/) (Ne z Google Play!)
2.) Povolte aplikaci přístup k uložišti pomocí:
```shell
termux-setup-storage
```
3.) Aktualizujte balíčky:
```shell
pkg upgrade
```
### Instalujte Flaresolverr
1.) ```
pkg install proot-distro
```
2.) ```
proot-distro install ubuntu
```
3.) ```
proot-distro login ubuntu
```
4.) ```
apt install skopeo umoci
```
5.) ```
cd /data/data/com.termux/files/home
skopeo copy docker://ghcr.io/flaresolverr/flaresolverr:v3.3.6 oci:flaresolverr:v3.3.6
umoci unpack --image flaresolverr:v3.3.6 rootfs
```
(Toto bude nèjakou dobu trvat)

4.) Nainstalujte Python:
```shell
pkg install python3
```
5.) Nainstalujte Numpy:
```shell
MATHLIB="m" pip install numpy
```
6.) Nainstalujte libjpeg-turbo:
```shell
pkg install libjpeg-turbo
```
7.) Nainstalujte Tor:
```shell
pkg install tor
```
8.) Nainstalujte Tkinter:
```shell
pkg install python-tkinter
```
9.) Nainstalujte Git:
```shell
pkg install git
```
10.) Nainstalujte opravenou verzi Ulozto-downloaderu:
```shell
pip install ulozto-downloader
```
11.) Nainstalujte grafické rozhraní, ve kterém budete opisovat captcha kódy, podle návodu [zde](https://wiki.termux.com/wiki/Graphical_Environment).

## MacOS

### Tor install
Installing tor package from brew provides all needed for Tor usage.
```shell
brew install tor
```

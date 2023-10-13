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
1.) 
```
pkg install proot-distro
```
2.)
```
proot-distro install ubuntu
```
3.)
```
proot-distro login ubuntu
```
4.)
```
apt install skopeo umoci
```
5.)
```
cd /data/data/com.termux/files/home
skopeo copy docker://ghcr.io/flaresolverr/flaresolverr:v3.3.6 oci:flaresolverr:v3.3.6
umoci unpack --image flaresolverr:v3.3.6 rootfs
```
(Toto bude nějakou dobu trvat)

6.) Přesuňte soubor [Flaresolverr.sh](https://github.com/Vojtak42/ulozto-downloader/blob/master/Termux/Flaresolverr.sh) do složky rootfs v uložišti termuxu (třeba pomocí správce souborů jako Total commander)

7.) 
```
cd rootfs
chmod +rwx flaresolverr.sh
./flaresolverr.sh
```
8.)
```
su flaresolverr
echo 127.0.0.1 localhost > /etc/hosts
python -u /app/flaresolverr.py
```
### Ulozto-downloader
1.) Otevřete novou "Session" potažením prstem z levé strany obrazovky a stisknutím "New session".

2.) Nainstalujte Python:
```shell
pkg install python3
```
3.) Nainstalujte Numpy:
```shell
pkg install python-numpy
```
4.) Nainstalujte libjpeg-turbo:
```shell
pkg install libjpeg-turbo
```
5.) Nainstalujte Tor:
```shell
pkg install tor
```
6.) Nainstalujte Tkinter:
```shell
pkg install python-tkinter
```
7.) Nainstalujte Ulozto-downloader:
```shell
pip install ulozto-downloader
```
8.) Nainstalujte grafické rozhraní, ve kterém budete opisovat captcha kódy, podle návodu [zde](https://wiki.termux.com/wiki/Graphical_Environment).

### Použití
Před každým spuštěním ulozto-downloaderu
budete muset zopakovat kroky 7 a 8 (kromě příkazu chmod).

## MacOS

### Tor install
Installing tor package from brew provides all needed for Tor usage.
```shell
brew install tor
```

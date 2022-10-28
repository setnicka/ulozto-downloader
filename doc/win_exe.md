# Návod na vyrobení EXE souboru na Windows

Autor: `1ucay` – <https://github.com/setnicka/ulozto-downloader/issues/101#issuecomment-1254279619>

*(netestováno)*

Udělal jsem si EXE helper pro ty, co nemají rádi konzoli. Zabere Vám to minutu :)

1. Stáhněte si PowerShell builder <https://github.com/MScholtes/Win-PS2EXE>
2. Vytvořte soubor `ulozto.ps1` v UTF-8

    ```ps1
    function isURI($address) {
    ($address -as [System.URI]).AbsoluteURI -ne $null
    }

    function isURIWeb($address) {
    $uri = $address -as [System.URI]
    $uri.AbsoluteURI -ne $null -and $uri.Scheme -match '[http|https]'
    }

    if( ( $(Get-Clipboard) -like '//uloz.to/file' ) -and ( isURI( $(Get-Clipboard) ) ) ) {

    (Get-Clipboard)
    } else {
    $defaultURL = "https://uloz.to/file/YPivhc3Jyn9r/debian-live-11-1-0-amd64-mate-iso#!ZGyxLwR2AzDmZmIzLGH4AGxmAzIvMKV5oayypHZkHayUZGZ1LD=="
    }

    Add-Type -AssemblyName Microsoft.VisualBasic
    $URL = [Microsoft.VisualBasic.Interaction]::InputBox('Zadejte URL souboru', 'Uloz.to', $defaultURL)
    $PARTS = [Microsoft.VisualBasic.Interaction]::InputBox('Počet částí', 'Uloz.to', "50")
    Start-Process -FilePath "ulozto-downloader" -ArgumentList ('--parts ' + $PARTS + ' "' + $URL + '"')
    ```

3. Stáhněte si <https://uloz.to/favicon.ico>
4. Spusťte Win-PS2EXE.exe, nastavte ulozto.ps1 a favicon.ico a dejte Compile :)

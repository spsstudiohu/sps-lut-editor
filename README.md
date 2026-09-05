# SPS LUT Editor

Biztonságos, helyi XMP preset-szerkesztő Adobe Lightroomhoz és Camera Raw-hoz.

A változások teljes listája: [CHANGELOG.md](<D:\SPS LUT EDITOR\CHANGELOG.md>).

Projektirányelvek: [közreműködés](CONTRIBUTING.md), [magatartási kódex](CODE_OF_CONDUCT.md), [biztonsági szabályzat](SECURITY.md) és [licenc](LICENSE).

GitHubon a `.github/workflows/python-package.yml` Windows futtatón ellenőrzi a teszteket és hordozható alkalmazáscsomagot készít letölthető build-artifactként.

## Windows gyorsindítás

Kattints duplán a [Start SPS LUT Editor.cmd](<D:\SPS LUT EDITOR\Start SPS LUT Editor.cmd>) fájlra. Első használatkor automatikusan létrehozza a helyi Python-környezetet és telepíti a PySide6 csomagot; ehhez internetkapcsolat szükséges. Az indító a Windows konzolt UTF-8 kódolásra állítja, ezért a telepítés magyar üzenetei és fájlnevei is helyesen jelennek meg.

Az első telepítés után az indító konzolablak nélkül nyitja meg az alkalmazást. Az editor alsó állapotsora jelzi a fontos műveleteket, például a megnyitott fájlt, a módosított mezőt és a mentés állapotát.

## Kézi indítás

Python 3.10+ szükséges.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r source\requirements.txt
python source\main.py
```

## Projektstruktúra

- `source/` – szerkeszthető Python-forrás, tesztek, képi assetek és függőségek
- `Start SPS LUT Editor.cmd` – Windows gyorsindító a forráskódos futtatáshoz
- `installer/` – NSIS telepítőszkript a forráskódos, beépített Python-környezetes telepítéshez

## MVP funkciók

- XMP megnyitás, fájladatok, előnézet és raw XML keresés
- Preset név, csoport és UUID szerkesztése/UUID-generálás
- Basic Tone paraméterek csúszkával és pontos numerikus mezővel
- HSL, Detail és Effects paraméterek, valamint támogatottatlan `crs:*` mezők
- Csak a megváltoztatott XML-attribútumok íródnak át; az ismeretlen namespace-ek és mezők megmaradnak
- Biztonságos **Save As**, XML-ellenőrzés, Undo/Redo és eredeti értékek visszaállítása
- Két preset összehasonlítása és egyedi értékek másolása
- UTF-8 mentés teljes magyar ékezetes karaktertámogatással
- SPS logó a megadott fekete és fehér PNG assetekkel, automatikus világos/sötét témaválasztással
- RAW profil kijelzés csak olvasható módban; a Camera Profile és Digest nem módosítható a normál szerkesztőből
- Embedded Look létrehozása Look nélküli presetekhez biztonságos `Amount=0` alapértékkel
- „Mentés SPS_ előtaggal” művelet: ugyanabban a mappában ment `SPS_eredeti-név.xmp` fájlt, és csak ezt a munkapéldányt írja felül megerősítés után

Az eredeti fájl felülírása nem alapértelmezett: a mentés mindig új fájlt kér.

# Közreműködés az SPS LUT Editorhoz

Köszönjük a közreműködést! Mielőtt változtatást küldenél, kérjük, kövesd az alábbi irányelveket.

## Fejlesztői környezet

Python 3.10 vagy újabb szükséges.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r source\requirements.txt
python -m unittest discover -s source\tests -v
```

## Változtatások küldése

1. Nyiss issue-t nagyobb funkció vagy lényeges viselkedésváltozás előtt.
2. Készíts külön ágat a módosításhoz.
3. A változtatás legyen kicsi, célzott és visszafejthető.
4. Őrizd meg az XMP-ben található ismeretlen mezőket és namespace-eket.
5. Futtasd a teszteket, és írd le, mit ellenőriztél.
6. Frissítsd a `CHANGELOG.md` fájlt minden felhasználót érintő módosításnál.

## XMP-kompatibilitás

Az editor alapelve, hogy kizárólag a felhasználó által módosított metaadatokat és beállításokat írja át. Ne vezess be olyan mentési logikát, amely egyéb presetértékeket, színprofilt vagy ismeretlen XML-adatot automatikusan átalakít.

## Hibajelentések és biztonság

Általános hibákhoz használd a GitHub issue-sablont. Biztonsági sérülékenységet ne nyilvános issue-ban jelents; lásd a [SECURITY.md](SECURITY.md) dokumentumot.

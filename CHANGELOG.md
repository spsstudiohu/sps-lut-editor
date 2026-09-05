# Changelog

Minden érdemi változás ebben a fájlban követhető.

## 2026-09-05

### [New]

- Kötegelt, biztonságos metaadat-szerkesztés és `SPS_` kiadási másolatkészítés.
- Mentés előtti változáslista, XMP-diagnosztika és választható `.bak` biztonsági mentés.
- Metaadat-sablonok JSON import/exportja, CSV/JSON presetjelentés és kötegelt átnevezési másolat.
- GitHub Releases-alapú, kézi jóváhagyást és SHA-256 ellenőrzést használó frissítéskereső.
- Címkével indítható GitHub Actions kiadási folyamat Windows telepítővel és ellenőrzőösszeggel.

### [Updated]

- NSIS telepítő verziója 0.2.0-ra frissítve az új szerkesztőfunkciókkal.

## 2026-09-04

### [New]

- SPS LUT Editor PySide6 asztali alkalmazás XMP presetek megnyitásához és szerkesztéséhez.
- Preset-információk: név, csoport, UUID, Creator Tool, Process Version és jogkezelési metaadatok.
- Basic Tone, HSL/Color Mixer, Detail, Effects és Tone Curve PV2012 szerkesztőpanelek.
- Advanced Raw XML nézet, XML-ellenőrzés, Undo/Redo és eredeti értékek visszaállítása.
- Ismeretlen `crs:*` paraméterek megjelenítése és megőrzése.
- Presetek összehasonlítása, eltérő értékek másolásával.
- Embedded Look és régebbi embedded `crs:Preset` metaadatok felismerése és szerkesztése.
- Embedded Look létrehozása `Amount=0` alapértékkel és `SPS Studio Hungary` csoporttal.
- Csak olvasható RAW-profil kijelzés a Camera Profile és Digest értékekhez.
- UTF-8 XMP mentés magyar ékezetes karaktertámogatással.
- `SPS_` előtagos biztonságos mentési lehetőség.
- SPS világos/sötét logómegjelenítés és Windows gyorsindító.
- NSIS forráskódos telepítőszkript, beépített Python/PySide környezettel és asztali ikonnal.
- GitHub Actions Windows workflow Python 3.13 teszteléssel és hordozható build-artifact készítésével.
- GitHub közösségi dokumentumok: magatartási kódex, közreműködési útmutató, MIT licenc, biztonsági szabályzat és hibajegy-sablon.

### [Fixed]

- GitHub Actions workflow automatikusan felderíti a repositoryban lévő `requirements.txt` fájl helyét.
- RDF `rdf:Alt` listában tárolt Name, Group, Sort Name és Rights mezők kezelése.
- Többféle Adobe XMP beágyazási forma (`crs:Look`, `crs:Preset`) feldolgozása.
- Windows gyorsindító UTF-8- és CRLF-kompatibilitása.

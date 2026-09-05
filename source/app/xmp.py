from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import uuid
from xml.etree import ElementTree as ET

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
CRS = "http://ns.adobe.com/camera-raw-settings/1.0/"
XMP = "http://ns.adobe.com/xap/1.0/"
DC = "http://purl.org/dc/elements/1.1/"

for prefix, uri in (("rdf", RDF), ("crs", CRS), ("xmp", XMP), ("dc", DC)):
    ET.register_namespace(prefix, uri)


class XmpError(ValueError):
    pass


@dataclass
class XmpDocument:
    path: Path | None
    root: ET.Element
    encoding: str = "utf-8"

    @classmethod
    def open(cls, path: str | Path) -> "XmpDocument":
        file_path = Path(path)
        try:
            raw = file_path.read_bytes()
            encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
            root = ET.fromstring(raw)
        except (OSError, ET.ParseError, UnicodeDecodeError) as exc:
            raise XmpError(f"A fájl nem olvasható érvényes XML/XMP-ként: {exc}") from exc
        document = cls(file_path, root, encoding)
        if document.description is None:
            raise XmpError("A fájlban nem található RDF Description elem; ez nem támogatott Adobe XMP.")
        return document

    @property
    def description(self) -> ET.Element | None:
        return self.root.find(f".//{{{RDF}}}Description")

    def value(self, name: str) -> str:
        element = self.description
        if element is None:
            return ""
        return element.get(f"{{{CRS}}}{name}", "")

    def set_value(self, name: str, value: str) -> None:
        if self.description is None:
            raise XmpError("Hiányzik az RDF Description elem.")
        self.description.set(f"{{{CRS}}}{name}", value)

    def set_attribute(self, namespace: str, name: str, value: str) -> None:
        if self.description is None:
            raise XmpError("Hiányzik az RDF Description elem.")
        self.description.set(f"{{{namespace}}}{name}", value)

    def remove_value(self, name: str) -> None:
        if self.description is not None:
            self.description.attrib.pop(f"{{{CRS}}}{name}", None)

    def metadata(self) -> dict[str, str]:
        d = self.description
        if d is None:
            return {}
        return {
            "Preset Name": self.localized_value("Name"),
            "Group": self.localized_value("Group"),
            "UUID": d.get(f"{{{CRS}}}UUID", ""),
            "Creator Tool": d.get(f"{{{XMP}}}CreatorTool", ""),
            "Process Version": d.get(f"{{{CRS}}}ProcessVersion", ""),
            "Copyright / Rights": self.rights_value(),
        }

    def localized_value(self, name: str) -> str:
        """Read a crs property stored either as an attribute or rdf:Alt list."""
        d = self.description
        if d is None:
            return ""
        element = d.find(f"{{{CRS}}}{name}")
        if element is not None:
            item = element.find(f".//{{{RDF}}}li")
            if item is not None and item.text:
                return item.text
            return element.text or ""
        return d.get(f"{{{CRS}}}{name}", "")

    def set_localized_value(self, name: str, value: str) -> None:
        """Update Name/Group without changing an existing XMP representation."""
        d = self.description
        if d is None:
            raise XmpError("Hiányzik az RDF Description elem.")
        element = d.find(f"{{{CRS}}}{name}")
        if element is not None:
            item = element.find(f".//{{{RDF}}}li")
            if item is None:
                alt = ET.SubElement(element, f"{{{RDF}}}Alt")
                item = ET.SubElement(alt, f"{{{RDF}}}li")
                item.set("{http://www.w3.org/XML/1998/namespace}lang", "x-default")
            item.text = value
            return
        if f"{{{CRS}}}{name}" in d.attrib:
            d.set(f"{{{CRS}}}{name}", value)
            return
        element = ET.SubElement(d, f"{{{CRS}}}{name}")
        alt = ET.SubElement(element, f"{{{RDF}}}Alt")
        item = ET.SubElement(alt, f"{{{RDF}}}li")
        item.set("{http://www.w3.org/XML/1998/namespace}lang", "x-default")
        item.text = value

    def rdf_list_values(self, name: str) -> list[str]:
        d = self.description
        if d is None:
            return []
        element = d.find(f"{{{CRS}}}{name}")
        if element is None:
            return []
        return [item.text or "" for item in element.findall(f".//{{{RDF}}}li")]

    def set_rdf_list_values(self, name: str, values: list[str]) -> None:
        d = self.description
        if d is None:
            raise XmpError("Hiányzik az RDF Description elem.")
        element = d.find(f"{{{CRS}}}{name}")
        if element is None:
            element = ET.SubElement(d, f"{{{CRS}}}{name}")
            container = ET.SubElement(element, f"{{{RDF}}}Seq")
        else:
            container = element.find(f"{{{RDF}}}Seq") or element.find(f"{{{RDF}}}Bag")
            if container is None:
                container = ET.SubElement(element, f"{{{RDF}}}Seq")
            for item in list(container.findall(f"{{{RDF}}}li")):
                container.remove(item)
        for value in values:
            item = ET.SubElement(container, f"{{{RDF}}}li")
            item.text = value

    @property
    def look_description(self) -> ET.Element | None:
        # A Look is not consistently placed below the first RDF Description.
        # Search the full XMP tree: Lightroom exports may place it in another
        # description block or wrap it in an extra RDF resource element.
        look = self.root.find(f".//{{{CRS}}}Look//{{{RDF}}}Description")
        if look is not None:
            return look
        # Older Lightroom exports store the same metadata in crs:Preset,
        # rather than the newer crs:Look container.
        return self.root.find(f".//{{{CRS}}}Preset/{{{RDF}}}Description")

    @property
    def embedded_metadata_kind(self) -> str:
        if self.root.find(f".//{{{CRS}}}Look//{{{RDF}}}Description") is not None:
            return "Look / Camera Raw profil"
        if self.root.find(f".//{{{CRS}}}Preset/{{{RDF}}}Description") is not None:
            return "beágyazott Lightroom preset"
        return ""

    def look_value(self, name: str, localized: bool = False) -> str:
        look = self.look_description
        if look is None:
            return ""
        if localized:
            element = look.find(f"{{{CRS}}}{name}")
            item = element.find(f".//{{{RDF}}}li") if element is not None else None
            return (item.text or "") if item is not None else (element.text or "" if element is not None else "")
        return look.get(f"{{{CRS}}}{name}", "")

    def set_look_value(self, name: str, value: str, localized: bool = False) -> None:
        look = self.look_description
        if look is None:
            raise XmpError("A preset nem tartalmaz beágyazott crs:Look leírást.")
        if localized:
            element = look.find(f"{{{CRS}}}{name}")
            if element is None:
                element = ET.SubElement(look, f"{{{CRS}}}{name}")
            item = element.find(f".//{{{RDF}}}li")
            if item is None:
                alt = ET.SubElement(element, f"{{{RDF}}}Alt")
                item = ET.SubElement(alt, f"{{{RDF}}}li")
                item.set("{http://www.w3.org/XML/1998/namespace}lang", "x-default")
            item.text = value
        else:
            look.set(f"{{{CRS}}}{name}", value)

    def create_embedded_look(self, name: str, group: str = "SPS Studio Hungary") -> None:
        """Create a new metadata-only Look without affecting preset rendering."""
        if self.look_description is not None:
            raise XmpError("A preset már tartalmaz beágyazott Look vagy preset leírást.")
        d = self.description
        if d is None:
            raise XmpError("Hiányzik az RDF Description elem.")
        look = ET.SubElement(d, f"{{{CRS}}}Look")
        description = ET.SubElement(look, f"{{{RDF}}}Description")
        description.set(f"{{{CRS}}}Name", name)
        # Amount=0 makes the reference informational until the user deliberately
        # changes it in Adobe Camera Raw / Lightroom.
        description.set(f"{{{CRS}}}Amount", "0")
        description.set(f"{{{CRS}}}UUID", uuid.uuid4().hex.upper())
        description.set(f"{{{CRS}}}Stubbed", "true")
        if group:
            element = ET.SubElement(description, f"{{{CRS}}}Group")
            alt = ET.SubElement(element, f"{{{RDF}}}Alt")
            item = ET.SubElement(alt, f"{{{RDF}}}li")
            item.set("{http://www.w3.org/XML/1998/namespace}lang", "x-default")
            item.text = group

    def rights_value(self) -> str:
        """Return dc:rights from either the common RDF form or a legacy attribute."""
        d = self.description
        if d is None:
            return ""
        rights = d.find(f"{{{DC}}}rights")
        if rights is not None:
            text = rights.find(f".//{{{RDF}}}li")
            if text is not None and text.text:
                return text.text
            return rights.text or ""
        return d.get(f"{{{DC}}}rights", "")

    def set_rights(self, value: str) -> None:
        """Update only the copyright text while retaining the existing RDF container."""
        d = self.description
        if d is None:
            raise XmpError("Hiányzik az RDF Description elem.")
        rights = d.find(f"{{{DC}}}rights")
        if rights is not None:
            item = rights.find(f".//{{{RDF}}}li")
            if item is None:
                alt = ET.SubElement(rights, f"{{{RDF}}}Alt")
                item = ET.SubElement(alt, f"{{{RDF}}}li")
                item.set("{http://www.w3.org/XML/1998/namespace}lang", "x-default")
            item.text = value
            return
        # Some minimal/legacy files use the property as an attribute. Preserve that form.
        if f"{{{DC}}}rights" in d.attrib:
            d.set(f"{{{DC}}}rights", value)
            return
        rights = ET.SubElement(d, f"{{{DC}}}rights")
        alt = ET.SubElement(rights, f"{{{RDF}}}Alt")
        item = ET.SubElement(alt, f"{{{RDF}}}li")
        item.set("{http://www.w3.org/XML/1998/namespace}lang", "x-default")
        item.text = value

    def crs_values(self) -> dict[str, str]:
        d = self.description
        if d is None:
            return {}
        return {key.split("}", 1)[1]: value for key, value in d.attrib.items() if key.startswith(f"{{{CRS}}}")}

    def to_bytes(self) -> bytes:
        # Adobe XMP files are XML; make the output encoding explicit so accented
        # preset names, groups and copyright notices remain readable everywhere.
        return ET.tostring(self.root, encoding="utf-8", xml_declaration=True, short_empty_elements=True)

    def raw_xml(self) -> str:
        return self.to_bytes().decode("utf-8")

    def save_as(self, target: str | Path) -> None:
        data = self.to_bytes()
        try:
            ET.fromstring(data)
        except ET.ParseError as exc:
            raise XmpError(f"A módosított XML nem érvényes, ezért a mentés megszakadt: {exc}") from exc
        try:
            Path(target).write_bytes(data)
        except OSError as exc:
            raise XmpError(f"A fájl nem menthető: {exc}") from exc

    def replace_from_raw(self, raw: str) -> None:
        try:
            root = ET.fromstring(raw.encode("utf-8"))
        except ET.ParseError as exc:
            raise XmpError(f"Érvénytelen XML: {exc}") from exc
        if root.find(f".//{{{RDF}}}Description") is None:
            raise XmpError("Az XML nem tartalmaz RDF Description elemet.")
        self.root = root

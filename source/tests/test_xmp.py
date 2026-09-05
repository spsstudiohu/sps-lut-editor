# -*- coding: utf-8 -*-
import tempfile
import unittest
from pathlib import Path

from app.xmp import XmpDocument

SAMPLE = b'''<?xml version="1.0"?><x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"><rdf:RDF><rdf:Description crs:Name="Airy" crs:Exposure2012="0.00" crs:FutureSetting="Keep me"/></rdf:RDF></x:xmpmeta>'''

class XmpDocumentTests(unittest.TestCase):
    def test_only_targeted_values_change_and_unknown_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.xmp"; target = Path(directory) / "result.xmp"; source.write_bytes(SAMPLE)
            doc = XmpDocument.open(source); doc.set_value("Exposure2012", "0.35"); doc.save_as(target)
            saved = XmpDocument.open(target)
            self.assertEqual(saved.value("Exposure2012"), "0.35")
            self.assertEqual(saved.value("FutureSetting"), "Keep me")

    def test_invalid_raw_xml_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"source.xmp"; source.write_bytes(SAMPLE); doc=XmpDocument.open(source)
            with self.assertRaises(Exception): doc.replace_from_raw("<broken>")

    def test_rights_rdf_value_can_be_edited(self):
        sample = SAMPLE.replace(b"/></rdf:RDF>", b"><dc:rights xmlns:dc=\"http://purl.org/dc/elements/1.1/\"><rdf:Alt><rdf:li xml:lang=\"x-default\">Original rights</rdf:li></rdf:Alt></dc:rights></rdf:Description></rdf:RDF>")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.xmp"; source.write_bytes(sample)
            doc = XmpDocument.open(source)
            self.assertEqual(doc.rights_value(), "Original rights")
            doc.set_rights("Copyright SPS Studio 2026")
            self.assertEqual(doc.rights_value(), "Copyright SPS Studio 2026")

    def test_hungarian_text_is_written_as_utf8_and_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.xmp"; target = Path(directory) / "magyar.xmp"; source.write_bytes(SAMPLE)
            doc = XmpDocument.open(source)
            doc.set_value("Name", "Tavaszi fény – őrzött változat")
            doc.set_rights("Szerzői jog: SPS Stúdió – minden jog fenntartva")
            doc.save_as(target)
            saved_bytes = target.read_bytes()
            self.assertTrue(saved_bytes.startswith(b"<?xml version='1.0' encoding='utf-8'"))
            self.assertIn("Tavaszi fény".encode("utf-8"), saved_bytes)
            self.assertEqual(XmpDocument.open(target).metadata()["Preset Name"], "Tavaszi fény – őrzött változat")
            self.assertEqual(XmpDocument.open(target).rights_value(), "Szerzői jog: SPS Stúdió – minden jog fenntartva")

    def test_rdf_alt_name_and_group_are_read_and_updated(self):
        sample = SAMPLE.replace(b"/>", b"><crs:Name><rdf:Alt><rdf:li xml:lang=\"x-default\">Airy Real Estate</rdf:li></rdf:Alt></crs:Name><crs:Group><rdf:Alt><rdf:li xml:lang=\"x-default\">JNCK Media</rdf:li></rdf:Alt></crs:Group></rdf:Description>", 1)
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"source.xmp"; source.write_bytes(sample); doc=XmpDocument.open(source)
            self.assertEqual(doc.metadata()["Preset Name"], "Airy Real Estate")
            self.assertEqual(doc.metadata()["Group"], "JNCK Media")
            doc.set_localized_value("Group", "SPS Studio")
            self.assertEqual(doc.localized_value("Group"), "SPS Studio")

    def test_editing_group_preserves_existing_curve_and_tone_values(self):
        sample = b'''<?xml version="1.0" encoding="utf-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"><rdf:RDF><rdf:Description crs:Exposure2012="0.35" crs:FutureSetting="must stay"><crs:Group><rdf:Alt><rdf:li xml:lang="x-default">JNCK Media</rdf:li></rdf:Alt></crs:Group><crs:ToneCurvePV2012Blue><rdf:Seq><rdf:li>0, 3</rdf:li><rdf:li>255, 251</rdf:li></rdf:Seq></crs:ToneCurvePV2012Blue></rdf:Description></rdf:RDF></x:xmpmeta>'''
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"source.xmp"; target=Path(directory)/"saved.xmp"; source.write_bytes(sample)
            doc=XmpDocument.open(source)
            doc.set_localized_value("Group", "SPS Studio")
            doc.save_as(target)
            saved=XmpDocument.open(target)
            self.assertEqual(saved.localized_value("Group"), "SPS Studio")
            self.assertEqual(saved.value("Exposure2012"), "0.35")
            self.assertEqual(saved.value("FutureSetting"), "must stay")
            self.assertEqual(saved.rdf_list_values("ToneCurvePV2012Blue"), ["0, 3", "255, 251"])

    def test_embedded_look_properties_are_read_and_updated(self):
        sample = b'''<?xml version="1.0"?><x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"><rdf:RDF><rdf:Description><crs:Look><rdf:Description crs:Name="Coconut ++" crs:Amount="0" crs:Cluster="Presetpro.com" crs:UUID="A0FCAF3A481E4079846CE358ED677C7F" crs:Stubbed="true"><crs:SortName><rdf:Alt><rdf:li xml:lang="x-default">57</rdf:li></rdf:Alt></crs:SortName><crs:Group><rdf:Alt><rdf:li xml:lang="x-default">010. Presetpro - Lifestyle</rdf:li></rdf:Alt></crs:Group></rdf:Description></crs:Look></rdf:Description></rdf:RDF></x:xmpmeta>'''
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"look.xmp"; source.write_bytes(sample); doc=XmpDocument.open(source)
            self.assertEqual(doc.look_value("Name"), "Coconut ++")
            self.assertEqual(doc.look_value("Group", True), "010. Presetpro - Lifestyle")
            self.assertEqual(doc.look_value("SortName", True), "57")
            doc.set_look_value("Cluster", "SPS Studio")
            self.assertEqual(doc.look_value("Cluster"), "SPS Studio")

    def test_look_in_a_second_rdf_description_is_found(self):
        sample = b'''<?xml version="1.0"?><x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"><rdf:RDF><rdf:Description crs:Name="Main preset"/><rdf:Description><rdf:Bag><rdf:li><crs:Look><rdf:Description crs:Name="Coconut ++" crs:Amount="0"/></crs:Look></rdf:li></rdf:Bag></rdf:Description></rdf:RDF></x:xmpmeta>'''
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"look-second-description.xmp"; source.write_bytes(sample); doc=XmpDocument.open(source)
            self.assertIsNotNone(doc.look_description)
            self.assertEqual(doc.look_value("Name"), "Coconut ++")

    def test_legacy_embedded_preset_metadata_is_found_and_updated(self):
        sample = b'''<?xml version="1.0"?><x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"><rdf:RDF><rdf:Description><crs:Preset><rdf:Description crs:Name="Bright Airy Wedding" crs:Amount="1" crs:UUID="D31FE70BAF8E19CC20E37BCFD5287391"><crs:Group><rdf:Alt><rdf:li xml:lang="x-default">JNCK Media</rdf:li></rdf:Alt></crs:Group><crs:Parameters><rdf:Description crs:Exposure2012="0.30"/></crs:Parameters></rdf:Description></crs:Preset></rdf:Description></rdf:RDF></x:xmpmeta>'''
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"legacy-preset.xmp"; source.write_bytes(sample); doc=XmpDocument.open(source)
            self.assertEqual(doc.embedded_metadata_kind, "beágyazott Lightroom preset")
            self.assertEqual(doc.look_value("Name"), "Bright Airy Wedding")
            self.assertEqual(doc.look_value("Group", True), "JNCK Media")
            doc.set_look_value("Amount", "0.75")
            self.assertEqual(doc.look_value("Amount"), "0.75")

    def test_embedded_look_can_be_created_without_changing_tone_values(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"plain.xmp"; source.write_bytes(SAMPLE)
            doc=XmpDocument.open(source)
            original_exposure=doc.value("Exposure2012")
            doc.create_embedded_look("SPS Metadata Look")
            self.assertEqual(doc.embedded_metadata_kind, "Look / Camera Raw profil")
            self.assertEqual(doc.look_value("Name"), "SPS Metadata Look")
            self.assertEqual(doc.look_value("Group", True), "SPS Studio Hungary")
            self.assertEqual(doc.look_value("Amount"), "0")
            self.assertEqual(doc.value("Exposure2012"), original_exposure)

    def test_metadata_template_changes_only_safe_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"source.xmp"; source.write_bytes(SAMPLE); doc=XmpDocument.open(source)
            changed=doc.apply_metadata_template({"Group":"SPS Studio Hungary", "Copyright / Rights":"Copyright SPS"})
            self.assertEqual(changed, ["Group", "Copyright / Rights"])
            self.assertEqual(doc.localized_value("Group"), "SPS Studio Hungary")
            self.assertEqual(doc.rights_value(), "Copyright SPS")
            self.assertEqual(doc.value("Exposure2012"), "0.00")

    def test_save_with_backup_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"source.xmp"; target=Path(directory)/"target.xmp"; source.write_bytes(SAMPLE); target.write_bytes(b"original target")
            doc=XmpDocument.open(source); doc.set_localized_value("Name", "SPS")
            backup=doc.save_with_backup(target)
            self.assertEqual(backup, target.with_suffix(".xmp.bak"))
            self.assertEqual(backup.read_bytes(), b"original target")
            self.assertEqual(XmpDocument.open(target).localized_value("Name"), "SPS")

    def test_diagnostics_identifies_missing_required_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"source.xmp"; source.write_bytes(SAMPLE.replace(b' crs:Name="Airy"', b"")); doc=XmpDocument.open(source)
            self.assertIn("Hiányzik a preset neve.", doc.diagnostics())
            self.assertIn("Hiányzik a preset UUID azonosítója.", doc.diagnostics())

if __name__ == "__main__": unittest.main()

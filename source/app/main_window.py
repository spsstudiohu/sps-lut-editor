from __future__ import annotations

import copy
import csv
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSplitter, QStackedWidget,
    QScrollArea, QTableWidget, QTableWidgetItem, QTextEdit, QToolBar, QVBoxLayout, QWidget
)

from app.widgets import NumericControl, SpsLogo, controls_panel
from app.update import INSTALLER_NAME, UpdateError, download_verified, is_newer, latest_release
from app.xmp import XmpDocument, XmpError

BASIC = [("Exposure2012", "Exposure", -5, 5, .01, 2), ("Contrast2012", "Contrast", -100, 100, 1, 0),
         ("Highlights2012", "Highlights", -100, 100, 1, 0), ("Shadows2012", "Shadows", -100, 100, 1, 0),
         ("Whites2012", "Whites", -100, 100, 1, 0), ("Blacks2012", "Blacks", -100, 100, 1, 0),
         ("Texture", "Texture", -100, 100, 1, 0), ("Clarity2012", "Clarity", -100, 100, 1, 0),
         ("Dehaze", "Dehaze", -100, 100, 1, 0), ("Vibrance", "Vibrance", -100, 100, 1, 0),
         ("Saturation", "Saturation", -100, 100, 1, 0)]
HSL_COLORS = ("Red", "Orange", "Yellow", "Green", "Aqua", "Blue", "Purple", "Magenta")
HSL = [(f"HueAdjustment{c}", f"{c} Hue", -100, 100, 1, 0) for c in HSL_COLORS] + [(f"SaturationAdjustment{c}", f"{c} Saturation", -100, 100, 1, 0) for c in HSL_COLORS] + [(f"LuminanceAdjustment{c}", f"{c} Luminance", -100, 100, 1, 0) for c in HSL_COLORS]
DETAIL = [("SharpenRadius", "Sharpen Radius", .5, 3, .1, 1), ("SharpenDetail", "Sharpen Detail", 0, 100, 1, 0), ("SharpenEdgeMasking", "Masking", 0, 100, 1, 0), ("LuminanceSmoothing", "Luminance Noise Reduction", 0, 100, 1, 0), ("ColorNoiseReduction", "Color Noise Reduction", 0, 100, 1, 0)]
EFFECTS = [("PostCropVignetteAmount", "Post-Crop Vignette", -100, 100, 1, 0), ("GrainAmount", "Grain Amount", 0, 100, 1, 0), ("GrainSize", "Grain Size", 0, 100, 1, 0), ("GrainFrequency", "Grain Roughness", 0, 100, 1, 0)]
APP_VERSION = "0.2.0"


class BatchMetadataDialog(QDialog):
    """Lets users choose only safe, non-rendering metadata for many files."""
    FIELDS = ("Group", "Creator Tool", "Process Version", "Copyright / Rights")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kötegelt metaadat-szerkesztés")
        layout = QVBoxLayout(self)
        note = QLabel("Csak metaadatok változnak; a szín- és presetértékek érintetlenek maradnak.")
        note.setWordWrap(True); layout.addWidget(note)
        form = QFormLayout(); self.fields = {}
        for label in self.FIELDS:
            row = QWidget(); row_layout = QHBoxLayout(row); row_layout.setContentsMargins(0, 0, 0, 0)
            enabled = QCheckBox("Módosítás"); field = QLineEdit(); field.setEnabled(False)
            enabled.toggled.connect(field.setEnabled)
            row_layout.addWidget(enabled); row_layout.addWidget(field, 1)
            form.addRow(label + ":", row); self.fields[label] = (enabled, field)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def values(self) -> dict[str, str]:
        return {label: field.text() for label, (enabled, field) in self.fields.items() if enabled.isChecked()}


class CompareDialog(QDialog):
    def __init__(self, parent: "MainWindow"):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Preset összehasonlítás")
        self.resize(820, 500)
        layout = QVBoxLayout(self)
        choose = QPushButton("Preset B megnyitása…")
        choose.clicked.connect(self.load_b)
        layout.addWidget(choose)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Paraméter", "Aktuális preset (A)", "Preset B", "Másolás"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.other: XmpDocument | None = None

    def load_b(self):
        path, _ = QFileDialog.getOpenFileName(self, "Preset B", "", "XMP preset (*.xmp);;Minden fájl (*)")
        if not path:
            return
        try:
            self.other = XmpDocument.open(path)
        except XmpError as exc:
            QMessageBox.critical(self, "Megnyitási hiba", str(exc)); return
        a = self.parent_window.document.crs_values() if self.parent_window.document else {}
        b = self.other.crs_values()
        keys = sorted(set(a) | set(b))
        self.table.setRowCount(0)
        for key in keys:
            if a.get(key, "") == b.get(key, ""):
                continue
            row = self.table.rowCount(); self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(key)); self.table.setItem(row, 1, QTableWidgetItem(a.get(key, "—"))); self.table.setItem(row, 2, QTableWidgetItem(b.get(key, "—")))
            button = QPushButton("B → A")
            button.clicked.connect(lambda _, k=key, v=b.get(key, ""): self.parent_window.apply_value(k, v))
            self.table.setCellWidget(row, 3, button)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.document: XmpDocument | None = None
        self.original_root = None
        self.history: list[object] = []
        self.future: list[object] = []
        self.controls: dict[str, NumericControl] = {}
        self.setWindowTitle(f"SPS LUT Editor {APP_VERSION}")
        self.setAcceptDrops(True)
        self.resize(1200, 780)
        self._build_ui(); self._build_actions(); self.statusBar().showMessage("Készen áll – nyisson meg egy XMP presetet."); self.update_ui()

    def _build_ui(self):
        toolbar = QToolBar("Fő műveletek"); toolbar.setMovable(False); self.addToolBar(toolbar)
        self.open_action = QAction("Megnyitás", self); self.save_action = QAction("Mentés másként", self); self.save_sps_action = QAction("Mentés SPS_ előtaggal", self)
        toolbar.addAction(self.open_action); toolbar.addAction(self.save_action); toolbar.addAction(self.save_sps_action)
        toolbar.addSeparator(); self.undo_action = QAction("Visszavonás", self); self.redo_action = QAction("Újra", self)
        toolbar.addAction(self.undo_action); toolbar.addAction(self.redo_action)
        root = QSplitter(); root.setChildrenCollapsible(False); self.setCentralWidget(root)
        sidebar = QWidget(); side = QVBoxLayout(sidebar); side.setContentsMargins(12, 12, 12, 12)
        side.addWidget(SpsLogo())
        self.nav_buttons: list[QPushButton] = []
        self.pages = QStackedWidget()
        for name, page in self._pages():
            button = QPushButton(name); button.setCheckable(True); button.setStyleSheet("text-align:left; padding:9px;")
            index = self.pages.addWidget(page); button.clicked.connect(lambda _, i=index: self.select_page(i))
            side.addWidget(button); self.nav_buttons.append(button)
        side.addStretch(); line = QFrame(); line.setFrameShape(QFrame.HLine); side.addWidget(line)
        self.file_label = QLabel("Nincs megnyitott fájl"); self.file_label.setWordWrap(True); side.addWidget(self.file_label)
        self.modified_label = QLabel("Módosítva: Nem"); side.addWidget(self.modified_label)
        root.addWidget(sidebar); root.addWidget(self.pages); root.setSizes([245, 955]); self.select_page(0)

    def _pages(self):
        yield "Preset információ", self._info_page()
        yield "Basic Tone", self._controls_page(BASIC, "A Lightroom/Camera Raw 2012-es Basic Tone értékei.")
        yield "Tone Curve", self._curve_page()
        yield "Color Mixer / HSL", self._controls_page(HSL, "A meglévő vagy újonnan megadott HSL értékek.")
        yield "Detail", self._controls_page(DETAIL)
        yield "Effects", self._controls_page(EFFECTS)
        yield "Other / Unsupported", self._other_page()
        yield "Raw XML (Advanced)", self._raw_page()

    def _info_page(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        page = QWidget(); scroll.setWidget(page); layout = QVBoxLayout(page); layout.setContentsMargins(32, 28, 32, 28)
        heading = QLabel("Preset információk"); heading.setStyleSheet("font-size: 22px; font-weight: 700;"); layout.addWidget(heading)
        note = QLabel("A jogkezelési metaadatokat az editor jelzi és változatlanul megőrzi."); note.setStyleSheet("color:#8a5a00;"); layout.addWidget(note)
        form = QFormLayout(); self.info_fields = {}
        for label in ("Preset Name", "Group", "UUID", "Creator Tool", "Process Version", "Copyright / Rights"):
            field = QLineEdit(); field.editingFinished.connect(lambda l=label, f=field: self.apply_metadata(l, f.text()))
            form.addRow(label + ":", field); self.info_fields[label] = field
        layout.addLayout(form)
        profile_heading = QLabel("RAW profil (csak olvasható)"); profile_heading.setStyleSheet("font-size: 15px; font-weight: 600; margin-top: 12px;"); layout.addWidget(profile_heading)
        profile_note = QLabel("A profil módosítása megváltoztathatja a preset színmegjelenítését, ezért itt zárolt."); profile_note.setWordWrap(True); profile_note.setStyleSheet("color:#8a5a00;"); layout.addWidget(profile_note)
        profile_form = QFormLayout(); self.profile_fields = {}
        for label in ("Camera Profile", "Camera Profile Digest"):
            field = QLineEdit(); field.setReadOnly(True); field.setToolTip("Csak olvasható a színprofil és a presetkompatibilitás védelmében.")
            profile_form.addRow(label + ":", field); self.profile_fields[label] = field
        layout.addLayout(profile_form)
        self.look_heading = QLabel("Embedded Look / Camera Raw profil"); self.look_heading.setStyleSheet("font-size: 15px; font-weight: 600; margin-top: 12px;"); layout.addWidget(self.look_heading)
        look_form = QFormLayout(); self.look_fields = {}
        for label in ("Look Name", "Look Group", "Sort Name", "Look UUID", "Amount", "Cluster", "Stubbed"):
            field = QLineEdit(); field.editingFinished.connect(lambda l=label, f=field: self.apply_look(l, f.text()))
            look_form.addRow(label + ":", field); self.look_fields[label] = field
        layout.addLayout(look_form)
        self.create_look_button = QPushButton("Embedded Look létrehozása")
        self.create_look_button.setToolTip("Új Look metaadatblokkot hoz létre Amount=0 értékkel, a kép színeinek módosítása nélkül.")
        self.create_look_button.clicked.connect(self.create_embedded_look)
        layout.addWidget(self.create_look_button, alignment=Qt.AlignLeft)
        generate = QPushButton("Új UUID generálása")
        generate.clicked.connect(self.generate_uuid); layout.addWidget(generate, alignment=Qt.AlignLeft); layout.addStretch()
        return scroll

    def _controls_page(self, definitions, intro=""):
        items=[]
        for key,label,minimum,maximum,step,decimals in definitions:
            control=NumericControl(label, minimum, maximum, step, decimals); control.changed.connect(lambda value, k=key: self.apply_value(k, value))
            self.controls[key]=control; items.append((key,control))
        return controls_panel(items, intro)

    def _other_page(self):
        page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(28,28,28,28)
        layout.addWidget(QLabel("Egyéb / nem támogatott Camera Raw paraméterek"))
        self.other_table=QTableWidget(0,2); self.other_table.setHorizontalHeaderLabels(["Paraméter", "Érték"]); self.other_table.horizontalHeader().setStretchLastSection(True)
        self.other_table.itemChanged.connect(self.other_changed); layout.addWidget(self.other_table); return page

    def _curve_page(self):
        page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(28,28,28,28)
        layout.addWidget(QLabel("Tone Curve PV2012 - egy pont soronként (pl. 0, 0)."))
        self.curve_edits={}
        for label,key in (("RGB / Master","ToneCurvePV2012"),("Red","ToneCurvePV2012Red"),("Green","ToneCurvePV2012Green"),("Blue","ToneCurvePV2012Blue")):
            layout.addWidget(QLabel(label)); field=QTextEdit(); field.setFixedHeight(92); field.setFontFamily("Consolas"); layout.addWidget(field); self.curve_edits[key]=field
        apply=QPushButton("Görbék alkalmazása"); apply.clicked.connect(self.apply_curves); layout.addWidget(apply, alignment=Qt.AlignRight); return page

    def _raw_page(self):
        page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(28,28,28,28)
        warning=QLabel("Advanced: a kézi XML-szerkesztés mentés előtt érvényesítésre kerül."); warning.setStyleSheet("color:#8a5a00;"); layout.addWidget(warning)
        self.raw_edit=QTextEdit(); self.raw_edit.setAcceptRichText(False); self.raw_edit.setFontFamily("Consolas"); layout.addWidget(self.raw_edit)
        apply=QPushButton("Raw XML érvényesítése és alkalmazása"); apply.clicked.connect(self.apply_raw); layout.addWidget(apply, alignment=Qt.AlignRight); return page

    def _build_actions(self):
        self.open_action.setShortcut(QKeySequence.Open); self.open_action.triggered.connect(self.open_file)
        self.save_action.setShortcut(QKeySequence.SaveAs); self.save_action.triggered.connect(self.save_as)
        self.undo_action.setShortcut(QKeySequence.Undo); self.undo_action.triggered.connect(self.undo)
        self.redo_action.setShortcut(QKeySequence.Redo); self.redo_action.triggered.connect(self.redo)
        menu=self.menuBar().addMenu("Fájl"); menu.addAction(self.open_action); menu.addAction(self.save_action); menu.addAction(self.save_sps_action)
        self.save_sps_action.triggered.connect(self.save_with_sps_prefix)
        menu.addSeparator()
        batch=QAction("Kötegelt metaadat-szerkesztés…",self); batch.triggered.connect(self.batch_edit); menu.addAction(batch)
        package=QAction("SPS kiadási csomag exportálása…",self); package.triggered.connect(self.export_package); menu.addAction(package)
        rename=QAction("Kötegelt átnevezési másolat…",self); rename.triggered.connect(self.batch_rename); menu.addAction(rename)
        report=QAction("Preset-jelentés exportálása…",self); report.triggered.connect(self.export_report); menu.addAction(report)
        self.backup_action=QAction(".bak biztonsági másolat felülíráskor",self); self.backup_action.setCheckable(True); self.backup_action.setChecked(True); menu.addAction(self.backup_action)
        edit=self.menuBar().addMenu("Szerkesztés"); edit.addAction(self.undo_action); edit.addAction(self.redo_action)
        reset=QAction("Eredeti értékek visszaállítása",self); reset.triggered.connect(self.restore_original); edit.addAction(reset)
        tools=self.menuBar().addMenu("Eszközök"); compare=QAction("Preset összehasonlítás…",self); compare.triggered.connect(self.compare); tools.addAction(compare)
        changes=QAction("Mentés előtti változások…",self); changes.triggered.connect(self.show_changes); tools.addAction(changes)
        diagnose=QAction("XMP diagnosztika…",self); diagnose.triggered.connect(self.show_diagnostics); tools.addAction(diagnose)
        tools.addSeparator()
        template_export=QAction("Metaadat-sablon mentése…",self); template_export.triggered.connect(self.export_template); tools.addAction(template_export)
        template_import=QAction("Metaadat-sablon alkalmazása…",self); template_import.triggered.connect(self.import_template); tools.addAction(template_import)
        help_menu=self.menuBar().addMenu("Súgó")
        check_update=QAction("Frissítések keresése…",self); check_update.triggered.connect(self.check_for_updates); help_menu.addAction(check_update)

    def select_page(self,index):
        self.pages.setCurrentIndex(index)
        for i,button in enumerate(self.nav_buttons): button.setChecked(i==index)

    def choose_xmp_files(self, title: str) -> list[str]:
        paths, _ = QFileDialog.getOpenFileNames(self, title, "", "XMP preset (*.xmp)")
        return paths

    def check_for_updates(self):
        self.statusBar().showMessage("Frissítések keresése a GitHubon…")
        QApplication.processEvents()
        try:
            release = latest_release()
            if not is_newer(release.version, APP_VERSION):
                QMessageBox.information(self, "Frissítések", f"A legújabb verziót használod ({APP_VERSION}).")
                return
            details = release.notes.strip() or "Nincs kiadási megjegyzés."
            answer = QMessageBox.question(self, "Új verzió elérhető", f"Elérhető: {release.version}\nJelenlegi: {APP_VERSION}\n\n{details[:1200]}\n\nLetöltöd az ellenőrzött telepítőt?", QMessageBox.Yes | QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
            target = Path(tempfile.gettempdir()) / INSTALLER_NAME
            installer = download_verified(release, target)
            QMessageBox.information(self, "Frissítő letöltve", "A telepítő elindul. A telepítés után indítsd újra az editort.")
            os.startfile(str(installer))
        except UpdateError as exc:
            QMessageBox.warning(self, "Frissítési hiba", str(exc))
        finally:
            self.statusBar().showMessage("Készen áll.")

    def show_changes(self):
        if not self.document or self.original_root is None:
            return
        before = XmpDocument(None, copy.deepcopy(self.original_root))
        changes = []
        for key in sorted(set(before.crs_values()) | set(self.document.crs_values())):
            old, new = before.value(key), self.document.value(key)
            if old != new:
                changes.append(f"{key}: {old or '—'}  →  {new or '—'}")
        for label, old, new in (
            ("Preset Name", before.localized_value("Name"), self.document.localized_value("Name")),
            ("Group", before.localized_value("Group"), self.document.localized_value("Group")),
            ("Copyright / Rights", before.rights_value(), self.document.rights_value()),
        ):
            if old != new:
                changes.append(f"{label}: {old or '—'}  →  {new or '—'}")
        QMessageBox.information(self, "Mentés előtti változások", "Nincs módosítás." if not changes else "\n".join(changes))

    def show_diagnostics(self):
        if not self.document:
            return
        issues = self.document.diagnostics()
        QMessageBox.information(self, "XMP diagnosztika", "Az XMP szerkezete rendben van." if not issues else "\n".join(f"• {issue}" for issue in issues))

    def export_template(self):
        if not self.document:
            return
        target, _ = QFileDialog.getSaveFileName(self, "Metaadat-sablon mentése", "sps-metadata-template.json", "JSON fájl (*.json)")
        if not target:
            return
        try:
            self.document.save_template(target)
            self.statusBar().showMessage(f"Metaadat-sablon mentve: {Path(target).name}")
        except XmpError as exc:
            QMessageBox.critical(self, "Sablon mentési hiba", str(exc))

    def import_template(self):
        if not self.document:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Metaadat-sablon megnyitása", "", "JSON fájl (*.json)")
        if not path:
            return
        try:
            values = XmpDocument.load_template(path)
            if not values:
                QMessageBox.information(self, "Sablon", "A sablon nem tartalmaz alkalmazható metaadatot."); return
            self.snapshot(); changed = self.document.apply_metadata_template(values)
            if not changed:
                self.history.pop()
            self.update_ui(); self.statusBar().showMessage("Sablon alkalmazva: " + (", ".join(changed) if changed else "nincs eltérés"))
        except XmpError as exc:
            QMessageBox.critical(self, "Sablon betöltési hiba", str(exc))

    def batch_edit(self):
        paths = self.choose_xmp_files("XMP presetek kijelölése")
        if not paths:
            return
        dialog = BatchMetadataDialog(self)
        if dialog.exec() != QDialog.Accepted or not dialog.values():
            return
        destination = QFileDialog.getExistingDirectory(self, "Kiadási mappa kiválasztása")
        if not destination:
            return
        values, saved, failures = dialog.values(), [], []
        for path in paths:
            try:
                document = XmpDocument.open(path)
                document.apply_metadata_template(values)
                source_name = Path(path).name
                target = Path(destination) / (source_name if source_name.startswith("SPS_") else f"SPS_{source_name}")
                document.save_as(target); saved.append(target.name)
            except XmpError as exc:
                failures.append(f"{Path(path).name}: {exc}")
        message = f"{len(saved)} preset elkészült a kiválasztott kiadási mappában."
        if failures: message += "\n\nNem sikerült:\n" + "\n".join(failures)
        QMessageBox.information(self, "Kötegelt szerkesztés", message)

    def export_package(self):
        paths = self.choose_xmp_files("Presetek kiválasztása az SPS csomaghoz")
        if not paths:
            return
        destination = QFileDialog.getExistingDirectory(self, "SPS kiadási mappa")
        if not destination:
            return
        copied, failures = [], []
        for path in paths:
            source = Path(path); target = Path(destination) / (source.name if source.name.startswith("SPS_") else f"SPS_{source.name}")
            try:
                shutil.copy2(source, target); copied.append(target.name)
            except OSError as exc:
                failures.append(f"{source.name}: {exc}")
        message = f"{len(copied)} változatlan preset került az SPS kiadási mappába."
        if failures: message += "\n\nNem sikerült:\n" + "\n".join(failures)
        QMessageBox.information(self, "SPS csomag export", message)

    def batch_rename(self):
        paths = self.choose_xmp_files("Átnevezendő presetek kiválasztása")
        if not paths:
            return
        find, ok = QInputDialog.getText(self, "Kötegelt átnevezés", "Cserélendő szöveg a fájlnévben:")
        if not ok:
            return
        replacement, ok = QInputDialog.getText(self, "Kötegelt átnevezés", "Új szöveg:")
        if not ok:
            return
        destination = QFileDialog.getExistingDirectory(self, "Új nevű másolatok mappája")
        if not destination:
            return
        copied = 0
        for path in paths:
            source = Path(path); name = source.name.replace(find, replacement) if find else source.name
            target = Path(destination) / (name if name.startswith("SPS_") else f"SPS_{name}")
            try:
                shutil.copy2(source, target); copied += 1
            except OSError as exc:
                QMessageBox.warning(self, "Átnevezési hiba", f"{source.name}: {exc}")
        QMessageBox.information(self, "Kötegelt átnevezés", f"{copied} új nevű másolat elkészült. Az eredeti fájlok változatlanok.")

    def export_report(self):
        paths = self.choose_xmp_files("Presetek kiválasztása a jelentéshez")
        if not paths:
            return
        target, _ = QFileDialog.getSaveFileName(self, "Preset-jelentés mentése", "sps-preset-report.csv", "CSV fájl (*.csv);;JSON fájl (*.json)")
        if not target:
            return
        rows = []
        for path in paths:
            try:
                document = XmpDocument.open(path); metadata = document.metadata()
                rows.append({"Fájl": Path(path).name, **metadata, "Look": document.look_value("Name"), "Look Group": document.look_value("Group", True)})
            except XmpError as exc:
                rows.append({"Fájl": Path(path).name, "Hiba": str(exc)})
        try:
            if Path(target).suffix.lower() == ".json":
                Path(target).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            else:
                keys = sorted({key for row in rows for key in row})
                with Path(target).open("w", encoding="utf-8-sig", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)
            QMessageBox.information(self, "Jelentés elkészült", f"{len(rows)} preset adatai mentve: {Path(target).name}")
        except OSError as exc:
            QMessageBox.critical(self, "Jelentés mentési hiba", str(exc))

    def open_file(self):
        path,_=QFileDialog.getOpenFileName(self,"XMP preset megnyitása","","XMP preset (*.xmp);;Minden fájl (*)")
        if not path:return
        try:
            self.document=XmpDocument.open(path); self.original_root=copy.deepcopy(self.document.root); self.history=[]; self.future=[]; self.update_ui()
            self.statusBar().showMessage(f"Megnyitva: {Path(path).name}")
        except XmpError as exc: QMessageBox.critical(self,"Megnyitási hiba",str(exc))

    def snapshot(self):
        if self.document: self.history.append(copy.deepcopy(self.document.root)); self.future.clear()

    def apply_metadata(self,label,value):
        mapping={"Preset Name":("crs","Name"),"Group":("crs","Group"),"UUID":("crs","UUID"),"Creator Tool":("xmp","CreatorTool"),"Process Version":("crs","ProcessVersion"),"Copyright / Rights":("dc","rights")}
        namespaces={"crs":"http://ns.adobe.com/camera-raw-settings/1.0/", "xmp":"http://ns.adobe.com/xap/1.0/", "dc":"http://purl.org/dc/elements/1.1/"}
        if self.document and label in ("Preset Name", "Group"):
            key=mapping[label][1]
            if self.document.localized_value(key) != value:
                self.snapshot(); self.document.set_localized_value(key,value); self.update_ui(keep_focus=True); self.statusBar().showMessage(f"Módosítva: {label}")
        elif self.document and label == "Copyright / Rights":
            if self.document.rights_value() != value:
                self.snapshot(); self.document.set_rights(value); self.update_ui(keep_focus=True); self.statusBar().showMessage("Módosítva: Copyright / Rights")
        elif self.document and label in mapping:
            prefix,name=mapping[label]; current=self.document.description.get(f"{{{namespaces[prefix]}}}{name}","")
            if current != value: self.snapshot(); self.document.set_attribute(namespaces[prefix],name,value); self.update_ui(keep_focus=True); self.statusBar().showMessage(f"Módosítva: {label}")

    def apply_value(self,key,value):
        if self.document and self.document.value(key)!=value:
            self.snapshot(); self.document.set_value(key,value); self.update_ui(keep_focus=True); self.statusBar().showMessage(f"Módosítva: {key} = {value}")

    def apply_look(self, label, value):
        if not self.document or self.document.look_description is None:
            return
        mapping={"Look Name":("Name",False), "Look Group":("Group",True), "Sort Name":("SortName",True), "Look UUID":("UUID",False), "Amount":("Amount",False), "Cluster":("Cluster",False), "Stubbed":("Stubbed",False)}
        key,localized=mapping[label]
        if self.document.look_value(key, localized) != value:
            self.snapshot(); self.document.set_look_value(key,value,localized); self.update_ui(keep_focus=True); self.statusBar().showMessage(f"Módosítva: {label}")

    def create_embedded_look(self):
        if not self.document or self.document.look_description is not None:
            return
        suggested = self.document.metadata().get("Preset Name") or "New SPS Look"
        name, accepted = QInputDialog.getText(self, "Embedded Look létrehozása", "Look neve:", text=suggested)
        if not accepted or not name.strip():
            return
        self.snapshot()
        try:
            self.document.create_embedded_look(name.strip())
            self.update_ui(); self.statusBar().showMessage("Embedded Look létrehozva (Amount = 0).")
        except XmpError as exc:
            self.history.pop(); QMessageBox.critical(self, "Look létrehozási hiba", str(exc))

    def generate_uuid(self):
        if self.document and QMessageBox.question(self,"UUID módosítása","Az új UUID miatt az Adobe új presetként kezelheti. Folytatja?")==QMessageBox.Yes: self.apply_value("UUID",str(uuid.uuid4()))

    def other_changed(self,item):
        if item.column()==1 and self.document:
            key=self.other_table.item(item.row(),0).text(); self.apply_value(key,item.text())

    def apply_raw(self):
        if not self.document:return
        self.snapshot()
        try: self.document.replace_from_raw(self.raw_edit.toPlainText()); self.update_ui(); self.statusBar().showMessage("Raw XML ellenőrizve és alkalmazva.")
        except XmpError as exc: self.history.pop(); QMessageBox.critical(self,"XML hiba",str(exc))

    def apply_curves(self):
        if not self.document: return
        new_values={key:[line.strip() for line in field.toPlainText().splitlines() if line.strip()] for key,field in self.curve_edits.items()}
        if any(self.document.rdf_list_values(key) != values for key,values in new_values.items()):
            self.snapshot()
            for key,values in new_values.items(): self.document.set_rdf_list_values(key, values)
            self.update_ui(); self.statusBar().showMessage("Tone Curve értékek módosítva.")

    def undo(self):
        if self.document and self.history: self.future.append(copy.deepcopy(self.document.root)); self.document.root=self.history.pop(); self.update_ui()
    def redo(self):
        if self.document and self.future: self.history.append(copy.deepcopy(self.document.root)); self.document.root=self.future.pop(); self.update_ui()
    def restore_original(self):
        if self.document and self.original_root is not None: self.snapshot(); self.document.root=copy.deepcopy(self.original_root); self.update_ui()
    def save_as(self):
        if not self.document:return
        default=str(self.document.path.with_name(self.document.path.stem+"-edited.xmp")) if self.document.path else "preset-edited.xmp"
        target,_=QFileDialog.getSaveFileName(self,"Mentés másként",default,"XMP preset (*.xmp)")
        if not target:return
        self.statusBar().showMessage("Mentés folyamatban: XML ellenőrzése…")
        QApplication.processEvents()
        try:
            backup = self.document.save_with_backup(target) if self.backup_action.isChecked() else (self.document.save_as(target) or None)
            detail = f"\nBiztonsági másolat: {backup.name}" if backup else ""
            self.statusBar().showMessage(f"Mentve és érvényesítve: {Path(target).name}"); QMessageBox.information(self,"Mentés kész","Az XMP érvényesítve és új fájlként mentve lett." + detail)
        except XmpError as exc: QMessageBox.critical(self,"Mentési hiba",str(exc))

    def save_with_sps_prefix(self):
        """Create or deliberately replace the SPS_ working copy beside the source."""
        if not self.document:
            return
        if self.document.path is None:
            self.save_as(); return
        filename = self.document.path.name
        target = self.document.path.with_name(filename if filename.startswith("SPS_") else f"SPS_{filename}")
        if target.exists() and QMessageBox.question(self, "SPS_ fájl felülírása", f"A következő fájl már létezik:\n{target.name}\n\nFelülírja a friss adatokkal?") != QMessageBox.Yes:
            return
        self.statusBar().showMessage("SPS_ fájl mentése és XML ellenőrzése…")
        QApplication.processEvents()
        try:
            backup = self.document.save_with_backup(target) if self.backup_action.isChecked() else (self.document.save_as(target) or None)
            self.statusBar().showMessage(f"Mentve: {target.name}")
            backup_note = f"\nBiztonsági másolat: {backup.name}" if backup else ""
            QMessageBox.information(self, "Mentés kész", f"Az új adatok a következő fájlba kerültek:\n{target.name}\n\nAz eredeti fájl változatlan maradt." + backup_note)
        except XmpError as exc:
            QMessageBox.critical(self, "Mentési hiba", str(exc))
    def compare(self):
        if not self.document: QMessageBox.information(self,"Összehasonlítás","Előbb nyisson meg egy presetet."); return
        CompareDialog(self).exec()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.toLocalFile().lower().endswith(".xmp") for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths=[url.toLocalFile() for url in event.mimeData().urls()]
        if paths:
            try: self.document=XmpDocument.open(paths[0]); self.original_root=copy.deepcopy(self.document.root); self.history=[]; self.future=[]; self.update_ui()
            except XmpError as exc: QMessageBox.critical(self,"Megnyitási hiba",str(exc))

    def update_ui(self,keep_focus=False):
        active=QApplication.focusWidget() if keep_focus else None
        if not self.document:
            for b in self.nav_buttons[1:]: b.setEnabled(False)
            self.save_action.setEnabled(False); self.save_sps_action.setEnabled(False); return
        for b in self.nav_buttons: b.setEnabled(True)
        self.save_action.setEnabled(True); self.save_sps_action.setEnabled(True); meta=self.document.metadata()
        for label,field in self.info_fields.items(): field.setText(meta.get(label,""))
        self.profile_fields["Camera Profile"].setText(self.document.value("CameraProfile") or "Nincs külön profil megadva")
        self.profile_fields["Camera Profile Digest"].setText(self.document.value("CameraProfileDigest") or "—")
        look_mapping={"Look Name":("Name",False), "Look Group":("Group",True), "Sort Name":("SortName",True), "Look UUID":("UUID",False), "Amount":("Amount",False), "Cluster":("Cluster",False), "Stubbed":("Stubbed",False)}
        has_look=self.document.look_description is not None
        kind=self.document.embedded_metadata_kind
        self.look_heading.setText(f"Embedded {kind} – felismerve" if has_look else "Embedded Look / Camera Raw profil – nincs ebben a presetben")
        for label,field in self.look_fields.items():
            key,localized=look_mapping[label]; field.setText(self.document.look_value(key,localized)); field.setEnabled(has_look)
        self.create_look_button.setVisible(not has_look)
        for key,control in self.controls.items(): control.set_text(self.document.value(key))
        for key,field in self.curve_edits.items(): field.setPlainText("\n".join(self.document.rdf_list_values(key)))
        known=set(self.controls)|{"Name","Group","UUID","ProcessVersion","CameraProfile","CameraProfileDigest"}
        values=self.document.crs_values(); self.other_table.blockSignals(True); self.other_table.setRowCount(0)
        for key,value in sorted(values.items()):
            if key not in known:
                row=self.other_table.rowCount(); self.other_table.insertRow(row); self.other_table.setItem(row,0,QTableWidgetItem(key)); self.other_table.setItem(row,1,QTableWidgetItem(value))
        self.other_table.blockSignals(False); self.raw_edit.setPlainText(self.document.raw_xml())
        self.file_label.setText(f"Fájl:\n{self.document.path.name if self.document.path else 'Névtelen'}")
        self.modified_label.setText("Módosítva: " + ("Igen" if self.history else "Nem")); self.undo_action.setEnabled(bool(self.history)); self.redo_action.setEnabled(bool(self.future))
        if active: active.setFocus()

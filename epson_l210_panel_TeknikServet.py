#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Epson L210 Yazdırma ve Bakım Paneli (PyQt5) - modern arayüz

Bu bir "sürücü" değil, CUPS ve escputil üzerinde çalışan bir arayüzdür.
Gerekenler:
  - python3-pyqt5
  - cups (lp, lpstat, cancel, cupsenable)
  - epson-inkjet-printer-escpr (Epson ESC/P-R sürücüsü)
  - escputil (bakım için)
  - poppler-utils veya python3-pypdf (PDF sayfa sayısı için, isteğe bağlı)
  - fonts-noto-color-emoji (simgeler için, isteğe bağlı)
Bakım için kullanıcı 'lp' grubunda olmalıdır.
"""
import glob
import os
import re
import subprocess
import sys

from PyQt5.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QComboBox, QPushButton, QLineEdit, QSpinBox, QCheckBox, QFileDialog,
    QMessageBox, QPlainTextEdit, QLabel, QListWidget, QFrame, QProgressBar,
)

USE_EMOJI = True  # Simgeler görünmüyorsa False yapın


def ic(e):
    return f"{e}  " if USE_EMOJI else ""


# ======================= Temalar =======================
THEMES = {
    "light": dict(
        bg="#F3F5F9", card="#FFFFFF", text="#1E2430", muted="#6B7385",
        border="#E1E5EE", input="#F8F9FC", btn="#FFFFFF", hover="#EEF1F7",
        accent="#3B82F6", accent_hover="#2563EB", accent_soft="#E3EDFF",
        log="#F8F9FC", ok="#15803D", ok_bg="#DCFCE7", warn="#B45309",
        warn_bg="#FEF3C7", bad="#B91C1C", bad_bg="#FEE2E2", chip="#E9ECF3",
        info="#1D4ED8", info_bg="#DBEAFE",
    ),
    "dark": dict(
        bg="#11141B", card="#1A1E28", text="#E7EAF1", muted="#98A1B3",
        border="#2A3040", input="#232938", btn="#222837", hover="#2B3245",
        accent="#4C8DFF", accent_hover="#6AA1FF", accent_soft="#22304D",
        log="#0C0F15", ok="#4ADE80", ok_bg="#16301F", warn="#FBBF24",
        warn_bg="#3A2E12", bad="#F87171", bad_bg="#3B1A1A", chip="#262C3B",
        info="#7DB0FF", info_bg="#1E2D4D",
    ),
}

QSS = """
QWidget { color:@text@; font-size:10pt; }
QWidget#root { background:@bg@; }
QMessageBox, QDialog, QFileDialog { background:@bg@; }
QLabel { background:transparent; }
QLabel#title { font-size:19pt; font-weight:700; }
QLabel#subtitle, QLabel#muted { color:@muted@; }
QLabel#cardTitle { font-weight:700; font-size:10.5pt; }
QLabel#fieldLabel { color:@muted@; font-size:9pt; font-weight:600; }
QLabel#chip { padding:5px 14px; border-radius:13px; background:@chip@;
              color:@muted@; font-weight:700; }
QLabel#chip[state="ok"] { background:@ok_bg@; color:@ok@; }
QLabel#chip[state="busy"] { background:@info_bg@; color:@info@; }
QLabel#chip[state="bad"] { background:@bad_bg@; color:@bad@; }
QFrame#card { background:@card@; border:1px solid @border@; border-radius:14px; }
QFrame#drop { background:@input@; border:1px dashed @border@; border-radius:10px; }

QTabWidget::pane { border:none; top:8px; }
QTabBar::tab { background:transparent; color:@muted@; padding:9px 18px;
               margin-right:4px; border-radius:9px; font-weight:700; }
QTabBar::tab:selected { background:@accent_soft@; color:@accent@; }
QTabBar::tab:hover:!selected { background:@hover@; }

QLineEdit, QSpinBox, QComboBox {
    background:@input@; border:1px solid @border@; border-radius:9px;
    padding:7px 10px; min-height:20px; selection-background-color:@accent@;
    selection-color:white; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border:1px solid @accent@; }
QComboBox QAbstractItemView { background:@card@; border:1px solid @border@;
    selection-background-color:@accent_soft@; selection-color:@accent@; outline:0; }
QPlainTextEdit, QListWidget { background:@log@; border:1px solid @border@;
    border-radius:10px; padding:6px; selection-background-color:@accent_soft@;
    selection-color:@text@; }
QPlainTextEdit#log { font-family:monospace; font-size:9pt; }
QListWidget::item { padding:7px; border-radius:6px; }
QListWidget::item:selected { background:@accent_soft@; color:@accent@; }

QPushButton { background:@btn@; border:1px solid @border@; border-radius:9px;
              padding:9px 16px; font-weight:600; }
QPushButton:hover { background:@hover@; }
QPushButton:pressed { background:@border@; }
QPushButton:disabled { color:@muted@; }
QPushButton[kind="primary"] { background:@accent@; border:none; color:white;
                              font-size:11pt; padding:12px 18px; }
QPushButton[kind="primary"]:hover { background:@accent_hover@; }
QPushButton[kind="danger"] { color:@bad@; }
QPushButton[kind="danger"]:hover { background:@bad_bg@; }
QPushButton#action { text-align:left; padding:13px 16px; font-weight:500; }
QPushButton#action[kind="warn"] { border:1px solid @warn@; }
QPushButton#ghost { background:transparent; border:none; font-size:14pt;
                    padding:4px 10px; border-radius:10px; }
QPushButton#ghost:hover { background:@hover@; }

QCheckBox { spacing:8px; background:transparent; }
QCheckBox::indicator { width:18px; height:18px; border-radius:6px;
                       border:1px solid @border@; background:@input@; }
QCheckBox::indicator:checked { background:@accent@; border:1px solid @accent@; }

QProgressBar { background:@input@; border:none; border-radius:5px; }
QProgressBar#busy { max-height:3px; background:transparent; }
QProgressBar#busy::chunk { background:@accent@; }

QScrollBar:vertical { background:transparent; width:10px; margin:0; }
QScrollBar::handle:vertical { background:@border@; border-radius:5px; min-height:28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QToolTip { background:@card@; color:@text@; border:1px solid @border@; padding:5px; }
"""


def build_qss(name):
    q = QSS
    for k, v in THEMES[name].items():
        q = q.replace(f"@{k}@", v)
    return q


# ======================= Yardımcılar =======================
class Runner(QThread):
    """Komutu arka planda çalıştırır, arayüzü dondurmaz."""
    finished_cmd = pyqtSignal(str, int, str)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        try:
            p = subprocess.run(self.cmd, capture_output=True, text=True, timeout=120)
            out = (p.stdout or "") + (p.stderr or "")
            self.finished_cmd.emit(" ".join(self.cmd), p.returncode, out.strip())
        except FileNotFoundError:
            self.finished_cmd.emit(" ".join(self.cmd), 127,
                                   f"'{self.cmd[0]}' bulunamadı. Paketi kurun.")
        except Exception as e:  # noqa
            self.finished_cmd.emit(" ".join(self.cmd), 1, str(e))


def run_sync(cmd, c_locale=False):
    env = None
    if c_locale:
        env = dict(os.environ, LC_ALL="C")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa
        return 1, str(e)


def page_count(path):
    """PDF sayfa sayısını döndürür, bulunamazsa None."""
    if not path.lower().endswith(".pdf"):
        return None
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages)
    except Exception:
        pass
    code, out = run_sync(["pdfinfo", path])
    if code == 0:
        for line in out.splitlines():
            if line.startswith("Pages:"):
                try:
                    return int(line.split()[1])
                except ValueError:
                    pass
    return None


def parse_ranges(text, total=None):
    """'1-5,8,11-13', '5-', '-3' gibi metni sıralı, tekrarsız sayfa listesine çevirir."""
    pages = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            if (a and not a.isdigit()) or (b and not b.isdigit()):
                raise ValueError(f"Geçersiz aralık: '{part}'")
            start = int(a) if a else 1
            if b:
                end = int(b)
            elif total:
                end = total
            else:
                raise ValueError(f"'{part}' için toplam sayfa sayısı bilinmiyor; "
                                 "bitiş sayfasını yazın (örn: 5-12).")
        else:
            if not part.isdigit():
                raise ValueError(f"Geçersiz sayfa: '{part}'")
            start = end = int(part)
        if start < 1 or end < start:
            raise ValueError(f"Geçersiz aralık: '{part}'")
        if total and end > total:
            raise ValueError(f"Belge {total} sayfa; '{part}' sınırı aşıyor.")
        pages.update(range(start, end + 1))
    if not pages:
        raise ValueError("Sayfa seçilmedi.")
    return sorted(pages)


def format_ranges(pages):
    """[1,2,3,5,7,8] -> '1-3,5,7-8'"""
    out, i = [], 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1:
            j += 1
        out.append(str(pages[i]) if i == j else f"{pages[i]}-{pages[j]}")
        i = j + 1
    return ",".join(out)


INK_NAMES = r"(Photo Black|Matte Black|Light Cyan|Light Magenta|Black|Cyan|Magenta|Yellow)"


def parse_ink(text):
    """escputil -i çıktısından {renk: yüzde} çıkarır. Başarısızsa boş sözlük."""
    levels = {}
    lines = text.splitlines()
    # Tablo biçimi: isimler bir satırda, değerler alttaki satırda
    for i, line in enumerate(lines[:-1]):
        names = re.findall(INK_NAMES, line, re.I)
        nums = re.findall(r"\d{1,3}", lines[i + 1])
        if len(names) >= 2 and len(names) == len(nums):
            return {n.title(): min(int(v), 100) for n, v in zip(names, nums)}
    # "Black: 85%" biçimi
    for m in re.finditer(INK_NAMES + r"\D{0,15}?(\d{1,3})", text, re.I):
        levels[m.group(1).title()] = min(int(m.group(2)), 100)
    return levels


INK_COLORS = {
    "black": "#6B7280", "photo black": "#6B7280", "matte black": "#6B7280",
    "cyan": "#06B6D4", "light cyan": "#67E8F9",
    "magenta": "#EC4899", "light magenta": "#F9A8D4", "yellow": "#EAB308",
}
INK_TR = {"black": "Siyah", "cyan": "Camgöbeği", "magenta": "Macenta", "yellow": "Sarı"}


# ======================= Bileşenler =======================
class Card(QFrame):
    def __init__(self, title=None, subtitle=None):
        super().__init__()
        self.setObjectName("card")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(18, 16, 18, 18)
        self.v.setSpacing(12)
        if title:
            t = QLabel(title)
            t.setObjectName("cardTitle")
            self.v.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("muted")
            s.setWordWrap(True)
            self.v.addWidget(s)


def field(label, widget):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(5)
    l = QLabel(label)
    l.setObjectName("fieldLabel")
    v.addWidget(l)
    v.addWidget(widget)
    return w


def set_prop(widget, name, value):
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def make_button(text, kind=None, slot=None):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    if kind:
        b.setProperty("kind", kind)
    if slot:
        b.clicked.connect(slot)
    return b


def action_button(icon, title, desc, slot, kind=None):
    b = QPushButton(f"{ic(icon)}{title}\n{desc}")
    b.setObjectName("action")
    b.setCursor(Qt.PointingHandCursor)
    b.setMinimumHeight(70)
    if kind:
        b.setProperty("kind", kind)
    b.clicked.connect(slot)
    return b


class InkPanel(Card):
    def __init__(self):
        super().__init__("Mürekkep seviyeleri")
        self.note = QLabel("Görmek için 'Mürekkep seviyesi' düğmesine basın.")
        self.note.setObjectName("muted")
        self.v.addWidget(self.note)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(8)
        self.v.addLayout(self.rows)

    def set_levels(self, levels):
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not levels:
            self.note.setText("Çıktı çözümlenemedi. Ham sonuç günlükte görünür.")
            self.note.show()
            return
        self.note.hide()
        for name, pct in levels.items():
            key = name.lower()
            color = INK_COLORS.get(key, "#9CA3AF")
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            n = QLabel(INK_TR.get(key, name))
            n.setFixedWidth(100)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(pct)
            bar.setTextVisible(False)
            bar.setFixedHeight(12)
            bar.setStyleSheet(
                f"QProgressBar::chunk {{ background:{color}; border-radius:5px; }}")
            p = QLabel(f"%{pct}")
            p.setFixedWidth(46)
            p.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            h.addWidget(n)
            h.addWidget(bar, 1)
            h.addWidget(p)
            self.rows.addWidget(row)


# ======================= Ana pencere =======================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle("Epson L210 Panel TeknikServet")
        self.resize(780, 820)
        self.setAcceptDrops(True)
        self.workers = []

        pal = QApplication.palette().window().color()
        self.theme = "dark" if pal.lightness() < 128 else "light"

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 16)
        root.setSpacing(12)

        # --- Başlık ---
        head = QHBoxLayout()
        tv = QVBoxLayout()
        tv.setSpacing(0)
        title = QLabel(f"{ic('🖨')}Epson L210")
        title.setObjectName("title")
        sub = QLabel("Yazdırma ve bakım paneli")
        sub.setObjectName("subtitle")
        tv.addWidget(title)
        tv.addWidget(sub)
        head.addLayout(tv)
        head.addStretch(1)
        self.chip = QLabel("● Bilinmiyor")
        self.chip.setObjectName("chip")
        head.addWidget(self.chip)
        self.theme_btn = QPushButton("☾" if self.theme == "light" else "☀")
        self.theme_btn.setObjectName("ghost")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setToolTip("Açık / koyu tema")
        self.theme_btn.clicked.connect(self.toggle_theme)
        head.addWidget(self.theme_btn)
        root.addLayout(head)

        self.busy = QProgressBar()
        self.busy.setObjectName("busy")
        self.busy.setRange(0, 0)
        self.busy.setTextVisible(False)
        self.busy.hide()
        root.addWidget(self.busy)

        # --- Yazıcı seçimi ---
        pc = Card()
        pr = QHBoxLayout()
        self.printer = QComboBox()
        self.printer.currentTextChanged.connect(self.on_printer_changed)
        pr.addWidget(field("YAZICI", self.printer), 1)
        rb = make_button(f"{ic('⟳')}Yenile", slot=self.load_printers)
        pr.addWidget(rb, 0, Qt.AlignBottom)
        pc.v.addLayout(pr)
        root.addWidget(pc)

        # --- Sekmeler ---
        tabs = QTabWidget()
        tabs.addTab(self.build_print_tab(), f"{ic('🖨')}Yazdır")
        tabs.addTab(self.build_maint_tab(), f"{ic('🛠')}Bakım")
        tabs.addTab(self.build_queue_tab(), f"{ic('📋')}Kuyruk")
        root.addWidget(tabs, 1)

        # --- Günlük ---
        lh = QHBoxLayout()
        ll = QLabel("Günlük")
        ll.setObjectName("fieldLabel")
        lh.addWidget(ll)
        lh.addStretch(1)
        clr = make_button("Temizle", slot=lambda: self.log.clear())
        clr.setStyleSheet("padding:3px 12px; font-size:9pt;")
        lh.addWidget(clr)
        root.addLayout(lh)
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
        root.addWidget(self.log)

        self.load_printers()
        self.detect_device()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(5000)

    # ---------- Tema ----------
    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        QApplication.instance().setStyleSheet(build_qss(self.theme))
        self.theme_btn.setText("☾" if self.theme == "light" else "☀")

    # ---------- Sürükle bırak ----------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.file_edit.setText(urls[0].toLocalFile())
            self.update_page_count()

    # ---------- Yazdır sekmesi ----------
    def build_print_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        fc = Card("Dosya", "Bir dosyayı pencereye sürükleyip bırakabilirsiniz.")
        row = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("PDF, resim veya metin dosyası...")
        self.file_edit.editingFinished.connect(self.update_page_count)
        row.addWidget(self.file_edit, 1)
        row.addWidget(make_button(f"{ic('📂')}Gözat", slot=self.browse))
        fc.v.addLayout(row)
        self.count_label = QLabel("")
        self.count_label.setObjectName("muted")
        fc.v.addWidget(self.count_label)
        lay.addWidget(fc)

        sc = Card("Ayarlar")
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(12)

        self.paper = QComboBox()
        self.paper.addItems(["A4", "A5", "Letter", "Legal", "A6"])
        self.quality = QComboBox()
        self.quality.addItems(["Normal", "Taslak (hızlı, az mürekkep)", "Yüksek"])
        self.color = QComboBox()
        self.color.addItems(["Renkli", "Siyah-beyaz"])
        self.copies = QSpinBox()
        self.copies.setRange(1, 99)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("1-5,8,11-13 veya 5-  (boş = tümü)")
        self.pages.setToolTip("Virgülle ayırın. '5-' 5. sayfadan sona kadar demektir "
                              "(PDF'lerde sayfa sayısı otomatik bulunur).")
        self.duplex = QComboBox()
        self.duplex.addItems(["Tek yüze", "Çift yüze (manuel)"])
        self.duplex.currentIndexChanged.connect(
            lambda i: self.duplex_box.setVisible(i == 1))

        g.addWidget(field("KAĞIT BOYUTU", self.paper), 0, 0)
        g.addWidget(field("KALİTE", self.quality), 0, 1)
        g.addWidget(field("RENK", self.color), 1, 0)
        g.addWidget(field("KOPYA", self.copies), 1, 1)
        g.addWidget(field("SAYFA ARALIĞI", self.pages), 2, 0, 1, 2)
        g.addWidget(field("YAZDIRMA ŞEKLİ", self.duplex), 3, 0, 1, 2)
        sc.v.addLayout(g)

        self.duplex_box = QFrame()
        self.duplex_box.setObjectName("drop")
        dv = QVBoxLayout(self.duplex_box)
        dv.setContentsMargins(14, 12, 14, 12)
        info = QLabel("L210 otomatik çift yüz yapamaz. Önce ön yüzler basılır, "
                      "sonra kağıdı çevirip tekrar yerleştirirsiniz, ardından arka "
                      "yüzler basılır.")
        info.setObjectName("muted")
        info.setWordWrap(True)
        dv.addWidget(info)
        self.reverse_even = QCheckBox("Arka yüz sayfalarını ters sırada yazdır")
        self.reverse_even.setToolTip(
            "Sayfalar ters sırada geliyorsa bu seçeneği değiştirin.\n"
            "Önce 2-4 sayfalık bir aralıkla deneyin.")
        dv.addWidget(self.reverse_even)
        self.duplex_box.hide()
        sc.v.addWidget(self.duplex_box)
        lay.addWidget(sc)

        pb = make_button(f"{ic('🖨')}Yazdır", "primary", self.do_print)
        lay.addWidget(pb)
        lay.addStretch(1)
        return w

    def browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "Dosya seç", os.path.expanduser("~"))
        if f:
            self.file_edit.setText(f)
            self.update_page_count()

    def update_page_count(self):
        f = self.file_edit.text().strip()
        n = page_count(f) if os.path.isfile(f) else None
        self.count_label.setText(f"Belge sayfa sayısı: {n}" if n else "")

    def base_args(self):
        args = ["lp", "-d", self.printer.currentText(),
                "-o", f"media={self.paper.currentText()}"]
        q = self.quality.currentIndex()
        args += ["-o", {0: "print-quality=4", 1: "print-quality=3", 2: "print-quality=5"}[q]]
        if self.color.currentIndex() == 1:
            args += ["-o", "print-color-mode=monochrome"]
        return args

    def do_print(self):
        f = self.file_edit.text().strip()
        if not f or not os.path.isfile(f):
            QMessageBox.warning(self, "Hata", "Geçerli bir dosya seçin.")
            return
        if not self.printer.currentText():
            QMessageBox.warning(self, "Hata", "Yazıcı bulunamadı.")
            return

        base = self.base_args()
        n = self.copies.value()
        total = page_count(f)
        text = self.pages.text().strip()

        sel = None
        try:
            if text:
                sel = parse_ranges(text, total)
            elif total:
                sel = list(range(1, total + 1))
        except ValueError as e:
            QMessageBox.warning(self, "Sayfa aralığı hatası", str(e))
            return

        if self.duplex.currentIndex() == 0:
            args = base + ["-n", str(n)]
            if sel:
                args += ["-o", f"page-ranges={format_ranges(sel)}"]
            self.run_cmd(args + [f])
            return

        # Manuel çift yüz: ön yüzler = 1., 3., 5. seçili sayfa; arka yüzler = 2., 4., 6.
        if sel:
            front, back = sel[0::2], sel[1::2]
            front_opts = ["-o", f"page-ranges={format_ranges(front)}"]
            back_opts = ["-o", f"page-ranges={format_ranges(back)}"] if back else None
        else:
            front_opts = ["-o", "page-set=odd"]
            back_opts = ["-o", "page-set=even"]

        for i in range(n):
            code, out = run_sync(base + front_opts + [f])
            self.log.appendPlainText(f"$ [ön yüzler] {out.strip()}")
            if code != 0:
                QMessageBox.critical(self, "Hata", out)
                return
            if back_opts is None:
                self.log.appendPlainText("Tek sayfa seçildi, çevirmeye gerek yok.")
                continue
            r = QMessageBox.information(
                self, f"Kopya {i + 1}/{n} - Kağıdı çevirin",
                "Ön yüzlerin basımının BİTTİĞİNDEN emin olun.\n\n"
                "1) Çıkan kağıt destesini alın.\n"
                "2) Desteyi uzun kenarından çevirin (boş yüz basılacak yüz olsun).\n"
                "3) Arka tepsiye geri yerleştirin.\n\n"
                "Hazır olunca Tamam'a basın.",
                QMessageBox.Ok | QMessageBox.Cancel)
            if r != QMessageBox.Ok:
                self.log.appendPlainText("İptal edildi.")
                return
            extra = list(back_opts)
            if self.reverse_even.isChecked():
                extra += ["-o", "outputorder=reverse"]
            code, out = run_sync(base + extra + [f])
            self.log.appendPlainText(f"$ [arka yüzler] {out.strip()}")
            if code != 0:
                QMessageBox.critical(self, "Hata", out)
                return

    # ---------- Bakım sekmesi ----------
    def build_maint_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        dc = Card("Aygıt", "Boş bırakırsanız yazıcı CUPS adıyla kullanılır.")
        dg = QHBoxLayout()
        self.device = QLineEdit()
        self.device.setPlaceholderText("/dev/usb/lp0")
        self.extra = QLineEdit()
        self.extra.setPlaceholderText("örn: -m l210")
        dg.addWidget(field("HAM AYGIT", self.device), 1)
        dg.addWidget(field("EK PARAMETRE", self.extra), 1)
        dc.v.addLayout(dg)
        lay.addWidget(dc)

        self.ink = InkPanel()
        lay.addWidget(self.ink)

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(action_button(
            "💧", "Mürekkep seviyesi", "Kalan mürekkebi göster",
            lambda: self.escp(["-i"])), 0, 0)
        grid.addWidget(action_button(
            "🔍", "Ağız (nozzle) testi", "Eksik çizgi var mı kontrol et",
            lambda: self.escp(["-n"])), 0, 1)
        grid.addWidget(action_button(
            "🧼", "Kafa temizleme", "Mürekkep harcar, gerekirse kullanın",
            lambda: self.escp(["-c"], confirm=True), "warn"), 1, 0)
        grid.addWidget(action_button(
            "ℹ", "Yazıcı durumu", "escputil durum bilgisi",
            lambda: self.escp(["-s"])), 1, 1)
        grid.addWidget(action_button(
            "📄", "Test sayfası yazdır", "CUPS test sayfasını gönder",
            self.test_page), 2, 0, 1, 2)
        lay.addLayout(grid)

        note = QLabel("İpucu: Önce ağız testi yapın. Çizgiler eksikse temizleyin, "
                      "arka arkaya en fazla 2-3 kez tekrarlayın.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        lay.addWidget(note)
        lay.addStretch(1)
        return w

    def detect_device(self):
        devs = sorted(glob.glob("/dev/usb/lp*"))
        if devs:
            self.device.setText(devs[0])

    def escp(self, flags, confirm=False):
        if confirm:
            r = QMessageBox.question(
                self, "Onay", "Kafa temizleme mürekkep harcar. Devam edilsin mi?")
            if r != QMessageBox.Yes:
                return
        cmd = ["escputil"]
        dev = self.device.text().strip()
        if dev:
            cmd += ["-r", dev]
        else:
            cmd += ["-P", self.printer.currentText()]
        cmd += ["-u"] + flags
        if self.extra.text().strip():
            cmd += self.extra.text().split()
        self.run_cmd(cmd)

    def test_page(self):
        tp = "/usr/share/cups/data/testprint"
        if not os.path.exists(tp):
            QMessageBox.warning(self, "Hata", "CUPS test sayfası bulunamadı.")
            return
        self.run_cmd(["lp", "-d", self.printer.currentText(), tp])

    # ---------- Kuyruk sekmesi ----------
    def build_queue_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        jc = Card("Yazdırma kuyruğu")
        self.jobs = QListWidget()
        self.jobs.setMinimumHeight(150)
        jc.v.addWidget(self.jobs, 1)
        row = QHBoxLayout()
        row.addWidget(make_button(f"{ic('⟳')}Yenile", slot=self.refresh_jobs))
        row.addWidget(make_button("Seçili işi iptal et", "danger", self.cancel_selected))
        row.addWidget(make_button("Tümünü iptal et", "danger", self.cancel_all))
        row.addStretch(1)
        jc.v.addLayout(row)
        lay.addWidget(jc, 1)

        sc = Card("Yazıcı durumu")
        self.status = QPlainTextEdit()
        self.status.setReadOnly(True)
        self.status.setMaximumHeight(110)
        sc.v.addWidget(self.status)
        sc.v.addWidget(make_button(f"{ic('▶')}Yazıcıyı etkinleştir / devam ettir",
                                   slot=self.enable_printer))
        lay.addWidget(sc)
        return w

    def refresh_jobs(self):
        self.jobs.clear()
        p = self.printer.currentText()
        _, out = run_sync(["lpstat", "-o", p])
        for line in out.strip().splitlines():
            if line.strip():
                self.jobs.addItem(line)
        if self.jobs.count() == 0:
            self.jobs.addItem("Kuyrukta iş yok.")
        _, st = run_sync(["lpstat", "-p", p, "-l"])
        self.status.setPlainText(st.strip())

    def cancel_selected(self):
        it = self.jobs.currentItem()
        if not it or " " not in it.text():
            return
        self.run_cmd(["cancel", it.text().split()[0]])
        QTimer.singleShot(800, self.refresh_jobs)

    def cancel_all(self):
        self.run_cmd(["cancel", "-a", self.printer.currentText()])
        QTimer.singleShot(800, self.refresh_jobs)

    def enable_printer(self):
        p = self.printer.currentText()
        self.run_cmd(["cupsenable", p])
        self.run_cmd(["cupsaccept", p])
        QTimer.singleShot(800, self.refresh_status)

    # ---------- Durum çipi ----------
    def refresh_status(self):
        p = self.printer.currentText()
        if not p:
            self.set_chip("Yazıcı yok", "bad")
            return
        code, out = run_sync(["lpstat", "-p", p], c_locale=True)
        t = out.lower()
        if code != 0:
            self.set_chip("Bilinmiyor", "")
        elif "disabled" in t:
            self.set_chip("Devre dışı", "bad")
        elif "now printing" in t or "processing" in t:
            self.set_chip("Yazdırıyor", "busy")
        elif "idle" in t:
            self.set_chip("Hazır", "ok")
        else:
            self.set_chip("Bilinmiyor", "")

    def set_chip(self, text, state):
        self.chip.setText(f"●  {text}")
        set_prop(self.chip, "state", state)

    def on_printer_changed(self, _):
        self.refresh_status()

    # ---------- Ortak ----------
    def load_printers(self):
        self.printer.blockSignals(True)
        self.printer.clear()
        _, out = run_sync(["lpstat", "-e"])
        names = [l.strip() for l in out.splitlines() if l.strip()]
        names.sort(key=lambda n: ("l210" not in n.lower(), n))
        self.printer.addItems(names)
        self.printer.blockSignals(False)
        if not names:
            self.log.appendPlainText(
                "Yazıcı bulunamadı. CUPS çalışıyor mu? (systemctl status cups)")
        self.refresh_status()

    def run_cmd(self, cmd):
        self.log.appendPlainText("$ " + " ".join(cmd))
        r = Runner(cmd)
        r.finished_cmd.connect(self.on_done)
        r.finished.connect(lambda r=r: self.worker_finished(r))
        self.workers.append(r)
        self.busy.show()
        r.start()

    def worker_finished(self, r):
        if r in self.workers:
            self.workers.remove(r)
        if not self.workers:
            self.busy.hide()

    def on_done(self, cmd, code, out):
        self.log.appendPlainText(out if out else "(çıktı yok)")
        if code != 0:
            self.log.appendPlainText(f"[çıkış kodu: {code}]")
        elif cmd.startswith("escputil") and " -i" in cmd:
            self.ink.set_levels(parse_ink(out))


if __name__ == "__main__":
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    app.setStyleSheet(build_qss(w.theme))
    w.show()
    sys.exit(app.exec_())

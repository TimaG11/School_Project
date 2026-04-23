import json
import math
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from PySide6 import QtCore, QtGui, QtWidgets

Point = Tuple[int, int]

IDEAL_AMMETER_R = 1e-8
IDEAL_VOLTMETER_R = 1e12

OHM_UNITS = [("Ом", 1.0), ("кОм", 1000.0)]
OHM_UNITS_FULL = [("Ом", 1.0), ("кОм", 1e3), ("МОм", 1e6), ("ГОм", 1e9)]
VOLT_UNITS = [("В", 1.0), ("кВ", 1000.0)]
WATT_UNITS = [("Вт", 1.0), ("кВт", 1000.0)]
FARAD_UNITS = [("Ф", 1.0), ("мФ", 1e-3), ("мкФ", 1e-6), ("нФ", 1e-9), ("пФ", 1e-12)]


def point_on_axis_segment(p: Point, a: Point, b: Point) -> bool:
    if a[0] == b[0] == p[0]:
        return min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
    if a[1] == b[1] == p[1]:
        return min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
    return False


def polyline_grid_length(points: List[Point]) -> int:
    total = 0
    for a, b in zip(points, points[1:]):
        total += abs(a[0] - b[0]) + abs(a[1] - b[1])
    return total


def split_polyline_at_point(points: List[Point], pt: Point) -> Optional[Tuple[List[Point], List[Point], int, int]]:
    if len(points) < 2:
        return None
    pts = list(points)
    insert_idx = None
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if not point_on_axis_segment(pt, a, b):
            continue
        if pt == a:
            insert_idx = i
        elif pt == b:
            insert_idx = i + 1
        else:
            pts = pts[:i + 1] + [pt] + pts[i + 1:]
            insert_idx = i + 1
        break
    if insert_idx is None:
        return None
    if insert_idx == 0 or insert_idx == len(pts) - 1:
        return None
    left = pts[:insert_idx + 1]
    right = pts[insert_idx:]
    if len(left) < 2 or len(right) < 2:
        return None
    return left, right, polyline_grid_length(left), polyline_grid_length(right)


# ----------------------- Formatters -----------------------
def fmt_ohms(x: float) -> str:
    x = float(x)
    if math.isinf(x):
        return "∞ Ω"
    ax = abs(x)
    if ax >= 1e9:
        return f"{x/1e9:.6g} GΩ"
    if ax >= 1e6:
        return f"{x/1e6:.6g} MΩ"
    if ax >= 1e3:
        return f"{x/1e3:.6g} kΩ"
    return f"{x:.6g} Ω"


def fmt_volts(x: float) -> str:
    x = float(x)
    if math.isinf(x):
        return "∞ V"
    ax = abs(x)
    if ax >= 1e3:
        return f"{x/1e3:.6g} kV"
    return f"{x:.6g} V"


def fmt_amps(x: float) -> str:
    x = float(x)
    if math.isinf(x):
        return "∞ A"
    ax = abs(x)
    if ax >= 1:
        return f"{x:.6g} A"
    if ax >= 1e-3:
        return f"{x*1e3:.6g} mA"
    if ax >= 1e-6:
        return f"{x*1e6:.6g} µA"
    return f"{x:.6g} A"


def fmt_watts(x: float) -> str:
    x = float(x)
    if math.isinf(x):
        return "∞ W"
    ax = abs(x)
    if ax >= 1e3:
        return f"{x/1e3:.6g} kW"
    if ax >= 1:
        return f"{x:.6g} W"
    if ax >= 1e-3:
        return f"{x*1e3:.6g} mW"
    if ax >= 1e-6:
        return f"{x*1e6:.6g} µW"
    return f"{x:.6g} W"


def fmt_farads(x: float) -> str:
    x = float(x)
    if math.isinf(x):
        return "∞ F"
    ax = abs(x)
    if ax >= 1:
        return f"{x:.6g} F"
    if ax >= 1e-3:
        return f"{x*1e3:.6g} mF"
    if ax >= 1e-6:
        return f"{x*1e6:.6g} µF"
    if ax >= 1e-9:
        return f"{x*1e9:.6g} nF"
    if ax >= 1e-12:
        return f"{x*1e12:.6g} pF"
    return f"{x:.6g} F"


def fmt_coulombs(x: float) -> str:
    x = float(x)
    if math.isinf(x):
        return "∞ C"
    ax = abs(x)
    if ax >= 1:
        return f"{x:.6g} C"
    if ax >= 1e-3:
        return f"{x*1e3:.6g} mC"
    if ax >= 1e-6:
        return f"{x*1e6:.6g} µC"
    if ax >= 1e-9:
        return f"{x*1e9:.6g} nC"
    return f"{x:.6g} C"


def fmt_joules(x: float) -> str:
    x = float(x)
    if math.isinf(x):
        return "∞ J"
    ax = abs(x)
    if ax >= 1:
        return f"{x:.6g} J"
    if ax >= 1e-3:
        return f"{x*1e3:.6g} mJ"
    if ax >= 1e-6:
        return f"{x*1e6:.6g} µJ"
    return f"{x:.6g} J"


def fmt_optional_value(x: Optional[float], kind: str) -> str:
    if x is None:
        return "?"
    if kind == "ohms":
        return fmt_ohms(x)
    if kind == "volts":
        return fmt_volts(x)
    if kind == "amps":
        return fmt_amps(x)
    if kind == "watts":
        return fmt_watts(x)
    if kind == "farads":
        return fmt_farads(x)
    if kind == "coulombs":
        return fmt_coulombs(x)
    if kind == "joules":
        return fmt_joules(x)
    return f"{x:.6g}"


def analysis_strings(an: Optional[Dict[str, Optional[float]]]) -> Tuple[str, str, str]:
    if not an:
        return "?", "?", "?"
    return (
        fmt_optional_value(an.get("I"), "amps"),
        fmt_optional_value(an.get("V"), "volts"),
        fmt_optional_value(an.get("P"), "watts"),
    )


# ----------------------- Linear solver -----------------------
def gauss_solve(A: List[List[float]], b: List[float], eps: float = 1e-12) -> List[float]:
    n = len(b)
    if n == 0:
        return []
    aug = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < eps:
            raise ValueError("Singular matrix")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= pv
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if abs(factor) < eps:
                continue
            for j in range(col, n + 1):
                aug[r][j] -= factor * aug[col][j]
    return [aug[i][n] for i in range(n)]


# ----------------------- Param model -----------------------
@dataclass
class ParamValue:
    mode: str = "value"  # "value" | "var"
    value: float = 0.0   # base units
    var: str = "x"

    def is_var(self) -> bool:
        return self.mode == "var"

    def numeric(self) -> Optional[float]:
        return None if self.is_var() else float(self.value)


def format_param(p: ParamValue, kind: str) -> str:
    if p.is_var():
        return p.var
    if kind == "ohms":
        return fmt_ohms(p.value)
    if kind == "volts":
        return fmt_volts(p.value)
    if kind == "watts":
        return fmt_watts(p.value)
    if kind == "farads":
        return fmt_farads(p.value)
    return f"{p.value:.6g}"


# ----------------------- Color / theme helpers -----------------------
COLOR_NAMES = ["default", "yellow", "cyan", "red", "green"]


def make_bulb_icon(filled: bool, dark: bool) -> QtGui.QIcon:
    pm = QtGui.QPixmap(20, 20)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing)

    if dark:
        fg = QtGui.QColor(240, 220, 80) if filled else QtGui.QColor(200, 210, 240)
        outline = QtGui.QColor(200, 210, 240)
    else:
        fg = QtGui.QColor(30, 30, 30) if not filled else QtGui.QColor(220, 180, 0)
        outline = QtGui.QColor(30, 30, 30)

    pen = QtGui.QPen(outline, 2)
    p.setPen(pen)
    if filled:
        p.setBrush(QtGui.QBrush(fg))
    else:
        p.setBrush(QtCore.Qt.NoBrush)

    p.drawEllipse(QtCore.QRectF(4, 2, 12, 12))
    p.drawRoundedRect(QtCore.QRectF(7, 13, 6, 4), 1.5, 1.5)

    p.end()
    return QtGui.QIcon(pm)


class NoWheelComboBox(QtWidgets.QComboBox):
    def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
        e.ignore()


class NoWheelDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
        e.ignore()


# ----------------------- Param widgets/dialog -----------------------
class ParamInputWidget(QtWidgets.QWidget):
    def __init__(
        self,
        units: List[Tuple[str, float]],
        default_value_base: float,
        default_unit_name: str,
        default_mode: str = "value",
        default_var: str = "x",
        parent=None,
    ):
        super().__init__(parent)
        self._units = [(n, float(m)) for n, m in units]

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.mode = NoWheelComboBox()
        self.mode.addItem("число", "value")
        self.mode.addItem("переменная", "var")
        lay.addWidget(self.mode, 0)

        self.stack = QtWidgets.QStackedWidget()
        lay.addWidget(self.stack, 1)

        w_num = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(w_num)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)

        self.spin = NoWheelDoubleSpinBox()
        self.spin.setRange(0.0, 1e12)
        self.spin.setDecimals(6)
        self.spin.setSingleStep(0.1)

        self.unit = NoWheelComboBox()
        for name, mult in self._units:
            self.unit.addItem(name, mult)

        hl.addWidget(self.spin, 1)
        hl.addWidget(self.unit, 0)
        self.stack.addWidget(w_num)

        w_var = QtWidgets.QWidget()
        hl2 = QtWidgets.QHBoxLayout(w_var)
        hl2.setContentsMargins(0, 0, 0, 0)
        hl2.setSpacing(6)
        self.var_edit = QtWidgets.QLineEdit()
        self.var_edit.setPlaceholderText("имя переменной (например R1)")
        hl2.addWidget(self.var_edit, 1)
        self.stack.addWidget(w_var)

        self.mode.currentIndexChanged.connect(self._sync_mode)

        self.set_param(
            ParamValue(mode=default_mode, value=default_value_base, var=default_var),
            prefer_unit=default_unit_name,
        )

    def _sync_mode(self) -> None:
        md = self.mode.currentData()
        self.stack.setCurrentIndex(0 if md == "value" else 1)

    def set_param(self, p: ParamValue, prefer_unit: Optional[str] = None) -> None:
        if p.mode not in ("value", "var"):
            p.mode = "value"

        if p.is_var():
            self.mode.setCurrentIndex(1)
            self.var_edit.setText(p.var or "x")
            self._sync_mode()
            return

        self.mode.setCurrentIndex(0)
        self._sync_mode()

        unit_idx = 0
        if prefer_unit is not None:
            for i in range(self.unit.count()):
                if self.unit.itemText(i) == prefer_unit:
                    unit_idx = i
                    break

        self.unit.setCurrentIndex(unit_idx)
        mult = float(self.unit.currentData())
        self.spin.setValue(float(p.value) / (mult if mult else 1.0))

    def get_param(self) -> ParamValue:
        md = str(self.mode.currentData())
        if md == "var":
            name = (self.var_edit.text() or "").strip()
            if not name:
                name = "x"
            return ParamValue(mode="var", value=0.0, var=name)
        mult = float(self.unit.currentData())
        return ParamValue(mode="value", value=float(self.spin.value()) * mult, var="x")


class ParamsDialog(QtWidgets.QDialog):
    def __init__(self, title: str, fields: List[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self._widgets: Dict[str, ParamInputWidget] = {}

        root = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignRight)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        root.addLayout(form)

        for f in fields:
            key = f["key"]
            label = f["label"]
            units = f["units"]
            param: ParamValue = f["param"]
            prefer_unit = f.get("prefer_unit", None)
            default_unit = prefer_unit if prefer_unit is not None else units[0][0]

            w = ParamInputWidget(
                units=units,
                default_value_base=param.value,
                default_unit_name=default_unit,
                default_mode=param.mode,
                default_var=param.var,
            )
            self._widgets[key] = w
            form.addRow(f"{label}:", w)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self.resize(520, 220)

    def values(self) -> Dict[str, ParamValue]:
        return {k: w.get_param() for k, w in self._widgets.items()}


class MeterParamsDialog(QtWidgets.QDialog):
    def __init__(self, title: str, ideal: bool, R: ParamValue, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        root = QtWidgets.QVBoxLayout(self)

        self.chk_ideal = QtWidgets.QCheckBox("Идеальный прибор")
        self.chk_ideal.setChecked(bool(ideal))
        root.addWidget(self.chk_ideal)

        form = QtWidgets.QFormLayout()
        root.addLayout(form)

        self.r_widget = ParamInputWidget(
            units=OHM_UNITS_FULL,
            default_value_base=R.value,
            default_unit_name="Ом",
            default_mode=R.mode,
            default_var=R.var,
        )
        form.addRow("Внутреннее сопротивление:", self.r_widget)

        self.chk_ideal.toggled.connect(self.r_widget.setDisabled)
        self.r_widget.setDisabled(self.chk_ideal.isChecked())

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self.resize(520, 180)

    def values(self) -> Tuple[bool, ParamValue]:
        return self.chk_ideal.isChecked(), self.r_widget.get_param()



class SwitchParamsDialog(QtWidgets.QDialog):
    def __init__(self, title: str, is_open: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        root = QtWidgets.QVBoxLayout(self)

        self.chk_open = QtWidgets.QCheckBox("Открыт (ток идет)")
        self.chk_open.setChecked(bool(is_open))
        root.addWidget(self.chk_open)

        hint = QtWidgets.QLabel("По логике этого приложения:\nоткрыт — ток идет, закрыт — ток не идет.")
        hint.setWordWrap(True)
        root.addWidget(hint)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self.resize(390, 150)

    def values(self) -> bool:
        return self.chk_open.isChecked()


class TextDialog(QtWidgets.QDialog):
    def __init__(self, title: str, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        lay = QtWidgets.QVBoxLayout(self)
        te = QtWidgets.QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(text)
        lay.addWidget(te)

        btn = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        btn.rejected.connect(self.reject)
        btn.accepted.connect(self.accept)
        lay.addWidget(btn)

        self.resize(760, 520)


# ----------------------- DnD payload -----------------------

@dataclass
class ToolPayload:
    tool: str

    r_mode: str = "value"
    r_value: float = 0.0
    r_var: str = "R"

    u_mode: str = "value"
    u_value: float = 0.0
    u_var: str = "U"

    p_mode: str = "value"
    p_value: float = 0.0
    p_var: str = "P"

    c_mode: str = "value"
    c_value: float = 0.0
    c_var: str = "C"

    meter_ideal: bool = False
    switch_open: bool = True

    def to_mime(self) -> QtCore.QMimeData:
        mime = QtCore.QMimeData()
        mime.setData(
            "application/x-circuit-tool",
            json.dumps(self.__dict__).encode("utf-8"),
        )
        return mime

    @staticmethod
    def from_mime(mime: QtCore.QMimeData) -> Optional["ToolPayload"]:
        if not mime.hasFormat("application/x-circuit-tool"):
            return None
        try:
            raw = bytes(mime.data("application/x-circuit-tool")).decode("utf-8")
            data = json.loads(raw) if raw else {}
            return ToolPayload(
                tool=str(data.get("tool", "")),
                r_mode=str(data.get("r_mode", "value")),
                r_value=float(data.get("r_value", 0.0)),
                r_var=str(data.get("r_var", "R")),
                u_mode=str(data.get("u_mode", "value")),
                u_value=float(data.get("u_value", 0.0)),
                u_var=str(data.get("u_var", "U")),
                p_mode=str(data.get("p_mode", "value")),
                p_value=float(data.get("p_value", 0.0)),
                p_var=str(data.get("p_var", "P")),
                c_mode=str(data.get("c_mode", "value")),
                c_value=float(data.get("c_value", 0.0)),
                c_var=str(data.get("c_var", "C")),
                meter_ideal=bool(data.get("meter_ideal", False)),
                switch_open=bool(data.get("switch_open", True)),
            )
        except Exception:
            return None

class ToolIconLabel(QtWidgets.QLabel):
    def __init__(self, pixmap: QtGui.QPixmap, payload_getter, parent=None):
        super().__init__(parent)
        self.payload_getter = payload_getter
        self.setPixmap(pixmap)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumHeight(64)
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self._drag_start_pos: Optional[QtCore.QPoint] = None

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = e.position().toPoint()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self._drag_start_pos = None
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        if self._drag_start_pos is None:
            return
        if (e.position().toPoint() - self._drag_start_pos).manhattanLength() < 10:
            return
        payload: ToolPayload = self.payload_getter()
        drag = QtGui.QDrag(self)
        drag.setMimeData(payload.to_mime())
        drag.setPixmap(self.pixmap() or QtGui.QPixmap())
        drag.setHotSpot(QtCore.QPoint((self.width() // 2), (self.height() // 2)))
        drag.exec(QtCore.Qt.CopyAction)



class ToolboxWidget(QtWidgets.QWidget):
    toggleRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dark = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        btn_toggle = QtWidgets.QPushButton("Скрыть/показать инструменты")
        btn_toggle.clicked.connect(self.toggleRequested.emit)
        layout.addWidget(btn_toggle)

        # Resistor
        res_group = QtWidgets.QGroupBox("Резистор")
        res_l = QtWidgets.QVBoxLayout(res_group)
        self.res_icon = ToolIconLabel(self._make_resistor_pixmap(), self._get_resistor_payload)
        res_l.addWidget(self.res_icon)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("R ="))
        self.res_R = ParamInputWidget(
            units=OHM_UNITS, default_value_base=1.0, default_unit_name="Ом", default_mode="value", default_var="R1"
        )
        row.addWidget(self.res_R, 1)
        res_l.addLayout(row)

        rowP = QtWidgets.QHBoxLayout()
        rowP.addWidget(QtWidgets.QLabel("P ="))
        self.res_P = ParamInputWidget(
            units=WATT_UNITS, default_value_base=0.0, default_unit_name="Вт", default_mode="value", default_var="P1"
        )
        rowP.addWidget(self.res_P, 1)
        res_l.addLayout(rowP)
        layout.addWidget(res_group)

        # Wire
        wire_group = QtWidgets.QGroupBox("Провод")
        wire_l = QtWidgets.QVBoxLayout(wire_group)
        self.wire_icon = ToolIconLabel(self._make_wire_pixmap(), self._get_wire_payload)
        wire_l.addWidget(self.wire_icon)

        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(QtWidgets.QLabel("R ="))
        self.wire_R = ParamInputWidget(
            units=OHM_UNITS, default_value_base=0.0, default_unit_name="Ом", default_mode="value", default_var="Rw"
        )
        row2.addWidget(self.wire_R, 1)
        wire_l.addLayout(row2)

        row2P = QtWidgets.QHBoxLayout()
        row2P.addWidget(QtWidgets.QLabel("P ="))
        self.wire_P = ParamInputWidget(
            units=WATT_UNITS, default_value_base=0.0, default_unit_name="Вт", default_mode="value", default_var="Pw"
        )
        row2P.addWidget(self.wire_P, 1)
        wire_l.addLayout(row2P)
        layout.addWidget(wire_group)

        # Source
        source_group = QtWidgets.QGroupBox("Источник")
        source_l = QtWidgets.QVBoxLayout(source_group)
        self.source_icon = ToolIconLabel(self._make_source_pixmap(), self._get_source_payload)
        source_l.addWidget(self.source_icon)

        row3 = QtWidgets.QHBoxLayout()
        row3.addWidget(QtWidgets.QLabel("r ="))
        self.src_r = ParamInputWidget(
            units=OHM_UNITS, default_value_base=0.0, default_unit_name="Ом", default_mode="value", default_var="r"
        )
        row3.addWidget(self.src_r, 1)
        source_l.addLayout(row3)

        row4 = QtWidgets.QHBoxLayout()
        row4.addWidget(QtWidgets.QLabel("U ="))
        self.src_u = ParamInputWidget(
            units=VOLT_UNITS, default_value_base=1.0, default_unit_name="В", default_mode="value", default_var="U"
        )
        row4.addWidget(self.src_u, 1)
        source_l.addLayout(row4)

        row5 = QtWidgets.QHBoxLayout()
        row5.addWidget(QtWidgets.QLabel("P ="))
        self.src_P = ParamInputWidget(
            units=WATT_UNITS, default_value_base=0.0, default_unit_name="Вт", default_mode="value", default_var="Ps"
        )
        row5.addWidget(self.src_P, 1)
        source_l.addLayout(row5)
        layout.addWidget(source_group)

        # Ammeter
        am_group = QtWidgets.QGroupBox("Амперметр")
        am_l = QtWidgets.QVBoxLayout(am_group)
        self.am_icon = ToolIconLabel(self._make_meter_pixmap("A"), self._get_ammeter_payload)
        am_l.addWidget(self.am_icon)

        self.am_ideal = QtWidgets.QCheckBox("Идеальный")
        self.am_ideal.setChecked(True)
        am_l.addWidget(self.am_ideal)

        am_row = QtWidgets.QHBoxLayout()
        am_row.addWidget(QtWidgets.QLabel("r ="))
        self.am_R = ParamInputWidget(
            units=OHM_UNITS_FULL, default_value_base=1.0, default_unit_name="Ом", default_mode="value", default_var="RA"
        )
        am_row.addWidget(self.am_R, 1)
        am_l.addLayout(am_row)
        self.am_ideal.toggled.connect(self.am_R.setDisabled)
        self.am_R.setDisabled(True)
        layout.addWidget(am_group)

        # Voltmeter
        vm_group = QtWidgets.QGroupBox("Вольтметр")
        vm_l = QtWidgets.QVBoxLayout(vm_group)
        self.vm_icon = ToolIconLabel(self._make_meter_pixmap("V"), self._get_voltmeter_payload)
        vm_l.addWidget(self.vm_icon)

        self.vm_ideal = QtWidgets.QCheckBox("Идеальный")
        self.vm_ideal.setChecked(True)
        vm_l.addWidget(self.vm_ideal)

        vm_row = QtWidgets.QHBoxLayout()
        vm_row.addWidget(QtWidgets.QLabel("r ="))
        self.vm_R = ParamInputWidget(
            units=OHM_UNITS_FULL, default_value_base=1e6, default_unit_name="МОм", default_mode="value", default_var="RV"
        )
        vm_row.addWidget(self.vm_R, 1)
        vm_l.addLayout(vm_row)
        self.vm_ideal.toggled.connect(self.vm_R.setDisabled)
        self.vm_R.setDisabled(True)
        layout.addWidget(vm_group)

        # Capacitor
        cap_group = QtWidgets.QGroupBox("Конденсатор")
        cap_l = QtWidgets.QVBoxLayout(cap_group)
        self.cap_icon = ToolIconLabel(self._make_capacitor_pixmap(), self._get_capacitor_payload)
        cap_l.addWidget(self.cap_icon)

        cap_row = QtWidgets.QHBoxLayout()
        cap_row.addWidget(QtWidgets.QLabel("C ="))
        self.cap_C = ParamInputWidget(
            units=FARAD_UNITS, default_value_base=1e-6, default_unit_name="мкФ", default_mode="value", default_var="C1"
        )
        cap_row.addWidget(self.cap_C, 1)
        cap_l.addLayout(cap_row)

        cap_hint = QtWidgets.QLabel("В расчете по постоянному току: \
в установившемся режиме ток через него не идет")
        cap_hint.setWordWrap(True)
        cap_l.addWidget(cap_hint)
        layout.addWidget(cap_group)

        # Switch
        switch_group = QtWidgets.QGroupBox("Ключ")
        switch_l = QtWidgets.QVBoxLayout(switch_group)
        self.switch_icon = ToolIconLabel(self._make_switch_pixmap(True), self._get_switch_payload)
        switch_l.addWidget(self.switch_icon)

        self.key_open = QtWidgets.QCheckBox("Открыт (ток идет)")
        self.key_open.setChecked(True)
        self.key_open.toggled.connect(self._update_switch_icon)
        switch_l.addWidget(self.key_open)

        key_hint = QtWidgets.QLabel("В этом приложении:\nоткрыт — ток идет,\nзакрыт — ток не идет")
        key_hint.setWordWrap(True)
        switch_l.addWidget(key_hint)
        layout.addWidget(switch_group)

        # Node
        node_group = QtWidgets.QGroupBox("Узел")
        node_l = QtWidgets.QVBoxLayout(node_group)
        self.node_icon = ToolIconLabel(self._make_node_pixmap(), self._get_node_payload)
        node_l.addWidget(self.node_icon)
        node_hint = QtWidgets.QLabel("Ставится только на провод\nили в точку соединения")
        node_hint.setWordWrap(True)
        node_l.addWidget(node_hint)
        layout.addWidget(node_group)

        layout.addStretch(1)
        self.apply_theme(False)

    def apply_theme(self, dark: bool) -> None:
        self._dark = bool(dark)
        self.res_icon.setPixmap(self._make_resistor_pixmap())
        self.wire_icon.setPixmap(self._make_wire_pixmap())
        self.source_icon.setPixmap(self._make_source_pixmap())
        self.am_icon.setPixmap(self._make_meter_pixmap("A"))
        self.vm_icon.setPixmap(self._make_meter_pixmap("V"))
        self.cap_icon.setPixmap(self._make_capacitor_pixmap())
        self._update_switch_icon()
        self.node_icon.setPixmap(self._make_node_pixmap())

    def _update_switch_icon(self) -> None:
        self.switch_icon.setPixmap(self._make_switch_pixmap(self.key_open.isChecked()))

    def _tool_color(self) -> QtGui.QColor:
        if self._dark:
            return QtGui.QColor(240, 220, 80)
        return QtGui.QColor(0, 0, 0)

    def _get_resistor_payload(self) -> ToolPayload:
        R = self.res_R.get_param()
        P = self.res_P.get_param()
        return ToolPayload(
            tool="resistor",
            r_mode=R.mode, r_value=R.value, r_var=R.var,
            p_mode=P.mode, p_value=P.value, p_var=P.var,
        )

    def _get_wire_payload(self) -> ToolPayload:
        R = self.wire_R.get_param()
        P = self.wire_P.get_param()
        return ToolPayload(
            tool="wire",
            r_mode=R.mode, r_value=R.value, r_var=R.var,
            p_mode=P.mode, p_value=P.value, p_var=P.var,
        )

    def _get_source_payload(self) -> ToolPayload:
        r = self.src_r.get_param()
        u = self.src_u.get_param()
        p = self.src_P.get_param()
        return ToolPayload(
            tool="source",
            r_mode=r.mode, r_value=r.value, r_var=r.var,
            u_mode=u.mode, u_value=u.value, u_var=u.var,
            p_mode=p.mode, p_value=p.value, p_var=p.var,
        )

    def _get_ammeter_payload(self) -> ToolPayload:
        R = self.am_R.get_param()
        return ToolPayload(
            tool="ammeter",
            r_mode=R.mode, r_value=R.value, r_var=R.var,
            meter_ideal=self.am_ideal.isChecked(),
        )

    def _get_voltmeter_payload(self) -> ToolPayload:
        R = self.vm_R.get_param()
        return ToolPayload(
            tool="voltmeter",
            r_mode=R.mode, r_value=R.value, r_var=R.var,
            meter_ideal=self.vm_ideal.isChecked(),
        )

    def _get_capacitor_payload(self) -> ToolPayload:
        C = self.cap_C.get_param()
        return ToolPayload(
            tool="capacitor",
            c_mode=C.mode, c_value=C.value, c_var=C.var,
        )

    def _get_switch_payload(self) -> ToolPayload:
        return ToolPayload(tool="switch", switch_open=self.key_open.isChecked())

    def _get_node_payload(self) -> ToolPayload:
        return ToolPayload(tool="node")

    def _make_resistor_pixmap(self) -> QtGui.QPixmap:
        pm = QtGui.QPixmap(110, 60)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(self._tool_color(), 3))
        p.drawRect(25, 18, 60, 24)
        p.end()
        return pm

    def _make_wire_pixmap(self) -> QtGui.QPixmap:
        pm = QtGui.QPixmap(110, 60)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        color = self._tool_color()
        pen = QtGui.QPen(color, 5, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(22, 30, 88, 30)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(color)
        p.drawEllipse(QtCore.QPointF(22, 30), 7, 7)
        p.drawEllipse(QtCore.QPointF(88, 30), 7, 7)
        p.end()
        return pm

    def _make_source_pixmap(self) -> QtGui.QPixmap:
        pm = QtGui.QPixmap(110, 60)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(self._tool_color(), 4))
        p.drawLine(50, 15, 50, 45)
        p.drawLine(65, 22, 65, 38)
        p.end()
        return pm

    def _make_meter_pixmap(self, letter: str) -> QtGui.QPixmap:
        pm = QtGui.QPixmap(110, 60)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(self._tool_color(), 3))
        p.drawLine(18, 30, 38, 30)
        p.drawLine(72, 30, 92, 30)
        p.drawEllipse(QtCore.QRectF(38, 12, 34, 34))
        font = p.font()
        font.setBold(True)
        font.setPointSize(14)
        p.setFont(font)
        p.drawText(QtCore.QRectF(38, 12, 34, 34), QtCore.Qt.AlignCenter, letter)
        p.end()
        return pm

    def _make_capacitor_pixmap(self) -> QtGui.QPixmap:
        pm = QtGui.QPixmap(110, 60)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(self._tool_color(), 4))
        p.drawLine(18, 30, 42, 30)
        p.drawLine(68, 30, 92, 30)
        p.drawLine(46, 15, 46, 45)
        p.drawLine(64, 15, 64, 45)
        p.end()
        return pm

    def _make_switch_pixmap(self, is_open: bool) -> QtGui.QPixmap:
        pm = QtGui.QPixmap(110, 60)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        color = self._tool_color()
        p.setPen(QtGui.QPen(color, 4, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        p.setBrush(QtGui.QBrush(color))
        p.drawLine(18, 30, 42, 30)
        p.drawLine(68, 30, 92, 30)
        p.drawEllipse(QtCore.QPointF(44, 30), 3.5, 3.5)
        p.drawEllipse(QtCore.QPointF(66, 30), 3.5, 3.5)
        if is_open:
            p.drawLine(44, 30, 66, 30)
        else:
            p.drawLine(44, 30, 58, 20)
        p.end()
        return pm

    def _make_node_pixmap(self) -> QtGui.QPixmap:
        pm = QtGui.QPixmap(110, 60)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QBrush(self._tool_color()))
        p.drawEllipse(QtCore.QPointF(55, 30), 9, 9)
        p.end()
        return pm

class DraggableReportHeader(QtWidgets.QWidget):
    def __init__(self, panel: "ReportPanel"):
        super().__init__(panel)
        self._panel = panel
        self._dragging = False
        self._drag_offset = QtCore.QPoint()
        self.setCursor(QtCore.Qt.OpenHandCursor)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == QtCore.Qt.LeftButton:
            self._dragging = True
            self._drag_offset = e.position().toPoint()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        if not self._dragging:
            super().mouseMoveEvent(e)
            return
        delta = e.position().toPoint() - self._drag_offset
        new_pos = self._panel.pos() + delta
        self._panel.move_clamped(new_pos, margin=10)
        self._panel.mark_user_moved()
        e.accept()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == QtCore.Qt.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(QtCore.Qt.OpenHandCursor)
            e.accept()
            return
        super().mouseReleaseEvent(e)


class ReportPanel(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.setMinimumWidth(360)
        self._user_moved = False

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)

        self.header = DraggableReportHeader(self)
        self.header.setMinimumHeight(28)
        top = QtWidgets.QHBoxLayout(self.header)
        top.setContentsMargins(0, 0, 0, 0)

        self.title = QtWidgets.QLabel("<b>Данные схемы</b>")
        self.title.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        top.addWidget(self.title, 1)

        self.btn_close = QtWidgets.QToolButton()
        self.btn_close.setText("✕")
        self.btn_close.setAutoRaise(True)
        self.btn_close.clicked.connect(self.hide)
        top.addWidget(self.btn_close, 0, QtCore.Qt.AlignRight)

        lay.addWidget(self.header)

        self.text = QtWidgets.QLabel("")
        self.text.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.text.setWordWrap(True)
        lay.addWidget(self.text)
        self.hide()

    def mark_user_moved(self) -> None:
        self._user_moved = True

    def user_moved(self) -> bool:
        return self._user_moved

    def move_clamped(self, pos: QtCore.QPoint, margin: int = 10) -> None:
        parent = self.parentWidget()
        if parent is None:
            self.move(pos)
            return
        max_x = max(margin, parent.width() - self.width() - margin)
        max_y = max(margin, parent.height() - self.height() - margin)
        x = min(max(pos.x(), margin), max_x)
        y = min(max(pos.y(), margin), max_y)
        self.move(x, y)

    def clamp_inside_parent(self, margin: int = 10) -> None:
        self.move_clamped(self.pos(), margin)

    def apply_theme(self, dark: bool) -> None:
        if dark:
            self.setStyleSheet(
                "QFrame { background: rgba(15,23,48,235); border: 1px solid #2a3a6a; border-radius: 8px; }"
                "QLabel { color: #e8eefc; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { background: rgba(255,255,255,230); border: 1px solid #444; border-radius: 8px; }"
                "QLabel { color: #111; }"
            )

    def set_report(self, text: str) -> None:
        self.text.setText(text)
        self.show()
        self.raise_()


class SelectionDetailsPanel(QtWidgets.QFrame):
    toggled = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self._expanded = False
        self.setMinimumWidth(420)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(6)

        self.header_btn = QtWidgets.QToolButton()
        self.header_btn.setCheckable(True)
        self.header_btn.setChecked(False)
        self.header_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.header_btn.setArrowType(QtCore.Qt.RightArrow)
        self.header_btn.setText("Выделенные элементы")
        self.header_btn.clicked.connect(self._toggle_expanded)
        lay.addWidget(self.header_btn)

        self.text = QtWidgets.QTextEdit()
        self.text.setReadOnly(True)
        self.text.setMinimumHeight(140)
        self.text.setMaximumHeight(220)
        self.text.hide()
        lay.addWidget(self.text)

    def _toggle_expanded(self, checked: bool) -> None:
        self._expanded = bool(checked)
        self.header_btn.setArrowType(QtCore.Qt.DownArrow if self._expanded else QtCore.Qt.RightArrow)
        self.text.setVisible(self._expanded)
        self.toggled.emit()

    def is_expanded(self) -> bool:
        return self._expanded

    def collapsed_height(self) -> int:
        return self.header_btn.sizeHint().height() + 16

    def expanded_height(self) -> int:
        return 220

    def set_text(self, text: str) -> None:
        self.text.setPlainText(text)

    def apply_theme(self, dark: bool) -> None:
        if dark:
            self.setStyleSheet(
                "QFrame { background: rgba(15,23,48,235); border: 1px solid #2a3a6a; border-radius: 8px; }"
                "QToolButton { background: transparent; color: #e8eefc; border: none; text-align: left; font-weight: 600; padding: 2px 4px; }"
                "QTextEdit { background: #111a38; color: #e8eefc; border: 1px solid #2a3a6a; border-radius: 6px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { background: rgba(255,255,255,230); border: 1px solid #444; border-radius: 8px; }"
                "QToolButton { background: transparent; color: #111; border: none; text-align: left; font-weight: 600; padding: 2px 4px; }"
                "QTextEdit { background: white; color: #111; border: 1px solid #888; border-radius: 6px; }"
            )


# ----------------------- Scene -----------------------
class CircuitScene(QtWidgets.QGraphicsScene):
    def __init__(self, cell_size: int = 40, parent=None):
        super().__init__(parent)
        self.cell = cell_size
        self.dot_r = 3.0
        self.setSceneRect(-5000, -5000, 10000, 10000)

        self.dark_theme = False
        self._pending_proxy: Optional[QtWidgets.QGraphicsProxyWidget] = None
        self._pending_pair: Optional[Tuple["CircuitItem", "CircuitItem", Point]] = None
        self._junctions: Set[Tuple[int, int, Point]] = set()

        self._parent: Dict[int, int] = {}
        self._items_by_id: Dict[int, "CircuitItem"] = {}

        self.analysis_per_item: Dict[int, Dict[str, Optional[float]]] = {}
        self.analysis_total: Dict[str, Optional[float]] = {}
        self.analysis_vars: Dict[str, Optional[float]] = {}

    def set_theme(self, dark: bool) -> None:
        self.dark_theme = bool(dark)
        self.invalidate_analysis()
        self.update()

    def invalidate_analysis(self) -> None:
        self.analysis_per_item = {}
        self.analysis_total = {}
        self.analysis_vars = {}
        for it in self._items_by_id.values():
            it.update()

    def register_item(self, item: "CircuitItem") -> None:
        self._items_by_id[item.item_id] = item
        self._parent.setdefault(item.item_id, item.item_id)
        self.invalidate_analysis()

    def find_group(self, item_id: int) -> int:
        p = self._parent.get(item_id, item_id)
        if p != item_id:
            self._parent[item_id] = self.find_group(p)
        return self._parent.get(item_id, item_id)

    def union_groups(self, a_id: int, b_id: int) -> None:
        ra, rb = self.find_group(a_id), self.find_group(b_id)
        if ra != rb:
            self._parent[rb] = ra
        self.invalidate_analysis()

    def group_items(self, item: "CircuitItem") -> List["CircuitItem"]:
        r = self.find_group(item.item_id)
        return [it for it in self._items_by_id.values() if self.find_group(it.item_id) == r]

    def translate_group(self, leader: "CircuitItem", dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        for it in self.group_items(leader):
            it.translate_grid(dx, dy)
        self.refresh_all_junction_geometry()

    def rebuild_dsu(self) -> None:
        valid_ids = set(self._items_by_id.keys())
        self._junctions = {j for j in self._junctions if (j[0] in valid_ids and j[1] in valid_ids)}
        self._parent = {iid: iid for iid in self._items_by_id.keys()}
        for (a, b, _) in self._junctions:
            ra = self.find_group(a)
            rb = self.find_group(b)
            if ra != rb:
                self._parent[rb] = ra

    def refresh_all_junction_geometry(self) -> None:
        new_junctions: Set[Tuple[int, int, Point]] = set()
        for a_id, b_id, _ in list(self._junctions):
            a = self._items_by_id.get(a_id)
            b = self._items_by_id.get(b_id)
            if a is None or b is None:
                continue
            shared = set(a.terminal_points()) & set(b.terminal_points())
            for pt in shared:
                new_junctions.add((min(a_id, b_id), max(a_id, b_id), pt))
        self._junctions = new_junctions
        self.rebuild_dsu()
        self.invalidate_analysis()

    def delete_item(self, item: "CircuitItem") -> None:
        self.clear_pending_popup()
        iid = item.item_id
        self._items_by_id.pop(iid, None)
        self._parent.pop(iid, None)
        self._junctions = {j for j in self._junctions if iid not in (j[0], j[1])}
        self.removeItem(item)
        try:
            item.deleteLater()
        except Exception:
            pass
        self.rebuild_dsu()
        self.invalidate_analysis()

    def delete_selected(self) -> None:
        items = [it for it in self.selectedItems() if isinstance(it, CircuitItem)]
        for it in list(items):
            self.delete_item(it)

    def items_for_analysis_from_selection(self) -> List["CircuitItem"]:
        selected = [it for it in self.selectedItems() if isinstance(it, CircuitItem)]
        if not selected:
            return []
        seen: Set[int] = set()
        out: List[CircuitItem] = []
        for it in selected:
            for g in self.group_items(it):
                if g.item_id not in seen:
                    seen.add(g.item_id)
                    out.append(g)
        return out

    def grid_to_scene(self, gp: Point) -> QtCore.QPointF:
        return QtCore.QPointF(gp[0] * self.cell, gp[1] * self.cell)

    def nearest_grid_point(self, sp: QtCore.QPointF) -> Point:
        return (int(round(sp.x() / self.cell)), int(round(sp.y() / self.cell)))

    def snap_scene_pos(self, sp: QtCore.QPointF) -> Point:
        return self.nearest_grid_point(sp)

    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)

        left = int(math.floor(rect.left() / self.cell)) - 1
        right = int(math.ceil(rect.right() / self.cell)) + 1
        top = int(math.floor(rect.top() / self.cell)) - 1
        bottom = int(math.ceil(rect.bottom() / self.cell)) + 1

        if self.dark_theme:
            painter.fillRect(rect, QtGui.QColor(11, 16, 32))
            grid_pen = QtGui.QPen(QtGui.QColor(35, 50, 90), 1)
            dot_brush = QtGui.QBrush(QtGui.QColor(200, 210, 240))
        else:
            grid_pen = QtGui.QPen(QtGui.QColor(220, 220, 220), 1)
            dot_brush = QtGui.QBrush(QtGui.QColor(30, 30, 30))

        painter.setPen(grid_pen)
        for x in range(left, right + 1):
            sx = x * self.cell
            painter.drawLine(sx, top * self.cell, sx, bottom * self.cell)
        for y in range(top, bottom + 1):
            sy = y * self.cell
            painter.drawLine(left * self.cell, sy, right * self.cell, sy)

        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(dot_brush)
        r = self.dot_r
        for x in range(left, right + 1):
            for y in range(top, bottom + 1):
                painter.drawEllipse(QtCore.QPointF(x * self.cell, y * self.cell), r, r)

        painter.restore()

    def clear_pending_popup(self) -> None:
        if self._pending_proxy is not None:
            proxy = self._pending_proxy
            self._pending_proxy = None
            self._pending_pair = None
            try:
                w = proxy.widget()
                proxy.setVisible(False)
                proxy.setWidget(None)
                self.removeItem(proxy)
                if w is not None:
                    w.deleteLater()
                proxy.deleteLater()
            except Exception:
                pass
        else:
            self._pending_pair = None

    def maybe_offer_connection(self, moved_item: "CircuitItem") -> None:
        self.clear_pending_popup()
        terms = moved_item.terminal_points()
        if not terms:
            return
        for pt in terms:
            for other in self._items_by_id.values():
                if other is moved_item:
                    continue
                if pt in other.terminal_points():
                    a, b = moved_item.item_id, other.item_id
                    key = (min(a, b), max(a, b), pt)
                    if key in self._junctions:
                        continue
                    self._pending_pair = (moved_item, other, pt)
                    self._pending_proxy = self._make_connect_popup(pt)
                    return

    def _make_connect_popup(self, pt: Point) -> QtWidgets.QGraphicsProxyWidget:
        w = QtWidgets.QWidget()
        if self.dark_theme:
            w.setStyleSheet(
                "background: rgba(15,23,48,235);"
                "border: 1px solid #2a3a6a; border-radius: 6px; color: #e8eefc;"
            )
        else:
            w.setStyleSheet(
                "background: rgba(250,250,250,240);"
                "border: 1px solid #444; border-radius: 6px;"
            )
        lay = QtWidgets.QHBoxLayout(w)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)

        btn = QtWidgets.QPushButton("Соединить")
        btn.setFixedWidth(110)
        lay.addWidget(btn)

        proxy = self.addWidget(w)
        sp = self.grid_to_scene(pt)
        proxy.setPos(sp + QtCore.QPointF(8, -28))
        proxy.setZValue(10)

        def on_click():
            if not self._pending_pair:
                return
            a, b, p = self._pending_pair
            btn.setEnabled(False)
            QtCore.QTimer.singleShot(0, lambda: self.confirm_connection(a, b, p))

        btn.clicked.connect(on_click)
        return proxy

    def confirm_connection(self, a: "CircuitItem", b: "CircuitItem", pt: Point) -> None:
        key = (min(a.item_id, b.item_id), max(a.item_id, b.item_id), pt)
        self._junctions.add(key)
        self.union_groups(a.item_id, b.item_id)
        self.clear_pending_popup()
        self.invalidate_analysis()

    def add_junction(self, a: "CircuitItem", b: "CircuitItem", pt: Point) -> None:
        key = (min(a.item_id, b.item_id), max(a.item_id, b.item_id), pt)
        if key in self._junctions:
            return
        self._junctions.add(key)
        self.union_groups(a.item_id, b.item_id)

    def add_wire_polyline(self, gpoints: List[Point], R: ParamValue, Pset: ParamValue) -> "WireItem":
        it = WireItem(scene=self, gpoints=gpoints, R=R, Pset=Pset)
        self.addItem(it)
        self.register_item(it)
        return it

    def add_node(self, point: Point) -> "NodeItem":
        it = NodeItem(scene=self, point=point)
        self.addItem(it)
        self.register_item(it)
        return it

    def wires_through_point(self, pt: Point) -> List["WireItem"]:
        out: List[WireItem] = []
        for it in self._items_by_id.values():
            if isinstance(it, WireItem) and it.contains_grid_point(pt):
                out.append(it)
        return out

    def terminal_items_at_point(self, pt: Point, exclude: Optional["CircuitItem"] = None) -> List["CircuitItem"]:
        out: List[CircuitItem] = []
        for it in self._items_by_id.values():
            if exclude is not None and it is exclude:
                continue
            if pt in it.terminal_points():
                out.append(it)
        return out

    def can_place_node_at(self, pt: Point) -> Tuple[bool, str]:
        wires = self.wires_through_point(pt)
        if not wires:
            return False, "Узел можно поставить только на провод или в точку соединения с проводом."
        for wire in wires:
            if pt not in wire.terminal_points():
                if wire.R.is_var() or wire.Pset.is_var():
                    return False, "Нельзя поставить узел внутрь провода, если у провода R или Pset заданы переменной."
        return True, ""

    def place_node(self, pt: Point) -> Tuple[Optional["NodeItem"], str]:
        ok, msg = self.can_place_node_at(pt)
        if not ok:
            return None, msg

        wires = self.wires_through_point(pt)
        redirected: List[Tuple["WireItem", Point, "CircuitItem"]] = []

        for wire in list(wires):
            if pt in wire.terminal_points():
                continue
            split = split_polyline_at_point(wire.gpoints, pt)
            if split is None:
                continue
            left_pts, right_pts, left_len, right_len = split
            total_len = left_len + right_len
            if total_len <= 0:
                continue

            old_junctions = [j for j in self._junctions if wire.item_id in (j[0], j[1])]

            left_R = ParamValue("value", wire.R.value * left_len / total_len, wire.R.var)
            right_R = ParamValue("value", wire.R.value * right_len / total_len, wire.R.var)
            left_P = ParamValue("value", wire.Pset.value * left_len / total_len, wire.Pset.var)
            right_P = ParamValue("value", wire.Pset.value * right_len / total_len, wire.Pset.var)

            left_wire = self.add_wire_polyline(left_pts, left_R, left_P)
            right_wire = self.add_wire_polyline(right_pts, right_R, right_P)
            left_wire.set_color(wire.color_name)
            right_wire.set_color(wire.color_name)

            start_pt, end_pt = wire.terminal_points()
            self._junctions = {j for j in self._junctions if wire.item_id not in (j[0], j[1])}
            for a_id, b_id, jpt in old_junctions:
                other_id = b_id if a_id == wire.item_id else a_id
                other = self._items_by_id.get(other_id)
                if other is None:
                    continue
                if jpt == start_pt:
                    redirected.append((left_wire, jpt, other))
                elif jpt == end_pt:
                    redirected.append((right_wire, jpt, other))

            self.removeItem(wire)
            self._items_by_id.pop(wire.item_id, None)
            self._parent.pop(wire.item_id, None)
            try:
                wire.deleteLater()
            except Exception:
                pass

        self.rebuild_dsu()
        for target_wire, jpt, other in redirected:
            self.add_junction(target_wire, other, jpt)

        node = self.add_node(pt)
        for other in self.terminal_items_at_point(pt, exclude=node):
            self.add_junction(node, other, pt)

        self.invalidate_analysis()
        return node, ""

    def add_wire(self, start: Point, R: ParamValue, Pset: ParamValue) -> "WireItem":
        pts = [start, (start[0] + 1, start[1])]
        it = WireItem(scene=self, gpoints=pts, R=R, Pset=Pset)
        self.addItem(it)
        self.register_item(it)
        return it

    def add_resistor(self, start: Point, R: ParamValue, Pset: ParamValue) -> "ResistorItem":
        it = ResistorItem(scene=self, start=start, R=R, Pset=Pset)
        self.addItem(it)
        self.register_item(it)
        return it

    def add_source(self, start: Point, r_int: ParamValue, U: ParamValue, Pset: ParamValue) -> "SourceItem":
        it = SourceItem(scene=self, start=start, r_int=r_int, U=U, Pset=Pset)
        self.addItem(it)
        self.register_item(it)
        return it

    def add_ammeter(self, start: Point, R: ParamValue, ideal: bool) -> "AmmeterItem":
        it = AmmeterItem(scene=self, start=start, R=R, ideal=ideal)
        self.addItem(it)
        self.register_item(it)
        return it

    def add_voltmeter(self, start: Point, R: ParamValue, ideal: bool) -> "VoltmeterItem":
        it = VoltmeterItem(scene=self, start=start, R=R, ideal=ideal)
        self.addItem(it)
        self.register_item(it)
        return it

    def add_capacitor(self, start: Point, C: ParamValue) -> "CapacitorItem":
        it = CapacitorItem(scene=self, start=start, C=C)
        self.addItem(it)
        self.register_item(it)
        return it

    def add_switch(self, start: Point, is_open: bool) -> "SwitchItem":
        it = SwitchItem(scene=self, start=start, is_open=is_open)
        self.addItem(it)
        self.register_item(it)
        return it


# ----------------------- View -----------------------
class CircuitView(QtWidgets.QGraphicsView):
    createSchemeRequested = QtCore.Signal()
    themeToggled = QtCore.Signal(bool)

    def __init__(self, scene: CircuitScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.TextAntialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.setAcceptDrops(True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)

        self._zoom = 1.0
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        self._dark = False
        self._rbtn_down = False
        self._rbtn_start_pos = QtCore.QPoint()
        self._panning_pending = False
        self._panning = False
        self._pan_start = QtCore.QPoint()
        self._pan_start_h = 0
        self._pan_start_v = 0
        self._pan_threshold = 8

        self._zoom_label = QtWidgets.QLabel("100%", self.viewport())
        self._zoom_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

        self._theme_btn = QtWidgets.QToolButton(self.viewport())
        self._theme_btn.setAutoRaise(True)
        self._theme_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._theme_btn.clicked.connect(self._toggle_theme)

        self.report_panel = ReportPanel(self.viewport())
        self.selection_panel = SelectionDetailsPanel(self.viewport())

        self.scene().selectionChanged.connect(self.refresh_selection_panel)
        self.scene().changed.connect(lambda *_: self.refresh_selection_panel())
        self.selection_panel.toggled.connect(self._layout_overlays)

        self.apply_theme(False)
        self.refresh_selection_panel()
        self._layout_overlays()

    def apply_theme(self, dark: bool) -> None:
        self._dark = bool(dark)
        if self._dark:
            self._zoom_label.setStyleSheet(
                "background: rgba(15,23,48,230); color: #e8eefc;"
                "border: 1px solid #2a3a6a; border-radius: 6px; padding: 2px 8px;"
            )
        else:
            self._zoom_label.setStyleSheet(
                "background: rgba(255,255,255,200); color: #111;"
                "border: 1px solid #444; border-radius: 6px; padding: 2px 8px;"
            )
        self._theme_btn.setIcon(make_bulb_icon(filled=(not self._dark), dark=self._dark))
        self._theme_btn.setIconSize(QtCore.QSize(18, 18))
        self.report_panel.apply_theme(self._dark)
        self.selection_panel.apply_theme(self._dark)
        self._layout_overlays()

    def _toggle_theme(self) -> None:
        self.themeToggled.emit(not self._dark)

    def _layout_overlays(self) -> None:
        m = 10
        self._zoom_label.adjustSize()
        self._theme_btn.adjustSize()

        total_w = self._theme_btn.sizeHint().width() + 6 + self._zoom_label.width()
        x0 = self.viewport().width() - total_w - m
        y0 = m

        self._theme_btn.move(x0, y0)
        self._zoom_label.move(x0 + self._theme_btn.sizeHint().width() + 6, y0)

        if self.report_panel.isVisible():
            self.report_panel.adjustSize()

        rp_w = max(self.report_panel.minimumWidth(), self.report_panel.sizeHint().width())
        rp_h = self.report_panel.sizeHint().height()
        self.report_panel.resize(rp_w, rp_h)

        default_pos = QtCore.QPoint(
            self.viewport().width() - rp_w - m,
            self.viewport().height() - rp_h - m,
        )

        if self.report_panel.user_moved():
            self.report_panel.clamp_inside_parent(m)
        else:
            self.report_panel.move(default_pos)

        sp_w = min(max(420, self.viewport().width() // 2), max(420, self.viewport().width() - 2 * m))
        sp_h = self.selection_panel.expanded_height() if self.selection_panel.is_expanded() else self.selection_panel.collapsed_height()
        self.selection_panel.setGeometry(
            m,
            self.viewport().height() - sp_h - m,
            sp_w,
            sp_h,
        )

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        super().resizeEvent(e)
        self._layout_overlays()

    def set_zoom(self, z: float) -> None:
        z = max(0.2, min(6.0, z))
        factor = z / self._zoom
        self._zoom = z
        self.scale(factor, factor)
        self._zoom_label.setText(f"{int(round(self._zoom * 100))}%")
        self._layout_overlays()

    def wheelEvent(self, e: QtGui.QWheelEvent) -> None:
        steps = e.angleDelta().y() / 120.0
        if steps == 0:
            return
        factor = 1.1 ** steps
        self.set_zoom(self._zoom * factor)
        e.accept()

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() == QtCore.Qt.Key_Delete:
            sc: CircuitScene = self.scene()  # type: ignore
            sc.delete_selected()
            e.accept()
            return
        super().keyPressEvent(e)

    def show_report(self, text: str) -> None:
        self.report_panel.set_report(text)
        self.refresh_selection_panel()
        self._layout_overlays()

    def _selection_title(self, item: "CircuitItem", base_name: str) -> str:
        color_label = item.color_label_for_selection_panel()
        if color_label:
            return f"{base_name} #{item.item_id} ({color_label})"
        return f"{base_name} #{item.item_id}"

    def _format_selected_item_details(self, item: "CircuitItem") -> str:
        an = self.scene().analysis_per_item.get(item.item_id, {})
        Itxt, Utxt, Ptxt = analysis_strings(an if an else None)

        if isinstance(item, WireItem):
            return "\n".join([
                self._selection_title(item, "Провод"),
                f"R = {format_param(item.R, 'ohms')}",
                f"Pset = {format_param(item.Pset, 'watts')}",
                f"I = {Itxt}",
                f"U = {Utxt}",
                f"P = {Ptxt}",
            ])

        if isinstance(item, ResistorItem):
            return "\n".join([
                self._selection_title(item, "Резистор"),
                f"R = {format_param(item.R, 'ohms')}",
                f"Pset = {format_param(item.Pset, 'watts')}",
                f"I = {Itxt}",
                f"U = {Utxt}",
                f"P = {Ptxt}",
            ])

        if isinstance(item, SourceItem):
            return "\n".join([
                self._selection_title(item, "Источник"),
                f"U = {format_param(item.U, 'volts')}",
                f"rвн = {format_param(item.r_int, 'ohms')}",
                f"Pset = {format_param(item.Pset, 'watts')}",
                f"I = {Itxt}",
                f"U(расчет) = {Utxt}",
                f"P = {Ptxt}",
            ])

        if isinstance(item, AmmeterItem):
            return "\n".join([
                self._selection_title(item, "Амперметр"),
                f"Внутреннее сопротивление = {item.resistance_text()}",
                f"Показание тока = {Itxt}",
                f"Напряжение на приборе = {Utxt}",
                f"P = {Ptxt}",
            ])

        if isinstance(item, VoltmeterItem):
            return "\n".join([
                self._selection_title(item, "Вольтметр"),
                f"Внутреннее сопротивление = {item.resistance_text()}",
                f"Показание напряжения = {Utxt}",
                f"Ток через прибор = {Itxt}",
                f"P = {Ptxt}",
            ])

        if isinstance(item, CapacitorItem):
            Qtxt = fmt_optional_value(an.get("Q") if an else None, "coulombs")
            Wtxt = fmt_optional_value(an.get("W") if an else None, "joules")
            return "\n".join([
                self._selection_title(item, "Конденсатор"),
                f"C = {format_param(item.C, 'farads')}",
                f"I = {Itxt}",
                f"U = {Utxt}",
                f"Q = {Qtxt}",
                f"W = {Wtxt}",
            ])

        if isinstance(item, SwitchItem):
            return "\n".join([
                self._selection_title(item, "Ключ"),
                f"Состояние = {item.state_text()}",
                f"I = {Itxt}",
                f"U = {Utxt}",
                f"P = {Ptxt}",
            ])

        if isinstance(item, NodeItem):
            return "\n".join([
                self._selection_title(item, "Узел"),
                "Точка подключения элементов.",
            ])

        return self._selection_title(item, "Элемент")

    def refresh_selection_panel(self) -> None:
        selected = [it for it in self.scene().selectedItems() if isinstance(it, CircuitItem)]  # type: ignore
        selected.sort(key=lambda it: it.item_id)

        if not selected:
            text = "Нет выделенных элементов."
        else:
            text = "\n\n".join(self._format_selected_item_details(it) for it in selected)

        self.selection_panel.set_text(text)
        self._layout_overlays()

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        payload = ToolPayload.from_mime(e.mimeData())
        if payload and payload.tool:
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent) -> None:
        payload = ToolPayload.from_mime(e.mimeData())
        if payload and payload.tool:
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        payload = ToolPayload.from_mime(e.mimeData())
        if not payload or not payload.tool:
            super().dropEvent(e)
            return

        sp = self.mapToScene(e.position().toPoint())
        gp = self.scene().snap_scene_pos(sp)  # type: ignore

        sc: CircuitScene = self.scene()  # type: ignore
        item: Optional[CircuitItem] = None
        Pset = ParamValue(mode=payload.p_mode, value=payload.p_value, var=payload.p_var)

        if payload.tool == "wire":
            item = sc.add_wire(gp, ParamValue(payload.r_mode, payload.r_value, payload.r_var), Pset)
        elif payload.tool == "resistor":
            item = sc.add_resistor(gp, ParamValue(payload.r_mode, payload.r_value, payload.r_var), Pset)
        elif payload.tool == "source":
            item = sc.add_source(
                gp,
                ParamValue(payload.r_mode, payload.r_value, payload.r_var),
                ParamValue(payload.u_mode, payload.u_value, payload.u_var),
                Pset,
            )
        elif payload.tool == "ammeter":
            item = sc.add_ammeter(
                gp,
                ParamValue(payload.r_mode, payload.r_value, payload.r_var),
                payload.meter_ideal,
            )
        elif payload.tool == "voltmeter":
            item = sc.add_voltmeter(
                gp,
                ParamValue(payload.r_mode, payload.r_value, payload.r_var),
                payload.meter_ideal,
            )
        elif payload.tool == "capacitor":
            item = sc.add_capacitor(
                gp,
                ParamValue(payload.c_mode, payload.c_value, payload.c_var),
            )
        elif payload.tool == "switch":
            item = sc.add_switch(gp, payload.switch_open)
        elif payload.tool == "node":
            item, msg = sc.place_node(gp)
            if item is None:
                self.show_report(msg)
                e.ignore()
                return

        if item:
            item.setSelected(True)
            if not isinstance(item, NodeItem):
                sc.maybe_offer_connection(item)
        e.acceptProposedAction()

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        self.setFocus()
        if e.button() == QtCore.Qt.RightButton:
            item = self.itemAt(e.position().toPoint())
            if item is None:
                self._rbtn_down = True
                self._rbtn_start_pos = e.position().toPoint()
                self._panning_pending = True
                e.accept()
                return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        if self._rbtn_down and self._panning_pending:
            dist = (e.position().toPoint() - self._rbtn_start_pos).manhattanLength()
            if dist >= self._pan_threshold:
                self._panning_pending = False
                self._panning = True
                self._pan_start = e.position().toPoint()
                self._pan_start_h = self.horizontalScrollBar().value()
                self._pan_start_v = self.verticalScrollBar().value()
                self.setCursor(QtCore.Qt.ClosedHandCursor)
                self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
                e.accept()
                return
        if self._panning:
            delta = e.position().toPoint() - self._pan_start
            self.horizontalScrollBar().setValue(self._pan_start_h - delta.x())
            self.verticalScrollBar().setValue(self._pan_start_v - delta.y())
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == QtCore.Qt.RightButton and self._rbtn_down:
            self._rbtn_down = False
            if self._panning:
                self._panning = False
                self.setCursor(QtCore.Qt.ArrowCursor)
                self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
                e.accept()
                return
            if self._panning_pending:
                self._panning_pending = False
                menu = QtWidgets.QMenu(self)
                selected = [it for it in self.scene().selectedItems() if isinstance(it, CircuitItem)]  # type: ignore
                act_make = menu.addAction("Создать схему")
                act_make.setEnabled(len(selected) > 0)

                def on_make():
                    self.createSchemeRequested.emit()

                act_make.triggered.connect(on_make)
                menu.exec(e.globalPosition().toPoint())
                e.accept()
                return
        super().mouseReleaseEvent(e)


# ----------------------- Items -----------------------
class CircuitItem(QtWidgets.QGraphicsObject):
    _next_id = 1
    COLOR_LABELS = {
        "default": "По умолчанию",
        "yellow": "Желтый",
        "cyan": "Голубой",
        "red": "Красный",
        "green": "Зеленый",
    }

    def __init__(self, scene: "CircuitScene"):
        super().__init__()
        self.scene_ref = scene
        self.item_id = CircuitItem._next_id
        CircuitItem._next_id += 1
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        self._drag_mode: Optional[str] = None
        self._last_mouse_grid: Optional[Point] = None
        self.color_name = "default"

    def translate_grid(self, dx: int, dy: int) -> None:
        raise NotImplementedError

    def terminal_points(self) -> List[Point]:
        return []

    def rotate_90(self) -> None:
        return

    def _grid_from_scene_pos(self, sp: QtCore.QPointF) -> Point:
        return self.scene_ref.nearest_grid_point(sp)

    def _scene_from_grid(self, gp: Point) -> QtCore.QPointF:
        return self.scene_ref.grid_to_scene(gp)

    def _analysis(self) -> Optional[Dict[str, Optional[float]]]:
        return self.scene_ref.analysis_per_item.get(self.item_id)

    def set_color(self, name: str) -> None:
        if name not in COLOR_NAMES:
            name = "default"
        self.color_name = name
        self.update()

    def color_label_for_selection_panel(self) -> Optional[str]:
        if self.color_name == "default":
            return None
        return self.COLOR_LABELS.get(self.color_name, self.color_name)

    def current_color(self) -> QtGui.QColor:
        dark = self.scene_ref.dark_theme
        name = self.color_name
        if dark:
            palette = {
                "default": QtGui.QColor(240, 220, 80),
                "yellow": QtGui.QColor(255, 230, 90),
                "cyan": QtGui.QColor(90, 230, 230),
                "red": QtGui.QColor(255, 110, 110),
                "green": QtGui.QColor(130, 230, 150),
            }
        else:
            palette = {
                "default": QtGui.QColor(0, 0, 0),
                "yellow": QtGui.QColor(220, 180, 0),
                "cyan": QtGui.QColor(0, 170, 200),
                "red": QtGui.QColor(220, 50, 50),
                "green": QtGui.QColor(40, 170, 80),
            }
        return palette.get(name, palette["default"])

    def add_color_menu(self, menu: QtWidgets.QMenu) -> None:
        cm = menu.addMenu("Установить цвет")
        actions: Dict[str, QtGui.QAction] = {}
        labels = {
            "default": "По умолчанию",
            "yellow": "Желтый",
            "cyan": "Голубой",
            "red": "Красный",
            "green": "Зеленый",
        }
        for key in COLOR_NAMES:
            act = cm.addAction(labels[key])
            act.setCheckable(True)
            act.setChecked(self.color_name == key)
            actions[key] = act

        def set_color_from_action(a: QtGui.QAction):
            for k, aa in actions.items():
                if a == aa:
                    self.set_color(k)
                    break

        for act in actions.values():
            act.triggered.connect(lambda checked=False, a=act: set_color_from_action(a))

    def add_persistent_rotate_button(self, menu: QtWidgets.QMenu, callback, text: str = "Повернуть на 90°") -> None:
        holder = QtWidgets.QWidget(menu)
        lay = QtWidgets.QHBoxLayout(holder)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(0)

        btn = QtWidgets.QPushButton(text)
        btn.setFlat(True)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setStyleSheet(
            "QPushButton { text-align: left; padding: 6px 10px; border: none; background: transparent; }"
            "QPushButton:hover { background: rgba(100, 140, 255, 50); }"
        )
        lay.addWidget(btn)

        act = QtWidgets.QWidgetAction(menu)
        act.setDefaultWidget(holder)
        menu.addAction(act)
        btn.clicked.connect(callback)


class WireItem(CircuitItem):
    def __init__(self, scene: "CircuitScene", gpoints: List[Point], R: ParamValue, Pset: ParamValue):
        super().__init__(scene)
        self.gpoints: List[Point] = self._simplify(gpoints)
        self.R = R
        self.Pset = Pset
        self._resize_end: Optional[int] = None

    def terminal_points(self) -> List[Point]:
        if len(self.gpoints) < 2:
            return []
        return [self.gpoints[0], self.gpoints[-1]]

    def contains_grid_point(self, pt: Point) -> bool:
        for a, b in zip(self.gpoints, self.gpoints[1:]):
            if point_on_axis_segment(pt, a, b):
                return True
        return False

    def translate_grid(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        self.prepareGeometryChange()
        self.gpoints = [(x + dx, y + dy) for (x, y) in self.gpoints]
        self.update()

    def rotate_90(self) -> None:
        if len(self.gpoints) < 2:
            return
        self.prepareGeometryChange()
        xs = [p[0] for p in self.gpoints]
        ys = [p[1] for p in self.gpoints]
        cx2 = min(xs) + max(xs)
        cy2 = min(ys) + max(ys)

        rotated2 = []
        for x, y in self.gpoints:
            x2 = 2 * x
            y2 = 2 * y
            nx2 = cx2 - (y2 - cy2)
            ny2 = cy2 + (x2 - cx2)
            rotated2.append((nx2, ny2))

        if rotated2 and ((rotated2[0][0] & 1) or (rotated2[0][1] & 1)):
            rotated2 = [(x2 + 1, y2 + 1) for x2, y2 in rotated2]

        self.gpoints = self._simplify([(x2 // 2, y2 // 2) for x2, y2 in rotated2])
        self.update()

    def boundingRect(self) -> QtCore.QRectF:
        pts = [self._scene_from_grid(p) for p in self.gpoints]
        if not pts:
            return QtCore.QRectF()
        xs = [p.x() for p in pts]
        ys = [p.y() for p in pts]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        margin = 14
        return QtCore.QRectF(minx - margin, miny - margin, (maxx - minx) + 2 * margin, (maxy - miny) + 2 * margin)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        if len(self.gpoints) < 2:
            return path
        pts = [self._scene_from_grid(p) for p in self.gpoints]
        path.moveTo(pts[0])
        for p in pts[1:]:
            path.lineTo(p)
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(path)

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget=None) -> None:
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        col = self.current_color()

        if self.isSelected():
            glow = QtGui.QPen(QtGui.QColor(80, 150, 255, 140), 9, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
            painter.setPen(glow)
            if len(self.gpoints) >= 2:
                pts = [self._scene_from_grid(p) for p in self.gpoints]
                for a, b in zip(pts, pts[1:]):
                    painter.drawLine(a, b)

        pen = QtGui.QPen(col, 5, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
        painter.setPen(pen)
        if len(self.gpoints) >= 2:
            pts = [self._scene_from_grid(p) for p in self.gpoints]
            for a, b in zip(pts, pts[1:]):
                painter.drawLine(a, b)

        end_r = 7.0
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(col))
        for gp in self.terminal_points():
            sp = self._scene_from_grid(gp)
            painter.drawEllipse(sp, end_r, end_r)

    def _hit_endpoint(self, sp: QtCore.QPointF) -> Optional[int]:
        r = 10.0
        terms = self.terminal_points()
        if len(terms) != 2:
            return None
        a = self._scene_from_grid(terms[0])
        b = self._scene_from_grid(terms[1])
        if QtCore.QLineF(sp, a).length() <= r:
            return 0
        if QtCore.QLineF(sp, b).length() <= r:
            return 1
        return None

    def mousePressEvent(self, e: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if e.button() == QtCore.Qt.LeftButton:
            self.scene_ref.clear_pending_popup()
            ep = self._hit_endpoint(e.scenePos())
            self._last_mouse_grid = self._grid_from_scene_pos(e.scenePos())
            self._drag_mode = "resize" if ep is not None else "move"
            self._resize_end = ep
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if self._drag_mode is None or self._last_mouse_grid is None:
            super().mouseMoveEvent(e)
            return
        gp = self._grid_from_scene_pos(e.scenePos())
        if self._drag_mode == "move":
            dx = gp[0] - self._last_mouse_grid[0]
            dy = gp[1] - self._last_mouse_grid[1]
            if dx or dy:
                self.scene_ref.translate_group(self, dx, dy)
                self._last_mouse_grid = gp
            e.accept()
            return
        if self._drag_mode == "resize":
            if self._resize_end is None:
                return
            self.prepareGeometryChange()
            self._resize_to_grid(self._resize_end, gp)
            self.update()
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if self._drag_mode is not None:
            mode = self._drag_mode
            self._drag_mode = None
            self._last_mouse_grid = None
            self._resize_end = None
            if mode == "resize":
                self.scene_ref.refresh_all_junction_geometry()
            self.scene_ref.maybe_offer_connection(self)
            self.scene_ref.invalidate_analysis()
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def _edit_params(self) -> None:
        dlg = ParamsDialog(
            "Параметры провода",
            fields=[
                {"key": "R", "label": "Сопротивление", "units": OHM_UNITS, "param": self.R, "prefer_unit": "Ом"},
                {"key": "Pset", "label": "Мощность (задано)", "units": WATT_UNITS, "param": self.Pset, "prefer_unit": "Вт"},
            ],
        )
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            vals = dlg.values()
            self.R = vals["R"]
            self.Pset = vals["Pset"]
            self.scene_ref.invalidate_analysis()
            self.update()

    def contextMenuEvent(self, e: QtWidgets.QGraphicsSceneContextMenuEvent) -> None:
        ep = self._hit_endpoint(e.scenePos())
        menu = QtWidgets.QMenu()
        an = self._analysis()
        Itxt, Utxt, Ptxt = analysis_strings(an)

        menu.addAction(f"R = {format_param(self.R, 'ohms')}").setEnabled(False)
        menu.addAction(f"Pset = {format_param(self.Pset, 'watts')}").setEnabled(False)
        menu.addAction(f"I(расчет) = {Itxt}").setEnabled(False)
        menu.addAction(f"U(расчет) = {Utxt}").setEnabled(False)
        menu.addAction(f"P(расчет) = {Ptxt}").setEnabled(False)

        menu.addSeparator()
        act_params = menu.addAction("Информация / изменить параметры...")
        self.add_persistent_rotate_button(menu, self._rotate_from_menu)
        act_del = menu.addAction("Удалить")
        self.add_color_menu(menu)

        branch_menu = None
        a2 = a3 = None
        if ep is not None:
            menu.addSeparator()
            branch_menu = menu.addMenu("Разветвить (только конец)")
            a2 = branch_menu.addAction("на 2")
            a3 = branch_menu.addAction("на 3")

        act = menu.exec(e.screenPos())
        if act is None:
            return
        if act == act_params:
            self._edit_params()
            return
        if act == act_del:
            self.scene_ref.delete_item(self)
            return
        if branch_menu is not None and (act == a2 or act == a3):
            endpoint = self.gpoints[0] if ep == 0 else self.gpoints[-1]
            self._branch(endpoint, 2 if act == a2 else 3)

    def _rotate_from_menu(self) -> None:
        self.rotate_90()
        self.scene_ref.refresh_all_junction_geometry()

    def _branch(self, at: Point, n: int) -> None:
        dirs = [(1, 0), (0, 1), (0, -1), (-1, 0)]
        used = set()

        if at == self.gpoints[0] and len(self.gpoints) >= 2:
            dx = self.gpoints[1][0] - self.gpoints[0][0]
            dy = self.gpoints[1][1] - self.gpoints[0][1]
            used.add((int(math.copysign(1, dx)) if dx else 0, int(math.copysign(1, dy)) if dy else 0))

        if at == self.gpoints[-1] and len(self.gpoints) >= 2:
            dx = self.gpoints[-1][0] - self.gpoints[-2][0]
            dy = self.gpoints[-1][1] - self.gpoints[-2][1]
            used.add((int(math.copysign(1, dx)) if dx else 0, int(math.copysign(1, dy)) if dy else 0))

        candidates = [d for d in dirs if d not in used]
        if len(candidates) < n:
            candidates = dirs

        for d in candidates[:n]:
            end = (at[0] + d[0], at[1] + d[1])
            w = self.scene_ref.add_wire(
                at,
                R=ParamValue(mode="value", value=0.0, var="Rw"),
                Pset=ParamValue(mode="value", value=0.0, var="Pw"),
            )
            w.gpoints = [at, end]
            w.update()
            self.scene_ref._junctions.add((min(self.item_id, w.item_id), max(self.item_id, w.item_id), at))
            self.scene_ref.rebuild_dsu()
            self.scene_ref.union_groups(self.item_id, w.item_id)

        self.scene_ref.invalidate_analysis()

    def _resize_to_grid(self, end_idx: int, new_end: Point) -> None:
        if len(self.gpoints) < 2:
            return
        if end_idx == 0:
            rev = list(reversed(self.gpoints))
            self.gpoints = list(reversed(self._resize_polyline_end(rev, new_end)))
        else:
            self.gpoints = self._resize_polyline_end(self.gpoints, new_end)
        self.gpoints = self._simplify(self.gpoints)

    def _resize_polyline_end(self, pts: List[Point], new_end: Point) -> List[Point]:
        if len(pts) < 2:
            return pts
        fixed = pts[:-1]
        anchor = pts[-1]

        if new_end == fixed[-1]:
            prev = fixed[-1]
            dx = anchor[0] - prev[0]
            dy = anchor[1] - prev[1]
            if dx == 0 and dy == 0:
                new_end = (prev[0] + 1, prev[1])
            else:
                step = (int(math.copysign(1, dx)) if dx else 0, int(math.copysign(1, dy)) if dy else 0)
                new_end = (prev[0] + step[0], prev[1] + step[1])

        if len(pts) == 2:
            if new_end[0] != pts[0][0] and new_end[1] != pts[0][1]:
                mid = (new_end[0], pts[0][1])
                return self._simplify([pts[0], mid, new_end])
            return [pts[0], new_end]

        prev = pts[-2]
        last_dir = "h" if anchor[1] == prev[1] else "v"
        out = fixed + [anchor]

        if last_dir == "h":
            first = (new_end[0], anchor[1])
            if first != out[-1]:
                out.append(first)
            if new_end != out[-1]:
                out.append(new_end)
        else:
            first = (anchor[0], new_end[1])
            if first != out[-1]:
                out.append(first)
            if new_end != out[-1]:
                out.append(new_end)

        return self._simplify(out)

    @staticmethod
    def _simplify(pts: List[Point]) -> List[Point]:
        if not pts:
            return pts
        out = [pts[0]]
        for p in pts[1:]:
            if p != out[-1]:
                out.append(p)
        changed = True
        while changed and len(out) >= 3:
            changed = False
            new = [out[0]]
            for i in range(1, len(out) - 1):
                a, b, c = out[i - 1], out[i], out[i + 1]
                if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
                    changed = True
                    continue
                new.append(b)
            new.append(out[-1])
            out = new
        return out


class TwoTerminalRotatableItem(CircuitItem):
    def __init__(self, scene: "CircuitScene"):
        super().__init__(scene)
        self.orientation = 0
        self.center: Point = (0, 0)

    def _dir(self) -> Point:
        dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        return dirs[self.orientation % 4]

    def terminal_points(self) -> List[Point]:
        dx, dy = self._dir()
        return [(self.center[0] - dx, self.center[1] - dy), (self.center[0] + dx, self.center[1] + dy)]

    def translate_grid(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        self.prepareGeometryChange()
        self.center = (self.center[0] + dx, self.center[1] + dy)
        self.update()

    def rotate_90(self) -> None:
        self.prepareGeometryChange()
        self.orientation = (self.orientation + 1) % 4
        self.update()

    def boundingRect(self) -> QtCore.QRectF:
        sp = self._scene_from_grid(self.center)
        margin = self.scene_ref.cell + 28
        return QtCore.QRectF(sp.x() - margin, sp.y() - margin, 2 * margin, 2 * margin)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def _component_center_scene(self) -> QtCore.QPointF:
        return self._scene_from_grid(self.center)

    def _draw_selected_glow(self, painter: QtGui.QPainter, cell: float, extra_rect: Optional[QtCore.QRectF] = None) -> None:
        if not self.isSelected():
            return
        painter.save()
        painter.setPen(QtGui.QPen(QtGui.QColor(80, 150, 255, 140), 6))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawLine(QtCore.QPointF(-cell, 0), QtCore.QPointF(cell, 0))
        if extra_rect is not None:
            painter.drawRect(extra_rect)
        painter.restore()

    def mousePressEvent(self, e: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if e.button() == QtCore.Qt.LeftButton:
            self.scene_ref.clear_pending_popup()
            self._drag_mode = "move"
            self._last_mouse_grid = self._grid_from_scene_pos(e.scenePos())
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if self._drag_mode == "move" and self._last_mouse_grid is not None:
            gp = self._grid_from_scene_pos(e.scenePos())
            dx = gp[0] - self._last_mouse_grid[0]
            dy = gp[1] - self._last_mouse_grid[1]
            if dx or dy:
                self.scene_ref.translate_group(self, dx, dy)
                self._last_mouse_grid = gp
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if self._drag_mode:
            self._drag_mode = None
            self._last_mouse_grid = None
            self.scene_ref.maybe_offer_connection(self)
            self.scene_ref.invalidate_analysis()
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def _rotate_from_menu(self) -> None:
        self.rotate_90()
        self.scene_ref.refresh_all_junction_geometry()


class ResistorItem(TwoTerminalRotatableItem):
    def __init__(self, scene: "CircuitScene", start: Point, R: ParamValue, Pset: ParamValue):
        super().__init__(scene)
        self.center = (start[0] + 1, start[1])
        self.R = R
        self.Pset = Pset

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget=None) -> None:
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        col = self.current_color()
        fill = QtGui.QColor(18, 28, 60) if self.scene_ref.dark_theme else QtGui.QColor(255, 255, 255)
        cell = float(self.scene_ref.cell)
        rect = QtCore.QRectF(-18, -9, 36, 18)

        painter.save()
        painter.translate(self._component_center_scene())
        painter.rotate(90 * self.orientation)

        self._draw_selected_glow(painter, cell, rect)

        painter.setPen(QtGui.QPen(col, 3))
        painter.drawLine(QtCore.QPointF(-cell, 0), QtCore.QPointF(-18, 0))
        painter.drawLine(QtCore.QPointF(18, 0), QtCore.QPointF(cell, 0))
        painter.setBrush(fill)
        painter.drawRect(rect)
        painter.restore()

    def _edit_params(self) -> None:
        dlg = ParamsDialog(
            "Параметры резистора",
            fields=[
                {"key": "R", "label": "Сопротивление", "units": OHM_UNITS, "param": self.R, "prefer_unit": "Ом"},
                {"key": "Pset", "label": "Мощность (задано)", "units": WATT_UNITS, "param": self.Pset, "prefer_unit": "Вт"},
            ],
        )
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            vals = dlg.values()
            self.R = vals["R"]
            self.Pset = vals["Pset"]
            self.scene_ref.invalidate_analysis()
            self.update()

    def contextMenuEvent(self, e: QtWidgets.QGraphicsSceneContextMenuEvent) -> None:
        menu = QtWidgets.QMenu()
        an = self._analysis()
        Itxt, Utxt, Ptxt = analysis_strings(an)

        menu.addAction(f"R = {format_param(self.R, 'ohms')}").setEnabled(False)
        menu.addAction(f"Pset = {format_param(self.Pset, 'watts')}").setEnabled(False)
        menu.addAction(f"I(расчет) = {Itxt}").setEnabled(False)
        menu.addAction(f"U(расчет) = {Utxt}").setEnabled(False)
        menu.addAction(f"P(расчет) = {Ptxt}").setEnabled(False)

        menu.addSeparator()
        act_params = menu.addAction("Информация / изменить параметры...")
        self.add_persistent_rotate_button(menu, self._rotate_from_menu)
        act_del = menu.addAction("Удалить")
        self.add_color_menu(menu)

        act = menu.exec(e.screenPos())
        if act == act_params:
            self._edit_params()
        elif act == act_del:
            self.scene_ref.delete_item(self)


class SourceItem(TwoTerminalRotatableItem):
    def __init__(self, scene: "CircuitScene", start: Point, r_int: ParamValue, U: ParamValue, Pset: ParamValue):
        super().__init__(scene)
        self.r_int = r_int
        self.U = U
        self.Pset = Pset
        self.center = (start[0] + 1, start[1])

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget=None) -> None:
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        col = self.current_color()
        cell = float(self.scene_ref.cell)

        painter.save()
        painter.translate(self._component_center_scene())
        painter.rotate(90 * self.orientation)

        if self.isSelected():
            painter.setPen(QtGui.QPen(QtGui.QColor(80, 150, 255, 140), 7))
            painter.drawLine(QtCore.QPointF(-cell, 0), QtCore.QPointF(cell, 0))

        painter.setPen(QtGui.QPen(col, 4))
        painter.drawLine(QtCore.QPointF(-cell, 0), QtCore.QPointF(-12, 0))
        painter.drawLine(QtCore.QPointF(12, 0), QtCore.QPointF(cell, 0))
        painter.drawLine(QtCore.QPointF(-8, -13), QtCore.QPointF(-8, 13))
        painter.drawLine(QtCore.QPointF(8, -8), QtCore.QPointF(8, 8))
        painter.restore()

    def _edit_params(self) -> None:
        dlg = ParamsDialog(
            "Параметры источника",
            fields=[
                {"key": "r", "label": "Внутреннее сопротивление", "units": OHM_UNITS, "param": self.r_int, "prefer_unit": "Ом"},
                {"key": "U", "label": "Напряжение", "units": VOLT_UNITS, "param": self.U, "prefer_unit": "В"},
                {"key": "Pset", "label": "Мощность (задано)", "units": WATT_UNITS, "param": self.Pset, "prefer_unit": "Вт"},
            ],
        )
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            vals = dlg.values()
            self.r_int = vals["r"]
            self.U = vals["U"]
            self.Pset = vals["Pset"]
            self.scene_ref.invalidate_analysis()
            self.update()

    def contextMenuEvent(self, e: QtWidgets.QGraphicsSceneContextMenuEvent) -> None:
        menu = QtWidgets.QMenu()
        an = self._analysis()
        Itxt, Utxt, Ptxt = analysis_strings(an)

        menu.addAction(f"U = {format_param(self.U, 'volts')}, r = {format_param(self.r_int, 'ohms')}").setEnabled(False)
        menu.addAction(f"Pset = {format_param(self.Pset, 'watts')}").setEnabled(False)
        menu.addAction(f"I(расчет) = {Itxt}").setEnabled(False)
        menu.addAction(f"U(расчет) = {Utxt}").setEnabled(False)
        menu.addAction(f"P(расчет) = {Ptxt}").setEnabled(False)

        menu.addSeparator()
        act_params = menu.addAction("Информация / изменить параметры...")
        self.add_persistent_rotate_button(menu, self._rotate_from_menu)
        act_del = menu.addAction("Удалить")
        self.add_color_menu(menu)

        act = menu.exec(e.screenPos())
        if act == act_params:
            self._edit_params()
        elif act == act_del:
            self.scene_ref.delete_item(self)


class NodeItem(CircuitItem):
    def __init__(self, scene: "CircuitScene", point: Point):
        super().__init__(scene)
        self.point = point

    def terminal_points(self) -> List[Point]:
        return [self.point]

    def translate_grid(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        self.prepareGeometryChange()
        self.point = (self.point[0] + dx, self.point[1] + dy)
        self.update()

    def boundingRect(self) -> QtCore.QRectF:
        sp = self._scene_from_grid(self.point)
        r = 12
        return QtCore.QRectF(sp.x() - r, sp.y() - r, 2 * r, 2 * r)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        sp = self._scene_from_grid(self.point)
        path.addEllipse(sp, 8, 8)
        return path

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget=None) -> None:
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        sp = self._scene_from_grid(self.point)
        col = self.current_color()

        if self.isSelected():
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QBrush(QtGui.QColor(80, 150, 255, 140)))
            painter.drawEllipse(sp, 10, 10)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(col))
        painter.drawEllipse(sp, 7, 7)

    def contextMenuEvent(self, e: QtWidgets.QGraphicsSceneContextMenuEvent) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction("Узел (точка подключения)").setEnabled(False)
        menu.addSeparator()
        act_del = menu.addAction("Удалить")
        self.add_color_menu(menu)
        act = menu.exec(e.screenPos())
        if act == act_del:
            self.scene_ref.delete_item(self)


class MeterItem(TwoTerminalRotatableItem):
    SYMBOL = "?"
    TITLE = "Прибор"
    IDEAL_R = 1.0
    IDEAL_HINT = ""

    def __init__(self, scene: "CircuitScene", start: Point, R: ParamValue, ideal: bool):
        super().__init__(scene)
        self.center = (start[0] + 1, start[1])
        self.R = R
        self.ideal = bool(ideal)

    def effective_resistance_numeric(self) -> Optional[float]:
        if self.ideal:
            return float(self.IDEAL_R)
        return self.R.numeric()

    def resistance_text(self) -> str:
        if self.ideal:
            return f"идеальный ({self.IDEAL_HINT})"
        return format_param(self.R, "ohms")

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget=None) -> None:
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        col = self.current_color()
        fill = QtGui.QColor(18, 28, 60) if self.scene_ref.dark_theme else QtGui.QColor(255, 255, 255)
        cell = float(self.scene_ref.cell)
        radius = 12.0

        painter.save()
        painter.translate(self._component_center_scene())
        painter.rotate(90 * self.orientation)

        if self.isSelected():
            painter.setPen(QtGui.QPen(QtGui.QColor(80, 150, 255, 140), 6))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawLine(QtCore.QPointF(-cell, 0), QtCore.QPointF(cell, 0))
            painter.drawEllipse(QtCore.QPointF(0, 0), radius + 3, radius + 3)

        painter.setPen(QtGui.QPen(col, 3))
        painter.drawLine(QtCore.QPointF(-cell, 0), QtCore.QPointF(-radius, 0))
        painter.drawLine(QtCore.QPointF(radius, 0), QtCore.QPointF(cell, 0))
        painter.setBrush(fill)
        painter.drawEllipse(QtCore.QPointF(0, 0), radius, radius)

        font = painter.font()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(
            QtCore.QRectF(-radius, -radius, 2 * radius, 2 * radius),
            QtCore.Qt.AlignCenter,
            self.SYMBOL,
        )
        painter.restore()

    def _edit_params(self) -> None:
        dlg = MeterParamsDialog(f"Параметры: {self.TITLE}", self.ideal, self.R)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            self.ideal, self.R = dlg.values()
            self.scene_ref.invalidate_analysis()
            self.update()

    def contextMenuEvent(self, e: QtWidgets.QGraphicsSceneContextMenuEvent) -> None:
        menu = QtWidgets.QMenu()
        an = self._analysis()
        Itxt, Utxt, Ptxt = analysis_strings(an)
        menu.addAction(f"Внутреннее сопротивление = {self.resistance_text()}").setEnabled(False)
        menu.addAction(f"I(расчет) = {Itxt}").setEnabled(False)
        menu.addAction(f"U(расчет) = {Utxt}").setEnabled(False)
        menu.addAction(f"P(расчет) = {Ptxt}").setEnabled(False)
        menu.addSeparator()
        act_params = menu.addAction("Информация / изменить параметры...")
        self.add_persistent_rotate_button(menu, self._rotate_from_menu)
        act_del = menu.addAction("Удалить")
        self.add_color_menu(menu)
        act = menu.exec(e.screenPos())
        if act == act_params:
            self._edit_params()
        elif act == act_del:
            self.scene_ref.delete_item(self)


class AmmeterItem(MeterItem):
    SYMBOL = "A"
    TITLE = "Амперметр"
    IDEAL_R = IDEAL_AMMETER_R
    IDEAL_HINT = "≈ 0 Ω"


class VoltmeterItem(MeterItem):
    SYMBOL = "V"
    TITLE = "Вольтметр"
    IDEAL_R = IDEAL_VOLTMETER_R
    IDEAL_HINT = "≈ ∞ Ω"



class CapacitorItem(TwoTerminalRotatableItem):
    TITLE = "Конденсатор"

    def __init__(self, scene: "CircuitScene", start: Point, C: ParamValue):
        super().__init__(scene)
        self.center = (start[0] + 1, start[1])
        self.C = C

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget=None) -> None:
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        col = self.current_color()
        cell = float(self.scene_ref.cell)

        painter.save()
        painter.translate(self._component_center_scene())
        painter.rotate(90 * self.orientation)

        if self.isSelected():
            painter.setPen(QtGui.QPen(QtGui.QColor(80, 150, 255, 140), 6))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawLine(QtCore.QPointF(-cell, 0), QtCore.QPointF(cell, 0))

        painter.setPen(QtGui.QPen(col, 4, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        painter.drawLine(QtCore.QPointF(-cell, 0), QtCore.QPointF(-10, 0))
        painter.drawLine(QtCore.QPointF(10, 0), QtCore.QPointF(cell, 0))
        painter.drawLine(QtCore.QPointF(-6, -14), QtCore.QPointF(-6, 14))
        painter.drawLine(QtCore.QPointF(6, -14), QtCore.QPointF(6, 14))
        painter.restore()

    def _edit_params(self) -> None:
        dlg = ParamsDialog(
            "Параметры конденсатора",
            fields=[
                {"key": "C", "label": "Ёмкость", "units": FARAD_UNITS, "param": self.C, "prefer_unit": "мкФ"},
            ],
        )
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            vals = dlg.values()
            self.C = vals["C"]
            self.scene_ref.invalidate_analysis()
            self.update()

    def contextMenuEvent(self, e: QtWidgets.QGraphicsSceneContextMenuEvent) -> None:
        menu = QtWidgets.QMenu()
        an = self._analysis()
        Itxt, Utxt, _ = analysis_strings(an)
        Qtxt = fmt_optional_value(an.get("Q") if an else None, "coulombs")
        Wtxt = fmt_optional_value(an.get("W") if an else None, "joules")
        menu.addAction(f"C = {format_param(self.C, 'farads')}").setEnabled(False)
        menu.addAction(f"I(расчет) = {Itxt}").setEnabled(False)
        menu.addAction(f"U(расчет) = {Utxt}").setEnabled(False)
        menu.addAction(f"Q(расчет) = {Qtxt}").setEnabled(False)
        menu.addAction(f"W(расчет) = {Wtxt}").setEnabled(False)
        menu.addSeparator()
        act_params = menu.addAction("Информация / изменить параметры...")
        self.add_persistent_rotate_button(menu, self._rotate_from_menu)
        act_del = menu.addAction("Удалить")
        self.add_color_menu(menu)
        act = menu.exec(e.screenPos())
        if act == act_params:
            self._edit_params()
        elif act == act_del:
            self.scene_ref.delete_item(self)


class SwitchItem(TwoTerminalRotatableItem):
    TITLE = "Ключ"

    def __init__(self, scene: "CircuitScene", start: Point, is_open: bool):
        super().__init__(scene)
        self.center = (start[0] + 1, start[1])
        self.is_open = bool(is_open)

    def state_text(self) -> str:
        return "открыт (ток идет)" if self.is_open else "закрыт (ток не идет)"

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget=None) -> None:
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        col = self.current_color()
        cell = float(self.scene_ref.cell)

        painter.save()
        painter.translate(self._component_center_scene())
        painter.rotate(90 * self.orientation)

        if self.isSelected():
            painter.setPen(QtGui.QPen(QtGui.QColor(80, 150, 255, 140), 6))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawLine(QtCore.QPointF(-cell, 0), QtCore.QPointF(cell, 0))

        painter.setPen(QtGui.QPen(col, 4, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        painter.drawLine(QtCore.QPointF(-cell, 0), QtCore.QPointF(-12, 0))
        painter.drawLine(QtCore.QPointF(12, 0), QtCore.QPointF(cell, 0))
        painter.setBrush(QtGui.QBrush(col))
        painter.drawEllipse(QtCore.QPointF(-12, 0), 3.5, 3.5)
        painter.drawEllipse(QtCore.QPointF(12, 0), 3.5, 3.5)
        if self.is_open:
            painter.drawLine(QtCore.QPointF(-12, 0), QtCore.QPointF(12, 0))
        else:
            painter.drawLine(QtCore.QPointF(-12, 0), QtCore.QPointF(4, -8))

        painter.restore()

    def _edit_params(self) -> None:
        dlg = SwitchParamsDialog("Параметры ключа", self.is_open)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            self.is_open = dlg.values()
            self.scene_ref.refresh_all_junction_geometry()

    def contextMenuEvent(self, e: QtWidgets.QGraphicsSceneContextMenuEvent) -> None:
        menu = QtWidgets.QMenu()
        an = self._analysis()
        Itxt, Utxt, Ptxt = analysis_strings(an)
        menu.addAction(f"Состояние = {self.state_text()}").setEnabled(False)
        menu.addAction(f"I(расчет) = {Itxt}").setEnabled(False)
        menu.addAction(f"U(расчет) = {Utxt}").setEnabled(False)
        menu.addAction(f"P(расчет) = {Ptxt}").setEnabled(False)
        menu.addSeparator()
        act_params = menu.addAction("Информация / изменить параметры...")
        self.add_persistent_rotate_button(menu, self._rotate_from_menu)
        act_del = menu.addAction("Удалить")
        self.add_color_menu(menu)
        act = menu.exec(e.screenPos())
        if act == act_params:
            self._edit_params()
        elif act == act_del:
            self.scene_ref.delete_item(self)


# ----------------------- Analysis -----------------------
class PointDSU:
    def __init__(self):
        self.parent: Dict[Point, Point] = {}

    def add(self, x: Point) -> None:
        self.parent.setdefault(x, x)

    def find(self, x: Point) -> Point:
        p = self.parent.get(x, x)
        if p != x:
            self.parent[x] = self.find(p)
        return self.parent.get(x, x)

    def union(self, a: Point, b: Point) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra



def analyze_scheme(items: List[CircuitItem]) -> Tuple[bool, str, Dict]:
    EPS_SHORT = 1e-9

    srcs = [it for it in items if isinstance(it, SourceItem)]
    if not srcs:
        return False, "Нужно выделить схему хотя бы с одним источником.", {}

    vars_found: Dict[str, Optional[float]] = {}
    var_kind: Dict[str, str] = {}

    def register_var(name: str, kind: str) -> str:
        name = (name or "").strip() or "x"
        vars_found.setdefault(name, None)
        if name not in var_kind:
            var_kind[name] = kind
        elif var_kind[name] != kind:
            var_kind[name] = "mixed"
        return name

    branches: List[Dict] = []
    for it in items:
        if isinstance(it, NodeItem):
            continue

        if isinstance(it, SourceItem):
            p, n = it.terminal_points()
            branches.append({
                "item": it,
                "kind": "source",
                "p": p,
                "q": n,
                "U": it.U.numeric(),
                "r": it.r_int.numeric(),
                "U_var": register_var(it.U.var, "volts") if it.U.is_var() else None,
                "r_var": register_var(it.r_int.var, "ohms") if it.r_int.is_var() else None,
            })
            if it.Pset.is_var():
                register_var(it.Pset.var, "watts")
            continue

        if isinstance(it, WireItem):
            p, q = it.terminal_points()
            branches.append({
                "item": it,
                "kind": "resistor",
                "subkind": "wire",
                "p": p,
                "q": q,
                "R": it.R.numeric(),
                "R_var": register_var(it.R.var, "ohms") if it.R.is_var() else None,
            })
            if it.Pset.is_var():
                register_var(it.Pset.var, "watts")
            continue

        if isinstance(it, ResistorItem):
            p, q = it.terminal_points()
            branches.append({
                "item": it,
                "kind": "resistor",
                "subkind": "resistor",
                "p": p,
                "q": q,
                "R": it.R.numeric(),
                "R_var": register_var(it.R.var, "ohms") if it.R.is_var() else None,
            })
            if it.Pset.is_var():
                register_var(it.Pset.var, "watts")
            continue

        if isinstance(it, MeterItem):
            p, q = it.terminal_points()
            r_var = None
            if (not it.ideal) and it.R.is_var():
                r_var = register_var(it.R.var, "ohms")
            branches.append({
                "item": it,
                "kind": "resistor",
                "subkind": it.SYMBOL.lower(),
                "p": p,
                "q": q,
                "R": it.effective_resistance_numeric(),
                "R_var": r_var,
            })
            continue

        if isinstance(it, CapacitorItem):
            p, q = it.terminal_points()
            branches.append({
                "item": it,
                "kind": "capacitor",
                "p": p,
                "q": q,
                "C": it.C.numeric(),
                "C_var": register_var(it.C.var, "farads") if it.C.is_var() else None,
            })
            continue

        if isinstance(it, SwitchItem):
            p, q = it.terminal_points()
            branches.append({
                "item": it,
                "kind": "switch",
                "p": p,
                "q": q,
                "conducting": bool(it.is_open),
            })
            continue

    adj_all: Dict[Point, Set[Point]] = {}

    def add_conn(u: Point, v: Point) -> None:
        adj_all.setdefault(u, set()).add(v)
        adj_all.setdefault(v, set()).add(u)

    for br in branches:
        if br["kind"] == "capacitor":
            continue
        if br["kind"] == "switch" and not br["conducting"]:
            continue
        add_conn(br["p"], br["q"])

    comp_of: Dict[Point, int] = {}
    comp_nodes: Dict[int, Set[Point]] = {}
    cid_next = 0
    for node in adj_all:
        if node in comp_of:
            continue
        st = [node]
        comp_of[node] = cid_next
        comp_nodes[cid_next] = {node}
        while st:
            u = st.pop()
            for v in adj_all.get(u, set()):
                if v not in comp_of:
                    comp_of[v] = cid_next
                    comp_nodes[cid_next].add(v)
                    st.append(v)
        cid_next += 1

    source_components: Set[int] = set()
    for br in branches:
        if br["kind"] == "source":
            cid = comp_of.get(br["p"])
            if cid is not None:
                source_components.add(cid)

    vars_affecting: Set[str] = set()
    for br in branches:
        cid = comp_of.get(br["p"])
        if cid is None or cid not in source_components:
            continue
        if br["kind"] == "source":
            if br.get("U_var"):
                vars_affecting.add(br["U_var"])
            if br.get("r_var"):
                vars_affecting.add(br["r_var"])
        elif br["kind"] == "resistor" and br.get("R_var"):
            vars_affecting.add(br["R_var"])

    def vars_block() -> str:
        if not vars_found:
            return ""
        lines = ["", "Переменные:"]
        for k in sorted(vars_found):
            val = vars_found[k]
            kind = var_kind.get(k, "mixed")
            if val is None:
                lines.append(f"- {k}: не удалось вычислить")
            else:
                if kind == "ohms":
                    lines.append(f"- {k} = {fmt_ohms(val)}")
                elif kind == "volts":
                    lines.append(f"- {k} = {fmt_volts(val)}")
                elif kind == "watts":
                    lines.append(f"- {k} = {fmt_watts(val)}")
                elif kind == "farads":
                    lines.append(f"- {k} = {fmt_farads(val)}")
                else:
                    lines.append(f"- {k} = {val:.6g}")
        return "\n".join(lines)

    if vars_affecting:
        lines = [
            "В выделенной схеме есть переменные, которые влияют на расчёт.",
            "Численный расчёт токов и мощностей невозможен без их значений.",
        ]
        vb = vars_block()
        if vb:
            lines.append(vb)
        return False, "\n".join(lines), {"vars": vars_found}

    node_voltage: Dict[Point, float] = {}
    ideal_source_current: Dict[int, float] = {}
    internal_loss_by_source: Dict[int, float] = {}
    comp_reports: List[str] = []

    for cid in sorted(source_components):
        comp_node_set = comp_nodes.get(cid, set())
        comp_branches = [
            br for br in branches
            if br["p"] in comp_node_set and br["q"] in comp_node_set
        ]
        if not comp_branches:
            continue

        dsu = PointDSU()
        for pt in comp_node_set:
            dsu.add(pt)

        for br in comp_branches:
            if br["kind"] == "switch":
                if br["conducting"]:
                    dsu.union(br["p"], br["q"])
                continue
            if br["kind"] == "resistor":
                R = br.get("R")
                if R is not None and float(R) <= EPS_SHORT:
                    dsu.union(br["p"], br["q"])

        compressed_nodes = sorted({dsu.find(pt) for pt in comp_node_set})
        if not compressed_nodes:
            continue

        for br in comp_branches:
            if br["kind"] != "source":
                continue
            U = br.get("U")
            r = br.get("r")
            if U is None or r is None:
                continue
            p = dsu.find(br["p"])
            q = dsu.find(br["q"])
            if float(r) <= EPS_SHORT and p == q and abs(float(U)) > 1e-12:
                return False, "Схема противоречива: идеальный источник с ненулевой ЭДС закорочен.", {"vars": vars_found}

        ref = compressed_nodes[0]
        unknown_nodes = [n for n in compressed_nodes if n != ref]
        node_idx = {n: i for i, n in enumerate(unknown_nodes)}

        ideal_sources = [
            br for br in comp_branches
            if br["kind"] == "source" and br.get("U") is not None and br.get("r") is not None and float(br["r"]) <= EPS_SHORT
        ]

        nvars = len(unknown_nodes) + len(ideal_sources)
        A = [[0.0 for _ in range(nvars)] for __ in range(nvars)]
        b = [0.0 for _ in range(nvars)]

        def node_var_index(n: Point) -> Optional[int]:
            return node_idx.get(n)

        def add_rhs(n: Point, val: float) -> None:
            idx = node_var_index(n)
            if idx is not None:
                b[idx] += val

        def stamp_conductance(a: Point, bnode: Point, g: float) -> None:
            ia = node_var_index(a)
            ib = node_var_index(bnode)
            if ia is not None:
                A[ia][ia] += g
            if ib is not None:
                A[ib][ib] += g
            if ia is not None and ib is not None:
                A[ia][ib] -= g
                A[ib][ia] -= g

        for br in comp_branches:
            if br["kind"] == "switch":
                continue

            p = dsu.find(br["p"])
            q = dsu.find(br["q"])

            if br["kind"] == "resistor":
                R = br.get("R")
                if R is None:
                    continue
                R = float(R)
                if R <= EPS_SHORT or p == q:
                    continue
                stamp_conductance(p, q, 1.0 / R)
                continue

            if br["kind"] == "source":
                U = float(br["U"])
                r = float(br["r"])
                if r <= EPS_SHORT:
                    continue
                if p != q:
                    g = 1.0 / r
                    stamp_conductance(p, q, g)
                    add_rhs(p, g * U)
                    add_rhs(q, -g * U)

        for k, br in enumerate(ideal_sources):
            p = dsu.find(br["p"])
            q = dsu.find(br["q"])
            col = len(unknown_nodes) + k

            ip = node_var_index(p)
            iq = node_var_index(q)
            if ip is not None:
                A[ip][col] += 1.0
                A[col][ip] += 1.0
            if iq is not None:
                A[iq][col] -= 1.0
                A[col][iq] -= 1.0

            b[col] += float(br["U"])

        try:
            sol = gauss_solve(A, b) if nvars > 0 else []
        except ValueError:
            return False, "Схема вырождена или противоречива: не удалось решить систему уравнений.", {"vars": vars_found}

        comp_v: Dict[Point, float] = {ref: 0.0}
        for n in unknown_nodes:
            comp_v[n] = float(sol[node_idx[n]])

        for pt in comp_node_set:
            node_voltage[pt] = comp_v[dsu.find(pt)]

        for k, br in enumerate(ideal_sources):
            ideal_source_current[br["item"].item_id] = float(sol[len(unknown_nodes) + k])

        comp_source_power = 0.0
        comp_load_power = 0.0
        comp_internal_loss = 0.0

        for br in comp_branches:
            if br["kind"] == "source":
                it = br["item"]
                Vp = node_voltage.get(br["p"], 0.0)
                Vq = node_voltage.get(br["q"], 0.0)
                U = float(br["U"])
                r = float(br["r"])
                if r <= EPS_SHORT:
                    I = ideal_source_current.get(it.item_id, 0.0)
                    internal_loss_by_source[it.item_id] = 0.0
                else:
                    I = (Vp - Vq - U) / r
                    internal_loss_by_source[it.item_id] = (I * I) * r
                comp_source_power += -(U * I)
                comp_internal_loss += internal_loss_by_source[it.item_id]
            elif br["kind"] == "resistor":
                R = br.get("R")
                if R is None:
                    continue
                R = float(R)
                if R <= EPS_SHORT:
                    continue
                Vp = node_voltage.get(br["p"], 0.0)
                Vq = node_voltage.get(br["q"], 0.0)
                I = (Vp - Vq) / R
                comp_load_power += (I * I) * R

        comp_reports.append("\n".join([
            f"Компонента {cid + 1}:",
            f"  Источников: {len([br for br in comp_branches if br['kind'] == 'source'])}",
            f"  Суммарная мощность источников: {fmt_watts(comp_source_power)}",
            f"  Мощность на внешних элементах: {fmt_watts(comp_load_power)}",
            f"  Потери на внутренних сопротивлениях: {fmt_watts(comp_internal_loss)}",
        ]))

    per_item: Dict[int, Dict[str, Optional[float]]] = {}

    for it in items:
        if isinstance(it, NodeItem):
            continue

        if isinstance(it, SourceItem):
            p, q = it.terminal_points()
            Vp = node_voltage.get(p)
            Vq = node_voltage.get(q)
            U_num = it.U.numeric()
            r_num = it.r_int.numeric()
            if Vp is None or Vq is None or U_num is None or r_num is None:
                per_item[it.item_id] = {"I": 0.0, "V": U_num, "P": 0.0}
                continue
            if float(r_num) <= EPS_SHORT:
                I = ideal_source_current.get(it.item_id, 0.0)
            else:
                I = (Vp - Vq - float(U_num)) / float(r_num)
            per_item[it.item_id] = {"I": abs(I), "V": abs(Vp - Vq), "P": -(float(U_num) * I)}
            continue

        if isinstance(it, CapacitorItem):
            p, q = it.terminal_points()
            Cn = it.C.numeric()
            Vp = node_voltage.get(p)
            Vq = node_voltage.get(q)
            if Vp is None or Vq is None:
                per_item[it.item_id] = {"I": 0.0, "V": None, "P": 0.0, "Q": None, "W": None}
            else:
                Vdrop = abs(Vp - Vq)
                if Cn is None:
                    per_item[it.item_id] = {"I": 0.0, "V": Vdrop, "P": 0.0, "Q": None, "W": None}
                else:
                    C = float(Cn)
                    per_item[it.item_id] = {"I": 0.0, "V": Vdrop, "P": 0.0, "Q": C * Vdrop, "W": 0.5 * C * Vdrop * Vdrop}
            continue

        if isinstance(it, SwitchItem):
            p, q = it.terminal_points()
            Vp = node_voltage.get(p)
            Vq = node_voltage.get(q)
            if it.is_open:
                if Vp is not None and Vq is not None:
                    per_item[it.item_id] = {"I": None, "V": 0.0, "P": 0.0}
                else:
                    per_item[it.item_id] = {"I": 0.0, "V": 0.0, "P": 0.0}
            else:
                Vdrop = abs(Vp - Vq) if (Vp is not None and Vq is not None) else 0.0
                per_item[it.item_id] = {"I": 0.0, "V": Vdrop, "P": 0.0}
            continue

        if isinstance(it, WireItem):
            p, q = it.terminal_points()
            Rn = it.R.numeric()
            if Rn is None:
                per_item[it.item_id] = {"I": 0.0, "V": 0.0, "P": 0.0}
                continue
            Vp = node_voltage.get(p)
            Vq = node_voltage.get(q)
            R = float(Rn)
            if Vp is None or Vq is None:
                per_item[it.item_id] = {"I": 0.0, "V": 0.0, "P": 0.0}
            elif R <= EPS_SHORT:
                per_item[it.item_id] = {"I": None, "V": 0.0, "P": 0.0}
            else:
                I = (Vp - Vq) / R
                per_item[it.item_id] = {"I": abs(I), "V": abs(Vp - Vq), "P": (I * I) * R}
            continue

        if isinstance(it, ResistorItem):
            p, q = it.terminal_points()
            Rn = it.R.numeric()
            if Rn is None:
                per_item[it.item_id] = {"I": 0.0, "V": 0.0, "P": 0.0}
                continue
            Vp = node_voltage.get(p)
            Vq = node_voltage.get(q)
            R = float(Rn)
            if Vp is None or Vq is None:
                per_item[it.item_id] = {"I": 0.0, "V": 0.0, "P": 0.0}
            elif R <= EPS_SHORT:
                per_item[it.item_id] = {"I": None, "V": 0.0, "P": 0.0}
            else:
                I = (Vp - Vq) / R
                per_item[it.item_id] = {"I": abs(I), "V": abs(Vp - Vq), "P": (I * I) * R}
            continue

        if isinstance(it, MeterItem):
            p, q = it.terminal_points()
            Rn = it.effective_resistance_numeric()
            if Rn is None:
                per_item[it.item_id] = {"I": 0.0, "V": 0.0, "P": 0.0}
                continue
            Vp = node_voltage.get(p)
            Vq = node_voltage.get(q)
            R = float(Rn)
            if Vp is None or Vq is None:
                per_item[it.item_id] = {"I": 0.0, "V": 0.0, "P": 0.0}
            elif R <= EPS_SHORT:
                per_item[it.item_id] = {"I": None, "V": 0.0, "P": 0.0}
            else:
                I = (Vp - Vq) / R
                per_item[it.item_id] = {"I": abs(I), "V": abs(Vp - Vq), "P": (I * I) * R}
            continue

    for it in items:
        if isinstance(it, (WireItem, ResistorItem, SourceItem)) and getattr(it, "Pset", None) and it.Pset.is_var():
            name = it.Pset.var.strip() or "x"
            if it.item_id in per_item and per_item[it.item_id].get("P") is not None:
                vars_found[name] = float(per_item[it.item_id]["P"] or 0.0)

    source_generated = 0.0
    source_absorbed = 0.0
    load_power = 0.0
    internal_power = 0.0

    for it in items:
        if isinstance(it, SourceItem):
            pwr = float(per_item.get(it.item_id, {}).get("P") or 0.0)
            if pwr >= 0:
                source_generated += pwr
            else:
                source_absorbed += -pwr
            internal_power += internal_loss_by_source.get(it.item_id, 0.0)
        elif isinstance(it, (WireItem, ResistorItem, MeterItem)):
            load_power += float(per_item.get(it.item_id, {}).get("P") or 0.0)

    total = {
        "P_sources_generated": source_generated,
        "P_sources_absorbed": source_absorbed,
        "P_load": load_power,
        "P_int": internal_power,
        "num_sources": len(srcs),
    }

    lines = [
        f"Источников в выделенной схеме: {len(srcs)}",
        f"Источник(и) отдают мощность: {fmt_watts(source_generated)}",
        f"Источник(и) поглощают мощность: {fmt_watts(source_absorbed)}",
        f"Мощность на внешних элементах: {fmt_watts(load_power)}",
        f"Потери на внутренних сопротивлениях источников: {fmt_watts(internal_power)}",
    ]

    if comp_reports:
        lines.append("")
        lines.extend(comp_reports)

    if vars_found:
        lines.append("")
        lines.append("Переменные:")
        for k in sorted(vars_found):
            val = vars_found[k]
            kind = var_kind.get(k, "mixed")
            if val is None:
                lines.append(f"- {k}: не удалось вычислить")
            else:
                if kind == "ohms":
                    lines.append(f"- {k} = {fmt_ohms(val)}")
                elif kind == "volts":
                    lines.append(f"- {k} = {fmt_volts(val)}")
                elif kind == "watts":
                    lines.append(f"- {k} = {fmt_watts(val)}")
                elif kind == "farads":
                    lines.append(f"- {k} = {fmt_farads(val)}")
                else:
                    lines.append(f"- {k} = {val:.6g}")

    return True, "\n".join(lines), {"per_item": per_item, "total": total, "vars": vars_found}

# ----------------------- Main / UI -----------------------
LIGHT_QSS = ""
DARK_QSS = """
QMainWindow, QWidget { background-color: #0b1020; color: #e8eefc; }
QMenuBar { background: #0f1730; color: #e8eefc; }
QMenuBar::item:selected { background: #1a2550; }
QMenu { background: #0f1730; color: #e8eefc; border: 1px solid #2a3a6a; }
QMenu::item:selected { background: #1a2550; }
QDockWidget { background: #0f1730; color: #e8eefc; }
QGroupBox { border: 1px solid #2a3a6a; border-radius: 6px; margin-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QLineEdit, QDoubleSpinBox, QComboBox, QTextEdit {
    background: #111a38; color: #e8eefc; border: 1px solid #2a3a6a; border-radius: 4px;
}
QPushButton, QToolButton, QCheckBox {
    background: #1a2550; color: #e8eefc; border: 1px solid #2a3a6a; border-radius: 4px;
    padding: 4px 8px;
}
QPushButton:hover, QToolButton:hover { background: #243066; }
QDialog { background-color: #0b1020; color: #e8eefc; }
QScrollArea { background: #0b1020; }
"""

GUIDE_TEXT = """УПРАВЛЕНИЕ (как пользоваться)

1) Добавление элементов
- Слева панель инструментов: Провод / Резистор / Источник / Амперметр / Вольтметр / Конденсатор / Ключ / Узел.
- ЛКМ зажать на картинке элемента и перетащить на поле (drag&drop).
- Элемент ставится в узлы сетки.

2) Перемещение и выделение
- ЛКМ: выделение элементов, выделение рамкой.
- Ctrl + ЛКМ: добавлять/убирать элементы в выделение.
- Delete: удалить выделенные элементы.
- ПКМ на пустом месте + потянуть: перемещение поля.

3) Масштаб
- Колёсико мыши: увеличить/уменьшить.
- В правом верхнем углу показывается масштаб.

4) Провод
- ЛКМ по точке на конце — изменять длину.
- ЛКМ по середине — перемещать (вместе с группой соединённых).
- ПКМ → можно повернуть на 90°.

5) Соединение
- При совпадении узлов появляется «соединить» → OK.
- После соединения элементы двигаются как единое целое.

6) Разветвление
- ПКМ по концу провода → Разветвить → на 2/на 3.

7) Поворот элементов
- Любой элемент, кроме узла, можно повернуть на 90° через ПКМ.
- Поворот идёт вокруг центра элемента.
- Кнопка поворота в контекстном меню не закрывает меню сразу, так что можно нажать несколько раз подряд.

8) Ключ
- Ключ можно поставить как «открыт» или «закрыт» ещё слева в панели инструментов.
- В этом приложении логика такая: открыт — ток идет, закрыт — ток не идет.
- Состояние ключа можно менять через ПКМ → Информация / изменить параметры...

9) Амперметр и вольтметр
- Амперметр подключай ПОСЛЕДОВАТЕЛЬНО в ветвь, ток которой хочешь измерить.
- Вольтметр подключай ПАРАЛЛЕЛЬНО участку, напряжение на котором хочешь измерить.
- Для каждого прибора можно выбрать режим «идеальный» или задать внутреннее сопротивление вручную/через переменную.

10) Конденсатор
- У конденсатора задаётся ёмкость C.
- В расчёте по постоянному току считается установившийся режим: ток через конденсатор не идет.
- Если напряжение на его выводах определяется схемой, приложение считает U, заряд Q = C*U и энергию W = C*U^2/2.
- Параметры меняются через ПКМ → Информация / изменить параметры...

11) Узел
- Узел ставится только на провод или в точку, где есть провод.
- Если поставить узел в середину провода, провод автоматически разделится на две части.
- К узлу можно подключать провод, резистор, источник, амперметр, вольтметр и конденсатор.

12) Параметры и информация
- ПКМ по элементу → Информация / изменить параметры...
- В меню элемента видно расчётные I, U и P. У конденсатора дополнительно показываются Q и W.
- Внизу есть панель «Выделенные элементы»: раскрой её, чтобы увидеть параметры всех выделенных элементов.
- Для амперметра и вольтметра там же видно их показания: ток и напряжение на приборе.

13) Создать схему (расчёт)
- Выдели элементы схемы.
- ПКМ по пустому месту → Создать схему.
- Справа снизу появится окно расчёта.
"""

THEORY_TEXT = """ТЕОРИЯ (что использует приложение)

Закон Ома: U = I*R
Мощность: P = U*I = I^2*R = U^2/R
Кирхгоф (KCL): сумма токов в узле = 0
Кирхгоф (KVL): сумма напряжений в контуре = 0
Метод узловых потенциалов: KCL через проводимости (1/R) + решение линейной системы
Источник с rвн: I = U / (rвн + Rнагрузки)

Амперметр включают последовательно. Идеальный амперметр имеет почти нулевое внутреннее сопротивление.
Вольтметр включают параллельно. Идеальный вольтметр имеет очень большое внутреннее сопротивление.
Узел — это точка подключения. Через узел можно соединять несколько элементов в одной точке схемы.
Ключ — управляемый элемент цепи. В этом приложении открыт = проводит, закрыт = не проводит.

Конденсатор: Q = C*U
Энергия конденсатора: W = C*U^2/2 = Q*U/2 = Q^2/(2*C)
В задачах на постоянный ток в установившемся режиме конденсатор считают разрывом цепи: через него ток не идет, но на нем может быть напряжение.
"""


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Прототип редактора схем")
        self.resize(1200, 800)

        self._dark = False
        self.scene = CircuitScene(cell_size=40)
        self.view = CircuitView(self.scene)
        self.setCentralWidget(self.view)

        self.toolbox = ToolboxWidget()
        self.toolbox.toggleRequested.connect(self._toggle_toolbox)

        self.dock = QtWidgets.QDockWidget("Инструменты", self)
        self.dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.toolbox)
        self.dock.setWidget(scroll)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dock)

        tb = self.addToolBar("UI")
        tb.setMovable(False)
        self.toggle_tools_btn = QtWidgets.QToolButton()
        self.toggle_tools_btn.setText("Инструменты")
        self.toggle_tools_btn.clicked.connect(self._toggle_toolbox)
        tb.addWidget(self.toggle_tools_btn)

        self._build_menubar()
        self.view.createSchemeRequested.connect(self._create_scheme)
        self.view.themeToggled.connect(self.set_theme)
        self.set_theme(False)

    def _build_menubar(self) -> None:
        mb = self.menuBar()
        guide = mb.addMenu("Руководство")
        act_controls = guide.addAction("Управление")
        act_theory = guide.addAction("Теория")
        act_controls.triggered.connect(lambda: TextDialog("Управление", GUIDE_TEXT, self).exec())
        act_theory.triggered.connect(lambda: TextDialog("Теория", THEORY_TEXT, self).exec())

    def set_theme(self, dark: bool) -> None:
        self._dark = bool(dark)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setStyleSheet(DARK_QSS if self._dark else LIGHT_QSS)
        self.scene.set_theme(self._dark)
        self.toolbox.apply_theme(self._dark)
        self.view.apply_theme(self._dark)
        for it in list(self.scene._items_by_id.values()):
            it.update()

    def _toggle_toolbox(self) -> None:
        self.dock.setVisible(not self.dock.isVisible())

    def _create_scheme(self) -> None:
        items = self.scene.items_for_analysis_from_selection()
        if not items:
            self.view.show_report("Ничего не выделено.\nВыдели элементы схемы и нажми ПКМ по пустому месту → «Создать схему».")
            return

        ok, report, data = analyze_scheme(items)
        if ok and "per_item" in data:
            self.scene.analysis_per_item = data.get("per_item", {})
            self.scene.analysis_total = data.get("total", {})
            self.scene.analysis_vars = data.get("vars", {})
            for it in items:
                it.update()
        else:
            self.scene.analysis_per_item = {}
            self.scene.analysis_total = {}
            self.scene.analysis_vars = data.get("vars", {})
            for it in items:
                it.update()

        self.view.show_report(report)


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

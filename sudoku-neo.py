#!/usr/bin/env python3
"""
Sudoku Neo - Advanced PyQt5 Sudoku
Features from sudoku.py and sudoku-glm.py:
  - 'j' for Write mode, 'k' for Mark (Notes) mode
  - Nested navigation: Big keys (wfprstxcd) + Small keys (luyneih,.)
  - F1: Toggle Hotkeys help
  - F2-F4: Difficulty adjustment
  - Esc: Exit
  - Number Status display (1-9)
  - Sidebar layout for controls and status
"""

import sys
import os
import random
import json
from copy import deepcopy
from datetime import datetime

# Suppress Qt font warning on Windows
os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts=false"

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QComboBox, QMessageBox,
    QStatusBar, QFrame, QSizePolicy, QLayout, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QGuiApplication
)

# ──────────────────────────────────────────────
#  Leaderboard Manager
# ──────────────────────────────────────────────

class LeaderboardManager:
    FILE_PATH = "sudoku_scores.json"

    @staticmethod
    def load_scores():
        if os.path.exists(LeaderboardManager.FILE_PATH):
            try:
                with open(LeaderboardManager.FILE_PATH, "r") as f:
                    return json.load(f)
            except:
                pass
        return {"easy": [], "medium": [], "hard": [], "expert": []}

    @staticmethod
    def save_score(difficulty, seconds):
        scores = LeaderboardManager.load_scores()
        entry = {
            "time": seconds,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        scores[difficulty].append(entry)
        # Sort by time (ascending) and keep top 10
        scores[difficulty].sort(key=lambda x: x["time"])
        scores[difficulty] = scores[difficulty][:10]
        
        with open(LeaderboardManager.FILE_PATH, "w") as f:
            json.dump(scores, f, indent=4)

class LeaderboardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Leaderboard")
        self.setFixedSize(400, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.tabs = QComboBox()
        self.tabs.addItems(["easy", "medium", "hard", "expert"])
        self.tabs.currentTextChanged.connect(self.update_table)
        layout.addWidget(self.tabs)

        self.table = QTableWidget(10, 3)
        self.table.setHorizontalHeaderLabels(["Rank", "Time", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        
        self.update_table(self.tabs.currentText())

    def update_table(self, difficulty):
        scores = LeaderboardManager.load_scores().get(difficulty, [])
        self.table.clearContents()
        for i in range(10):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            if i < len(scores):
                s = scores[i]
                mins, secs = divmod(s["time"], 60)
                self.table.setItem(i, 1, QTableWidgetItem(f"{mins:02d}:{secs:02d}"))
                self.table.setItem(i, 2, QTableWidgetItem(s["date"]))
            else:
                self.table.setItem(i, 1, QTableWidgetItem("-"))
                self.table.setItem(i, 2, QTableWidgetItem("-"))

# ──────────────────────────────────────────────
#  Sudoku Generator / Solver Engine
# ──────────────────────────────────────────────

class SudokuEngine:
    @staticmethod
    def is_valid(board, row, col, num):
        if num in board[row]:
            return False
        if any(board[r][col] == num for r in range(9)):
            return False
        box_r, box_c = 3 * (row // 3), 3 * (col // 3)
        for r in range(box_r, box_r + 3):
            for c in range(box_c, box_c + 3):
                if board[r][c] == num:
                    return False
        return True

    @staticmethod
    def solve(board):
        for r in range(9):
            for c in range(9):
                if board[r][c] == 0:
                    nums = list(range(1, 10))
                    random.shuffle(nums)
                    for num in nums:
                        if SudokuEngine.is_valid(board, r, c, num):
                            board[r][c] = num
                            if SudokuEngine.solve(board):
                                return True
                            board[r][c] = 0
                    return False
        return True

    @staticmethod
    def generate(difficulty="medium"):
        board = [[0] * 9 for _ in range(9)]
        SudokuEngine.solve(board)
        solution = deepcopy(board)

        cells_to_remove = {
            "easy":   30,
            "medium": 45,
            "hard":   55,
            "expert": 62,
        }.get(difficulty, 45)

        puzzle = deepcopy(solution)
        positions = [(r, c) for r in range(9) for c in range(9)]
        random.shuffle(positions)

        removed = 0
        for r, c in positions:
            if removed >= cells_to_remove:
                break
            backup = puzzle[r][c]
            puzzle[r][c] = 0
            test = deepcopy(puzzle)
            if SudokuEngine.count_solutions(test, limit=2) == 1:
                removed += 1
            else:
                puzzle[r][c] = backup

        return puzzle, solution

    @staticmethod
    def count_solutions(board, limit=2):
        count = [0]
        def _solve(b):
            if count[0] >= limit: return
            for r in range(9):
                for c in range(9):
                    if b[r][c] == 0:
                        for num in range(1, 10):
                            if SudokuEngine.is_valid(b, r, c, num):
                                b[r][c] = num
                                _solve(b)
                                b[r][c] = 0
                        return
            count[0] += 1
        _solve(board)
        return count[0]

    @staticmethod
    def validate_board(board):
        conflicts = set()
        for r in range(9):
            for c in range(9):
                num = board[r][c]
                if num == 0: continue
                for cc in range(9):
                    if cc != c and board[r][cc] == num:
                        conflicts.add((r, c)); conflicts.add((r, cc))
                for rr in range(9):
                    if rr != r and board[rr][c] == num:
                        conflicts.add((r, c)); conflicts.add((rr, c))
                box_r, box_c = 3 * (r // 3), 3 * (c // 3)
                for rr in range(box_r, box_r + 3):
                    for cc in range(box_c, box_c + 3):
                        if (rr, cc) != (r, c) and board[rr][cc] == num:
                            conflicts.add((r, c)); conflicts.add((rr, cc))
        return conflicts

# ──────────────────────────────────────────────
#  Sudoku Cell Widget
# ──────────────────────────────────────────────

class SudokuCell(QLabel):
    """A single cell in the Sudoku grid."""
    clicked = pyqtSignal(int, int)

    def __init__(self, row, col, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.value = 0
        self.given = False
        self.notes = set()
        self.error = False
        self.selected = False
        self.highlighted = False
        self.same_number = False

        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(56, 56)
        self._set_main_font()
        self.update_style()

    def _set_main_font(self):
        font = QFont("Consolas", 28, QFont.Bold)
        self.setFont(font)

    def _set_notes_font(self):
        font = QFont("Consolas", 9)
        self.setFont(font)

    def set_value(self, val):
        if self.given:
            return
        self.value = val
        if val != 0:
            self.notes.clear()
            self.setText(str(val))
            self._set_main_font()
        else:
            self.setText("")
            self._set_main_font()
        self.update_style()

    def set_notes(self, notes_set):
        if self.given:
            return
        self.notes = notes_set.copy()
        if self.value == 0 and self.notes:
            lines = []
            for i in range(0, 9, 3):
                chunk = self.notes.intersection(range(i + 1, i + 4))
                lines.append(" ".join(str(n) for n in sorted(chunk)) if chunk else "  ")
            self.setText("\n".join(lines))
            self._set_notes_font()
        elif self.value == 0:
            self.setText("")
        self.update_style()

    def update_style(self):
        bg = "#FFFFFF"
        fg = "#2C3E50"

        if self.selected:
            bg = "#BBDEFB"
        elif self.same_number and not self.given:
            bg = "#E3F2FD"
        elif self.highlighted:
            bg = "#F5F5F5"

        if self.error:
            fg = "#E74C3C"
        elif self.given:
            fg = "#1A1A2E"
        else:
            fg = "#2980B9"

        border_top = 1
        border_left = 1
        border_bottom = 1
        border_right = 1

        if self.row % 3 == 0:
            border_top = 2
        if self.row == 8:
            border_bottom = 2
        if self.col % 3 == 0:
            border_left = 2
        if self.col == 8:
            border_right = 2

        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-top: {border_top}px solid #555;
                border-left: {border_left}px solid #555;
                border-bottom: {border_bottom}px solid #555;
                border-right: {border_right}px solid #555;
                font-weight: bold;
            }}
            """
        )

    def mousePressEvent(self, event):
        self.clicked.emit(self.row, self.col)
        super().mousePressEvent(event)


# ──────────────────────────────────────────────
#  Number Pad Widget
# ──────────────────────────────────────────────

class NumberPad(QWidget):
    """Row of buttons 1-9 + erase."""
    number_selected = pyqtSignal(int)
    erase_selected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)

        num_btn_style = """
            QPushButton {
                background-color: #3498DB;
                color: white;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #1F6DA3;
            }
        """

        for i in range(1, 10):
            btn = QPushButton(str(i))
            btn.setFixedSize(44, 44)
            btn.setFont(QFont("Segoe UI", 16, QFont.Bold))
            btn.setStyleSheet(num_btn_style)
            btn.clicked.connect(lambda checked, n=i: self.number_selected.emit(n))
            layout.addWidget(btn)

        erase_btn = QPushButton("\u2715")
        erase_btn.setFixedSize(44, 44)
        erase_btn.setFont(QFont("Segoe UI", 18, QFont.Bold))
        erase_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QPushButton:pressed {
                background-color: #A93226;
            }
        """)
        erase_btn.clicked.connect(self.erase_selected.emit)
        layout.addWidget(erase_btn)


# ──────────────────────────────────────────────
#  Sudoku Grid Widget
# ──────────────────────────────────────────────

class SudokuGrid(QWidget):
    cell_selected = pyqtSignal(int, int)
    board_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cells = [[None] * 9 for _ in range(9)]
        self.selected_pos = (0, 0)
        self.notes_mode = False
        self.undo_stack = []

        layout = QGridLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        for r in range(9):
            for c in range(9):
                cell = SudokuCell(r, c)
                cell.clicked.connect(self.on_cell_clicked)
                self.cells[r][c] = cell
                layout.addWidget(cell, r, c)
        
        self.update_highlights()

    def load_puzzle(self, puzzle):
        self.undo_stack.clear()
        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                val = puzzle[r][c]
                if val != 0:
                    cell.value = val
                    cell.given = True
                    cell.setText(str(val))
                    cell.notes.clear()
                else:
                    cell.value = 0
                    cell.given = False
                    cell.setText("")
                    cell.notes.clear()
                cell.error = False
                cell._set_main_font()
                cell.update_style()
        self.update_highlights()

    def on_cell_clicked(self, row, col):
        self.selected_pos = (row, col)
        self.update_highlights()
        self.cell_selected.emit(row, col)

    def update_highlights(self):
        sr, sc = self.selected_pos
        selected_val = self.cells[sr][sc].value
        box_r, box_c = 3 * (sr // 3), 3 * (sc // 3)

        for r in range(9):
            for c in range(9):
                cell = self.cells[r][c]
                cell.selected = (r == sr and c == sc)
                cell.highlighted = (
                    r == sr or c == sc or
                    (box_r <= r < box_r + 3 and box_c <= c < box_c + 3)
                )
                cell.same_number = (selected_val != 0 and cell.value == selected_val)
                cell.update_style()

    def place_number(self, num):
        r, c = self.selected_pos
        cell = self.cells[r][c]
        if cell.given: return
        self.undo_stack.append((r, c, cell.value, cell.notes.copy()))
        if self.notes_mode and num != 0:
            if num in cell.notes: cell.notes.discard(num)
            else: cell.notes.add(num)
            cell.value = 0
            cell.set_notes(cell.notes)
        else:
            cell.set_value(num)
        self.validate_and_mark()
        self.update_highlights()
        self.board_changed.emit()

    def erase_cell(self):
        r, c = self.selected_pos
        cell = self.cells[r][c]
        if cell.given: return
        self.undo_stack.append((r, c, cell.value, cell.notes.copy()))
        cell.set_value(0)
        cell.notes.clear()
        cell.set_notes(set())
        self.validate_and_mark()
        self.update_highlights()
        self.board_changed.emit()

    def undo(self):
        if not self.undo_stack: return
        r, c, old_val, old_notes = self.undo_stack.pop()
        cell = self.cells[r][c]
        if cell.given: return
        cell.value = old_val
        cell.notes = old_notes
        if old_val:
            cell.set_value(old_val)
        else:
            cell.set_notes(old_notes)
        self.validate_and_mark()
        self.update_highlights()
        self.board_changed.emit()

    def validate_and_mark(self):
        board = [[self.cells[r][c].value for c in range(9)] for r in range(9)]
        conflicts = SudokuEngine.validate_board(board)
        for r in range(9):
            for c in range(9):
                self.cells[r][c].error = (r, c) in conflicts
                self.cells[r][c].update_style()

    def get_board(self):
        return [[self.cells[r][c].value for c in range(9)] for r in range(9)]

    def is_complete(self, solution):
        board = self.get_board()
        for r in range(9):
            for c in range(9):
                if board[r][c] != solution[r][c]:
                    return False
        return True

    def move_selection(self, dr, dc):
        r, c = self.selected_pos
        r = (r + dr) % 9
        c = (c + dc) % 9
        self.on_cell_clicked(r, c)

# ──────────────────────────────────────────────
#  Sidebar Components
# ──────────────────────────────────────────────

class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.setFixedWidth(260)

# ──────────────────────────────────────────────
#  Main Window
# ──────────────────────────────────────────────

class SudokuWindow(QMainWindow):
    # Windows 11 friendly emoji or plain text fallbacks
    ICON_NEW    = "\U0001F504"   # 🔄
    ICON_UNDO   = "\u21A9"      # ↩
    ICON_HINT   = "\U0001F4A1"  # 💡
    ICON_NOTES  = "\u270F"      # ✏
    ICON_CHECK  = "\u2713"       # ✓
    ICON_SOLVE  = "\U0001F3C6"  # 🏆
    ICON_TIMER  = "\u23F1"      # ⏱
    ICON_HELP   = "\u2753"      # ❓
    ICON_QUIT   = "\u274C"      # ❌

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sudoku Neo")
        self.solution = None
        self.puzzle = None
        self.difficulty = "medium"
        self.elapsed = 0
        self.timer_running = False
        
        self.held_big = None
        self.held_small = None
        
        # Keyboard Layouts
        self.layouts = {
            "qwerty": {
                "big": "wersdfxcv",
                "small": "uiojklm,."
            },
            "colemak": {
                "big": "wfprstxcv",
                "small": "luyneih,."
            },
            "colemak_dh": {
                "big": "wfprstxcd",
                "small": "luyneih,."
            },
            "dvorak": {
                "big": ",.poeuqjk",
                "small": "gcrhtnmwv"
            },
            "workman": {
                "big": "drwshtxmc",
                "small": "fupneol,."
            },
            "custom": {
                "big": "123456789",
                "small": "abcdefghi"
            }
        }
        self.current_layout_name = "qwerty"
        self.big_keys = self.layouts[self.current_layout_name]["big"]
        self.small_keys = self.layouts[self.current_layout_name]["small"]
        
        self.init_ui()

        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        self.sidebar_widget.hide()  # Hide by default
        self.new_game()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.outer_layout = QVBoxLayout(central)
        self.outer_layout.setContentsMargins(12, 12, 12, 12)
        self.outer_layout.setSpacing(10)

        # ── Top bar (Timer & Difficulty & Layout) ──
        self.top_container = QWidget()
        self.top_bar = QHBoxLayout(self.top_container)
        self.top_bar.setContentsMargins(0, 0, 0, 0)
        
        diff_label = QLabel("Difficulty:")
        diff_label.setFont(QFont("Segoe UI", 12))
        self.top_bar.addWidget(diff_label)

        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["easy", "medium", "hard", "expert"])
        self.diff_combo.setCurrentText("medium")
        self.diff_combo.setFont(QFont("Segoe UI", 11))
        self.diff_combo.setMinimumWidth(110)
        self.diff_combo.currentTextChanged.connect(self.on_difficulty_changed)
        self.top_bar.addWidget(self.diff_combo)

        self.top_bar.addSpacing(10)
        
        layout_label = QLabel("Layout:")
        layout_label.setFont(QFont("Segoe UI", 12))
        self.top_bar.addWidget(layout_label)

        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["qwerty", "colemak", "colemak_dh", "dvorak", "workman", "custom"])
        self.layout_combo.setCurrentText(self.current_layout_name)
        self.layout_combo.setFont(QFont("Segoe UI", 11))
        self.layout_combo.setMinimumWidth(120)
        self.layout_combo.currentTextChanged.connect(self.on_layout_changed)
        self.top_bar.addWidget(self.layout_combo)

        self.top_bar.addStretch()

        self.timer_label = QLabel(f"{self.ICON_TIMER} 00:00")
        self.timer_label.setFont(QFont("Consolas", 18, QFont.Bold))
        self.timer_label.setStyleSheet("color: #2C3E50;")
        self.top_bar.addWidget(self.timer_label)
        self.outer_layout.addWidget(self.top_container)

        # ── Main Content Area (Grid + Sidebar) ──
        self.content_container = QWidget()
        self.main_layout = QHBoxLayout(self.content_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)
        
        # Left Side: Grid & Buttons (Locked width to prevent jumps)
        self.left_container = QWidget()
        self.left_container.setFixedWidth(550)
        self.left_side = QVBoxLayout(self.left_container)
        self.left_side.setContentsMargins(0, 0, 0, 0)
        self.left_side.setSpacing(10)
        
        self.grid = SudokuGrid()
        self.grid.cell_selected.connect(self.on_cell_selected)
        self.grid.board_changed.connect(self.on_board_changed)
        
        self.grid_frame = QFrame()
        self.grid_frame.setStyleSheet("""
            QFrame {
                background-color: #555;
                border: 3px solid #333;
                border-radius: 4px;
            }
        """)
        self.grid_layout = QVBoxLayout(self.grid_frame)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        self.grid_layout.addWidget(self.grid)
        self.left_side.addWidget(self.grid_frame, alignment=Qt.AlignCenter)

        # Number Pad
        self.number_pad = NumberPad()
        self.number_pad.number_selected.connect(self.on_number_selected)
        self.number_pad.erase_selected.connect(self.on_erase)
        self.left_side.addWidget(self.number_pad, alignment=Qt.AlignCenter)
        
        # ── Control Buttons Bar ──
        self.ctrl_container = QWidget()
        self.ctrl_layout = QHBoxLayout(self.ctrl_container)
        self.ctrl_layout.setSpacing(8)
        self.ctrl_layout.setContentsMargins(0, 0, 0, 0)

        btn_style = """
            QPushButton {
                background-color: #2C3E50;
                color: white;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: bold;
                min-height: 40px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #34495E;
            }
            QPushButton:pressed {
                background-color: #1A252F;
            }
            QPushButton:checked {
                background-color: #1A252F;
                border: 2px solid #3498DB;
            }
        """

        self.new_game_btn = QPushButton(f"{self.ICON_NEW}\nNew")
        self.new_game_btn.setStyleSheet(btn_style)
        self.new_game_btn.clicked.connect(self.new_game)
        self.ctrl_layout.addWidget(self.new_game_btn)

        self.undo_btn = QPushButton(f"{self.ICON_UNDO}\nUndo")
        self.undo_btn.setStyleSheet(btn_style)
        self.undo_btn.clicked.connect(self.grid.undo)
        self.ctrl_layout.addWidget(self.undo_btn)

        self.hint_btn = QPushButton(f"{self.ICON_HINT}\nHint")
        self.hint_btn.setStyleSheet(btn_style)
        self.hint_btn.clicked.connect(self.give_hint)
        self.ctrl_layout.addWidget(self.hint_btn)

        self.notes_btn = QPushButton(f"{self.ICON_NOTES}\nNotes")
        self.notes_btn.setStyleSheet(btn_style)
        self.notes_btn.setCheckable(True)
        self.notes_btn.toggled.connect(self.on_notes_toggled)
        self.ctrl_layout.addWidget(self.notes_btn)

        self.solve_btn = QPushButton(f"{self.ICON_SOLVE}\nSolve")
        self.solve_btn.setStyleSheet(btn_style)
        self.solve_btn.clicked.connect(self.show_solution)
        self.ctrl_layout.addWidget(self.solve_btn)

        self.toggle_help_btn = QPushButton(f"{self.ICON_HELP}\nHelp")
        self.toggle_help_btn.setStyleSheet(btn_style)
        self.toggle_help_btn.clicked.connect(self.toggle_sidebar)
        self.ctrl_layout.addWidget(self.toggle_help_btn)

        self.quit_btn = QPushButton(f"{self.ICON_QUIT}\nQuit")
        self.quit_btn.setStyleSheet(btn_style)
        self.quit_btn.clicked.connect(self.confirm_quit)
        self.ctrl_layout.addWidget(self.quit_btn)
        
        self.left_side.addWidget(self.ctrl_container)
        self.main_layout.addWidget(self.left_container)

        # Right Side: Sidebar
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(260)
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_layout.setSpacing(10)
        self.sidebar_layout.setContentsMargins(10, 0, 0, 0)
        
        # Help Text
        self.help_label = QLabel(
            "CONTROLS\n"
            "──────────────\n"
            "[Esc]   Quit\n"
            "[0/Spc] Clear\n"
            "[F1]    Toggle Help\n"
            "[F5]    Leaderboard\n"
            "[=]     WRITE Mode\n"
            "[-]     MARK Mode\n"
            "[Ctrl+Z] Undo\n\n"
            "STENO LOCATE\n"
            "──────────────\n"
            "Hold BIG + Tap SMALL\n"
        )
        self.help_label.setFont(QFont("Consolas", 10))
        self.help_label.setStyleSheet("color: #2C3E50;")
        self.sidebar_layout.addWidget(self.help_label)
        
        # Big/Small Key Grids
        self.big_grid_ui_container = QWidget()
        self.big_grid_ui = QGridLayout(self.big_grid_ui_container)
        self.big_grid_ui.setSpacing(3)
        self.big_grid_ui.setContentsMargins(0, 0, 0, 0)
        self.big_labels = {}
        
        self.small_grid_ui_container = QWidget()
        self.small_grid_ui = QGridLayout(self.small_grid_ui_container)
        self.small_grid_ui.setSpacing(3)
        self.small_grid_ui.setContentsMargins(0, 0, 0, 0)
        self.small_labels = {}

        self.update_layout_ui()

        self.sidebar_layout.addWidget(QLabel("BIG (Block):"))
        self.sidebar_layout.addWidget(self.big_grid_ui_container)
        self.sidebar_layout.addWidget(QLabel("SMALL (Cell):"))
        self.sidebar_layout.addWidget(self.small_grid_ui_container)
        
        # Number Status
        status_label = QLabel("NUMBER STATUS")
        status_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.sidebar_layout.addWidget(status_label)
        self.status_grid = QGridLayout()
        self.status_grid.setSpacing(3)
        self.num_labels = {}
        for i in range(1, 10):
            r, c = divmod(i-1, 3)
            lbl = QLabel(str(i))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(34, 34)
            lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
            lbl.setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; color: #3498DB;")
            self.status_grid.addWidget(lbl, r, c)
            self.num_labels[i] = lbl
        self.sidebar_layout.addLayout(self.status_grid)
        self.sidebar_layout.addStretch()
        
        self.main_layout.addWidget(self.sidebar_widget)
        self.outer_layout.addWidget(self.content_container)

    def update_layout_ui(self):
        # Clear existing labels
        for lbl in self.big_labels.values(): lbl.deleteLater()
        for lbl in self.small_labels.values(): lbl.deleteLater()
        self.big_labels.clear()
        self.small_labels.clear()

        for i, char in enumerate(self.big_keys):
            r, c = divmod(i, 3)
            lbl = QLabel(char.upper())
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(34, 34)
            lbl.setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; color: #2C3E50; font-weight: bold;")
            self.big_grid_ui.addWidget(lbl, r, c)
            self.big_labels[char.lower()] = lbl

        for i, char in enumerate(self.small_keys):
            r, c = divmod(i, 3)
            lbl = QLabel(char.upper())
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(34, 34)
            lbl.setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; color: #2C3E50; font-weight: bold;")
            self.small_grid_ui.addWidget(lbl, r, c)
            self.small_labels[char.lower()] = lbl

    def on_layout_changed(self, text):
        self.current_layout_name = text
        self.big_keys = self.layouts[text]["big"]
        self.small_keys = self.layouts[text]["small"]
        self.update_layout_ui()
        self.setFocus()

    def toggle_sidebar(self):
        if self.sidebar_widget.isVisible():
            self.sidebar_widget.hide()
            self.setFixedSize(580, 750)
        else:
            self.sidebar_widget.show()
            self.setFixedSize(850, 750)

    def confirm_quit(self):
        reply = QMessageBox.question(
            self, "Quit Game",
            "Do you want to quit the game? (Y/N)",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()

    def new_game(self):
        self.difficulty = self.diff_combo.currentText()
        self.puzzle, self.solution = SudokuEngine.generate(self.difficulty)
        self.grid.load_puzzle(self.puzzle)
        self.elapsed = 0
        self.timer_running = True
        self.timer.start(1000)
        self.update_timer_label()
        self.update_num_status()
        self.statusBar().showMessage(f"New {self.difficulty} game started.")
        self.setFocus()  # Ensure window has focus for keys

    def on_difficulty_changed(self, text):
        self.difficulty = text
        self.new_game()

    def on_number_selected(self, num):
        self.grid.place_number(num)

    def on_erase(self):
        self.grid.erase_cell()

    def on_notes_toggled(self, enabled):
        self.grid.notes_mode = enabled

    def update_num_status(self):
        board = self.grid.get_board()
        counts = {i: 0 for i in range(1, 10)}
        for r in range(9):
            for c in range(9):
                val = board[r][c]
                if 1 <= val <= 9: counts[val] += 1
        
        for i in range(1, 10):
            if counts[i] >= 9:
                self.num_labels[i].setStyleSheet("background-color: #E74C3C; color: white; border: 1px solid #C0392B; border-radius: 4px;")
            else:
                self.num_labels[i].setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; color: #3498DB;")

    def on_board_changed(self):
        self.update_num_status()
        if self.grid.is_complete(self.solution):
            self.timer_running = False
            self.timer.stop()
            LeaderboardManager.save_score(self.difficulty, self.elapsed)
            QMessageBox.information(self, "Congratulations!", f"🎉 Puzzle Solved!\nTime: {self.timer_label.text()[2:]}")
            self.show_leaderboard()
            self.new_game()

    def show_leaderboard(self):
        dlg = LeaderboardDialog(self)
        dlg.tabs.setCurrentText(self.difficulty)
        dlg.exec_()

    def on_cell_selected(self, r, c):
        val = self.grid.cells[r][c].value
        if val:
            self.statusBar().showMessage(f"Cell ({r+1},{c+1}): {val}")
        else:
            self.statusBar().showMessage(f"Cell ({r+1},{c+1})")

    def give_hint(self):
        r, c = self.grid.selected_pos
        if not self.grid.cells[r][c].given:
            self.grid.cells[r][c].set_value(self.solution[r][c])
            self.grid.cells[r][c].given = True
            self.grid.validate_and_mark()
            self.grid.update_highlights()
            self.on_board_changed()

    def show_solution(self):
        reply = QMessageBox.question(
            self, "Show Solution?",
            "Are you sure you want to reveal the solution?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.timer_running = False
            self.timer.stop()
            for r in range(9):
                for c in range(9):
                    cell = self.grid.cells[r][c]
                    cell.set_value(self.solution[r][c])
                    cell.given = True
                    cell.error = False
                    cell.update_style()
            self.on_board_changed()

    def update_timer(self):
        self.elapsed += 1
        self.update_timer_label()

    def update_timer_label(self):
        mins = self.elapsed // 60
        secs = self.elapsed % 60
        self.timer_label.setText(f"{self.ICON_TIMER} {mins:02d}:{secs:02d}")

    def locate_nested(self):
        if self.held_big is not None and self.held_small is not None:
            br, bc = divmod(self.held_big, 3)
            sr, sc = divmod(self.held_small, 3)
            tr, tc = br * 3 + sr, bc * 3 + sc
            self.grid.on_cell_clicked(tr, tc)

    def keyPressEvent(self, event):
        key = event.key()
        
        if key == Qt.Key_Escape:
            self.confirm_quit()
            return
        elif key == Qt.Key_F1:
            self.toggle_sidebar()
            return
        elif key == Qt.Key_F5:
            self.show_leaderboard()
            return
        elif key == Qt.Key_F2:
            self.diff_combo.setCurrentText("easy")
            return
        elif key == Qt.Key_F3:
            self.diff_combo.setCurrentText("medium")
            return
        elif key == Qt.Key_F4:
            self.diff_combo.setCurrentText("hard")
            return
        elif key == Qt.Key_F8:
            self.give_hint()
            return
        elif key == Qt.Key_F9:
            self.show_solution()
            return
        elif key == Qt.Key_F10:
            self.new_game()
            return
        elif key == Qt.Key_Up:
            self.grid.move_selection(-1, 0)
            return
        elif key == Qt.Key_Down:
            self.grid.move_selection(1, 0)
            return
        elif key == Qt.Key_Left:
            self.grid.move_selection(0, -1)
            return
        elif key == Qt.Key_Right:
            self.grid.move_selection(0, 1)
            return
        elif key == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            self.grid.undo()
            return

        char = event.text().lower()
        if not char:
            return
        
        if char == '=':
            self.notes_btn.setChecked(False)
        elif char == '-':
            self.notes_btn.setChecked(True)
        elif char in self.big_keys:
            self.held_big = self.big_keys.index(char)
            self.big_labels[char].setStyleSheet("background-color: #3498DB; color: white; border: 1px solid #2980B9; border-radius: 4px; font-weight: bold;")
            self.locate_nested()
        elif char in self.small_keys:
            self.held_small = self.small_keys.index(char)
            self.small_labels[char].setStyleSheet("background-color: #3498DB; color: white; border: 1px solid #2980B9; border-radius: 4px; font-weight: bold;")
            self.locate_nested()
        elif Qt.Key_1 <= key <= Qt.Key_9:
            self.grid.place_number(key - Qt.Key_0)
        elif key in (Qt.Key_0, Qt.Key_Space, Qt.Key_Backspace, Qt.Key_Delete):
            self.grid.erase_cell()

    def keyReleaseEvent(self, event):
        char = event.text().lower()
        if not char:
            return
        if char in self.big_keys:
            self.held_big = None
            self.big_labels[char].setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; color: #2C3E50; font-weight: bold;")
        elif char in self.small_keys:
            self.held_small = None
            self.small_labels[char].setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; color: #2C3E50; font-weight: bold;")

if __name__ == "__main__":
    # ── High-DPI support for Windows 11 ──
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Application-wide font
    font = QFont("Segoe UI", 11)
    app.setFont(font)

    # Fusion palette with polished colors
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor("#ECF0F1"))
    palette.setColor(QPalette.WindowText,      QColor("#2C3E50"))
    palette.setColor(QPalette.Base,            QColor("#FFFFFF"))
    palette.setColor(QPalette.AlternateBase,   QColor("#F5F5F5"))
    palette.setColor(QPalette.ToolTipBase,     QColor("#2C3E50"))
    palette.setColor(QPalette.ToolTipText,     QColor("#FFFFFF"))
    palette.setColor(QPalette.Text,            QColor("#2C3E50"))
    palette.setColor(QPalette.Button,          QColor("#BDC3C7"))
    palette.setColor(QPalette.ButtonText,     QColor("#2C3E50"))
    palette.setColor(QPalette.Highlight,       QColor("#3498DB"))
    palette.setColor(QPalette.HighlightedText,  QColor("#FFFFFF"))
    app.setPalette(palette)

    window = SudokuWindow()
    window.show()
    sys.exit(app.exec_())


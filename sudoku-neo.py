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
import time
import winsound
import threading
import ctypes
import struct
from pathlib import Path
from copy import deepcopy
from datetime import datetime



def resource_path(*parts):
    """Return an absolute path to a bundled resource.

    When frozen by PyInstaller, resources live in ``sys._MEIPASS`` (a temp
    directory created at launch). In dev, fall back to the script's own
    directory so the same code works both ways.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def user_data_path(filename):
    """Return a writable per-user path for save data (leaderboards, etc.)."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "sudoku-neo")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        pass
    return os.path.join(folder, filename)


# Suppress Qt font warning on Windows
os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts=false"

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QComboBox, QMessageBox,
    QStatusBar, QFrame, QSizePolicy, QLayout, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QGuiApplication
)

LANGUAGES = {
    "en": "English",
    "zh_cn": "普通话（简化字）",
    "zh_tw": "國語（繁體字）",
}

DIFFICULTIES = ["easy", "medium", "hard", "expert"]

# ── Modes (Normal / Versus AI / Mission / Fog) ──
MODES = ["normal", "versus", "mission", "fog"]

# Normal mode sub-levels: id, desc_key, cells_to_remove
NORMAL_SUBLEVELS = [
    ("chujie",   "diff_chujie",   30),
    ("zhongjie", "diff_zhongjie", 36),
    ("gaojie",   "diff_gaojie",   42),
    ("dashi",    "diff_dashi",    48),
    ("chuanqi",  "diff_chuanqi",  54),
    ("shenhua",  "diff_shenhua",  62),
]
NORMAL_SUBLEVEL_KEYS = {k for k, _, _ in NORMAL_SUBLEVELS}

# Versus AI sub-levels: id, desc_key, cadence_seconds
VERSUS_SUBLEVELS = [
    ("v_easy",   "versus_easy_ai",   15.0),
    ("v_medium", "versus_medium_ai", 12.0),
    ("v_hard",   "versus_hard_ai",   10.0),
]

# Mission catalog (36): category, desc_key, target
MISSION_CATALOG = [
    *[("fill_small_block", "mission_fill_block", i) for i in range(9)],
    *[("show_number_n", "mission_show_n", n) for n in range(1, 10)],
    ("complete_row", "mission_complete_rows", 1),
    ("complete_row", "mission_complete_rows", 2),
    ("complete_row", "mission_complete_rows", 3),
    ("complete_col", "mission_complete_cols", 1),
    ("complete_col", "mission_complete_cols", 2),
    ("complete_col", "mission_complete_cols", 3),
    ("complete_box_set", "mission_complete_band", 0),
    ("complete_box_set", "mission_complete_band", 1),
    ("complete_box_set", "mission_complete_band", 2),
    ("hint_free",        "mission_hint_free",     None),
    ("no_mistake",       "mission_no_mistake",    None),
    ("speed_run",        "mission_speed_run",     None),
    ("undo_free",        "mission_undo_free",     None),
    ("first_move",       "mission_first_move",    None),
    ("diagonal_corners", "mission_corners",       None),
    ("no_notes",         "mission_no_notes",      None),
    ("center_block",     "mission_center_block",  None),
    ("row_sum_45",       "mission_row_sum_45",    None),
]

TRANSLATIONS = {
    "en": {
        "app_title": "Sudoku Neo",
        "new": "New",
        "undo": "Undo",
        "hint": "Hint",
        "notes": "Notes",
        "solve": "Solve",
        "help": "Help",
        "quit": "Quit",
        "numbers": "Numbers:",
        "difficulty": "Difficulty:",
        "layout": "Layout:",
        "language": "Language:",
        "big_block": "BIG (Block):",
        "small_cell": "SMALL (Cell):",
        "number_status": "NUMBER STATUS",
        "leaderboard": "Leaderboard",
        "rank": "Rank",
        "time": "Time",
        "date": "Date",
        "quit_game": "Quit Game",
        "quit_game_msg": "Do you want to quit the game? (Y/N)",
        "start_game": "Start Game?",
        "start_game_msg": "Do you want to start a new game?",
        "congratulations": "Congratulations!",
        "puzzle_solved": "Puzzle Solved!",
        "show_solution": "Show Solution?",
        "show_solution_msg": "Are you sure you want to reveal the solution?",
        "yes": "Yes",
        "no": "No",
        "ok": "OK",
        "bgm_playing": "BGM: Playing",
        "bgm_paused": "BGM: Paused",
        "bgm_changing": "BGM: Changing track...",
        "cell": "Cell",
        "new_game_status": "New {difficulty} game started.",
        "auto_8s": "auto 8s",
        "diff_easy": "easy",
        "diff_medium": "medium",
        "diff_hard": "hard",
        "diff_expert": "expert",
        "mode_label": "Mode:",
        "mode_normal": "Normal",
        "mode_versus": "Versus AI",
        "mode_mission": "Mission",
        "mode_fog": "Fog",
        "fog_status": "Fog: {kind} revealed",
        "fog_row": "row {n}",
        "fog_col": "column {n}",
        "fog_box": "box {n}",
        "fog_locked": "Locked by fog",
        "fog_locked_msg": "Fog covers this cell. You can only edit cells in the revealed row/column/box.",
        "tab_versus": "Versus",
        "tab_mission": "Mission",
        "diff_chujie": "Beginner",
        "diff_zhongjie": "Intermediate",
        "diff_gaojie": "Advanced",
        "diff_dashi": "Expert",
        "diff_chuanqi": "Legend",
        "diff_shenhua": "Mythic",
        "versus_easy_ai": "Easy AI",
        "versus_medium_ai": "Medium AI",
        "versus_hard_ai": "Hard AI",
        "versus_random": "Random",
        "versus_player_turn": "Your turn",
        "versus_ai_turn": "AI's turn",
        "versus_player_win": "You win!",
        "versus_ai_win": "AI wins",
        "versus_draw": "Draw",
        "mission_panel": "Missions",
        "mission_completed": "Done",
        "missions_done": "All missions complete!",
        "mission_score": "Score",
        "mission_fill_block": "Complete small block {n}",
        "mission_show_n": "Place all nine {n}'s on the board",
        "mission_complete_rows": "Complete {n} full row(s)",
        "mission_complete_cols": "Complete {n} full column(s)",
        "mission_complete_band": "Complete every block in band {n}",
        "mission_hint_free": "Finish without using the Hint button",
        "mission_no_mistake": "Finish without entering a single wrong digit",
        "mission_speed_run": "Fill any 3×3 sub-block within 60 seconds",
        "mission_undo_free": "Finish without using Undo",
        "mission_first_move": "Place one correct digit within 30 seconds of start",
        "mission_corners": "Fill the four corner cells",
        "mission_no_notes": "Complete a full row without ever toggling Notes mode",
        "mission_center_block": "Fill the center 3×3 sub-block",
        "mission_row_sum_45": "Complete any row (its digits must sum to 45)",
        "help_pages": [
            ["ESC: Quit", "F1: Help Sidebar", "F2: BGM On/Off", "F3: BGM Next", "F5: Scores"],
            ["F8: Hint", "F9: Solve", "F10: New Game", "CTRL+Z: Undo", "Arrows: Navigation"],
            ["Phys N: Write Mode", "Phys B: Mark Mode", "Hold N + Left 9-sq: Write Digit", "Hold B + Right 9-sq: Mark Note"],
            ["A/G/H/;: Write Add (Sum)", "Q/T/Y/P: Mark Add (Sum)", "Big Key + Small Key: Precision", "1-9: Direct Entry", "SPACE/DEL: Erase"],
            ["Fog: every 8s a row/col/box is revealed", "Locked cells (\u2588) cannot be edited"],
        ],
    },
    "zh_cn": {
        "app_title": "数独 Neo",
        "new": "新游戏",
        "undo": "撤销",
        "hint": "提示",
        "notes": "笔记",
        "solve": "解答",
        "help": "帮助",
        "quit": "退出",
        "numbers": "数字：",
        "difficulty": "难度：",
        "layout": "键盘布局：",
        "language": "语言：",
        "big_block": "大格（宫）：",
        "small_cell": "小格（单元）：",
        "number_status": "数字状态",
        "leaderboard": "排行榜",
        "rank": "排名",
        "time": "时间",
        "date": "日期",
        "quit_game": "退出游戏",
        "quit_game_msg": "要退出游戏吗？",
        "start_game": "开始游戏？",
        "start_game_msg": "要开始一局新游戏吗？",
        "congratulations": "恭喜！",
        "puzzle_solved": "谜题已完成！",
        "show_solution": "显示答案？",
        "show_solution_msg": "确定要显示答案吗？",
        "yes": "是",
        "no": "否",
        "ok": "确定",
        "bgm_playing": "背景音乐：播放中",
        "bgm_paused": "背景音乐：已暂停",
        "bgm_changing": "背景音乐：正在切换曲目...",
        "cell": "格子",
        "new_game_status": "新的{difficulty}游戏已开始。",
        "auto_8s": "每 8 秒自动",
        "diff_easy": "简单",
        "diff_medium": "中等",
        "diff_hard": "困难",
        "diff_expert": "专家",
        "mode_label": "模式：",
        "mode_normal": "闯关",
        "mode_versus": "对战 AI",
        "mode_mission": "任务",
        "mode_fog": "迷雾",
        "fog_status": "迷雾：已显 {kind}",
        "fog_row": "第 {n} 行",
        "fog_col": "第 {n} 列",
        "fog_box": "第 {n} 宫",
        "fog_locked": "迷雾遮挡",
        "fog_locked_msg": "该格被迷雾遮挡，只能填写已显行/列/宫内的格子。",
        "tab_versus": "对战",
        "tab_mission": "任务",
        "diff_chujie": "初阶",
        "diff_zhongjie": "中阶",
        "diff_gaojie": "高阶",
        "diff_dashi": "大师",
        "diff_chuanqi": "传奇",
        "diff_shenhua": "神话",
        "versus_easy_ai": "简单 AI",
        "versus_medium_ai": "普通 AI",
        "versus_hard_ai": "困难 AI",
        "versus_random": "随机",
        "versus_player_turn": "你的回合",
        "versus_ai_turn": "AI 回合",
        "versus_player_win": "你赢了！",
        "versus_ai_win": "AI 走完最后一步",
        "versus_draw": "平局",
        "mission_panel": "任务",
        "mission_completed": "完成",
        "missions_done": "全部任务完成！",
        "mission_score": "得分",
        "mission_fill_block": "填满第 {n} 个小宫",
        "mission_show_n": "集齐 9 个数字 {n}",
        "mission_complete_rows": "完成 {n} 个整行",
        "mission_complete_cols": "完成 {n} 个整列",
        "mission_complete_band": "完成第 {n} 区的全部小宫",
        "mission_hint_free": "全程不使用提示键通关",
        "mission_no_mistake": "全程不填入任何错误数字通关",
        "mission_speed_run": "60 秒内填满任一 3×3 小宫",
        "mission_undo_free": "全程不使用撤销通关",
        "mission_first_move": "开始后 30 秒内填入一个正确数字",
        "mission_corners": "填入四个角落的格子",
        "mission_no_notes": "全程未开启笔记模式完成一个整行",
        "mission_center_block": "填满中央的 3×3 小宫",
        "mission_row_sum_45": "完成任一整行（其数字之和恰为 45）",
        "help_pages": [
            ["ESC：退出", "F1：帮助侧栏", "F2：背景音乐开/关", "F3：下一首背景音乐", "F5：排行榜"],
            ["F8：提示", "F9：解答", "F10：新游戏", "CTRL+Z：撤销", "方向键：移动"],
            ["实体 N：写入模式", "实体 B：笔记模式", "按住 N + 左 9 格：写入数字", "按住 B + 右 9 格：标记笔记"],
            ["A/G/H/;：写入加总", "Q/T/Y/P：笔记加总", "大格键 + 小格键：精准定位", "1-9：直接输入", "SPACE/DEL：清除"],
            ["迷雾：每 8 秒揭示一行/列/宫", "被遮掩格（█）不可填写"],
        ],
    },
    "zh_tw": {
        "app_title": "數獨 Neo",
        "new": "新遊戲",
        "undo": "復原",
        "hint": "提示",
        "notes": "筆記",
        "solve": "解答",
        "help": "說明",
        "quit": "離開",
        "numbers": "數字：",
        "difficulty": "難度：",
        "layout": "鍵盤配置：",
        "language": "語言：",
        "big_block": "大格（宮）：",
        "small_cell": "小格（單元）：",
        "number_status": "數字狀態",
        "leaderboard": "排行榜",
        "rank": "排名",
        "time": "時間",
        "date": "日期",
        "quit_game": "離開遊戲",
        "quit_game_msg": "要離開遊戲嗎？",
        "start_game": "開始遊戲？",
        "start_game_msg": "要開始一局新遊戲嗎？",
        "congratulations": "恭喜！",
        "puzzle_solved": "謎題已完成！",
        "show_solution": "顯示答案？",
        "show_solution_msg": "確定要顯示答案嗎？",
        "yes": "是",
        "no": "否",
        "ok": "確定",
        "bgm_playing": "背景音樂：播放中",
        "bgm_paused": "背景音樂：已暫停",
        "bgm_changing": "背景音樂：正在切換曲目...",
        "cell": "格子",
        "new_game_status": "新的{difficulty}遊戲已開始。",
        "auto_8s": "每 8 秒自動",
        "diff_easy": "簡單",
        "diff_medium": "中等",
        "diff_hard": "困難",
        "diff_expert": "專家",
        "mode_label": "模式：",
        "mode_normal": "闖關",
        "mode_versus": "對戰 AI",
        "mode_mission": "任務",
        "mode_fog": "迷霧",
        "fog_status": "迷霧：已顯 {kind}",
        "fog_row": "第 {n} 列（行）",
        "fog_col": "第 {n} 欄（列）",
        "fog_box": "第 {n} 宮",
        "fog_locked": "迷霧遮擋",
        "fog_locked_msg": "該格被迷霧遮擋，只能填寫已顯列／欄／宮內的格子。",
        "tab_versus": "對戰",
        "tab_mission": "任務",
        "diff_chujie": "初階",
        "diff_zhongjie": "中階",
        "diff_gaojie": "高階",
        "diff_dashi": "大師",
        "diff_chuanqi": "傳奇",
        "diff_shenhua": "神話",
        "versus_easy_ai": "簡單 AI",
        "versus_medium_ai": "普通 AI",
        "versus_hard_ai": "困難 AI",
        "versus_random": "隨機",
        "versus_player_turn": "你的回合",
        "versus_ai_turn": "AI 回合",
        "versus_player_win": "你贏了！",
        "versus_ai_win": "AI 走完最後一步",
        "versus_draw": "平局",
        "mission_panel": "任務",
        "mission_completed": "完成",
        "missions_done": "全部任務完成！",
        "mission_score": "得分",
        "mission_fill_block": "填滿第 {n} 個小宮",
        "mission_show_n": "集齊 9 個數字 {n}",
        "mission_complete_rows": "完成 {n} 個整列",
        "mission_complete_cols": "完成 {n} 個整欄",
        "mission_complete_band": "完成第 {n} 區的全部小宮",
        "mission_hint_free": "全程不使用提示鍵通關",
        "mission_no_mistake": "全程不填入任何錯誤數字通關",
        "mission_speed_run": "60 秒內填滿任一 3×3 小宮",
        "mission_undo_free": "全程不使用復原通關",
        "mission_first_move": "開始後 30 秒內填入一個正確數字",
        "mission_corners": "填入四個角落的格子",
        "mission_no_notes": "全程未開啟筆記模式完成一個整列",
        "mission_center_block": "填滿中央的 3×3 小宮",
        "mission_row_sum_45": "完成任一整列（其數字之和恰為 45）",
        "help_pages": [
            ["ESC：離開", "F1：說明側欄", "F2：背景音樂開/關", "F3：下一首背景音樂", "F5：排行榜"],
            ["F8：提示", "F9：解答", "F10：新遊戲", "CTRL+Z：復原", "方向鍵：移動"],
            ["實體 N：寫入模式", "實體 B：筆記模式", "按住 N + 左 9 格：寫入數字", "按住 B + 右 9 格：標記筆記"],
            ["A/G/H/;：寫入加總", "Q/T/Y/P：筆記加總", "大格鍵 + 小格鍵：精準定位", "1-9：直接輸入", "SPACE/DEL：清除"],
            ["迷雾：每 8 秒揭示一列（行）/欄（列）/宮", "遮擋格（█）不可填寫"],
        ],
    },
}

def tr(language, key):
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

def difficulty_label(language, difficulty):
    return tr(language, f"diff_{difficulty}")

# ──────────────────────────────────────────────
#  BGM Engine (MIDI Style)
# ──────────────────────────────────────────────

class BGMThread(QThread):
    def __init__(self):
        super().__init__()
        self.is_playing = False
        self.should_change_track = False
        
        self.winmm = ctypes.WinDLL("winmm")
        self.handle = ctypes.c_void_p()
        self.MIDI_MAPPER = ctypes.c_uint(-1).value
        self.CALLBACK_NULL = 0

    def _read_varlen(self, data, pos):
        value = 0
        while True:
            byte = data[pos]
            pos += 1
            value = (value << 7) | (byte & 0x7F)
            if not byte & 0x80:
                return value, pos

    def _parse_midi(self, path):
        try:
            data = Path(path).read_bytes()
            pos = 0

            if data[pos : pos + 4] != b"MThd": return None
            pos += 4
            header_len = struct.unpack(">I", data[pos : pos + 4])[0]
            pos += 4
            fmt, tracks, division = struct.unpack(">HHH", data[pos : pos + 6])
            pos += header_len

            if division & 0x8000: return None

            events = []
            for _ in range(tracks):
                if data[pos : pos + 4] != b"MTrk": break
                pos += 4
                track_len = struct.unpack(">I", data[pos : pos + 4])[0]
                pos += 4
                end = pos + track_len
                tick = 0
                running_status = None

                while pos < end:
                    delta, pos = self._read_varlen(data, pos)
                    tick += delta
                    status = data[pos]

                    if status < 0x80:
                        if running_status is None: break
                        status = running_status
                    else:
                        pos += 1
                        if status < 0xF0:
                            running_status = status

                    if status == 0xFF:
                        meta_type = data[pos]
                        pos += 1
                        length, pos = self._read_varlen(data, pos)
                        payload = data[pos : pos + length]
                        pos += length
                        if meta_type == 0x51 and length == 3:
                            tempo = (payload[0] << 16) | (payload[1] << 8) | payload[2]
                            events.append((tick, "tempo", tempo))
                        elif meta_type == 0x2F:
                            break
                    elif status in (0xF0, 0xF7):
                        length, pos = self._read_varlen(data, pos)
                        pos += length
                    else:
                        event_type = status & 0xF0
                        channel = status & 0x0F
                        size = 1 if event_type in (0xC0, 0xD0) else 2
                        payload = data[pos : pos + size]
                        pos += size
                        events.append((tick, "midi", status, bytes(payload)))

            events.sort(key=lambda item: item[0])
            return division, events
        except:
            return None

    def _short_message(self, status, payload):
        message = status
        if len(payload) > 0: message |= payload[0] << 8
        if len(payload) > 1: message |= payload[1] << 16
        return message

    def _all_notes_off(self):
        if self.handle:
            for channel in range(16):
                self.winmm.midiOutShortMsg(self.handle, self._short_message(0xB0 | channel, bytes([123, 0])))

    def run(self):
        result = self.winmm.midiOutOpen(ctypes.byref(self.handle), self.MIDI_MAPPER, 0, 0, self.CALLBACK_NULL)
        if result: return

        while True:
            # Refresh list of MIDI files
            bundled_dir = Path(resource_path("."))
            cwd_dir = Path(".")
            seen = set()
            midi_files = []
            for search_dir in (bundled_dir, cwd_dir):
                try:
                    for pattern in ("*.mid", "*.midi"):
                        for midi_path in search_dir.glob(pattern):
                            resolved = str(midi_path.resolve())
                            if resolved in seen:
                                continue
                            seen.add(resolved)
                            midi_files.append(midi_path)
                except OSError:
                    continue
            if not midi_files:
                time.sleep(5)
                continue
            
            random.shuffle(midi_files)
            
            for midi_path in midi_files:
                parsed = self._parse_midi(midi_path)
                if not parsed: continue
                
                ticks_per_quarter, events = parsed
                track_start_time = time.time()
                self.should_change_track = False
                
                # Repeat for ~1 minute 50 seconds (110s)
                while time.time() - track_start_time < 110 and not self.should_change_track:
                    tempo = 500000
                    last_tick = 0
                    
                    for event in events:
                        if self.should_change_track: break
                        
                        while not self.is_playing:
                            self._all_notes_off()
                            time.sleep(0.1)
                            if self.should_change_track: break
                        
                        if self.should_change_track: break
                        
                        tick = event[0]
                        if tick > last_tick:
                            seconds = ((tick - last_tick) * tempo) / (ticks_per_quarter * 1_000_000)
                            # Sleep in small chunks to stay responsive
                            start_sleep = time.perf_counter()
                            while True:
                                elapsed = time.perf_counter() - start_sleep
                                remaining = seconds - elapsed
                                if remaining <= 0 or not self.is_playing or self.should_change_track:
                                    break
                                time.sleep(min(0.01, remaining))
                            
                            if self.should_change_track: break
                            if not self.is_playing:
                                while not self.is_playing and not self.should_change_track:
                                    self._all_notes_off()
                                    time.sleep(0.1)
                                if self.should_change_track: break
                            
                            last_tick = tick

                        if event[1] == "tempo":
                            tempo = event[2]
                        elif event[1] == "midi":
                            _, _, status, payload = event
                            self.winmm.midiOutShortMsg(self.handle, self._short_message(status, payload))
                    
                    if self.should_change_track: break
                    # Small gap between repeats
                    time.sleep(1.0)

    def toggle(self):
        self.is_playing = not self.is_playing
        if not self.is_playing:
            self._all_notes_off()
        return self.is_playing

    def next_track(self):
        self.should_change_track = True
        self._all_notes_off()


# ──────────────────────────────────────────────
#  Leaderboard Manager
# ──────────────────────────────────────────────

class LeaderboardManager:
    FILE_PATH = user_data_path("sudoku_scores.json")

    # All buckets the leaderboard dialog displays.
    # Legacy easy/medium/hard/expert kept for backward compatibility.
    DEFAULT_BUCKETS = [
        "easy", "medium", "hard", "expert",
        "chujie", "zhongjie", "gaojie", "dashi", "chuanqi", "shenhua",
        "versus", "mission", "fog",
    ]

    @staticmethod
    def load_scores():
        # Start with empty defaults, then layer in on-disk data so
        # unknown keys in old files survive a roundtrip.
        scores = {b: [] for b in LeaderboardManager.DEFAULT_BUCKETS}
        if os.path.exists(LeaderboardManager.FILE_PATH):
            try:
                with open(LeaderboardManager.FILE_PATH, "r") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    for k, v in saved.items():
                        if isinstance(v, list):
                            scores[k] = v
            except:
                pass
        return scores

    @staticmethod
    def save_score(difficulty, value, is_score=False):
        scores = LeaderboardManager.load_scores()
        if is_score:
            entry = {"score": value, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
            sort_key = lambda x: -x["score"]  # higher is better for mission
        else:
            entry = {"time": value, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
            sort_key = lambda x: x["time"]
        bucket = scores.setdefault(difficulty, [])
        bucket.append(entry)
        bucket.sort(key=sort_key)
        scores[difficulty] = bucket[:10]

        with open(LeaderboardManager.FILE_PATH, "w") as f:
            json.dump(scores, f, indent=4)

class LeaderboardDialog(QDialog):
    def __init__(self, parent=None, language="en"):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(tr(self.language, "leaderboard"))
        self.setFixedSize(400, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Tab list mixes Normal sub-levels + Versus + Mission
        self.tab_keys = (
            [k for k, _, _ in NORMAL_SUBLEVELS] + ["versus", "mission"]
        )
        self.tabs = QComboBox()
        for key in self.tab_keys:
            if key in ("versus", "mission"):
                label = tr(self.language, f"tab_{key}")
            else:
                label = difficulty_label(self.language, key)
            self.tabs.addItem(label, key)
        self.tabs.currentIndexChanged.connect(self.update_table)
        layout.addWidget(self.tabs)

        self.table = QTableWidget(10, 3)
        self.table.setHorizontalHeaderLabels([tr(self.language, "rank"), tr(self.language, "time"), tr(self.language, "date")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.update_table()

    def set_difficulty(self, difficulty):
        index = self.tabs.findData(difficulty)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def update_table(self, *_):
        key = self.tabs.currentData()
        scores = LeaderboardManager.load_scores().get(key, [])
        is_mission = (key == "mission")
        time_label = tr(self.language, "mission_score") if is_mission else tr(self.language, "time")
        # Update column header for second column.
        self.table.setHorizontalHeaderLabels([tr(self.language, "rank"), time_label, tr(self.language, "date")])
        self.table.clearContents()
        for i in range(10):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            if i < len(scores):
                s = scores[i]
                if is_mission and "score" in s:
                    self.table.setItem(i, 1, QTableWidgetItem(str(s["score"])))
                elif "time" in s:
                    mins, secs = divmod(s["time"], 60)
                    self.table.setItem(i, 1, QTableWidgetItem(f"{mins:02d}:{secs:02d}"))
                else:
                    self.table.setItem(i, 1, QTableWidgetItem("-"))
                self.table.setItem(i, 2, QTableWidgetItem(s.get("date", "-")))
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

        # cells_to_remove covers legacy 4 + new 6 sub-levels + versus/mission.
        # Versus/mission default to "dashi" (48) puzzle.
        NORMAL_MAP = {
            "easy": 30, "medium": 36, "hard": 42, "expert": 48,
            "chujie": 30, "zhongjie": 36, "gaojie": 42, "dashi": 48,
            "chuanqi": 54, "shenhua": 62,
            "v_easy": 48, "v_medium": 48, "v_hard": 48,
        }
        cells_to_remove = NORMAL_MAP.get(difficulty, 48)

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
#  AI Brain (pure heuristic for Versus mode)
# ──────────────────────────────────────────────

class AIBrain:
    """Pick the next AI move by simulating 'easiest-to-infer first' technique.

    Score each empty cell by its remaining candidate count on the current
    partial board. Cells with fewer candidates (more constrained) are
    considered easier for a human to deduce, so the AI prefers them.
    """

    @staticmethod
    def pick_move(board, solution):
        empties = [(r, c) for r in range(9) for c in range(9) if board[r][c] == 0]
        if not empties:
            return None

        def candidates(r, c):
            used = {board[r][cc] for cc in range(9) if board[r][cc]}
            used |= {board[rr][c] for rr in range(9) if board[rr][c]}
            br, bc = 3 * (r // 3), 3 * (c // 3)
            used |= {board[rr][cc]
                     for rr in range(br, br + 3)
                     for cc in range(bc, bc + 3)
                     if board[rr][cc]}
            return 9 - len(used)

        # Sort ascending by candidate count (most constrained first).
        empties.sort(key=lambda rc: candidates(rc[0], rc[1]))
        # Random pick from the top tier to avoid lockstep behavior.
        top = empties[:min(5, len(empties))]
        r, c = random.choice(top)
        return r, c, solution[r][c]


class AIWorker(QThread):
    """Background thread that emits AI moves on a 10-15s cadence."""

    moveReady = pyqtSignal(object)  # (r, c, val)

    def __init__(self, solution, cadence_seconds=12.0, parent=None):
        super().__init__(parent)
        self._solution = solution
        self._cadence = cadence_seconds
        self._lock = threading.Lock()
        self._board = [[0] * 9 for _ in range(9)]
        self._stop = False

    def update_board(self, board):
        with self._lock:
            self._board = [row[:] for row in board]

    def stop(self):
        with self._lock:
            self._stop = True

    def run(self):
        while True:
            time.sleep(self._cadence + random.uniform(-1.5, 1.5))
            with self._lock:
                if self._stop:
                    return
                snap = [row[:] for row in self._board]
            move = AIBrain.pick_move(snap, self._solution)
            if move is None:
                return
            r, c, val = move
            self.moveReady.emit((r, c, val))


# ──────────────────────────────────────────────
#  Mission Engine (36-task catalog)
# ──────────────────────────────────────────────

class MissionEngine:
    """Sample 3 missions per game from MISSION_CATALOG and evaluate progress."""

    @staticmethod
    def sample_three():
        # Pick one from up to 3 distinct categories to keep variety.
        by_cat = {}
        for cat, key, tgt in MISSION_CATALOG:
            by_cat.setdefault(cat, []).append((cat, key, tgt))
        cats = list(by_cat.keys())
        random.shuffle(cats)
        chosen = []
        for cat in cats:
            if len(chosen) == 3:
                break
            chosen.append(random.choice(by_cat[cat]))
        # Backfill from any remaining entries if categories were short.
        pool = list(MISSION_CATALOG)
        random.shuffle(pool)
        for entry in pool:
            if len(chosen) == 3:
                break
            if entry not in chosen:
                chosen.append(entry)
        return [{"category": c, "desc_key": k, "target": t, "done": False}
                for c, k, t in chosen]

    @staticmethod
    def evaluate(missions, board, solution, ctx):
        updated = []
        for m in missions:
            done = MissionEngine._check(m, board, solution, ctx)
            if done != m["done"]:
                m["done"] = done
                updated.append(m)
        return updated

    @staticmethod
    def all_done(missions):
        return bool(missions) and all(m["done"] for m in missions)

    @staticmethod
    def _check(m, board, solution, ctx):
        cat, tgt = m["category"], m["target"]
        if cat == "fill_small_block":
            br, bc = 3 * (tgt // 3), 3 * (tgt % 3)
            return all(board[br + i][bc + j] != 0 for i in range(3) for j in range(3))
        if cat == "show_number_n":
            return sum(1 for r in range(9) for c in range(9) if board[r][c] == tgt) >= 9
        if cat == "complete_row":
            return sum(1 for r in range(9) if all(board[r][c] != 0 for c in range(9))) >= tgt
        if cat == "complete_col":
            return sum(1 for c in range(9) if all(board[r][c] != 0 for r in range(9))) >= tgt
        if cat == "complete_box_set":
            # A "band" is one horizontal strip of three 3x3 boxes.
            # Old code iterated br over 3 rows per band, which incorrectly
            # checked overlapping slices (e.g. rows 1-3 instead of rows 0-2
            # for the top band) and never matched unless the whole board
            # was filled. Use a single br per band and walk the three boxes
            # across it.
            br = 3 * tgt
            for cc in range(0, 9, 3):
                if not all(board[br + i][cc + j] != 0 for i in range(3) for j in range(3)):
                    return False
            return True
        # "Fill the center 3x3 sub-block" must fire as soon as the center
        # block is complete, not when the entire board is filled, so check
        # it before the singleton-category full-board guard.
        if cat == "center_block":
            return all(board[3 + i][3 + j] != 0 for i in range(3) for j in range(3))
        # Singleton categories — most need full board completion to "win".
        full = all(board[r][c] != 0 for r in range(9) for c in range(9))
        if not full and cat not in ("diagonal_corners", "first_move", "speed_run",
                                    "no_notes", "row_sum_45"):
            return False
        if cat == "hint_free":
            return not ctx["used_hint"]
        if cat == "no_mistake":
            return not ctx["made_error"]
        if cat == "speed_run":
            return ctx.get("subblock_done", False)
        if cat == "undo_free":
            return not ctx["used_undo"]
        if cat == "first_move":
            return ctx.get("first_move_correct", False)
        if cat == "diagonal_corners":
            return all(board[r][c] != 0 for r, c in [(0, 0), (0, 8), (8, 0), (8, 8)])
        if cat == "no_notes":
            return ctx.get("row_no_notes", False)
        if cat == "row_sum_45":
            return any(sum(board[r][c] for c in range(9)) == 45 for r in range(9))
        return False


class MissionPanel(QFrame):
    """Right-sidebar widget listing the 3 active missions."""

    def __init__(self, language="en", parent=None):
        super().__init__(parent)
        self.language = language
        self.setFixedHeight(155)
        self.setFixedWidth(280)
        self.setStyleSheet("background-color: #FFF8E1; border: 1px solid #F0C36D; border-radius: 4px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(4)

        self.title_label = QLabel()
        self.title_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.title_label.setStyleSheet("color: #8A6D3B; border: none;")
        layout.addWidget(self.title_label)

        self.labels = []
        for _ in range(3):
            lbl = QLabel()
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #2C3E50; background: transparent; border: none;")
            layout.addWidget(lbl)
            self.labels.append(lbl)
        layout.addStretch(1)

    def set_language(self, language):
        self.language = language

    def render(self, missions):
        self.title_label.setText(tr(self.language, "mission_panel").upper())
        for i, lbl in enumerate(self.labels):
            if i < len(missions):
                m = missions[i]
                desc = self._describe(m)
                if m["done"]:
                    lbl.setText(f"✓ {desc}  — {tr(self.language, 'mission_completed')}")
                    lbl.setStyleSheet(
                        "color: #27AE60; background: transparent; border: none;"
                        " text-decoration: line-through;"
                    )
                else:
                    lbl.setText(f"○ {desc}")
                    lbl.setStyleSheet("color: #2C3E50; background: transparent; border: none;")
            else:
                lbl.setText("")

    def _describe(self, m):
        key = m["desc_key"]
        tgt = m["target"]
        template = tr(self.language, key)
        try:
            return template.format(n=tgt + 1 if m["category"] == "fill_small_block" else tgt)
        except (KeyError, IndexError):
            return template

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
        self.ai_filled = False
        self.notes = set()
        self.error = False
        self.selected = False
        self.highlighted = False
        self.same_number = False
        # Fog density: 0 = clear (current reveal), 1 = 25% dim, 2 = 50% dim,
        # 3 = 75% dim, 4 = fully black (the original "███" mask). Cells outside
        # the current reveal band age one step per fog rotation.
        self.fog_level = 0

        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(64, 64)
        self.setFocusPolicy(Qt.StrongFocus)
        self._set_main_font()
        self.update_style()

    @property
    def is_locked(self):
        # Any fog density above 0 keeps the cell un-editable, matching the
        # "only edit cells in the currently revealed band" rule.
        return self.given or self.ai_filled or self.fog_level >= 1

    def set_fog_level(self, level):
        """Apply a fog density 0..4. 0 is fully revealed, 4 is fully black."""
        level = max(0, min(4, int(level)))
        if level == self.fog_level:
            return
        self.fog_level = level
        if level >= 4:
            # Fully masked; keep notes/value intact so we can restore them.
            self.setText("█" * 3)
        else:
            # Restore whatever the cell should currently display so the digit
            # (or notes) remains visible while the background fades.
            if self.value != 0:
                self.setText(str(self.value))
                self._set_main_font()
            elif self.notes:
                self.set_notes(self.notes)
            else:
                self.setText("")
                self._set_main_font()
        self.update_style()

    def set_fog_hidden(self, hidden):
        # Backward-compatible wrapper: True -> fully black (level 4), False -> clear.
        self.set_fog_level(4 if hidden else 0)

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

    def set_given(self, val):
        self.value = val
        self.given = True
        self.notes.clear()
        if val != 0:
            self.setText(str(val))
            self._set_main_font()
        else:
            self.setText("")
        self.update_style()

    def update_style(self):
        if self.fog_level >= 4:
            # Fully fogged: same look as the original mask so the player can tell
            # the cell is completely hidden.
            self.setStyleSheet(
                """
                QLabel {
                    background-color: #2C3E50;
                    color: #2C3E50;
                    border-top: 1px solid #555;
                    border-left: 1px solid #555;
                    border-bottom: 1px solid #555;
                    border-right: 1px solid #555;
                    font-weight: bold;
                }
                """
            )
            return
        if self.fog_level >= 1:
            # Progressive fog: still show the digit, but dim the background by
            # 25 / 50 / 75 percent so the player can see decay across rotations.
            dim_steps = {
                1: ("#E0E0E0", "#2C3E50"),  # 25% dim
                2: ("#B0B0B0", "#2C3E50"),  # 50% dim
                3: ("#707070", "#ECF0F1"),  # 75% dim
            }
            fog_bg, fog_fg = dim_steps[self.fog_level]
            self.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {fog_bg};
                    color: {fog_fg};
                    border-top: 1px solid #555;
                    border-left: 1px solid #555;
                    border-bottom: 1px solid #555;
                    border-right: 1px solid #555;
                    font-weight: bold;
                }}
                """
            )
            return
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
        elif self.ai_filled:
            fg = "#8E44AD"
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
    """Buttons 1-9 + erase arranged in a 3x3 grid."""
    number_selected = pyqtSignal(int)
    erase_selected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_size = 50

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
            r, c = divmod(i - 1, 3)
            btn = QPushButton(str(i))
            btn.setFixedSize(btn_size, btn_size)
            btn.setFont(QFont("Segoe UI", 18, QFont.Bold))
            btn.setStyleSheet(num_btn_style)
            btn.clicked.connect(lambda checked, n=i: self.number_selected.emit(n))
            grid_layout.addWidget(btn, r, c)

        main_layout.addLayout(grid_layout)

        erase_btn = QPushButton("\u2715")
        erase_btn.setFixedSize(btn_size * 3 + 12, btn_size) # Width spans 3 columns + spacing
        erase_btn.setFont(QFont("Segoe UI", 20, QFont.Bold))
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
        main_layout.addWidget(erase_btn, alignment=Qt.AlignCenter)


# ──────────────────────────────────────────────
#  Sudoku Grid Widget
# ──────────────────────────────────────────────

# ────────────────────────────────────────────────────────────
#  Fog Manager (Fog mode)
# ────────────────────────────────────────────────────────────

class FogManager(QObject):
    """Drives Fog mode: every 8 s reveal a fresh row, column, or 3x3 box.

    Cells outside the revealed band are hidden and locked until fog rolls over.
    """

    rotated = pyqtSignal(str, int)  # kind ('row'/'col'/'box'), index (0..8)

    FOG_INTERVAL_MS = 8000

    def __init__(self, grid, language='en', parent=None):
        super().__init__(parent)
        self.grid = grid
        self.language = language
        self.kind = None  # 'row' | 'col' | 'box'
        self.index = 0

    def start(self):
        # Fire the first reveal almost immediately, then on a steady 8 s cadence.
        self._schedule_timer()
        QTimer.singleShot(0, self._advance)

    def _schedule_timer(self):
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self._on_tick)
        self._timer = timer
        timer.start(self.FOG_INTERVAL_MS)

    def _on_tick(self):
        self._advance()
        self._timer.start(self.FOG_INTERVAL_MS)

    def stop(self):
        timer = getattr(self, '_timer', None)
        if timer is not None:
            timer.stop()
        self._clear_all()
        self.kind = None
        self.index = -1

    def _advance(self):
        kinds = ['row', 'col', 'box']
        if self.kind is not None:
            candidates = [k for k in kinds if k != self.kind]
            if random.random() < 0.4:
                candidates = kinds
            kind = random.choice(candidates)
        else:
            kind = random.choice(kinds)
        for _ in range(6):
            idx = random.randrange(9)
            if kind != self.kind or idx != self.index:
                break
        self.kind = kind
        self.index = idx
        self._apply()
        self.rotated.emit(kind, idx)

    def _clear_all(self):
        # Reset every cell to the fully-revealed state.
        for r in range(9):
            for c in range(9):
                cell = self.grid.cells[r][c]
                cell.set_fog_level(0)

    def _apply(self):
        # Cells in the newly revealed band become fully clear. Every other cell
        # ages by one step (capped at 4 = full black). This produces the
        # 25 / 50 / 75 / 100 percent dimming the user asked for.
        revealed = self._revealed_cells()
        for r in range(9):
            for c in range(9):
                cell = self.grid.cells[r][c]
                if (r, c) in revealed:
                    cell.set_fog_level(0)
                else:
                    cell.set_fog_level(min(cell.fog_level + 1, 4))

    def _revealed_cells(self):
        if self.kind == 'row':
            return {(self.index, c) for c in range(9)}
        if self.kind == 'col':
            return {(r, self.index) for r in range(9)}
        if self.kind == 'box':
            br, bc = 3 * (self.index // 3), 3 * (self.index % 3)
            return {(br + dr, bc + dc) for dr in range(3) for dc in range(3)}
        return set()

    def revealed_band_full(self):
        """True iff the currently revealed band is completely filled in.

        Returns False when no band has been revealed yet.
        """
        if self.kind is None:
            return False
        for r, c in self._revealed_cells():
            if self.grid.cells[r][c].value == 0:
                return False
        return True

    def _pick_next_kind_index(self):
        # Pick a new (kind, index) different from the current reveal so the
        # rotation is always visible. The 40% same-kind chance still allows
        # variety (e.g., row 4 -> row 7) while guaranteeing we never stall on
        # the exact same band.
        kinds = ['row', 'col', 'box']
        if self.kind is not None:
            candidates = [k for k in kinds if k != self.kind]
            if random.random() < 0.4:
                candidates = kinds
            kind = random.choice(candidates)
        else:
            kind = random.choice(kinds)
        for _ in range(20):
            idx = random.randrange(9)
            if kind != self.kind or idx != self.index:
                break
        else:
            idx = (self.index + 1) % 9 if self.index is not None else 0
        return kind, idx

    def maybe_advance_now(self):
        """If the current reveal is fully filled, rotate immediately.

        Resets the 8 s timer so the next rotation also waits a full interval
        after this early advance. Returns True iff a rotation happened.
        """
        if self.kind is None or not self.revealed_band_full():
            return False
        kind, idx = self._pick_next_kind_index()
        self.kind = kind
        self.index = idx
        self._apply()
        self.rotated.emit(kind, idx)
        timer = getattr(self, '_timer', None)
        if timer is not None:
            timer.start(self.FOG_INTERVAL_MS)
        return True

    def describe(self):
        if self.kind is None:
            return ''
        kind_key = f'fog_{self.kind}'
        n = self.index + 1
        try:
            return tr(self.language, kind_key).format(n=n)
        except KeyError:
            return f'{self.kind} {n}'


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
                    cell.ai_filled = False
                    cell.setText(str(val))
                    cell.notes.clear()
                else:
                    cell.value = 0
                    cell.given = False
                    cell.ai_filled = False
                    cell.setText("")
                    cell.notes.clear()
                cell.error = False
                cell.fog_level = 0
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
        if cell.is_locked: return
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
        if cell.is_locked: return
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
        if cell.is_locked: return
        cell.value = old_val
        cell.notes = old_notes
        if old_val:
            cell.set_value(old_val)
        else:
            cell.set_notes(old_notes)
        self.validate_and_mark()
        self.update_highlights()
        self.board_changed.emit()

    def set_cell_value_ai(self, r, c, val):
        """Place a value bypassing the lock check (used by AI worker)."""
        cell = self.cells[r][c]
        if cell.value != 0:
            return False  # Player beat the AI to this cell
        if cell.fog_level >= 1:
            return False  # Fog mode keeps cells hidden; AI cannot pre-fill them.
        cell.ai_filled = True
        cell.set_value(val)
        self.validate_and_mark()
        self.update_highlights()
        self.board_changed.emit()
        return True

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
#  Help Pager Widget
# ──────────────────────────────────────────────

class HelpPager(QFrame):
    def __init__(self, parent=None, language="en"):
        super().__init__(parent)
        self.language = language
        self.current_page = 0

        self.setFixedHeight(155)
        self.setFixedWidth(280)
        self.setStyleSheet("background-color: #ECF0F1; border: 1px solid #BDC3C7; border-radius: 4px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(4)

        self.title_label = QLabel()
        self.title_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.title_label.setStyleSheet("color: #7F8C8D; border: none;")
        layout.addWidget(self.title_label)

        self.content_label = QLabel()
        self.content_label.setFont(QFont("Consolas", 9))
        self.content_label.setStyleSheet("color: #2C3E50; background: transparent; border: none;")
        self.content_label.setWordWrap(True)
        self.content_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.content_label, 1)

        self.page_label = QLabel()
        self.page_label.setFont(QFont("Segoe UI", 8))
        self.page_label.setStyleSheet("color: #7F8C8D; background: transparent; border: none;")
        self.page_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.page_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.show_next_page)
        self.update_page()

    def set_language(self, language):
        self.language = language
        self.current_page = min(self.current_page, len(tr(self.language, "help_pages")) - 1)
        self.update_page()

    def start(self):
        if not self.timer.isActive():
            self.timer.start(8000)

    def stop(self):
        self.timer.stop()

    def show_next_page(self):
        pages = tr(self.language, "help_pages")
        self.current_page = (self.current_page + 1) % len(pages)
        self.update_page()

    def update_page(self):
        pages = tr(self.language, "help_pages")
        self.title_label.setText(tr(self.language, "help").upper())
        self.content_label.setText("\n".join(pages[self.current_page]))
        self.page_label.setText(f"{self.current_page + 1}/{len(pages)} - {tr(self.language, 'auto_8s')}")

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
        self.language = "en"
        self.setWindowTitle(tr(self.language, "app_title"))
        self.solution = None
        self.puzzle = None
        self.difficulty = "medium"
        self.elapsed = 0
        self.timer_running = False
        self.used_assist = False

        # Mode + sublevel
        self.mode = "normal"
        self.sublevel = NORMAL_SUBLEVELS[0][0]
        self.ai_worker = None
        self.ai_cadence = 12.0

        # Mission mode state
        self.missions = []
        self.mission_panel = None
        self.ctx = {
            "used_hint": False,
            "used_undo": False,
            "made_error": False,
            "first_move_correct": False,
            "subblock_done": False,
            "row_no_notes": False,
        }
        self.first_move_deadline = 0.0
        self.speed_run_deadline = 0.0

        # Fog mode state
        self.fog_manager = None
        self.fog_status_label = None
        self.fog_status_base_text = ""

        self.held_big = None
        self.held_small = None
        
        # Keyboard Layouts
        self.layouts = {
            "qwerty": {
                "big": "wersdfxcv",
                "small": "uiojklm,.",
                "write_add": {"a": 1, "g": 2, "h": 5, ";": 2},
                "mark_add": {"q": 1, "t": 2, "y": 5, "p": 2},
                "mod_write": "n",
                "mod_mark": "b",
                "mode_write": "n",
                "mode_note": "b"
            },
            "colemak": {
                "big": "wfprstxcv",
                "small": "luyneih,.",
                "write_add": {"a": 1, "d": 2, "h": 5, "o": 2},
                "mark_add": {"q": 1, "g": 2, "j": 5, ";": 2},
                "mod_write": "k",
                "mod_mark": "b",
                "mode_write": "k",
                "mode_note": "b"
            },
            "colemak_dh": {
                "big": "wfprstxcd",
                "small": "luyneih,.",
                "write_add": {"a": 1, "g": 2, "m": 5, "o": 2},
                "mark_add": {"q": 1, "b": 2, "j": 5, ";": 2},
                "mod_write": "k",
                "mod_mark": "v",
                "mode_write": "k",
                "mode_note": "v"
            },
            "colemak_dhk": {
                "big": "wfprstxcd",
                "small": "luyneih,.",
                "write_add": {"a": 1, "g": 2, "k": 5, "o": 2},
                "mark_add": {"q": 1, "b": 2, "j": 5, ";": 2},
                "mod_write": "m",
                "mod_mark": "v",
                "mode_write": "m",
                "mode_note": "v"
            },
            "dvorak": {
                "big": ",.poeuqjk",
                "small": "gcrhtnmwv",
                "write_add": {"a": 1, "i": 2, "d": 5, "s": 2},
                "mark_add": {"'": 1, "y": 2, "f": 5, "l": 2},
                "mod_write": "b",
                "mod_mark": "x",
                "mode_write": "m",
                "mode_note": "b"
            },
            "workman": {
                "big": "drwshtxmc",
                "small": "fupneol,.",
                "write_add": {"a": 1, "g": 2, "y": 5, "i": 2},
                "mark_add": {"q": 1, "b": 2, "j": 5, ";": 2},
                "mod_write": "k",
                "mod_mark": "v",
                "mode_write": "k",
                "mode_note": "v"
            },
            "custom": {
                "big": "123456789",
                "small": "abcdefghi",
                "write_add": {},
                "mark_add": {},
                "mod_write": "",
                "mod_mark": "",
                "mode_write": "w",
                "mode_note": "n"
            }
        }
        self.current_layout_name = "qwerty"
        self.update_current_layout()
        
        self.held_write_add = set()
        self.held_mark_add = set()
        self.held_mod_write = False
        self.held_mod_mark = False
        
        # BGM Thread
        self.bgm_thread = BGMThread()
        self.bgm_thread.start()
        
        self.init_ui()

        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        self.sidebar_widget.hide()  # Hide by default
        
        # Stabilization hack: Fullscreen -> Restore -> Fullscreen
        self.showFullScreen()
        self.showNormal()
        self.showFullScreen()

    def update_current_layout(self):
        layout = self.layouts[self.current_layout_name]
        self.big_keys = layout["big"]
        self.small_keys = layout["small"]
        self.write_add_keys = layout.get("write_add", {})
        self.mark_add_keys = layout.get("mark_add", {})
        self.mod_write_key = layout.get("mod_write", "")
        self.mod_mark_key = layout.get("mod_mark", "")
        self.mode_write_key = layout.get("mode_write", "")
        self.mode_note_key = layout.get("mode_note", "")

    def init_ui(self):
        # Instantiate core widgets first to avoid AttributeError in connections
        self.grid = SudokuGrid()
        self.grid.cell_selected.connect(self.on_cell_selected)
        self.grid.board_changed.connect(self.on_board_changed)

        central = QWidget()
        self.setCentralWidget(central)
        
        # Root layout is horizontal
        self.root_layout = QHBoxLayout(central)
        self.root_layout.setContentsMargins(15, 15, 15, 15)
        self.root_layout.setSpacing(20)

        # ── Left Sidebar: Controls & Numbers ──
        self.left_sidebar = QVBoxLayout()
        self.left_sidebar.setSpacing(8)
        
        btn_style = """
            QPushButton {
                background-color: #2C3E50;
                color: white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 80px;
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

        self.new_game_btn = QPushButton()
        self.new_game_btn.setStyleSheet(btn_style)
        self.new_game_btn.clicked.connect(self.new_game)
        self.left_sidebar.addWidget(self.new_game_btn)

        self.undo_btn = QPushButton()
        self.undo_btn.setStyleSheet(btn_style)
        self.undo_btn.clicked.connect(self.on_undo_clicked)
        self.left_sidebar.addWidget(self.undo_btn)

        self.hint_btn = QPushButton()
        self.hint_btn.setStyleSheet(btn_style)
        self.hint_btn.clicked.connect(self.give_hint)
        self.left_sidebar.addWidget(self.hint_btn)

        self.notes_btn = QPushButton()
        self.notes_btn.setStyleSheet(btn_style)
        self.notes_btn.setCheckable(True)
        self.notes_btn.toggled.connect(self.on_notes_toggled)
        self.left_sidebar.addWidget(self.notes_btn)

        self.solve_btn = QPushButton()
        self.solve_btn.setStyleSheet(btn_style)
        self.solve_btn.clicked.connect(self.show_solution)
        self.left_sidebar.addWidget(self.solve_btn)

        self.toggle_help_btn = QPushButton()
        self.toggle_help_btn.setStyleSheet(btn_style)
        self.toggle_help_btn.clicked.connect(self.toggle_sidebar)
        self.left_sidebar.addWidget(self.toggle_help_btn)

        self.quit_btn = QPushButton()
        self.quit_btn.setStyleSheet(btn_style)
        self.quit_btn.clicked.connect(self.confirm_quit)
        self.left_sidebar.addWidget(self.quit_btn)

        self.left_sidebar.addSpacing(20)
        self.numbers_label = QLabel()
        self.left_sidebar.addWidget(self.numbers_label, alignment=Qt.AlignCenter)

        # Number Pad (Grid)
        self.number_pad = NumberPad()
        self.number_pad.number_selected.connect(self.on_number_selected)
        self.number_pad.erase_selected.connect(self.on_erase)
        self.left_sidebar.addWidget(self.number_pad, alignment=Qt.AlignCenter)
        
        self.left_sidebar.addStretch()
        self.root_layout.addLayout(self.left_sidebar)

        # ── Middle Area: Top Bar & Grid ──
        self.main_area = QVBoxLayout()
        self.main_area.setSpacing(15)

        # Top Bar
        self.top_container = QWidget()
        self.top_bar = QHBoxLayout(self.top_container)
        self.top_bar.setContentsMargins(0, 0, 0, 0)
        
        self.mode_label = QLabel()
        self.mode_label.setFont(QFont("Segoe UI", 12))
        self.top_bar.addWidget(self.mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.setFont(QFont("Segoe UI", 11))
        self.mode_combo.setMinimumWidth(110)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.top_bar.addWidget(self.mode_combo)

        self.top_bar.addSpacing(15)

        self.diff_label = QLabel()
        self.diff_label.setFont(QFont("Segoe UI", 12))
        self.top_bar.addWidget(self.diff_label)

        self.diff_combo = QComboBox()
        self.diff_combo.setFont(QFont("Segoe UI", 11))
        self.diff_combo.setMinimumWidth(110)
        self.diff_combo.currentIndexChanged.connect(self.on_difficulty_changed)
        self.top_bar.addWidget(self.diff_combo)

        self.top_bar.addStretch()

        self.timer_label = QLabel(f"{self.ICON_TIMER} 00:00")
        self.timer_label.setFont(QFont("Consolas", 20, QFont.Bold))
        self.timer_label.setStyleSheet("color: #2C3E50;")
        self.top_bar.addWidget(self.timer_label)

        self.main_area.addWidget(self.top_container)

        # Second row: keyboard layout + language combo. Keeping these off the
        # first row prevents the top bar from getting too wide and squeezing
        # the right-side help/status panel against the window edge.
        self.top_container_2 = QWidget()
        self.top_bar_2 = QHBoxLayout(self.top_container_2)
        self.top_bar_2.setContentsMargins(0, 0, 0, 0)

        self.layout_label = QLabel()
        self.layout_label.setFont(QFont("Segoe UI", 12))
        self.top_bar_2.addWidget(self.layout_label)

        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["qwerty", "colemak", "colemak_dh", "colemak_dhk", "dvorak", "workman", "custom"])
        self.layout_combo.setCurrentText(self.current_layout_name)
        self.layout_combo.setFont(QFont("Segoe UI", 11))
        self.layout_combo.setMinimumWidth(120)
        self.layout_combo.currentTextChanged.connect(self.on_layout_changed)
        self.top_bar_2.addWidget(self.layout_combo)

        self.top_bar_2.addSpacing(20)

        self.language_label = QLabel()
        self.language_label.setFont(QFont("Segoe UI", 12))
        self.top_bar_2.addWidget(self.language_label)

        self.language_combo = QComboBox()
        for code, label in LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.language))
        self.language_combo.setFont(QFont("Segoe UI", 11))
        self.language_combo.setMinimumWidth(150)
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        self.top_bar_2.addWidget(self.language_combo)

        self.top_bar_2.addStretch()

        self.main_area.addWidget(self.top_container_2)

        # Grid Area
        self.grid_frame = QFrame()
        self.grid_frame.setStyleSheet("""
            QFrame {
                background-color: #555;
                border: 4px solid #333;
                border-radius: 6px;
            }
        """)
        self.grid_layout = QVBoxLayout(self.grid_frame)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        self.grid_layout.addWidget(self.grid)
        self.main_area.addWidget(self.grid_frame, 1, alignment=Qt.AlignCenter)
        
        self.root_layout.addLayout(self.main_area, 2) # Give middle more weight

        # ── Right Sidebar: Help & Status ──
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(280)
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)
        self.sidebar_layout.setSpacing(12)
        self.sidebar_layout.setContentsMargins(10, 0, 0, 0)
        
        # Help pager
        self.help_pager = HelpPager(language=self.language)
        self.sidebar_layout.addWidget(self.help_pager)

        # Mission panel (shown only in mission mode)
        self.mission_panel = MissionPanel(language=self.language)
        self.mission_panel.hide()
        self.sidebar_layout.addWidget(self.mission_panel)
        
        # Big/Small Key Grids
        self.big_grid_ui_container = QWidget()
        self.big_grid_ui = QGridLayout(self.big_grid_ui_container)
        self.big_grid_ui.setSpacing(4)
        self.big_grid_ui.setContentsMargins(0, 0, 0, 0)
        self.big_labels = {}
        
        self.small_grid_ui_container = QWidget()
        self.small_grid_ui = QGridLayout(self.small_grid_ui_container)
        self.small_grid_ui.setSpacing(4)
        self.small_grid_ui.setContentsMargins(0, 0, 0, 0)
        self.small_labels = {}

        self.update_layout_ui()

        self.big_grid_label = QLabel()
        self.sidebar_layout.addWidget(self.big_grid_label)
        self.sidebar_layout.addWidget(self.big_grid_ui_container)
        self.small_grid_label = QLabel()
        self.sidebar_layout.addWidget(self.small_grid_label)
        self.sidebar_layout.addWidget(self.small_grid_ui_container)
        
        # Number Status
        self.status_label = QLabel()
        self.status_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.sidebar_layout.addWidget(self.status_label)
        self.status_grid = QGridLayout()
        self.status_grid.setSpacing(4)
        self.num_labels = {}
        for i in range(1, 10):
            r, c = divmod(i-1, 3)
            lbl = QLabel(str(i))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(38, 38)
            lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
            lbl.setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; color: #3498DB;")
            self.status_grid.addWidget(lbl, r, c)
            self.num_labels[i] = lbl
        self.sidebar_layout.addLayout(self.status_grid)
        self.sidebar_layout.addStretch()
        
        self.root_layout.addWidget(self.sidebar_widget)
        
        self.apply_translations()
        self.showMaximized()

    def apply_translations(self):
        if self.fog_manager is not None:
            self.fog_manager.language = self.language
        self.setWindowTitle(tr(self.language, "app_title"))
        self.new_game_btn.setText(f"{self.ICON_NEW} {tr(self.language, 'new')}")
        self.undo_btn.setText(f"{self.ICON_UNDO} {tr(self.language, 'undo')}")
        self.hint_btn.setText(f"{self.ICON_HINT} {tr(self.language, 'hint')}")
        self.notes_btn.setText(f"{self.ICON_NOTES} {tr(self.language, 'notes')}")
        self.solve_btn.setText(f"{self.ICON_SOLVE} {tr(self.language, 'solve')}")
        self.toggle_help_btn.setText(f"{self.ICON_HELP} {tr(self.language, 'help')}")
        self.quit_btn.setText(f"{self.ICON_QUIT} {tr(self.language, 'quit')}")
        self.numbers_label.setText(tr(self.language, "numbers"))
        self.mode_label.setText(tr(self.language, "mode_label"))
        self.diff_label.setText(tr(self.language, "difficulty"))
        self.layout_label.setText(tr(self.language, "layout"))
        self.language_label.setText(tr(self.language, "language"))
        self.big_grid_label.setText(tr(self.language, "big_block"))
        self.small_grid_label.setText(tr(self.language, "small_cell"))
        self.status_label.setText(tr(self.language, "number_status"))
        self.help_pager.set_language(self.language)
        if self.mission_panel:
            self.mission_panel.set_language(self.language)
        self.refresh_combos()

    def refresh_combos(self):
        # Mode combo
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        for m in MODES:
            self.mode_combo.addItem(tr(self.language, f"mode_{m}"), m)
        idx = self.mode_combo.findData(self.mode)
        self.mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.mode_combo.blockSignals(False)

        # Difficulty combo depends on current mode
        self.diff_combo.blockSignals(True)
        self.diff_combo.clear()
        if self.mode == "normal":
            for key, key_for_label, _ in NORMAL_SUBLEVELS:
                self.diff_combo.addItem(difficulty_label(self.language, key), key)
        elif self.mode == "versus":
            for key, key_for_label, cadence in VERSUS_SUBLEVELS:
                self.diff_combo.addItem(tr(self.language, key_for_label), key)
        elif self.mode == "mission":
            self.diff_combo.addItem(tr(self.language, "versus_random"), "random")
        elif self.mode == "fog":
            for key, key_for_label, _ in NORMAL_SUBLEVELS:
                self.diff_combo.addItem(difficulty_label(self.language, key), key)
        # Pick current sublevel if still present, else first
        idx = self.diff_combo.findData(self.sublevel)
        if idx < 0:
            idx = 0
            self.sublevel = self.diff_combo.itemData(idx) or self.sublevel
        self.diff_combo.setCurrentIndex(idx)
        self.diff_combo.blockSignals(False)

    # Backward-compat shim so any external caller still works.
    def refresh_difficulty_combo(self):
        self.refresh_combos()

    def on_language_changed(self, *_):
        language = self.language_combo.currentData()
        if not language:
            return
        self.language = language
        self.apply_translations()
        if self.fog_manager is not None:
            kind = self.fog_manager.kind
            idx = self.fog_manager.index
            if kind is not None:
                self.on_fog_rotated(kind, idx)
        self.setFocus()

    def ask_yes_no(self, title_key, message_key, default_yes=False):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(tr(self.language, title_key))
        box.setText(tr(self.language, message_key))
        yes_btn = box.addButton(tr(self.language, "yes"), QMessageBox.YesRole)
        no_btn = box.addButton(tr(self.language, "no"), QMessageBox.NoRole)
        box.setDefaultButton(yes_btn if default_yes else no_btn)
        box.exec_()
        return box.clickedButton() == yes_btn

    def show_info(self, title_key, message):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle(tr(self.language, title_key))
        box.setText(message)
        box.addButton(tr(self.language, "ok"), QMessageBox.AcceptRole)
        box.exec_()

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
        self.update_current_layout()
        self.update_layout_ui()
        self.setFocus()

    def toggle_sidebar(self):
        # Mission mode: only the help pager toggles; mission panel must stay visible.
        if self.mode == "mission" and self.mission_panel is not None:
            if self.help_pager.isVisible():
                self.help_pager.hide()
                self.help_pager.stop()
            else:
                self.help_pager.show()
                self.help_pager.start()
            return
        if self.sidebar_widget.isVisible():
            self.sidebar_widget.hide()
            self.help_pager.stop()
        else:
            self.sidebar_widget.show()
            self.help_pager.start()

    def confirm_quit(self):
        if self.ask_yes_no("quit_game", "quit_game_msg"):
            self.close()

    def closeEvent(self, event):
        # Make sure the AI worker thread can't outlive the window.
        self._stop_ai()
        self._stop_fog()
        try:
            self.bgm_thread.next_track()
        except Exception:
            pass
        super().closeEvent(event)

    def new_game(self):
        # Confirmation dialog
        if not self.ask_yes_no("start_game", "start_game_msg", default_yes=True):
            return

        # Stabilization hack: Fullscreen -> Restore -> Fullscreen
        self.showFullScreen()
        self.showNormal()
        self.showFullScreen()

        # Reset held key states to prevent stuck keys from dialogs
        self.held_write_add = set()
        self.held_mark_add = set()
        self.held_mod_write = False
        self.held_mod_mark = False
        self.held_big = None
        self.held_small = None

        # Stop any in-flight AI from previous game
        self._stop_ai()

        # Reset label styles
        for lbl in self.big_labels.values():
            lbl.setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; color: #2C3E50; font-weight: bold;")
        for lbl in self.small_labels.values():
            lbl.setStyleSheet("background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 4px; color: #2C3E50; font-weight: bold;")

        # Pull sublevel from combo
        combo_val = self.diff_combo.currentData()
        if combo_val:
            self.sublevel = combo_val

        # Resolve which puzzle key to send to the engine
        engine_key = self.sublevel
        if self.mode == "versus":
            engine_key = self.sublevel  # v_easy/v_medium/v_hard all map to dashi internally
            self.ai_cadence = next((c for k, _, c in VERSUS_SUBLEVELS if k == self.sublevel), 12.0)
        elif self.mode == "mission":
            engine_key = "dashi"
        elif self.mode == "fog":
            # Fog mode rides on the normal difficulty track.
            engine_key = self.sublevel if self.sublevel in NORMAL_SUBLEVEL_KEYS else NORMAL_SUBLEVELS[0][0]
        # Normal: engine_key is one of NORMAL_SUBLEVELS keys

        self.puzzle, self.solution = SudokuEngine.generate(engine_key)
        self.difficulty = engine_key
        self.grid.load_puzzle(self.puzzle)
        self.elapsed = 0
        self.used_assist = False
        self.timer_running = True
        self.timer.start(1000)
        self.update_timer_label()
        self.update_num_status()

        # Mode-specific state
        if self.mode == "versus":
            self._stop_fog()
            self._start_ai()
        elif self.mode == "mission":
            self._stop_fog()
            self._start_mission()
        elif self.mode == "fog":
            self._stop_ai()
            self.missions = []
            if self.mission_panel:
                self.mission_panel.render([])
            self._start_fog()
        else:
            self._stop_fog()
            self.missions = []
            if self.mission_panel:
                self.mission_panel.render([])

        diff_label = difficulty_label(self.language, self.difficulty)
        self.statusBar().showMessage(
            tr(self.language, "new_game_status").format(difficulty=diff_label)
        )
        self.setFocus()  # Ensure window has focus for keys

    def _stop_ai(self):
        if self.ai_worker is not None:
            self.ai_worker.stop()
            self.ai_worker.wait(2000)
            self.ai_worker = None

    def _start_ai(self):
        if not self.solution:
            return
        self.ai_worker = AIWorker(self.solution, cadence_seconds=self.ai_cadence, parent=self)
        self.ai_worker.moveReady.connect(self.on_ai_move_ready)
        self.ai_worker.update_board(self.grid.get_board())
        self.ai_worker.start()

    def _start_fog(self):
        if self.fog_manager is None:
            self.fog_manager = FogManager(self.grid, language=self.language, parent=self)
            self.fog_manager.rotated.connect(self.on_fog_rotated)
        # Make sure the visible status pill exists.
        self._ensure_fog_status_label()
        self.fog_manager.language = self.language
        self.fog_manager.start()

    def _stop_fog(self):
        if self.fog_manager is not None:
            self.fog_manager.stop()
        label = getattr(self, 'fog_status_label', None)
        if label is not None:
            label.setText("")
            label.hide()

    def _ensure_fog_status_label(self):
        if getattr(self, 'fog_status_label', None) is not None:
            return
        label = QLabel("")
        label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        label.setStyleSheet(
            "color: #ECF0F1; background-color: #34495E; padding: 6px 14px;"
            " border-radius: 14px;"
        )
        label.setAlignment(Qt.AlignCenter)
        label.hide()
        # Park it in the second top bar to the right of the language combo so
        # it stays out of the grid.
        self.top_bar_2.addWidget(label)
        self.fog_status_label = label

    def on_fog_rotated(self, kind, index):
        if self.fog_status_label is None:
            return
        desc = self.fog_manager.describe() if self.fog_manager else ''
        try:
            text = tr(self.language, 'fog_status').format(kind=desc)
        except KeyError:
            text = f'Fog: {desc}'
        self.fog_status_label.setText(text)
        self.fog_status_label.show()
        self.statusBar().showMessage(text)

    def _start_mission(self):
        self.missions = MissionEngine.sample_three()
        # Reset ctx
        for k in self.ctx:
            self.ctx[k] = False
        self.first_move_deadline = time.time() + 30
        self.speed_run_deadline = time.time() + 60
        if self.mission_panel:
            self.mission_panel.render(self.missions)
            self.mission_panel.setVisible(True)

    def on_ai_move_ready(self, move):
        r, c, val = move
        # Drop moves on cells the player already filled.
        cell = self.grid.cells[r][c]
        if cell.value != 0 or cell.is_locked:
            return
        if self.grid.is_complete(self.solution):
            return
        self.grid.set_cell_value_ai(r, c, val)
        if self.ai_worker:
            self.ai_worker.update_board(self.grid.get_board())
        # Sync the timer state too (board_changed handles win check)

    def on_difficulty_changed(self, *_):
        self.sublevel = self.diff_combo.currentData() or self.sublevel
        self.new_game()

    def _sync_sidebar_for_mode(self):
        """Mission mode always shows the right sidebar (mission panel lives inside).

        In other modes, the user controls visibility via F1.
        """
        if self.mode == "mission":
            self.sidebar_widget.show()
            self.help_pager.start()
        # Other modes: leave visibility as the user set it (default hidden).

    def on_mode_changed(self, *_):
        new_mode = self.mode_combo.currentData() or "normal"
        if new_mode == self.mode:
            return
        self._stop_ai()
        self._stop_fog()
        self.mode = new_mode
        # Reset sublevel to first available for the new mode
        if self.mode == "normal":
            self.sublevel = NORMAL_SUBLEVELS[0][0]
        elif self.mode == "versus":
            self.sublevel = VERSUS_SUBLEVELS[0][0]
        elif self.mode == "fog":
            self.sublevel = NORMAL_SUBLEVELS[0][0]
        else:
            self.sublevel = "random"
        self.refresh_combos()
        # Mission panel visibility
        if self.mission_panel:
            self.mission_panel.setVisible(self.mode == "mission")
        self._sync_sidebar_for_mode()
        self.new_game()

    def on_number_selected(self, num):
        self.grid.place_number(num)

    def on_erase(self):
        self.grid.erase_cell()

    def on_notes_toggled(self, enabled):
        self.grid.notes_mode = enabled

    def on_undo_clicked(self):
        if self.mode == "mission":
            self.ctx["used_undo"] = True
        self.grid.undo()

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
        if self.mode == "fog" and self.fog_manager is not None:
            # If the player just filled every cell in the currently revealed
            # band, rotate the fog immediately instead of waiting for the
            # 8 s timer.
            self.fog_manager.maybe_advance_now()
        if self.mode == "mission":
            self._evaluate_missions()
            if self.missions and MissionEngine.all_done(self.missions):
                self._finish_mission_game(bonus=True)
                return
        if self.grid.is_complete(self.solution):
            self.timer_running = False
            self.timer.stop()
            self._stop_ai()
            self._stop_fog()
            if self.mode == "versus":
                # Versus excluded from leaderboard.
                self.show_info(
                    "congratulations",
                    f"{tr(self.language, 'versus_player_win')}\n"
                    f"{tr(self.language, 'time')}: {self.timer_label.text()[2:]}"
                )
                self.new_game()
                return
            if self.mode == "mission":
                self._finish_mission_game(bonus=False)
                return
            if self.mode == "fog":
                if not self.used_assist:
                    LeaderboardManager.save_score("fog", self.elapsed)
                self.show_info(
                    "congratulations",
                    f"🌪️ {tr(self.language, 'puzzle_solved')}\n{tr(self.language, 'time')}: {self.timer_label.text()[2:]}"
                )
                self.show_leaderboard()
                self.new_game()
                return
            if not self.used_assist:
                LeaderboardManager.save_score(self.difficulty, self.elapsed)
            self.show_info(
                "congratulations",
                f"🎉 {tr(self.language, 'puzzle_solved')}\n{tr(self.language, 'time')}: {self.timer_label.text()[2:]}"
            )
            self.show_leaderboard()
            self.new_game()

    def _finish_mission_game(self, bonus=False):
        """End the current mission game and save score.

        When all 3 missions finish before the board is full (bonus=True), the
        player gets extra points proportional to how much of the board remains
        empty — rewarding the early end.
        """
        self.timer_running = False
        self.timer.stop()
        base = 3000 - self.elapsed
        if base < 0:
            base = 0
        bonus_pts = 0
        empties = 0
        if bonus:
            for r in range(9):
                for c in range(9):
                    if self.grid.cells[r][c].value == 0:
                        empties += 1
            bonus_pts = empties * 10
        score = base + bonus_pts
        LeaderboardManager.save_score("mission", score, is_score=True)
        if bonus:
            msg = (
                f"{tr(self.language, 'missions_done')}\n"
                f"{tr(self.language, 'mission_score')}: {score}"
                f"  (+{bonus_pts})"
            )
        else:
            msg = (
                f"{tr(self.language, 'missions_done')}\n"
                f"{tr(self.language, 'mission_score')}: {score}"
            )
        self.show_info("congratulations", msg)
        self.show_leaderboard()
        self.new_game()

    def show_leaderboard(self):
        dlg = LeaderboardDialog(self, self.language)
        dlg.set_difficulty(self.difficulty if self.mode == "normal" else self.mode)
        dlg.exec_()
        self.setFocus()

    def _evaluate_missions(self):
        if not self.missions:
            return
        board = self.grid.get_board()
        # Track first-move correctness: any correct non-given non-ai fill within 30s.
        if not self.ctx["first_move_correct"] and self.elapsed <= 30 and board != self.puzzle:
            for r in range(9):
                for c in range(9):
                    pv = self.puzzle[r][c]
                    bv = board[r][c]
                    if pv == 0 and bv != 0 and bv == self.solution[r][c]:
                        self.ctx["first_move_correct"] = True
                        break
                if self.ctx["first_move_correct"]:
                    break
        # Track speed-run: any 3x3 sub-block fully filled within 60s.
        if not self.ctx["subblock_done"] and self.elapsed <= 60:
            for br in range(0, 9, 3):
                for bc in range(0, 9, 3):
                    if all(board[br + i][bc + j] != 0 for i in range(3) for j in range(3)):
                        self.ctx["subblock_done"] = True
                        break
                if self.ctx["subblock_done"]:
                    break
        # made_error: any non-given non-ai cell disagrees with solution.
        if not self.ctx["made_error"]:
            for r in range(9):
                for c in range(9):
                    cell = self.grid.cells[r][c]
                    bv = board[r][c]
                    if bv != 0 and not cell.given and not cell.ai_filled:
                        if bv != self.solution[r][c]:
                            self.ctx["made_error"] = True
                            break
                if self.ctx["made_error"]:
                    break
        # row_no_notes: any row fully filled while we never used notes mode this game.
        # Notes mode is global; we approximate by checking notes_btn.isChecked never was True.
        if not self.ctx["row_no_notes"] and not self.notes_btn.isChecked():
            for r in range(9):
                if all(board[r][c] != 0 for c in range(9)):
                    self.ctx["row_no_notes"] = True
                    break

        ctx = dict(self.ctx)
        ctx["elapsed"] = self.elapsed
        MissionEngine.evaluate(self.missions, board, self.solution, ctx)
        if self.mission_panel:
            self.mission_panel.render(self.missions)

    def on_cell_selected(self, r, c):
        val = self.grid.cells[r][c].value
        if val:
            self.statusBar().showMessage(f"{tr(self.language, 'cell')} ({r+1},{c+1}): {val}")
        else:
            self.statusBar().showMessage(f"{tr(self.language, 'cell')} ({r+1},{c+1})")

    def give_hint(self):
        r, c = self.grid.selected_pos
        cell = self.grid.cells[r][c]
        if not cell.given:
            self.used_assist = True
            if self.mode == "mission":
                self.ctx["used_hint"] = True
            cell.set_given(self.solution[r][c])
            self.grid.validate_and_mark()
            self.grid.update_highlights()
            self.on_board_changed()

    def show_solution(self):
        if self.ask_yes_no("show_solution", "show_solution_msg"):
            self.used_assist = True
            if self.mode == "mission":
                self.ctx["used_hint"] = True
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
            playing = self.bgm_thread.toggle()
            self.statusBar().showMessage(tr(self.language, "bgm_playing" if playing else "bgm_paused"))
            return
        elif key == Qt.Key_F3:
            self.bgm_thread.next_track()
            self.statusBar().showMessage(tr(self.language, "bgm_changing"))
            return
        elif key == Qt.Key_F4:
            # Removed old difficulty shortcut
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
            self.on_undo_clicked()
            return

        char = event.text().lower()
        if not char:
            return
        
        # Track momentary modifiers
        if char == self.mod_write_key:
            self.held_mod_write = True
        if char == self.mod_mark_key:
            self.held_mod_mark = True

        if char == self.mode_write_key:
            self.notes_btn.setChecked(False)
        elif char == self.mode_note_key:
            self.notes_btn.setChecked(True)
        elif char in self.write_add_keys:
            # Sum-keys are disabled in Mission mode per requirement.
            if self.mode == "mission":
                return
            self.held_write_add.add(char)
            total = sum(self.write_add_keys[k] for k in self.held_write_add)
            if total > 9: total = 0
            old_mode = self.grid.notes_mode
            self.grid.notes_mode = False
            self.grid.place_number(total)
            self.grid.notes_mode = old_mode
        elif char in self.mark_add_keys:
            # Sum-keys are disabled in Mission mode per requirement.
            if self.mode == "mission":
                return
            self.held_mark_add.add(char)
            total = sum(self.mark_add_keys[k] for k in self.held_mark_add)
            if total > 9: total = 0
            old_mode = self.grid.notes_mode
            self.grid.notes_mode = True
            self.grid.place_number(total)
            self.grid.notes_mode = old_mode
        elif char in self.big_keys:
            idx = self.big_keys.index(char)
            if self.held_mod_write:
                # Momentary Write Mode (n + big)
                old_mode = self.grid.notes_mode
                self.grid.notes_mode = False
                self.grid.place_number(idx + 1)
                self.grid.notes_mode = old_mode
            else:
                self.held_big = idx
                self.big_labels[char].setStyleSheet("background-color: #3498DB; color: white; border: 1px solid #2980B9; border-radius: 4px; font-weight: bold;")
                self.locate_nested()
        elif char in self.small_keys:
            idx = self.small_keys.index(char)
            if self.held_mod_mark:
                # Momentary Mark Mode (b + small)
                old_mode = self.grid.notes_mode
                self.grid.notes_mode = True
                self.grid.place_number(idx + 1)
                self.grid.notes_mode = old_mode
            else:
                self.held_small = idx
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
            
        if char == self.mod_write_key:
            self.held_mod_write = False
        if char == self.mod_mark_key:
            self.held_mod_mark = False
            
        if char in self.write_add_keys:
            if char in self.held_write_add:
                self.held_write_add.remove(char)
        elif char in self.mark_add_keys:
            if char in self.held_mark_add:
                self.held_mark_add.remove(char)
        elif char in self.big_keys:
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


"""poker_app_gui_pretty_v4.py

Prettier + more usable Tkinter GUI for the poker engine.

Changes vs earlier versions:
- Intuitive menu bar (Game / CPU / Help)
- CPU difficulty selector (presets)
- "What does this mean?" legend window
- Preflop practice trainer (simple RFI / unopened-pot training)
- Bigger community + player cards, with *player cards under the board*

Run:
  python poker_app_gui_pretty_v3.py
"""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

from poker_engine import GameSettings, PokerEngine, estimate_win_prob, format_cards, street_name


# --- CPU difficulty presets (higher = smarter but slower) ---
CPU_PRESETS = {
    "Beginner": dict(cpu_aggression=0.90, cpu_randomness=0.65, mc_pre=120, mc_post=180),
    "Normal":   dict(cpu_aggression=1.00, cpu_randomness=0.45, mc_pre=220, mc_post=320),
    "Strong":   dict(cpu_aggression=1.15, cpu_randomness=0.25, mc_pre=450, mc_post=650),
    "Pro":      dict(cpu_aggression=1.25, cpu_randomness=0.12, mc_pre=800, mc_post=1100),
}


class PokerGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Texas Hold'em (Adaptive CPUs)")
        self.geometry("1140x770")
        self.minsize(980, 660)

        # --- Visual theme (no external deps) ---
        self._setup_style()

        # Auto-advance flow (no need to click 'Next' every hand)
        self.auto_advance_hand = True
        self._auto_next_after_id = None

        self.cpu_preset_var = tk.StringVar(value="Normal")
        self._build_menu()

        self.settings = GameSettings()
        self.engine = PokerEngine(self.settings)

        self._build_ui()
        self._refresh()
        # Auto-start a new 6-player hand on launch
        self.after(10, self._next_hand)

    # ---------------- UI: menu / theme ----------------
    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        game = tk.Menu(menubar, tearoff=0)
        game.add_command(label="New hand", accelerator="Ctrl+N", command=self._next_hand)
        game.add_command(label="Preflop practice…", accelerator="Ctrl+P", command=self._open_preflop_practice)
        game.add_separator()
        game.add_command(label="Settings…", accelerator="Ctrl+,", command=self._open_settings)
        game.add_separator()
        game.add_command(label="Quit", accelerator="Ctrl+Q", command=self.destroy)
        menubar.add_cascade(label="Game", menu=game)

        cpu = tk.Menu(menubar, tearoff=0)
        for name in CPU_PRESETS.keys():
            cpu.add_radiobutton(label=name, variable=self.cpu_preset_var, value=name, command=self._apply_cpu_preset)
        menubar.add_cascade(label="CPU", menu=cpu)

        helpm = tk.Menu(menubar, tearoff=0)
        helpm.add_command(label="What does this mean? (Legend)", accelerator="F1", command=self._open_info)
        menubar.add_cascade(label="Help", menu=helpm)

        self.config(menu=menubar)

        # Keyboard shortcuts
        self.bind_all("<Control-n>", lambda e: self._next_hand())
        self.bind_all("<Control-p>", lambda e: self._open_preflop_practice())
        self.bind_all("<Control-comma>", lambda e: self._open_settings())
        self.bind_all("<Control-q>", lambda e: self.destroy())
        self.bind_all("<F1>", lambda e: self._open_info())

    def _setup_style(self) -> None:
        """Make the Tkinter/ttk UI look more modern and readable."""
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Palette (dark, poker-table-ish)
        self.ui_bg = "#101418"
        self.ui_panel = "#151b22"
        self.ui_panel2 = "#0f141b"
        self.ui_text = "#e7eef8"
        self.ui_muted = "#a9b7c8"
        self.ui_accent = "#4da3ff"
        self.ui_good = "#2ecc71"
        self.ui_bad = "#ff5c5c"
        self.ui_border = "#253041"

        self.configure(bg=self.ui_bg)

        # Fonts
        self.font_base = tkfont.Font(family="Segoe UI", size=10)
        self.font_title = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.font_mono = tkfont.Font(family="Consolas", size=11)
        self.font_mono_bold = tkfont.Font(family="Consolas", size=11, weight="bold")
        # Bigger cards (requested)
        self.font_cards = tkfont.Font(family="Consolas", size=18, weight="bold")
        self.font_cards_small = tkfont.Font(family="Consolas", size=13, weight="bold")

        # Generic ttk widget styling
        style.configure(".", font=self.font_base, background=self.ui_bg, foreground=self.ui_text)
        style.configure("TFrame", background=self.ui_bg)
        style.configure("Card.TFrame", background=self.ui_panel, relief="flat")
        style.configure("TLabel", background=self.ui_bg, foreground=self.ui_text)
        style.configure("Title.TLabel", font=self.font_title, background=self.ui_bg, foreground=self.ui_text)
        style.configure("Muted.TLabel", background=self.ui_bg, foreground=self.ui_muted)
        style.configure("TSeparator", background=self.ui_border)

        style.configure("TLabelframe", background=self.ui_bg, foreground=self.ui_text)
        style.configure("TLabelframe.Label", background=self.ui_bg, foreground=self.ui_text, font=self.font_base)

        style.configure("TButton", padding=(10, 6))
        style.map(
            "TButton",
            foreground=[("disabled", self.ui_muted)],
            background=[("disabled", self.ui_panel2)],
        )

        style.configure("Primary.TButton", padding=(12, 7))
        style.map(
            "Primary.TButton",
            foreground=[("!disabled", self.ui_text)],
            background=[("!disabled", self.ui_accent), ("active", self.ui_accent)],
        )

        # Action buttons (highlight legal moves in red)
        style.configure("Action.TButton", padding=(10, 6))
        style.map(
            "Action.TButton",
            foreground=[("disabled", self.ui_muted), ("!disabled", self.ui_text)],
            background=[("disabled", self.ui_panel2), ("!disabled", self.ui_panel)],
        )

        style.configure("Hot.Action.TButton", padding=(10, 6))
        style.map(
            "Hot.Action.TButton",
            foreground=[("!disabled", self.ui_bad), ("active", self.ui_bad), ("disabled", self.ui_muted)],
            background=[("!disabled", self.ui_panel), ("active", self.ui_panel)],
        )

        # Treeview styling
        style.configure(
            "Treeview",
            background=self.ui_panel2,
            fieldbackground=self.ui_panel2,
            foreground=self.ui_text,
            bordercolor=self.ui_border,
            lightcolor=self.ui_border,
            darkcolor=self.ui_border,
            rowheight=26,
        )
        style.configure(
            "Treeview.Heading",
            font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
            background=self.ui_panel,
            foreground=self.ui_text,
            relief="flat",
        )
        style.map("Treeview.Heading", background=[("active", self.ui_panel)])

        style.configure("TEntry", padding=(6, 4))

    # ---------------- UI: main layout ----------------
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=12, style="Card.TFrame")
        right = ttk.Frame(self, padding=12, style="Card.TFrame")
        left.grid(row=0, column=0, sticky="nsew")
        right.grid(row=0, column=1, sticky="nsew")

        # Left layout rows
        left.rowconfigure(4, weight=1)  # table expands
        right.rowconfigure(1, weight=1)

        self.status_var = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.status_var, style="Title.TLabel").grid(row=0, column=0, sticky="w")

        # --- Big cards area (community on top, player under it) ---
        cards = ttk.Frame(left)
        cards.grid(row=1, column=0, sticky="ew", pady=(10, 2))
        cards.columnconfigure(0, weight=1)

        self.board_cards_var = tk.StringVar(value="")
        self.hero_cards_var = tk.StringVar(value="")
        ttk.Label(cards, textvariable=self.board_cards_var, font=self.font_cards).grid(row=0, column=0, sticky="w")
        ttk.Label(cards, textvariable=self.hero_cards_var, font=self.font_cards).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.pot_var = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.pot_var, style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(2, 8))

        # Players table
        cols = ("player", "stack", "street_bet", "status")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=11)
        self.tree.tag_configure("odd", background="#111722")
        self.tree.tag_configure("even", background=self.ui_panel2)
        for c, w, anchor in (
            ("player", 170, "w"),
            ("stack", 90, "e"),
            ("street_bet", 95, "e"),
            ("status", 170, "w"),
        ):
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=w, anchor=anchor)
        self.tree.grid(row=4, column=0, sticky="nsew", pady=(8, 10))

        tree_scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.grid(row=4, column=1, sticky="ns", pady=(8, 10))
        left.columnconfigure(1, weight=0)

        # Action box
        action_box = ttk.LabelFrame(left, text="Your action", padding=10)
        action_box.grid(row=5, column=0, sticky="ew")
        action_box.columnconfigure(0, weight=1)

        self.prompt_var = tk.StringVar(value="")
        self.odds_var = tk.StringVar(value="")
        ttk.Label(action_box, textvariable=self.prompt_var).grid(row=0, column=0, sticky="w", pady=(2, 2))
        ttk.Label(action_box, textvariable=self.odds_var).grid(row=1, column=0, sticky="w", pady=(0, 8))

        btn_row = ttk.Frame(action_box)
        btn_row.grid(row=2, column=0, sticky="w")

        self.btn_fold = ttk.Button(btn_row, text="Fold", style="Action.TButton", command=lambda: self._act("fold"))
        self.btn_check = ttk.Button(btn_row, text="Check", style="Action.TButton", command=lambda: self._act("check"))
        self.btn_call = ttk.Button(btn_row, text="Call", style="Action.TButton", command=lambda: self._act("call"))
        self.btn_bet = ttk.Button(btn_row, text="Bet", style="Action.TButton", command=lambda: self._act("bet"))
        self.btn_raise = ttk.Button(btn_row, text="Raise", style="Action.TButton", command=lambda: self._act("raise"))
        self.btn_allin = ttk.Button(btn_row, text="All-in", style="Action.TButton", command=lambda: self._act("allin"))
        for j, b in enumerate([
            self.btn_fold,
            self.btn_check,
            self.btn_call,
            self.btn_bet,
            self.btn_raise,
            self.btn_allin,
        ]):
            b.grid(row=0, column=j, padx=(0 if j == 0 else 6, 0))

        amt_row = ttk.Frame(action_box)
        amt_row.grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(amt_row, text="Amount:").grid(row=0, column=0, sticky="w")
        self.amount_var = tk.StringVar(value="")
        self.amount_entry = ttk.Entry(amt_row, textvariable=self.amount_var, width=10)
        self.amount_entry.grid(row=0, column=1, padx=(6, 0))
        ttk.Label(amt_row, text="(used for Bet/Raise; blank uses default)").grid(row=0, column=2, padx=(8, 0))

        # Controls row
        ctrl = ttk.Frame(left)
        ctrl.grid(row=6, column=0, sticky="w", pady=(10, 0))

        self.btn_next = ttk.Button(ctrl, text="New hand", style="Primary.TButton", command=self._next_hand)
        self.btn_practice = ttk.Button(ctrl, text="Preflop practice", command=self._open_preflop_practice)
        self.btn_settings = ttk.Button(ctrl, text="Settings", command=self._open_settings)
        self.btn_info = ttk.Button(ctrl, text="What does this mean?", command=self._open_info)

        ttk.Separator(ctrl, orient="vertical").grid(row=0, column=4, sticky="ns", padx=10)
        ttk.Label(ctrl, text="CPU:").grid(row=0, column=5, sticky="w")
        self.cpu_combo = ttk.Combobox(
            ctrl,
            textvariable=self.cpu_preset_var,
            values=list(CPU_PRESETS.keys()),
            width=10,
            state="readonly",
        )
        self.cpu_combo.grid(row=0, column=6, padx=(6, 6))
        ttk.Button(ctrl, text="Apply", command=self._apply_cpu_preset).grid(row=0, column=7, padx=(0, 10))
        ttk.Button(ctrl, text="Quit", command=self.destroy).grid(row=0, column=8)

        self.btn_next.grid(row=0, column=0, padx=(0, 8))
        self.btn_practice.grid(row=0, column=1, padx=(0, 8))
        self.btn_settings.grid(row=0, column=2, padx=(0, 8))
        self.btn_info.grid(row=0, column=3, padx=(0, 8))

        # Right: log + stats
        ttk.Label(right, text="Game log", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        log_wrap = ttk.Frame(right)
        log_wrap.grid(row=1, column=0, sticky="nsew", pady=(8, 10))
        log_wrap.rowconfigure(0, weight=1)
        log_wrap.columnconfigure(0, weight=1)

        self.log = tk.Text(
            log_wrap,
            wrap="word",
            bg=self.ui_panel2,
            fg=self.ui_text,
            insertbackground=self.ui_text,
            relief="flat",
            borderwidth=0,
            font=self.font_base,
            padx=10,
            pady=8,
            highlightthickness=1,
            highlightbackground=self.ui_border,
            highlightcolor=self.ui_border,
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(state="disabled")

        self.log.tag_configure("good", foreground=self.ui_good)
        self.log.tag_configure("bad", foreground=self.ui_bad)
        self.log.tag_configure("muted", foreground=self.ui_muted)
        self.log.tag_configure("street", foreground=self.ui_accent, font=self.font_base)

        self.stats_var = tk.StringVar(value="")
        stats = ttk.LabelFrame(right, text="Learning / style stats", padding=12)
        stats.grid(row=2, column=0, sticky="ew")
        ttk.Label(stats, textvariable=self.stats_var, justify="left").grid(row=0, column=0, sticky="w")

    # ---------------- CPU presets ----------------
    def _apply_cpu_preset(self) -> None:
        """Apply selected CPU preset (resets the current game)."""
        name = self.cpu_preset_var.get()
        p = CPU_PRESETS.get(name, CPU_PRESETS["Normal"])

        self.settings = GameSettings(
            players=self.settings.players,
            start_stack=self.settings.start_stack,
            sb=self.settings.sb,
            bb=self.settings.bb,
            seed=self.settings.seed,
            cpu_aggression=p["cpu_aggression"],
            cpu_randomness=p["cpu_randomness"],
            mc_iters_preflop=p["mc_pre"],
            mc_iters_postflop=p["mc_post"],
        )
        self.engine = PokerEngine(self.settings)
        self._refresh()
        self.after(10, self._next_hand)

    # ---------------- Legend / info ----------------
    def _open_info(self) -> None:
        win = tk.Toplevel(self)
        win.title("Legend / Help")
        win.geometry("760x580")
        win.minsize(640, 440)

        outer = ttk.Frame(win, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")
        win.rowconfigure(0, weight=1)
        win.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="What all this info means", style="Title.TLabel").grid(row=0, column=0, sticky="w")

        txt = tk.Text(
            outer,
            wrap="word",
            bg=self.ui_panel2,
            fg=self.ui_text,
            insertbackground=self.ui_text,
            relief="flat",
            borderwidth=0,
            font=self.font_base,
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground=self.ui_border,
            highlightcolor=self.ui_border,
        )
        txt.grid(row=1, column=0, sticky="nsew", pady=(10, 10))
        scr = ttk.Scrollbar(outer, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=scr.set)
        scr.grid(row=1, column=1, sticky="ns", pady=(10, 10))

        help_text = """TABLE (left)
• Player: name + badges
   D = Dealer button, SB/BB = blinds, * = acting right now
• Stack: chips you still have
• Street bet: chips you put in on the CURRENT street (preflop/flop/turn/river)
• Status: FOLD or ALL‑IN

CARDS (top)
• Board: community cards (shared)
• You: your two hole cards

POT LINE
• Pot: total chips in the pot
• Bet: current amount to match on this street

YOUR ACTION box
• To call: how much you need to put in to match the current bet
• Min raise to: the smallest total bet size you’re allowed to raise to
• Amount: only used for Bet/Raise (blank uses a sensible default)

WIN ODDS
• “Win odds” is a quick Monte‑Carlo estimate vs the remaining opponents.
  It’s approximate (higher CPU difficulty uses more simulations).

GAME LOG (right)
• A readable history of what happened this hand.

CPU DIFFICULTY
• Beginner → more random, fewer simulations (faster, weaker)
• Pro → less random, more simulations (slower, stronger)
"""
        txt.insert("1.0", help_text)
        txt.configure(state="disabled")

        btns = ttk.Frame(outer)
        btns.grid(row=2, column=0, columnspan=2, sticky="e")
        ttk.Button(btns, text="Close", command=win.destroy).grid(row=0, column=0)

    # ---------------- Preflop practice ----------------
    def _open_preflop_practice(self) -> None:
        """Simple preflop trainer: unopened pot, choose a default action."""
        win = tk.Toplevel(self)
        win.title("Preflop practice")
        win.geometry("720x520")
        win.minsize(620, 460)

        outer = ttk.Frame(win, padding=14)
        outer.grid(row=0, column=0, sticky="nsew")
        win.rowconfigure(0, weight=1)
        win.columnconfigure(0, weight=1)

        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="Preflop Trainer", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text=(
                "Goal: practice a solid default decision in an *unopened* pot (everyone folded to you).\n"
                "This is a simplified trainer (good for fundamentals)."
            ),
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 10))

        # Trainer controls
        ctl = ttk.Frame(outer)
        ctl.grid(row=1, column=0, sticky="ew", pady=(6, 10))
        ctl.columnconfigure(5, weight=1)

        level_var = tk.StringVar(value="Beginner")
        pos_focus_var = tk.StringVar(value="Any")

        ttk.Label(ctl, text="Level:", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        level_cb = ttk.Combobox(ctl, textvariable=level_var, state="readonly",
                                values=["Beginner", "Intermediate", "Advanced"], width=14)
        level_cb.grid(row=0, column=1, sticky="w", padx=(6, 18))

        ttk.Label(ctl, text="Position focus:", style="Muted.TLabel").grid(row=0, column=2, sticky="w")
        pos_cb = ttk.Combobox(ctl, textvariable=pos_focus_var, state="readonly",
                              values=["Any", "UTG", "HJ", "CO", "BTN", "SB"], width=8)
        pos_cb.grid(row=0, column=3, sticky="w", padx=(6, 18))

        ttk.Label(ctl, text="Tip: choose a level + position, then answer fast. It auto-deals the next hand.", style="Muted.TLabel").grid(row=0, column=4, sticky="w")

        # State
        hand_var = tk.StringVar(value="")
        spot_var = tk.StringVar(value="")
        advice_var = tk.StringVar(value="")
        feedback_var = tk.StringVar(value="")

        # Big hand display
        ttk.Label(outer, textvariable=hand_var, font=self.font_cards).grid(row=2, column=0, sticky="w")
        ttk.Label(outer, textvariable=spot_var, font=self.font_cards_small).grid(row=3, column=0, sticky="w", pady=(6, 2))

        box = ttk.LabelFrame(outer, text="Your choice", padding=12)
        box.grid(row=4, column=0, sticky="ew", pady=(12, 8))
        box.columnconfigure(0, weight=1)

        btns = ttk.Frame(box)
        btns.grid(row=0, column=0, sticky="w")

        # The trainer expects: Fold / Call / Raise
        def choose(action: str) -> None:
            nonlocal correct_action, _auto_next_id
            if action == correct_action:
                feedback_var.set("✅ Nice — that matches the suggested default.")
            else:
                feedback_var.set(f"❌ Suggested: {correct_action}. Tap ‘Show why’ to learn.")

            # Auto move on after a short beat (keeps reps fast)
            if _auto_next_id is not None:
                try:
                    win.after_cancel(_auto_next_id)
                except Exception:
                    pass
            _auto_next_id = win.after(900, deal_new)

        ttk.Button(btns, text="Fold", style="Hot.Action.TButton", command=lambda: choose("Fold")).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Call", style="Hot.Action.TButton", command=lambda: choose("Call")).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btns, text="Raise", style="Hot.Action.TButton", command=lambda: choose("Raise")).grid(row=0, column=2)

        ttk.Label(box, textvariable=feedback_var).grid(row=1, column=0, sticky="w", pady=(10, 0))

        why = ttk.LabelFrame(outer, text="Show why", padding=12)
        why.grid(row=5, column=0, sticky="nsew")
        outer.rowconfigure(5, weight=1)

        txt = tk.Text(
            why,
            wrap="word",
            bg=self.ui_panel2,
            fg=self.ui_text,
            insertbackground=self.ui_text,
            relief="flat",
            borderwidth=0,
            font=self.font_base,
            padx=10,
            pady=8,
            height=9,
            highlightthickness=1,
            highlightbackground=self.ui_border,
            highlightcolor=self.ui_border,
        )
        txt.grid(row=0, column=0, sticky="nsew")
        why.rowconfigure(0, weight=1)
        why.columnconfigure(0, weight=1)
        txt.configure(state="disabled")

        correct_action = "Fold"
        expl = ""
        _auto_next_id = None

        def deal_new() -> None:
            nonlocal correct_action, expl
            feedback_var.set("")

            # Random hand as *strings* so we don't depend on Card internals
            ranks = list("23456789TJQKA")
            suits = ["s", "h", "d", "c"]
            r1, r2 = random.sample(ranks, 2)
            s1, s2 = random.choice(suits), random.choice(suits)
            suited = (s1 == s2)

            # Sometimes generate pairs
            if random.random() < 0.25:
                r2 = r1
                s2 = random.choice([x for x in suits if x != s1])
                suited = False

            pos_choices = ["UTG", "HJ", "CO", "BTN", "SB"]
            pos = random.choice(pos_choices) if pos_focus_var.get() == "Any" else pos_focus_var.get()
            eff = random.choice([20, 30, 40, 60, 100])

            hand = _pretty_hand(r1, s1, r2, s2)
            hand_var.set(f"Hand: {hand}")
            spot_var.set(f"Spot: Unopened pot • Position: {pos} • Effective stack: {eff}bb")

            correct_action, expl = _trainer_advice(r1, r2, suited, pos, level_var.get())
            advice_var.set(correct_action)

            # Clear explanation until requested
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert(
                "1.0",
                "Tap ‘Show why’ below to reveal the suggested default and the reasoning.",
            )
            txt.configure(state="disabled")

        def show_why() -> None:
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", f"Suggested default: {correct_action}\n\n{expl}")
            txt.configure(state="disabled")

        foot = ttk.Frame(outer)
        foot.grid(row=6, column=0, sticky="e", pady=(10, 0))
        ttk.Button(foot, text="Show why", command=show_why).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(foot, text="Deal now", style="Primary.TButton", command=deal_new).grid(row=0, column=1)

        deal_new()

    # ---------------- Game loop ----------------
    def _next_hand(self) -> None:
        self.engine.start_new_hand()
        self.engine.advance()
        self._refresh()
        self.after(10, self._cpu_loop)

    def _cpu_loop(self) -> None:
        if not self.engine.hand_active or self.engine.waiting_for_human:
            self._refresh()
            return
        self.engine.advance()
        self._refresh()
        self.after(10, self._cpu_loop)

    def _parse_amount(self) -> int:
        raw = self.amount_var.get().strip()
        if raw == "":
            return 0
        try:
            return max(0, int(raw))
        except ValueError:
            return 0

    def _act(self, action: str) -> None:
        prompt = self.engine.prompt
        amt = self._parse_amount()

        if action in ("bet", "raise") and prompt and amt <= 0:
            pot = prompt["pot"]
            min_raise_to = prompt["min_raise_to"]
            you_stack = prompt["you_stack"]
            if action == "bet":
                amt = min(max(self.settings.bb * 2, pot // 2), you_stack)
            else:
                amt = min(max(min_raise_to, min_raise_to + pot // 2), you_stack + prompt["you_bet_street"])

        self.engine.apply_human_action(action, amt)
        self.engine.advance()
        self._refresh()
        self.after(10, self._cpu_loop)

    def _refresh(self) -> None:
        street = street_name(self.engine.board)
        self.status_var.set(street)

        # Big cards display
        board_txt = format_cards(self.engine.board) if self.engine.board else "— — — — —"
        self.board_cards_var.set(f"Board: {board_txt}")

        hero = next((p for p in self.engine.players if p.is_human), None)
        hero_txt = format_cards(hero.hole) if hero and hero.hole else "?? ??"
        self.hero_cards_var.set(f"You:   {hero_txt}")

        self.pot_var.set(f"Pot: {self.engine.pot}   Bet: {self.engine.current_bet}")

        # Table
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, p in enumerate(self.engine.players):
            badges = []
            if idx == self.engine.dealer_index:
                badges.append("D")
            if idx == self.engine.sb_index:
                badges.append("SB")
            if idx == self.engine.bb_index:
                badges.append("BB")
            if idx == self.engine.acting_i and self.engine.hand_active:
                badges.append("*")
            name = p.name + (f" ({'/'.join(badges)})" if badges else "")
            status = "FOLD" if p.folded else "ALL-IN" if p.all_in else ""
            tag = "even" if (idx % 2 == 0) else "odd"
            self.tree.insert("", "end", values=(name, p.stack, p.bet_street, status), tags=(tag,))

        # Odds
        odds_txt = ""
        if hero and getattr(hero, "hole", None):
            num_opps = sum(1 for p in self.engine.players if not p.is_human and not p.folded)
            if num_opps > 0:
                base_iters = self.settings.mc_iters_preflop if len(self.engine.board) == 0 else self.settings.mc_iters_postflop
                iters = max(150, int(base_iters * 0.6))
                try:
                    wp = estimate_win_prob(self.engine.rng, hero.hole, self.engine.board, num_opps, iters)
                    odds_txt = f"Win odds vs {num_opps} opps: {wp * 100:.1f}%"
                except Exception:
                    odds_txt = ""
        self.odds_var.set(odds_txt)

        if self.engine.waiting_for_human and self.engine.prompt:
            pr = self.engine.prompt
            self.prompt_var.set(
                f"To call: {pr['to_call']}   Min raise to: {pr['min_raise_to']}   Your stack: {pr['you_stack']}"
            )
        else:
            self.prompt_var.set("Click 'New hand' to start." if not self.engine.hand_active else "Waiting…")

        # Log
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        for line in self.engine.log[-300:]:
            tag = None
            upper = line.upper()
            if any(k in upper for k in ("WIN", "WINS", "COLLECT")):
                tag = "good"
            elif any(k in upper for k in ("FOLD", "LOSE", "BUST")):
                tag = "bad"
            elif any(k in upper for k in ("FLOP", "TURN", "RIVER", "PREFLOP", "SHOWDOWN")):
                tag = "street"
            elif any(k in upper for k in ("POSTS", "BLIND", "ANTE")):
                tag = "muted"
            self.log.insert("end", line + "\n", tag) if tag else self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

        # Stats (best-effort; engine provides these)
        hs = self.engine.human_stats
        vpip_pct = (hs.vpip_hands / max(1, hs.hands)) * 100.0
        prof_lines = []
        for i, (prf, st) in enumerate(zip(self.engine.cpu_learner.profiles, self.engine.cpu_learner.stats)):
            avg = (st.total_reward / st.count) if st.count else 0.0
            prof_lines.append(
                f"Profile {i+1}: aggr×{prf.aggression:.2f} rand+{prf.randomness:.2f}   avgΔ {avg:.1f} (n={st.count})"
            )
        self.stats_var.set(
            "Human:\n"
            f"  hands={hs.hands}  VPIP={vpip_pct:.0f}%  postflop(A/C)={hs.postflop_aggr}/{hs.postflop_calls}  folds_to_bet={hs.folds_to_bet}\n\n"
            "CPU bandit:\n  " + "\n  ".join(prof_lines)
        )

        # Buttons
        can_act = self.engine.waiting_for_human
        to_call = self.engine.prompt["to_call"] if self.engine.prompt else 0
        for b in (self.btn_fold, self.btn_check, self.btn_call, self.btn_bet, self.btn_raise, self.btn_allin):
            b.configure(state=("normal" if can_act else "disabled"))
        if can_act:
            if to_call == 0:
                self.btn_fold.configure(state="disabled")
                self.btn_call.configure(state="disabled")
                self.btn_raise.configure(state="disabled")
            else:
                self.btn_check.configure(state="disabled")
                self.btn_bet.configure(state="disabled")
        self.btn_next.configure(state=("normal" if not self.engine.hand_active else "disabled"))

        # Highlight *legal* actions in red (enabled buttons) to make options obvious
        self._highlight_legal_actions()

        # Auto-advance to the next hand when the current hand ends (keeps flow moving)
        if not self.engine.hand_active and getattr(self, "auto_advance_hand", True):
            if getattr(self, "_auto_next_after_id", None) is None:
                self._auto_next_after_id = self.after(1200, self._auto_next_hand_if_idle)
        else:
            # If a new hand is active, cancel any pending auto-next
            if getattr(self, "_auto_next_after_id", None) is not None:
                try:
                    self.after_cancel(self._auto_next_after_id)
                except Exception:
                    pass
                self._auto_next_after_id = None


    def _legal_actions_now(self) -> set[str]:
        """Best-effort legal-move detection based on prompt/to_call (kept engine-agnostic)."""
        if not self.engine.hand_active or not self.engine.prompt:
            return set()
        to_call = int(self.engine.prompt.get("to_call", 0))
        legal: set[str] = set()
        if to_call <= 0:
            # No bet to you: you can usually check or bet (and go all-in)
            legal.update({"check", "bet", "allin"})
        else:
            legal.update({"fold", "call", "raise", "allin"})
        return legal

    def _highlight_legal_actions(self) -> None:
        legal = self._legal_actions_now()
        btn_map = {
            "fold": self.btn_fold,
            "check": self.btn_check,
            "call": self.btn_call,
            "bet": self.btn_bet,
            "raise": self.btn_raise,
            "allin": self.btn_allin,
        }
        for act, btn in btn_map.items():
            # Default to neutral styling
            base_style = "Action.TButton"
            hot_style = "Hot.Action.TButton"
            if act in legal and str(btn.cget("state")) == "normal":
                btn.configure(style=hot_style)
            else:
                btn.configure(style=base_style)

    def _auto_next_hand_if_idle(self) -> None:
        # Clear the pending id first
        self._auto_next_after_id = None
        if not self.engine.hand_active:
            self._next_hand()

    # ---------------- Settings (kept compatible) ----------------
    def _open_settings(self) -> None:
        win = tk.Toplevel(self)
        win.title("Settings")
        win.resizable(False, False)
        frm = ttk.Frame(win, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        def row(r: int, label: str, default: str) -> tk.StringVar:
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=4)
            v = tk.StringVar(value=default)
            ttk.Entry(frm, textvariable=v, width=14).grid(row=r, column=1, sticky="w", padx=(10, 0))
            return v

        v_players = row(0, "Players (2-9)", str(self.settings.players))
        v_stack = row(1, "Starting stack", str(self.settings.start_stack))
        v_sb = row(2, "Small blind", str(self.settings.sb))
        v_bb = row(3, "Big blind", str(self.settings.bb))
        v_seed = row(4, "Seed (blank=none)", "" if self.settings.seed is None else str(self.settings.seed))
        v_aggr = row(5, "CPU aggression", f"{self.settings.cpu_aggression:.2f}")
        v_rand = row(6, "CPU randomness", f"{self.settings.cpu_randomness:.2f}")
        v_pre = row(7, "MC iters preflop", str(self.settings.mc_iters_preflop))
        v_post = row(8, "MC iters postflop", str(self.settings.mc_iters_postflop))

        err = tk.StringVar(value="")
        ttk.Label(frm, textvariable=err, foreground="#b00020").grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        def apply() -> None:
            try:
                players = int(v_players.get())
                start_stack = int(v_stack.get())
                sb = int(v_sb.get())
                bb = int(v_bb.get())
                seed_raw = v_seed.get().strip()
                seed = None if seed_raw == "" else int(seed_raw)
                cpu_aggr = float(v_aggr.get())
                cpu_rand = float(v_rand.get())
                mc_pre = int(v_pre.get())
                mc_post = int(v_post.get())
            except Exception:
                err.set("Invalid values.")
                return
            if not (2 <= players <= 9):
                err.set("Players must be 2-9.")
                return
            if not (20 <= start_stack <= 10000):
                err.set("Starting stack must be 20-10000.")
                return
            if not (0 < sb < bb):
                err.set("Require 0 < SB < BB.")
                return

            self.settings = GameSettings(
                players=players,
                start_stack=start_stack,
                sb=sb,
                bb=bb,
                seed=seed,
                cpu_aggression=cpu_aggr,
                cpu_randomness=cpu_rand,
                mc_iters_preflop=max(60, mc_pre),
                mc_iters_postflop=max(60, mc_post),
            )
            self.engine = PokerEngine(self.settings)
            self._refresh()
            win.destroy()

        btns = ttk.Frame(frm)
        btns.grid(row=10, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Cancel", command=win.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Apply (resets game)", command=apply).grid(row=0, column=1)


# ---------------- helpers for preflop trainer ----------------
SUIT_SYMBOL = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
RANK_VAL = {r: i for i, r in enumerate("23456789TJQKA", start=2)}


def _pretty_hand(r1: str, s1: str, r2: str, s2: str) -> str:
    return f"{r1}{SUIT_SYMBOL.get(s1, s1)}  {r2}{SUIT_SYMBOL.get(s2, s2)}"


def _trainer_advice(r1: str, r2: str, suited: bool, pos: str, level: str = "Beginner") -> tuple[str, str]:
    """Return (action, explanation) for a simplified unopened-pot spot."""
    # Normalize order
    if RANK_VAL[r2] > RANK_VAL[r1]:
        r1, r2 = r2, r1
    is_pair = (r1 == r2)

    level = (level or "Beginner").strip().title()
    if level not in ("Beginner", "Intermediate", "Advanced"):
        level = "Beginner"
    # Loosen ranges as level increases
    loosen = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}[level]

    # Very simplified ranges:
    # - Early (UTG): tighter
    # - Late (CO/BTN): wider
    tight = pos in ("UTG",)
    mid = pos in ("HJ", "SB")
    late = pos in ("CO", "BTN")

    # Premiums
    premiums = {("A", "A"), ("K", "K"), ("Q", "Q"), ("J", "J"), ("A", "K")}
    strong_broadways = {("A", "Q"), ("A", "J"), ("K", "Q"), ("K", "J"), ("Q", "J")}

    key = (r1, r2)

    if is_pair:
        pair_raise_cut = ["9", "8", "7"][min(loosen, 2)]
        pair_mid_raise_cut = ["6", "5", "4"][min(loosen, 2)]
        if RANK_VAL[r1] >= RANK_VAL[pair_raise_cut]:
            return (
                "Raise",
                "Big pairs and medium-high pairs play great heads-up. In an unopened pot, raising is the default to build value and take initiative.",
            )
        if late or (mid and RANK_VAL[r1] >= RANK_VAL[pair_mid_raise_cut]):
            return (
                "Raise",
                "Small pairs can be raised in later positions because you’ll steal blinds often and sometimes flop strong sets.",
            )
        return (
            "Fold",
            "From early position, tiny pairs are often dominated and you’ll be out of position. A simple default is to fold the smallest pairs UTG.",
        )

    # Suited big cards
    if suited and (key in premiums or key in strong_broadways or r1 in ("A", "K", "Q") and RANK_VAL[r2] >= RANK_VAL["T"]):
        return (
            "Raise",
            "Suited high cards make strong top pairs and can make nut flushes. Raising is the standard default in an unopened pot.",
        )

    # Offsuit big cards
    if (not suited) and (key in premiums or key in {("A", "Q"), ("A", "K"), ("K", "Q")}):
        return (
            "Raise",
            "Top broadways (like AK/AQ/KQ) are strong enough to raise even when offsuit. You often win by making top pair with good kicker.",
        )

    # Suited connectors / one-gappers
    connectors = {("9", "8"), ("T", "9"), ("J", "T"), ("Q", "J"), ("K", "Q"), ("8", "7")}
    if loosen >= 1:
        connectors |= {("7", "6"), ("9", "7"), ("T", "8")}
    if loosen >= 2:
        connectors |= {("6", "5"), ("8", "6"), ("J", "9")}
    if suited and key in connectors:
        if late:
            return (
                "Raise",
                "In late position, suited connectors are good steals and can flop strong draws. A raise is a solid default when folded to you.",
            )
        if mid:
            return (
                "Call",
                "From middle/out-of-position spots, suited connectors are playable but not mandatory. A simple default is call more and raise less.",
            )
        return (
            "Fold",
            "From early position, suited connectors can get you into tough spots out of position. Tight default: fold them UTG.",
        )

    # Axs suited (wheel-ish)
    if suited and r1 == "A" and RANK_VAL[r2] >= RANK_VAL["5"]:
        if late or mid:
            return (
                "Raise",
                "Suited A-x can make nut flushes and has blocker value. In late/mid positions, raising is a good default.",
            )
        if loosen >= 2:
            return (
                "Call",
                "Advanced default: some suited A-x can be mixed (call/raise) even UTG because it has nut-flush potential. Keep it simple: call with the better suited aces.",
            )
        return (
            "Fold",
            "Suited A-x is tempting, but from UTG it’s easy to get dominated when you make one pair. Tight default: fold UTG.",
        )

    # Otherwise
    late_suited_cut = ["T", "9", "8"][min(loosen, 2)]
    if late and suited and RANK_VAL[r1] >= RANK_VAL[late_suited_cut]:
        return (
            "Raise",
            "Late position gives you fold equity and position advantage. Suited hands with decent high cards can be raised as steals.",
        )
    return (
        "Fold",
        f"Default fundamentals ({level}): if it’s not a pair, strong Broadway, suited ace, or a good suited connector — fold. Tight is okay while learning.",
    )


def main() -> None:
    PokerGUI().mainloop()


if __name__ == "__main__":
    main()

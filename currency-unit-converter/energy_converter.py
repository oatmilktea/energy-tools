"""
energy_converter.py
===================

A desktop GUI application for converting energy units and currencies for
LNG (Liquefied Natural Gas) and natural gas.

Built with tkinter, which is part of Python's standard library, so the GUI
itself needs no extra installation. The only third-party library used is
`requests`, which we use to fetch live foreign-exchange (FX) rates.

The app has two screens ("stages"):
  Stage 1 -- pick a product (LNG or Gas)
  Stage 2 -- choose units, type an amount, and convert

This file is organised top-to-bottom as:
  1. Imports
  2. Configuration / constant data (units, conversion factors, etc.)
  3. The FX (currency) rate fetching helper
  4. The main application class (the tkinter window and all its widgets)
  5. The program entry point

Comments are deliberately verbose because this project is a learning exercise.
"""

# ---------------------------------------------------------------------------
# 1. IMPORTS
# ---------------------------------------------------------------------------

import tkinter as tk                 # The core tkinter GUI toolkit
from tkinter import ttk              # "Themed" tkinter widgets (nicer looking)
from datetime import datetime        # Used to timestamp when FX rates were fetched

# `requests` is a popular library for making web requests (HTTP). We use it to
# call the Frankfurter currency API. It is the only thing in requirements.txt.
# We import it inside a try/except so that, if it is somehow missing, the app
# can still start and simply fall back to offline currency rates.
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ---------------------------------------------------------------------------
# 2. CONFIGURATION / CONSTANT DATA
# ---------------------------------------------------------------------------

# ---- LNG physical properties (used to derive the "m3 LNG" volume unit) -------
# Liquid LNG is far denser and more energy-rich than pipeline gas, so a cubic
# metre of LNG is a completely different quantity from a cubic metre of gas.
# These are typical reference values; real cargoes vary, so for production use a
# cargo-specific density and calorific value.
LNG_DENSITY_KG_PER_M3 = 450.0      # typical liquid LNG density (kg per m3)
LNG_GROSS_CV_MJ_PER_KG = 55.0      # typical gross calorific value (MJ per kg)
# Energy in one cubic metre of liquid LNG:
#   450 kg/m3 x 55 MJ/kg = 24,750 MJ/m3 = 24.75 GJ/m3 (~= 6.875 MWh/m3).
LNG_MJ_PER_M3 = LNG_DENSITY_KG_PER_M3 * LNG_GROSS_CV_MJ_PER_KG   # 24,750 MJ/m3
# Because 1 MWh = 3,600 MJ, the number of m3 of LNG in 1 MWh is 3,600 / 24,750.
LNG_M3_PER_MWH = 3_600.0 / LNG_MJ_PER_M3                          # ~0.145455

# ---- Units, grouped into categories ------------------------------------------
# Units are organised into categories so the dropdowns can group them for easier
# selection. Order here is the order shown on screen. Each category also implies
# a product scope (see CATEGORY_SCOPE below): some units only apply to Gas, some
# only to LNG, and the rest apply to both.
UNIT_CATEGORIES = [
    ("Energy", ["KWh", "MWh", "GWh", "TWh", "KJ", "GJ", "kcal", "Gcal",
                "MMBtu", "th"]),
    ("Gas volume", ["m3", "thou.m3", "mcm", "bcm",
                    "ft3", "thou.ft3", "m ft3", "bcf"]),
    ("LNG", ["tonnes", "m3 LNG", "mtce"]),
    ("Currency", ["EUR", "USD", "GBP"]),
]

# Which product each category applies to ("both" = always shown).
CATEGORY_SCOPE = {
    "Energy": "both",
    "Gas volume": "Gas",   # cubic-feet / cubic-metre gas volumes -> Gas only
    "LNG": "LNG",          # tonnes / m3 of liquid LNG / mtce       -> LNG only
    "Currency": "both",
}

# Derived lookups built from the categories above (so we only edit one place).
UNITS = [u for _category, units in UNIT_CATEGORIES for u in units]
UNIT_CATEGORY = {u: cat for cat, units in UNIT_CATEGORIES for u in units}
UNIT_SCOPE = {u: CATEGORY_SCOPE[UNIT_CATEGORY[u]] for u in UNITS}

# Which units are currencies (handled via live FX, not the factor table below).
CURRENCIES = {"EUR", "USD", "GBP"}

# Energy conversion factors, expressed on a "per 1 MWh" basis: each value is HOW
# MANY of that unit equal exactly 1 MWh. (MWh is our base unit, so it is 1.)
#
# To convert an amount between two energy units we do:
#     result = amount * (factor[to_unit] / factor[from_unit])
#
# Example: 1 MWh = 3.41199886 MMBtu, and 1 MWh = 1 MWh, so
#     500 MMBtu -> MWh  =  500 * (1 / 3.41199886)  =  146.54 MWh
ENERGY_FACTORS = {
    # --- Energy (apply to both products) ---
    "KWh": 1_000.0,         # 1 MWh = 1,000 KWh
    "MWh": 1.0,             # base unit, by definition
    "GWh": 0.001,           # 1 MWh = 0.001 GWh
    "TWh": 0.000_001,       # 1 MWh = 0.000001 TWh
    "KJ": 3_600_000.0,      # 1 MWh = 3,600,000 kJ
    "GJ": 3.6,              # 1 MWh = 3.6 GJ
    "kcal": 859_845.0,      # 1 MWh = 859,845 kcal
    "Gcal": 0.859_845,      # 1 MWh = 0.859845 Gcal
    "MMBtu": 3.41199886,    # 1 MWh = 3.41199886 MMBtu
    "th": 34.1199886,       # 1 MWh = 34.1199886 therms
    # --- Gas volumes (Gas product only) ---
    "m3": 91.1602,          # 1 MWh = 91.1602 m3 of natural gas
    "thou.m3": 0.0911602,   # 1 MWh = 0.0911602 thousand m3
    "mcm": 9.11602e-05,     # 1 MWh = 9.11602e-5 million m3
    "bcm": 9.11602e-08,     # 1 MWh = 9.11602e-8 billion m3
    "ft3": 3218.87,         # 1 MWh = 3,218.87 cubic feet
    "thou.ft3": 3.2187,     # 1 MWh = 3.2187 thousand ft3
    "m ft3": 0.00321887,    # 1 MWh = 0.00321887 million ft3 (MMcf)
    "bcf": 3.21887e-06,     # 1 MWh = 3.21887e-6 billion ft3
    # --- LNG (LNG product only) ---
    "tonnes": 0.06617963,   # 1 MWh = 0.06617963 tonnes (~15.1 MWh per tonne LNG)
    "m3 LNG": LNG_M3_PER_MWH,  # derived above from LNG density x calorific value
    "mtce": 6.617963e-08,   # 1 MWh = 6.617963e-8 million tonnes (LNG) equivalent
}

# Options offered by the optional "Per time period" quotient selector.
# When this feature is switched on, a value is treated as a RATE (an amount per
# unit of time), so converting between two different time periods now actually
# rescales the number -- e.g. 500 MMBtu/day becomes 182,500 MMBtu/year.
TIME_PERIODS = ["per second", "per day", "per month", "per year"]

# Maps the dropdown text ("per day") to the short label suffix ("/day") used
# in the result line.
TIME_SUFFIX = {
    "per second": "/s",
    "per day": "/day",
    "per month": "/month",
    "per year": "/year",
}

# How many seconds each time period contains. These let us rescale a rate when
# the "From" and "To" periods differ. To convert a rate from one period to
# another we multiply by (seconds in the TO period / seconds in the FROM period):
#   500 /day -> /year  =  500 * (31,536,000 / 86,400)  =  500 * 365  =  182,500
#
# We treat a year as 365 days and a month as exactly one twelfth of that year,
# so 12 months always equals 1 year. These are approximations (real months and
# leap years vary), which is fine for indicative energy-rate conversions.
SECONDS_PER_PERIOD = {
    "per second": 1,
    "per day": 86_400,           # 24 * 60 * 60
    "per month": 31_536_000 / 12,  # one twelfth of a 365-day year = 2,628,000 s
    "per year": 31_536_000,      # 365 * 86,400
}

# Hardcoded fallback FX rates, used ONLY if the live API call fails.
# These are expressed as "how many of this currency per 1 USD", matching the
# format the Frankfurter API returns when queried with from=USD.
# (USD is always 1.0 because it is the base.)
FALLBACK_RATES = {
    "USD": 1.0,
    "EUR": 0.92,   # ~0.92 EUR per 1 USD
    "GBP": 0.79,   # ~0.79 GBP per 1 USD
}

# Colours for our dark theme, kept in one place so they are easy to tweak.
COLOR_BG = "#1e1e2e"          # window background (dark)
COLOR_PANEL = "#28283c"       # slightly lighter panel background
COLOR_TEXT = "#e0e0e0"        # main text (light grey)
COLOR_MUTED = "#9a9ab0"       # secondary / muted text
COLOR_ACCENT = "#4f9cf9"      # accent blue (buttons, highlights)
COLOR_ACCENT_DARK = "#3a7bd5" # darker accent for button hover/active
COLOR_RESULT = "#7ee787"      # green for the final result text
COLOR_ERROR = "#f97583"       # red for error messages
COLOR_WARN_BG = "#5c3a1e"     # amber-ish background for the offline warning


# ---------------------------------------------------------------------------
# 3. FX RATE FETCHING HELPER
# ---------------------------------------------------------------------------

def fetch_fx_rates():
    """Fetch live currency rates once, at app launch.

    Returns a tuple of three things:
        rates      -- a dict like {"USD": 1.0, "EUR": 0.92, "GBP": 0.79}
        is_live    -- True if we got live data, False if we fell back to offline
        timestamp  -- a human-readable string describing the source and time

    We query the Frankfurter API with USD as the base currency:
        https://api.frankfurter.app/latest?from=USD
    which returns USD-relative rates for EUR, GBP, and others.

    If anything goes wrong (no internet, library missing, bad response) we
    quietly fall back to the hardcoded FALLBACK_RATES so the app still works.
    """
    # If the requests library could not be imported, go straight to offline.
    if not REQUESTS_AVAILABLE:
        return dict(FALLBACK_RATES), False, "Offline rates (requests library not installed)"

    try:
        # Call the API. timeout stops the app hanging forever if the network
        # is slow or unreachable.
        response = requests.get(
            "https://api.frankfurter.app/latest?from=USD", timeout=6
        )
        response.raise_for_status()   # raises an error for HTTP 4xx/5xx responses
        data = response.json()        # parse the JSON body into a Python dict

        # The API gives rates relative to USD but does NOT include USD itself,
        # so we start our dict with USD = 1.0 and add the others on top.
        rates = {"USD": 1.0}
        for currency in ("EUR", "GBP"):
            # Only keep the currencies our app actually offers.
            if currency in data.get("rates", {}):
                rates[currency] = data["rates"][currency]

        # Make sure we actually got the currencies we need; if not, fall back.
        if "EUR" not in rates or "GBP" not in rates:
            raise ValueError("API response missing expected currencies")

        # Build a friendly timestamp: the API's data date plus the time we fetched.
        api_date = data.get("date", "unknown date")
        fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        timestamp = f"Live FX via Frankfurter (data {api_date}, fetched {fetched_at})"
        return rates, True, timestamp

    except Exception:
        # ANY failure -> use offline fallback rates.
        return dict(FALLBACK_RATES), False, "Offline rates -- live FX unavailable"


# ---------------------------------------------------------------------------
# 4. THE MAIN APPLICATION
# ---------------------------------------------------------------------------

class EnergyConverterApp(tk.Tk):
    """The whole application lives in this class.

    It subclasses tk.Tk, so an instance *is* the main window. We build both
    screens (stages) up front and simply show/hide them as the user navigates.
    """

    def __init__(self):
        super().__init__()

        # --- Window basics ---------------------------------------------------
        self.title("Energy Unit & Currency Converter")
        self.geometry("560x620")
        self.minsize(520, 560)
        self.configure(bg=COLOR_BG)

        # --- Fetch FX rates ONCE and cache them for the whole session --------
        # We store them on the instance (self....) so every conversion reuses
        # them instead of hitting the API again.
        self.fx_rates, self.fx_is_live, self.fx_timestamp = fetch_fx_rates()

        # --- State that changes as the user interacts ------------------------
        self.product = None  # "LNG" or "Gas", chosen on Stage 1

        # A WORKING copy of the energy conversion factors. We start from the
        # built-in defaults (ENERGY_FACTORS) but the user can inspect and edit
        # these via the "Edit conversion values" screen. All conversions use
        # this copy, so any edits immediately affect the maths. Currencies are
        # NOT included here because their rates come from live FX, not the user.
        self.energy_factors = dict(ENERGY_FACTORS)

        # --- Apply the dark theme styling to ttk widgets ---------------------
        self._setup_styles()

        # --- Offline warning banner (only shown if FX is NOT live) -----------
        # We build it now but only pack (show) it when needed.
        self.warning_banner = tk.Label(
            self,
            text="⚠  Using offline rates — live FX unavailable",
            bg=COLOR_WARN_BG, fg="#ffd9a0",
            font=("Helvetica", 11, "bold"), pady=6,
        )
        if not self.fx_is_live:
            self.warning_banner.pack(fill="x", side="top")

        # --- Container that holds whichever stage is currently visible -------
        self.container = tk.Frame(self, bg=COLOR_BG)
        self.container.pack(fill="both", expand=True)

        # --- Footer: shows the FX rate source and timestamp ------------------
        self.footer = tk.Label(
            self, text=self.fx_timestamp,
            bg=COLOR_BG, fg=COLOR_MUTED, font=("Helvetica", 9), pady=4,
        )
        self.footer.pack(side="bottom", fill="x")

        # --- Build the two stages and show Stage 1 first ---------------------
        self.show_stage1()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _setup_styles(self):
        """Configure ttk styles so widgets match our dark theme.

        On macOS/Windows the default ttk theme ignores many colours, so we
        switch to the 'clam' theme which respects them, then customise it.
        """
        style = ttk.Style(self)
        style.theme_use("clam")

        # Generic frame / label backgrounds
        style.configure("Dark.TFrame", background=COLOR_BG)
        style.configure("Panel.TFrame", background=COLOR_PANEL)
        style.configure("Dark.TLabel", background=COLOR_BG, foreground=COLOR_TEXT,
                        font=("Helvetica", 11))
        style.configure("Muted.TLabel", background=COLOR_BG, foreground=COLOR_MUTED,
                        font=("Helvetica", 10))
        style.configure("Title.TLabel", background=COLOR_BG, foreground=COLOR_TEXT,
                        font=("Helvetica", 18, "bold"))
        style.configure("Rate.TLabel", background=COLOR_BG, foreground=COLOR_ACCENT,
                        font=("Helvetica", 11, "italic"))
        style.configure("Result.TLabel", background=COLOR_BG, foreground=COLOR_RESULT,
                        font=("Helvetica", 15, "bold"))
        style.configure("Error.TLabel", background=COLOR_BG, foreground=COLOR_ERROR,
                        font=("Helvetica", 11))

        # Standard buttons
        style.configure("Accent.TButton", font=("Helvetica", 12, "bold"),
                        foreground="white", background=COLOR_ACCENT,
                        borderwidth=0, padding=10)
        style.map("Accent.TButton",
                  background=[("active", COLOR_ACCENT_DARK), ("disabled", "#3a3a4a")],
                  foreground=[("disabled", "#7a7a8a")])

        # The large product-selection buttons on Stage 1
        style.configure("Big.TButton", font=("Helvetica", 20, "bold"),
                        foreground="white", background=COLOR_ACCENT,
                        borderwidth=0, padding=30)
        style.map("Big.TButton", background=[("active", COLOR_ACCENT_DARK)])

        # The small "Back" button
        style.configure("Back.TButton", font=("Helvetica", 10),
                        foreground=COLOR_TEXT, background=COLOR_PANEL,
                        borderwidth=0, padding=6)
        style.map("Back.TButton", background=[("active", "#3a3a52")])

        # Dropdown (combobox) styling
        style.configure("TCombobox", fieldbackground=COLOR_PANEL,
                        background=COLOR_PANEL, foreground=COLOR_TEXT,
                        arrowcolor=COLOR_TEXT, borderwidth=0, padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", COLOR_PANEL)],
                  foreground=[("readonly", COLOR_TEXT)])

        # Checkbutton styling
        style.configure("Dark.TCheckbutton", background=COLOR_BG,
                        foreground=COLOR_TEXT, font=("Helvetica", 11))
        style.map("Dark.TCheckbutton", background=[("active", COLOR_BG)],
                  foreground=[("active", COLOR_TEXT)])

    # ------------------------------------------------------------------
    # Helper to clear the container before showing a new stage
    # ------------------------------------------------------------------
    def _clear_container(self):
        """Remove all widgets currently inside the container frame."""
        for child in self.container.winfo_children():
            child.destroy()

    # ==================================================================
    # STAGE 1 -- PRODUCT SELECTION
    # ==================================================================
    def show_stage1(self):
        """Build and display the product selection screen."""
        self._clear_container()

        # A title prompting the user to choose.
        ttk.Label(self.container, text="Select a product",
                  style="Title.TLabel").pack(pady=(60, 10))
        ttk.Label(self.container, text="Choose which energy product you want to convert",
                  style="Muted.TLabel").pack(pady=(0, 40))

        # A frame to hold the two big buttons side by side.
        button_row = ttk.Frame(self.container, style="Dark.TFrame")
        button_row.pack()

        # The two large product buttons. Clicking either records the choice
        # and moves to Stage 2.
        ttk.Button(button_row, text="LNG", style="Big.TButton",
                   command=lambda: self.choose_product("LNG")).grid(
                       row=0, column=0, padx=20)
        ttk.Button(button_row, text="Gas", style="Big.TButton",
                   command=lambda: self.choose_product("Gas")).grid(
                       row=0, column=1, padx=20)

    def choose_product(self, product):
        """Record the chosen product and advance to the conversion screen."""
        self.product = product
        self.show_stage2()

    def _grouped_units_for_product(self):
        """Build the dropdown entries for the current product, grouped by category.

        Returns a list of strings suitable for a Combobox. Category names are
        inserted as non-selectable header rows (e.g. "—— Energy ——") so the user
        can see the grouping; _reject_header() below ignores them if clicked.
        Units tagged Gas-only or LNG-only are hidden unless they match the
        chosen product.
        """
        values = []
        self._header_values = set()  # remembered so we can reject header clicks
        for category, units in UNIT_CATEGORIES:
            # Keep only the units in this category that suit the current product.
            visible = [u for u in units
                       if CATEGORY_SCOPE[category] in ("both", self.product)]
            if not visible:
                continue
            header = f"—— {category} ——"
            self._header_values.add(header)
            values.append(header)
            values.extend(visible)
        return values

    # ==================================================================
    # STAGE 2 -- CONVERSION SCREEN
    # ==================================================================
    def show_stage2(self):
        """Build and display the main conversion screen."""
        self._clear_container()

        # --- Top bar with a Back button and the current product name --------
        top_bar = ttk.Frame(self.container, style="Dark.TFrame")
        top_bar.pack(fill="x", pady=(10, 0), padx=10)
        ttk.Button(top_bar, text="← Back", style="Back.TButton",
                   command=self.show_stage1).pack(side="left")
        # Opens a window where the user can inspect and edit the energy
        # conversion factors (currencies are excluded -- they use live FX).
        ttk.Button(top_bar, text="⚙ Edit conversion values", style="Back.TButton",
                   command=self.show_factor_editor).pack(side="left", padx=(10, 0))
        ttk.Label(top_bar, text=f"Product: {self.product}",
                  style="Muted.TLabel").pack(side="right")

        # --- tkinter "variables" -------------------------------------------
        # These special objects let us read the current value of a widget AND
        # get notified whenever it changes (via .trace_add below). That is how
        # we update the live rate line and enable/disable the Convert button.
        self.from_unit = tk.StringVar()
        self.to_unit = tk.StringVar()
        self.amount_var = tk.StringVar()
        self.use_quotient = tk.BooleanVar(value=False)
        self.from_period = tk.StringVar(value=TIME_PERIODS[1])  # default "per day"
        self.to_period = tk.StringVar(value=TIME_PERIODS[1])

        # --- The From / To dropdown row -------------------------------------
        ttk.Label(self.container, text="Convert between units",
                  style="Title.TLabel").pack(pady=(20, 15))

        dropdown_row = ttk.Frame(self.container, style="Dark.TFrame")
        dropdown_row.pack()

        # The units available depend on the chosen product (e.g. gas volumes are
        # Gas-only, tonnes/LNG units are LNG-only). Build the grouped, category-
        # labelled list once and use it for both dropdowns.
        units = self._grouped_units_for_product()

        # "From" side (left)
        from_col = ttk.Frame(dropdown_row, style="Dark.TFrame")
        from_col.grid(row=0, column=0, padx=15)
        ttk.Label(from_col, text="From", style="Dark.TLabel").pack(anchor="w")
        self.from_combo = ttk.Combobox(
            from_col, textvariable=self.from_unit, values=units,
            state="readonly", width=14,
        )
        self.from_combo.pack()
        # The per-time-period dropdown for the From side. Built now but hidden
        # until the "Per time period" checkbox is ticked.
        self.from_period_combo = ttk.Combobox(
            from_col, textvariable=self.from_period, values=TIME_PERIODS,
            state="readonly", width=12,
        )

        # A small arrow between the two dropdowns for visual clarity.
        ttk.Label(dropdown_row, text="→", style="Title.TLabel").grid(
            row=0, column=1, padx=5)

        # "To" side (right)
        to_col = ttk.Frame(dropdown_row, style="Dark.TFrame")
        to_col.grid(row=0, column=2, padx=15)
        ttk.Label(to_col, text="To", style="Dark.TLabel").pack(anchor="w")
        self.to_combo = ttk.Combobox(
            to_col, textvariable=self.to_unit, values=units,
            state="readonly", width=14,
        )
        self.to_combo.pack()
        self.to_period_combo = ttk.Combobox(
            to_col, textvariable=self.to_period, values=TIME_PERIODS,
            state="readonly", width=12,
        )

        # --- The "Per time period" checkbox ---------------------------------
        ttk.Checkbutton(
            self.container, text="Per time period", variable=self.use_quotient,
            style="Dark.TCheckbutton", command=self._toggle_quotient,
        ).pack(pady=(15, 5))

        # --- Live conversion-rate indicator line ----------------------------
        # Shows e.g. "1 MWh = 3.412 MMBtu". Updated by _update_rate_line().
        self.rate_label = ttk.Label(self.container, text="", style="Rate.TLabel")
        self.rate_label.pack(pady=(5, 15))

        # --- Amount input ---------------------------------------------------
        ttk.Label(self.container, text="Enter amount to convert",
                  style="Dark.TLabel").pack()
        # The entry and the From-unit indicator sit side by side in a small row.
        amount_row = ttk.Frame(self.container, style="Dark.TFrame")
        amount_row.pack(pady=(5, 20))
        self.amount_entry = ttk.Entry(
            amount_row, textvariable=self.amount_var,
            font=("Helvetica", 13), justify="center", width=18,
        )
        self.amount_entry.pack(side="left")
        # Indicator showing the chosen From unit right next to the input box.
        # It stays blank until a From unit is selected, then shows e.g. "MMBtu".
        self.amount_unit_label = ttk.Label(amount_row, text="", style="Rate.TLabel")
        self.amount_unit_label.pack(side="left", padx=(8, 0))

        # --- Convert button (starts disabled) -------------------------------
        self.convert_button = ttk.Button(
            self.container, text="Convert", style="Accent.TButton",
            command=self.do_conversion, state="disabled",
        )
        self.convert_button.pack(pady=(0, 15))

        # --- Result / error message line ------------------------------------
        self.result_label = ttk.Label(self.container, text="", style="Result.TLabel",
                                       wraplength=480, justify="center")
        self.result_label.pack(pady=(5, 10))

        # --- Wire up "react when something changes" callbacks ---------------
        # Whenever the From unit, To unit, or amount changes, we re-check
        # whether the Convert button should be enabled and refresh the rate
        # line. trace_add("write", ...) calls our function on every change.
        self.from_unit.trace_add("write", self._on_change)
        self.to_unit.trace_add("write", self._on_change)
        self.amount_var.trace_add("write", self._on_change)
        # The time-period choices now affect the maths, so refresh when they
        # change too (only has a visible effect while the checkbox is ticked).
        self.from_period.trace_add("write", self._on_change)
        self.to_period.trace_add("write", self._on_change)

        # Initialise the rate line and button state for the empty form.
        self._on_change()

    # ------------------------------------------------------------------
    # Show/hide the per-period dropdowns when the checkbox is toggled
    # ------------------------------------------------------------------
    def _toggle_quotient(self):
        """Show or hide the two time-period dropdowns based on the checkbox."""
        if self.use_quotient.get():
            # Reveal the period dropdowns beneath each unit dropdown.
            self.from_period_combo.pack(pady=(6, 0))
            self.to_period_combo.pack(pady=(6, 0))
        else:
            # Hide them again.
            self.from_period_combo.pack_forget()
            self.to_period_combo.pack_forget()
        # The rate line text doesn't depend on the period, but refresh anyway.
        self._update_rate_line()

    # ------------------------------------------------------------------
    # Called whenever From / To / amount changes
    # ------------------------------------------------------------------
    def _on_change(self, *args):
        """Refresh the rate line and enable/disable the Convert button.

        The *args are ignored -- trace_add passes internal variable names that
        we don't need, but the function must accept them.
        """
        # Category headers (e.g. "—— Energy ——") are shown in the dropdowns for
        # grouping but are not real units. If one gets selected, clear it. The
        # .set("") re-triggers this callback, which then continues normally.
        headers = getattr(self, "_header_values", set())
        for var in (self.from_unit, self.to_unit):
            if var.get() in headers:
                var.set("")
                return

        self._update_rate_line()

        # Update the From-unit indicator shown next to the amount input.
        # It mirrors the currently selected From unit (blank if none chosen).
        from_u = self.from_unit.get()
        self.amount_unit_label.config(text=from_u if from_u in UNITS else "")

        # The Convert button is enabled ONLY when all three are present:
        #   a From unit, a To unit, and a numeric amount.
        from_ok = self.from_unit.get() in UNITS
        to_ok = self.to_unit.get() in UNITS
        amount_ok = self._parse_amount() is not None

        if from_ok and to_ok and amount_ok:
            self.convert_button.config(state="normal")
        else:
            self.convert_button.config(state="disabled")

    def _parse_amount(self):
        """Try to read the amount field as a number.

        Returns the float value, or None if the field is empty or not a number.
        """
        text = self.amount_var.get().strip()
        if text == "":
            return None
        try:
            return float(text)
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # The live "1 X = Y Z" indicator line
    # ------------------------------------------------------------------
    def _update_rate_line(self):
        """Update the small indicator showing the current conversion rate."""
        from_u = self.from_unit.get()
        to_u = self.to_unit.get()

        # Only show a rate once BOTH units are selected.
        if from_u not in UNITS or to_u not in UNITS:
            self.rate_label.config(text="", style="Rate.TLabel")
            return

        from_is_currency = from_u in CURRENCIES
        to_is_currency = to_u in CURRENCIES

        # If one side is a currency and the other is not, that's invalid.
        if from_is_currency != to_is_currency:
            self.rate_label.config(
                text="Currencies can only convert to currencies",
                style="Error.TLabel",
            )
            return

        # Work out how many "to" units equal 1 "from" unit, including any
        # time-period rescaling that is active.
        rate = self._unit_rate(from_u, to_u) * self._time_scale()
        # When the quotient is on, show the time suffixes too so the rate line
        # matches the result, e.g. "1 MWh/day = 365 MWh/year".
        if self.use_quotient.get():
            from_suffix = TIME_SUFFIX.get(self.from_period.get(), "")
            to_suffix = TIME_SUFFIX.get(self.to_period.get(), "")
        else:
            from_suffix = to_suffix = ""
        # Format the number nicely (trim trailing zeros, sensible precision).
        self.rate_label.config(
            text=f"1 {from_u}{from_suffix} = {self._fmt(rate)} {to_u}{to_suffix}",
            style="Rate.TLabel",
        )

    def _unit_rate(self, from_u, to_u):
        """Return how many `to_u` units equal exactly 1 `from_u` unit.

        Handles both energy-to-energy and currency-to-currency conversions.
        Assumes the caller has already checked the two units are compatible.
        This does NOT include any time-period scaling -- see _time_scale().
        """
        if from_u in CURRENCIES:
            # Currency: rates are "units per USD". So 1 A in B is:
            #   rate[B] / rate[A]
            return self.fx_rates[to_u] / self.fx_rates[from_u]
        else:
            # Energy: factors are "units per MWh". So 1 from-unit in to-units is:
            #   factor[to] / factor[from]
            # We read from self.energy_factors (the editable working copy).
            return self.energy_factors[to_u] / self.energy_factors[from_u]

    def _time_scale(self):
        """Return the factor by which the time period rescales a rate.

        When the "Per time period" checkbox is off, this is 1 (no effect).
        When on, converting a rate from the From period to the To period
        multiplies by (seconds in To period / seconds in From period). For
        example /day -> /year gives 31,536,000 / 86,400 = 365.
        """
        if not self.use_quotient.get():
            return 1.0
        return (SECONDS_PER_PERIOD[self.to_period.get()]
                / SECONDS_PER_PERIOD[self.from_period.get()])

    # ------------------------------------------------------------------
    # The Convert button action
    # ------------------------------------------------------------------
    def do_conversion(self):
        """Perform the conversion and display the result (or an error)."""
        from_u = self.from_unit.get()
        to_u = self.to_unit.get()
        amount = self._parse_amount()

        # Safety check: should never happen because the button is disabled
        # until everything is valid, but we guard anyway.
        if from_u not in UNITS or to_u not in UNITS or amount is None:
            return

        from_is_currency = from_u in CURRENCIES
        to_is_currency = to_u in CURRENCIES

        # RULE: currency may only convert to/from another currency.
        if from_is_currency != to_is_currency:
            self.result_label.config(
                text=("Currency conversion is only available between "
                      "currencies — please select a currency on both sides"),
                style="Error.TLabel",
            )
            return

        # Do the actual maths:
        #   amount * (rate of 1 from-unit in to-units) * any time rescaling.
        result = amount * self._unit_rate(from_u, to_u) * self._time_scale()

        # Build the time-period suffixes. If the checkbox is off, both suffixes
        # are empty strings and no time scaling was applied above.
        from_suffix = ""
        to_suffix = ""
        if self.use_quotient.get():
            from_suffix = TIME_SUFFIX.get(self.from_period.get(), "")
            to_suffix = TIME_SUFFIX.get(self.to_period.get(), "")

        # Display the result in the required format:
        #   [input] [from unit] = [result] [to unit]
        # e.g. "500 MMBtu/day = 182,500 MMBtu/year"
        self.result_label.config(
            text=f"{self._fmt(amount)} {from_u}{from_suffix} = "
                 f"{self._fmt(result)} {to_u}{to_suffix}",
            style="Result.TLabel",
        )

    # ==================================================================
    # CONVERSION-VALUE EDITOR (a pop-up window)
    # ==================================================================
    def show_factor_editor(self):
        """Open a window to inspect and edit the energy conversion factors.

        The user can change how many MWh each unit equals, then Save (which
        feeds straight back into every future conversion) or Revert to the
        built-in defaults. Currencies are deliberately excluded because their
        rates come from live FX, not from the user.
        """
        # Toplevel is a second, independent window owned by the main one.
        editor = tk.Toplevel(self)
        editor.title("Edit conversion values")
        editor.configure(bg=COLOR_BG)
        editor.resizable(False, False)
        # transient + grab_set make this behave like a focused dialog.
        editor.transient(self)
        editor.grab_set()

        # --- Heading and explanation ----------------------------------------
        ttk.Label(editor, text="Energy conversion values",
                  style="Title.TLabel").pack(pady=(15, 4), padx=20)
        ttk.Label(editor,
                  text="Each value is how many of that unit equal 1 MWh.\n"
                       "Edits apply to all conversions once you click Save.",
                  style="Muted.TLabel", justify="center").pack(pady=(0, 12), padx=20)

        # --- One editable row per energy unit -------------------------------
        rows = ttk.Frame(editor, style="Dark.TFrame")
        rows.pack(padx=20)

        # We keep each unit's Entry widget in this dict so Save/Revert can read
        # and refill them later. We only show units relevant to the current
        # product (e.g. m3 is hidden for LNG, tonnes is hidden for Gas).
        entry_for = {}
        editable_units = [u for u in self.energy_factors
                          if UNIT_SCOPE.get(u, "both") in ("both", self.product)]
        for i, unit in enumerate(editable_units):
            # Left: the unit name.
            ttk.Label(rows, text=unit, style="Dark.TLabel").grid(
                row=i, column=0, sticky="w", pady=4, padx=(0, 12))
            # Middle: an editable box pre-filled with the current factor.
            # ".10g" keeps the user's precision but trims noise (e.g. shows
            # "3.41199886" and "9.11602e-08" rather than long repr() tails).
            entry = ttk.Entry(rows, font=("Helvetica", 12), width=16, justify="right")
            entry.insert(0, f"{self.energy_factors[unit]:.10g}")
            entry.grid(row=i, column=1, pady=4)
            # Right: a small "per MWh" reminder of what the value means.
            ttk.Label(rows, text="per MWh", style="Muted.TLabel").grid(
                row=i, column=2, sticky="w", pady=4, padx=(8, 0))
            entry_for[unit] = entry

        # --- Status line for feedback (errors / confirmation) ---------------
        status = ttk.Label(editor, text="", style="Muted.TLabel")
        status.pack(pady=(10, 0), padx=20)

        # --- The Save / Revert / Close actions ------------------------------
        def save():
            """Validate every shown entry, then commit the values into the app."""
            # Start from the current values so units NOT shown in this editor
            # (e.g. m3 while editing LNG) are preserved rather than dropped.
            new_values = dict(self.energy_factors)
            for unit, entry in entry_for.items():
                text = entry.get().strip()
                try:
                    value = float(text)
                except ValueError:
                    status.config(text=f"'{unit}' is not a valid number.",
                                  style="Error.TLabel")
                    return
                if value <= 0:
                    status.config(text=f"'{unit}' must be greater than zero.",
                                  style="Error.TLabel")
                    return
                new_values[unit] = value
            # All good -- commit the new factors and refresh the live rate line.
            self.energy_factors = new_values
            self._update_rate_line()
            status.config(text="Saved. Conversions now use these values.",
                          style="Result.TLabel")

        def revert():
            """Restore the built-in defaults and refill the entry boxes."""
            self.energy_factors = dict(ENERGY_FACTORS)
            for unit, entry in entry_for.items():
                entry.delete(0, tk.END)
                entry.insert(0, f"{self.energy_factors[unit]:.10g}")
            self._update_rate_line()
            status.config(text="Reverted to default values.",
                          style="Muted.TLabel")

        button_row = ttk.Frame(editor, style="Dark.TFrame")
        button_row.pack(pady=15)
        ttk.Button(button_row, text="Save", style="Accent.TButton",
                   command=save).grid(row=0, column=0, padx=6)
        ttk.Button(button_row, text="Revert to default", style="Back.TButton",
                   command=revert).grid(row=0, column=1, padx=6)
        ttk.Button(button_row, text="Close", style="Back.TButton",
                   command=editor.destroy).grid(row=0, column=2, padx=6)

    # ------------------------------------------------------------------
    # Number formatting helper
    # ------------------------------------------------------------------
    @staticmethod
    def _fmt(number):
        """Format a number for display: readable precision, no ugly trailing zeros.

        - Very small or very large magnitudes use scientific notation, so tiny
          factors like 9.11602e-08 (m3 in a bcm) stay legible.
        - Large numbers (>= 1000) get thousands separators and up to 2 decimals.
        - Mid-range numbers keep up to 4 decimals.
        - Small numbers keep up to 8 decimals.
        In every case trailing zeros (and a dangling decimal point) are removed,
        so 146.5350 shows as 146.535 and 10,556,000.00 shows as 10,556,000.
        """
        if number == 0:
            return "0"

        magnitude = abs(number)
        # Outside this comfortable range, plain decimals are unreadable (either
        # a long row of leading zeros or a huge integer), so use scientific form.
        if magnitude < 1e-4 or magnitude >= 1e12:
            return f"{number:.6g}"       # e.g. 9.11602e-08 or 1.23457e+12

        if magnitude >= 1000:
            text = f"{number:,.2f}"      # e.g. 10,556,000.00
        elif magnitude >= 1:
            text = f"{number:.4f}"       # e.g. 146.5350
        else:
            text = f"{number:.8f}"       # e.g. 0.00321887

        # Trim trailing zeros after the decimal point, then a leftover ".".
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text


# ---------------------------------------------------------------------------
# 5. PROGRAM ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Create the application window and start tkinter's event loop. The
    # mainloop() call runs until the user closes the window.
    app = EnergyConverterApp()
    app.mainloop()

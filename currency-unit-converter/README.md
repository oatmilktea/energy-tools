# Energy Unit & Currency Converter

A small desktop GUI application for converting **energy units and currencies**
for LNG (Liquefied Natural Gas) and natural gas. Built in Python with
[tkinter](https://docs.python.org/3/library/tkinter.html), the GUI toolkit that
comes bundled with Python.

## What it does

- **Two-stage interface**
  1. **Product selection** — choose between **LNG** and **Gas**.
  2. **Conversion screen** — pick a *From* unit and a *To* unit, type an amount,
     and convert.
- **Supported units:** KWh, MWh, GWh, TWh, m³, bcm, th (therm), MMBtu, tonnes,
  plus the currencies EUR, USD and GBP.
- **Live conversion-rate indicator** — as you change the dropdowns, a line shows
  the current rate, e.g. `1 MWh = 3.412 MMBtu`.
- **Optional time quotient** — tick **"Per time period"** to label results with
  a rate such as *per second / per day / per month / per year*
  (e.g. `500 MMBtu/day = 146.5 MWh/day`). This is **cosmetic only** — it changes
  the label, not the underlying number.
- **Smart Convert button** — stays greyed out until a *From* unit, a *To* unit
  and a numeric amount have all been provided.
- **Live exchange rates** — currency rates are fetched once at launch from the
  free [Frankfurter API](https://www.frankfurter.app/) and cached for the
  session. If the request fails, the app falls back to built-in approximate
  rates and shows an *"Using offline rates — live FX unavailable"* banner.
- **Dark, professional theme** using `tkinter.ttk` styled widgets.

## Requirements

- **Python 3.8+** (tkinter is included with standard Python installations).
- The [`requests`](https://pypi.org/project/requests/) library, used for the
  live FX rates.

Install the dependency with:

```bash
pip install -r requirements.txt
```

## How to run

From inside the `currency-unit-converter` folder:

```bash
python energy_converter.py
```

(On some systems you may need `python3` instead of `python`.)

## Conversion factors

All energy units are converted via **MWh** as the base unit:

| Unit   | Value in MWh        |
|--------|---------------------|
| KWh    | 0.001               |
| MWh    | 1 (base)            |
| GWh    | 1,000               |
| TWh    | 1,000,000           |
| MMBtu  | 0.29307             |
| th     | 0.029307            |
| m³     | 0.010556            |
| bcm    | 10,556,000          |
| tonnes | 1.4286 (approx.)    |

## Known limitations

- **Approximate tonne conversion.** The figure of `1 tonne ≈ 1.4286 MWh` is a
  generic approximation and is used for **both** LNG and Gas products in this
  version. In reality the calorific value varies by cargo, so a more precise,
  cargo-specific value should be used in production.
- **Offline FX fallback.** If there is no internet connection (or the
  Frankfurter API is unavailable), the app uses hardcoded approximate exchange
  rates and displays a warning banner. These offline rates will drift from the
  real market over time.
- **Currencies convert only to currencies.** Mixing a currency with an energy
  unit (e.g. USD → MWh) is not meaningful and shows an error message.
- **Single calorific value.** The m³/bcm gas figures use a single standard
  calorific value rather than a region- or contract-specific one.

## License

Provided as-is for educational and internal use.

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
- **Categorised, product-aware units** — the dropdowns group units under
  headers for easier selection, and only show units relevant to the chosen
  product:
  - **Energy** (both products): KWh, MWh, GWh, TWh, kJ, GJ, kcal, Gcal, MMBtu, th
  - **Gas volume** (Gas only): m³, thou.m³, mcm, bcm, ft³, thou.ft³, m ft³ (MMcf), bcf
  - **LNG** (LNG only): tonnes, m³ LNG (liquid), mtce
  - **Currency**: EUR, USD, GBP

  So `m³` (pipeline gas) appears only under **Gas**, while `tonnes` and
  `m³ LNG` (liquid) appear only under **LNG** — because a cubic metre of gas
  and a cubic metre of liquid LNG are very different quantities.
- **Live conversion-rate indicator** — as you change the dropdowns, a line shows
  the current rate, e.g. `1 MWh = 3.412 MMBtu`.
- **From-unit indicator** — once a *From* unit is selected it appears right next
  to the amount input box, so you always see what you are typing.
- **Editable conversion values** — the **⚙ Edit conversion values** button opens
  a window where you can inspect and change how many of each energy unit equal
  1 MWh (the values are stored on a *"per 1 MWh"* basis). **Save** feeds the new
  values straight into every future conversion, and **Revert to default**
  restores the built-in figures. (Currencies are excluded — they always use live
  FX.)
- **Time quotient (rate conversion)** — tick **"Per time period"** to treat the
  value as a rate (*per second / per day / per month / per year*). The *From* and
  *To* periods can differ, and the number is rescaled accordingly — e.g.
  `500 MMBtu/day = 182,500 MMBtu/year`. A year is treated as 365 days and a month
  as exactly one twelfth of that year.
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

All energy units are converted via **MWh** as the base unit. Factors are stored
on a *"per 1 MWh"* basis — i.e. how many of each unit equal 1 MWh:

| Unit        | Per 1 MWh        | Notes                          |
|-------------|------------------|--------------------------------|
| KWh         | 1,000            |                                |
| MWh         | 1 (base)         |                                |
| GWh         | 0.001            |                                |
| TWh         | 0.000001         |                                |
| kJ          | 3,600,000        |                                |
| GJ          | 3.6              |                                |
| kcal        | 859,845          |                                |
| Gcal        | 0.859845         |                                |
| MMBtu       | 3.41199886       |                                |
| th (therm)  | 34.1199886       |                                |
| m³          | 91.1602          | natural gas (Gas only)         |
| thou.m³     | 0.0911602        | Gas only                       |
| mcm         | 9.11602×10⁻⁵     | million m³, Gas only           |
| bcm         | 9.11602×10⁻⁸     | billion m³, Gas only           |
| ft³         | 3,218.87         | Gas only                       |
| thou.ft³    | 3.2187           | Gas only                       |
| m ft³       | 0.00321887       | million ft³ (MMcf), Gas only   |
| bcf         | 3.21887×10⁻⁶     | billion ft³, Gas only          |
| tonnes      | 0.06617963       | ≈ 15.1 MWh/tonne LNG (LNG only)|
| m³ LNG      | ≈ 0.145455       | liquid LNG, derived (LNG only) |
| mtce        | 6.617963×10⁻⁸    | LNG only                       |

The **m³ LNG (liquid)** factor is derived from typical LNG properties:
density **450 kg/m³** × gross calorific value **55 MJ/kg** = 24,750 MJ/m³
≈ **6.875 MWh/m³**. These two constants live near the top of
[`energy_converter.py`](energy_converter.py) and are easy to adjust.

## Known limitations

- **Reference LNG properties.** The `tonnes`, `m³ LNG` and `mtce` figures assume
  a typical LNG density (450 kg/m³) and gross calorific value (55 MJ/kg). Real
  cargoes vary, so for production use cargo-specific values.
- **Offline FX fallback.** If there is no internet connection (or the
  Frankfurter API is unavailable), the app uses hardcoded approximate exchange
  rates and displays a warning banner. These offline rates will drift from the
  real market over time.
- **Currencies convert only to currencies.** Mixing a currency with an energy
  unit (e.g. USD → MWh) is not meaningful and shows an error message.
- **Single calorific value.** The m³/bcm gas figures use a single standard
  calorific value rather than a region- or contract-specific one.
- **Approximate time periods.** The "Per time period" feature treats a year as
  365 days and a month as exactly one twelfth of that year. It ignores leap
  years and the differing lengths of real calendar months.
- **Edited values are session-only.** Changes made in the *Edit conversion
  values* window apply until you revert them or close the app; they are not
  saved to disk.

## License

Provided as-is for educational and internal use.

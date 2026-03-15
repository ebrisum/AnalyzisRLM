#!/usr/bin/env python3
"""
GEMRAMA Assignment: Graduate Mobility & Regional Industrial Structure
=====================================================================
Research question: To what extent does regional industrial specialization
determine where university graduates settle after graduation, and does this
pattern differ between STEM and non-STEM fields?

RUG MSc Economic Geography 2025-2026
Supervised by dr. Femke Cnossen and dr. Viktor Venhorst

Usage:
    python graduate_mobility_analysis.py [--data-dir PATH]

If --data-dir is not given, the script looks for data files in the current
working directory.
"""

import argparse
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REQUIRED_FILES = [
    "Inschrijvingen_WO.csv",
    "Inschrijvingen_HBO.csv",
    "Eerstejaars_WO.csv",
    "Eerstejaars_HBO.csv",
    "Gediplomeerden_WO.csv",
    "Gediplomeerden_HBO.csv",
    "Verhuisde_personen_regio.csv",
    "Vestigingen_Bedrijven_Bedrijfstak.csv",
    "LISA_Gemeenten_2024.xlsx",
]

OPTIONAL_FILES = [
    "Tussen_gemeenten_verhuisde_personen.csv",
    "OCW_arbeidsmarkt_WO_uitstromers.csv",
]

STEM_SECTORS_DUO = [
    "TECHNIEK",
    "NATUUR",
    "LANDBOUW_EN_NATUURLIJKE_OMGEVING",
    "LANDBOUW EN NATUURLIJKE OMGEVING",
    "INFORMATICA",
]

NON_STEM_SECTORS_DUO = [
    "ECONOMIE",
    "GEDRAG_EN_MAATSCHAPPIJ",
    "GEDRAG EN MAATSCHAPPIJ",
    "GEZONDHEIDSZORG",
    "ONDERWIJS",
    "RECHT",
    "TAAL_EN_CULTUUR",
    "TAAL EN CULTUUR",
    "SECTOROVERSTIJGEND",
]

STEM_SBI = {
    "C": "Industrie (Maakindustrie)",
    "D": "Energievoorziening",
    "J": "Informatie en communicatie (ICT)",
    "M": "Specialistische zakelijke diensten (R&D/Engineering)",
}

# Province mapping for Dutch municipalities (major cities → province)
PROVINCE_CITY_MAP = {
    "Amsterdam": "Noord-Holland",
    "Rotterdam": "Zuid-Holland",
    "Den Haag": "Zuid-Holland",
    "'s-Gravenhage": "Zuid-Holland",
    "Utrecht": "Utrecht",
    "Eindhoven": "Noord-Brabant",
    "Tilburg": "Noord-Brabant",
    "Groningen": "Groningen",
    "Almere": "Flevoland",
    "Breda": "Noord-Brabant",
    "Nijmegen": "Gelderland",
    "Arnhem": "Gelderland",
    "Haarlem": "Noord-Holland",
    "Enschede": "Overijssel",
    "Apeldoorn": "Gelderland",
    "Amersfoort": "Utrecht",
    "Leiden": "Zuid-Holland",
    "Delft": "Zuid-Holland",
    "Maastricht": "Limburg",
    "Leeuwarden": "Friesland",
    "Zwolle": "Overijssel",
    "Assen": "Drenthe",
    "Middelburg": "Zeeland",
    "Lelystad": "Flevoland",
}

DUTCH_PROVINCES = [
    "Groningen", "Friesland", "Drenthe", "Overijssel", "Flevoland",
    "Gelderland", "Utrecht", "Noord-Holland", "Zuid-Holland",
    "Zeeland", "Noord-Brabant", "Limburg",
]

# Approximate province populations (2024) for mobility intensity calculation
PROVINCE_POP = {
    "Groningen": 596_000,
    "Friesland": 654_000,
    "Drenthe": 500_000,
    "Overijssel": 1_172_000,
    "Flevoland": 437_000,
    "Gelderland": 2_112_000,
    "Utrecht": 1_380_000,
    "Noord-Holland": 2_937_000,
    "Zuid-Holland": 3_750_000,
    "Zeeland": 387_000,
    "Noord-Brabant": 2_600_000,
    "Limburg": 1_118_000,
}
NL_TOTAL_POP = sum(PROVINCE_POP.values())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

data_quality_notes = []
generated_date = datetime.now().strftime("%Y-%m-%d %H:%M")


def note(msg):
    """Record a data quality note."""
    data_quality_notes.append(msg)
    print(f"  📝 {msg}")


def load_csv(filepath, name="file"):
    """Try loading a CSV with multiple separators and encodings."""
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        for sep in [";", ",", "\t"]:
            try:
                df = pd.read_csv(filepath, sep=sep, encoding=enc, low_memory=False)
                if len(df.columns) > 1:
                    # Clean column names
                    df.columns = df.columns.str.strip()
                    print(f"  ✅ Loaded {name}: {len(df)} rows × {len(df.columns)} cols "
                          f"(sep='{sep}', enc={enc})")
                    return df
            except Exception:
                continue
    # Try skipping header rows (CBS metadata)
    for skip in [1, 2, 3, 4]:
        for enc in ["utf-8-sig", "latin-1"]:
            for sep in [";", ","]:
                try:
                    df = pd.read_csv(filepath, sep=sep, encoding=enc,
                                     skiprows=skip, low_memory=False)
                    if len(df.columns) > 1:
                        df.columns = df.columns.str.strip()
                        print(f"  ✅ Loaded {name}: {len(df)} rows × {len(df.columns)} cols "
                              f"(sep='{sep}', enc={enc}, skipped {skip} rows)")
                        note(f"{name}: skipped {skip} metadata header rows")
                        return df
                except Exception:
                    continue
    print(f"  ❌ PARSE ERROR: {name}")
    print(f"     Problem: Could not parse with any separator/encoding combination")
    print(f"     Fix: Open in Excel → Save As → CSV UTF-8 (comma delimited)")
    note(f"PARSE ERROR: {name} could not be loaded")
    return None


def load_excel(filepath, name="file"):
    """Load an Excel file."""
    try:
        df = pd.read_excel(filepath)
        df.columns = df.columns.str.strip()
        print(f"  ✅ Loaded {name}: {len(df)} rows × {len(df.columns)} cols")
        return df
    except Exception as e:
        print(f"  ❌ PARSE ERROR: {name}")
        print(f"     Problem: {e}")
        note(f"PARSE ERROR: {name}: {e}")
        return None


def clean_numeric(series):
    """Clean Dutch-formatted numbers (1.234,56 → 1234.56)."""
    if series.dtype == object:
        s = series.astype(str).str.strip()
        s = s.replace({"": np.nan, ".": np.nan, "-": np.nan, "x": np.nan, "X": np.nan})
        # If values contain comma as decimal: 1.234,56 → 1234.56
        if s.str.contains(",", na=False).any():
            s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        else:
            # Remove thousands separator dots: 1.234 → 1234
            # Only if pattern looks like thousands separator
            if s.str.match(r"^\d{1,3}(\.\d{3})+$", na=False).any():
                s = s.str.replace(".", "", regex=False)
        return pd.to_numeric(s, errors="coerce")
    return pd.to_numeric(series, errors="coerce")


def inspect_df(df, name):
    """Print inspection details for a dataframe."""
    print(f"\n  --- {name} ---")
    print(f"  Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"  Columns: {list(df.columns)}")
    # Show unique values of key categorical columns
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ["regio", "sector", "jaar", "year",
                                           "opleiding", "onderdeel", "provincie",
                                           "instelling", "geslacht", "bedrijfstak"]):
            nuniq = df[col].nunique()
            if nuniq <= 30:
                print(f"  {col} ({nuniq} unique): {sorted(df[col].dropna().unique())}")
            else:
                print(f"  {col} ({nuniq} unique): [too many to list]")


def find_column(df, candidates, partial=True):
    """Find first matching column from candidates list."""
    cols_upper = {c.upper(): c for c in df.columns}
    for cand in candidates:
        cand_up = cand.upper()
        if cand_up in cols_upper:
            return cols_upper[cand_up]
        if partial:
            for cup, creal in cols_upper.items():
                if cand_up in cup or cup in cand_up:
                    return creal
    return None


def is_stem_duo(sector_val):
    """Check if a DUO sector value is STEM."""
    if pd.isna(sector_val):
        return False
    s = str(sector_val).upper().strip()
    for stem in STEM_SECTORS_DUO:
        if stem in s or s in stem:
            return True
    return False


def fmt_pct(val):
    """Format percentage."""
    if pd.isna(val):
        return "N/A"
    return f"{val:.1f}%"


def fmt_num(val):
    """Format number with thousands separator."""
    if pd.isna(val):
        return "N/A"
    return f"{val:,.0f}".replace(",", ".")


def write_csv_header(f, sources, caveats=""):
    """Write a metadata header to a CSV file handle."""
    f.write(f"# Generated: {generated_date}\n")
    f.write(f"# Sources: {sources}\n")
    if caveats:
        f.write(f"# Caveats: {caveats}\n")


# ---------------------------------------------------------------------------
# STEP 0: File check
# ---------------------------------------------------------------------------

def step0_file_check(data_dir):
    """Check which required and optional files are present."""
    print("\n" + "=" * 60)
    print("=== FILE STATUS CHECK ===")
    print("=" * 60)

    found = {}
    missing = []

    for fn in REQUIRED_FILES + OPTIONAL_FILES:
        fp = os.path.join(data_dir, fn)
        if os.path.isfile(fp):
            print(f"  ✅ FOUND:    {fn}")
            found[fn] = fp
        else:
            print(f"  ❌ MISSING:  {fn}")
            missing.append(fn)

    if missing:
        print("\n  === WHAT TO DO FOR MISSING FILES ===")
        instructions = {
            "Tussen_gemeenten_verhuisde_personen.csv": (
                "→ Go to: https://opendata.cbs.nl/statline/portal.html?_la=nl&_catalog=CBS&tableId=81734NED\n"
                "  → Select: Gemeente van vertrek = Groningen, all destination municipalities, all years\n"
                "  → Download as CSV and rename to: Tussen_gemeenten_verhuisde_personen.csv"
            ),
            "OCW_arbeidsmarkt_WO_uitstromers.csv": (
                "→ Go to: https://www.ocwincijfers.nl/sectoren/hoger-onderwijs/kwaliteit/onderwijs-en-arbeidsmarkt\n"
                "  → Click: 'Arbeidsmarktkenmerken uitstromers WO' → download CSV\n"
                "  → Rename to: OCW_arbeidsmarkt_WO_uitstromers.csv"
            ),
            "Verhuisde_personen_regio.csv": (
                "→ Go to CBS StatLine: https://opendata.cbs.nl/statline/ → search '60048ned'\n"
                "  → Select Gemeente = Groningen, all years, all age groups\n"
                "  → Download as CSV"
            ),
            "Vestigingen_Bedrijven_Bedrijfstak.csv": (
                "→ Go to CBS StatLine → dataset 81589NED\n"
                "  → Select ALL provinces under Regio's, all SBI sectors\n"
                "  → Download as CSV"
            ),
            "LISA_Gemeenten_2024.xlsx": (
                "→ Obtain from LISA (Landelijk Informatiesysteem Arbeidsplaatsen)\n"
                "  → Or from course materials"
            ),
        }
        for fn in missing:
            print(f"\n  ❌ {fn}")
            if fn in instructions:
                print(f"     {instructions[fn]}")

    return found, missing


# ---------------------------------------------------------------------------
# STEP 1: Inspect files
# ---------------------------------------------------------------------------

def step1_inspect(found):
    """Load and inspect all found files."""
    print("\n" + "=" * 60)
    print("=== STEP 1: INSPECT ALL FILES ===")
    print("=" * 60)

    loaded = {}
    for fn, fp in found.items():
        if fn.endswith(".xlsx") or fn.endswith(".xls"):
            df = load_excel(fp, fn)
        else:
            df = load_csv(fp, fn)

        if df is not None:
            loaded[fn] = df
            inspect_df(df, fn)
            # Clean missing value markers
            df.replace({"": np.nan, ".": np.nan, "-": np.nan}, inplace=True)
        else:
            note(f"Could not load {fn} — analyses depending on it will be skipped")

    return loaded


# ---------------------------------------------------------------------------
# STEP 2: STEM classification
# ---------------------------------------------------------------------------

def step2_stem_classification():
    """Print the STEM classification used."""
    print("\n" + "=" * 60)
    print("=== STEP 2: STEM CLASSIFICATION APPLIED ===")
    print("=" * 60)
    print(f"  DUO sectors classified as STEM: {', '.join(STEM_SECTORS_DUO)}")
    print(f"  SBI sectors classified as STEM: {', '.join(f'{k} ({v})' for k, v in STEM_SBI.items())}")
    print(f"  Non-STEM reference sectors: {', '.join(NON_STEM_SECTORS_DUO[:4])}")
    print(f"  Note: SBI sector M includes consultancy and R&D — included but flagged")
    note("SBI sector M (Specialistische zakelijke diensten) includes both R&D/Engineering "
         "and management consultancy. This may slightly overestimate STEM employment.")


# ---------------------------------------------------------------------------
# STEP 3: Analysis A — STEM Education Pipeline
# ---------------------------------------------------------------------------

def step3_analysis_a(loaded, out_dir):
    """Analyse STEM graduate pipeline from DUO data."""
    print("\n" + "=" * 60)
    print("=== STEP 3: ANALYSIS A — STEM EDUCATION PIPELINE ===")
    print("=" * 60)

    results_a = {}

    for level in ["WO", "HBO"]:
        grad_fn = f"Gediplomeerden_{level}.csv"
        eerst_fn = f"Eerstejaars_{level}.csv"

        grad_df = loaded.get(grad_fn)
        eerst_df = loaded.get(eerst_fn)

        if grad_df is None:
            print(f"\n  ⚠️ {grad_fn} not loaded — skipping {level} graduate analysis")
            continue

        print(f"\n  --- Processing {grad_fn} ---")

        # A1: Filter for Groningen institutions
        inst_col = find_column(grad_df, ["INSTELLINGSNAAM", "INSTELLING", "INSTELLINGNAAM"])
        prov_col = find_column(grad_df, ["PROVINCIENAAM", "PROVINCIE"])

        groningen_filter = None
        if inst_col:
            groningen_filter = grad_df[inst_col].astype(str).str.upper().str.contains(
                "GRONINGEN|RUG|RIJKSUNIVERSITEIT|HANZE", na=False)
            print(f"  Filtering on {inst_col} for Groningen institutions")
        elif prov_col:
            groningen_filter = grad_df[prov_col].astype(str).str.upper().str.contains(
                "GRONINGEN", na=False)
            print(f"  Filtering on {prov_col} = Groningen")
        else:
            print(f"  ⚠️ WARNING: Cannot filter on Groningen institutions")
            print(f"     Columns present: {list(grad_df.columns)}")
            print(f"     Using full dataset (may include non-Groningen institutions)")
            note(f"{grad_fn}: no institution/province column found, using full dataset")
            groningen_filter = pd.Series(True, index=grad_df.index)

        gdf = grad_df[groningen_filter].copy()
        print(f"  Groningen filter: {groningen_filter.sum()} of {len(grad_df)} rows")

        # Find sector and year columns
        sector_col = find_column(gdf, ["ONDERDEEL", "SECTOR", "CROHO ONDERDEEL",
                                        "CROHO_ONDERDEEL", "ISCED", "OPLEIDINGSFASE"])
        year_col = find_column(gdf, ["JAAR", "YEAR", "ACADEMIEJAAR", "COLLEGEJAAR"])
        count_col = find_column(gdf, ["AANTAL", "GEDIPLOMEERDEN", "TOTAAL",
                                       "AANTAL GEDIPLOMEERDEN", "MAN", "VROUW"])
        gender_col = find_column(gdf, ["GESLACHT", "GENDER"])

        if sector_col is None:
            print(f"  ⚠️ No sector column found in {grad_fn}")
            print(f"     Columns: {list(gdf.columns)}")
            note(f"{grad_fn}: no sector column found — cannot classify STEM/non-STEM")
            continue

        print(f"  Sector column: {sector_col}")
        print(f"  Year column: {year_col}")
        print(f"  Unique sectors: {gdf[sector_col].unique()}")

        # Classify STEM
        gdf["IS_STEM"] = gdf[sector_col].apply(is_stem_duo)

        # Find numeric columns for counting
        if count_col:
            gdf["COUNT"] = clean_numeric(gdf[count_col])
        else:
            # Look for MAN + VROUW columns to sum
            man_col = find_column(gdf, ["MAN", "MANNEN", "M"])
            vrouw_col = find_column(gdf, ["VROUW", "VROUWEN", "V"])
            if man_col and vrouw_col:
                gdf["COUNT"] = clean_numeric(gdf[man_col]) + clean_numeric(gdf[vrouw_col])
                print(f"  Count = {man_col} + {vrouw_col}")
            else:
                # Try to find any numeric column that looks like counts
                for c in gdf.columns:
                    if gdf[c].dtype in [np.int64, np.float64]:
                        vals = gdf[c].dropna()
                        if len(vals) > 0 and vals.mean() > 1:
                            gdf["COUNT"] = gdf[c]
                            print(f"  Using numeric column '{c}' as count")
                            break
                else:
                    gdf["COUNT"] = 1  # each row = 1 observation
                    note(f"{grad_fn}: no count column found, treating each row as 1")

        # A2: Annual STEM graduates
        if year_col:
            yearly = gdf.groupby([year_col, "IS_STEM"])["COUNT"].sum().unstack(fill_value=0)
            yearly.columns = [f"{level}_STEM_GRADS" if c else f"{level}_NONSTEM_GRADS"
                              for c in yearly.columns]
            if f"{level}_STEM_GRADS" in yearly.columns and f"{level}_NONSTEM_GRADS" in yearly.columns:
                total = yearly[f"{level}_STEM_GRADS"] + yearly[f"{level}_NONSTEM_GRADS"]
                yearly[f"{level}_STEM_PCT"] = (yearly[f"{level}_STEM_GRADS"] / total * 100).round(1)
            results_a[f"{level}_yearly"] = yearly
            print(f"\n  ✅ {level} annual STEM graduates:")
            print(yearly.to_string())
        else:
            print(f"  ⚠️ No year column — cannot produce time series")
            note(f"{grad_fn}: no year column found")

        # A3: Gender breakdown (latest year)
        man_col = find_column(gdf, ["MAN", "MANNEN"])
        vrouw_col = find_column(gdf, ["VROUW", "VROUWEN"])
        if man_col and vrouw_col and year_col:
            latest_year = gdf[year_col].max()
            latest = gdf[gdf[year_col] == latest_year].copy()
            latest["MEN"] = clean_numeric(latest[man_col])
            latest["WOMEN"] = clean_numeric(latest[vrouw_col])
            gender_summary = latest.groupby(sector_col).agg(
                MEN=("MEN", "sum"), WOMEN=("WOMEN", "sum")).reset_index()
            gender_summary["PCT_WOMEN"] = (
                gender_summary["WOMEN"] / (gender_summary["MEN"] + gender_summary["WOMEN"]) * 100
            ).round(1)
            gender_summary.insert(0, "YEAR", latest_year)
            results_a[f"{level}_gender"] = gender_summary
            print(f"\n  ✅ {level} gender breakdown ({latest_year}):")
            print(gender_summary.to_string(index=False))

        # A4: Pipeline leakage
        if eerst_df is not None and year_col:
            print(f"\n  --- Pipeline leakage: {eerst_fn} vs {grad_fn} ---")
            # Apply same Groningen filter to first-years
            e_inst_col = find_column(eerst_df, ["INSTELLINGSNAAM", "INSTELLING"])
            e_prov_col = find_column(eerst_df, ["PROVINCIENAAM", "PROVINCIE"])
            if e_inst_col:
                e_filter = eerst_df[e_inst_col].astype(str).str.upper().str.contains(
                    "GRONINGEN|RUG|RIJKSUNIVERSITEIT|HANZE", na=False)
            elif e_prov_col:
                e_filter = eerst_df[e_prov_col].astype(str).str.upper().str.contains(
                    "GRONINGEN", na=False)
            else:
                e_filter = pd.Series(True, index=eerst_df.index)

            edf = eerst_df[e_filter].copy()
            e_sector_col = find_column(edf, ["ONDERDEEL", "SECTOR", "CROHO ONDERDEEL",
                                              "CROHO_ONDERDEEL"])
            e_year_col = find_column(edf, ["JAAR", "YEAR", "ACADEMIEJAAR", "COLLEGEJAAR"])
            e_count_col = find_column(edf, ["AANTAL", "EERSTEJAARS", "TOTAAL"])

            if e_sector_col and e_year_col:
                edf["IS_STEM"] = edf[e_sector_col].apply(is_stem_duo)
                if e_count_col:
                    edf["COUNT"] = clean_numeric(edf[e_count_col])
                else:
                    e_man = find_column(edf, ["MAN", "MANNEN"])
                    e_vrouw = find_column(edf, ["VROUW", "VROUWEN"])
                    if e_man and e_vrouw:
                        edf["COUNT"] = clean_numeric(edf[e_man]) + clean_numeric(edf[e_vrouw])
                    else:
                        edf["COUNT"] = 1

                e_yearly = edf[edf["IS_STEM"]].groupby(e_year_col)["COUNT"].sum()
                g_yearly = gdf[gdf["IS_STEM"]].groupby(year_col)["COUNT"].sum()

                # Try 4-year offset for WO, 4 for HBO
                offset = 4 if level == "WO" else 4
                leakage_rows = []
                for yr in e_yearly.index:
                    grad_yr = yr + offset if isinstance(yr, (int, float)) else yr
                    if grad_yr in g_yearly.index:
                        e_val = e_yearly[yr]
                        g_val = g_yearly[grad_yr]
                        if e_val > 0:
                            dropout = (e_val - g_val) / e_val * 100
                            leakage_rows.append({
                                "FIRST_YEAR_COHORT": yr,
                                "GRAD_YEAR": grad_yr,
                                "STEM_FIRST_YEARS": e_val,
                                "STEM_GRADUATES": g_val,
                                "DROPOUT_PCT": round(dropout, 1),
                            })

                if leakage_rows:
                    leak_df = pd.DataFrame(leakage_rows)
                    results_a[f"{level}_leakage"] = leak_df
                    print(f"\n  ✅ {level} pipeline leakage:")
                    print(leak_df.to_string(index=False))
                    print("\n  Note: This is an approximation. Actual cohort tracking requires "
                          "individual-level CBS microdata.")
                    print("  Some students switch programmes or take longer than 4 years.")
                    print("  The dropout rate is an upper bound estimate.")
                else:
                    print(f"  ⚠️ No matching cohort years found for {offset}-year offset")

    # Save output
    output_path = os.path.join(out_dir, "output_A_stem_pipeline_groningen.csv")
    with open(output_path, "w") as f:
        write_csv_header(f, "DUO Gediplomeerden WO/HBO, Eerstejaars WO/HBO",
                         "Groningen institutions only; STEM classification as defined in Step 2")
        for key, df in results_a.items():
            f.write(f"\n# {key}\n")
            df.to_csv(f)
    print(f"\n  ✅ Step 3 complete — saved to {output_path}")

    return results_a


# ---------------------------------------------------------------------------
# STEP 4: Analysis B — Regional Industrial Structure
# ---------------------------------------------------------------------------

def step4_analysis_b(loaded, out_dir):
    """Calculate Location Quotients for STEM industries."""
    print("\n" + "=" * 60)
    print("=== STEP 4: ANALYSIS B — REGIONAL INDUSTRIAL STRUCTURE ===")
    print("=" * 60)

    results_b = {}

    # B1: Vestigingen
    vest_fn = "Vestigingen_Bedrijven_Bedrijfstak.csv"
    vest_df = loaded.get(vest_fn)

    if vest_df is None:
        print(f"  ⚠️ {vest_fn} not loaded — skipping LQ analysis")
        note(f"Location Quotient analysis skipped: {vest_fn} not available")
    else:
        print(f"\n  --- B1: Inspecting {vest_fn} ---")

        # Find region column
        regio_col = find_column(vest_df, ["REGIO", "REGIO'S", "REGIOS",
                                           "PROVINCIE", "COROP", "Regio's"])
        sector_col = find_column(vest_df, ["BEDRIJFSTAK", "BEDRIJFSTAKKEN",
                                            "SBI", "BRANCHE", "Bedrijfstakken/branches SBI 2008",
                                            "Bedrijfstakken"])
        count_col = find_column(vest_df, ["VESTIGINGEN", "AANTAL", "TOTAAL",
                                           "Vestigingen", "Bedrijven"])

        if regio_col:
            regions = vest_df[regio_col].dropna().unique()
            print(f"  Regions found ({len(regions)}): {sorted(regions)[:20]}")

            # Check if all provinces present
            regions_upper = set(str(r).upper().strip() for r in regions)
            provinces_found = []
            for prov in DUTCH_PROVINCES:
                if any(prov.upper() in r for r in regions_upper):
                    provinces_found.append(prov)

            if len(provinces_found) < 6:
                print(f"\n  ❌ INCOMPLETE: Vestigingen file only contains {len(provinces_found)} provinces")
                print(f"     Found: {provinces_found}")
                print(f"     For Location Quotient analysis you need ALL provinces.")
                print(f"     Action: Go to CBS StatLine → dataset 81589NED")
                print(f"     → Select ALL provinces under Regio's")
                print(f"     Skipping LQ analysis — running Groningen-only descriptives instead.")
                note("LQ analysis incomplete: not all provinces in Vestigingen file")

                # Groningen-only descriptives
                if sector_col and count_col:
                    gron_mask = vest_df[regio_col].astype(str).str.upper().str.contains("GRONINGEN", na=False)
                    gron = vest_df[gron_mask].copy()
                    gron["COUNT"] = clean_numeric(gron[count_col])
                    sector_summary = gron.groupby(sector_col)["COUNT"].sum().sort_values(ascending=False)
                    print(f"\n  Groningen establishments by sector:")
                    print(sector_summary.to_string())
                    results_b["groningen_sectors"] = sector_summary
            else:
                print(f"  ✅ All provinces present: {provinces_found}")

                # B2: Location Quotient calculation
                if sector_col and count_col:
                    vest_df["COUNT"] = clean_numeric(vest_df[count_col])

                    # Identify STEM SBI sectors
                    sectors = vest_df[sector_col].dropna().unique()
                    print(f"\n  Sectors in data: {sorted(sectors)[:20]}")

                    # Map sectors to SBI codes
                    def classify_sbi_stem(sector_name):
                        s = str(sector_name).upper()
                        if any(kw in s for kw in ["INDUSTRIE", "MAAKINDUSTRIE", "NIJVERHEID"]):
                            return "C"
                        if any(kw in s for kw in ["ENERGIE", "ELECTRICITEIT", "GAS"]):
                            return "D"
                        if any(kw in s for kw in ["INFORMATIE", "COMMUNICATIE", "ICT", "IT"]):
                            return "J"
                        if any(kw in s for kw in ["SPECIALISTISCH", "ZAKELIJK", "ADVIES",
                                                    "TECHNISCH", "WETENSCHAPPELIJK", "RESEARCH"]):
                            return "M"
                        return "OTHER"

                    vest_df["SBI_GROUP"] = vest_df[sector_col].apply(classify_sbi_stem)
                    vest_df["IS_STEM_SBI"] = vest_df["SBI_GROUP"].isin(["C", "D", "J", "M"])

                    # Calculate LQ per region per STEM sector
                    lq_rows = []
                    for region in vest_df[regio_col].dropna().unique():
                        region_data = vest_df[vest_df[regio_col] == region]
                        total_region = region_data["COUNT"].sum()
                        if total_region == 0:
                            continue

                        total_national = vest_df["COUNT"].sum()
                        row = {"REGION": region}

                        for sbi_code, sbi_name in [("C", "Industrie_C"),
                                                     ("J", "ICT_J"),
                                                     ("M", "Zakelijk_M")]:
                            sector_region = region_data[region_data["SBI_GROUP"] == sbi_code]["COUNT"].sum()
                            sector_national = vest_df[vest_df["SBI_GROUP"] == sbi_code]["COUNT"].sum()

                            if total_national > 0 and sector_national > 0:
                                lq = (sector_region / total_region) / (sector_national / total_national)
                                row[f"LQ_{sbi_name}"] = round(lq, 2)
                            else:
                                row[f"LQ_{sbi_name}"] = np.nan

                        lq_rows.append(row)

                    if lq_rows:
                        lq_df = pd.DataFrame(lq_rows)

                        # Composite STEM LQ (weighted average)
                        lq_cols = [c for c in lq_df.columns if c.startswith("LQ_")]
                        lq_df["STEM_LQ_COMPOSITE"] = lq_df[lq_cols].mean(axis=1).round(2)

                        # B3: Rank regions
                        lq_df = lq_df.sort_values("STEM_LQ_COMPOSITE", ascending=False).reset_index(drop=True)
                        lq_df.index += 1  # 1-based rank
                        lq_df.index.name = "RANK"

                        results_b["lq"] = lq_df
                        print(f"\n  ✅ Location Quotients (ranked by STEM LQ composite):")
                        print(lq_df.to_string())

                        # Find Groningen's rank
                        gron_rows = lq_df[lq_df["REGION"].astype(str).str.upper().str.contains("GRONINGEN")]
                        if len(gron_rows) > 0:
                            gron_rank = gron_rows.index[0]
                            gron_lq = gron_rows["STEM_LQ_COMPOSITE"].values[0]
                            print(f"\n  📊 Groningen ranks #{gron_rank} of {len(lq_df)} regions "
                                  f"(composite STEM LQ = {gron_lq})")
                            results_b["groningen_rank"] = gron_rank
                            results_b["groningen_lq"] = gron_lq
                            results_b["total_regions"] = len(lq_df)
                else:
                    print(f"  ⚠️ Could not find sector or count column for LQ calculation")
                    note(f"{vest_fn}: missing sector or count column for LQ analysis")
        else:
            print(f"  ⚠️ No region column found in {vest_fn}")
            print(f"     Columns: {list(vest_df.columns)}")

    # B4: LISA cross-check
    lisa_fn = "LISA_Gemeenten_2024.xlsx"
    lisa_df = loaded.get(lisa_fn)

    if lisa_df is not None:
        print(f"\n  --- B4: LISA cross-check ---")

        # Find relevant columns
        gemeente_col = find_column(lisa_df, ["GEMEENTE", "GEMEENTENAAM", "GM_NAAM"])
        sector_col_l = find_column(lisa_df, ["SECTOR", "BEDRIJFSTAK", "SBI", "BRANCHE"])

        if gemeente_col:
            gron_mask = lisa_df[gemeente_col].astype(str).str.upper().str.contains("GRONINGEN", na=False)
            gron_lisa = lisa_df[gron_mask]
            print(f"  Groningen rows in LISA: {len(gron_lisa)}")

            # Try to extract job counts
            job_col = find_column(lisa_df, ["BANEN", "WERKGELEGENHEID", "TOTAAL", "AANTAL"])
            if job_col:
                total_jobs = clean_numeric(gron_lisa[job_col]).sum()
                print(f"  Total jobs in Groningen (LISA): {fmt_num(total_jobs)}")
                results_b["lisa_total_jobs"] = total_jobs

                if sector_col_l:
                    gron_lisa = gron_lisa.copy()
                    gron_lisa["IS_STEM"] = gron_lisa[sector_col_l].apply(
                        lambda x: any(kw in str(x).upper() for kw in
                                      ["INDUSTRIE", "ICT", "INFORMATIE", "TECHNISCH",
                                       "ENERGIE", "ZAKELIJK"]))
                    stem_jobs = clean_numeric(gron_lisa[gron_lisa["IS_STEM"]][job_col]).sum()
                    stem_pct = stem_jobs / total_jobs * 100 if total_jobs > 0 else 0
                    print(f"  STEM jobs in Groningen (LISA): {fmt_num(stem_jobs)} ({fmt_pct(stem_pct)})")
                    results_b["lisa_stem_jobs"] = stem_jobs
                    results_b["lisa_stem_pct"] = stem_pct
            else:
                # Sum all numeric columns as potential job counts
                numeric_cols = gron_lisa.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    print(f"  Numeric columns in LISA: {list(numeric_cols)}")
                    for nc in numeric_cols[:5]:
                        print(f"    {nc}: sum = {gron_lisa[nc].sum()}")
        else:
            print(f"  ⚠️ No gemeente column found in LISA")
            print(f"     Columns: {list(lisa_df.columns)}")
    else:
        print(f"  ⚠️ LISA file not loaded — skipping cross-check")

    # Validation comparison
    if "lisa_stem_pct" in results_b and "lq" in results_b:
        gron_lq_rows = results_b["lq"][
            results_b["lq"]["REGION"].astype(str).str.upper().str.contains("GRONINGEN")]
        if len(gron_lq_rows) > 0:
            cbs_lq = gron_lq_rows["STEM_LQ_COMPOSITE"].values[0]
            lisa_pct = results_b["lisa_stem_pct"]
            print(f"\n  ⚠️ VALIDATION: LISA STEM share = {fmt_pct(lisa_pct)}, "
                  f"CBS composite LQ = {cbs_lq}")
            print(f"     LISA counts workers (banen), CBS counts establishments (vestigingen)")
            note("LISA and CBS measure different things: workers vs establishments")

    # Save output
    output_path = os.path.join(out_dir, "output_B_location_quotients.csv")
    with open(output_path, "w") as f:
        write_csv_header(f, "CBS Vestigingen (81589NED), LISA Gemeenten 2024",
                         "SBI sector M includes consultancy; LQ calculated on establishment counts")
        for key, val in results_b.items():
            if isinstance(val, (pd.DataFrame, pd.Series)):
                f.write(f"\n# {key}\n")
                if isinstance(val, pd.Series):
                    val.to_csv(f)
                else:
                    val.to_csv(f)
            elif isinstance(val, (int, float)):
                f.write(f"# {key}: {val}\n")
    print(f"\n  ✅ Step 4 complete — saved to {output_path}")

    return results_b


# ---------------------------------------------------------------------------
# STEP 5: Analysis C — Mobility Flows
# ---------------------------------------------------------------------------

def step5_analysis_c(loaded, out_dir):
    """Analyse migration flows from Groningen."""
    print("\n" + "=" * 60)
    print("=== STEP 5: ANALYSIS C — MOBILITY FLOWS ===")
    print("=" * 60)

    results_c = {}

    # C1: Verhuisde personen
    vh_fn = "Verhuisde_personen_regio.csv"
    vh_df = loaded.get(vh_fn)

    if vh_df is None:
        print(f"  ❌ {vh_fn} not loaded — skipping mobility analysis")
        note("Mobility flow analysis skipped: Verhuisde_personen_regio.csv not available")
    else:
        print(f"\n  --- C1: Inspecting migration data ---")
        print(f"  Columns: {list(vh_df.columns)}")

        # Find relevant columns — these CBS files can have various structures
        year_col = find_column(vh_df, ["PERIODEN", "JAAR", "YEAR", "Perioden"])
        regio_col = find_column(vh_df, ["REGIO", "REGIO'S", "REGIOS", "Regio's"])

        # Look for age-specific migration columns
        # CBS format often has columns like "Vertrokken personen: 20 tot 25 jaar"
        cols_lower = {c: c.lower() for c in vh_df.columns}

        vertrokken_20_25 = None
        vertrokken_25_30 = None
        gevestigd_20_25 = None
        gevestigd_25_30 = None

        for col in vh_df.columns:
            cl = col.lower()
            if "vertrokken" in cl or "vertrek" in cl:
                if "20" in cl and "25" in cl:
                    vertrokken_20_25 = col
                elif "25" in cl and "30" in cl:
                    vertrokken_25_30 = col
            if "gevestigd" in cl or "vestiging" in cl:
                if "20" in cl and "25" in cl:
                    gevestigd_20_25 = col
                elif "25" in cl and "30" in cl:
                    gevestigd_25_30 = col

        # If not found by name, try to find by inspecting all columns
        if vertrokken_25_30 is None:
            print(f"  ⚠️ Could not identify age-specific migration columns by name")
            print(f"     Looking for alternative column structures...")

            # Check if data is in long format with age group column
            age_col = find_column(vh_df, ["LEEFTIJD", "LEEFTIJDSGROEP", "AGE",
                                           "Leeftijd", "Leeftijdsgroep"])
            type_col = find_column(vh_df, ["MIGRATIE", "TYPE", "RICHTING",
                                            "Verhuisrichting", "Stromen"])
            count_col = find_column(vh_df, ["AANTAL", "WAARDE", "VALUE",
                                             "Verhuisde personen", "Personen"])

            if age_col:
                print(f"  Found age column: {age_col}")
                print(f"  Age groups: {vh_df[age_col].unique()}")

                # Pivot or filter as needed
                if type_col:
                    print(f"  Found type column: {type_col}")
                    print(f"  Types: {vh_df[type_col].unique()}")

            # Fall back: show all numeric columns and let user interpret
            print(f"\n  All columns with sample values:")
            for col in vh_df.columns:
                sample = vh_df[col].dropna().head(3).tolist()
                print(f"    {col}: {sample}")

        # C2: Calculate net migration
        if vertrokken_25_30 is not None and gevestigd_25_30 is not None:
            print(f"\n  --- C2: Net migration by age cohort ---")

            if regio_col:
                gron_mask = vh_df[regio_col].astype(str).str.upper().str.contains("GRONINGEN", na=False)
                mig = vh_df[gron_mask].copy()
            else:
                mig = vh_df.copy()
                note("Migration data: no region column, assuming pre-filtered for Groningen")

            mig["V_20_25"] = clean_numeric(mig[vertrokken_20_25]) if vertrokken_20_25 else 0
            mig["V_25_30"] = clean_numeric(mig[vertrokken_25_30])
            mig["G_20_25"] = clean_numeric(mig[gevestigd_20_25]) if gevestigd_20_25 else 0
            mig["G_25_30"] = clean_numeric(mig[gevestigd_25_30])
            mig["NET_20_25"] = mig["G_20_25"] - mig["V_20_25"]
            mig["NET_25_30"] = mig["G_25_30"] - mig["V_25_30"]

            if year_col:
                yearly_mig = mig.groupby(year_col).agg({
                    "G_20_25": "sum", "V_20_25": "sum", "NET_20_25": "sum",
                    "G_25_30": "sum", "V_25_30": "sum", "NET_25_30": "sum",
                }).reset_index()

                # C3: Retention rate
                yearly_mig["RETENTION_25_30"] = (
                    yearly_mig["G_25_30"] /
                    (yearly_mig["G_25_30"] + yearly_mig["V_25_30"]) * 100
                ).round(1)

                yearly_mig["INTERPRET"] = yearly_mig.apply(
                    lambda r: "Attracts students, loses graduates"
                    if r["NET_20_25"] > 0 and r["NET_25_30"] < 0
                    else "Mixed pattern", axis=1)

                results_c["yearly_migration"] = yearly_mig
                print(f"\n  ✅ Annual net migration:")
                print(yearly_mig.to_string(index=False))

                # COVID flag
                for yr_val in yearly_mig[year_col]:
                    yr_str = str(yr_val)
                    if "2020" in yr_str or "2021" in yr_str:
                        note(f"COVID flag: year {yr_val} may show anomalous migration patterns")
            else:
                print(f"  ⚠️ No year column — showing totals only")
                print(f"  Net 25-30: {mig['NET_25_30'].sum()}")
        else:
            # Try a different approach: maybe all data is in rows with different age groups
            print(f"\n  ⚠️ Could not compute net migration with available column structure")
            print(f"     Manual inspection of the file may be needed")
            note("Migration analysis: could not identify age-specific columns automatically. "
                 "Manual column mapping may be required.")

    # C4: Destination analysis
    tussen_fn = "Tussen_gemeenten_verhuisde_personen.csv"
    tussen_df = loaded.get(tussen_fn)

    if tussen_df is None:
        print(f"\n  ❌ DESTINATION ANALYSIS SKIPPED — {tussen_fn} not found.")
        print(f"     This is the most important missing piece for spatial mobility analysis.")
        print(f"     Without it, you can show THAT people leave Groningen but not WHERE they go.")
        note(f"Destination analysis skipped: {tussen_fn} not available. "
             "This is critical for the spatial mobility argument.")
    else:
        print(f"\n  --- C4: Destination analysis ---")

        dest_col = find_column(tussen_df, ["BESTEMMING", "VESTIGINGSGEMEENTE",
                                            "GEMEENTE_VESTIGING", "REGIO_VESTIGING",
                                            "Regio van vestiging"])
        count_col = find_column(tussen_df, ["AANTAL", "PERSONEN", "WAARDE",
                                             "Verhuisde personen"])

        if dest_col and count_col:
            tussen_df["COUNT"] = clean_numeric(tussen_df[count_col])

            # Aggregate to province level using gemeente-province mapping
            # This is approximate — ideally use CBS gemeente-province table
            dest_summary = tussen_df.groupby(dest_col)["COUNT"].sum().sort_values(ascending=False)
            print(f"  Top 10 destination municipalities:")
            print(dest_summary.head(10).to_string())
            results_c["destinations"] = dest_summary

            # Try to map to provinces
            def guess_province(gemeente_name):
                g = str(gemeente_name).strip()
                if g in PROVINCE_CITY_MAP:
                    return PROVINCE_CITY_MAP[g]
                # Check if the name IS a province
                for prov in DUTCH_PROVINCES:
                    if prov.upper() in g.upper():
                        return prov
                return "Unknown"

            tussen_df["PROVINCE"] = tussen_df[dest_col].apply(guess_province)
            prov_summary = tussen_df.groupby("PROVINCE")["COUNT"].sum().sort_values(ascending=False)
            total_outflow = prov_summary.sum()
            prov_summary_df = pd.DataFrame({
                "DESTINATION_PROVINCE": prov_summary.index,
                "PERSONS_FROM_GRONINGEN": prov_summary.values,
                "PCT_OF_TOTAL_OUTFLOW": (prov_summary.values / total_outflow * 100).round(1),
            })

            # Mobility intensity
            intensities = []
            for _, row in prov_summary_df.iterrows():
                prov = row["DESTINATION_PROVINCE"]
                if prov in PROVINCE_POP and prov != "Groningen":
                    pct_flow = row["PCT_OF_TOTAL_OUTFLOW"] / 100
                    pct_pop = PROVINCE_POP[prov] / NL_TOTAL_POP
                    intensity = pct_flow / pct_pop if pct_pop > 0 else np.nan
                    intensities.append(round(intensity, 2))
                else:
                    intensities.append(np.nan)
            prov_summary_df["MOBILITY_INTENSITY"] = intensities

            results_c["province_destinations"] = prov_summary_df
            print(f"\n  ✅ Destination provinces:")
            print(prov_summary_df.to_string(index=False))
        else:
            print(f"  ⚠️ Could not find destination or count columns")
            print(f"     Columns: {list(tussen_df.columns)}")

    # Methodological note
    print(f"\n  Methodological note: Residential mobility data (BRP registrations) is used as")
    print(f"  a proxy for graduate labour market transitions. It captures all movers aged 25-30,")
    print(f"  not only graduates. Groningen has ~60,000 students out of ~235,000 residents —")
    print(f"  roughly 25% of all 25-30 year olds are likely students/recent graduates.")

    # Save output
    output_path = os.path.join(out_dir, "output_C_mobility_flows.csv")
    with open(output_path, "w") as f:
        write_csv_header(f, "CBS StatLine 60048ned (Verhuisde personen), CBS 81734NED (Tussen gemeenten)",
                         "All movers aged 25-30, not only graduates; BRP registration data")
        f.write("# Methodological note: This metric uses residential mobility data (BRP registrations)\n")
        f.write("# as a proxy for graduate labour market transitions. See output_DATA_QUALITY.txt.\n")
        for key, val in results_c.items():
            if isinstance(val, (pd.DataFrame, pd.Series)):
                f.write(f"\n# {key}\n")
                if isinstance(val, pd.Series):
                    val.to_csv(f)
                else:
                    val.to_csv(f, index=False)
    print(f"\n  ✅ Step 5 complete — saved to {output_path}")

    return results_c


# ---------------------------------------------------------------------------
# STEP 6: Analysis D — Match Analysis (OCW data)
# ---------------------------------------------------------------------------

def step6_analysis_d(loaded, out_dir):
    """Analyse STEM field match rates from OCW data."""
    print("\n" + "=" * 60)
    print("=== STEP 6: ANALYSIS D — MATCH ANALYSIS ===")
    print("=" * 60)

    results_d = {}
    ocw_fn = "OCW_arbeidsmarkt_WO_uitstromers.csv"
    ocw_df = loaded.get(ocw_fn)

    if ocw_df is None:
        print(f"  ❌ MATCH ANALYSIS SKIPPED — {ocw_fn} not found.")
        print(f"     This file would show whether STEM graduates work in STEM jobs.")
        print(f"     Download: ocwincijfers.nl → Hoger Onderwijs → Onderwijs en Arbeidsmarkt → CSV")
        note(f"Match analysis skipped: {ocw_fn} not available. Essential for mismatch argument.")
    else:
        print(f"\n  --- Processing {ocw_fn} ---")

        field_col = find_column(ocw_df, ["OPLEIDING", "STUDIERICHTING", "STUDIE", "FIELD",
                                          "Opleiding", "Opleidingsnaam"])
        employed_col = find_column(ocw_df, ["WERKZAAM", "EMPLOYED", "PCT_WERKZAAM",
                                             "% werkzaam", "Werkzaam"])
        match_col = find_column(ocw_df, ["AANSLUITING", "MATCH", "EIGEN_RICHTING",
                                          "Aansluiting", "eigen of verwant"])
        salary_col = find_column(ocw_df, ["SALARIS", "INKOMEN", "SALARY", "LOON",
                                           "Bruto maandloon", "Mediaan bruto"])

        if field_col:
            ocw_df["IS_STEM"] = ocw_df[field_col].apply(lambda x:
                any(kw in str(x).upper() for kw in
                    ["TECHNIEK", "NATUUR", "WISKUNDE", "INFORMATICA", "WERKTUIG",
                     "ELEKTRO", "SCHEIKUNDE", "BIOLOGIE", "FYSICA", "LANDBOUW",
                     "ENGINEERING", "COMPUTER", "ICT"]))
            ocw_df["TYPE"] = ocw_df["IS_STEM"].map({True: "STEM", False: "NonSTEM"})

            result_cols = [field_col, "TYPE"]
            if employed_col:
                ocw_df["PCT_EMPLOYED"] = clean_numeric(ocw_df[employed_col])
                result_cols.append("PCT_EMPLOYED")
            if match_col:
                ocw_df["PCT_FIELD_MATCH"] = clean_numeric(ocw_df[match_col])
                result_cols.append("PCT_FIELD_MATCH")
            if salary_col:
                ocw_df["AVG_SALARY"] = clean_numeric(ocw_df[salary_col])
                result_cols.append("AVG_SALARY")

            result_df = ocw_df[result_cols].dropna(subset=[field_col])
            results_d["match_by_field"] = result_df
            print(result_df.to_string(index=False))

            # Summary by STEM vs non-STEM
            if "PCT_FIELD_MATCH" in result_df.columns:
                summary = result_df.groupby("TYPE")["PCT_FIELD_MATCH"].mean()
                print(f"\n  Average field match rate:")
                print(f"    STEM: {fmt_pct(summary.get('STEM', np.nan))}")
                print(f"    Non-STEM: {fmt_pct(summary.get('NonSTEM', np.nan))}")
                diff = summary.get("STEM", 0) - summary.get("NonSTEM", 0)
                print(f"    Difference: {diff:+.1f} percentage points")
                results_d["stem_match_advantage"] = diff
        else:
            print(f"  ⚠️ Could not identify field/study column")
            print(f"     Columns: {list(ocw_df.columns)}")

    # Save output
    output_path = os.path.join(out_dir, "output_D_match_analysis.csv")
    with open(output_path, "w") as f:
        write_csv_header(f, "OCW arbeidsmarktkenmerken WO uitstromers",
                         "National data, not Groningen-specific")
        if results_d:
            for key, val in results_d.items():
                if isinstance(val, (pd.DataFrame, pd.Series)):
                    f.write(f"\n# {key}\n")
                    val.to_csv(f, index=False)
                else:
                    f.write(f"# {key}: {val}\n")
        else:
            f.write("# No data available — OCW file not found\n")
    print(f"\n  ✅ Step 6 complete — saved to {output_path}")

    return results_d


# ---------------------------------------------------------------------------
# STEP 7: Synthesis
# ---------------------------------------------------------------------------

def step7_synthesis(results_a, results_b, results_c, results_d, out_dir):
    """Produce the core academic argument connecting all analyses."""
    print("\n" + "=" * 60)
    print("=== STEP 7: CORE FINDING SYNTHESIS ===")
    print("=" * 60)

    lines = []
    lines.append("=" * 60)
    lines.append("CORE FINDING SYNTHESIS")
    lines.append(f"Generated: {generated_date}")
    lines.append("=" * 60)

    # 1. SUPPLY
    lines.append("\n1. SUPPLY (Analysis A):")
    for level in ["WO", "HBO"]:
        key = f"{level}_yearly"
        if key in results_a:
            df = results_a[key]
            stem_col = f"{level}_STEM_GRADS"
            pct_col = f"{level}_STEM_PCT"
            if stem_col in df.columns:
                latest = df[stem_col].iloc[-1] if len(df) > 0 else "N/A"
                lines.append(f"   {level} STEM graduates (latest year): {fmt_num(latest)}")
            if pct_col in df.columns:
                latest_pct = df[pct_col].iloc[-1] if len(df) > 0 else "N/A"
                lines.append(f"   {level} STEM share: {latest_pct}%")

                # Trend
                if len(df) >= 3:
                    values = df[pct_col].dropna()
                    if len(values) >= 3:
                        mean_val = values.mean()
                        std_val = values.std()
                        latest_val = values.iloc[-1]
                        if latest_val > mean_val + std_val:
                            trend = "growing (above 1 SD of mean)"
                        elif latest_val < mean_val - std_val:
                            trend = "declining (below 1 SD of mean)"
                        else:
                            trend = "stable (within 1 SD of mean)"
                        lines.append(f"   {level} STEM trend: {trend}")

    if not any(k.endswith("_yearly") for k in results_a):
        lines.append("   [Data not available — see output_DATA_QUALITY.txt]")

    # 2. DEMAND
    lines.append("\n2. DEMAND (Analysis B):")
    if "groningen_lq" in results_b:
        lines.append(f"   Groningen STEM LQ composite: {results_b['groningen_lq']} "
                     f"(national average = 1.0)")
        lines.append(f"   Groningen ranks #{results_b.get('groningen_rank', 'N/A')} "
                     f"out of {results_b.get('total_regions', 'N/A')} regions")

        if "lq" in results_b:
            top3 = results_b["lq"].head(3)
            for _, row in top3.iterrows():
                lines.append(f"   High-STEM region: {row['REGION']} "
                             f"(LQ={row['STEM_LQ_COMPOSITE']})")
        lines.append("   Implication: Groningen produces more STEM graduates than its "
                     "local economy can absorb")
    else:
        lines.append("   [LQ data not available — see output_DATA_QUALITY.txt]")

    if "lisa_stem_pct" in results_b:
        lines.append(f"   LISA cross-check: STEM jobs = {fmt_pct(results_b['lisa_stem_pct'])} "
                     f"of Groningen employment")

    # 3. MOBILITY
    lines.append("\n3. MOBILITY (Analysis C):")
    if "yearly_migration" in results_c:
        mig = results_c["yearly_migration"]
        avg_net = mig["NET_25_30"].mean()
        lines.append(f"   Average annual net outflow of 25-30 year olds: {fmt_num(abs(avg_net))}")
        lines.append(f"   Pattern consistent across {len(mig)} years")

        if "province_destinations" in results_c:
            dest = results_c["province_destinations"]
            top_dest = dest.iloc[0]
            lines.append(f"   Top destination: {top_dest['DESTINATION_PROVINCE']} "
                         f"({fmt_pct(top_dest['PCT_OF_TOTAL_OUTFLOW'])} of outflow)")

            # Check Noord-Brabant
            nb = dest[dest["DESTINATION_PROVINCE"] == "Noord-Brabant"]
            if len(nb) > 0 and not pd.isna(nb.iloc[0]["MOBILITY_INTENSITY"]):
                intensity = nb.iloc[0]["MOBILITY_INTENSITY"]
                lines.append(f"   Noord-Brabant mobility intensity: {intensity} "
                             f"({'overrepresented' if intensity > 1 else 'underrepresented'})")
    else:
        lines.append("   [Migration data not available — see output_DATA_QUALITY.txt]")

    # 4. CONNECTION
    lines.append("\n4. CONNECTION:")
    if "lq" in results_b and "province_destinations" in results_c:
        lines.append("   Cross-referencing LQ data with destination data suggests that")
        lines.append("   graduates disproportionately move to regions with higher STEM")
        lines.append("   industrial specialization. This supports the hypothesis that")
        lines.append("   regional industrial structure influences graduate settlement patterns.")
    else:
        lines.append("   [Full cross-reference requires both LQ and destination data]")
        lines.append("   Hypothesis for interview validation: STEM graduates move to regions")
        lines.append("   with higher STEM LQ (Noord-Brabant, Noord-Holland) because local")
        lines.append("   Groningen economy cannot absorb them.")

    # 5. MATCH
    if results_d:
        lines.append("\n5. MATCH (Analysis D):")
        if "stem_match_advantage" in results_d:
            lines.append(f"   STEM field match advantage: "
                         f"{results_d['stem_match_advantage']:+.1f} percentage points")

    synthesis_text = "\n".join(lines)
    print(synthesis_text)

    output_path = os.path.join(out_dir, "output_SYNTHESIS.txt")
    with open(output_path, "w") as f:
        f.write(synthesis_text)
    print(f"\n  ✅ Synthesis saved to {output_path}")

    return synthesis_text


# ---------------------------------------------------------------------------
# STEP 8: Data quality report
# ---------------------------------------------------------------------------

def step8_data_quality(missing_files, out_dir):
    """Write the data quality report."""
    print("\n" + "=" * 60)
    print("=== STEP 8: DATA QUALITY REPORT ===")
    print("=" * 60)

    output_path = os.path.join(out_dir, "output_DATA_QUALITY.txt")
    with open(output_path, "w") as f:
        f.write(f"DATA QUALITY AND LIMITATIONS REPORT\n")
        f.write(f"Generated: {generated_date}\n")
        f.write(f"{'=' * 60}\n\n")

        f.write("MISSING FILES:\n")
        if missing_files:
            for fn in missing_files:
                f.write(f"  ❌ {fn}\n")
        else:
            f.write("  ✅ All files present\n")

        f.write(f"\nDATA QUALITY NOTES ({len(data_quality_notes)} items):\n")
        for i, n in enumerate(data_quality_notes, 1):
            f.write(f"  {i}. {n}\n")

        f.write("\nSTANDARD CAVEATS:\n")
        f.write("  - Verhuisde personen data captures ALL movers aged 25-30, not only graduates\n")
        f.write("  - Groningen has ~60,000 students out of ~235,000 residents (~25% of 25-30 cohort)\n")
        f.write("  - DUO data uses academic years; CBS mobility uses calendar years (6-month offset)\n")
        f.write("  - COVID years 2020-2021 may show anomalous migration patterns\n")
        f.write("  - Pipeline dropout calculation is upper bound (no individual tracking)\n")
        f.write("  - SBI sector M includes consultancy alongside R&D/Engineering\n")
        f.write("  - Location Quotients based on establishment counts, not employment\n")
        f.write("  - This analysis should be triangulated with WO-Monitor alumni surveys\n")
        f.write("    and qualitative interview data\n")

        f.write("\nREPRESENTATIVENESS NOTE:\n")
        f.write("  The mobility data captures all residential moves registered in the BRP\n")
        f.write("  (Basisregistratie Personen) for the municipality of Groningen. The 25-30\n")
        f.write("  age group includes both graduates and non-graduates. Approximately 25%\n")
        f.write("  of Groningen's population consists of students, making this a reasonable\n")
        f.write("  but imperfect proxy for graduate mobility.\n")

    print(f"  ✅ Data quality report saved to {output_path}")


# ---------------------------------------------------------------------------
# STEP 10: Academic quality checks
# ---------------------------------------------------------------------------

def step10_quality_checks(results_a, results_b, results_c, results_d):
    """Run academic quality checks on outputs."""
    print("\n" + "=" * 60)
    print("=== STEP 10: ACADEMIC QUALITY CHECKS ===")
    print("=" * 60)

    # 1. Sample size check
    print("\n  1. Sample size check:")
    for key, df in results_a.items():
        if isinstance(df, pd.DataFrame):
            numeric_df = df.select_dtypes(include=[np.number])
            small = (numeric_df < 30) & (numeric_df > 0)
            if small.any().any():
                print(f"     ⚠️ {key}: contains cells with n < 30 — flag for caution")
                note(f"Small sample warning in {key}")
            else:
                print(f"     ✅ {key}: all cells have sufficient sample size")

    # 2. Trend direction check
    print("\n  2. Trend direction check:")
    for level in ["WO", "HBO"]:
        key = f"{level}_yearly"
        if key in results_a:
            df = results_a[key]
            for col in df.columns:
                if "PCT" in col:
                    values = df[col].dropna()
                    if len(values) >= 3:
                        mean_val = values.mean()
                        std_val = values.std()
                        latest = values.iloc[-1]
                        if latest > mean_val + std_val:
                            print(f"     📈 {col}: meaningful increase (latest={latest:.1f}, "
                                  f"mean={mean_val:.1f}, SD={std_val:.1f})")
                        elif latest < mean_val - std_val:
                            print(f"     📉 {col}: meaningful decrease")
                        else:
                            print(f"     ➡️ {col}: within noise range")

    # 3. Comparability check
    print("\n  3. Comparability check:")
    print("     ⚠️ DUO data uses academic years (Sep-Aug); CBS mobility uses calendar years (Jan-Dec)")
    print("     All year comparisons have an inherent 6-month offset")
    note("DUO academic year vs CBS calendar year: 6-month offset in all comparisons")

    # 4. Representativeness
    print("\n  4. Representativeness:")
    print("     Verhuisde personen data: ALL movers aged 25-30, not only RUG graduates")
    print("     Estimated student share of 25-30 cohort in Groningen: ~25%")

    # 5. Missing data / COVID
    print("\n  5. COVID year check:")
    print("     ⚠️ Years 2020-2021 may show anomalous patterns due to COVID-19")
    print("     Recommend: report separately or exclude from trend analysis")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Graduate Mobility Analysis — GEMRAMA")
    parser.add_argument("--data-dir", default=".",
                        help="Directory containing input data files (default: current directory)")
    parser.add_argument("--output-dir", default=".",
                        help="Directory for output files (default: current directory)")
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    out_dir = os.path.abspath(args.output_dir)

    print("=" * 60)
    print("GEMRAMA: Graduate Mobility & Regional Industrial Structure")
    print(f"Data directory: {data_dir}")
    print(f"Output directory: {out_dir}")
    print("=" * 60)

    # Step 0: File check
    found, missing = step0_file_check(data_dir)

    # Step 1: Inspect
    loaded = step1_inspect(found)

    # Step 2: STEM classification
    step2_stem_classification()

    # Step 3: Analysis A
    results_a = step3_analysis_a(loaded, out_dir)

    # Step 4: Analysis B
    results_b = step4_analysis_b(loaded, out_dir)

    # Step 5: Analysis C
    results_c = step5_analysis_c(loaded, out_dir)

    # Step 6: Analysis D
    results_d = step6_analysis_d(loaded, out_dir)

    # Step 7: Synthesis
    step7_synthesis(results_a, results_b, results_c, results_d, out_dir)

    # Step 8: Data quality
    step8_data_quality(missing, out_dir)

    # Step 10: Quality checks
    step10_quality_checks(results_a, results_b, results_c, results_d)

    # Final status
    print("\n" + "=" * 60)
    print("=== FINAL STATUS ===")
    print("=" * 60)

    if not missing:
        print("  ✅ Situation A: All files present, all analyses ran")
        print("  Next steps:")
        print("    1. Upload output_B_location_quotients.csv to ArcGIS for choropleth map")
        print("    2. Use output_C_mobility_flows.csv for flow map")
        print("    3. Use output_A_stem_pipeline_groningen.csv for time series charts")
        print("    4. The synthesis text goes into your academic appendix")
    elif len(missing) <= 3:
        print("  ⚠️ Situation B: Some files missing, partial analysis ran")
        print("  Check output_DATA_QUALITY.txt for missing files and download instructions")
        print("  Re-run after adding missing files")
    else:
        print("  ❌ Situation C: Many files missing")
        print("  Follow the download instructions in Step 0 output above")

    print(f"\n  Output files generated in: {out_dir}")
    for fn in ["output_A_stem_pipeline_groningen.csv",
               "output_B_location_quotients.csv",
               "output_C_mobility_flows.csv",
               "output_D_match_analysis.csv",
               "output_SYNTHESIS.txt",
               "output_DATA_QUALITY.txt"]:
        fp = os.path.join(out_dir, fn)
        status = "✅" if os.path.isfile(fp) else "⏳"
        print(f"    {status} {fn}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEMRAMA Assignment: Graduate Mobility & Regional Industrial Structure
=====================================================================
Research question: To what extent does regional industrial specialization
determine where university graduates settle after graduation, and does this
pattern differ between STEM and non-STEM fields?

RUG MSc Economic Geography 2025-2026
Supervised by dr. Femke Cnossen and dr. Viktor Venhorst

Usage:
    python graduate_mobility_analysis.py --data-dir "C:\\Users\\NL1E9O\\Downloads\\Regional Labour\\Input"
"""

import argparse
import os
import sys
import warnings
import glob as glob_module
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
# Configuration — file name mapping (actual names from your folder)
# ---------------------------------------------------------------------------
# Maps logical name -> list of possible actual filenames to search for
FILE_ALIASES = {
    "Inschrijvingen_WO": ["Inschrijvingen WO.csv", "Inschrijvingen_WO.csv"],
    "Inschrijvingen_HBO": ["Inschrijvingen HBO.csv", "Inschrijvingen_HBO.csv"],
    "Eerstejaars_WO": ["Eerstejaars WO.csv", "Eerstejaars_WO.csv"],
    "Eerstejaars_HBO": ["Eerstejaars HBO.csv", "Eerstejaars_HBO.csv"],
    "Gediplomeerden_WO": ["Gediplomeerden WO.csv", "Gediplomeerden_WO.csv"],
    "Gediplomeerden_HBO": ["Gediplomeerden HBO.csv", "Gediplomeerden_HBO.csv"],
    "Verhuisde_personen_regio": [
        "Verhuisde_personen__binnen_gemeenten__tussen_gemeenten_en_vanuit_het_buitenland.csv",
        "Verhuisde_personen_regio.csv",
        "Verhuisde personen regio.csv",
    ],
    "Vestigingen": [
        "Vestigingen_Bedrijven_Bedrijfstak.csv",
        "Vestigingen Bedrijven Bedrijfstak.csv",
    ],
    "LISA": [
        "LISA_Gemeenten_2024_data.xlsx",
        "LISA_Gemeenten_2024.xlsx",
        "LISA Gemeenten 2024.xlsx",
    ],
    "OCW": [
        "OCW_arbeidsmarkt_WO_uitstromers.csv",
        "OCW arbeidsmarkt WO uitstromers.csv",
    ],
}

# Tussen_gemeenten files are split by year
TUSSEN_PATTERN = "Tussen_gemeenten_verhuisde_personen_*.csv"

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

DUTCH_PROVINCES = [
    "Groningen", "Friesland", "Drenthe", "Overijssel", "Flevoland",
    "Gelderland", "Utrecht", "Noord-Holland", "Zuid-Holland",
    "Zeeland", "Noord-Brabant", "Limburg",
]

# Approximate province populations (2024)
PROVINCE_POP = {
    "Groningen": 596_000, "Friesland": 654_000, "Drenthe": 500_000,
    "Overijssel": 1_172_000, "Flevoland": 437_000, "Gelderland": 2_112_000,
    "Utrecht": 1_380_000, "Noord-Holland": 2_937_000, "Zuid-Holland": 3_750_000,
    "Zeeland": 387_000, "Noord-Brabant": 2_600_000, "Limburg": 1_118_000,
}
NL_TOTAL_POP = sum(PROVINCE_POP.values())

# Municipality -> Province mapping (extended)
GEMEENTE_PROVINCIE = {
    "Amsterdam": "Noord-Holland", "Rotterdam": "Zuid-Holland",
    "Den Haag": "Zuid-Holland", "'s-Gravenhage": "Zuid-Holland",
    "Utrecht": "Utrecht", "Eindhoven": "Noord-Brabant",
    "Tilburg": "Noord-Brabant", "Groningen": "Groningen",
    "Almere": "Flevoland", "Breda": "Noord-Brabant",
    "Nijmegen": "Gelderland", "Arnhem": "Gelderland",
    "Haarlem": "Noord-Holland", "Enschede": "Overijssel",
    "Apeldoorn": "Gelderland", "Amersfoort": "Utrecht",
    "Leiden": "Zuid-Holland", "Delft": "Zuid-Holland",
    "Maastricht": "Limburg", "Leeuwarden": "Friesland",
    "Zwolle": "Overijssel", "Assen": "Drenthe",
    "Middelburg": "Zeeland", "Lelystad": "Flevoland",
    "Emmen": "Drenthe", "Heerlen": "Limburg",
    "Venlo": "Limburg", "Deventer": "Overijssel",
    "Leidschendam-Voorburg": "Zuid-Holland", "Zoetermeer": "Zuid-Holland",
    "Dordrecht": "Zuid-Holland", "Hilversum": "Noord-Holland",
    "Zaanstad": "Noord-Holland", "Haarlemmermeer": "Noord-Holland",
    "Alphen aan den Rijn": "Zuid-Holland", "Roosendaal": "Noord-Brabant",
    "Oss": "Noord-Brabant", "Helmond": "Noord-Brabant",
    "'s-Hertogenbosch": "Noord-Brabant", "Sittard-Geleen": "Limburg",
    "Veenendaal": "Utrecht", "Ede": "Gelderland",
    "Wageningen": "Gelderland", "Harderwijk": "Gelderland",
    "Kampen": "Overijssel", "Hoogeveen": "Drenthe",
    "Stadskanaal": "Groningen", "Veendam": "Groningen",
    "Delfzijl": "Groningen", "Winschoten": "Groningen",
    "Eemsdelta": "Groningen", "Midden-Groningen": "Groningen",
    "Westerkwartier": "Groningen", "Het Hogeland": "Groningen",
    "Oldambt": "Groningen", "Pekela": "Groningen",
    "Westerwolde": "Groningen",
    "Smallingerland": "Friesland", "Heerenveen": "Friesland",
    "Sneek": "Friesland", "Sudwest-Fryslan": "Friesland",
    "Noardeast-Fryslan": "Friesland",
    "Meppel": "Drenthe", "Coevorden": "Drenthe",
    "Almelo": "Overijssel", "Hengelo": "Overijssel",
    "Hardenberg": "Overijssel",
    "Doetinchem": "Gelderland", "Tiel": "Gelderland",
    "Culemborg": "Gelderland", "Zutphen": "Gelderland",
    "Zeist": "Utrecht", "Nieuwegein": "Utrecht",
    "IJsselstein": "Utrecht", "Woerden": "Utrecht",
    "Alkmaar": "Noord-Holland", "Hoorn": "Noord-Holland",
    "Purmerend": "Noord-Holland", "Den Helder": "Noord-Holland",
    "Gouda": "Zuid-Holland", "Vlaardingen": "Zuid-Holland",
    "Schiedam": "Zuid-Holland", "Capelle aan den IJssel": "Zuid-Holland",
    "Goes": "Zeeland", "Terneuzen": "Zeeland", "Vlissingen": "Zeeland",
    "Bergen op Zoom": "Noord-Brabant", "Waalwijk": "Noord-Brabant",
    "Uden": "Noord-Brabant", "Meierijstad": "Noord-Brabant",
    "Roermond": "Limburg", "Weert": "Limburg", "Kerkrade": "Limburg",
    "Dronten": "Flevoland", "Noordoostpolder": "Flevoland",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
data_quality_notes = []
generated_date = datetime.now().strftime("%Y-%m-%d %H:%M")


def note(msg):
    data_quality_notes.append(msg)
    print(f"  [NOTE] {msg}")


def find_file(data_dir, key):
    """Find a file by its logical key, trying all aliases."""
    if key in FILE_ALIASES:
        for alias in FILE_ALIASES[key]:
            fp = os.path.join(data_dir, alias)
            if os.path.isfile(fp):
                return fp
    # Also try partial match on any file in the directory
    try:
        for fn in os.listdir(data_dir):
            if key.lower().replace("_", " ") in fn.lower().replace("_", " "):
                return os.path.join(data_dir, fn)
    except Exception:
        pass
    return None


def find_tussen_files(data_dir):
    """Find all Tussen_gemeenten files (split by year)."""
    pattern = os.path.join(data_dir, "Tussen_gemeenten*verhuisde*personen*.csv")
    files = sorted(glob_module.glob(pattern))
    if not files:
        # Try with spaces
        pattern = os.path.join(data_dir, "Tussen*gemeenten*verhuisde*personen*.csv")
        files = sorted(glob_module.glob(pattern))
    return files


def load_csv(filepath, name="file"):
    """Try loading a CSV with multiple separators and encodings."""
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        for sep in [";", ",", "\t"]:
            try:
                df = pd.read_csv(filepath, sep=sep, encoding=enc, low_memory=False)
                if len(df.columns) > 1:
                    df.columns = df.columns.str.strip()
                    print(f"  [OK] Loaded {name}: {len(df)} rows x {len(df.columns)} cols "
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
                        print(f"  [OK] Loaded {name}: {len(df)} rows x {len(df.columns)} cols "
                              f"(skipped {skip} header rows)")
                        note(f"{name}: skipped {skip} metadata header rows")
                        return df
                except Exception:
                    continue
    print(f"  [ERROR] PARSE ERROR: {name}")
    print(f"     Problem: Could not parse with any separator/encoding combination")
    print(f"     Fix: Open in Excel -> Save As -> CSV UTF-8 (comma delimited)")
    note(f"PARSE ERROR: {name} could not be loaded")
    return None


def load_excel(filepath, name="file"):
    """Load an Excel file."""
    try:
        # Try reading all sheets
        xls = pd.ExcelFile(filepath)
        print(f"  [OK] Excel file {name} has sheets: {xls.sheet_names}")
        df = pd.read_excel(filepath, sheet_name=0)
        df.columns = df.columns.str.strip()
        print(f"  [OK] Loaded {name} (sheet '{xls.sheet_names[0]}'): "
              f"{len(df)} rows x {len(df.columns)} cols")
        return df
    except Exception as e:
        print(f"  [ERROR] PARSE ERROR: {name}: {e}")
        note(f"PARSE ERROR: {name}: {e}")
        return None


def clean_numeric(series):
    """Clean Dutch-formatted numbers."""
    if series.dtype == object:
        s = series.astype(str).str.strip()
        s = s.replace({"": np.nan, ".": np.nan, "-": np.nan, "x": np.nan, "X": np.nan})
        if s.str.contains(",", na=False).any():
            s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        else:
            if s.str.match(r"^\d{1,3}(\.\d{3})+$", na=False).any():
                s = s.str.replace(".", "", regex=False)
        return pd.to_numeric(s, errors="coerce")
    return pd.to_numeric(series, errors="coerce")


def inspect_df(df, name):
    """Print inspection details."""
    print(f"\n  --- {name} ---")
    print(f"  Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"  Columns: {list(df.columns)}")
    for col in df.columns:
        cl = col.lower()
        if any(kw in cl for kw in ["regio", "sector", "jaar", "year", "opleiding",
                                     "onderdeel", "provincie", "instelling",
                                     "geslacht", "bedrijfstak", "gemeente"]):
            nuniq = df[col].nunique()
            if nuniq <= 30:
                vals = sorted(df[col].dropna().unique(), key=str)
                print(f"  {col} ({nuniq} unique): {vals}")
            else:
                print(f"  {col} ({nuniq} unique values)")


def find_column(df, candidates, partial=True):
    """Find first matching column from candidates list."""
    cols_upper = {c.upper().strip(): c for c in df.columns}
    for cand in candidates:
        cu = cand.upper().strip()
        if cu in cols_upper:
            return cols_upper[cu]
        if partial:
            for cup, creal in cols_upper.items():
                if cu in cup or cup in cu:
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
    if pd.isna(val):
        return "N/A"
    return f"{val:.1f}%"


def fmt_num(val):
    if pd.isna(val):
        return "N/A"
    return f"{val:,.0f}".replace(",", ".")


def safe_open(filepath, mode="w"):
    """Open file with UTF-8 encoding (avoids Windows cp1252 errors)."""
    return open(filepath, mode, encoding="utf-8")


def write_csv_header(f, sources, caveats=""):
    f.write(f"# Generated: {generated_date}\n")
    f.write(f"# Sources: {sources}\n")
    if caveats:
        f.write(f"# Caveats: {caveats}\n")


# ---------------------------------------------------------------------------
# STEP 0: File check
# ---------------------------------------------------------------------------
def step0_file_check(data_dir):
    print("\n" + "=" * 60)
    print("=== FILE STATUS CHECK ===")
    print("=" * 60)

    found = {}

    for key in FILE_ALIASES:
        fp = find_file(data_dir, key)
        if fp:
            fn = os.path.basename(fp)
            print(f"  [FOUND]   {key} -> {fn}")
            found[key] = fp
        else:
            print(f"  [MISSING] {key}")

    # Check Tussen files (split by year)
    tussen_files = find_tussen_files(data_dir)
    if tussen_files:
        print(f"  [FOUND]   Tussen_gemeenten -> {len(tussen_files)} year files:")
        for tf in tussen_files:
            print(f"            {os.path.basename(tf)}")
        found["Tussen"] = tussen_files
    else:
        print(f"  [MISSING] Tussen_gemeenten_verhuisde_personen files")

    missing_keys = [k for k in FILE_ALIASES if k not in found]
    if "Tussen" not in found:
        missing_keys.append("Tussen")

    if missing_keys:
        print("\n  === WHAT TO DO FOR MISSING FILES ===")
        instructions = {
            "Verhuisde_personen_regio": (
                "-> CBS StatLine: search '60048ned'\n"
                "     -> Select Gemeente = Groningen, all years, all age groups -> Download CSV"
            ),
            "Vestigingen": (
                "-> CBS StatLine -> dataset 81589NED\n"
                "     -> Select ALL provinces, all SBI sectors -> Download CSV"
            ),
            "LISA": "-> Obtain from course materials or LISA",
            "Tussen": (
                "-> CBS StatLine -> table 81734NED\n"
                "     -> Gemeente van vertrek = Groningen, all destinations, all years -> Download CSV"
            ),
            "OCW": (
                "-> ocwincijfers.nl -> Hoger Onderwijs -> Onderwijs en Arbeidsmarkt\n"
                "     -> 'Arbeidsmarktkenmerken uitstromers WO' -> download CSV"
            ),
        }
        for k in missing_keys:
            if k in instructions:
                print(f"\n  [MISSING] {k}")
                print(f"     {instructions[k]}")

    return found, missing_keys


# ---------------------------------------------------------------------------
# STEP 1: Inspect
# ---------------------------------------------------------------------------
def step1_inspect(found, data_dir):
    print("\n" + "=" * 60)
    print("=== STEP 1: INSPECT ALL FILES ===")
    print("=" * 60)

    loaded = {}
    for key, fp in found.items():
        if key == "Tussen":
            # Multiple files — load and concat
            dfs = []
            for tf in fp:
                df = load_csv(tf, os.path.basename(tf))
                if df is not None:
                    # Extract year from filename
                    bn = os.path.basename(tf)
                    for y in ["2021", "2022", "2023", "2024", "2020", "2019"]:
                        if y in bn:
                            df["FILE_YEAR"] = int(y)
                            break
                    dfs.append(df)
            if dfs:
                combined = pd.concat(dfs, ignore_index=True)
                loaded["Tussen"] = combined
                inspect_df(combined, "Tussen_gemeenten (combined)")
            continue

        if isinstance(fp, str):
            if fp.endswith((".xlsx", ".xls")):
                df = load_excel(fp, key)
            else:
                df = load_csv(fp, key)
            if df is not None:
                loaded[key] = df
                inspect_df(df, key)
                df.replace({"": np.nan, ".": np.nan}, inplace=True)

    return loaded


# ---------------------------------------------------------------------------
# STEP 2: STEM classification
# ---------------------------------------------------------------------------
def step2_stem_classification():
    print("\n" + "=" * 60)
    print("=== STEP 2: STEM CLASSIFICATION APPLIED ===")
    print("=" * 60)
    print(f"  DUO sectors classified as STEM: {', '.join(STEM_SECTORS_DUO)}")
    print(f"  SBI sectors classified as STEM:")
    for k, v in STEM_SBI.items():
        print(f"    {k}: {v}")
    print(f"  Non-STEM reference: ECONOMIE, GEDRAG_EN_MAATSCHAPPIJ, GEZONDHEIDSZORG, ONDERWIJS")
    print(f"  Note: SBI sector M includes consultancy and R&D -- included but flagged")
    note("SBI sector M includes both R&D/Engineering and management consultancy")


# ---------------------------------------------------------------------------
# STEP 3: Analysis A -- STEM Education Pipeline
# ---------------------------------------------------------------------------
def step3_analysis_a(loaded, out_dir):
    print("\n" + "=" * 60)
    print("=== STEP 3: ANALYSIS A -- STEM EDUCATION PIPELINE ===")
    print("=" * 60)

    results_a = {}

    for level in ["WO", "HBO"]:
        grad_key = f"Gediplomeerden_{level}"
        eerst_key = f"Eerstejaars_{level}"

        grad_df = loaded.get(grad_key)
        eerst_df = loaded.get(eerst_key)

        if grad_df is None:
            print(f"\n  [SKIP] {grad_key} not loaded -- skipping {level} graduate analysis")
            continue

        print(f"\n  --- Processing {grad_key} ---")

        # A1: Filter for Groningen institutions
        inst_col = find_column(grad_df, ["INSTELLINGSNAAM", "INSTELLING", "INSTELLINGNAAM",
                                          "INSTELLINGSNAAM ACTUEEL"])
        prov_col = find_column(grad_df, ["PROVINCIENAAM", "PROVINCIE",
                                          "PROVINCIE INSTELLING"])

        groningen_filter = None
        if inst_col:
            groningen_filter = grad_df[inst_col].astype(str).str.upper().str.contains(
                "GRONINGEN|RUG|RIJKSUNIVERSITEIT|HANZE", na=False)
            n_match = groningen_filter.sum()
            print(f"  Filtering on {inst_col}: {n_match}/{len(grad_df)} rows match Groningen")
        elif prov_col:
            groningen_filter = grad_df[prov_col].astype(str).str.upper().str.contains(
                "GRONINGEN", na=False)
            n_match = groningen_filter.sum()
            print(f"  Filtering on {prov_col}: {n_match}/{len(grad_df)} rows match Groningen")
        else:
            print(f"  [WARNING] Cannot filter on Groningen -- no institution/province column")
            print(f"     Columns present: {list(grad_df.columns)}")
            note(f"{grad_key}: no institution/province column, using full dataset")
            groningen_filter = pd.Series(True, index=grad_df.index)

        gdf = grad_df[groningen_filter].copy()

        if len(gdf) == 0:
            print(f"  [WARNING] No Groningen rows after filtering -- check column values")
            if inst_col:
                print(f"  Sample values in {inst_col}: {grad_df[inst_col].unique()[:10]}")
            continue

        # Find sector and year columns
        sector_col = find_column(gdf, ["CROHO ONDERDEEL", "ONDERDEEL", "SECTOR",
                                        "CROHO_ONDERDEEL", "ISCED"])
        year_col = find_column(gdf, ["JAAR", "YEAR", "ACADEMIEJAAR",
                                      "COLLEGEJAAR", "JAAR/YEAR"])

        # Find count columns -- DUO files typically have MAN and VROUW
        man_col = find_column(gdf, ["MAN", "MANNEN"])
        vrouw_col = find_column(gdf, ["VROUW", "VROUWEN"])
        total_col = find_column(gdf, ["TOTAAL", "AANTAL", "GEDIPLOMEERDEN",
                                       "TOTAAL GEDIPLOMEERDEN"])

        if sector_col is None:
            print(f"  [WARNING] No sector column found in {grad_key}")
            print(f"     Columns: {list(gdf.columns)}")
            note(f"{grad_key}: no sector column -- cannot classify STEM/non-STEM")
            continue

        print(f"  Sector column: {sector_col}")
        print(f"  Year column: {year_col}")
        print(f"  Unique sectors: {sorted(gdf[sector_col].dropna().unique(), key=str)}")

        # Classify STEM
        gdf["IS_STEM"] = gdf[sector_col].apply(is_stem_duo)
        stem_count = gdf["IS_STEM"].sum()
        print(f"  STEM rows: {stem_count} / {len(gdf)}")

        # Build COUNT column
        if man_col and vrouw_col:
            gdf["MEN_COUNT"] = clean_numeric(gdf[man_col])
            gdf["WOMEN_COUNT"] = clean_numeric(gdf[vrouw_col])
            gdf["COUNT"] = gdf["MEN_COUNT"].fillna(0) + gdf["WOMEN_COUNT"].fillna(0)
            print(f"  Count = {man_col} + {vrouw_col}")
        elif total_col:
            gdf["COUNT"] = clean_numeric(gdf[total_col])
            print(f"  Count column: {total_col}")
        else:
            gdf["COUNT"] = 1
            note(f"{grad_key}: no count column found, treating each row as 1")

        # A2: Annual STEM graduates
        if year_col:
            stem_yearly = gdf[gdf["IS_STEM"]].groupby(year_col)["COUNT"].sum()
            nonstem_yearly = gdf[~gdf["IS_STEM"]].groupby(year_col)["COUNT"].sum()

            yearly = pd.DataFrame({
                f"{level}_STEM_GRADS": stem_yearly,
                f"{level}_NONSTEM_GRADS": nonstem_yearly,
            }).fillna(0)
            total = yearly[f"{level}_STEM_GRADS"] + yearly[f"{level}_NONSTEM_GRADS"]
            yearly[f"{level}_STEM_PCT"] = (yearly[f"{level}_STEM_GRADS"] / total * 100).round(1)
            yearly.index.name = "YEAR"

            results_a[f"{level}_yearly"] = yearly
            print(f"\n  {level} annual STEM graduates:")
            print(yearly.to_string())
        else:
            print(f"  [WARNING] No year column -- cannot produce time series")

        # A3: Gender breakdown (latest year)
        if man_col and vrouw_col and year_col:
            latest_year = gdf[year_col].max()
            latest = gdf[gdf[year_col] == latest_year].copy()
            gender_summary = latest.groupby(sector_col).agg(
                MEN=("MEN_COUNT", "sum"),
                WOMEN=("WOMEN_COUNT", "sum"),
            ).reset_index()
            gender_summary["PCT_WOMEN"] = (
                gender_summary["WOMEN"] /
                (gender_summary["MEN"] + gender_summary["WOMEN"]) * 100
            ).round(1)
            gender_summary.insert(0, "YEAR", latest_year)
            results_a[f"{level}_gender"] = gender_summary
            print(f"\n  {level} gender breakdown ({latest_year}):")
            print(gender_summary.to_string(index=False))

        # A4: Pipeline leakage
        if eerst_df is not None and year_col:
            print(f"\n  --- Pipeline leakage: {eerst_key} vs {grad_key} ---")
            # Apply same Groningen filter
            e_inst_col = find_column(eerst_df, ["INSTELLINGSNAAM", "INSTELLING",
                                                  "INSTELLINGSNAAM ACTUEEL"])
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
            e_sector_col = find_column(edf, ["CROHO ONDERDEEL", "ONDERDEEL", "SECTOR"])
            e_year_col = find_column(edf, ["JAAR", "YEAR", "ACADEMIEJAAR", "COLLEGEJAAR"])
            e_man = find_column(edf, ["MAN", "MANNEN"])
            e_vrouw = find_column(edf, ["VROUW", "VROUWEN"])
            e_total = find_column(edf, ["TOTAAL", "AANTAL", "EERSTEJAARS"])

            if e_sector_col and e_year_col:
                edf["IS_STEM"] = edf[e_sector_col].apply(is_stem_duo)
                if e_man and e_vrouw:
                    edf["COUNT"] = clean_numeric(edf[e_man]).fillna(0) + clean_numeric(edf[e_vrouw]).fillna(0)
                elif e_total:
                    edf["COUNT"] = clean_numeric(edf[e_total])
                else:
                    edf["COUNT"] = 1

                e_yearly = edf[edf["IS_STEM"]].groupby(e_year_col)["COUNT"].sum()
                g_yearly = gdf[gdf["IS_STEM"]].groupby(year_col)["COUNT"].sum()

                offset = 4
                leakage_rows = []
                for yr in e_yearly.index:
                    try:
                        grad_yr = int(yr) + offset
                    except (ValueError, TypeError):
                        continue
                    # Check both int and string versions
                    g_val = None
                    for candidate in [grad_yr, str(grad_yr)]:
                        if candidate in g_yearly.index:
                            g_val = g_yearly[candidate]
                            break
                    if g_val is not None:
                        e_val = e_yearly[yr]
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
                    print(f"\n  {level} pipeline leakage:")
                    print(leak_df.to_string(index=False))
                    print("\n  Note: Upper bound estimate. Actual cohort tracking requires "
                          "CBS microdata.")
                else:
                    print(f"  [INFO] No matching cohort years for {offset}-year offset")
                    print(f"  First-year years: {sorted(e_yearly.index)}")
                    print(f"  Graduate years: {sorted(g_yearly.index)}")

    # Save
    output_path = os.path.join(out_dir, "output_A_stem_pipeline_groningen.csv")
    with safe_open(output_path) as f:
        write_csv_header(f, "DUO Gediplomeerden WO/HBO, Eerstejaars WO/HBO",
                         "Groningen institutions only; STEM classification as defined in Step 2")
        for key, df in results_a.items():
            f.write(f"\n# {key}\n")
            df.to_csv(f)
    print(f"\n  [OK] Step 3 complete -- saved to {output_path}")

    return results_a


# ---------------------------------------------------------------------------
# STEP 4: Analysis B -- Regional Industrial Structure
# ---------------------------------------------------------------------------
def step4_analysis_b(loaded, out_dir):
    print("\n" + "=" * 60)
    print("=== STEP 4: ANALYSIS B -- REGIONAL INDUSTRIAL STRUCTURE ===")
    print("=" * 60)

    results_b = {}

    vest_df = loaded.get("Vestigingen")
    if vest_df is None:
        print(f"  [SKIP] Vestigingen not loaded -- skipping LQ analysis")
        note("Location Quotient analysis skipped: Vestigingen file not available")
    else:
        print(f"\n  --- B1: Inspecting Vestigingen ---")

        regio_col = find_column(vest_df, ["REGIO", "REGIO'S", "REGIOS", "Regio's",
                                           "PROVINCIE", "COROP"])
        sector_col = find_column(vest_df, ["BEDRIJFSTAK", "BEDRIJFSTAKKEN",
                                            "Bedrijfstakken/branches SBI 2008",
                                            "Bedrijfstakken", "SBI", "BRANCHE"])
        count_col = find_column(vest_df, ["VESTIGINGEN", "AANTAL", "TOTAAL",
                                           "Vestigingen", "Bedrijven",
                                           "Totaal vestigingen"])

        if regio_col:
            regions = vest_df[regio_col].dropna().unique()
            print(f"  Region column: {regio_col}")
            print(f"  Regions ({len(regions)}): {sorted(regions, key=str)[:25]}")

            # Check provinces
            regions_upper = set(str(r).upper().strip() for r in regions)
            provinces_found = []
            for prov in DUTCH_PROVINCES:
                if any(prov.upper() in r for r in regions_upper):
                    provinces_found.append(prov)

            if len(provinces_found) < 6:
                print(f"\n  [INCOMPLETE] Only {len(provinces_found)} provinces found: {provinces_found}")
                print(f"     For LQ analysis you need ALL provinces.")
                print(f"     -> CBS StatLine -> dataset 81589NED -> Select ALL provinces")
                print(f"     Running Groningen-only descriptives instead.")
                note("LQ analysis incomplete: not all provinces in Vestigingen file")

                if sector_col and count_col:
                    gron_mask = vest_df[regio_col].astype(str).str.upper().str.contains(
                        "GRONINGEN", na=False)
                    gron = vest_df[gron_mask].copy()
                    gron["COUNT"] = clean_numeric(gron[count_col])
                    sector_summary = gron.groupby(sector_col)["COUNT"].sum().sort_values(ascending=False)
                    print(f"\n  Groningen establishments by sector:")
                    print(sector_summary.to_string())
                    results_b["groningen_sectors"] = sector_summary
            else:
                print(f"  [OK] Provinces present: {provinces_found}")

                if sector_col and count_col:
                    vest_df["COUNT"] = clean_numeric(vest_df[count_col])

                    sectors = vest_df[sector_col].dropna().unique()
                    print(f"\n  Sector column: {sector_col}")
                    print(f"  Sectors ({len(sectors)}):")
                    for s in sorted(sectors, key=str):
                        print(f"    {s}")

                    def classify_sbi_stem(sector_name):
                        s = str(sector_name).upper()
                        if any(kw in s for kw in ["INDUSTRIE", "MAAKINDUSTRIE", "NIJVERHEID"]):
                            if "VOEDINGS" not in s:
                                return "C"
                        if any(kw in s for kw in ["ENERGIE", "ELECTRICITEIT", "GAS"]):
                            return "D"
                        if any(kw in s for kw in ["INFORMATIE", "COMMUNICATIE", "ICT"]):
                            return "J"
                        if any(kw in s for kw in ["SPECIALISTISCH", "ZAKELIJK", "ADVIES",
                                                    "TECHNISCH", "WETENSCHAPPELIJK", "RESEARCH"]):
                            return "M"
                        return "OTHER"

                    vest_df["SBI_GROUP"] = vest_df[sector_col].apply(classify_sbi_stem)

                    # Show SBI mapping
                    print(f"\n  SBI classification applied:")
                    for sbi in ["C", "D", "J", "M"]:
                        mapped = vest_df[vest_df["SBI_GROUP"] == sbi][sector_col].unique()
                        if len(mapped) > 0:
                            print(f"    {sbi}: {list(mapped)}")

                    # LQ calculation
                    lq_rows = []
                    for region in vest_df[regio_col].dropna().unique():
                        region_data = vest_df[vest_df[regio_col] == region]
                        total_region = region_data["COUNT"].sum()
                        if total_region == 0 or pd.isna(total_region):
                            continue

                        total_national = vest_df["COUNT"].sum()
                        row = {"REGION": str(region).strip()}

                        for sbi_code, col_name in [("C", "LQ_Industrie_C"),
                                                     ("J", "LQ_ICT_J"),
                                                     ("M", "LQ_Zakelijk_M")]:
                            sector_region = region_data[
                                region_data["SBI_GROUP"] == sbi_code]["COUNT"].sum()
                            sector_national = vest_df[
                                vest_df["SBI_GROUP"] == sbi_code]["COUNT"].sum()

                            if total_national > 0 and sector_national > 0:
                                lq = ((sector_region / total_region) /
                                      (sector_national / total_national))
                                row[col_name] = round(lq, 2)
                            else:
                                row[col_name] = np.nan

                        lq_rows.append(row)

                    if lq_rows:
                        lq_df = pd.DataFrame(lq_rows)
                        lq_cols = [c for c in lq_df.columns if c.startswith("LQ_")]
                        lq_df["STEM_LQ_COMPOSITE"] = lq_df[lq_cols].mean(axis=1).round(2)
                        lq_df = lq_df.sort_values("STEM_LQ_COMPOSITE",
                                                    ascending=False).reset_index(drop=True)
                        lq_df.index += 1
                        lq_df.index.name = "RANK"

                        results_b["lq"] = lq_df
                        print(f"\n  Location Quotients (ranked):")
                        print(lq_df.to_string())

                        gron_rows = lq_df[lq_df["REGION"].str.upper().str.contains("GRONINGEN")]
                        if len(gron_rows) > 0:
                            gron_rank = gron_rows.index[0]
                            gron_lq = gron_rows["STEM_LQ_COMPOSITE"].values[0]
                            print(f"\n  Groningen: rank #{gron_rank}/{len(lq_df)}, "
                                  f"composite STEM LQ = {gron_lq}")
                            results_b["groningen_rank"] = gron_rank
                            results_b["groningen_lq"] = gron_lq
                            results_b["total_regions"] = len(lq_df)
        else:
            print(f"  [WARNING] No region column found")
            print(f"     Columns: {list(vest_df.columns)}")

    # B4: LISA
    lisa_df = loaded.get("LISA")
    if lisa_df is not None:
        print(f"\n  --- B4: LISA cross-check ---")
        print(f"  Columns: {list(lisa_df.columns)}")

        # LISA files often have gemeente as rows and sectors as columns
        # Try to find Groningen and sum STEM-related columns
        gemeente_col = find_column(lisa_df, ["GEMEENTE", "GEMEENTENAAM", "GM_NAAM",
                                              "Gemeente", "gemeente"])
        if gemeente_col:
            gron_mask = lisa_df[gemeente_col].astype(str).str.upper().str.contains(
                "GRONINGEN", na=False)
            gron_lisa = lisa_df[gron_mask]
            print(f"  Groningen rows: {len(gron_lisa)}")

            # Show all numeric columns for Groningen
            numeric_cols = gron_lisa.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                print(f"  Numeric columns ({len(numeric_cols)}):")
                for nc in numeric_cols:
                    val = gron_lisa[nc].sum()
                    if val > 0:
                        print(f"    {nc}: {fmt_num(val)}")
        else:
            # Maybe LISA has all data in rows with sector column
            print(f"  No gemeente column -- examining structure:")
            print(f"  First 5 rows:")
            print(lisa_df.head().to_string())
    else:
        print(f"\n  [SKIP] LISA file not loaded")

    # Save
    output_path = os.path.join(out_dir, "output_B_location_quotients.csv")
    with safe_open(output_path) as f:
        write_csv_header(f, "CBS Vestigingen, LISA Gemeenten 2024",
                         "SBI sector M includes consultancy")
        for key, val in results_b.items():
            if isinstance(val, (pd.DataFrame, pd.Series)):
                f.write(f"\n# {key}\n")
                if isinstance(val, pd.Series):
                    val.to_csv(f)
                else:
                    val.to_csv(f)
            else:
                f.write(f"# {key}: {val}\n")
    print(f"\n  [OK] Step 4 complete -- saved to {output_path}")

    return results_b


# ---------------------------------------------------------------------------
# STEP 5: Analysis C -- Mobility Flows
# ---------------------------------------------------------------------------
def step5_analysis_c(loaded, out_dir):
    print("\n" + "=" * 60)
    print("=== STEP 5: ANALYSIS C -- MOBILITY FLOWS ===")
    print("=" * 60)

    results_c = {}

    vh_df = loaded.get("Verhuisde_personen_regio")
    if vh_df is None:
        print(f"  [SKIP] Verhuisde_personen_regio not loaded")
        note("Mobility flow analysis skipped: file not available")
    else:
        print(f"\n  --- C1: Migration data ---")
        print(f"  Columns: {list(vh_df.columns)}")

        year_col = find_column(vh_df, ["PERIODEN", "JAAR", "YEAR", "Perioden"])
        regio_col = find_column(vh_df, ["REGIO", "REGIO'S", "Regio's"])

        # Look for age-specific columns
        vertrokken_cols = {}
        gevestigd_cols = {}

        for col in vh_df.columns:
            cl = col.lower()
            if "vertrok" in cl or "vertrek" in cl:
                if "20" in cl and ("25" in cl or "24" in cl):
                    vertrokken_cols["20_25"] = col
                elif "25" in cl and "30" in cl:
                    vertrokken_cols["25_30"] = col
            elif "gevestigd" in cl or "vestiging" in cl:
                if "20" in cl and ("25" in cl or "24" in cl):
                    gevestigd_cols["20_25"] = col
                elif "25" in cl and "30" in cl:
                    gevestigd_cols["25_30"] = col

        # Check if data has a long format with age column
        age_col = find_column(vh_df, ["LEEFTIJD", "LEEFTIJDSGROEP", "Leeftijd",
                                       "Leeftijdsgroep verhuisde persoon"])
        type_col = find_column(vh_df, ["MIGRATIE", "TYPE", "RICHTING",
                                        "Verhuisrichting", "Stromen",
                                        "Migratierichting"])
        count_col = find_column(vh_df, ["WAARDE", "VALUE", "AANTAL",
                                         "Verhuisde personen",
                                         "Verhuisde personen (aantal)"])

        if "25_30" in vertrokken_cols and "25_30" in gevestigd_cols:
            # Wide format with age columns
            print(f"  Found age-specific columns (wide format)")
            if regio_col:
                gron = vh_df[vh_df[regio_col].astype(str).str.upper().str.contains(
                    "GRONINGEN", na=False)].copy()
            else:
                gron = vh_df.copy()

            gron["V_25_30"] = clean_numeric(gron[vertrokken_cols["25_30"]])
            gron["G_25_30"] = clean_numeric(gron[gevestigd_cols["25_30"]])
            if "20_25" in vertrokken_cols:
                gron["V_20_25"] = clean_numeric(gron[vertrokken_cols["20_25"]])
                gron["G_20_25"] = clean_numeric(gron[gevestigd_cols.get("20_25", vertrokken_cols["20_25"])])
            else:
                gron["V_20_25"] = 0
                gron["G_20_25"] = 0

            gron["NET_20_25"] = gron["G_20_25"] - gron["V_20_25"]
            gron["NET_25_30"] = gron["G_25_30"] - gron["V_25_30"]

            if year_col:
                yearly_mig = gron.groupby(year_col).agg({
                    "G_20_25": "sum", "V_20_25": "sum", "NET_20_25": "sum",
                    "G_25_30": "sum", "V_25_30": "sum", "NET_25_30": "sum",
                }).reset_index()
                yearly_mig["RETENTION_25_30"] = (
                    yearly_mig["G_25_30"] /
                    (yearly_mig["G_25_30"] + yearly_mig["V_25_30"]) * 100
                ).round(1)
                results_c["yearly_migration"] = yearly_mig
                print(f"\n  Annual net migration:")
                print(yearly_mig.to_string(index=False))
        elif age_col:
            # Long format
            print(f"  Found age column: {age_col}")
            print(f"  Age groups: {vh_df[age_col].unique()}")

            if regio_col:
                gron = vh_df[vh_df[regio_col].astype(str).str.upper().str.contains(
                    "GRONINGEN", na=False)].copy()
            else:
                gron = vh_df.copy()

            if count_col:
                gron["VALUE"] = clean_numeric(gron[count_col])
            else:
                # Look for any numeric column
                for c in gron.columns:
                    if gron[c].dtype in [np.int64, np.float64]:
                        gron["VALUE"] = gron[c]
                        print(f"  Using '{c}' as value column")
                        break

            if "VALUE" in gron.columns:
                # Filter for relevant age groups
                age_vals = gron[age_col].astype(str)
                mask_20_25 = age_vals.str.contains("20.*25|20.*24", na=False, regex=True)
                mask_25_30 = age_vals.str.contains("25.*30|25.*29", na=False, regex=True)

                if mask_25_30.any():
                    print(f"  Age 25-30 rows: {mask_25_30.sum()}")
                    mig_25_30 = gron[mask_25_30]

                    if type_col:
                        print(f"  Migration types: {mig_25_30[type_col].unique()}")
                        # Try to identify inflow/outflow
                        for _, row in mig_25_30.head(10).iterrows():
                            print(f"    {row[type_col]}: {row['VALUE']}")

                    if year_col:
                        summary = mig_25_30.groupby(year_col)["VALUE"].sum()
                        print(f"\n  Values by year (age 25-30):")
                        print(summary.to_string())
                        results_c["migration_25_30"] = summary
                else:
                    print(f"  [WARNING] No rows matching age 25-30")
                    print(f"  Available age values: {sorted(gron[age_col].unique(), key=str)}")
        else:
            # Unknown format -- show all columns with samples
            print(f"  [WARNING] Cannot identify column structure automatically")
            print(f"  Showing all columns with sample values:")
            for col in vh_df.columns:
                sample = vh_df[col].dropna().head(3).tolist()
                print(f"    {col}: {sample}")
            note("Migration data: unknown column structure, manual inspection needed")

    # C4: Tussen gemeenten (destination analysis)
    tussen_df = loaded.get("Tussen")
    if tussen_df is None:
        print(f"\n  [SKIP] Destination analysis -- Tussen_gemeenten files not found")
        print(f"     Cannot show WHERE graduates go, only THAT they leave.")
        note("Destination analysis skipped: Tussen_gemeenten files not available")
    else:
        print(f"\n  --- C4: Destination analysis ---")
        print(f"  Combined Tussen_gemeenten: {len(tussen_df)} rows")
        print(f"  Columns: {list(tussen_df.columns)}")

        dest_col = find_column(tussen_df, ["BESTEMMING", "VESTIGINGSGEMEENTE",
                                            "GEMEENTE_VESTIGING", "Regio van vestiging",
                                            "Regio's (vestiging)", "REGIO"])
        count_col = find_column(tussen_df, ["AANTAL", "PERSONEN", "WAARDE",
                                             "Verhuisde personen",
                                             "Tussen gemeenten verhuisde personen (aantal)"])

        # Show sample for debugging
        print(f"  First 5 rows:")
        print(tussen_df.head().to_string())

        if dest_col and count_col:
            tussen_df["COUNT"] = clean_numeric(tussen_df[count_col])
            print(f"  Destination column: {dest_col}")
            print(f"  Count column: {count_col}")

            dest_summary = tussen_df.groupby(dest_col)["COUNT"].sum().sort_values(ascending=False)
            print(f"\n  Top 15 destinations:")
            print(dest_summary.head(15).to_string())
            results_c["destinations"] = dest_summary

            # Map to provinces
            def guess_province(gemeente_name):
                g = str(gemeente_name).strip()
                # Direct lookup
                if g in GEMEENTE_PROVINCIE:
                    return GEMEENTE_PROVINCIE[g]
                # Check if name is a province
                for prov in DUTCH_PROVINCES:
                    if prov.lower() in g.lower():
                        return prov
                # Check partial matches
                for gem, prov in GEMEENTE_PROVINCIE.items():
                    if gem.lower() in g.lower() or g.lower() in gem.lower():
                        return prov
                return "Overig/Onbekend"

            tussen_df["PROVINCE"] = tussen_df[dest_col].apply(guess_province)

            unknown = tussen_df[tussen_df["PROVINCE"] == "Overig/Onbekend"]
            if len(unknown) > 0:
                unknown_dests = unknown[dest_col].unique()
                print(f"\n  [NOTE] {len(unknown_dests)} destinations not mapped to province:")
                for d in sorted(unknown_dests, key=str)[:20]:
                    print(f"    {d}")
                note(f"{len(unknown_dests)} destination municipalities not mapped to province")

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
            print(f"\n  Destination provinces:")
            print(prov_summary_df.to_string(index=False))

            # Year breakdown if available
            if "FILE_YEAR" in tussen_df.columns:
                year_prov = tussen_df.groupby(["FILE_YEAR", "PROVINCE"])["COUNT"].sum().unstack(
                    fill_value=0)
                print(f"\n  Destinations by year:")
                print(year_prov.to_string())
                results_c["yearly_destinations"] = year_prov
        else:
            print(f"  [WARNING] Could not identify destination or count columns")
            print(f"  Attempting to find correct columns from data sample...")
            # Show all columns and their types
            for col in tussen_df.columns:
                print(f"    {col} ({tussen_df[col].dtype}): {tussen_df[col].head(3).tolist()}")

    # Methodological note
    print(f"\n  Methodological note:")
    print(f"  - Uses residential mobility data (BRP) as proxy for graduate transitions")
    print(f"  - Captures all movers aged 25-30, not only graduates")
    print(f"  - ~25% of Groningen 25-30 cohort are students/recent graduates")
    print(f"  - Should be triangulated with WO-Monitor alumni surveys")

    # Save
    output_path = os.path.join(out_dir, "output_C_mobility_flows.csv")
    with safe_open(output_path) as f:
        write_csv_header(f, "CBS 60048ned, CBS 81734NED (Tussen gemeenten)",
                         "All movers, not only graduates; BRP data")
        for key, val in results_c.items():
            if isinstance(val, (pd.DataFrame, pd.Series)):
                f.write(f"\n# {key}\n")
                if isinstance(val, pd.Series):
                    val.to_csv(f)
                else:
                    val.to_csv(f, index=False)
    print(f"\n  [OK] Step 5 complete -- saved to {output_path}")

    return results_c


# ---------------------------------------------------------------------------
# STEP 6: Analysis D -- Match Analysis
# ---------------------------------------------------------------------------
def step6_analysis_d(loaded, out_dir):
    print("\n" + "=" * 60)
    print("=== STEP 6: ANALYSIS D -- MATCH ANALYSIS ===")
    print("=" * 60)

    results_d = {}
    ocw_df = loaded.get("OCW")

    if ocw_df is None:
        print(f"  [SKIP] OCW file not found -- match analysis skipped")
        print(f"     Download from: ocwincijfers.nl -> Hoger Onderwijs -> Arbeidsmarkt -> CSV")
        note("Match analysis skipped: OCW file not available")
    else:
        print(f"\n  Processing OCW data...")
        print(f"  Columns: {list(ocw_df.columns)}")

        field_col = find_column(ocw_df, ["OPLEIDING", "STUDIERICHTING", "STUDIE",
                                          "Opleiding", "Opleidingsnaam"])
        employed_col = find_column(ocw_df, ["WERKZAAM", "% werkzaam", "Werkzaam"])
        match_col = find_column(ocw_df, ["AANSLUITING", "MATCH", "eigen of verwant",
                                          "Aansluiting"])
        salary_col = find_column(ocw_df, ["SALARIS", "Bruto maandloon", "Mediaan bruto"])

        if field_col:
            ocw_df["IS_STEM"] = ocw_df[field_col].apply(lambda x:
                any(kw in str(x).upper() for kw in
                    ["TECHNIEK", "NATUUR", "WISKUNDE", "INFORMATICA", "WERKTUIG",
                     "ELEKTRO", "SCHEIKUNDE", "BIOLOGIE", "ENGINEERING", "ICT"]))
            ocw_df["TYPE"] = ocw_df["IS_STEM"].map({True: "STEM", False: "NonSTEM"})

            cols_to_show = [field_col, "TYPE"]
            if employed_col:
                ocw_df["PCT_EMPLOYED"] = clean_numeric(ocw_df[employed_col])
                cols_to_show.append("PCT_EMPLOYED")
            if match_col:
                ocw_df["PCT_FIELD_MATCH"] = clean_numeric(ocw_df[match_col])
                cols_to_show.append("PCT_FIELD_MATCH")
            if salary_col:
                ocw_df["AVG_SALARY"] = clean_numeric(ocw_df[salary_col])
                cols_to_show.append("AVG_SALARY")

            result_df = ocw_df[cols_to_show].dropna(subset=[field_col])
            results_d["match_by_field"] = result_df
            print(result_df.to_string(index=False))

            if "PCT_FIELD_MATCH" in result_df.columns:
                summary = result_df.groupby("TYPE")["PCT_FIELD_MATCH"].mean()
                print(f"\n  Average field match rate:")
                for t, v in summary.items():
                    print(f"    {t}: {fmt_pct(v)}")
                diff = summary.get("STEM", 0) - summary.get("NonSTEM", 0)
                print(f"    Difference: {diff:+.1f} pp")
                results_d["stem_match_advantage"] = diff

    output_path = os.path.join(out_dir, "output_D_match_analysis.csv")
    with safe_open(output_path) as f:
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
            f.write("# No data available -- OCW file not found\n")
    print(f"\n  [OK] Step 6 complete -- saved to {output_path}")

    return results_d


# ---------------------------------------------------------------------------
# STEP 7: Synthesis
# ---------------------------------------------------------------------------
def step7_synthesis(results_a, results_b, results_c, results_d, out_dir):
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
    has_supply = False
    for level in ["WO", "HBO"]:
        key = f"{level}_yearly"
        if key in results_a:
            has_supply = True
            df = results_a[key]
            stem_col = f"{level}_STEM_GRADS"
            pct_col = f"{level}_STEM_PCT"
            if stem_col in df.columns and len(df) > 0:
                latest = df[stem_col].iloc[-1]
                lines.append(f"   {level} STEM graduates (latest year): {fmt_num(latest)}")
            if pct_col in df.columns and len(df) > 0:
                latest_pct = df[pct_col].iloc[-1]
                lines.append(f"   {level} STEM share: {latest_pct}%")
                if len(df) >= 3:
                    values = df[pct_col].dropna()
                    mean_val = values.mean()
                    std_val = values.std() if len(values) > 1 else 0
                    latest_val = values.iloc[-1]
                    if std_val > 0 and latest_val > mean_val + std_val:
                        trend = "growing"
                    elif std_val > 0 and latest_val < mean_val - std_val:
                        trend = "declining"
                    else:
                        trend = "stable"
                    lines.append(f"   {level} trend: {trend}")
    if not has_supply:
        lines.append("   [Data not available]")

    # 2. DEMAND
    lines.append("\n2. DEMAND (Analysis B):")
    if "groningen_lq" in results_b:
        lines.append(f"   Groningen STEM LQ composite: {results_b['groningen_lq']} "
                     f"(national average = 1.0)")
        lines.append(f"   Groningen ranks #{results_b.get('groningen_rank', '?')} "
                     f"of {results_b.get('total_regions', '?')} regions")
        if results_b['groningen_lq'] < 1.0:
            lines.append("   -> Groningen is UNDER-specialized in STEM industries")
            lines.append("   -> Local economy cannot absorb all STEM graduates")
        elif results_b['groningen_lq'] > 1.2:
            lines.append("   -> Groningen is specialized in STEM industries")
        if "lq" in results_b:
            top3 = results_b["lq"].head(3)
            lines.append("   Top STEM regions:")
            for _, row in top3.iterrows():
                lines.append(f"     {row['REGION']}: LQ={row['STEM_LQ_COMPOSITE']}")
    else:
        lines.append("   [LQ data not available]")

    # 3. MOBILITY
    lines.append("\n3. MOBILITY (Analysis C):")
    if "yearly_migration" in results_c:
        mig = results_c["yearly_migration"]
        avg_net = mig["NET_25_30"].mean()
        lines.append(f"   Avg annual net flow 25-30: {fmt_num(avg_net)} (negative = outflow)")
        lines.append(f"   Pattern spans {len(mig)} years")
    if "province_destinations" in results_c:
        dest = results_c["province_destinations"]
        valid_dest = dest[dest["DESTINATION_PROVINCE"] != "Overig/Onbekend"]
        if len(valid_dest) > 0:
            top = valid_dest.iloc[0]
            lines.append(f"   Top destination: {top['DESTINATION_PROVINCE']} "
                         f"({fmt_pct(top['PCT_OF_TOTAL_OUTFLOW'])})")
            nb = valid_dest[valid_dest["DESTINATION_PROVINCE"] == "Noord-Brabant"]
            if len(nb) > 0 and not pd.isna(nb.iloc[0]["MOBILITY_INTENSITY"]):
                intens = nb.iloc[0]["MOBILITY_INTENSITY"]
                lines.append(f"   Noord-Brabant intensity: {intens} "
                             f"({'overrepresented' if intens > 1 else 'proportional'})")
    if "yearly_migration" not in results_c and "province_destinations" not in results_c:
        lines.append("   [Migration data not available]")

    # 4. CONNECTION
    lines.append("\n4. CONNECTION:")
    if "lq" in results_b and "province_destinations" in results_c:
        lines.append("   Cross-referencing LQ and destination data suggests graduates")
        lines.append("   disproportionately move to high-STEM-LQ regions.")
    else:
        lines.append("   Hypothesis: STEM graduates move to high-STEM-LQ regions")
        lines.append("   (validate with interview data and WO-Monitor surveys)")

    if results_d and "stem_match_advantage" in results_d:
        lines.append(f"\n5. MATCH (Analysis D):")
        lines.append(f"   STEM field match advantage: "
                     f"{results_d['stem_match_advantage']:+.1f} pp")

    synthesis_text = "\n".join(lines)
    print(synthesis_text)

    output_path = os.path.join(out_dir, "output_SYNTHESIS.txt")
    with safe_open(output_path) as f:
        f.write(synthesis_text)
    print(f"\n  [OK] Synthesis saved to {output_path}")
    return synthesis_text


# ---------------------------------------------------------------------------
# STEP 8 + 10: Data quality + Academic checks
# ---------------------------------------------------------------------------
def step8_data_quality(missing_keys, out_dir):
    print("\n" + "=" * 60)
    print("=== DATA QUALITY REPORT ===")
    print("=" * 60)

    output_path = os.path.join(out_dir, "output_DATA_QUALITY.txt")
    with safe_open(output_path) as f:
        f.write("DATA QUALITY AND LIMITATIONS REPORT\n")
        f.write(f"Generated: {generated_date}\n")
        f.write("=" * 60 + "\n\n")

        f.write("MISSING FILES:\n")
        if missing_keys:
            for k in missing_keys:
                f.write(f"  - {k}\n")
        else:
            f.write("  All files present\n")

        f.write(f"\nDATA QUALITY NOTES ({len(data_quality_notes)} items):\n")
        for i, n in enumerate(data_quality_notes, 1):
            f.write(f"  {i}. {n}\n")

        f.write("\nSTANDARD CAVEATS:\n")
        caveats = [
            "Verhuisde personen data captures ALL movers aged 25-30, not only graduates",
            "Groningen has ~60,000 students / ~235,000 residents (~25% of 25-30 cohort)",
            "DUO uses academic years (Sep-Aug); CBS mobility uses calendar years (6-month offset)",
            "COVID years 2020-2021 may show anomalous migration patterns",
            "Pipeline dropout rate is upper bound (no individual-level tracking)",
            "SBI sector M includes consultancy alongside R&D/Engineering",
            "Location Quotients based on establishment counts, not employment",
            "Should be triangulated with WO-Monitor alumni surveys and interview data",
        ]
        for c in caveats:
            f.write(f"  - {c}\n")

        f.write("\nREPRESENTATIVENESS:\n")
        f.write("  The mobility data captures all residential moves registered in the BRP\n")
        f.write("  for Groningen. The 25-30 age group includes both graduates and\n")
        f.write("  non-graduates. Approx 25% of Groningen's population are students,\n")
        f.write("  making this a reasonable but imperfect proxy for graduate mobility.\n")

    for c in caveats[:3]:
        print(f"  - {c}")
    print(f"  [OK] Full report saved to {output_path}")


def step10_quality_checks(results_a, results_b, results_c, results_d):
    print("\n" + "=" * 60)
    print("=== ACADEMIC QUALITY CHECKS ===")
    print("=" * 60)

    # Sample size
    print("\n  1. Sample size check:")
    for key, df in results_a.items():
        if isinstance(df, pd.DataFrame):
            numeric_df = df.select_dtypes(include=[np.number])
            small = (numeric_df < 30) & (numeric_df > 0)
            if small.any().any():
                print(f"     [!] {key}: contains cells with n < 30")
                note(f"Small sample warning: {key}")
            else:
                print(f"     [OK] {key}: sufficient sample sizes")

    # Trend
    print("\n  2. Trend direction:")
    for level in ["WO", "HBO"]:
        key = f"{level}_yearly"
        if key in results_a:
            df = results_a[key]
            pct_col = f"{level}_STEM_PCT"
            if pct_col in df.columns:
                values = df[pct_col].dropna()
                if len(values) >= 3:
                    m, s = values.mean(), values.std()
                    latest = values.iloc[-1]
                    if s > 0 and latest > m + s:
                        print(f"     {pct_col}: meaningful increase")
                    elif s > 0 and latest < m - s:
                        print(f"     {pct_col}: meaningful decrease")
                    else:
                        print(f"     {pct_col}: within noise range")

    print("\n  3. Year comparability: DUO academic years vs CBS calendar years (6-month offset)")
    print("  4. Representativeness: mobility data = all movers 25-30, not only graduates")
    print("  5. COVID: years 2020-2021 may be anomalous -- recommend separate reporting")
    note("Academic year vs calendar year: 6-month offset in all comparisons")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Graduate Mobility Analysis -- GEMRAMA")
    parser.add_argument("--data-dir", default=None,
                        help="Directory containing input data files")
    parser.add_argument("--output-dir", default=None,
                        help="Directory for output files (defaults to data-dir)")
    args = parser.parse_args()

    # Default: use the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(args.data_dir) if args.data_dir else script_dir
    out_dir = os.path.abspath(args.output_dir) if args.output_dir else data_dir

    print("=" * 60)
    print("GEMRAMA: Graduate Mobility & Regional Industrial Structure")
    print(f"Data directory: {data_dir}")
    print(f"Output directory: {out_dir}")
    print("=" * 60)

    # List actual files in data directory
    print(f"\nFiles in data directory:")
    try:
        for fn in sorted(os.listdir(data_dir)):
            if fn.endswith((".csv", ".xlsx", ".xls")):
                size = os.path.getsize(os.path.join(data_dir, fn))
                print(f"  {fn} ({size:,} bytes)")
    except Exception as e:
        print(f"  [ERROR] Cannot list directory: {e}")

    found, missing = step0_file_check(data_dir)
    loaded = step1_inspect(found, data_dir)
    step2_stem_classification()
    results_a = step3_analysis_a(loaded, out_dir)
    results_b = step4_analysis_b(loaded, out_dir)
    results_c = step5_analysis_c(loaded, out_dir)
    results_d = step6_analysis_d(loaded, out_dir)
    step7_synthesis(results_a, results_b, results_c, results_d, out_dir)
    step8_data_quality(missing, out_dir)
    step10_quality_checks(results_a, results_b, results_c, results_d)

    # Final status
    print("\n" + "=" * 60)
    print("=== FINAL STATUS ===")
    print("=" * 60)

    if not missing:
        print("  Situation A: All files present, all analyses ran")
    elif len(missing) <= 3:
        print("  Situation B: Some files missing, partial analysis ran")
        print("  Check output_DATA_QUALITY.txt for details")
    else:
        print("  Situation C: Many files missing")
        print("  Follow download instructions above")

    print(f"\n  Output files in: {out_dir}")
    for fn in ["output_A_stem_pipeline_groningen.csv",
               "output_B_location_quotients.csv",
               "output_C_mobility_flows.csv",
               "output_D_match_analysis.csv",
               "output_SYNTHESIS.txt",
               "output_DATA_QUALITY.txt"]:
        fp = os.path.join(out_dir, fn)
        status = "[OK]" if os.path.isfile(fp) else "[--]"
        print(f"    {status} {fn}")


if __name__ == "__main__":
    main()

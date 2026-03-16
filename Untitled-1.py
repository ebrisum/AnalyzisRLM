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

Usage: Place this script in the same folder as your data files and run:
    python graduate_mobility_analysis.py
Or specify data directory:
    python graduate_mobility_analysis.py --data-dir "C:\\path\\to\\data"
"""

import argparse
import os
import sys
import warnings
import glob as glob_module
from datetime import datetime

import pandas as pd
import numpy as np

# Force UTF-8 output on Windows (fixes cp1252 crash)
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
# Configuration
# ---------------------------------------------------------------------------

# Maps logical name -> list of possible filenames (tried in order)
FILE_ALIASES = {
    "Inschrijvingen_WO": ["Inschrijvingen WO.csv", "Inschrijvingen_WO.csv"],
    "Inschrijvingen_HBO": ["Inschrijvingen HBO.csv", "Inschrijvingen_HBO.csv"],
    "Eerstejaars_WO": ["Eerstejaars WO.csv", "Eerstejaars_WO.csv"],
    "Eerstejaars_HBO": ["Eerstejaars HBO.csv", "Eerstejaars_HBO.csv"],
    "Gediplomeerden_WO": ["Gediplomeerden WO.csv", "Gediplomeerden_WO.csv"],
    "Gediplomeerden_HBO": ["Gediplomeerden HBO.csv", "Gediplomeerden_HBO.csv"],
    "Verhuisde_personen_regio": [],  # matched by partial name below
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

STEM_SECTORS_DUO = [
    "TECHNIEK", "NATUUR", "LANDBOUW_EN_NATUURLIJKE_OMGEVING",
    "LANDBOUW EN NATUURLIJKE OMGEVING", "INFORMATICA",
]

STEM_SBI = {
    "C": "Industrie (Maakindustrie)",
    "D": "Energievoorziening",
    "J": "Informatie en communicatie (ICT)",
    "M": "Specialistische zakelijke diensten (R&D/Engineering)",
}

# LISA sector -> STEM classification
LISA_STEM_SECTORS = {
    "L02. Industrie": "C",
    "L03. Nutsbedrijven": "D",
    "L08. Informatie en Communicatie": "J",
    "L10. Zakelijke diensten": "M",
}

DUTCH_PROVINCES = [
    "Groningen", "Friesland", "Frysl\u00e2n", "Drenthe", "Overijssel",
    "Flevoland", "Gelderland", "Utrecht", "Noord-Holland", "Zuid-Holland",
    "Zeeland", "Noord-Brabant", "Limburg",
]

# Map LISA province names to standard names
PROVINCE_NORMALIZE = {
    "Frysl\u00e2n": "Friesland",
}

# Approximate province populations (2024)
PROVINCE_POP = {
    "Groningen": 596_000, "Friesland": 654_000, "Drenthe": 500_000,
    "Overijssel": 1_172_000, "Flevoland": 437_000, "Gelderland": 2_112_000,
    "Utrecht": 1_380_000, "Noord-Holland": 2_937_000, "Zuid-Holland": 3_750_000,
    "Zeeland": 387_000, "Noord-Brabant": 2_600_000, "Limburg": 1_118_000,
}
NL_TOTAL_POP = sum(PROVINCE_POP.values())

# Extended gemeente -> province mapping
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
    "Zoetermeer": "Zuid-Holland", "Dordrecht": "Zuid-Holland",
    "Hilversum": "Noord-Holland", "Zaanstad": "Noord-Holland",
    "Haarlemmermeer": "Noord-Holland", "Roosendaal": "Noord-Brabant",
    "Oss": "Noord-Brabant", "Helmond": "Noord-Brabant",
    "'s-Hertogenbosch": "Noord-Brabant", "Sittard-Geleen": "Limburg",
    "Ede": "Gelderland", "Wageningen": "Gelderland",
    "Almelo": "Overijssel", "Hengelo": "Overijssel",
    "Gouda": "Zuid-Holland", "Alkmaar": "Noord-Holland",
    "Bergen op Zoom": "Noord-Brabant", "Roermond": "Limburg",
    "Leidschendam-Voorburg": "Zuid-Holland", "Capelle aan den IJssel": "Zuid-Holland",
    "Vlaardingen": "Zuid-Holland", "Schiedam": "Zuid-Holland",
    "Goes": "Zeeland", "Terneuzen": "Zeeland", "Vlissingen": "Zeeland",
    "Dronten": "Flevoland", "Noordoostpolder": "Flevoland",
    "Hoogeveen": "Drenthe", "Meppel": "Drenthe", "Coevorden": "Drenthe",
    "Stadskanaal": "Groningen", "Veendam": "Groningen",
    "Eemsdelta": "Groningen", "Midden-Groningen": "Groningen",
    "Westerkwartier": "Groningen", "Het Hogeland": "Groningen",
    "Oldambt": "Groningen", "Pekela": "Groningen",
    "Westerwolde": "Groningen",
    "Smallingerland": "Friesland", "Heerenveen": "Friesland",
    "S\u00fadwest-Frysl\u00e2n": "Friesland",
    "Doetinchem": "Gelderland", "Zutphen": "Gelderland",
    "Zeist": "Utrecht", "Nieuwegein": "Utrecht", "Woerden": "Utrecht",
    "Purmerend": "Noord-Holland", "Den Helder": "Noord-Holland",
    "Meierijstad": "Noord-Brabant", "Waalwijk": "Noord-Brabant",
    "Weert": "Limburg", "Kerkrade": "Limburg",
    "Hardenberg": "Overijssel", "Kampen": "Overijssel",
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
    """Find a file by logical key, trying aliases then partial match."""
    if key in FILE_ALIASES:
        for alias in FILE_ALIASES[key]:
            fp = os.path.join(data_dir, alias)
            if os.path.isfile(fp):
                return fp
    # Partial match on any file in directory
    try:
        key_words = key.lower().replace("_", " ").split()
        for fn in os.listdir(data_dir):
            fn_lower = fn.lower().replace("_", " ")
            if all(w in fn_lower for w in key_words):
                return os.path.join(data_dir, fn)
    except Exception:
        pass
    return None


def find_tussen_files(data_dir):
    """Find all Tussen_gemeenten year files."""
    pattern = os.path.join(data_dir, "Tussen_gemeenten*verhuisde*personen*.csv")
    files = sorted(glob_module.glob(pattern))
    if not files:
        pattern = os.path.join(data_dir, "Tussen*gemeenten*verhuisde*personen*.csv")
        files = sorted(glob_module.glob(pattern))
    return files


def load_csv(filepath, name="file"):
    """Load CSV trying multiple encodings and separators."""
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
    # Try skipping CBS metadata headers
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
                        return df
                except Exception:
                    continue
    print(f"  [ERROR] Cannot parse {name}")
    note(f"PARSE ERROR: {name}")
    return None


def load_excel(filepath, name="file"):
    try:
        xls = pd.ExcelFile(filepath)
        print(f"  [OK] Excel {name}: sheets = {xls.sheet_names}")
        df = pd.read_excel(filepath, sheet_name=0)
        df.columns = df.columns.str.strip()
        print(f"  [OK] Loaded {name}: {len(df)} rows x {len(df.columns)} cols")
        return df
    except Exception as e:
        print(f"  [ERROR] {name}: {e}")
        note(f"PARSE ERROR: {name}: {e}")
        return None


def clean_numeric(series):
    """Clean Dutch-formatted numbers."""
    if series.dtype == object:
        s = series.astype(str).str.strip()
        s = s.replace({"": np.nan, ".": np.nan, "-": np.nan, "x": np.nan})
        if s.str.contains(",", na=False).any():
            s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        elif s.str.match(r"^\d{1,3}(\.\d{3})+$", na=False).any():
            s = s.str.replace(".", "", regex=False)
        return pd.to_numeric(s, errors="coerce")
    return pd.to_numeric(series, errors="coerce")


def inspect_df(df, name):
    print(f"\n  --- {name} ---")
    print(f"  Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"  Columns: {list(df.columns)}")
    for col in df.columns:
        cl = col.lower()
        if any(kw in cl for kw in ["regio", "sector", "jaar", "year", "opleiding",
                                     "onderdeel", "provincie", "instelling",
                                     "geslacht", "bedrijfstak", "gemeente",
                                     "lisa_sector", "corop"]):
            nuniq = df[col].nunique()
            if nuniq <= 30:
                print(f"  {col} ({nuniq}): {sorted(df[col].dropna().unique(), key=str)}")
            else:
                print(f"  {col}: {nuniq} unique values")


def find_column(df, candidates, partial=True):
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
    if pd.isna(sector_val):
        return False
    s = str(sector_val).upper().strip()
    for stem in STEM_SECTORS_DUO:
        if stem in s or s in stem:
            return True
    return False


def fmt_pct(val):
    return f"{val:.1f}%" if not pd.isna(val) else "N/A"


def fmt_num(val):
    return f"{val:,.0f}".replace(",", ".") if not pd.isna(val) else "N/A"


def safe_open(filepath, mode="w"):
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
            print(f"  [FOUND]   {key} -> {os.path.basename(fp)}")
            found[key] = fp
        else:
            print(f"  [MISSING] {key}")

    tussen_files = find_tussen_files(data_dir)
    if tussen_files:
        print(f"  [FOUND]   Tussen_gemeenten -> {len(tussen_files)} year files")
        found["Tussen"] = tussen_files
    else:
        print(f"  [MISSING] Tussen_gemeenten files")

    missing = [k for k in FILE_ALIASES if k not in found]
    if "Tussen" not in found:
        missing.append("Tussen")

    if missing:
        print("\n  === DOWNLOAD INSTRUCTIONS FOR MISSING FILES ===")
        instructions = {
            "Verhuisde_personen_regio": (
                "CBS StatLine: search '60048ned' -> Gemeente = Groningen, "
                "all years, all age groups -> Download CSV"),
            "Vestigingen": (
                "CBS StatLine -> 81589NED -> ALL provinces, all SBI -> Download CSV"),
            "LISA": "Obtain from course materials or LISA",
            "Tussen": (
                "CBS StatLine -> 81734NED -> Gemeente vertrek = Groningen, "
                "ALL destination municipalities, all years -> Download CSV"),
            "OCW": (
                "ocwincijfers.nl -> Hoger Onderwijs -> Arbeidsmarkt -> "
                "'Arbeidsmarktkenmerken uitstromers WO' -> CSV"),
        }
        for k in missing:
            if k in instructions:
                print(f"  {k}: {instructions[k]}")

    return found, missing


# ---------------------------------------------------------------------------
# STEP 1: Inspect
# ---------------------------------------------------------------------------
def step1_inspect(found):
    print("\n" + "=" * 60)
    print("=== STEP 1: INSPECT ALL FILES ===")
    print("=" * 60)

    loaded = {}
    for key, fp in found.items():
        if key == "Tussen":
            # Multiple year files -> load and concat
            dfs = []
            for tf in fp:
                df = load_csv(tf, os.path.basename(tf))
                if df is not None:
                    for y in ["2019", "2020", "2021", "2022", "2023", "2024"]:
                        if y in os.path.basename(tf):
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

    return loaded


# ---------------------------------------------------------------------------
# STEP 2: STEM classification
# ---------------------------------------------------------------------------
def step2_stem_classification():
    print("\n" + "=" * 60)
    print("=== STEP 2: STEM CLASSIFICATION ===")
    print("=" * 60)
    print(f"  DUO sectors -> STEM: {', '.join(STEM_SECTORS_DUO)}")
    print(f"  SBI sectors -> STEM:")
    for k, v in STEM_SBI.items():
        print(f"    {k}: {v}")
    print(f"  LISA sectors -> STEM:")
    for k, v in LISA_STEM_SECTORS.items():
        print(f"    {k} -> SBI {v}")
    print(f"  Non-STEM ref: ECONOMIE, GEDRAG_EN_MAATSCHAPPIJ, GEZONDHEIDSZORG, ONDERWIJS")
    print(f"  Note: SBI M / LISA L10 includes consultancy alongside R&D -- flagged")
    note("SBI sector M / LISA L10 includes consultancy and R&D")


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
            print(f"\n  [SKIP] {grad_key} not loaded")
            continue

        print(f"\n  --- {grad_key} ---")

        # A1: Filter for Groningen
        # Column is INSTELLINGSNAAM_ACTUEEL based on actual data
        inst_col = find_column(grad_df, ["INSTELLINGSNAAM_ACTUEEL", "INSTELLINGSNAAM"])
        prov_col = find_column(grad_df, ["PROVINCIENAAM", "PROVINCIE"])

        if inst_col:
            gron_filter = grad_df[inst_col].astype(str).str.upper().str.contains(
                "GRONINGEN|RUG|RIJKSUNIVERSITEIT|HANZE", na=False)
            print(f"  Filtering {inst_col}: {gron_filter.sum()}/{len(grad_df)} Groningen rows")
        elif prov_col:
            gron_filter = grad_df[prov_col].astype(str).str.upper().str.contains(
                "GRONINGEN", na=False)
            print(f"  Filtering {prov_col}: {gron_filter.sum()}/{len(grad_df)} Groningen rows")
        else:
            print(f"  [WARNING] No institution/province column -- using full dataset")
            gron_filter = pd.Series(True, index=grad_df.index)

        gdf = grad_df[gron_filter].copy()
        if len(gdf) == 0:
            print(f"  [WARNING] No Groningen rows found")
            continue

        # Columns: ONDERDEEL (sector), DIPLOMAJAAR (year), AANTAL_GEDIPLOMEERDEN (count)
        sector_col = "ONDERDEEL"  # known from data inspection
        year_col = find_column(gdf, ["DIPLOMAJAAR", "STUDIEJAAR", "JAAR"])
        count_col = find_column(gdf, ["AANTAL_GEDIPLOMEERDEN", "AANTAL"])

        # Check for gender column (Gediplomeerden may have GESLACHT)
        gender_col = find_column(gdf, ["GESLACHT"])

        if sector_col not in gdf.columns:
            sector_col = find_column(gdf, ["ONDERDEEL", "SECTOR", "CROHO ONDERDEEL"])
        if sector_col is None:
            print(f"  [WARNING] No sector column")
            continue

        print(f"  Sectors: {sorted(gdf[sector_col].unique())}")
        gdf["IS_STEM"] = gdf[sector_col].apply(is_stem_duo)
        gdf["COUNT"] = clean_numeric(gdf[count_col]) if count_col else 1
        print(f"  STEM rows: {gdf['IS_STEM'].sum()}/{len(gdf)}")

        # A2: Annual STEM graduates
        if year_col:
            stem_yr = gdf[gdf["IS_STEM"]].groupby(year_col)["COUNT"].sum()
            nonstem_yr = gdf[~gdf["IS_STEM"]].groupby(year_col)["COUNT"].sum()
            yearly = pd.DataFrame({
                f"{level}_STEM_GRADS": stem_yr,
                f"{level}_NONSTEM_GRADS": nonstem_yr,
            }).fillna(0)
            total = yearly[f"{level}_STEM_GRADS"] + yearly[f"{level}_NONSTEM_GRADS"]
            yearly[f"{level}_STEM_PCT"] = (yearly[f"{level}_STEM_GRADS"] / total * 100).round(1)
            yearly.index.name = "YEAR"
            results_a[f"{level}_yearly"] = yearly
            print(f"\n  {level} annual STEM graduates:")
            print(yearly.to_string())

        # A3: Gender breakdown
        if gender_col and year_col:
            latest_year = gdf[year_col].max()
            latest = gdf[gdf[year_col] == latest_year]
            gender_tbl = latest.groupby([sector_col, gender_col])["COUNT"].sum().unstack(fill_value=0)
            if "MAN" in gender_tbl.columns and "VROUW" in gender_tbl.columns:
                gender_tbl["PCT_WOMEN"] = (
                    gender_tbl["VROUW"] /
                    (gender_tbl["MAN"] + gender_tbl["VROUW"]) * 100
                ).round(1)
                gender_tbl.insert(0, "YEAR", latest_year)
                results_a[f"{level}_gender"] = gender_tbl
                print(f"\n  {level} gender breakdown ({latest_year}):")
                print(gender_tbl.to_string())
            else:
                print(f"  Gender values: {list(gender_tbl.columns)} -- no MAN/VROUW split")
        elif not gender_col:
            # No GESLACHT column in Gediplomeerden -- check Inschrijvingen instead
            insch_key = f"Inschrijvingen_{level}"
            insch_df = loaded.get(insch_key)
            if insch_df is not None:
                i_inst = find_column(insch_df, ["INSTELLINGSNAAM_ACTUEEL", "INSTELLINGSNAAM"])
                i_gender = find_column(insch_df, ["GESLACHT"])
                i_count = find_column(insch_df, ["AANTAL_INGESCHREVENEN", "AANTAL"])
                i_year = find_column(insch_df, ["STUDIEJAAR", "JAAR"])
                if i_inst and i_gender and i_count and i_year:
                    i_gron = insch_df[insch_df[i_inst].astype(str).str.upper().str.contains(
                        "GRONINGEN|RUG|RIJKSUNIVERSITEIT|HANZE", na=False)].copy()
                    i_gron["IS_STEM"] = i_gron[sector_col].apply(is_stem_duo) if sector_col in i_gron.columns else False
                    i_gron["COUNT"] = clean_numeric(i_gron[i_count])
                    latest_yr = i_gron[i_year].max()
                    lat = i_gron[i_gron[i_year] == latest_yr]
                    g_tbl = lat.groupby([sector_col, i_gender])["COUNT"].sum().unstack(fill_value=0)
                    if "MAN" in g_tbl.columns and "VROUW" in g_tbl.columns:
                        g_tbl["PCT_WOMEN"] = (
                            g_tbl["VROUW"] / (g_tbl["MAN"] + g_tbl["VROUW"]) * 100
                        ).round(1)
                        g_tbl.insert(0, "YEAR", latest_yr)
                        results_a[f"{level}_gender_inschrijvingen"] = g_tbl
                        print(f"\n  {level} gender breakdown from Inschrijvingen ({latest_yr}):")
                        print(g_tbl.to_string())

        # A4: Pipeline leakage
        if eerst_df is not None and year_col:
            print(f"\n  --- Pipeline leakage ---")
            e_inst = find_column(eerst_df, ["INSTELLINGSNAAM_ACTUEEL", "INSTELLINGSNAAM"])
            if e_inst:
                e_gron = eerst_df[eerst_df[e_inst].astype(str).str.upper().str.contains(
                    "GRONINGEN|RUG|RIJKSUNIVERSITEIT|HANZE", na=False)].copy()
            else:
                e_gron = eerst_df.copy()

            e_sector = find_column(e_gron, ["ONDERDEEL", "SECTOR"])
            e_year = find_column(e_gron, ["STUDIEJAAR", "JAAR"])
            e_count = find_column(e_gron, ["AANTAL_EERSTEJAARS_INGESCHREVENEN", "AANTAL"])

            if e_sector and e_year and e_count:
                e_gron["IS_STEM"] = e_gron[e_sector].apply(is_stem_duo)
                e_gron["COUNT"] = clean_numeric(e_gron[e_count])
                e_stem = e_gron[e_gron["IS_STEM"]].groupby(e_year)["COUNT"].sum()
                g_stem = gdf[gdf["IS_STEM"]].groupby(year_col)["COUNT"].sum()

                # The year columns are: Eerstejaars STUDIEJAAR 2020-2024
                # Gediplomeerden DIPLOMAJAAR 2019-2023
                # Try offsets of 3 and 4 years
                print(f"  First-year years: {sorted(e_stem.index)}")
                print(f"  Graduate years: {sorted(g_stem.index)}")

                for offset in [4, 3, 5]:
                    leakage_rows = []
                    for yr in e_stem.index:
                        grad_yr = yr + offset
                        if grad_yr in g_stem.index:
                            e_val = e_stem[yr]
                            g_val = g_stem[grad_yr]
                            if e_val > 0:
                                leakage_rows.append({
                                    "FIRST_YEAR_COHORT": yr,
                                    "GRAD_YEAR": grad_yr,
                                    "OFFSET_YEARS": offset,
                                    "STEM_FIRST_YEARS": e_val,
                                    "STEM_GRADUATES": g_val,
                                    "DROPOUT_PCT": round((e_val - g_val) / e_val * 100, 1),
                                })
                    if leakage_rows:
                        leak_df = pd.DataFrame(leakage_rows)
                        results_a[f"{level}_leakage"] = leak_df
                        print(f"\n  {level} pipeline leakage (offset={offset}):")
                        print(leak_df.to_string(index=False))
                        print("  Note: Upper bound estimate. Cohort tracking needs CBS microdata.")
                        break
                else:
                    # No offset works -- show descriptive comparison
                    print(f"  No overlapping years with standard offsets.")
                    print(f"  Descriptive comparison (latest available):")
                    if len(e_stem) > 0 and len(g_stem) > 0:
                        print(f"    First-years STEM ({e_stem.index[-1]}): {e_stem.iloc[-1]:.0f}")
                        print(f"    Graduates STEM ({g_stem.index[-1]}): {g_stem.iloc[-1]:.0f}")
                        results_a[f"{level}_pipeline_descriptive"] = pd.DataFrame({
                            "Metric": ["First-year STEM (latest)", "Graduate STEM (latest)"],
                            "Year": [e_stem.index[-1], g_stem.index[-1]],
                            "Count": [e_stem.iloc[-1], g_stem.iloc[-1]],
                        })

    # Save
    output_path = os.path.join(out_dir, "output_A_stem_pipeline_groningen.csv")
    with safe_open(output_path) as f:
        write_csv_header(f, "DUO Gediplomeerden/Eerstejaars WO+HBO",
                         "Groningen institutions only")
        for key, df in results_a.items():
            f.write(f"\n# {key}\n")
            df.to_csv(f)
    print(f"\n  [OK] Step 3 complete -> {output_path}")
    return results_a


# ---------------------------------------------------------------------------
# STEP 4: Analysis B -- Regional Industrial Structure (using LISA)
# ---------------------------------------------------------------------------
def step4_analysis_b(loaded, out_dir):
    print("\n" + "=" * 60)
    print("=== STEP 4: ANALYSIS B -- REGIONAL INDUSTRIAL STRUCTURE ===")
    print("=" * 60)

    results_b = {}

    # --- Use LISA as primary source (has all provinces, sectors, job counts) ---
    lisa_df = loaded.get("LISA")
    if lisa_df is not None:
        print(f"\n  --- Using LISA for Location Quotient analysis ---")
        print(f"  LISA sectors: {sorted(lisa_df['LISA_sector'].unique())}")

        # Use latest year
        latest_year = lisa_df["Jaar"].max()
        lisa_latest = lisa_df[lisa_df["Jaar"] == latest_year].copy()
        print(f"  Using year: {latest_year}")

        # Normalize province names
        lisa_latest["Province"] = lisa_latest["Provincie"].replace(PROVINCE_NORMALIZE)

        # Classify STEM
        lisa_latest["IS_STEM"] = lisa_latest["LISA_sector"].isin(LISA_STEM_SECTORS.keys())
        lisa_latest["SBI_GROUP"] = lisa_latest["LISA_sector"].map(LISA_STEM_SECTORS).fillna("OTHER")

        # B2: Location Quotient per province
        print(f"\n  --- B2: Location Quotients by province ---")

        lq_rows = []
        for prov in sorted(lisa_latest["Province"].unique()):
            prov_data = lisa_latest[lisa_latest["Province"] == prov]
            total_prov = prov_data["Banen"].sum()
            if total_prov == 0:
                continue

            total_national = lisa_latest["Banen"].sum()
            row = {"REGION": prov, "TOTAL_JOBS": total_prov}

            for lisa_sector, sbi_code in LISA_STEM_SECTORS.items():
                sector_prov = prov_data[prov_data["LISA_sector"] == lisa_sector]["Banen"].sum()
                sector_national = lisa_latest[lisa_latest["LISA_sector"] == lisa_sector]["Banen"].sum()

                if total_national > 0 and sector_national > 0:
                    lq = (sector_prov / total_prov) / (sector_national / total_national)
                    sbi_label = STEM_SBI.get(sbi_code, sbi_code)
                    short = sbi_label.split("(")[0].strip() if "(" in sbi_label else sbi_label
                    row[f"LQ_{sbi_code}_{short}"] = round(lq, 2)

            lq_rows.append(row)

        lq_df = pd.DataFrame(lq_rows)
        # Composite STEM LQ
        lq_cols = [c for c in lq_df.columns if c.startswith("LQ_")]
        lq_df["STEM_LQ_COMPOSITE"] = lq_df[lq_cols].mean(axis=1).round(2)

        # B3: Rank
        lq_df = lq_df.sort_values("STEM_LQ_COMPOSITE", ascending=False).reset_index(drop=True)
        lq_df.index += 1
        lq_df.index.name = "RANK"

        results_b["lq"] = lq_df
        print(f"\n  Location Quotients (ranked by STEM LQ composite):")
        print(lq_df.to_string())

        # Groningen position
        gron_rows = lq_df[lq_df["REGION"].str.contains("Groningen", case=False)]
        if len(gron_rows) > 0:
            gron_rank = gron_rows.index[0]
            gron_lq = gron_rows["STEM_LQ_COMPOSITE"].values[0]
            results_b["groningen_rank"] = gron_rank
            results_b["groningen_lq"] = gron_lq
            results_b["total_regions"] = len(lq_df)
            print(f"\n  >> Groningen: rank #{gron_rank}/{len(lq_df)}, "
                  f"composite STEM LQ = {gron_lq}")

        # National STEM employment share (for gravity model)
        stem_national = lisa_latest[lisa_latest["IS_STEM"]]["Banen"].sum()
        total_national_all = lisa_latest["Banen"].sum()
        if total_national_all > 0:
            results_b["national_stem_share"] = round(stem_national / total_national_all, 4)
            print(f"\n  National STEM share: {results_b['national_stem_share']:.1%}")

        # Also do COROP-level analysis
        if "COROP_gebied" in lisa_latest.columns:
            print(f"\n  --- COROP-level LQ analysis ---")
            corop_lq_rows = []
            for corop in sorted(lisa_latest["COROP_gebied"].unique()):
                corop_data = lisa_latest[lisa_latest["COROP_gebied"] == corop]
                total_corop = corop_data["Banen"].sum()
                if total_corop == 0:
                    continue
                total_national = lisa_latest["Banen"].sum()
                row = {"COROP_REGION": corop, "TOTAL_JOBS": total_corop}
                for lisa_sector, sbi_code in LISA_STEM_SECTORS.items():
                    s_corop = corop_data[corop_data["LISA_sector"] == lisa_sector]["Banen"].sum()
                    s_nat = lisa_latest[lisa_latest["LISA_sector"] == lisa_sector]["Banen"].sum()
                    if total_national > 0 and s_nat > 0:
                        lq = (s_corop / total_corop) / (s_nat / total_national)
                        row[f"LQ_{sbi_code}"] = round(lq, 2)
                corop_lq_rows.append(row)

            corop_df = pd.DataFrame(corop_lq_rows)
            corop_lq_cols = [c for c in corop_df.columns if c.startswith("LQ_")]
            corop_df["STEM_LQ_COMPOSITE"] = corop_df[corop_lq_cols].mean(axis=1).round(2)
            corop_df = corop_df.sort_values("STEM_LQ_COMPOSITE", ascending=False).reset_index(drop=True)
            corop_df.index += 1
            corop_df.index.name = "RANK"
            results_b["corop_lq"] = corop_df
            print(corop_df.to_string())

            gron_corop = corop_df[corop_df["COROP_REGION"].str.contains("Groningen", case=False)]
            if len(gron_corop) > 0:
                cr = gron_corop.index[0]
                cl = gron_corop["STEM_LQ_COMPOSITE"].values[0]
                results_b["groningen_corop_rank"] = cr
                results_b["groningen_corop_lq"] = cl
                results_b["total_corop_regions"] = len(corop_df)
                print(f"\n  >> Groningen COROP: rank #{cr}/{len(corop_df)}, "
                      f"STEM LQ = {cl}")

        # B4: Groningen STEM employment detail
        print(f"\n  --- B4: Groningen STEM employment detail ---")
        gron_lisa = lisa_latest[lisa_latest["Gemeente"].str.contains("Groningen", case=False)]
        if len(gron_lisa) > 0:
            total_gron = gron_lisa["Banen"].sum()
            stem_gron = gron_lisa[gron_lisa["IS_STEM"]]["Banen"].sum()
            stem_pct = stem_gron / total_gron * 100 if total_gron > 0 else 0
            print(f"  Groningen municipality ({latest_year}):")
            print(f"    Total jobs: {fmt_num(total_gron)}")
            print(f"    STEM jobs:  {fmt_num(stem_gron)} ({fmt_pct(stem_pct)})")
            results_b["lisa_total_jobs"] = total_gron
            results_b["lisa_stem_jobs"] = stem_gron
            results_b["lisa_stem_pct"] = stem_pct

            sector_detail = gron_lisa.groupby("LISA_sector")["Banen"].sum().sort_values(ascending=False)
            print(f"\n  Jobs by sector in Groningen:")
            for sec, val in sector_detail.items():
                stem_flag = " [STEM]" if sec in LISA_STEM_SECTORS else ""
                print(f"    {sec}: {fmt_num(val)}{stem_flag}")
            results_b["groningen_sector_detail"] = sector_detail
    else:
        print(f"  [SKIP] LISA file not loaded")

    # --- Also inspect Vestigingen (transposed CBS format) ---
    vest_df = loaded.get("Vestigingen")
    if vest_df is not None:
        print(f"\n  --- Vestigingen (CBS transposed format) ---")
        # This file has: first column = region names, other columns = SBI sectors
        # Columns: 'Bedrijfstakken/branches (SBI 2008)', 'C Industrie', 'J Informatie...' etc.
        first_col = vest_df.columns[0]  # region column
        print(f"  Region column: '{first_col}'")
        print(f"  SBI sector columns: {list(vest_df.columns[1:])}")

        # The regions are in the first column
        print(f"  Regions in data: {list(vest_df[first_col].head(20))}")

        # Extract STEM sector columns
        stem_cols = []
        for col in vest_df.columns[1:]:
            if any(col.startswith(f"{sbi} ") for sbi in ["C", "D", "J", "M"]):
                stem_cols.append(col)
        print(f"  STEM columns identified: {stem_cols}")

        # Clean numeric values in sector columns
        for col in vest_df.columns[1:]:
            vest_df[col] = clean_numeric(vest_df[col])

        # Show Groningen row
        gron_mask = vest_df[first_col].astype(str).str.contains("Groningen", case=False, na=False)
        gron_vest = vest_df[gron_mask]
        if len(gron_vest) > 0:
            print(f"\n  Groningen establishments:")
            for col in vest_df.columns[1:]:
                val = gron_vest[col].values[0]
                stem_flag = " [STEM]" if col in stem_cols else ""
                print(f"    {col}: {fmt_num(val)}{stem_flag}")
            results_b["vestigingen_groningen"] = gron_vest

        # If multiple regions present, calculate LQ from vestigingen too
        if len(vest_df) > 5:
            print(f"\n  Vestigingen LQ (establishment-based):")
            vest_lq_rows = []
            for _, row in vest_df.iterrows():
                region = str(row[first_col]).strip()
                if not region or region == "nan":
                    continue
                total_r = sum(clean_numeric(pd.Series([row[c]])).fillna(0).iloc[0]
                              for c in vest_df.columns[1:])
                if total_r == 0:
                    continue
                total_n = sum(vest_df[c].sum() for c in vest_df.columns[1:])
                lq_row = {"REGION": region}
                for sc in stem_cols:
                    s_r = row[sc] if not pd.isna(row[sc]) else 0
                    s_n = vest_df[sc].sum()
                    if total_n > 0 and s_n > 0:
                        lq = (s_r / total_r) / (s_n / total_n)
                        lq_row[f"LQ_{sc[:1]}"] = round(lq, 2)
                vest_lq_rows.append(lq_row)

            if vest_lq_rows:
                vest_lq_df = pd.DataFrame(vest_lq_rows)
                lq_c = [c for c in vest_lq_df.columns if c.startswith("LQ_")]
                vest_lq_df["STEM_LQ_COMPOSITE"] = vest_lq_df[lq_c].mean(axis=1).round(2)
                vest_lq_df = vest_lq_df.sort_values("STEM_LQ_COMPOSITE", ascending=False)
                results_b["vestigingen_lq"] = vest_lq_df
                print(vest_lq_df.to_string(index=False))
    else:
        print(f"\n  [SKIP] Vestigingen not loaded")

    # Validation: compare LISA vs CBS Vestigingen for Groningen
    if "lisa_stem_pct" in results_b and "vestigingen_groningen" in results_b:
        print(f"\n  [VALIDATION] LISA STEM share = {fmt_pct(results_b['lisa_stem_pct'])}")
        print(f"  Note: LISA counts workers (banen), CBS counts establishments (vestigingen)")
        print(f"  Both are valid but measure different things")
        note("LISA=workers vs CBS=establishments: different denominators")

    # Save
    output_path = os.path.join(out_dir, "output_B_location_quotients.csv")
    with safe_open(output_path) as f:
        write_csv_header(f, "LISA Gemeenten 2024, CBS Vestigingen",
                         "LISA LQ based on workers; M/L10 includes consultancy")
        for key, val in results_b.items():
            if isinstance(val, (pd.DataFrame, pd.Series)):
                f.write(f"\n# {key}\n")
                if isinstance(val, pd.Series):
                    val.to_csv(f)
                else:
                    val.to_csv(f)
            elif isinstance(val, (int, float)):
                f.write(f"# {key}: {val}\n")
    print(f"\n  [OK] Step 4 complete -> {output_path}")
    return results_b


# ---------------------------------------------------------------------------
# STEP 5: Analysis C -- Mobility Flows
# ---------------------------------------------------------------------------
def step5_analysis_c(loaded, out_dir):
    print("\n" + "=" * 60)
    print("=== STEP 5: ANALYSIS C -- MOBILITY FLOWS ===")
    print("=" * 60)

    results_c = {}

    # C1: Verhuisde personen
    vh_df = loaded.get("Verhuisde_personen_regio")
    if vh_df is None:
        print(f"  [SKIP] Verhuisde_personen not loaded")
        note("Mobility flow analysis skipped: Verhuisde_personen file not available")
    else:
        print(f"\n  --- C1: Migration data ---")
        print(f"  Columns: {list(vh_df.columns)}")
        print(f"  First 10 rows:")
        print(vh_df.head(10).to_string())

        # This CBS file can have various structures. Try to parse it.
        year_col = find_column(vh_df, ["PERIODEN", "JAAR", "Perioden"])

        # Look for age-specific columns in wide format
        age_cols = {}
        for col in vh_df.columns:
            cl = col.lower()
            if ("vertrok" in cl or "vertrek" in cl):
                if "20" in cl and "25" in cl:
                    age_cols["V_20_25"] = col
                elif "25" in cl and "30" in cl:
                    age_cols["V_25_30"] = col
            elif ("gevestigd" in cl or "vestiging" in cl):
                if "20" in cl and "25" in cl:
                    age_cols["G_20_25"] = col
                elif "25" in cl and "30" in cl:
                    age_cols["G_25_30"] = col

        if "V_25_30" in age_cols:
            print(f"  Found age-specific columns: {age_cols}")
            # Wide format processing
            regio_col = find_column(vh_df, ["REGIO", "REGIOS", "Regio's"])
            if regio_col:
                gron = vh_df[vh_df[regio_col].astype(str).str.upper().str.contains(
                    "GRONINGEN", na=False)].copy()
            else:
                gron = vh_df.copy()

            for key, col in age_cols.items():
                gron[key] = clean_numeric(gron[col])

            gron["NET_20_25"] = gron.get("G_20_25", 0) - gron.get("V_20_25", 0)
            gron["NET_25_30"] = gron["G_25_30"] - gron["V_25_30"]

            if year_col:
                mig_cols = ["G_20_25", "V_20_25", "NET_20_25",
                            "G_25_30", "V_25_30", "NET_25_30"]
                mig_cols = [c for c in mig_cols if c in gron.columns]
                yearly_mig = gron.groupby(year_col)[mig_cols].sum().reset_index()
                yearly_mig["RETENTION_25_30"] = (
                    yearly_mig["G_25_30"] /
                    (yearly_mig["G_25_30"] + yearly_mig["V_25_30"]) * 100
                ).round(1)
                results_c["yearly_migration"] = yearly_mig
                print(f"\n  Annual net migration:")
                print(yearly_mig.to_string(index=False))
        else:
            # Try long format with age group column
            age_col = find_column(vh_df, ["LEEFTIJD", "LEEFTIJDSGROEP", "Leeftijd",
                                           "Leeftijdsgroep verhuisde persoon"])
            if age_col:
                print(f"  Long format with age column: {age_col}")
                print(f"  Age groups: {vh_df[age_col].unique()}")
            else:
                print(f"  [WARNING] Cannot identify age-specific columns")
                print(f"  Attempting to show all data:")
                for col in vh_df.columns:
                    print(f"    {col}: {vh_df[col].head(3).tolist()}")
                note("Migration: unknown column structure")

    # C4: Tussen gemeenten (destination analysis)
    tussen_df = loaded.get("Tussen")
    if tussen_df is None:
        print(f"\n  [SKIP] Tussen_gemeenten not loaded")
        note("Destination analysis skipped: critical for spatial argument")
    else:
        print(f"\n  --- C4: Destination analysis ---")
        print(f"  Shape: {tussen_df.shape}")
        print(f"  Columns: {list(tussen_df.columns)}")
        print(f"  All data:")
        print(tussen_df.to_string())

        # The Tussen files have a peculiar structure from the output:
        # Column 'Unnamed: 0' has province names and counts mixed
        # Column 'Regio van vestiging' has more province/count values
        # This appears to be a transposed/pivoted CBS download

        # Try to parse the unusual structure
        # Each year-file seems to have: row 0 = province names, row 1 = "aantal",
        # row 2 = actual counts, row 3 = NaN
        # And columns represent different destination provinces

        print(f"\n  Attempting to parse transposed Tussen_gemeenten structure...")

        # Group by FILE_YEAR and try to extract province->count pairs
        dest_data = []
        for year in sorted(tussen_df["FILE_YEAR"].unique()):
            year_data = tussen_df[tussen_df["FILE_YEAR"] == year]

            # The data seems to have province names in one row, counts in another
            # Each column pair represents a destination
            for col in tussen_df.columns:
                if col == "FILE_YEAR":
                    continue
                values = year_data[col].tolist()
                # Look for pattern: province name, "aantal", number, NaN
                province_name = None
                count_val = None
                for v in values:
                    v_str = str(v).strip()
                    if "(PV)" in v_str:
                        province_name = v_str.replace(" (PV)", "")
                    elif v_str.isdigit():
                        count_val = int(v_str)
                    else:
                        try:
                            count_val = int(float(v_str))
                        except (ValueError, TypeError):
                            pass

                if province_name and count_val:
                    dest_data.append({
                        "YEAR": year,
                        "DESTINATION_PROVINCE": province_name,
                        "PERSONS": count_val,
                    })

        if dest_data:
            dest_df = pd.DataFrame(dest_data)
            print(f"\n  Parsed destination data:")
            print(dest_df.to_string(index=False))

            # Aggregate across years
            prov_total = dest_df.groupby("DESTINATION_PROVINCE")["PERSONS"].sum().sort_values(ascending=False)
            total_outflow = prov_total.sum()

            prov_summary = pd.DataFrame({
                "DESTINATION_PROVINCE": prov_total.index,
                "PERSONS_FROM_GRONINGEN": prov_total.values,
                "PCT_OF_TOTAL_OUTFLOW": (prov_total.values / total_outflow * 100).round(1),
            })

            # Mobility intensity
            intensities = []
            for _, row in prov_summary.iterrows():
                prov = row["DESTINATION_PROVINCE"]
                if prov in PROVINCE_POP and prov != "Groningen":
                    pct_flow = row["PCT_OF_TOTAL_OUTFLOW"] / 100
                    pct_pop = PROVINCE_POP[prov] / NL_TOTAL_POP
                    intensities.append(round(pct_flow / pct_pop, 2) if pct_pop > 0 else np.nan)
                else:
                    intensities.append(np.nan)
            prov_summary["MOBILITY_INTENSITY"] = intensities

            results_c["province_destinations"] = prov_summary
            print(f"\n  Destination provinces (aggregated):")
            print(prov_summary.to_string(index=False))

            # Year breakdown
            yearly_dest = dest_df.pivot_table(index="DESTINATION_PROVINCE",
                                              columns="YEAR", values="PERSONS",
                                              aggfunc="sum", fill_value=0)
            results_c["yearly_destinations"] = yearly_dest
            print(f"\n  By year:")
            print(yearly_dest.to_string())
        else:
            print(f"  [WARNING] Could not parse Tussen_gemeenten structure")
            print(f"  The CBS download may need different filter settings:")
            print(f"  -> Select ALL destination municipalities (not just a few)")
            print(f"  -> The current files only have 2 columns = 2 destinations")
            note("Tussen_gemeenten: only 2 destination provinces found. "
                 "Re-download with ALL municipalities selected.")

    # Methodological note
    print(f"\n  Methodological note:")
    print(f"  - BRP mobility data is a proxy for graduate transitions")
    print(f"  - Captures all movers 25-30, not only graduates")
    print(f"  - ~25% of Groningen 25-30 cohort = students/recent grads")

    # Save
    output_path = os.path.join(out_dir, "output_C_mobility_flows.csv")
    with safe_open(output_path) as f:
        write_csv_header(f, "CBS 60048ned, CBS 81734NED",
                         "All movers, not only graduates")
        for key, val in results_c.items():
            if isinstance(val, (pd.DataFrame, pd.Series)):
                f.write(f"\n# {key}\n")
                val.to_csv(f)
    print(f"\n  [OK] Step 5 complete -> {output_path}")
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
        print(f"  [SKIP] OCW file not found")
        print(f"  Download: ocwincijfers.nl -> Hoger Onderwijs -> Arbeidsmarkt -> CSV")
        note("Match analysis skipped: OCW file not available")
    else:
        field_col = find_column(ocw_df, ["OPLEIDING", "STUDIERICHTING", "Opleiding"])
        if field_col:
            ocw_df["TYPE"] = ocw_df[field_col].apply(lambda x:
                "STEM" if any(kw in str(x).upper() for kw in
                    ["TECHNIEK", "NATUUR", "WISKUNDE", "INFORMATICA", "WERKTUIG",
                     "ELEKTRO", "SCHEIKUNDE", "BIOLOGIE", "ENGINEERING"]) else "NonSTEM")
            print(ocw_df.to_string())
            results_d["raw"] = ocw_df

    output_path = os.path.join(out_dir, "output_D_match_analysis.csv")
    with safe_open(output_path) as f:
        write_csv_header(f, "OCW arbeidsmarktkenmerken", "National data")
        if results_d:
            for key, val in results_d.items():
                if isinstance(val, pd.DataFrame):
                    f.write(f"\n# {key}\n")
                    val.to_csv(f, index=False)
        else:
            f.write("# No data available -- OCW file not found\n")
    print(f"\n  [OK] Step 6 complete -> {output_path}")
    return results_d


# ---------------------------------------------------------------------------
# STEP 7: Synthesis
# ---------------------------------------------------------------------------
def step7_synthesis(results_a, results_b, results_c, results_d, out_dir):
    print("\n" + "=" * 60)
    print("=== STEP 7: CORE FINDING SYNTHESIS ===")
    print("=" * 60)

    lines = ["=" * 60, "CORE FINDING SYNTHESIS", f"Generated: {generated_date}", "=" * 60]

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
                lines.append(f"   {level} STEM graduates (latest): {fmt_num(df[stem_col].iloc[-1])}")
            if pct_col in df.columns and len(df) > 0:
                lines.append(f"   {level} STEM share: {df[pct_col].iloc[-1]}%")
                vals = df[pct_col].dropna()
                if len(vals) >= 3:
                    m, s = vals.mean(), vals.std()
                    l = vals.iloc[-1]
                    trend = ("growing" if s > 0 and l > m + s else
                             "declining" if s > 0 and l < m - s else "stable")
                    lines.append(f"   {level} trend: {trend}")
    if not has_supply:
        lines.append("   [Data not available]")

    # Combined
    wo_key, hbo_key = "WO_yearly", "HBO_yearly"
    if wo_key in results_a and hbo_key in results_a:
        wo_latest = results_a[wo_key]["WO_STEM_GRADS"].iloc[-1]
        hbo_latest = results_a[hbo_key]["HBO_STEM_GRADS"].iloc[-1]
        lines.append(f"   Combined STEM graduates (WO+HBO): {fmt_num(wo_latest + hbo_latest)}")

    # 2. DEMAND
    lines.append("\n2. DEMAND (Analysis B):")
    if "groningen_lq" in results_b:
        lines.append(f"   Groningen STEM LQ (province): {results_b['groningen_lq']} "
                     f"(national avg = 1.0)")
        lines.append(f"   Province rank: #{results_b.get('groningen_rank', '?')}"
                     f"/{results_b.get('total_regions', '?')}")
        if results_b['groningen_lq'] < 1.0:
            lines.append("   -> UNDER-specialized in STEM: local economy cannot absorb all grads")
        if "groningen_corop_lq" in results_b:
            lines.append(f"   COROP rank: #{results_b['groningen_corop_rank']}"
                         f"/{results_b['total_corop_regions']}"
                         f" (LQ={results_b['groningen_corop_lq']})")
        if "lq" in results_b:
            top3 = results_b["lq"].head(3)
            lines.append("   Top STEM provinces:")
            for _, r in top3.iterrows():
                lines.append(f"     {r['REGION']}: LQ={r['STEM_LQ_COMPOSITE']}")
    if "lisa_stem_pct" in results_b:
        lines.append(f"   Groningen STEM employment: {fmt_pct(results_b['lisa_stem_pct'])} "
                     f"of {fmt_num(results_b['lisa_total_jobs'])} total jobs")

    # 3. MOBILITY
    lines.append("\n3. MOBILITY (Analysis C):")
    if "yearly_migration" in results_c:
        mig = results_c["yearly_migration"]
        avg = mig["NET_25_30"].mean()
        lines.append(f"   Avg annual net flow 25-30: {fmt_num(avg)}")
    if "province_destinations" in results_c:
        dest = results_c["province_destinations"]
        for _, r in dest.head(3).iterrows():
            lines.append(f"   -> {r['DESTINATION_PROVINCE']}: "
                         f"{fmt_num(r['PERSONS_FROM_GRONINGEN'])} persons "
                         f"({fmt_pct(r['PCT_OF_TOTAL_OUTFLOW'])})")
            if not pd.isna(r.get("MOBILITY_INTENSITY")):
                lines.append(f"      Mobility intensity: {r['MOBILITY_INTENSITY']}")

    # 4. CONNECTION
    lines.append("\n4. CONNECTION:")
    if "lq" in results_b and "province_destinations" in results_c:
        lines.append("   Cross-reference: do graduates flow to high-STEM-LQ regions?")
        dest = results_c.get("province_destinations")
        lq = results_b.get("lq")
        if dest is not None and lq is not None:
            for _, d_row in dest.iterrows():
                prov = d_row["DESTINATION_PROVINCE"]
                lq_match = lq[lq["REGION"] == prov]
                if len(lq_match) > 0:
                    lq_val = lq_match["STEM_LQ_COMPOSITE"].values[0]
                    lines.append(f"   {prov}: outflow={fmt_pct(d_row['PCT_OF_TOTAL_OUTFLOW'])}, "
                                 f"STEM LQ={lq_val}")
    else:
        lines.append("   Hypothesis: STEM grads move to high-STEM-LQ regions")
        lines.append("   (validate with interview data + WO-Monitor)")

    synthesis = "\n".join(lines)
    print(synthesis)

    output_path = os.path.join(out_dir, "output_SYNTHESIS.txt")
    with safe_open(output_path) as f:
        f.write(synthesis)
    print(f"\n  [OK] Synthesis -> {output_path}")
    return synthesis


# ---------------------------------------------------------------------------
# STEP 8 + 10: Data quality + Quality checks
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
        for k in missing_keys:
            f.write(f"  - {k}\n")
        if not missing_keys:
            f.write("  All files present\n")

        f.write(f"\nDATA QUALITY NOTES ({len(data_quality_notes)}):\n")
        for i, n in enumerate(data_quality_notes, 1):
            f.write(f"  {i}. {n}\n")

        f.write("\nSTANDARD CAVEATS:\n")
        for c in [
            "Verhuisde personen = ALL movers aged 25-30, not only graduates",
            "Groningen: ~60k students / ~235k residents (~25% of 25-30 cohort)",
            "DUO academic years (Sep-Aug) vs CBS calendar years (6-month offset)",
            "COVID 2020-2021 may show anomalous patterns",
            "Pipeline dropout is upper bound (no individual tracking)",
            "SBI M / LISA L10 includes consultancy + R&D",
            "LISA LQ based on worker counts; CBS Vestigingen on establishments",
            "Triangulate with WO-Monitor alumni surveys + interview data",
        ]:
            f.write(f"  - {c}\n")

    print(f"  [OK] -> {output_path}")


def step10_quality_checks(results_a):
    print("\n" + "=" * 60)
    print("=== ACADEMIC QUALITY CHECKS ===")
    print("=" * 60)

    print("\n  1. Sample size:")
    for key, df in results_a.items():
        if isinstance(df, pd.DataFrame):
            num = df.select_dtypes(include=[np.number])
            small = (num < 30) & (num > 0)
            if small.any().any():
                print(f"     [!] {key}: some cells n < 30")
            else:
                print(f"     [OK] {key}")

    print("\n  2. Trend direction:")
    for level in ["WO", "HBO"]:
        key = f"{level}_yearly"
        if key in results_a:
            pct_col = f"{level}_STEM_PCT"
            if pct_col in results_a[key].columns:
                vals = results_a[key][pct_col].dropna()
                if len(vals) >= 3:
                    m, s = vals.mean(), vals.std()
                    l = vals.iloc[-1]
                    if s > 0 and l > m + s:
                        print(f"     {pct_col}: meaningful increase (latest={l:.1f}, mean={m:.1f})")
                    elif s > 0 and l < m - s:
                        print(f"     {pct_col}: meaningful decrease")
                    else:
                        print(f"     {pct_col}: within noise (latest={l:.1f}, mean={m:.1f})")

    print("\n  3. DUO academic years vs CBS calendar years: 6-month offset")
    print("  4. Representativeness: mobility data = all movers 25-30")
    print("  5. COVID: 2020-2021 may be anomalous")


# ---------------------------------------------------------------------------
# STEP 11: GRAVITY MODEL -- Predict STEM graduate destination probabilities
# ---------------------------------------------------------------------------

# Driving distances from Groningen (km) to province capitals / economic centres
DISTANCE_FROM_GRONINGEN = {
    "Groningen": 0, "Friesland": 60, "Drenthe": 45, "Overijssel": 115,
    "Flevoland": 140, "Gelderland": 175, "Utrecht": 185, "Noord-Holland": 195,
    "Zuid-Holland": 230, "Zeeland": 310, "Noord-Brabant": 260, "Limburg": 300,
}


def step11_gravity_model(results_a, results_b, results_c, out_dir):
    """
    Gravity model: predicts probability of a Groningen STEM graduate
    settling in each province, based on:
      - STEM jobs in destination (pull factor)
      - Distance from Groningen (friction)
      - Province population / labour market size (mass)
      - Observed migration flows (calibration)

    Outputs map-ready CSV + regression diagnostics + STEM occupation estimates.
    """
    print("\n" + "=" * 60)
    print("=== STEP 11: GRAVITY MODEL -- STEM GRADUATE DESTINATIONS ===")
    print("=" * 60)

    results_grav = {}

    # Check prerequisites
    if "lq" not in results_b:
        print("  [SKIP] No LQ data available")
        return results_grav
    lq_df = results_b["lq"].copy()

    # -----------------------------------------------------------------------
    # 1. Build province-level feature table
    # -----------------------------------------------------------------------
    print("\n  --- Building province feature table ---")

    provinces = []
    for _, row in lq_df.iterrows():
        prov = row["REGION"]
        if prov == "Groningen":
            continue  # exclude origin
        if prov not in DISTANCE_FROM_GRONINGEN:
            continue

        d = {
            "PROVINCE": prov,
            "DISTANCE_KM": DISTANCE_FROM_GRONINGEN[prov],
            "POPULATION": PROVINCE_POP.get(prov, np.nan),
            "TOTAL_JOBS": row["TOTAL_JOBS"],
            "STEM_LQ": row["STEM_LQ_COMPOSITE"],
        }

        # Compute STEM jobs (total jobs * national STEM share * LQ)
        # National STEM share from LISA
        national_stem_share = results_b.get("national_stem_share", 0.15)
        d["STEM_JOBS_EST"] = int(row["TOTAL_JOBS"] * national_stem_share * row["STEM_LQ_COMPOSITE"])

        # Individual LQ columns
        for col in row.index:
            if col.startswith("LQ_"):
                d[col] = row[col]

        provinces.append(d)

    feat = pd.DataFrame(provinces)
    if len(feat) < 3:
        print("  [SKIP] Not enough provinces for regression")
        return results_grav

    # Add log-transformed features for gravity model
    feat["LOG_DISTANCE"] = np.log(feat["DISTANCE_KM"].clip(lower=1))
    feat["LOG_JOBS"] = np.log(feat["TOTAL_JOBS"].clip(lower=1))
    feat["LOG_STEM_JOBS"] = np.log(feat["STEM_JOBS_EST"].clip(lower=1))
    feat["LOG_POP"] = np.log(feat["POPULATION"].clip(lower=1))

    print(f"  Provinces in model: {len(feat)}")
    print(feat[["PROVINCE", "DISTANCE_KM", "TOTAL_JOBS", "STEM_LQ", "STEM_JOBS_EST"]].to_string(index=False))

    # -----------------------------------------------------------------------
    # 2. Merge observed flows (if available)
    # -----------------------------------------------------------------------
    has_observed = False
    if "province_destinations" in results_c:
        obs = results_c["province_destinations"].copy()
        obs = obs.rename(columns={"DESTINATION_PROVINCE": "PROVINCE"})
        feat = feat.merge(obs[["PROVINCE", "PERSONS_FROM_GRONINGEN", "PCT_OF_TOTAL_OUTFLOW"]],
                          on="PROVINCE", how="left")
        feat["PERSONS_FROM_GRONINGEN"] = feat["PERSONS_FROM_GRONINGEN"].fillna(0)
        feat["PCT_OF_TOTAL_OUTFLOW"] = feat["PCT_OF_TOTAL_OUTFLOW"].fillna(0)
        has_observed = feat["PERSONS_FROM_GRONINGEN"].sum() > 0
        if has_observed:
            feat["LOG_FLOW"] = np.log(feat["PERSONS_FROM_GRONINGEN"].clip(lower=1))
            print(f"\n  Observed flows available -- will calibrate model")

    # -----------------------------------------------------------------------
    # 3. Gravity model (log-linear regression)
    # -----------------------------------------------------------------------
    print(f"\n  --- Gravity Model Regression ---")
    print(f"  Model: log(Flow) ~ beta1*log(STEM_Jobs) + beta2*log(Distance) + beta3*STEM_LQ")

    from scipy import stats as scipy_stats

    # --- Model A: Pure gravity (uncalibrated, theoretical) ---
    # Flow_ij proportional to (STEM_Jobs_j ^ alpha) / (Distance_ij ^ beta)
    # Standard gravity: alpha ~ 1, beta ~ 1-2

    # Theoretical prediction (no calibration needed)
    feat["GRAVITY_RAW"] = feat["STEM_JOBS_EST"] / (feat["DISTANCE_KM"] ** 1.5)
    feat["GRAVITY_PROB_THEORY"] = (feat["GRAVITY_RAW"] / feat["GRAVITY_RAW"].sum() * 100).round(2)

    print(f"\n  Theoretical gravity model (alpha=1, beta=1.5):")
    print(feat[["PROVINCE", "STEM_JOBS_EST", "DISTANCE_KM", "GRAVITY_PROB_THEORY"]].to_string(index=False))

    # --- Model B: Calibrated (if observed data exists) ---
    regression_results = {}
    if has_observed and feat["PERSONS_FROM_GRONINGEN"].gt(0).sum() >= 3:
        valid = feat[feat["PERSONS_FROM_GRONINGEN"] > 0].copy()

        # OLS: log(flow) = a + b1*log(stem_jobs) + b2*log(distance) + b3*stem_lq
        Y = valid["LOG_FLOW"].values
        X_vars = valid[["LOG_STEM_JOBS", "LOG_DISTANCE", "STEM_LQ"]].values
        X_with_const = np.column_stack([np.ones(len(Y)), X_vars])

        try:
            # OLS via numpy
            betas, residuals, rank, sv = np.linalg.lstsq(X_with_const, Y, rcond=None)
            Y_pred = X_with_const @ betas
            ss_res = np.sum((Y - Y_pred) ** 2)
            ss_tot = np.sum((Y - Y.mean()) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            n = len(Y)
            k = X_with_const.shape[1]
            adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - k - 1) if n > k + 1 else r_squared

            beta_names = ["Intercept", "log(STEM_Jobs)", "log(Distance)", "STEM_LQ"]
            print(f"\n  Calibrated regression results:")
            print(f"  {'Variable':<20} {'Coefficient':>12}")
            print(f"  {'-'*32}")
            for name, b in zip(beta_names, betas):
                print(f"  {name:<20} {b:>12.4f}")
                regression_results[name] = round(b, 4)
            print(f"  R-squared:         {r_squared:.4f}")
            print(f"  Adj R-squared:     {adj_r_squared:.4f}")
            print(f"  N observations:    {n}")

            regression_results["R_squared"] = round(r_squared, 4)
            regression_results["Adj_R_squared"] = round(adj_r_squared, 4)
            regression_results["N"] = n

            # Distance decay interpretation
            dist_beta = betas[2]
            print(f"\n  >> Distance decay: beta = {dist_beta:.2f}")
            if dist_beta < -0.5:
                print(f"     Strong distance friction (graduates prefer nearby regions)")
            elif dist_beta < 0:
                print(f"     Moderate distance friction")
            else:
                print(f"     Weak/no distance friction (graduates willing to move far)")

            # STEM pull interpretation
            stem_beta = betas[1]
            print(f"  >> STEM jobs pull: beta = {stem_beta:.2f}")
            if stem_beta > 0.5:
                print(f"     Strong STEM pull (regions with more STEM jobs attract more graduates)")
            elif stem_beta > 0:
                print(f"     Moderate STEM pull effect")
            else:
                print(f"     No STEM pull effect detected")

            # Calibrated predictions for ALL provinces
            X_all = np.column_stack([
                np.ones(len(feat)),
                feat["LOG_STEM_JOBS"].values,
                feat["LOG_DISTANCE"].values,
                feat["STEM_LQ"].values,
            ])
            feat["LOG_FLOW_PRED"] = X_all @ betas
            feat["FLOW_PRED"] = np.exp(feat["LOG_FLOW_PRED"]).round(0).astype(int)
            feat["GRAVITY_PROB_CALIBRATED"] = (
                feat["FLOW_PRED"] / feat["FLOW_PRED"].sum() * 100
            ).round(2)

            print(f"\n  Calibrated destination probabilities:")
            compare = feat[["PROVINCE", "PCT_OF_TOTAL_OUTFLOW", "GRAVITY_PROB_CALIBRATED",
                           "GRAVITY_PROB_THEORY"]].copy()
            compare.columns = ["Province", "Observed_%", "Calibrated_%", "Theory_%"]
            compare = compare.sort_values("Calibrated_%", ascending=False)
            print(compare.to_string(index=False))

        except Exception as e:
            print(f"  [WARNING] Regression failed: {e}")
            print(f"  Using theoretical model only")
    else:
        print(f"  No observed flows for calibration -- using theoretical model")

    # -----------------------------------------------------------------------
    # 4. STEM occupation probability estimation
    # -----------------------------------------------------------------------
    print(f"\n  --- STEM Occupation Probability by Province ---")
    print(f"  Estimating P(STEM job | settling in province j)")

    # Logic: if a province has STEM LQ > 1, graduates there are more likely
    # to be in STEM. Scale by LQ as probability multiplier.
    # Base rate: ~35% of STEM graduates nationally end up in STEM occupations
    # (from WO-Monitor / HBO-Monitor typical figures)
    STEM_BASE_RATE = 0.35

    feat["P_STEM_JOB"] = (feat["STEM_LQ"] * STEM_BASE_RATE).clip(upper=0.90).round(3)
    feat["P_STEM_JOB_PCT"] = (feat["P_STEM_JOB"] * 100).round(1)

    # Expected STEM graduates per province
    # Total STEM grads from Groningen
    total_stem_grads = 0
    wo = results_a.get("WO_yearly")
    hbo = results_a.get("HBO_yearly")
    if wo is not None and "WO_STEM_GRADS" in wo.columns:
        total_stem_grads += wo["WO_STEM_GRADS"].iloc[-1]
    if hbo is not None and "HBO_STEM_GRADS" in hbo.columns:
        total_stem_grads += hbo["HBO_STEM_GRADS"].iloc[-1]
    total_stem_grads = int(total_stem_grads)

    if total_stem_grads > 0:
        # Use calibrated probabilities if available, else theoretical
        prob_col = "GRAVITY_PROB_CALIBRATED" if "GRAVITY_PROB_CALIBRATED" in feat.columns else "GRAVITY_PROB_THEORY"
        feat["EST_STEM_GRADS_ARRIVING"] = (feat[prob_col] / 100 * total_stem_grads).round(0).astype(int)
        feat["EST_IN_STEM_OCCUPATION"] = (feat["EST_STEM_GRADS_ARRIVING"] * feat["P_STEM_JOB"]).round(0).astype(int)
        feat["EST_IN_NON_STEM"] = feat["EST_STEM_GRADS_ARRIVING"] - feat["EST_IN_STEM_OCCUPATION"]
        print(f"\n  Based on {total_stem_grads} STEM graduates per year from Groningen:")
    else:
        print(f"  [NOTE] No graduate count available; showing proportions only")

    # -----------------------------------------------------------------------
    # 5. Build final map-ready output
    # -----------------------------------------------------------------------
    print(f"\n  --- MAP-READY OUTPUT ---")

    # Select and order columns for the map table
    map_cols = ["PROVINCE", "DISTANCE_KM", "POPULATION", "TOTAL_JOBS",
                "STEM_JOBS_EST", "STEM_LQ"]

    # Add individual LQ columns
    lq_cols = [c for c in feat.columns if c.startswith("LQ_")]
    map_cols.extend(sorted(lq_cols))

    map_cols.append("GRAVITY_PROB_THEORY")
    if "GRAVITY_PROB_CALIBRATED" in feat.columns:
        map_cols.append("GRAVITY_PROB_CALIBRATED")
    if "PCT_OF_TOTAL_OUTFLOW" in feat.columns:
        map_cols.append("PCT_OF_TOTAL_OUTFLOW")
    map_cols.extend(["P_STEM_JOB_PCT"])
    if "EST_STEM_GRADS_ARRIVING" in feat.columns:
        map_cols.extend(["EST_STEM_GRADS_ARRIVING", "EST_IN_STEM_OCCUPATION", "EST_IN_NON_STEM"])

    map_cols = [c for c in map_cols if c in feat.columns]
    map_df = feat[map_cols].sort_values(
        "GRAVITY_PROB_CALIBRATED" if "GRAVITY_PROB_CALIBRATED" in feat.columns else "GRAVITY_PROB_THEORY",
        ascending=False
    ).reset_index(drop=True)
    map_df.index += 1
    map_df.index.name = "RANK"

    # Add province centroids for direct map plotting (lat/lon)
    PROVINCE_CENTROIDS = {
        "Groningen": (53.22, 6.57), "Friesland": (53.16, 5.78),
        "Drenthe": (52.95, 6.62), "Overijssel": (52.44, 6.50),
        "Flevoland": (52.53, 5.47), "Gelderland": (52.05, 5.87),
        "Utrecht": (52.09, 5.11), "Noord-Holland": (52.67, 4.81),
        "Zuid-Holland": (52.03, 4.49), "Zeeland": (51.49, 3.83),
        "Noord-Brabant": (51.57, 5.14), "Limburg": (51.21, 5.94),
    }
    map_df["LAT"] = map_df["PROVINCE"].map(lambda p: PROVINCE_CENTROIDS.get(p, (np.nan,))[0])
    map_df["LON"] = map_df["PROVINCE"].map(lambda p: PROVINCE_CENTROIDS.get(p, (np.nan, np.nan))[1])

    print(f"\n  Map-ready table (sorted by predicted flow probability):")
    display_cols = ["PROVINCE", "STEM_LQ", "DISTANCE_KM"]
    if "GRAVITY_PROB_CALIBRATED" in map_df.columns:
        display_cols.append("GRAVITY_PROB_CALIBRATED")
    display_cols.append("GRAVITY_PROB_THEORY")
    if "PCT_OF_TOTAL_OUTFLOW" in map_df.columns:
        display_cols.append("PCT_OF_TOTAL_OUTFLOW")
    display_cols.append("P_STEM_JOB_PCT")
    if "EST_STEM_GRADS_ARRIVING" in map_df.columns:
        display_cols.extend(["EST_STEM_GRADS_ARRIVING", "EST_IN_STEM_OCCUPATION"])
    print(map_df[display_cols].to_string())

    # Save
    map_path = os.path.join(out_dir, "table_E1_gravity_model_map.csv")
    map_df.to_csv(map_path)
    print(f"\n  [OK] {map_path}")

    results_grav["map_table"] = map_df
    results_grav["feature_table"] = feat
    results_grav["regression"] = regression_results

    # Save regression summary
    if regression_results:
        reg_df = pd.DataFrame([
            {"Variable": k, "Value": v} for k, v in regression_results.items()
        ])
        reg_path = os.path.join(out_dir, "table_E2_regression_coefficients.csv")
        reg_df.to_csv(reg_path, index=False)
        print(f"  [OK] {reg_path}")
        results_grav["regression_df"] = reg_df

    # -----------------------------------------------------------------------
    # 6. Charts
    # -----------------------------------------------------------------------
    if HAS_PLOT:
        # Chart E1: Gravity model scatter (predicted vs observed)
        if has_observed and "GRAVITY_PROB_CALIBRATED" in feat.columns:
            try:
                fig, axes = plt.subplots(1, 2, figsize=(14, 6))

                # Left: Predicted vs Observed
                ax = axes[0]
                valid = feat[feat["PCT_OF_TOTAL_OUTFLOW"] > 0]
                ax.scatter(valid["PCT_OF_TOTAL_OUTFLOW"], valid["GRAVITY_PROB_CALIBRATED"],
                           s=100, c="#2196F3", edgecolors="black", zorder=5)
                for _, row in valid.iterrows():
                    ax.annotate(row["PROVINCE"],
                                (row["PCT_OF_TOTAL_OUTFLOW"], row["GRAVITY_PROB_CALIBRATED"]),
                                textcoords="offset points", xytext=(5, 5), fontsize=8)
                max_val = max(valid["PCT_OF_TOTAL_OUTFLOW"].max(),
                              valid["GRAVITY_PROB_CALIBRATED"].max())
                ax.plot([0, max_val * 1.1], [0, max_val * 1.1], "r--", alpha=0.4,
                        label="Perfect prediction")
                ax.set_xlabel("Observed % of Outflow")
                ax.set_ylabel("Predicted % of Outflow (Gravity Model)")
                ax.set_title("Model Fit: Predicted vs Observed")
                ax.legend()

                # Right: Distance decay
                ax2 = axes[1]
                ax2.scatter(feat["DISTANCE_KM"], feat["GRAVITY_PROB_CALIBRATED"],
                            s=feat["STEM_LQ"] * 80, c=feat["STEM_LQ"],
                            cmap="RdYlGn", edgecolors="black", zorder=5)
                for _, row in feat.iterrows():
                    ax2.annotate(row["PROVINCE"],
                                 (row["DISTANCE_KM"], row["GRAVITY_PROB_CALIBRATED"]),
                                 textcoords="offset points", xytext=(3, 3), fontsize=7)
                ax2.set_xlabel("Distance from Groningen (km)")
                ax2.set_ylabel("Predicted Flow %")
                ax2.set_title("Distance Decay (bubble size = STEM LQ)")
                sm = plt.cm.ScalarMappable(cmap="RdYlGn",
                                           norm=plt.Normalize(feat["STEM_LQ"].min(),
                                                              feat["STEM_LQ"].max()))
                sm.set_array([])
                plt.colorbar(sm, ax=ax2, label="STEM LQ")

                plt.suptitle("Gravity Model: Where Do Groningen STEM Graduates Go?", fontsize=13)
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, "chart_E1_gravity_model.png"), dpi=150)
                plt.close()
                print(f"  [OK] chart_E1_gravity_model.png")
            except Exception as e:
                print(f"  [WARNING] Chart E1 failed: {e}")

        # Chart E2: Map-style bubble plot (lat/lon)
        try:
            fig, ax = plt.subplots(figsize=(10, 10))
            prob_col = "GRAVITY_PROB_CALIBRATED" if "GRAVITY_PROB_CALIBRATED" in map_df.columns else "GRAVITY_PROB_THEORY"

            # Plot Groningen as origin
            gron_lat, gron_lon = PROVINCE_CENTROIDS["Groningen"]
            ax.scatter([gron_lon], [gron_lat], s=300, c="red", marker="*",
                       zorder=10, label="Groningen (origin)")
            ax.annotate("GRONINGEN", (gron_lon, gron_lat),
                        textcoords="offset points", xytext=(10, 10),
                        fontsize=10, fontweight="bold", color="red")

            # Plot destinations as bubbles
            scatter = ax.scatter(
                map_df["LON"], map_df["LAT"],
                s=map_df[prob_col] * 30,  # size = probability
                c=map_df["P_STEM_JOB_PCT"],  # color = STEM job probability
                cmap="RdYlGn", edgecolors="black", alpha=0.7, zorder=5
            )
            for _, row in map_df.iterrows():
                label = f"{row['PROVINCE']}\n{row[prob_col]:.1f}%"
                ax.annotate(label, (row["LON"], row["LAT"]),
                            textcoords="offset points", xytext=(8, -5), fontsize=7)

                # Draw flow line from Groningen
                ax.plot([gron_lon, row["LON"]], [gron_lat, row["LAT"]],
                        "b-", alpha=row[prob_col] / 100 * 2, linewidth=row[prob_col] / 5)

            plt.colorbar(scatter, label="P(STEM occupation) %", shrink=0.6)
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.set_title(f"Predicted STEM Graduate Flows from Groningen\n"
                         f"Bubble size = flow probability, Color = STEM occupation chance")
            ax.legend(loc="lower left")
            ax.set_xlim(3.0, 7.5)
            ax.set_ylim(50.8, 53.7)
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, "chart_E2_flow_map.png"), dpi=150)
            plt.close()
            print(f"  [OK] chart_E2_flow_map.png")
        except Exception as e:
            print(f"  [WARNING] Chart E2 failed: {e}")

        # Chart E3: STEM occupation breakdown (stacked bar)
        if "EST_STEM_GRADS_ARRIVING" in feat.columns:
            try:
                fig, ax = plt.subplots(figsize=(10, 6))
                plot_df = feat.sort_values("EST_STEM_GRADS_ARRIVING", ascending=True)
                ax.barh(range(len(plot_df)), plot_df["EST_IN_STEM_OCCUPATION"],
                        color="#2196F3", label="In STEM occupation")
                ax.barh(range(len(plot_df)), plot_df["EST_IN_NON_STEM"],
                        left=plot_df["EST_IN_STEM_OCCUPATION"],
                        color="#FF9800", label="In non-STEM occupation")
                ax.set_yticks(range(len(plot_df)))
                ax.set_yticklabels(plot_df["PROVINCE"])
                ax.set_xlabel("Estimated STEM Graduates from Groningen")
                ax.set_title("Where Do Groningen STEM Graduates End Up?")
                ax.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, "chart_E3_stem_occupation_breakdown.png"), dpi=150)
                plt.close()
                print(f"  [OK] chart_E3_stem_occupation_breakdown.png")
            except Exception as e:
                print(f"  [WARNING] Chart E3 failed: {e}")

    return results_grav


# ---------------------------------------------------------------------------
# STEP 9: Clean output tables + charts
# ---------------------------------------------------------------------------
def step9_export_tables(results_a, results_b, results_c, results_d, out_dir,
                         results_grav=None):
    """Produce clean, directly usable output tables and charts."""
    print("\n" + "=" * 60)
    print("=== STEP 9: EXPORTING CLEAN TABLES & CHARTS ===")
    print("=" * 60)

    if results_grav is None:
        results_grav = {}

    tables = {}  # name -> DataFrame for Excel workbook

    # -----------------------------------------------------------------------
    # TABLE 1: STEM Graduates Annual (combined WO + HBO)
    # -----------------------------------------------------------------------
    wo = results_a.get("WO_yearly")
    hbo = results_a.get("HBO_yearly")
    if wo is not None or hbo is not None:
        dfs = []
        if wo is not None:
            dfs.append(wo)
        if hbo is not None:
            dfs.append(hbo)
        t1 = pd.concat(dfs, axis=1).fillna(0)
        # Add combined columns
        stem_cols = [c for c in t1.columns if "STEM_GRADS" in c and "NON" not in c]
        nonstem_cols = [c for c in t1.columns if "NONSTEM_GRADS" in c]
        if stem_cols:
            t1["TOTAL_STEM"] = t1[stem_cols].sum(axis=1).astype(int)
        if nonstem_cols:
            t1["TOTAL_NONSTEM"] = t1[nonstem_cols].sum(axis=1).astype(int)
        if "TOTAL_STEM" in t1.columns and "TOTAL_NONSTEM" in t1.columns:
            total = t1["TOTAL_STEM"] + t1["TOTAL_NONSTEM"]
            t1["TOTAL_STEM_PCT"] = (t1["TOTAL_STEM"] / total * 100).round(1)
        t1.index.name = "YEAR"
        t1.to_csv(os.path.join(out_dir, "table_A1_stem_graduates_annual.csv"))
        tables["A1_STEM_Graduates"] = t1
        print(f"  [OK] table_A1_stem_graduates_annual.csv")
        print(t1.to_string())

    # -----------------------------------------------------------------------
    # TABLE 2: Gender by Sector
    # -----------------------------------------------------------------------
    for level in ["WO", "HBO"]:
        for suffix in ["_gender", "_gender_inschrijvingen"]:
            key = f"{level}{suffix}"
            if key in results_a:
                t2 = results_a[key].copy()
                fname = f"table_A2_gender_{level.lower()}.csv"
                t2.to_csv(os.path.join(out_dir, fname), index=False)
                tables[f"A2_Gender_{level}"] = t2
                print(f"  [OK] {fname}")
                break

    # -----------------------------------------------------------------------
    # TABLE 3: Province-level Location Quotients
    # -----------------------------------------------------------------------
    if "lq" in results_b:
        t3 = results_b["lq"].copy()
        t3.to_csv(os.path.join(out_dir, "table_B1_province_lq.csv"))
        tables["B1_Province_LQ"] = t3
        print(f"  [OK] table_B1_province_lq.csv")

    # -----------------------------------------------------------------------
    # TABLE 4: COROP-level Location Quotients
    # -----------------------------------------------------------------------
    if "corop_lq" in results_b:
        t4 = results_b["corop_lq"].copy()
        t4.to_csv(os.path.join(out_dir, "table_B2_corop_lq.csv"))
        tables["B2_COROP_LQ"] = t4
        print(f"  [OK] table_B2_corop_lq.csv")

    # -----------------------------------------------------------------------
    # TABLE 5: Groningen Sector Employment Detail
    # -----------------------------------------------------------------------
    if "groningen_sector_detail" in results_b:
        t5 = results_b["groningen_sector_detail"].reset_index()
        t5.columns = ["Sector", "Jobs"]
        t5["Is_STEM"] = t5["Sector"].isin(LISA_STEM_SECTORS.keys())
        t5["Pct_of_Total"] = (t5["Jobs"] / t5["Jobs"].sum() * 100).round(1)
        t5.to_csv(os.path.join(out_dir, "table_B3_groningen_jobs.csv"), index=False)
        tables["B3_Groningen_Jobs"] = t5
        print(f"  [OK] table_B3_groningen_jobs.csv")

    # -----------------------------------------------------------------------
    # TABLE 6: Net Migration (if available)
    # -----------------------------------------------------------------------
    if "yearly_migration" in results_c:
        t6 = results_c["yearly_migration"].copy()
        # Rename columns to readable names
        rename_map = {
            "G_20_25": "Settled_20_25", "V_20_25": "Departed_20_25",
            "G_25_30": "Settled_25_30", "V_25_30": "Departed_25_30",
            "NET_20_25": "Net_20_25", "NET_25_30": "Net_25_30",
            "RETENTION_25_30": "Retention_Rate_25_30_pct",
        }
        t6 = t6.rename(columns={k: v for k, v in rename_map.items() if k in t6.columns})
        t6.to_csv(os.path.join(out_dir, "table_C1_net_migration.csv"), index=False)
        tables["C1_Net_Migration"] = t6
        print(f"  [OK] table_C1_net_migration.csv")

    # -----------------------------------------------------------------------
    # TABLE 7: Destination Provinces
    # -----------------------------------------------------------------------
    if "province_destinations" in results_c:
        t7 = results_c["province_destinations"].copy()
        # Merge with LQ data to show the connection
        if "lq" in results_b:
            lq = results_b["lq"][["REGION", "STEM_LQ_COMPOSITE"]].copy()
            lq = lq.rename(columns={"REGION": "DESTINATION_PROVINCE"})
            t7 = t7.merge(lq, on="DESTINATION_PROVINCE", how="left")
        t7.to_csv(os.path.join(out_dir, "table_C2_destination_provinces.csv"), index=False)
        tables["C2_Destinations"] = t7
        print(f"  [OK] table_C2_destination_provinces.csv")
        print(t7.to_string(index=False))

    # -----------------------------------------------------------------------
    # TABLE 8: LQ vs Outflow Correlation (KEY ANALYTICAL TABLE)
    # -----------------------------------------------------------------------
    if "lq" in results_b and "province_destinations" in results_c:
        lq = results_b["lq"][["REGION", "STEM_LQ_COMPOSITE"]].copy()
        dest = results_c["province_destinations"].copy()
        lq = lq.rename(columns={"REGION": "PROVINCE"})
        dest = dest.rename(columns={"DESTINATION_PROVINCE": "PROVINCE"})
        t8 = dest.merge(lq, on="PROVINCE", how="inner")
        t8 = t8[t8["PROVINCE"] != "Groningen"]  # exclude self
        t8 = t8[t8["PROVINCE"] != "Overig/Onbekend"]
        t8 = t8.sort_values("STEM_LQ_COMPOSITE", ascending=False)

        if len(t8) >= 3:
            # Calculate correlation
            from scipy import stats as scipy_stats
            try:
                r, p = scipy_stats.pearsonr(t8["STEM_LQ_COMPOSITE"], t8["PCT_OF_TOTAL_OUTFLOW"])
                t8.attrs["pearson_r"] = round(r, 3)
                t8.attrs["pearson_p"] = round(p, 3)
                print(f"\n  >> CORRELATION: Pearson r = {r:.3f}, p = {p:.3f}")
                if p < 0.05:
                    print(f"     Statistically significant at 5% level")
                else:
                    print(f"     Not significant (p > 0.05) -- small sample ({len(t8)} provinces)")
            except Exception:
                pass

            # Also try with mobility intensity
            t8_valid = t8.dropna(subset=["MOBILITY_INTENSITY"])
            if len(t8_valid) >= 3:
                try:
                    r2, p2 = scipy_stats.pearsonr(t8_valid["STEM_LQ_COMPOSITE"],
                                                   t8_valid["MOBILITY_INTENSITY"])
                    print(f"     INTENSITY correlation: r = {r2:.3f}, p = {p2:.3f}")
                except Exception:
                    pass

        t8.to_csv(os.path.join(out_dir, "table_D1_lq_vs_outflow.csv"), index=False)
        tables["D1_LQ_vs_Outflow"] = t8
        print(f"  [OK] table_D1_lq_vs_outflow.csv")
        print(t8.to_string(index=False))

    # -----------------------------------------------------------------------
    # TABLE 9: Summary Key Figures
    # -----------------------------------------------------------------------
    summary_rows = []

    def add_metric(metric, value, unit="", source="", year="", caveat=""):
        summary_rows.append({
            "METRIC": metric, "VALUE": value, "UNIT": unit,
            "SOURCE": source, "YEAR": year, "CAVEAT": caveat,
        })

    if wo is not None and len(wo) > 0:
        add_metric("WO STEM graduates", int(wo["WO_STEM_GRADS"].iloc[-1]),
                   "persons", "DUO", str(wo.index[-1]))
        add_metric("WO STEM share", round(wo["WO_STEM_PCT"].iloc[-1], 1),
                   "%", "DUO", str(wo.index[-1]))
    if hbo is not None and len(hbo) > 0:
        add_metric("HBO STEM graduates", int(hbo["HBO_STEM_GRADS"].iloc[-1]),
                   "persons", "DUO", str(hbo.index[-1]))
        add_metric("HBO STEM share", round(hbo["HBO_STEM_PCT"].iloc[-1], 1),
                   "%", "DUO", str(hbo.index[-1]))
    if wo is not None and hbo is not None:
        combined = int(wo["WO_STEM_GRADS"].iloc[-1] + hbo["HBO_STEM_GRADS"].iloc[-1])
        add_metric("Total STEM graduates (WO+HBO)", combined, "persons", "DUO")
    if "groningen_lq" in results_b:
        add_metric("Groningen STEM LQ (province)", results_b["groningen_lq"],
                   "ratio", "LISA", str(results_b.get("lisa_year", "")),
                   "1.0 = national average")
        add_metric("Groningen province STEM rank",
                   f"{results_b['groningen_rank']}/{results_b['total_regions']}",
                   "rank", "LISA")
    if "groningen_corop_lq" in results_b:
        add_metric("Groningen COROP STEM LQ", results_b["groningen_corop_lq"],
                   "ratio", "LISA")
        add_metric("Groningen COROP STEM rank",
                   f"{results_b['groningen_corop_rank']}/{results_b['total_corop_regions']}",
                   "rank", "LISA")
    if "lisa_stem_pct" in results_b:
        add_metric("Groningen STEM employment share", round(results_b["lisa_stem_pct"], 1),
                   "%", "LISA", "", "Includes L10 Zakelijke diensten")
        add_metric("Groningen total jobs", int(results_b["lisa_total_jobs"]),
                   "jobs", "LISA")
    if "yearly_migration" in results_c:
        mig = results_c["yearly_migration"]
        add_metric("Avg net migration 25-30", round(mig["NET_25_30"].mean()),
                   "persons/year", "CBS", f"{mig.iloc[0, 0]}-{mig.iloc[-1, 0]}",
                   "All movers, not only graduates")

    if summary_rows:
        t9 = pd.DataFrame(summary_rows)
        t9.to_csv(os.path.join(out_dir, "table_SUMMARY_key_figures.csv"), index=False)
        tables["SUMMARY"] = t9
        print(f"\n  [OK] table_SUMMARY_key_figures.csv")
        print(t9.to_string(index=False))

    # -----------------------------------------------------------------------
    # Gravity model tables (from step 11)
    # -----------------------------------------------------------------------
    if "map_table" in results_grav:
        tables["E1_Gravity_Map"] = results_grav["map_table"]
        print(f"  [OK] table_E1_gravity_model_map.csv (from step 11)")
    if "regression_df" in results_grav:
        tables["E2_Regression"] = results_grav["regression_df"]
        print(f"  [OK] table_E2_regression_coefficients.csv (from step 11)")

    # -----------------------------------------------------------------------
    # EXCEL WORKBOOK (all tables as sheets)
    # -----------------------------------------------------------------------
    try:
        xlsx_path = os.path.join(out_dir, "GEMRAMA_all_tables.xlsx")
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            for sheet_name, df in tables.items():
                # Excel sheet names max 31 chars
                sn = sheet_name[:31]
                df.to_csv  # ensure it's a DataFrame
                df.to_excel(writer, sheet_name=sn, index=True)
        print(f"\n  [OK] GEMRAMA_all_tables.xlsx ({len(tables)} sheets)")
    except Exception as e:
        print(f"  [WARNING] Could not write Excel workbook: {e}")

    # -----------------------------------------------------------------------
    # CHARTS
    # -----------------------------------------------------------------------
    if HAS_PLOT:
        print(f"\n  --- Generating charts ---")
        plt.style.use("seaborn-v0_8-whitegrid") if "seaborn-v0_8-whitegrid" in plt.style.available else None
        chart_count = 0

        # CHART 1: STEM graduates trend
        if "A1_STEM_Graduates" in tables:
            try:
                fig, ax1 = plt.subplots(figsize=(10, 6))
                t = tables["A1_STEM_Graduates"]
                x = t.index.astype(str)
                width = 0.35
                x_pos = np.arange(len(x))

                bars1 = ax1.bar(x_pos - width/2, t.get("WO_STEM_GRADS", pd.Series(dtype=float)),
                                width, label="WO STEM", color="#2196F3")
                bars2 = ax1.bar(x_pos + width/2, t.get("HBO_STEM_GRADS", pd.Series(dtype=float)),
                                width, label="HBO STEM", color="#FF9800")
                ax1.set_xlabel("Year")
                ax1.set_ylabel("Number of STEM Graduates")
                ax1.set_xticks(x_pos)
                ax1.set_xticklabels(x)
                ax1.legend(loc="upper left")

                if "TOTAL_STEM_PCT" in t.columns:
                    ax2 = ax1.twinx()
                    ax2.plot(x_pos, t["TOTAL_STEM_PCT"], "r-o", linewidth=2,
                             label="STEM % of total")
                    ax2.set_ylabel("STEM % of Total Graduates")
                    ax2.legend(loc="upper right")

                ax1.set_title("STEM Graduates from Groningen Institutions (WO + HBO)")
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, "chart_A1_stem_graduates_trend.png"), dpi=150)
                plt.close()
                chart_count += 1
                print(f"  [OK] chart_A1_stem_graduates_trend.png")
            except Exception as e:
                print(f"  [WARNING] Chart A1 failed: {e}")

        # CHART 2: Province LQ heatmap
        if "B1_Province_LQ" in tables:
            try:
                t = tables["B1_Province_LQ"].copy()
                lq_cols = [c for c in t.columns if c.startswith("LQ_")]
                if lq_cols:
                    plot_data = t.set_index("REGION")[lq_cols]
                    # Shorten column names
                    plot_data.columns = [c.replace("LQ_", "").split("_")[0] for c in plot_data.columns]

                    fig, ax = plt.subplots(figsize=(10, 8))
                    sns.heatmap(plot_data, annot=True, fmt=".2f", cmap="RdYlGn",
                                center=1.0, linewidths=0.5, ax=ax,
                                cbar_kws={"label": "Location Quotient"})
                    ax.set_title(f"STEM Location Quotients by Province (LISA {results_b.get('lisa_year', '')})")
                    ax.set_ylabel("")

                    # Highlight Groningen
                    for i, region in enumerate(plot_data.index):
                        if "Groningen" in str(region):
                            ax.get_yticklabels()[i].set_weight("bold")
                            ax.get_yticklabels()[i].set_color("red")

                    plt.tight_layout()
                    plt.savefig(os.path.join(out_dir, "chart_B1_province_lq_heatmap.png"), dpi=150)
                    plt.close()
                    chart_count += 1
                    print(f"  [OK] chart_B1_province_lq_heatmap.png")
            except Exception as e:
                print(f"  [WARNING] Chart B1 failed: {e}")

        # CHART 3: COROP top 20
        if "B2_COROP_LQ" in tables:
            try:
                t = tables["B2_COROP_LQ"].head(20).copy()
                fig, ax = plt.subplots(figsize=(10, 8))
                colors = ["#e74c3c" if "Groningen" in str(r) else "#3498db"
                          for r in t["COROP_REGION"]]
                ax.barh(range(len(t)), t["STEM_LQ_COMPOSITE"], color=colors)
                ax.set_yticks(range(len(t)))
                ax.set_yticklabels(t["COROP_REGION"], fontsize=8)
                ax.axvline(x=1.0, color="black", linestyle="--", alpha=0.5, label="National avg")
                ax.set_xlabel("Composite STEM LQ")
                ax.set_title("Top 20 COROP Regions by STEM Specialization")
                ax.invert_yaxis()
                ax.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, "chart_B2_corop_lq_top20.png"), dpi=150)
                plt.close()
                chart_count += 1
                print(f"  [OK] chart_B2_corop_lq_top20.png")
            except Exception as e:
                print(f"  [WARNING] Chart B2 failed: {e}")

        # CHART 4: Net migration time series
        if "C1_Net_Migration" in tables:
            try:
                t = tables["C1_Net_Migration"]
                year_col = t.columns[0]  # first column is year
                fig, ax = plt.subplots(figsize=(10, 6))
                if "Net_20_25" in t.columns:
                    ax.plot(t[year_col].astype(str), t["Net_20_25"], "b-o",
                            label="Net 20-25 (students)", linewidth=2)
                if "Net_25_30" in t.columns:
                    ax.plot(t[year_col].astype(str), t["Net_25_30"], "r-s",
                            label="Net 25-30 (graduates)", linewidth=2)
                ax.axhline(y=0, color="black", linestyle="-", alpha=0.3)
                ax.fill_between(range(len(t)), t.get("Net_25_30", 0), 0,
                                alpha=0.1, color="red")
                ax.set_xlabel("Year")
                ax.set_ylabel("Net Migration (positive = inflow)")
                ax.set_title("Net Migration Groningen by Age Group")
                ax.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, "chart_C1_net_migration.png"), dpi=150)
                plt.close()
                chart_count += 1
                print(f"  [OK] chart_C1_net_migration.png")
            except Exception as e:
                print(f"  [WARNING] Chart C1 failed: {e}")

        # CHART 5: Destination flow bars
        if "C2_Destinations" in tables:
            try:
                t = tables["C2_Destinations"]
                t = t[t["DESTINATION_PROVINCE"] != "Overig/Onbekend"].head(10)
                fig, ax = plt.subplots(figsize=(10, 6))

                # Color by STEM LQ if available
                if "STEM_LQ_COMPOSITE" in t.columns:
                    norm = plt.Normalize(t["STEM_LQ_COMPOSITE"].min(),
                                         t["STEM_LQ_COMPOSITE"].max())
                    colors = plt.cm.RdYlGn(norm(t["STEM_LQ_COMPOSITE"]))
                else:
                    colors = "#3498db"

                ax.barh(range(len(t)), t["PCT_OF_TOTAL_OUTFLOW"], color=colors)
                ax.set_yticks(range(len(t)))
                ax.set_yticklabels(t["DESTINATION_PROVINCE"])
                ax.set_xlabel("% of Total Outflow from Groningen")
                ax.set_title("Where Do People Leaving Groningen Go?")
                ax.invert_yaxis()

                if "STEM_LQ_COMPOSITE" in t.columns:
                    sm = plt.cm.ScalarMappable(cmap="RdYlGn", norm=norm)
                    sm.set_array([])
                    cbar = plt.colorbar(sm, ax=ax)
                    cbar.set_label("STEM LQ (color)")

                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, "chart_C2_destination_flow.png"), dpi=150)
                plt.close()
                chart_count += 1
                print(f"  [OK] chart_C2_destination_flow.png")
            except Exception as e:
                print(f"  [WARNING] Chart C2 failed: {e}")

        # CHART 6: LQ vs Outflow scatter (THE KEY CHART)
        if "D1_LQ_vs_Outflow" in tables:
            try:
                t = tables["D1_LQ_vs_Outflow"]
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.scatter(t["STEM_LQ_COMPOSITE"], t["PCT_OF_TOTAL_OUTFLOW"],
                           s=100, c="#2196F3", edgecolors="black", zorder=5)

                # Label each point
                for _, row in t.iterrows():
                    ax.annotate(row["PROVINCE"],
                                (row["STEM_LQ_COMPOSITE"], row["PCT_OF_TOTAL_OUTFLOW"]),
                                textcoords="offset points", xytext=(5, 5), fontsize=8)

                # Trend line
                if len(t) >= 3:
                    z = np.polyfit(t["STEM_LQ_COMPOSITE"], t["PCT_OF_TOTAL_OUTFLOW"], 1)
                    p = np.poly1d(z)
                    x_line = np.linspace(t["STEM_LQ_COMPOSITE"].min(),
                                         t["STEM_LQ_COMPOSITE"].max(), 100)
                    ax.plot(x_line, p(x_line), "r--", alpha=0.5, label="Trend")

                ax.axvline(x=1.0, color="gray", linestyle=":", alpha=0.5,
                           label="National avg LQ")
                ax.set_xlabel("STEM Location Quotient (province)")
                ax.set_ylabel("% of Groningen Outflow to Province")
                ax.set_title("Do Graduates Move to STEM-Specialized Regions?")
                ax.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, "chart_D1_lq_vs_outflow_scatter.png"), dpi=150)
                plt.close()
                chart_count += 1
                print(f"  [OK] chart_D1_lq_vs_outflow_scatter.png")
            except Exception as e:
                print(f"  [WARNING] Chart D1 failed: {e}")

        # CHART 7: Groningen jobs by sector
        if "B3_Groningen_Jobs" in tables:
            try:
                t = tables["B3_Groningen_Jobs"].sort_values("Jobs", ascending=True)
                fig, ax = plt.subplots(figsize=(10, 7))
                colors = ["#e74c3c" if s else "#95a5a6" for s in t["Is_STEM"]]
                ax.barh(range(len(t)), t["Jobs"], color=colors)
                ax.set_yticks(range(len(t)))
                ax.set_yticklabels(t["Sector"], fontsize=8)
                ax.set_xlabel("Number of Jobs")
                ax.set_title("Employment by Sector in Groningen (LISA)\nRed = STEM sectors")
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, "chart_B3_groningen_jobs.png"), dpi=150)
                plt.close()
                chart_count += 1
                print(f"  [OK] chart_B3_groningen_jobs.png")
            except Exception as e:
                print(f"  [WARNING] Chart B3 failed: {e}")

        print(f"\n  Generated {chart_count} charts")
    else:
        print(f"  [SKIP] Charts -- install matplotlib and seaborn")

    return tables


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Graduate Mobility Analysis")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(args.data_dir) if args.data_dir else script_dir
    out_dir = os.path.abspath(args.output_dir) if args.output_dir else data_dir

    print("=" * 60)
    print("GEMRAMA: Graduate Mobility & Regional Industrial Structure")
    print(f"Data directory: {data_dir}")
    print(f"Output directory: {out_dir}")
    print("=" * 60)

    # List data files
    print(f"\nFiles in data directory:")
    try:
        for fn in sorted(os.listdir(data_dir)):
            if fn.endswith((".csv", ".xlsx", ".xls")):
                size = os.path.getsize(os.path.join(data_dir, fn))
                print(f"  {fn} ({size:,} bytes)")
    except Exception as e:
        print(f"  [ERROR] {e}")

    found, missing = step0_file_check(data_dir)
    loaded = step1_inspect(found)
    step2_stem_classification()
    results_a = step3_analysis_a(loaded, out_dir)
    results_b = step4_analysis_b(loaded, out_dir)
    results_c = step5_analysis_c(loaded, out_dir)
    results_d = step6_analysis_d(loaded, out_dir)
    step7_synthesis(results_a, results_b, results_c, results_d, out_dir)
    step8_data_quality(missing, out_dir)
    step10_quality_checks(results_a)

    # Gravity model for STEM destination prediction
    results_grav = step11_gravity_model(results_a, results_b, results_c, out_dir)

    # Export clean tables and charts
    tables = step9_export_tables(results_a, results_b, results_c, results_d, out_dir,
                                 results_grav=results_grav)

    print("\n" + "=" * 60)
    print("=== FINAL STATUS ===")
    print("=" * 60)
    if not missing:
        print("  All files present, all analyses ran")
    else:
        print(f"  {len(missing)} files missing -- partial analysis")
        print(f"  Missing: {', '.join(missing)}")

    print(f"\n  === OUTPUT FILES IN: {out_dir} ===")
    print(f"\n  CLEAN TABLES (directly usable in Excel/ArcGIS):")
    table_files = [
        ("table_A1_stem_graduates_annual.csv", "STEM grads by year (WO+HBO) -> time series chart"),
        ("table_A2_gender_wo.csv",             "Gender breakdown by sector -> bar chart"),
        ("table_B1_province_lq.csv",           "Province LQ -> choropleth map"),
        ("table_B2_corop_lq.csv",              "COROP LQ -> detailed choropleth map"),
        ("table_B3_groningen_jobs.csv",         "Groningen jobs by sector -> pie/bar chart"),
        ("table_C1_net_migration.csv",          "Net migration by age -> time series"),
        ("table_C2_destination_provinces.csv",  "Where grads go + LQ -> flow map"),
        ("table_D1_lq_vs_outflow.csv",          "LQ vs outflow correlation -> scatter plot"),
        ("table_E1_gravity_model_map.csv",      "GRAVITY MODEL: predicted flows + STEM job prob -> MAP"),
        ("table_E2_regression_coefficients.csv", "Regression coefficients for gravity model"),
        ("table_SUMMARY_key_figures.csv",       "All key numbers in one table"),
        ("GEMRAMA_all_tables.xlsx",             "ALL tables in one Excel workbook"),
    ]
    for fn, desc in table_files:
        fp = os.path.join(out_dir, fn)
        status = "[OK]" if os.path.isfile(fp) else "[--]"
        print(f"    {status} {fn}")
        print(f"         -> {desc}")

    print(f"\n  CHARTS (PNG, ready for StoryMap):")
    chart_files = [
        ("chart_A1_stem_graduates_trend.png",   "STEM graduate trend (bar + line)"),
        ("chart_B1_province_lq_heatmap.png",    "Province LQ heatmap"),
        ("chart_B2_corop_lq_top20.png",         "Top 20 COROP regions"),
        ("chart_B3_groningen_jobs.png",          "Groningen sector employment"),
        ("chart_C1_net_migration.png",           "Net migration time series"),
        ("chart_C2_destination_flow.png",        "Destination flow bars (colored by LQ)"),
        ("chart_D1_lq_vs_outflow_scatter.png",   "LQ vs outflow scatter"),
        ("chart_E1_gravity_model.png",           "Gravity model: predicted vs observed + distance decay"),
        ("chart_E2_flow_map.png",                "FLOW MAP: bubbles on NL map (lat/lon)"),
        ("chart_E3_stem_occupation_breakdown.png","STEM vs non-STEM occupation by province"),
    ]
    for fn, desc in chart_files:
        fp = os.path.join(out_dir, fn)
        status = "[OK]" if os.path.isfile(fp) else "[--]"
        print(f"    {status} {fn}")
        print(f"         -> {desc}")

    print(f"\n  NARRATIVE:")
    for fn in ["output_SYNTHESIS.txt", "output_DATA_QUALITY.txt"]:
        fp = os.path.join(out_dir, fn)
        print(f"    {'[OK]' if os.path.isfile(fp) else '[--]'} {fn}")


if __name__ == "__main__":
    main()

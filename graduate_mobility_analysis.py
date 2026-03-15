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

    print("\n" + "=" * 60)
    print("=== FINAL STATUS ===")
    print("=" * 60)
    if not missing:
        print("  All files present, all analyses ran")
    else:
        print(f"  {len(missing)} files missing -- partial analysis")
        print(f"  Missing: {', '.join(missing)}")

    print(f"\n  Output files in: {out_dir}")
    for fn in ["output_A_stem_pipeline_groningen.csv",
               "output_B_location_quotients.csv",
               "output_C_mobility_flows.csv",
               "output_D_match_analysis.csv",
               "output_SYNTHESIS.txt",
               "output_DATA_QUALITY.txt"]:
        fp = os.path.join(out_dir, fn)
        print(f"    {'[OK]' if os.path.isfile(fp) else '[--]'} {fn}")


if __name__ == "__main__":
    main()

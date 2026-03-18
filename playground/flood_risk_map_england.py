#!/usr/bin/env python3
"""
Flood Risk Map of England with LAD (Local Authority District) Boundaries
========================================================================

Creates a standalone static PNG map showing Environment Agency Flood Zones
overlaid on England's Local Authority District boundaries.

Data sources:
  - Flood zones: EA "Flood Map for Planning" GeoPackage (.gpkg)
    Download: https://environment.data.gov.uk/
  - LAD boundaries: ONS Open Geography Portal (auto-downloaded)

Usage:
    python flood_risk_map_england.py --flood-gpkg "path/to/Flood_Map_for_Planning_Flood_Zones.gpkg"

    # Or set the path in the CONFIG section below.
"""

import argparse
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# CONFIG – edit these if you don't want to pass command-line arguments
# ---------------------------------------------------------------------------
DEFAULT_FLOOD_GPKG = r"C:\Users\NL1E9O\Downloads\Flood\Flood_Map_for_Planning_Flood_Zones.gpkg"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILENAME = "flood_risk_map_england.png"

# ONS LAD Boundaries (December 2023, BFC – full resolution)
# Using the GeoJSON endpoint from the ONS Open Geography Portal
LAD_BOUNDARIES_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "Local_Authority_Districts_December_2023_Boundaries_UK_BFC/FeatureServer/0/"
    "query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
)

# Fallback: simplified boundaries (smaller download)
LAD_BOUNDARIES_URL_SIMPLE = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "Local_Authority_Districts_December_2023_Boundaries_UK_BSC/FeatureServer/0/"
    "query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
)

# Map styling
FIGURE_SIZE = (14, 18)
DPI = 300
BACKGROUND_COLOR = "#f7f7f7"
LAD_EDGE_COLOR = "#444444"
LAD_EDGE_WIDTH = 0.3
LAD_FILL_COLOR = "#e8e8e8"
FLOOD_ZONE_3_COLOR = "#1a5276"   # Dark blue – high probability
FLOOD_ZONE_2_COLOR = "#85c1e9"   # Light blue – medium probability
FLOOD_ZONE_3A_COLOR = "#2e86c1"  # Medium blue – functional floodplain (if present)
TITLE_FONTSIZE = 16
# ---------------------------------------------------------------------------


def check_dependencies():
    """Verify required packages are installed."""
    missing = []
    for pkg in ["geopandas", "matplotlib", "requests"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"ERROR: Missing packages: {', '.join(missing)}")
        print(f"Install with:  pip install {' '.join(missing)}")
        sys.exit(1)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a flood risk map of England with LAD boundaries."
    )
    parser.add_argument(
        "--flood-gpkg",
        default=DEFAULT_FLOOD_GPKG,
        help="Path to the EA Flood Map for Planning GeoPackage (.gpkg)",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help="Directory to save the output PNG",
    )
    parser.add_argument(
        "--output-name",
        default=OUTPUT_FILENAME,
        help="Output filename (default: flood_risk_map_england.png)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DPI,
        help="Output resolution in DPI (default: 300)",
    )
    parser.add_argument(
        "--lad-cache",
        default=None,
        help="Path to a cached LAD boundaries GeoJSON file (skips download)",
    )
    return parser.parse_args()


def download_lad_boundaries(cache_path=None):
    """Download LAD boundaries from ONS Open Geography Portal.

    The ONS ArcGIS Feature Server has a max record limit (typically 2000).
    We paginate through all features using resultOffset.
    """
    import geopandas as gpd
    import requests

    # If a cached file is provided, use it
    if cache_path and os.path.exists(cache_path):
        print(f"  Loading cached LAD boundaries from: {cache_path}")
        return gpd.read_file(cache_path)

    print("  Downloading LAD boundaries from ONS Open Geography Portal...")

    base_url = (
        "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
        "Local_Authority_Districts_December_2023_Boundaries_UK_BSC/FeatureServer/0/query"
    )

    all_features = []
    offset = 0
    batch_size = 1000

    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "outSR": "4326",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": batch_size,
        }
        resp = requests.get(base_url, params=params, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if not features:
            break

        all_features.extend(features)
        print(f"    Fetched {len(all_features)} LAD features so far...")

        # If we got fewer than requested, we've reached the end
        if len(features) < batch_size:
            break
        offset += batch_size

    if not all_features:
        raise RuntimeError("No LAD features returned from ONS API.")

    geojson = {"type": "FeatureCollection", "features": all_features}
    gdf = gpd.GeoDataFrame.from_features(geojson, crs="EPSG:4326")

    # Cache for future use
    cache_file = os.path.join(OUTPUT_DIR, "lad_boundaries_england_cache.geojson")
    try:
        gdf.to_file(cache_file, driver="GeoJSON")
        print(f"    Cached LAD boundaries to: {cache_file}")
    except Exception:
        pass  # Non-critical

    return gdf


def filter_england_lads(lad_gdf):
    """Filter LAD boundaries to England only.

    England LAD codes start with 'E' (e.g. E06000001, E07000026, E08000001, E09000001).
    """
    # Try common column names for the LAD code
    code_col = None
    for candidate in ["LAD23CD", "LAD22CD", "LAD21CD", "LAD24CD", "lad23cd", "LAD_CODE", "LADCD"]:
        if candidate in lad_gdf.columns:
            code_col = candidate
            break

    if code_col is None:
        # Fallback: find any column that looks like LAD codes
        for col in lad_gdf.columns:
            sample = lad_gdf[col].dropna().astype(str).head(5)
            if sample.str.match(r"^[ENSW]\d{8}$").all():
                code_col = col
                break

    if code_col is None:
        print("  WARNING: Could not identify LAD code column. Using all features.")
        print(f"  Available columns: {list(lad_gdf.columns)}")
        return lad_gdf

    england = lad_gdf[lad_gdf[code_col].astype(str).str.startswith("E")].copy()
    print(f"  Filtered to {len(england)} England LADs (column: {code_col})")
    return england


def load_flood_zones(gpkg_path):
    """Load EA Flood Zone data from GeoPackage.

    The GeoPackage typically contains layers like:
      - Flood_Zone_2
      - Flood_Zone_3
      - Areas_Benefiting_from_Defences
      - Flood_Storage_Areas
    """
    import geopandas as gpd
    import fiona

    if not os.path.exists(gpkg_path):
        print(f"ERROR: Flood GeoPackage not found: {gpkg_path}")
        print("Please provide the correct path with --flood-gpkg")
        sys.exit(1)

    # List available layers
    layers = fiona.listlayers(gpkg_path)
    print(f"  Available layers in GeoPackage: {layers}")

    flood_data = {}

    for layer in layers:
        layer_lower = layer.lower()
        if "zone_3" in layer_lower or "zone3" in layer_lower:
            print(f"  Loading Flood Zone 3 from layer: {layer}")
            flood_data["zone3"] = gpd.read_file(gpkg_path, layer=layer)
        elif "zone_2" in layer_lower or "zone2" in layer_lower:
            print(f"  Loading Flood Zone 2 from layer: {layer}")
            flood_data["zone2"] = gpd.read_file(gpkg_path, layer=layer)

    # If no named zones found, try loading all layers and inspecting
    if not flood_data:
        print("  No explicitly named flood zone layers found. Loading all layers...")
        for layer in layers:
            gdf = gpd.read_file(gpkg_path, layer=layer)
            print(f"    Layer '{layer}': {len(gdf)} features, columns: {list(gdf.columns)}")

            # Check for a type/zone column
            for col in gdf.columns:
                if col.lower() in ("type", "zone", "layer", "flood_zone", "fz_type"):
                    unique_vals = gdf[col].unique()
                    print(f"      Column '{col}' values: {unique_vals}")

            flood_data[layer] = gdf

    return flood_data


def create_map(england_lads, flood_data, output_path, dpi):
    """Create the flood risk map with LAD boundaries."""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.colors import to_rgba

    plt.rcParams["font.family"] = "sans-serif"

    fig, ax = plt.subplots(1, 1, figsize=FIGURE_SIZE, facecolor=BACKGROUND_COLOR)
    ax.set_facecolor(BACKGROUND_COLOR)

    # Reproject to British National Grid for proper display
    try:
        england_lads_proj = england_lads.to_crs(epsg=27700)
    except Exception:
        england_lads_proj = england_lads

    # -- 1. Draw LAD boundaries (base layer) --
    england_lads_proj.plot(
        ax=ax,
        facecolor=LAD_FILL_COLOR,
        edgecolor=LAD_EDGE_COLOR,
        linewidth=LAD_EDGE_WIDTH,
        zorder=1,
    )

    # -- 2. Overlay flood zones --
    legend_patches = []

    # Draw Flood Zone 2 first (lower risk, underneath)
    if "zone2" in flood_data and flood_data["zone2"] is not None:
        fz2 = flood_data["zone2"]
        try:
            fz2_proj = fz2.to_crs(epsg=27700)
        except Exception:
            fz2_proj = fz2
        fz2_proj.plot(
            ax=ax,
            facecolor=FLOOD_ZONE_2_COLOR,
            edgecolor="none",
            alpha=0.7,
            zorder=2,
        )
        legend_patches.append(
            mpatches.Patch(
                facecolor=FLOOD_ZONE_2_COLOR,
                alpha=0.7,
                label="Flood Zone 2 (Medium probability)",
            )
        )

    # Draw Flood Zone 3 on top (higher risk)
    if "zone3" in flood_data and flood_data["zone3"] is not None:
        fz3 = flood_data["zone3"]
        try:
            fz3_proj = fz3.to_crs(epsg=27700)
        except Exception:
            fz3_proj = fz3
        fz3_proj.plot(
            ax=ax,
            facecolor=FLOOD_ZONE_3_COLOR,
            edgecolor="none",
            alpha=0.8,
            zorder=3,
        )
        legend_patches.append(
            mpatches.Patch(
                facecolor=FLOOD_ZONE_3_COLOR,
                alpha=0.8,
                label="Flood Zone 3 (High probability)",
            )
        )

    # Handle case where flood data uses different keys (loaded by layer name)
    if not legend_patches:
        # Plot all available flood data with a generic style
        colors = ["#85c1e9", "#1a5276", "#2e86c1", "#a9cce3"]
        for i, (name, gdf) in enumerate(flood_data.items()):
            if gdf is not None and len(gdf) > 0:
                try:
                    gdf_proj = gdf.to_crs(epsg=27700)
                except Exception:
                    gdf_proj = gdf
                color = colors[i % len(colors)]
                gdf_proj.plot(
                    ax=ax,
                    facecolor=color,
                    edgecolor="none",
                    alpha=0.7,
                    zorder=2 + i,
                )
                legend_patches.append(
                    mpatches.Patch(facecolor=color, alpha=0.7, label=name)
                )

    # -- 3. Re-draw LAD borders on top for clarity --
    england_lads_proj.boundary.plot(
        ax=ax,
        edgecolor=LAD_EDGE_COLOR,
        linewidth=LAD_EDGE_WIDTH,
        zorder=10,
    )

    # -- 4. Add LAD base layer to legend --
    legend_patches.insert(
        0,
        mpatches.Patch(
            facecolor=LAD_FILL_COLOR,
            edgecolor=LAD_EDGE_COLOR,
            linewidth=0.5,
            label="Local Authority District",
        ),
    )

    # -- 5. Style the map --
    ax.set_title(
        "Flood Risk Areas in England\nby Local Authority District",
        fontsize=TITLE_FONTSIZE,
        fontweight="bold",
        pad=20,
    )
    ax.set_axis_off()

    # Legend
    ax.legend(
        handles=legend_patches,
        loc="lower left",
        fontsize=9,
        frameon=True,
        facecolor="white",
        edgecolor="#cccccc",
        framealpha=0.9,
        title="Legend",
        title_fontsize=10,
    )

    # Attribution
    ax.annotate(
        "Data: Environment Agency Flood Map for Planning | Boundaries: ONS Open Geography",
        xy=(0.5, 0.01),
        xycoords="figure fraction",
        ha="center",
        fontsize=7,
        color="#888888",
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor=BACKGROUND_COLOR)
    plt.close(fig)
    print(f"\n  Map saved to: {output_path}")


def main():
    check_dependencies()
    args = parse_args()

    output_path = os.path.join(args.output_dir, args.output_name)
    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 60)
    print("  FLOOD RISK MAP OF ENGLAND – LAD Districts")
    print("=" * 60)

    # Step 1: Load LAD boundaries
    print("\n[1/4] Loading LAD boundaries...")
    lad_gdf = download_lad_boundaries(cache_path=args.lad_cache)

    # Step 2: Filter to England
    print("\n[2/4] Filtering to England LADs...")
    england_lads = filter_england_lads(lad_gdf)

    if len(england_lads) == 0:
        print("ERROR: No England LADs found. Check boundary data.")
        sys.exit(1)

    # Step 3: Load flood zones
    print("\n[3/4] Loading flood zone data...")
    flood_data = load_flood_zones(args.flood_gpkg)

    if not flood_data:
        print("ERROR: No flood zone data loaded.")
        sys.exit(1)

    # Step 4: Create map
    print("\n[4/4] Creating map...")
    create_map(england_lads, flood_data, output_path, args.dpi)

    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()

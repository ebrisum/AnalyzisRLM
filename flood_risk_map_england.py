#!/usr/bin/env python3
"""
Fast flood risk map of England with LAD boundaries.
Prioritises speed: aggressive simplification, low-res output, chunked plotting.

Usage:
    python flood_risk_map_england.py --flood-gpkg "path/to/Flood_Map_for_Planning_Flood_Zones.gpkg"
"""

import argparse
import os
import sys
import warnings

warnings.filterwarnings("ignore")

DEFAULT_FLOOD_GPKG = r"C:\Users\NL1E9O\Downloads\Flood\Flood_Map_for_Planning_Flood_Zones.gpkg"
OUTPUT = "flood_risk_map_england.png"
DPI = 150
SIMPLIFY_TOLERANCE = 100  # metres – coarser = faster


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import geopandas as gpd
    import fiona
    import requests
    from shapely.geometry import box

    parser = argparse.ArgumentParser()
    parser.add_argument("--flood-gpkg", default=DEFAULT_FLOOD_GPKG)
    parser.add_argument("--output", default=OUTPUT)
    parser.add_argument("--dpi", type=int, default=DPI)
    parser.add_argument("--lad-cache", default=None)
    args = parser.parse_args()

    # ── 1. LAD boundaries ────────────────────────────────────────────
    print("[1/4] LAD boundaries...")
    lad_gdf = None
    cache = args.lad_cache or "lad_cache.geojson"
    if os.path.exists(cache):
        lad_gdf = gpd.read_file(cache)
    else:
        url = (
            "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
            "Local_Authority_Districts_December_2023_Boundaries_UK_BSC/FeatureServer/0/query"
        )
        feats, offset = [], 0
        while True:
            r = requests.get(url, params={
                "where": "1=1", "outFields": "*", "outSR": "4326",
                "f": "geojson", "resultOffset": offset, "resultRecordCount": 1000,
            }, timeout=120)
            r.raise_for_status()
            batch = r.json().get("features", [])
            if not batch:
                break
            feats.extend(batch)
            if len(batch) < 1000:
                break
            offset += 1000
        lad_gdf = gpd.GeoDataFrame.from_features(
            {"type": "FeatureCollection", "features": feats}, crs="EPSG:4326"
        )
        try:
            lad_gdf.to_file(cache, driver="GeoJSON")
        except Exception:
            pass

    # ── 2. Filter England ────────────────────────────────────────────
    print("[2/4] Filtering England...")
    code_col = None
    for c in lad_gdf.columns:
        if lad_gdf[c].dropna().astype(str).head(5).str.match(r"^[ENSW]\d{8}$").all():
            code_col = c
            break
    if code_col:
        lad_gdf = lad_gdf[lad_gdf[code_col].astype(str).str.startswith("E")].copy()
    lad_gdf = lad_gdf.to_crs(epsg=27700)
    print(f"  {len(lad_gdf)} LADs")

    # ── 3. Flood zones ──────────────────────────────────────────────
    print("[3/4] Loading flood zones...")
    if not os.path.exists(args.flood_gpkg):
        sys.exit(f"ERROR: not found: {args.flood_gpkg}")

    layers = fiona.listlayers(args.flood_gpkg)
    print(f"  Layers: {layers}")

    flood = {}
    for lyr in layers:
        ll = lyr.lower()
        if "zone_3" in ll or "zone3" in ll:
            flood["zone3"] = gpd.read_file(args.flood_gpkg, layer=lyr)
        elif "zone_2" in ll or "zone2" in ll:
            flood["zone2"] = gpd.read_file(args.flood_gpkg, layer=lyr)
    if not flood:
        for lyr in layers:
            flood[lyr] = gpd.read_file(args.flood_gpkg, layer=lyr)

    # ── 4. Plot ──────────────────────────────────────────────────────
    print("[4/4] Plotting...")
    fig, ax = plt.subplots(figsize=(14, 18), facecolor="#f7f7f7")
    ax.set_facecolor("#f7f7f7")

    lad_gdf.plot(ax=ax, facecolor="#e8e8e8", edgecolor="#444", linewidth=0.3, zorder=1)

    clip = box(*lad_gdf.total_bounds)
    patches = []
    styles = {
        "zone2": ("#85c1e9", 0.7, 2, "Flood Zone 2 (Medium)"),
        "zone3": ("#1a5276", 0.8, 3, "Flood Zone 3 (High)"),
    }
    fallback_colors = ["#85c1e9", "#1a5276", "#2e86c1", "#a9cce3"]

    for i, (key, gdf) in enumerate(flood.items()):
        gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()
        gdf = gdf.to_crs(epsg=27700)
        gdf = gdf[gdf.intersects(clip)]
        gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
        gdf = gdf[~gdf.geometry.is_empty]
        print(f"  {key}: {len(gdf)} features")

        if key in styles:
            color, alpha, z, label = styles[key]
        else:
            color, alpha, z, label = fallback_colors[i % 4], 0.7, 2 + i, key

        # Plot in chunks
        for s in range(0, len(gdf), 50000):
            gdf.iloc[s:s + 50000].plot(ax=ax, facecolor=color, edgecolor="none", alpha=alpha, zorder=z)

        patches.append(mpatches.Patch(facecolor=color, alpha=alpha, label=label))

    lad_gdf.boundary.plot(ax=ax, edgecolor="#444", linewidth=0.3, zorder=10)

    patches.insert(0, mpatches.Patch(facecolor="#e8e8e8", edgecolor="#444", linewidth=0.5, label="LAD"))
    ax.legend(handles=patches, loc="lower left", fontsize=9, frameon=True,
              facecolor="white", edgecolor="#ccc", framealpha=0.9)
    ax.set_title("Flood Risk Areas in England\nby Local Authority District",
                 fontsize=16, fontweight="bold", pad=20)
    ax.set_axis_off()
    plt.tight_layout()
    fig.savefig(args.output, dpi=args.dpi, bbox_inches="tight", facecolor="#f7f7f7")
    plt.close(fig)
    print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()

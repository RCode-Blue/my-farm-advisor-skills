"""Static EDA outputs for the three Assignment 2 farms (2022-focused).

Reads runtime tables and boundaries; writes PNG, CSV, and text outputs under
DATA_PIPELINE_DATA_ROOT/../../workspace data-pipeline/eda (see OUT_DIR).
No report generation here; this only produces reusable artefacts.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RUNTIME = Path(os.environ.get("DATA_PIPELINE_DATA_ROOT", "/home/coder/my-farm-advisor-runtime"))
OUT_DIR = Path(os.environ.get(
    "EDA_OUT_DIR", str(RUNTIME / "data-pipeline" / "eda")))
FARMS = [
    ("Iowa", "ia-grower", "ia-grower-iowa"),
    ("Illinois", "il-grower", "il-grower-illinois"),
    ("Nebraska", "ne-grower", "ne-grower-buffalo"),
]
COLORS = {"Iowa": "#4c78a8", "Illinois": "#72b7b2", "Nebraska": "#f58518"}
CROP_COLORS = {"Corn": "#1f77b4", "Soybeans": "#9ed9e8", "Other": "#bbbbbb"}
DROUGHT_YEAR = 2022


def farm_dir(grower: str, farm: str) -> Path:
    return RUNTIME / "data-pipeline" / "growers" / grower / "farms" / farm


def load_boundaries() -> gpd.GeoDataFrame:
    frames = []
    for name, grower, farm in FARMS:
        g = gpd.read_file(farm_dir(grower, farm) / "boundary" / "field_boundaries.geojson")
        g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
        g["farm"] = name
        g["area_ha"] = g.to_crs(6933).area / 1e4
        frames.append(g[["farm", "field_id", "area_ha", "geometry"]])
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=4326)


def load_weather() -> pd.DataFrame:
    frames = []
    for name, grower, farm in FARMS:
        f = glob.glob(str(farm_dir(grower, farm) / "derived" / "tables" / "*weather_2021_2025*.csv"))[0]
        w = pd.read_csv(f, parse_dates=["date"])
        # One record per farm: average across field rows (identical in current data),
        # so totals are per farm, not summed over fields.
        w = w.groupby("date", as_index=False)[["PRECTOTCORR", "T2M"]].mean()
        w["farm"] = name
        w["year"] = w.date.dt.year
        w["doy"] = w.date.dt.dayofyear
        frames.append(w)
    return pd.concat(frames, ignore_index=True)


def load_cdl() -> pd.DataFrame:
    frames = []
    for name, grower, farm in FARMS:
        f = glob.glob(str(farm_dir(grower, farm) / "derived" / "tables" / "*cdl_2021_2025_full_composition.csv"))[0]
        d = pd.read_csv(f)
        d["farm"] = name
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    tot = d.groupby(["farm", "field_id", "year"]).pixel_count.sum().rename("tot")
    d = d.join(tot, on=["farm", "field_id", "year"])
    d["share"] = d.pixel_count / d.tot * 100
    return d


def save(fig, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / name, dpi=110, bbox_inches="tight")
    plt.close(fig)


def boundary_outputs(b: gpd.GeoDataFrame, cdl: pd.DataFrame) -> list[str]:
    notes = []
    # Viz 1: field size by farm
    fig, ax = plt.subplots(figsize=(7, 4))
    for i, (name, _, _) in enumerate(FARMS):
        s = b[b.farm == name].area_ha.to_numpy()
        ax.scatter(np.full(len(s), i) + np.random.default_rng(0).uniform(-0.12, 0.12, len(s)), s,
                   color=COLORS[name], s=40, label=name)
        ax.hlines(np.median(s), i - 0.25, i + 0.25, color="black", lw=1.5)
    ax.set_xticks(range(len(FARMS)))
    ax.set_xticklabels([n for n, _, _ in FARMS])
    ax.set_ylabel("Field area (ha)")
    ax.set_title("Field size by farm (black bar = median)", fontweight="bold")
    save(fig, "boundary_size_by_farm.png")

    # Viz 2: nearest-neighbour spacing between field centroids
    fig, ax = plt.subplots(figsize=(7, 4))
    data, labels = [], []
    for name, _, _ in FARMS:
        g = b[b.farm == name].to_crs(6933)
        c = g.geometry.centroid
        nn = []
        for i, p in enumerate(c):
            d = [p.distance(q) / 1000 for j, q in enumerate(c) if j != i]
            nn.append(min(d))
        data.append(nn)
        labels.append(name)
    ax.boxplot(data, tick_labels=labels)
    ax.set_ylabel("Nearest other field centre (km)")
    ax.set_title("Field spacing: nearest-neighbour distance by farm", fontweight="bold")
    save(fig, "boundary_spacing_by_farm.png")

    # Comparison: field size vs number of dominant-crop changes 2021-2025
    dom = (cdl.sort_values("share", ascending=False)
           .drop_duplicates(["farm", "field_id", "year"])
           .sort_values(["farm", "field_id", "year"]))
    changes = dom.groupby(["farm", "field_id"]).crop_name.apply(
        lambda s: int((s.values[1:] != s.values[:-1]).sum()))
    cmp_df = b.set_index(["farm", "field_id"]).join(changes.rename("crop_changes")).reset_index()
    cmp_df[["farm", "field_id", "area_ha", "crop_changes"]].to_csv(OUT_DIR / "boundary_size_vs_changes.csv", index=False)
    r = np.corrcoef(cmp_df.area_ha, cmp_df.crop_changes)[0, 1]
    fig, ax = plt.subplots(figsize=(7, 4))
    for name, _, _ in FARMS:
        s = cmp_df[cmp_df.farm == name]
        ax.scatter(s.area_ha, s.crop_changes + np.random.default_rng(1).uniform(-0.08, 0.08, len(s)),
                   color=COLORS[name], label=name)
    ax.set_xlabel("Field area (ha)")
    ax.set_ylim(-0.4, 4.4)
    ax.set_ylabel("Dominant-crop changes, 2021-2025")
    ax.set_title(f"Field size vs crop changes (r = {r:.2f}, n = {len(cmp_df)})", fontweight="bold")
    ax.legend(fontsize=8)
    save(fig, "boundary_size_vs_changes.png")
    notes.append(f"Field size vs crop changes: r = {r:.2f}, n = {len(cmp_df)} (exploratory, small sample).")
    return notes


def map_fields(b: gpd.GeoDataFrame, colour_by: pd.Series | None, title: str, name: str,
               legend_map: dict | None = None) -> None:
    fig, axes = plt.subplots(1, len(FARMS), figsize=(15, 5))
    for ax, (fname, _, _) in zip(axes, FARMS):
        g = b[b.farm == fname]
        if colour_by is None:
            g.plot(ax=ax, color=COLORS[fname], edgecolor="black", linewidth=0.5)
        else:
            cols = [legend_map.get(colour_by.get((fname, fid)), "#cccccc") for fid in g.field_id]
            g.plot(ax=ax, color=cols, edgecolor="black", linewidth=0.5)
        for _, r in g.iterrows():
            p = r.geometry.representative_point()
            ax.annotate(str(r.field_id), (p.x, p.y), fontsize=6, ha="center")
        ax.set_title(fname, fontweight="bold")
        ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
    if legend_map:
        from matplotlib.patches import Patch
        handles = [Patch(color=c, label=k) for k, c in legend_map.items()]
        fig.legend(handles=handles, loc="lower center", ncol=len(handles), fontsize=9, frameon=False)
    fig.suptitle(title, fontweight="bold")
    save(fig, name)


def weather_outputs(w: pd.DataFrame) -> list[str]:
    notes = []
    annual = w.groupby(["farm", "year"]).PRECTOTCORR.sum().unstack(0)
    annual = annual[[n for n, _, _ in FARMS]]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(annual.index)); width = 0.27
    for i, farm in enumerate(annual.columns):
        ax.bar(x + (i - 1) * width, annual[farm], width, label=farm, color=COLORS[farm])
    i22 = list(annual.index).index(DROUGHT_YEAR)
    ax.axvspan(i22 - 0.5, i22 + 0.5, color="#ffe0b2", alpha=0.6, zorder=0)
    ax.set_xticks(x); ax.set_xticklabels(annual.index)
    ax.set_ylabel("Annual precipitation (mm)")
    ax.set_title("Annual precipitation by farm, 2021-2025 (one weather record per farm)", fontweight="bold", fontsize=11)
    ax.legend(fontsize=8)
    save(fig, "weather_annual_precip_by_farm.png")
    annual.round(0).to_csv(OUT_DIR / "weather_annual_precip_by_farm.csv")

    # Viz 2: cumulative precipitation by day of year, one panel per farm
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, (fname, _, _) in zip(axes, FARMS):
        s = w[w.farm == fname]
        for y, g in s.groupby("year"):
            g = g.sort_values("doy")
            lw = 2.5 if y == DROUGHT_YEAR else 1.0
            alpha = 1.0 if y == DROUGHT_YEAR else 0.5
            ax.plot(g.doy, g.PRECTOTCORR.cumsum(), lw=lw, alpha=alpha, label=str(y))
        ax.set_title(fname, fontweight="bold")
        ax.set_xlabel("Day of year")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("Cumulative precipitation (mm)")
    fig.suptitle("Cumulative precipitation by day of year (2022 highlighted)", fontweight="bold")
    save(fig, "weather_cumulative_precip_by_doy.png")

    # Comparison: 2022 vs average of other years, per farm
    other = annual.drop(index=DROUGHT_YEAR).mean()
    pct = (annual.loc[DROUGHT_YEAR] / other - 1) * 100
    comp = pd.DataFrame({"precip_2022_mm": annual.loc[DROUGHT_YEAR], "mean_other_years_mm": other.round(0),
                         "pct_vs_other_years": pct.round(0)})
    comp.to_csv(OUT_DIR / "weather_2022_vs_other_years.csv")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(comp.index, comp.pct_vs_other_years, color=[COLORS[f] for f in comp.index])
    for i, v in enumerate(comp.pct_vs_other_years):
        ax.text(i, v / 2, f"{v:.0f}%", ha="center", va="center", color="black", fontsize=9)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("2022 vs mean of other years (%)")
    ax.set_title("2022 precipitation against other years", fontweight="bold")
    save(fig, "weather_2022_vs_other_years.png")
    notes.append("2022 vs other years: " + ", ".join(f"{f} {v:.0f}%" for f, v in pct.items()) + ".")
    return notes


def cdl_outputs(cdl: pd.DataFrame, w: pd.DataFrame) -> list[str]:
    notes = []
    # Viz 1: area-weighted farm share by year
    farm_share = {}
    for fname, _, _ in FARMS:
        s = cdl[cdl.farm == fname]
        pix = s.groupby(["year", "crop_name"]).pixel_count.sum().unstack(fill_value=0)
        pct = pix.div(pix.sum(axis=1), axis=0) * 100
        farm_share[fname] = pct
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, (fname, _, _) in zip(axes, FARMS):
        pct = farm_share[fname]
        bottom = np.zeros(len(pct))
        for crop in ["Corn", "Soybeans"]:
            vals = pct[crop].to_numpy() if crop in pct else np.zeros(len(pct))
            ax.bar([str(y) for y in pct.index], vals, bottom=bottom, color=CROP_COLORS[crop], label=crop)
            bottom += vals
        ax.bar([str(y) for y in pct.index], 100 - bottom, bottom=bottom, color=CROP_COLORS["Other"], label="Other")
        ax.set_title(fname, fontweight="bold")
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("% of farm area")
    axes[-1].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
    fig.suptitle("Farm crop share by year (area-weighted)", fontweight="bold")
    save(fig, "cdl_farm_share_by_year.png")
    pd.concat({k: v for k, v in farm_share.items()}, names=["farm"]).round(1).to_csv(
        OUT_DIR / "cdl_farm_share_by_year.csv")

    # Viz 2: per-field corn/soy share heatmap, one panel per farm
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    for ax, (fname, _, _) in zip(axes, FARMS):
        s = cdl[(cdl.farm == fname) & cdl.crop_name.isin(["Corn", "Soybeans"])]
        p = s.pivot_table(index="field_id", columns="year", values="share", aggfunc="sum").fillna(0)
        corn = cdl[(cdl.farm == fname) & (cdl.crop_name == "Corn")].pivot_table(
            index="field_id", columns="year", values="share", aggfunc="sum").reindex(p.index).fillna(0)
        frac = (corn / p.replace(0, np.nan)).fillna(0).to_numpy()
        img = np.array([[np.array(matplotlib.colors.to_rgb("#1f77b4")) * f
                         + np.array(matplotlib.colors.to_rgb("#9ed9e8")) * (1 - f) for f in row]
                        for row in frac])
        ax.imshow(img, aspect="auto")
        for i in range(p.shape[0]):
            for j in range(p.shape[1]):
                c = corn.iloc[i, j]; sshare = p.iloc[i, j] - c
                ax.text(j, i, f"C{c:.0f}\nS{sshare:.0f}", ha="center", va="center", fontsize=6)
        ax.set_xticks(range(p.shape[1])); ax.set_xticklabels(p.columns, fontsize=8)
        ax.set_yticks(range(p.shape[0])); ax.set_yticklabels(p.index, fontsize=7)
        ax.set_title(fname, fontweight="bold")
    fig.suptitle("Per-field corn (C) and soybean (S) share by year, %", fontweight="bold")
    save(fig, "cdl_field_heatmap.png")

    # Comparison: Illinois planting-window rain vs soybean share by year (exploratory)
    il = w[w.farm == "Illinois"]
    pw = il[(il.date.dt.month > 4) | ((il.date.dt.month == 4) & (il.date.dt.day >= 15))]
    pw = pw[(pw.date.dt.month < 6) | ((pw.date.dt.month == 5) & (pw.date.dt.day <= 31))]
    rain = pw.groupby("year").PRECTOTCORR.sum()
    soy = farm_share["Illinois"]["Soybeans"] if "Soybeans" in farm_share["Illinois"] else None
    r = float(np.corrcoef(rain.loc[soy.index], soy)[0, 1])
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(rain.loc[soy.index], soy, color=COLORS["Illinois"])
    for y in soy.index:
        ax.annotate(str(y), (rain.loc[y], soy[y]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("Planting-window rainfall, 15 Apr-31 May (mm)")
    ax.set_ylabel("Farm soybean share (%)")
    ax.set_title(f"Illinois: planting rain vs soybean share (r = {r:.2f}, n = {len(soy)})", fontweight="bold", fontsize=10)
    save(fig, "cdl_illinois_planting_rain_vs_soy.png")
    notes.append(f"Illinois planting-window rain vs soybean share: r = {r:.2f}, n = {len(soy)}; exploratory, "
                 "not causal, and one weather record per farm.")
    return notes


def weather_map(b: gpd.GeoDataFrame, w: pd.DataFrame) -> None:
    annual = w.groupby(["farm", "year"]).PRECTOTCORR.sum().unstack(0)
    fig, ax = plt.subplots(figsize=(8, 6))
    b.plot(ax=ax, color="#eeeeee", edgecolor="#999999", linewidth=0.3)
    for name, _, _ in FARMS:
        g = b[b.farm == name]
        cx, cy = g.geometry.unary_union.centroid.x, g.geometry.unary_union.centroid.y
        v22 = annual.loc[DROUGHT_YEAR, name]
        other = annual.drop(index=DROUGHT_YEAR)[name].mean()
        ax.scatter(cx, cy, s=260, color=COLORS[name], edgecolor="black", zorder=3)
        ax.annotate(f"{name}\n2022: {v22:.0f} mm\n({(v22 / other - 1) * 100:+.0f}% vs other years)",
                    (cx, cy), xytext=(12, -40), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.set_ylim(40, 44.5)
    ax.set_title("Farm locations with 2022 annual precipitation (one weather record per farm)", fontweight="bold", fontsize=10, pad=12)
    save(fig, "map_weather_2022_by_farm.png")


def main() -> None:
    b = load_boundaries()
    w = load_weather()
    cdl = load_cdl()
    notes = []
    notes += boundary_outputs(b, cdl)
    notes += weather_outputs(w)
    notes += cdl_outputs(cdl, w)
    # Maps
    map_fields(b, None, "Field boundaries by farm (real boundaries)", "map_fields_by_farm.png")
    dom22 = (cdl[cdl.year == DROUGHT_YEAR].sort_values("share", ascending=False)
             .drop_duplicates(["farm", "field_id"]))
    dom_map = {(r.farm, r.field_id): r.crop_name for r in dom22.itertuples()}
    palette = {"Corn": CROP_COLORS["Corn"], "Soybeans": CROP_COLORS["Soybeans"], "Other": CROP_COLORS["Other"]}
    map_fields(b, pd.Series(dom_map), "Dominant crop by field, 2022 (drought year)", "map_cdl_dominant_2022.png", palette)
    weather_map(b, w)
    (OUT_DIR / "NOTES.txt").write_text("\n".join(notes) + "\n")
    print("\n".join(notes))
    print("outputs in", OUT_DIR)


if __name__ == "__main__":
    main()

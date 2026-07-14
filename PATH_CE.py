import numpy as np
import pandas as pd
from pulp import LpMinimize, LpMaximize, LpProblem, LpStatus, LpVariable, PulpSolverError


def ce_select_sites_flexible(
    data,
    treatments,
    treatment_cost,
    treatment_quantity,
    fixed_cost,
    sdyd_threshold,
    sddc_threshold,
    slope_range=None,
    bs_threshold=None,
    id_col=None,
    area_col=None,
    return_increase_class=True,
):
    """Run CE site selection on either cumulative-contribution or stream-order Omni outputs.

    Auto-detects identifier and area columns used by the two common schemas:
    - Legacy/cumulative-style tables: wepp_id + area
    - Aggregate/stream-order-style tables: contrast_id + area_sum
    """
    all_data = data.copy()

    if id_col is None:
        if "wepp_id" in data.columns:
            id_col = "wepp_id"
            print("Using 'wepp_id' as identifier column.")
        elif "contrast_id" in data.columns:
            id_col = "contrast_id"
            print("Using 'contrast_id' as identifier column.")
        else:
            raise KeyError("Data must contain either 'wepp_id' or 'contrast_id'.")
    
    if area_col is None:
        if "area" in data.columns:
            area_col = "area"
            print("Using 'area' as area column.")
        elif "area_sum" in data.columns:
            area_col = "area_sum"
            print("Using 'area_sum' as area column.")
        else:
            raise KeyError("Data must contain either 'area' or 'area_sum'.")
    
    total_Sddc_postfire = pd.to_numeric(data["Sddc post-fire"], errors="coerce").iloc[0]
    Sddc_reduction_threshold = total_Sddc_postfire - sddc_threshold
    if Sddc_reduction_threshold <= 0:
        print("Alert: Sddc threshold already met.")
        Sddc_reduction_threshold = 0

    if slope_range is not None:
        min_slope, max_slope = slope_range
        data = data.loc[(data["slope_deg"] >= min_slope) & (data["slope_deg"] <= max_slope)]
    if bs_threshold is not None:
        data = data[data["Burn severity"].isin(bs_threshold)]
    data = data.reset_index(drop=True)

    water_quality = data.filter(regex="Sddc reduction")
    soil_erosion = data.filter(regex="Sdyd reduction")
    if water_quality.empty or soil_erosion.empty:
        raise ValueError("Data is missing required 'Sddc reduction' and/or 'Sdyd reduction' columns.")

    hillslope = data[id_col].values
    sediment_yield_reduction_thresholds = (pd.to_numeric(data["Sdyd post-fire"], errors="coerce") - sdyd_threshold).clip(lower=0)
    num_sites = len(data)

    treatment_cost_vectors = {
        t: pd.to_numeric(data[area_col], errors="coerce") * c * q
        for t, c, q in zip(treatments, treatment_cost, treatment_quantity)
    }

    model_primary = LpProblem("Select_Sites", LpMinimize)
    x = {t: [LpVariable(f"x_{t}_{i}", 0, 1, cat="Binary") for i in range(num_sites)] for t in treatments}
    B = {t: LpVariable(f"B_{t}", 0, 1, cat="Binary") for t in treatments}

    model_primary += (
        sum(x[t][i] * treatment_cost_vectors[t][i] for t in treatments for i in range(num_sites))
        + sum(B[t] * fixed_cost[n] for n, t in enumerate(treatments))
    )

    for i in range(num_sites):
        model_primary += sum(x[t][i] for t in treatments) <= 1

    for t in treatments:
        for i in range(num_sites):
            model_primary += B[t] >= x[t][i]

    model_primary += (
        sum(
            x[t][i] * water_quality.iloc[:, n].values[i]
            for n, t in enumerate(treatments)
            for i in range(num_sites)
        )
        >= Sddc_reduction_threshold
    )

    for i in range(num_sites):
        if max(soil_erosion.iloc[i, :]) > sediment_yield_reduction_thresholds[i]:
            model_primary += (
                sum(x[t][i] * soil_erosion.iloc[:, n].values[i] for n, t in enumerate(treatments))
                >= sediment_yield_reduction_thresholds[i]
            )
        elif all(soil_erosion.iloc[i, :] <= 0):
            model_primary += sum(x[t][i] for t in treatments) == 0
        else:
            model_primary += (
                sum(x[t][i] * soil_erosion.iloc[:, n].values[i] for n, t in enumerate(treatments))
                == max(soil_erosion.iloc[i, :])
            )

    try:
        _ = model_primary.solve()
        if LpStatus[model_primary.status] != "Optimal":
            print("Warning: No optimal solution found for given thresholds. Second best solution will be returned")
            model_primary_status = 0

            model_secondary = LpProblem("Select_Sites_Secondary", LpMaximize)
            x_2 = {t: [LpVariable(f"x_2_{t}_{i}", 0, 1, cat="Binary") for i in range(num_sites)] for t in treatments}
            B_2 = {t: LpVariable(f"B_2_{t}", 0, 1, cat="Binary") for t in treatments}

            model_secondary += sum(
                x_2[t][i] * water_quality.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
                for i in range(num_sites)
            )

            for i in range(num_sites):
                # The fallback model should preserve the primary model's ability to leave a site untreated. 
                model_secondary += sum(x_2[t][i] for t in treatments) <= 1

            for t in treatments:
                for i in range(num_sites):
                    model_secondary += B_2[t] >= x_2[t][i]

            for i in range(num_sites):
                if max(soil_erosion.iloc[i, :]) > sediment_yield_reduction_thresholds[i]:
                    model_secondary += (
                        sum(x_2[t][i] * soil_erosion.iloc[:, n].values[i] for n, t in enumerate(treatments))
                        >= sediment_yield_reduction_thresholds[i]
                    )
                elif all(soil_erosion.iloc[i, :] <= 0):
                    model_secondary += sum(x_2[t][i] for t in treatments) == 0
                else:
                    model_secondary += (
                        sum(x_2[t][i] * soil_erosion.iloc[:, n].values[i] for n, t in enumerate(treatments))
                        == max(soil_erosion.iloc[i, :])
                    )

            _ = model_secondary.solve()
            if LpStatus[model_secondary.status] != "Optimal":
                print("Warning: No second best solution found for given thresholds")
                return None

            selected_sites = [[i for i in range(num_sites) if x_2[t][i].varValue == 1] for t in treatments]
            selected = [i for t in treatments for i in range(num_sites) if x_2[t][i].varValue == 1]
            selected_hillslopes = [hillslope[i] for i in selected]
            treatment_hillslopes = [hillslope[idxs].tolist() for idxs in selected_sites]

            total_cost = sum(treatment_cost_vectors[t][i] for n, t in enumerate(treatments) for i in selected_sites[n])
            total_fixed_cost = sum(B_2[t].varValue * fixed_cost[n] for n, t in enumerate(treatments))
            total_Sddc_reduction = sum(
                x_2[t][i].varValue * water_quality.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
                for i in range(num_sites)
            )
            final_Sddc = total_Sddc_postfire - total_Sddc_reduction

            hillslopes_sdyd = []
            for i in range(num_sites):
                for t in treatments:
                    if x_2[t][i].varValue == 1:
                        hillslopes_sdyd.append([data[id_col][i], data[f"Sdyd post-treat {t}"][i]])
            for i in range(num_sites):
                if all(x_2[t][i].varValue == 0 for t in treatments):
                    hillslopes_sdyd.append([data[id_col][i], data["Sdyd post-fire"][i]])

        else:
            print("Optimal solution found")
            model_primary_status = 1

            selected_sites = [[i for i in range(num_sites) if x[t][i].varValue == 1] for t in treatments]
            selected = [i for t in treatments for i in range(num_sites) if x[t][i].varValue == 1]
            selected_hillslopes = [hillslope[i] for i in selected]
            treatment_hillslopes = [hillslope[idxs].tolist() for idxs in selected_sites]

            total_cost = sum(treatment_cost_vectors[t][i] for n, t in enumerate(treatments) for i in selected_sites[n])
            total_fixed_cost = sum(B[t].varValue * fixed_cost[n] for n, t in enumerate(treatments))
            total_Sddc_reduction = sum(
                x[t][i].varValue * water_quality.iloc[:, n].values[i]
                for n, t in enumerate(treatments)
                for i in range(num_sites)
            )
            final_Sddc = total_Sddc_postfire - total_Sddc_reduction

            hillslopes_sdyd = []
            for i in range(num_sites):
                for t in treatments:
                    if x[t][i].varValue == 1:
                        hillslopes_sdyd.append([data[id_col][i], data[f"Sdyd post-treat {t}"][i]])
            for i in range(num_sites):
                if all(x[t][i].varValue == 0 for t in treatments):
                    hillslopes_sdyd.append([data[id_col][i], data["Sdyd post-fire"][i]])

        sdyd_df = pd.DataFrame(hillslopes_sdyd, columns=[id_col, "final_Sdyd"])
        untreatable_sdyd = sdyd_df[sdyd_df["final_Sdyd"] > sdyd_threshold].copy()

        # Subclass of untreatable hillslopes: Sdyd increases under every treatment option.
        # Keep this as a dedicated table so plotting/reporting can style it separately.
        untreatable_sdyd_increase = pd.DataFrame(columns=[id_col, "final_Sdyd"])
        treatment_sdyd_cols = [f"Sdyd post-treat {t}" for t in treatments if f"Sdyd post-treat {t}" in data.columns]
        if treatment_sdyd_cols and not untreatable_sdyd.empty:
            tmp_df = data[[id_col, "Sdyd post-fire"] + treatment_sdyd_cols].copy()
            tmp_df["Sdyd post-fire"] = pd.to_numeric(tmp_df["Sdyd post-fire"], errors="coerce")
            for col in treatment_sdyd_cols:
                tmp_df[col] = pd.to_numeric(tmp_df[col], errors="coerce")

            strictly_increase_mask = tmp_df[treatment_sdyd_cols].gt(tmp_df["Sdyd post-fire"], axis=0).all(axis=1)
            increase_ids = set(tmp_df.loc[strictly_increase_mask, id_col].tolist())

            if increase_ids:
                untreatable_sdyd_increase = data[data[id_col].isin(increase_ids)].copy()

        missing_hillslopes = all_data[~all_data[id_col].isin(data[id_col])]
        if not missing_hillslopes.empty:
            missing_sdyd = missing_hillslopes[[id_col, "Sdyd post-fire"]].rename(columns={"Sdyd post-fire": "final_Sdyd"})
            sdyd_df = pd.concat([sdyd_df, missing_sdyd], ignore_index=True)

        sdyd_df = sdyd_df.sort_values(by=id_col).reset_index(drop=True)

    except PulpSolverError:
        print("Solver failed!")
        return None

    results = (
        model_primary_status,
        treatment_cost_vectors,
        sediment_yield_reduction_thresholds,
        selected_hillslopes,
        treatment_hillslopes,
        total_Sddc_reduction,
        final_Sddc,
        hillslopes_sdyd,
        sdyd_df,
        untreatable_sdyd,
        total_cost,
        total_fixed_cost,
    )
    if return_increase_class:
        return results + (untreatable_sdyd_increase,)
    return results

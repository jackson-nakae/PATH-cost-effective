def find_threshold_ranges(data, treatments, treatment_cost, treatment_quantity, 
                                    fixed_cost, step_size=5, tolerance=1e-6):
    """
    Find SDDC threshold range by:
    - Decreasing SDDC by `step_size` until model status == 0 (infeasible)
    - Then increasing by 1 until status == 1 (feasible). That SDDC is the lower bound.

    Returns:
    - sddc_threshold_range: (lower_bound_sddc, max_sddc_threshold)
    - sdyd_threshold_range: (min_sdyd_threshold, max_sdyd_threshold)
    """
    import pandas as pd
    import numpy as np
    import os
    from contextlib import redirect_stdout, redirect_stderr

    from PATH_CE import ce_select_sites_2

    # Determine Sdyd min/max from data based on post-treat columns for provided treatments
    sdyd_treatments = []
    for i in range(len(treatments)):
        sdyd_treatment = 'Sdyd post-treat ' + treatments[i]
        sdyd_treatments.append(sdyd_treatment)

    max_sdyd_val = int(data['Sdyd post-fire'].max()) + 1
    try:
        min_sdyd_val = data[sdyd_treatments].min().min()
    except Exception:
        # Fallback if post-treat columns differ; use post-fire min
        min_sdyd_val = data['Sdyd post-fire'].min()
    min_sdyd_round = int(min_sdyd_val)

    # Determine max SDDC threshold as the sum of post-fire NTU (or t)
    max_sddc_val = data['NTU post-fire'].sum()
    #max_sddc_val = data['Sddc post-fire'].sum()
    max_sddc_round = int(max_sddc_val) + 1

    # Phase 1: Decrease by step_size until status == 0
    current_sddc = max_sddc_round
    hit_infeasible = False
    while current_sddc > 0:
        try:
            with open(os.devnull, 'w') as devnull:
                with redirect_stdout(devnull), redirect_stderr(devnull):
                    result = ce_select_sites_2(
                        data=data,
                        treatments=treatments,
                        treatment_cost=treatment_cost,
                        treatment_quantity=treatment_quantity,
                        fixed_cost=fixed_cost,
                        sdyd_threshold=max_sdyd_val,
                        sddc_threshold=current_sddc,
                        slope_range=None,
                        bs_threshold=None,
                    )
            status = result[0]
        except Exception:
            status = None
        
        if status == 0:
            hit_infeasible = True
            break
        
        current_sddc = max(0, current_sddc - step_size)

    # Phase 2: Increase by 1 until status == 1 (feasible)
    lower_bound_sddc = current_sddc
    while lower_bound_sddc <= max_sddc_round:
        try:
            with open(os.devnull, 'w') as devnull:
                with redirect_stdout(devnull), redirect_stderr(devnull):
                    result = ce_select_sites_2(
                        data=data,
                        treatments=treatments,
                        treatment_cost=treatment_cost,
                        treatment_quantity=treatment_quantity,
                        fixed_cost=fixed_cost,
                        sdyd_threshold=max_sdyd_val,
                        sddc_threshold=lower_bound_sddc,
                        slope_range=None,
                        bs_threshold=None,
                    )
            status = result[0]
        except Exception:
            status = None
        
        if status == 1:
            break
        lower_bound_sddc += 1

    # If never feasible, set lower bound to max
    if lower_bound_sddc > max_sddc_round:
        lower_bound_sddc = max_sddc_round

    sddc_threshold_range = (lower_bound_sddc, max_sddc_round)
    sdyd_threshold_range = (min_sdyd_round, max_sdyd_val)
    return sddc_threshold_range, sdyd_threshold_range

def all_thresholds(data, treatments, treatment_cost, treatment_quantity, fixed_cost, sdyd_threshold, sddc_threshold, sdyd_threshold_range, sddc_threshold_range):
    
    from PATH_CE import ce_select_sites_2
    import numpy as np
    import pandas as pd
    import os
    from contextlib import redirect_stdout, redirect_stderr

    sdyd_range_size = sdyd_threshold_range[1] - sdyd_threshold_range[0]
    if sdyd_range_size <= 20:
        sdyd_step_values = np.linspace(sdyd_threshold_range[0], sdyd_threshold_range[1], sdyd_range_size + 1, dtype=int)
    elif 20<sdyd_range_size<=200:
        sdyd_step_values = np.linspace(sdyd_threshold_range[0], sdyd_threshold_range[1], 20, dtype=int)
    elif 200<sdyd_range_size<=2000:
        sdyd_step_values = np.linspace(sdyd_threshold_range[0], sdyd_threshold_range[1], 50, dtype=int)
    else:
        sdyd_step_values = np.linspace(sdyd_threshold_range[0], sdyd_threshold_range[1], 75, dtype=int)

    # Ensure specified sdyd_threshold is included
    if sdyd_threshold not in sdyd_step_values:
        closest_sdyd_idx=np.argmin(np.abs(sdyd_step_values-sdyd_threshold))
        sdyd_step_values=np.delete(sdyd_step_values, closest_sdyd_idx)
        sdyd_step_values = np.append(sdyd_step_values, sdyd_threshold)
        sdyd_step_values = np.sort(sdyd_step_values)
    else:
        pass
        
    sddc_range_size = sddc_threshold_range[1] - sddc_threshold_range[0]
    if sddc_range_size <= 20:
        sddc_step_values = np.linspace(sddc_threshold_range[0], sddc_threshold_range[1], sddc_range_size + 1, dtype=int)
    elif 20<sddc_range_size<=200:
        sddc_step_values = np.linspace(sddc_threshold_range[0], sddc_threshold_range[1], 20, dtype=int)
    elif 200<sddc_range_size<=2000:
        sddc_step_values = np.linspace(sddc_threshold_range[0], sddc_threshold_range[1], 50, dtype=int)
    else:
        sddc_step_values = np.linspace(sddc_threshold_range[0], sddc_threshold_range[1], 75, dtype=int)
    
    # Ensure specified sddc_threshold is included
    if sddc_threshold not in sddc_step_values:
        closest_sddc_idx=np.argmin(np.abs(sddc_step_values-sddc_threshold))
        sddc_step_values=np.delete(sddc_step_values, closest_sddc_idx)
        sddc_step_values = np.append(sddc_step_values, sdyd_threshold)
        sddc_step_values = np.sort(sddc_step_values)
    else:
        pass

    results = []
    for sdyd_thr in sdyd_step_values:
        for sddc_thr in sddc_step_values:
            try:
                with open(os.devnull, 'w') as devnull:
                    with redirect_stdout(devnull), redirect_stderr(devnull):
                        status,treatment_cost_vectors, sediment_yield_reduction_thresholds, selected_hillslopes, treatment_hillslopes, total_Sddc_reduction, final_Sddc, hillslopes_sdyd, sdyd_df, untreatable_sdyd, total_cost, total_fixed_cost = ce_select_sites_2(
                            data,
                            treatments,
                            treatment_cost,
                            treatment_quantity,
                            fixed_cost,
                            sdyd_thr,
                            sddc_thr,
                            slope_range=(None),
                            bs_threshold=(None)
                        )
                
                results.append({
                    'sddc_threshold': sddc_thr,
                    'sdyd_threshold': sdyd_thr,
                    'selected_hillslopes': selected_hillslopes,
                    'treatment_hillslopes': treatment_hillslopes,
                    'total_Sddc_reduction': total_Sddc_reduction,
                    'final_Sddc': final_Sddc,
                    'hillslopes_sdyd': hillslopes_sdyd,
                    'sdyd_df': sdyd_df,
                    'untreatable_sdyd': untreatable_sdyd,
                    'total_cost': total_cost,
                    'total_fixed_cost': total_fixed_cost
                })
            except Exception as e:
                print(f"Error at sdyd: {sdyd_thr}, sddc: {sddc_thr} - {e}")
    
    results_df = pd.DataFrame(results)
    return results_df

def plot_sddc_vs_cost(results_df, sdyd_threshold=200, sddc_threshold=200, ax=None, figsize=(10, 6)):
    """
    Plot Sddc threshold vs total cost from results_df for a fixed Sdyd threshold.

    Parameters
    - results_df: DataFrame with columns ['sddc_threshold','sdyd_threshold','total_cost']
    - sdyd_threshold: int/float, the Sdyd threshold to filter on (default 200)
    - ax: matplotlib.axes.Axes (optional). If None, a new figure is created.
    - figsize: tuple for figure size when ax is None.

    Returns
    - ax: matplotlib axes containing the plot
    """
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    df_plot = results_df[results_df['sdyd_threshold'] ==sdyd_threshold].copy()
    if df_plot.empty:
        raise ValueError(f"No rows found in results_df for sdyd_threshold == {sdyd_threshold}")

    # ensure correct dtypes and sort
    df_plot['sddc_threshold'] = df_plot['sddc_threshold'].astype(float)
    df_plot['total_cost'] = df_plot['total_cost'].astype(float)
    df_plot = df_plot.sort_values('sddc_threshold')

    x = df_plot['sddc_threshold'].values
    y = df_plot['total_cost'].values
    y_plot = y
    ylabel = 'Total Cost ($)'
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    ax.plot(x, y_plot, linestyle='-', color='C0', label=f'Sdyd = {sdyd_threshold}')
    ax.set_xlabel('Sddc Threshold (t)')
    ax.set_ylabel(ylabel)
    ax.set_title(f'Total Cost vs Outlet Sediment Discharge Threshold (Sdyd threshold (t/ac) = {sdyd_threshold})', fontsize=11)
    ax.grid(True, linestyle=':', alpha=0.6)

    #Indicate the location of the specified sdyd_threshold with arrow and dot
    corresponding_cost = y_plot[x==sddc_threshold][0]
    # Add a dot at the specified threshold location
    #ax.plot(sddc_threshold, corresponding_cost, 'ro', markersize=5, zorder=5)
    
    # Add an arrow pointing to the threshold location
    # ax.annotate(f'User Sediment Discharge Threshold\nSddc(t) = {sddc_threshold}\nCost({ylabel.split("(")[1].split(")")[0]})={corresponding_cost:.2f}',
    #             xy=(sddc_threshold, corresponding_cost),
    #             xytext=(sddc_threshold - 20, corresponding_cost + (0.1 * max(y_plot))),
    #             arrowprops=dict( arrowstyle='->', lw=2, color='red'),
    #             fontsize=10,
    #             bbox=dict(boxstyle='round,pad=0.3', fc='lightblue', alpha=0.7))
    
    
    #plt.tight_layout()
    #plt.show()
    
    return ax

def plot_sdyd_vs_cost(results_df, sdyd_threshold=200, sddc_threshold=200, ax=None, figsize=(10, 6)):
    """
    Plot Sdyd threshold vs total cost from results_df for a fixed Sddc threshold.

    Parameters
    - results_df: DataFrame with columns ['sddc_threshold','sdyd_threshold','total_cost']
    - sdyd_threshold: int/float, the Sdyd threshold to highlight on the plot (default 200)
    - sddc_threshold: int/float, the Sddc threshold to filter on (default 200)
    - ax: matplotlib.axes.Axes (optional). If None, a new figure is created.
    - figsize: tuple for figure size when ax is None.

    Returns
    - ax: matplotlib axes containing the plot
    """
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    
    # Find the closest Sddc threshold in the data
    sddc_thresholds = results_df['sddc_threshold'].unique()
    closest_sddc = min(sddc_thresholds, key=lambda x: abs(x - sddc_threshold))

    df_plot = results_df[results_df['sddc_threshold'] == sddc_threshold].copy()
    if df_plot.empty:
        raise ValueError(f"No rows found in results_df for sddc_threshold == {sddc_threshold}")

    # Ensure correct dtypes and sort
    df_plot['sdyd_threshold'] = df_plot['sdyd_threshold'].astype(float)
    df_plot['total_cost'] = df_plot['total_cost'].astype(float)
    df_plot = df_plot.sort_values('sdyd_threshold')

    x = df_plot['sdyd_threshold'].values
    y = df_plot['total_cost'].values
    y_plot = y
    ylabel = 'Total Cost ($)'
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)


    ax.plot(x, y_plot, linestyle='-', color='C0', label=f'Sddc = {sddc_threshold}')
    ax.set_xlabel('Sdyd Threshold (t/ac)')
    ax.set_ylabel(ylabel)
    ax.set_title(f'Total Cost vs Hillslope Sediment Yield Threshold (Sddc threshold (t) = {sddc_threshold})', fontsize=11)
    ax.grid(True, linestyle=':', alpha=0.6)
    
    # Indicate the location of the specified sdyd_threshold with arrow and dot
    corresponding_cost = y_plot[x==sdyd_threshold][0]
    
    # Add a dot at the specified threshold location
    #ax.plot(sdyd_threshold, corresponding_cost, 'ro', markersize=5, zorder=5)
    
    # Add an arrow pointing to the threshold location
    # ax.annotate(f'User Sediment Yield Threshold\nSdyd = {sdyd_threshold}\nCost ({ylabel.split("(")[1].split(")")[0]})={corresponding_cost:.2f}',
    #             xy=(sdyd_threshold, corresponding_cost),
    #             xytext=(sdyd_threshold - 20, corresponding_cost + (0.1 * max(y_plot))),
    #             arrowprops=dict( arrowstyle='->', lw=2, color='red'),
    #             fontsize=10,
    #             bbox=dict(boxstyle='round,pad=0.3', fc='lightblue', alpha=0.7))
    

    #if ax is None:
        #plt.tight_layout()
        #plt.show()

    return ax

def create_jupyter_widgets_interactive_map(final_results, gdf, gdf_channels=None,
                                          initial_sdyd=200, initial_sddc=200,
                                          width=1200, height=700):
    """
    Create an interactive map with Jupyter widgets (ipywidgets) and Plotly.
    This provides smooth, real-time slider interactions within Jupyter notebooks.
    
    Parameters:
    - final_results: DataFrame with optimization results
    - gdf: GeoDataFrame for hillslope mapping with 'WeppID' column
    - gdf_channels: GeoDataFrame for channel mapping (optional)
    - initial_sdyd, initial_sddc: Initial threshold values
    - width, height: Figure dimensions
    
    Returns:
    - Interactive widget with map and controls
    """
    import ipywidgets as widgets
    from IPython.display import display, clear_output
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import ast
    import pandas as pd
    import numpy as np
    
    print("Creating interactive Jupyter widgets map...")
    
    # Get unique threshold values
    sdyd_values = sorted(final_results['sdyd_threshold'].unique())
    sddc_values = sorted(final_results['sddc_threshold'].unique())
    
    print(f"SDYD range: {min(sdyd_values)} - {max(sdyd_values)} ({len(sdyd_values)} values)")
    print(f"SDDC range: {min(sddc_values)} - {max(sddc_values)} ({len(sddc_values)} values)")
    
    # Pre-process geometries for fast access
    hillslope_coords = {}
    for idx, row in gdf.iterrows():
        try:
            if hasattr(row.geometry, 'exterior'):
                coords = list(row.geometry.exterior.coords)
                if coords:
                    x_coords, y_coords = zip(*coords)
                    hillslope_coords[row['WeppID']] = (list(x_coords), list(y_coords))
        except:
            continue
    
    print(f"Processed {len(hillslope_coords)} hillslope geometries")
    
    # Process channel geometries
    channel_x, channel_y = [], []
    if gdf_channels is not None and not gdf_channels.empty:
        for _, row in gdf_channels.iterrows():
            try:
                geom = row.geometry
                coords = []
                if geom.geom_type == 'LineString':
                    coords = list(geom.coords)
                elif geom.geom_type == 'MultiLineString':
                    for line in geom.geoms:
                        coords.extend(list(line.coords))
                        coords.append((None, None))
                
                if coords:
                    x_vals, y_vals = zip(*coords)
                    channel_x.extend(x_vals)
                    channel_y.extend(y_vals)
                    channel_x.append(None)
                    channel_y.append(None)
            except:
                continue
    
    # Pre-process all threshold combinations with correct treatment mapping
    threshold_data = {}
    for _, row in final_results.iterrows():
        sdyd_thr = int(row['sdyd_threshold'])
        sddc_thr = int(row['sddc_threshold'])
        key = (sdyd_thr, sddc_thr)
        
        # Parse treatment data
        treatment_hillslopes_raw = row['treatment_hillslopes']
        selected_hillslopes = row['selected_hillslopes']
        
        if isinstance(treatment_hillslopes_raw, str):
            try:
                treatment_hillslopes = ast.literal_eval(treatment_hillslopes_raw)
            except:
                treatment_hillslopes = [[], [], []]
        else:
            treatment_hillslopes = treatment_hillslopes_raw if treatment_hillslopes_raw else [[], [], []]
            
        if isinstance(selected_hillslopes, str):
            try:
                selected_hillslopes = ast.literal_eval(selected_hillslopes)
            except:
                selected_hillslopes = []
        
        # Ensure proper structure
        if not isinstance(treatment_hillslopes, list) or len(treatment_hillslopes) < 3:
            treatment_hillslopes = [[], [], []]
            
        # Get treatment sets - map to correct tons/acre values
        treat_05_tons = set(treatment_hillslopes[0] if isinstance(treatment_hillslopes[0], list) else [])  # 0.5 tons/acre
        treat_10_tons = set(treatment_hillslopes[1] if isinstance(treatment_hillslopes[1], list) else [])  # 1.0 tons/acre
        treat_20_tons = set(treatment_hillslopes[2] if isinstance(treatment_hillslopes[2], list) else [])  # 2.0 tons/acre
        selected_ids = set(selected_hillslopes)
        all_wepp_ids = set(hillslope_coords.keys())
        does_not_meet_threshold = all_wepp_ids - selected_ids
        
        threshold_data[key] = {
            'treat_05_tons': treat_05_tons,
            'treat_10_tons': treat_10_tons,
            'treat_20_tons': treat_20_tons,
            'does_not_meet': does_not_meet_threshold,
            'total_cost': float(row['total_cost']),
            'final_sddc': float(row['final_Sddc'])
        }
    
    print(f"Pre-processed {len(threshold_data)} threshold combinations")
    
    # Create output widget for the plot
    output = widgets.Output()
    
    # Create sliders
    sdyd_slider = widgets.IntSlider(
        value=initial_sdyd,
        min=min(sdyd_values),
        max=max(sdyd_values),
        step=sdyd_values[1] - sdyd_values[0] if len(sdyd_values) > 1 else 5,
        description='SDYD Threshold:',
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='400px')
    )
    
    sddc_slider = widgets.IntSlider(
        value=initial_sddc,
        min=min(sddc_values),
        max=max(sddc_values),
        step=sddc_values[1] - sddc_values[0] if len(sddc_values) > 1 else 5,
        description='SDDC Threshold:',
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='400px')
    )
    
    # Create info display widgets
    cost_label = widgets.HTML(value="<b>Total Cost:</b> $0")
    sddc_label = widgets.HTML(value="<b>Final SDDC:</b> 0.0")
    
    # Treatment count widgets with correct colors and labels
    treat_20_count = widgets.HTML(value="<span style='color: #0d5016;'>●</span> 2.0 tons/acre: 0")
    treat_10_count = widgets.HTML(value="<span style='color: #2d7a32;'>●</span> 1.0 tons/acre: 0") 
    treat_05_count = widgets.HTML(value="<span style='color: #66bb6a;'>●</span> 0.5 tons/acre: 0")
    does_not_meet_count = widgets.HTML(value="<span style='color: red;'>⬜</span> Does not meet SDYD threshold: 0")
    
    def build_group_coords(wepp_ids, color, name):
        """Build coordinate arrays for a group of hillslopes"""
        if not wepp_ids:
            return go.Scatter(x=[], y=[], mode='lines', line=dict(color='black', width=1), 
                            fill='toself', fillcolor=color, name=name, showlegend=True,
                            hovertemplate=f'<b>{name}</b><extra></extra>')
        
        all_x, all_y = [], []
        for wepp_id in wepp_ids:
            if wepp_id in hillslope_coords:
                x_coords, y_coords = hillslope_coords[wepp_id]
                all_x.extend(x_coords)
                all_y.extend(y_coords)
                all_x.append(None)
                all_y.append(None)
        
        # For "does not meet threshold", use white fill with red outline
        if name == "Does not meet SDYD threshold":
            line_color = 'red'
            line_width = 2
        else:
            line_color = 'black'
            line_width = 0.5
        
        return go.Scatter(
            x=all_x, y=all_y, mode='lines', line=dict(color=line_color, width=line_width),
            fill='toself', fillcolor=color, name=name, showlegend=True,
            opacity=0.8,
            hovertemplate=f'<b>{name}</b><br>Count: {len(wepp_ids)}<extra></extra>'
        )
    
    def update_plot(change=None):
        """Update the plot when sliders change"""
        with output:
            clear_output(wait=True)
            
            # Get current threshold values
            sdyd_val = sdyd_slider.value
            sddc_val = sddc_slider.value
            key = (sdyd_val, sddc_val)
            
            # Get data for current thresholds
            current_data = threshold_data.get(key, {})
            
            if not current_data:
                print(f"Warning: No data for SDYD={sdyd_val}, SDDC={sddc_val}")
            
            # Update info displays
            cost_label.value = f"<b>Total Cost:</b> ${current_data.get('total_cost', 0):,.0f}"
            sddc_label.value = f"<b>Final SDDC:</b> {current_data.get('final_sddc', 0):.1f}"
            
            # Update treatment counts with correct colors and labels
            treat_20_count.value = f"<span style='color: #0d5016; font-size: 16px;'>●</span> 2.0 tons/acre: {len(current_data.get('treat_20_tons', []))}"
            treat_10_count.value = f"<span style='color: #2d7a32; font-size: 16px;'>●</span> 1.0 tons/acre: {len(current_data.get('treat_10_tons', []))}"
            treat_05_count.value = f"<span style='color: #66bb6a; font-size: 16px;'>●</span> 0.5 tons/acre: {len(current_data.get('treat_05_tons', []))}"
            does_not_meet_count.value = f"<span style='color: red; font-size: 16px;'>⬜</span> Does not meet SDYD threshold: {len(current_data.get('does_not_meet', []))}"
            
            # Create figure
            fig = go.Figure()
            
            # Add hillslope traces with correct colors (shades of green)
            if current_data:
                # Add in order from lightest to darkest, with "does not meet" first
                fig.add_trace(build_group_coords(current_data.get('does_not_meet', []), 'white', 'Does not meet SDYD threshold'))
                fig.add_trace(build_group_coords(current_data.get('treat_05_tons', []), '#66bb6a', '0.5 tons/acre'))
                fig.add_trace(build_group_coords(current_data.get('treat_10_tons', []), '#2d7a32', '1.0 tons/acre'))
                fig.add_trace(build_group_coords(current_data.get('treat_20_tons', []), '#0d5016', '2.0 tons/acre'))
            
            # Add channels
            if channel_x and channel_y:
                fig.add_trace(go.Scatter(
                    x=channel_x, y=channel_y, mode='lines',
                    line=dict(color='blue', width=2),
                    name='Stream Channels', showlegend=True,
                    hovertemplate='<b>Stream Channel</b><extra></extra>'
                ))
            
            # Update layout
            fig.update_layout(
                title=f"PATH Optimization Results - SDYD: {sdyd_val}, SDDC: {sddc_val}",
                width=width, height=height,
                xaxis=dict(title="Longitude", scaleanchor="y", scaleratio=1),
                yaxis=dict(title="Latitude"),
                showlegend=True,
                legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.8)'),
                margin=dict(l=50, r=50, t=80, b=50),
                plot_bgcolor='lightblue'
            )
            
            fig.show()
    
    # Connect sliders to update function
    sdyd_slider.observe(update_plot, names='value')
    sddc_slider.observe(update_plot, names='value')
    
    # Create layout
    controls = widgets.VBox([
        widgets.HTML("<h3>🎛️ Threshold Controls</h3>"),
        sdyd_slider,
        sddc_slider,
        widgets.HTML("<br><h4>📊 Results</h4>"),
        widgets.HBox([cost_label, sddc_label]),
        widgets.HTML("<br><h4>🗺️ Treatment Summary</h4>"),
        widgets.VBox([treat_20_count, treat_10_count, treat_05_count, 
                     does_not_meet_count])
    ])
    
    # Create main widget
    main_widget = widgets.HBox([
        controls,
        output
    ], layout=widgets.Layout(border='2px solid #ddd', padding='10px'))
    
    # Initial plot
    update_plot()
    
    print("✓ Interactive Jupyter widgets map created!")
    print("Use the sliders to explore different threshold scenarios.")
    
    return main_widget

def create_jupyter_widgets_fast_map(final_results, gdf, gdf_channels=None,
                                   initial_sdyd=200, initial_sddc=200):
    """
    Create a fast, lightweight interactive map using Jupyter widgets and matplotlib.
    This version prioritizes speed and responsiveness over visual complexity.
    
    Parameters:
    - final_results: DataFrame with optimization results
    - gdf: GeoDataFrame for hillslope mapping with 'WeppID' column
    - gdf_channels: GeoDataFrame for channel mapping (optional)
    - initial_sdyd, initial_sddc: Initial threshold values
    
    Returns:
    - Interactive widget with map and controls
    """
    import ipywidgets as widgets
    import matplotlib.pyplot as plt
    from IPython.display import display, clear_output
    import ast
    import pandas as pd
    import numpy as np
    
    print("Creating fast Jupyter widgets map with matplotlib...")
    
    # Get exact threshold values from the data
    sdyd_values = sorted(final_results['sdyd_threshold'].unique())
    sddc_values = sorted(final_results['sddc_threshold'].unique())
    
    print(f"Available thresholds: SDYD {len(sdyd_values)} values ({min(sdyd_values)}-{max(sdyd_values)})")
    print(f"                     SDDC {len(sddc_values)} values ({min(sddc_values)}-{max(sddc_values)})")
    
    # Pre-process threshold data with exact matching
    threshold_data = {}
    for _, row in final_results.iterrows():
        sdyd_thr = row['sdyd_threshold']  # Keep as original type
        sddc_thr = row['sddc_threshold']  # Keep as original type
        key = (sdyd_thr, sddc_thr)
        
        # Parse treatment data
        treatment_hillslopes_raw = row['treatment_hillslopes']
        selected_hillslopes = row['selected_hillslopes']
        untreatable_sdyd = row['untreatable_sdyd']
        
        if isinstance(treatment_hillslopes_raw, str):
            try:
                treatment_hillslopes = ast.literal_eval(treatment_hillslopes_raw)
            except:
                treatment_hillslopes = [[], [], []]
        else:
            treatment_hillslopes = treatment_hillslopes_raw if treatment_hillslopes_raw else [[], [], []]
            
        if isinstance(selected_hillslopes, str):
            try:
                selected_hillslopes = ast.literal_eval(selected_hillslopes)
            except:
                selected_hillslopes = []
          # Handle untreatable_sdyd - this contains hillslopes that exceed SDYD threshold
        if pd.isna(untreatable_sdyd) or str(untreatable_sdyd).strip() in ['nan', '', 'None']:
            untreatable_ids = []
        elif isinstance(untreatable_sdyd, str):
            try:
                # Handle DataFrame string representation
                clean_str = str(untreatable_sdyd).strip()
                
                # Look for DataFrame-like content
                if 'wepp_id' in clean_str and 'final_Sdyd' in clean_str:
                    # Extract wepp_id values using regex
                    import re
                    # Look for patterns like "1     77.7193" or "  1     77.7193"
                    pattern = r'^\s*(\d+)\s+[\d\.]+.*$'
                    wepp_ids = []
                    
                    for line in clean_str.split('\n'):
                        match = re.match(pattern, line)
                        if match:
                            wepp_ids.append(int(match.group(1)))
                    
                    untreatable_ids = wepp_ids
                else:
                    # Try to parse as a simple list or other format
                    try:
                        parsed = ast.literal_eval(untreatable_sdyd)
                        if isinstance(parsed, list):
                            untreatable_ids = parsed
                        else:
                            untreatable_ids = []
                    except:
                        untreatable_ids = []
            except Exception as e:
                print(f"Warning: Could not parse untreatable data: {e}")
                untreatable_ids = []
        elif hasattr(untreatable_sdyd, 'empty') and not untreatable_sdyd.empty:
            untreatable_ids = untreatable_sdyd['wepp_id'].tolist() if 'wepp_id' in untreatable_sdyd.columns else []
        elif isinstance(untreatable_sdyd, list):
            untreatable_ids = untreatable_sdyd
        else:
            untreatable_ids = []
        
        if not isinstance(treatment_hillslopes, list) or len(treatment_hillslopes) < 3:
            treatment_hillslopes = [[], [], []]
              # Get treatment sets - these correspond to 0.5, 1.0, and 2.0 tons/acre
        treat_05_ids = set(treatment_hillslopes[0] if isinstance(treatment_hillslopes[0], list) else [])
        treat_10_ids = set(treatment_hillslopes[1] if isinstance(treatment_hillslopes[1], list) else [])
        treat_20_ids = set(treatment_hillslopes[2] if isinstance(treatment_hillslopes[2], list) else [])
        untreatable_ids_set = set(untreatable_ids)
        selected_ids = set(selected_hillslopes)
        all_wepp_ids = set(gdf['WeppID'].values)
        not_selected_ids = all_wepp_ids - selected_ids
        
        # Hillslopes that don't meet SDYD threshold = all hillslopes not in selected_hillslopes
        # These should get red outline as "Does not meet SDYD threshold"
        
        threshold_data[key] = {
            'treat_05': treat_05_ids,      # 0.5 tons/acre
            'treat_10': treat_10_ids,      # 1.0 tons/acre 
            'treat_20': treat_20_ids,      # 2.0 tons/acre
            'untreatable': untreatable_ids_set,  # Untreatable (exceed SDYD limit) - red outline
            'no_treatment': not_selected_ids,  # Not selected for treatment
            'total_cost': float(row['total_cost']),
            'final_sddc': float(row['final_Sddc'])
        }
    
    print(f"Processed {len(threshold_data)} threshold combinations")
    
    # Create matplotlib-based interactive function
    def interactive_plot(sdyd_threshold, sddc_threshold):
        """Create matplotlib plot for given thresholds"""
        key = (sdyd_threshold, sddc_threshold)
        current_data = threshold_data.get(key, {})
        
        if not current_data:
            print(f"Warning: No exact match for SDYD={sdyd_threshold}, SDDC={sddc_threshold}")
            return
        
        # Create figure with no axes labels
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        
        # Define correct colors - shades of green plus white and red outline
        colors = {
            'treat_20': '#0d5016',    # Dark green - 2.0 tons/acre
            'treat_10': '#2d7a32',    # Medium green - 1.0 tons/acre
            'treat_05': '#66bb6a',    # Light green - 0.5 tons/acre
            'no_treatment': 'white',  # White - not selected
            'untreatable': 'white'    # White with red outline - doesn't meet SDYD threshold
        }
          # Count hillslopes for legend
        counts = {
            'treat_20': len(current_data.get('treat_20', [])),
            'treat_10': len(current_data.get('treat_10', [])),
            'treat_05': len(current_data.get('treat_05', [])),
            'untreatable': len(current_data.get('untreatable', [])),
            'no_treatment': len(current_data.get('no_treatment', []))
        }
        
        print(f"Treatment counts: 2.0={counts['treat_20']}, 1.0={counts['treat_10']}, 0.5={counts['treat_05']}, untreatable={counts['untreatable']}, no_treatment={counts['no_treatment']}")
          # Plot hillslopes by treatment type
        for _, row in gdf.iterrows():
            wepp_id = row['WeppID']
            
            if wepp_id in current_data.get('treat_20', set()):
                fill_color = colors['treat_20']
                edge_color = 'black'
                edge_width = 1
                treatment = '2.0 tons/acre'
            elif wepp_id in current_data.get('treat_10', set()):
                fill_color = colors['treat_10']
                edge_color = 'black'
                edge_width = 1
                treatment = '1.0 tons/acre'
            elif wepp_id in current_data.get('treat_05', set()):
                fill_color = colors['treat_05']
                edge_color = 'black'
                edge_width = 1
                treatment = '0.5 tons/acre'
            elif wepp_id in current_data.get('untreatable', set()):
                fill_color = 'lightgray'  # Light gray for untreatable
                edge_color = 'red'  # Red outline for untreatable (exceeds SDYD limit)
                edge_width = 2
                treatment = 'Does not meet SDYD threshold'
            elif wepp_id in current_data.get('no_treatment', set()):
                fill_color = 'lightgray'  # Light gray for hillslopes that don't meet threshold
                edge_color = 'black'  # Red outline for hillslopes that don't meet SDYD threshold
                edge_width = 1
                treatment = 'Untreated'
            else:
                fill_color = 'lightgray'
                edge_color = 'black'
                edge_width = 1
                treatment = 'Other'
            
            # Plot the hillslope
            if hasattr(row.geometry, 'exterior'):
                x, y = row.geometry.exterior.xy
                ax.fill(x, y, color=fill_color, edgecolor=edge_color, linewidth=edge_width, alpha=0.8)
        
        # Add channels if provided
        if gdf_channels is not None and not gdf_channels.empty:
            for _, row in gdf_channels.iterrows():
                if row.geometry.geom_type == 'LineString':
                    x, y = row.geometry.xy
                    ax.plot(x, y, color='blue', linewidth=2, alpha=0.8)
                elif row.geometry.geom_type == 'MultiLineString':
                    for line in row.geometry.geoms:
                        x, y = line.xy
                        ax.plot(x, y, color='blue', linewidth=2, alpha=0.8)
        
        # Customize plot - remove axes and labels as requested
        ax.set_aspect('equal')
        ax.set_title(f'PATH Optimization Results\\n' +
                    f'SDYD Threshold: {sdyd_threshold} | SDDC Threshold: {sddc_threshold}\\n' +
                    f'Total Cost: ${current_data.get("total_cost", 0):,.0f} | ' +
                    f'Final SDDC: {current_data.get("final_sddc", 0):.1f}', fontsize=14)
        
        # Remove longitude/latitude axes as requested
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel('')
        ax.set_ylabel('')
          # Create custom legend with correct labels and colors
        legend_elements = [
            plt.Rectangle((0,0),1,1, facecolor=colors['treat_20'], edgecolor='black', 
                         label=f'2.0 tons/acre ({counts["treat_20"]})'),
            plt.Rectangle((0,0),1,1, facecolor=colors['treat_10'], edgecolor='black', 
                         label=f'1.0 tons/acre ({counts["treat_10"]})'),
            plt.Rectangle((0,0),1,1, facecolor=colors['treat_05'], edgecolor='black', 
                         label=f'0.5 tons/acre ({counts["treat_05"]})'),
            plt.Rectangle((0,0),1,1, facecolor='lightgray', edgecolor='red', linewidth=1,
                         label=f'Does not meet SDYD threshold ({counts["untreatable"]})'),
            plt.Rectangle((0,0),1,1, facecolor='lightgray', edgecolor='black', linewidth=2,
                         label=f'Untreated ({counts["no_treatment"]})')
        ]
        
        if gdf_channels is not None and not gdf_channels.empty:
            legend_elements.append(plt.Line2D([0], [0], color='blue', linewidth=2, label='Stream Channels'))
        
        ax.legend(handles=legend_elements, loc='upper right', framealpha=0.9, fontsize=10)
        
        plt.tight_layout()
        plt.show()
    
    # Find closest initial values if exact match doesn't exist
    # def find_closest_value(target, values_list):
    #     return min(values_list, key=lambda x: abs(x - target))
    
    # closest_sdyd = find_closest_value(initial_sdyd, sdyd_values)
    # closest_sddc = find_closest_value(initial_sddc, sddc_values)
    
    # use a SelectionSlider (discrete values from a list) instead of an IntSlider with a step
    closest_sdyd = min(sdyd_values, key=lambda x: abs(x - initial_sdyd))
    closest_sddc = min(sddc_values, key=lambda x: abs(x - initial_sddc))

    interactive_widget = widgets.interact(
        interactive_plot,
        sdyd_threshold=widgets.SelectionSlider(
            options=sdyd_values,
            value=closest_sdyd,
            description='SDYD Threshold:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='500px')
        ),
        sddc_threshold=widgets.SelectionSlider(
            options=sddc_values,
            value=closest_sddc,
            description='SDDC Threshold:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='500px')
        )
    )
    
    print("✓ Fast matplotlib-based interactive map created!")
    print("Use the dropdown menus to explore threshold scenarios with exact value matching.")
    
    return interactive_widget


def create_plotly_map_for_quarto(final_results, gdf, gdf_channels=None,
                                  initial_sdyd=200, initial_sddc=200,
                                  width=1200, height=800):
    """
    Create an interactive Plotly map with sliders that works in Quarto HTML output.
    Uses Plotly's native slider functionality instead of ipywidgets.
    
    Parameters:
    - final_results: DataFrame with optimization results
    - gdf: GeoDataFrame for hillslope mapping with 'WeppID' column
    - gdf_channels: GeoDataFrame for channel mapping (optional)
    - initial_sdyd, initial_sddc: Initial threshold values
    - width, height: Figure dimensions
    
    Returns:
    - Plotly figure object that renders in Quarto
    """
    import plotly.graph_objects as go
    import ast
    import pandas as pd
    import numpy as np
    
    print("Creating Plotly map for Quarto...")
    
    # Get unique threshold values
    sdyd_values = sorted(final_results['sdyd_threshold'].unique())
    sddc_values = sorted(final_results['sddc_threshold'].unique())
    
    print(f"SDYD range: {min(sdyd_values)} - {max(sdyd_values)} ({len(sdyd_values)} values)")
    print(f"SDDC range: {min(sddc_values)} - {max(sddc_values)} ({len(sddc_values)} values)")
    
    # Pre-process geometries
    hillslope_coords = {}
    for idx, row in gdf.iterrows():
        try:
            if hasattr(row.geometry, 'exterior'):
                coords = list(row.geometry.exterior.coords)
                if coords:
                    x_coords, y_coords = zip(*coords)
                    hillslope_coords[row['WeppID']] = (list(x_coords), list(y_coords))
        except:
            continue
    
    # Pre-process channel geometries
    channel_coords = []
    if gdf_channels is not None:
        for idx, row in gdf_channels.iterrows():
            try:
                if hasattr(row.geometry, 'coords'):
                    coords = list(row.geometry.coords)
                    if coords:
                        x_coords, y_coords = zip(*coords)
                        channel_coords.append((list(x_coords), list(y_coords)))
            except:
                continue
    
    # Define treatment colors (green gradient)
    treatment_colors = {
        0.5: '#66bb6a',   # Light green
        1.0: '#2d7a32',   # Medium green
        2.0: '#0d5016'    # Dark green
    }
    
    # Create frames for each threshold combination
    frames = []
    slider_steps = []
    
    # Find initial frame index
    initial_frame_idx = 0
    
    for frame_idx, (sdyd_val, sddc_val) in enumerate([(s, d) for s in sdyd_values for d in sddc_values]):
        if sdyd_val == initial_sdyd and sddc_val == initial_sddc:
            initial_frame_idx = frame_idx
            
        # Get data for this threshold combination
        row_data = final_results[
            (final_results['sdyd_threshold'] == sdyd_val) & 
            (final_results['sddc_threshold'] == sddc_val)
        ]
        
        if row_data.empty:
            continue
            
        row_data = row_data.iloc[0]
        
        # Parse treatment data
        try:
            treatment_hillslopes = ast.literal_eval(row_data['treatment_hillslopes'])
            selected_hillslopes = ast.literal_eval(row_data['selected_hillslopes'])
        except:
            treatment_hillslopes = []
            selected_hillslopes = []
        
        # Parse untreatable data
        try:
            untreatable_str = str(row_data['untreatable_sdyd'])
            if pd.isna(untreatable_str) or untreatable_str.strip() in ['nan', '', 'None']:
                untreatable_ids = set()
            elif 'wepp_id' in untreatable_str and 'final_Sdyd' in untreatable_str:
                import re
                pattern = r'^\s*(\d+)\s+[\d\.]+.*$'
                wepp_ids = []
                for line in untreatable_str.split('\n'):
                    match = re.match(pattern, line)
                    if match:
                        wepp_ids.append(int(match.group(1)))
                untreatable_ids = set(wepp_ids)
            else:
                untreatable_ids = set()
        except:
            untreatable_ids = set()
        
        # Build treatment mapping
        treatment_map = {}
        if isinstance(treatment_hillslopes, list) and len(treatment_hillslopes) >= 3:
            for wepp_id in treatment_hillslopes[0]:
                treatment_map[wepp_id] = 0.5
            for wepp_id in treatment_hillslopes[1]:
                treatment_map[wepp_id] = 1.0
            for wepp_id in treatment_hillslopes[2]:
                treatment_map[wepp_id] = 2.0
        
        selected_set = set(selected_hillslopes) if isinstance(selected_hillslopes, list) else set()
        all_wepp_ids = set(hillslope_coords.keys())
        does_not_meet_sdyd = all_wepp_ids - selected_set
        
        # Create traces for this frame
        frame_data = []
        
        # Treatment traces (one for each level)
        for treatment_level, color in treatment_colors.items():
            x_coords = []
            y_coords = []
            hover_text = []
            
            for wepp_id, (x, y) in hillslope_coords.items():
                if treatment_map.get(wepp_id) == treatment_level:
                    x_coords.extend(x + [None])
                    y_coords.extend(y + [None])
                    hover_text.extend([f'WeppID: {wepp_id}<br>Treatment: {treatment_level} tons/acre'] * len(x) + [None])
            
            if x_coords:
                frame_data.append(go.Scatter(
                    x=x_coords,
                    y=y_coords,
                    mode='lines',
                    fill='toself',
                    fillcolor=color,
                    line=dict(color='black', width=0.5),
                    name=f'{treatment_level} tons/acre',
                    hovertext=hover_text,
                    hoverinfo='text',
                    showlegend=(frame_idx == 0)
                ))
        
        # Does not meet SDYD threshold trace
        x_coords = []
        y_coords = []
        hover_text = []
        for wepp_id in does_not_meet_sdyd:
            if wepp_id in hillslope_coords:
                x, y = hillslope_coords[wepp_id]
                x_coords.extend(x + [None])
                y_coords.extend(y + [None])
                hover_text.extend([f'WeppID: {wepp_id}<br>Does not meet SDYD threshold'] * len(x) + [None])
        
        if x_coords:
            frame_data.append(go.Scatter(
                x=x_coords,
                y=y_coords,
                mode='lines',
                fill='toself',
                fillcolor='lightgray',
                line=dict(color='red', width=1),
                name='Does not meet SDYD threshold',
                hovertext=hover_text,
                hoverinfo='text',
                showlegend=(frame_idx == 0)
            ))
        
        # Untreatable trace
        x_coords = []
        y_coords = []
        hover_text = []
        for wepp_id in untreatable_ids:
            if wepp_id in hillslope_coords:
                x, y = hillslope_coords[wepp_id]
                x_coords.extend(x + [None])
                y_coords.extend(y + [None])
                hover_text.extend([f'WeppID: {wepp_id}<br>Untreatable (exceeds SDYD limit)'] * len(x) + [None])
        
        if x_coords:
            frame_data.append(go.Scatter(
                x=x_coords,
                y=y_coords,
                mode='lines',
                fill='toself',
                fillcolor='lightgray',
                line=dict(color='red', width=2),
                name='Untreatable (exceeds SDYD limit)',
                hovertext=hover_text,
                hoverinfo='text',
                showlegend=(frame_idx == 0)
            ))
        
        # Channel trace
        if channel_coords:
            x_coords = []
            y_coords = []
            for x, y in channel_coords:
                x_coords.extend(x + [None])
                y_coords.extend(y + [None])
            
            frame_data.append(go.Scatter(
                x=x_coords,
                y=y_coords,
                mode='lines',
                line=dict(color='blue', width=2),
                name='Stream channels',
                hoverinfo='skip',
                showlegend=(frame_idx == 0)
            ))
        
        frames.append(go.Frame(
            data=frame_data,
            name=f'sdyd_{sdyd_val}_sddc_{sddc_val}',
            layout=go.Layout(
                title_text=f'Treatment Allocation Map<br>SDYD Threshold: {sdyd_val}, SDDC Threshold: {sddc_val}<br>Total Cost: ${row_data["total_cost"]:,.0f}'
            )
        ))
        
        slider_steps.append({
            'args': [[f'sdyd_{sdyd_val}_sddc_{sddc_val}'], {
                'frame': {'duration': 0, 'redraw': True},
                'mode': 'immediate',
                'transition': {'duration': 0}
            }],
            'label': f'SDYD:{sdyd_val}, SDDC:{sddc_val}',
            'method': 'animate'
        })
    
    # Create figure with initial frame
    fig = go.Figure(
        data=frames[initial_frame_idx].data if frames else [],
        frames=frames,
        layout=go.Layout(
            title=f'Treatment Allocation Map<br>SDYD Threshold: {initial_sdyd}, SDDC Threshold: {initial_sddc}',
            width=width,
            height=height,
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, title=''),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, title='', scaleanchor='x'),
            hovermode='closest',
            sliders=[{
                'active': initial_frame_idx,
                'yanchor': 'top',
                'y': -0.1,
                'xanchor': 'left',
                'currentvalue': {
                    'prefix': 'Thresholds: ',
                    'visible': True,
                    'xanchor': 'right'
                },
                'transition': {'duration': 0},
                'pad': {'b': 10, 't': 50},
                'len': 0.9,
                'x': 0.05,
                'steps': slider_steps
            }]
        )
    )
    
    print(f"✓ Created Plotly figure with {len(frames)} threshold combinations")
    return fig





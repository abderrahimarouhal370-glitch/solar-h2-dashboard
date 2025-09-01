import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ====================
# Page Config
# ====================
st.set_page_config(
    page_title="Solar-H₂ Dashboard",
    layout="wide",
    initial_sidebar_state="auto"
)

# ====================
# Constants
# ====================
SYSTEM_INFO = {
    "PV Plant": "3.9 MW",
    "Battery": "7.3 MWh",
    "Electrolyzer": "1 MW",
    "Simulation": "MATLAB/Simulink"
}

MONTHS = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]

# ====================
# Header & Month Selector (Only One!)
# ====================
st.title("🌞 Solar-to-Hydrogen MPC Dashboard – 2023")
st.markdown("Analyze monthly performance of solar-powered hydrogen production with battery storage.")

# === Single Month Selector at Top ===
col1, col2 = st.columns([3, 1])

available_months = sorted(all_months_data.keys(), key=lambda x: MONTHS.index(x))
selected_month = st.selectbox(
    "📊 Choose Month to View",
    options=available_months,
    index=0,
    key="month_selector"
)

current_data = pd.DataFrame(all_months_data[selected_month])
st.subheader(f"📊 {selected_month} 2023 Results")

with col2:
    st.markdown("### ⚙️ System")
    st.markdown(f"""
    - **PV Plant**: {SYSTEM_INFO['PV Plant']}  
    - **Battery**: {SYSTEM_INFO['Battery']}  
    - **Electrolyzer**: {SYSTEM_INFO['Electrolyzer']}  
    *Simulated in {SYSTEM_INFO['Simulation']}*
    """)

st.markdown("---")

# ====================
# Auto-Load CSV Files from Root Folder
# ====================
csv_files = [f for f in os.listdir(".") if f.lower().endswith(".csv")]

if not csv_files:
    st.warning("⚠️ No CSV files found in the project folder. Please upload your data.")
    st.stop()

all_months_data = {}

for file in csv_files:
    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip()

        # Detect month from filename
        filename = file.lower()
        detected_month = None
        for m in MONTHS:
            if m.lower() in filename:
                detected_month = m
                break
        if not detected_month:
            st.warning(f"⚠️ Could not detect month from filename: {file}")
            continue

        required_cols = [
            'Day', 'PV_Total_MWh', 'PV_to_H2_kWh', 'Batt_to_H2_kWh',
            'H2_Start_Hour', 'H2_Stop_Hour', 'H2_Produced_kg',
            'Final_SOC_pct', 'Battery_Cycles_Daily'
        ]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.warning(f"❌ Missing columns in {file}: {missing}")
            continue

        # Clean and filter data
        df = df[pd.to_numeric(df['Day'], errors='coerce').notna()]
        df['Day'] = pd.to_numeric(df['Day'])
        df = df[df['Day'] >= 1].sort_values('Day').reset_index(drop=True)

        # Compute derived columns
        df['H2_Duration'] = (df['H2_Stop_Hour'] - df['H2_Start_Hour']).clip(lower=0)
        zero_mask = (df['H2_Produced_kg'] == 0) | (df['H2_Produced_kg'].isna())
        df.loc[zero_mask, ['H2_Duration', 'H2_Start_Hour', 'H2_Stop_Hour']] = 0

        df['H2_Energy_Total_kWh'] = df['PV_to_H2_kWh'] + df['Batt_to_H2_kWh']

        all_months_data[detected_month] = df.to_dict('records')

    except Exception as e:
        st.error(f"❌ Error processing {file}: {str(e)}")

# ====================
# Handle No Data
# ====================
if not all_months_data:
    st.info("📁 No valid data loaded. Please check your CSV files.")
    st.stop()

# ====================
# Month Selector for Processed Data
# ====================
available_months = sorted(all_months_data.keys(), key=lambda x: MONTHS.index(x))
selected_month = st.selectbox(
    "📊 Choose Month to View",
    options=available_months,
    index=0,
    key="month_selector"
)

current_data = pd.DataFrame(all_months_data[selected_month])
st.subheader(f"📊 {selected_month} 2023 Results")

# ====================
# Summary Metrics
# ====================
total_h2 = current_data['H2_Produced_kg'].sum()
avg_h2 = current_data['H2_Produced_kg'].mean()
days_at_min_soc = (current_data['Final_SOC_pct'] <= 20.5).sum()
zero_h2_days = (current_data['H2_Produced_kg'] == 0).sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total H₂ Produced", f"{total_h2:.0f} kg")
col2.metric("Avg Daily H₂", f"{avg_h2:.1f} kg")
col3.metric("Zero H₂ Days", f"{zero_h2_days}")
col4.metric("Days at ≤20% SOC", f"{days_at_min_soc}")

st.markdown("")

# ====================
# Shared X-Axis Settings
# ====================
def get_xaxis():
    return dict(
        title="Day of Month",
        tickmode='linear',
        dtick=1,
        tickfont=dict(size=10),
        tickangle=0,
        showgrid=False,
        range=[current_data['Day'].min() - 0.5, current_data['Day'].max() + 0.5]
    )

# ====================
# Helper: Add Max/Min Annotations
# ====================
def add_max_min_annotations(fig, x_data, y_data, y_max_color="red", y_min_color="blue"):
    if len(y_data) == 0:
        return fig
    valid_data = y_data.dropna() if hasattr(y_data, 'dropna') else pd.Series(y_data).dropna()
    if valid_data.empty:
        return fig
    max_val = valid_data.max()
    min_val = valid_data.min()
    max_idx = valid_data.idxmax()
    min_idx = valid_data.idxmin()
    max_x = x_data.iloc[max_idx]
    min_x = x_data.iloc[min_idx]
    fig.add_annotation(
        x=max_x, y=max_val,
        text=f"Max: {max_val:.2f}",
        showarrow=True, arrowhead=2, ax=0, ay=-30,
        font=dict(size=10, color=y_max_color), arrowcolor=y_max_color
    )
    fig.add_annotation(
        x=min_x, y=min_val,
        text=f"Min: {min_val:.2f}",
        showarrow=True, arrowhead=2, ax=0, ay=30,
        font=dict(size=10, color=y_min_color), arrowcolor=y_min_color
    )
    return fig

# ====================
# Chart 1: PV and H2 Production
# ====================
st.subheader("🌤️ Daily Energy & Hydrogen Production")

col_left1, col_right1 = st.columns(2)

# Left: PV Production
with col_left1:
    max_pv = current_data['PV_Total_MWh'].max()
    yaxis_tick = round(max_pv / 5, 1) if max_pv > 0 else 1
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=current_data['Day'],
        y=current_data['PV_Total_MWh'],
        marker_color='rgb(70, 130, 180)',
        marker_line_color='darkblue',
        marker_line_width=1.5,
        text=current_data['PV_Total_MWh'].round(1),
        textposition='outside',
        hovertemplate='Day %{x}: %{y:.1f} MWh<extra></extra>'
    ))
    fig1.update_layout(
        title="Daily PV Production",
        xaxis=get_xaxis(),
        yaxis=dict(title="PV Energy (MWh)", dtick=yaxis_tick, range=[0, max_pv * 1.1], tickfont=dict(size=10)),
        showlegend=False,
        height=500,
        margin=dict(b=80, l=50, r=30, t=80),
        title_font_size=16
    )
    fig1 = add_max_min_annotations(fig1, current_data['Day'], current_data['PV_Total_MWh'], y_max_color="red", y_min_color="blue")
    st.plotly_chart(fig1, use_container_width=True)

# Right: H2 Production
with col_right1:
    max_h2 = current_data['H2_Produced_kg'].max()
    yaxis_tick = round(max_h2 / 5, 1) if max_h2 > 0 else 1
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=current_data['Day'],
        y=current_data['H2_Produced_kg'],
        marker_color='rgb(46, 139, 87)',
        marker_line_color='darkgreen',
        marker_line_width=1.5,
        text=current_data['H2_Produced_kg'].round(1),
        textposition='outside',
        hovertemplate='Day %{x}: %{y:.1f} kg<extra></extra>'
    ))
    fig2.update_layout(
        title="Daily H₂ Production",
        xaxis=get_xaxis(),
        yaxis=dict(title="H₂ Produced (kg)", dtick=yaxis_tick, range=[0, max_h2 * 1.1], tickfont=dict(size=10)),
        showlegend=False,
        height=500,
        margin=dict(b=80, l=50, r=30, t=80),
        title_font_size=16
    )
    fig2 = add_max_min_annotations(fig2, current_data['Day'], current_data['H2_Produced_kg'], y_max_color="darkgreen", y_min_color="gray")
    st.plotly_chart(fig2, use_container_width=True)

# ====================
# Chart 2: Energy Contribution to Electrolyzer
# ====================
st.subheader("⚡ Energy Contribution to Electrolyzer")

col_left2, col_right2 = st.columns(2)

# Left: Battery → H2
with col_left2:
    max_batt = current_data['Batt_to_H2_kWh'].max()
    yaxis_tick = round(max_batt / 5, 0) if max_batt > 0 else 1
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=current_data['Day'],
        y=current_data['Batt_to_H2_kWh'],
        marker_color='#FFD580',
        marker_line_color='#CC8E35',
        marker_line_width=1.5,
        text=current_data['Batt_to_H2_kWh'].round(1),
        textposition='outside',
        hovertemplate='Day %{x}: %{y:.1f} kWh<extra></extra>'
    ))
    fig3.update_layout(
        title="Battery → Electrolyzer",
        xaxis=get_xaxis(),
        yaxis=dict(title="Energy (kWh)", dtick=yaxis_tick, range=[0, max_batt * 1.1], tickfont=dict(size=10)),
        showlegend=False,
        height=500,
        margin=dict(b=80, l=50, r=30, t=80),
        title_font_size=16
    )
    fig3 = add_max_min_annotations(fig3, current_data['Day'], current_data['Batt_to_H2_kWh'], y_max_color="orange", y_min_color="purple")
    st.plotly_chart(fig3, use_container_width=True)

# Right: PV → H2
with col_right2:
    max_pv_h2 = current_data['PV_to_H2_kWh'].max()
    yaxis_tick = round(max_pv_h2 / 5, 0) if max_pv_h2 > 0 else 1
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        x=current_data['Day'],
        y=current_data['PV_to_H2_kWh'],
        marker_color='#FFF9C4',
        marker_line_color='#F4B400',
        marker_line_width=1.5,
        text=current_data['PV_to_H2_kWh'].round(1),
        textposition='outside',
        hovertemplate='Day %{x}: %{y:.1f} kWh<extra></extra>'
    ))
    fig4.update_layout(
        title="PV → Electrolyzer",
        xaxis=get_xaxis(),
        yaxis=dict(title="Energy (kWh)", dtick=yaxis_tick, range=[0, max_pv_h2 * 1.1], tickfont=dict(size=10)),
        showlegend=False,
        height=500,
        margin=dict(b=80, l=50, r=30, t=80),
        title_font_size=16
    )
    fig4 = add_max_min_annotations(fig4, current_data['Day'], current_data['PV_to_H2_kWh'], y_max_color="goldenrod", y_min_color="gray")
    st.plotly_chart(fig4, use_container_width=True)

# ====================
# Chart 3: Total Electrolyzer Energy
# ====================
st.subheader("⚡ Electrolyzer Total Energy Absorption")

max_total_energy = current_data['H2_Energy_Total_kWh'].max()
yaxis_tick_energy = max(1, round(max_total_energy / 5))
fig_energy = go.Figure()
fig_energy.add_trace(go.Bar(
    x=current_data['Day'],
    y=current_data['H2_Energy_Total_kWh'],
    marker_color='rgb(255, 165, 0)',
    marker_line_color='darkred',
    marker_line_width=1.5,
    text=current_data['H2_Energy_Total_kWh'].round(1),
    textposition='outside',
    hovertemplate='Day %{x}: %{y:.1f} kWh<extra></extra>'
))
fig_energy.update_layout(
    title="Total Energy Used by Electrolyzer (PV + Battery)",
    xaxis=get_xaxis(),
    yaxis=dict(title="Total Energy (kWh)", dtick=yaxis_tick_energy, range=[0, max_total_energy * 1.1], tickfont=dict(size=10)),
    showlegend=False,
    height=500,
    margin=dict(b=80, l=50, r=30, t=80),
    title_font_size=16
)
fig_energy = add_max_min_annotations(fig_energy, current_data['Day'], current_data['H2_Energy_Total_kWh'], y_max_color="red", y_min_color="blue")
st.plotly_chart(fig_energy, use_container_width=True)

# ====================
# Chart 4: H2 Duration & Timeline
# ====================
st.subheader("⏱️ Electrolyzer Operation Schedule")

col_left3, col_right3 = st.columns(2)

# Left: H2 Duration
with col_left3:
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        x=current_data['Day'],
        y=current_data['H2_Duration'],
        marker_color='rgb(255, 140, 0)',
        marker_line_color='darkred',
        marker_line_width=1.5,
        text=current_data['H2_Duration'].round(1),
        textposition='outside',
        hovertemplate='Day %{x}: %{y:.1f} h<extra></extra>'
    ))
    fig5.update_layout(
        title="H₂ On Duration (Hours)",
        xaxis=get_xaxis(),
        yaxis=dict(title="Hours Running", range=[0, 24], dtick=6, tickfont=dict(size=10)),
        showlegend=False,
        height=500,
        margin=dict(b=80, l=50, r=30, t=80),
        title_font_size=16
    )
    fig5 = add_max_min_annotations(fig5, current_data['Day'], current_data['H2_Duration'], y_max_color="red", y_min_color="green")
    st.plotly_chart(fig5, use_container_width=True)

# Right: Start & Stop Timeline
with col_right3:
    fig6 = go.Figure()
    hover_text = [
        f"Start: {row['H2_Start_Hour']:.1f} h, Stop: {row['H2_Stop_Hour']:.1f} h" if pd.notna(row['H2_Start_Hour']) else "No H₂"
        for _, row in current_data.iterrows()
    ]
    fig6.add_trace(go.Bar(
        x=current_data['Day'],
        y=current_data['H2_Duration'],
        base=current_data['H2_Start_Hour'],
        marker_color='rgb(255, 140, 0)',
        marker_line_color='darkred',
        marker_line_width=1.5,
        width=0.8,
        hovertemplate=hover_text,
        name="H₂ Operation"
    ))
    fig6.update_layout(
        title="Daily H₂ Start & Stop Times",
        xaxis=get_xaxis(),
        yaxis=dict(title="Time of Day (Hours)", range=[0, 24], dtick=6, tickfont=dict(size=10)),
        barmode='overlay',
        showlegend=False,
        height=500,
        margin=dict(b=80, l=50, r=30, t=80),
        title_font_size=16
    )
    for _, row in current_data.iterrows():
        day = row['Day']
        start = row['H2_Start_Hour']
        stop = row['H2_Stop_Hour']
        if pd.notna(start) and 1 <= start <= 23:
            fig6.add_annotation(x=day, y=start - 1, text=f"{start:.1f}", showarrow=False, font=dict(size=9, color="blue"), xanchor="center")
        if pd.notna(stop) and 1 <= stop <= 23:
            fig6.add_annotation(x=day, y=stop + 1, text=f"{stop:.1f}", showarrow=False, font=dict(size=9, color="red"), xanchor="center")
    fig6 = add_max_min_annotations(fig6, current_data['Day'], current_data['H2_Duration'], y_max_color="red", y_min_color="green")
    st.plotly_chart(fig6, use_container_width=True)

# ====================
# Chart 5: Battery SOC & Cycles
# ====================
st.subheader("🔋 Battery Health & Usage")

col_left4, col_right4 = st.columns(2)

# Left: Final SOC (with value labels on each point)
with col_left4:
    fig7 = go.Figure()
    fig7.add_trace(go.Scatter(
        x=current_data['Day'],
        y=current_data['Final_SOC_pct'],
        mode='lines+markers+text',  # ✅ Show values on points
        text=current_data['Final_SOC_pct'].round(0).astype(str) + "%",
        textposition="top center",
        textfont=dict(size=9),
        marker=dict(color='purple', size=8, line=dict(color='darkred', width=2)),
        line=dict(color='purple', width=3),
        hovertemplate='Day %{x}: %{y:.1f}%<extra></extra>'
    ))
    fig7.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Min (20%)", annotation_position="bottom right")
    fig7.add_hline(y=95, line_dash="dash", line_color="green", annotation_text="Max (95%)", annotation_position="top right")
    fig7.update_layout(
        title="Battery End-of-Day SOC",
        xaxis=get_xaxis(),
        yaxis=dict(title="SOC (%)", range=[0, 100], dtick=20, tickfont=dict(size=10)),
        height=500,
        margin=dict(b=80, l=50, r=30, t=80),
        title_font_size=16
    )
    fig7 = add_max_min_annotations(fig7, current_data['Day'], current_data['Final_SOC_pct'], y_max_color="green", y_min_color="red")
    st.plotly_chart(fig7, use_container_width=True)

# Right: Battery Cycles
with col_right4:
    max_cycles = current_data['Battery_Cycles_Daily'].max()
    yaxis_tick = max(0.5, round(max_cycles / 5, 1))
    fig8 = go.Figure()
    fig8.add_trace(go.Bar(
        x=current_data['Day'],
        y=current_data['Battery_Cycles_Daily'],
        marker_color='rgb(128, 128, 128)',
        marker_line_color='black',
        marker_line_width=1.5,
        text=current_data['Battery_Cycles_Daily'].round(1),
        textposition='outside',
        hovertemplate='Day %{x}: %{y:.1f} cycles<extra></extra>'
    ))
    fig8.update_layout(
        title="Daily Battery Cycles",
        xaxis=get_xaxis(),
        yaxis=dict(title="Charge/Discharge Events", dtick=yaxis_tick, range=[0, max_cycles * 1.1], tickfont=dict(size=10)),
        showlegend=False,
        height=500,
        margin=dict(b=80, l=50, r=30, t=80),
        title_font_size=16
    )
    fig8 = add_max_min_annotations(fig8, current_data['Day'], current_data['Battery_Cycles_Daily'], y_max_color="red", y_min_color="green")
    st.plotly_chart(fig8, use_container_width=True)

# ====================
# Raw Data Table
# ====================
st.markdown("### 📊 Raw Data")
df_display = pd.DataFrame(all_months_data[selected_month])
df_display['H2_Energy_Total_kWh'] = df_display['H2_Energy_Total_kWh'].round(1)

st.dataframe(df_display.round(1), height=300)

st.download_button(
    label=f"⬇️ Download {selected_month} Data as CSV",
    data=df_display.to_csv(index=False),
    file_name=f"solar_h2_{selected_month.lower()}_2023_detailed.csv",
    mime="text/csv"
)

# ====================
# Footer
# ====================
st.markdown("---")
st.markdown("🔋 *Dashboard by: Abderrahim AROUHAL | System: Solar + Battery + H₂ | Simulation: MATLAB MPC + Simulink*")







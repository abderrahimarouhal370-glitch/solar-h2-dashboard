import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# ====================
# Page Title
# ====================
st.title("🌞 Solar-to-Hydrogen MPC Dashboard – 2023")
st.markdown("Select a month to view daily energy, H₂ production, and battery performance.")

# ====================
# Sidebar: Month Selection + System Info
# ====================
st.sidebar.header("📅 Select Month")
months = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]
selected_month = st.sidebar.selectbox("Choose a month:", options=months, index=0)

# System Info
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ System Configuration")
st.sidebar.markdown("""
- **PV Plant**: 3.9 MW  
- **Battery**: 7.3 MWh  
- **Electrolyzer**: 1 MW  
""")
st.sidebar.markdown("Simulated with MATLAB MPC + Simulink")

# Map month to filename
filename = f"solar_h2_{selected_month.lower()}_2023_detailed.csv"

# Display current month
st.subheader(f"📊 {selected_month} 2023 Results")

# ====================
# Load the Data
# ====================
if not os.path.exists(filename):
    st.error(f"❌ Data file not found: `{filename}`\n\nPlease export this month's results from MATLAB using:\n```matlab\nwritetable(results_table, 'solar_h2_{selected_month.lower()}_2023_detailed.csv');\n```")
    st.stop()

try:
    df = pd.read_csv(filename)
    df.columns = df.columns.str.strip()

    # Required columns (updated to include cycles and actual/planned hours)
    required_cols = ['Day', 'PV_Total_MWh', 'PV_to_H2_kWh', 'Batt_to_H2_kWh',
                     'H2_Start_Hour', 'H2_Stop_Hour', 'H2_Produced_kg', 'Final_SOC_pct',
                     'Battery_Cycles_Daily', 'Battery_Cycles_Cumulative']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"❌ Missing required column: '{col}' in {filename}")
            st.stop()

    # Clean and sort
    df = df[pd.to_numeric(df['Day'], errors='coerce').notna()]
    df['Day'] = pd.to_numeric(df['Day'])
    df = df[df['Day'] >= 1]
    df = df.sort_values('Day').reset_index(drop=True)

    # Compute H2 duration
    df['H2_Duration'] = df['H2_Stop_Hour'] - df['H2_Start_Hour']
    df['H2_Duration'] = df['H2_Duration'].clip(lower=0)

    # Zero H2 → set duration and times to NaN
    zero_h2_mask = (df['H2_Produced_kg'] == 0) | (df['H2_Produced_kg'].isna())
    df.loc[zero_h2_mask, 'H2_Duration'] = 0
    df.loc[zero_h2_mask, 'H2_Start_Hour'] = None
    df.loc[zero_h2_mask, 'H2_Stop_Hour'] = None

except Exception as e:
    st.error(f"❌ Error loading {filename}: {e}")
    st.stop()

# ====================
# Summary Metrics
# ====================
total_h2 = df['H2_Produced_kg'].sum()
avg_h2 = df['H2_Produced_kg'].mean()
days_at_min_soc = (df['Final_SOC_pct'] <= 20.5).sum()
zero_h2_days = (df['H2_Produced_kg'] == 0).sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total H₂ Produced", f"{total_h2:.0f} kg")
col2.metric("Avg Daily H₂", f"{avg_h2:.1f} kg")
col3.metric("Zero H₂ Days", f"{zero_h2_days}")
col4.metric("Days at 20% SOC", f"{days_at_min_soc}")

# ====================
# Row 1: PV and H2 Production
# ====================
st.subheader("🌤️ Daily Energy Generation & Hydrogen Production")

col_left1, col_right1 = st.columns(2)

# Left: PV Production
with col_left1:
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=df['Day'],
        y=df['PV_Total_MWh'],
        marker_color='rgb(70, 130, 180)',
        marker_line_color='darkblue',
        marker_line_width=2,
        hovertemplate='Day %{x}: %{y:.1f} MWh<extra></extra>'
    ))
    fig1.update_layout(
        title="Daily PV Production",
        xaxis_title="Day of Month",
        yaxis_title="PV Energy (MWh)",
        xaxis=dict(tickmode='linear', dtick=1),
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig1, use_container_width=True)

# Right: H2 Production
with col_right1:
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df['Day'],
        y=df['H2_Produced_kg'],
        marker_color='rgb(46, 139, 87)',
        marker_line_color='darkgreen',
        marker_line_width=2,
        hovertemplate='Day %{x}: %{y:.1f} kg<extra></extra>'
    ))
    fig2.update_layout(
        title="Daily H₂ Production",
        xaxis_title="Day of Month",
        yaxis_title="H₂ Produced (kg)",
        xaxis=dict(tickmode='linear', dtick=1),
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig2, use_container_width=True)

# ====================
# Row 2: PV → H2 and Batt → H2
# ====================
st.subheader("⚡ Energy Contribution to Electrolyzer")

col_left2, col_right2 = st.columns(2)

# Left: Battery → H2
with col_left2:
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=df['Day'],
        y=df['Batt_to_H2_kWh'],
        marker_color='#FFD580',
        marker_line_color='#CC8E35',
        marker_line_width=2,
        hovertemplate='Day %{x}: %{y:.1f} kWh<extra></extra>'
    ))
    fig3.update_layout(
        title="Battery → Electrolyzer",
        xaxis_title="Day of Month",
        yaxis_title="Energy (kWh)",
        xaxis=dict(tickmode='linear', dtick=1),
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig3, use_container_width=True)

# Right: PV → H2
with col_right2:
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        x=df['Day'],
        y=df['PV_to_H2_kWh'],
        marker_color='#FFF9C4',
        marker_line_color='#F4B400',
        marker_line_width=2,
        hovertemplate='Day %{x}: %{y:.1f} kWh<extra></extra>'
    ))
    fig4.update_layout(
        title="PV → Electrolyzer",
        xaxis_title="Day of Month",
        yaxis_title="Energy (kWh)",
        xaxis=dict(tickmode='linear', dtick=1),
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig4, use_container_width=True)

# ====================
# Row 3: H2 On Duration + Start/Stop Timeline
# ====================
st.subheader("⏱️ Electrolyzer Operation Schedule")

col_left3, col_right3 = st.columns(2)

# Left: H2 On Duration
with col_left3:
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        x=df['Day'],
        y=df['H2_Duration'],
        marker_color='rgb(255, 140, 0)',
        marker_line_color='darkred',
        marker_line_width=2,
        hovertemplate='Day %{x}: %{y:.1f} h<extra></extra>'
    ))
    fig5.update_layout(
        title="H₂ On Duration (Hours)",
        xaxis_title="Day of Month",
        yaxis_title="Hours Running",
        yaxis=dict(range=[0, 24]),
        xaxis=dict(tickmode='linear', dtick=1),
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig5, use_container_width=True)

# Right: Start & Stop Timeline
with col_right3:
    fig6 = go.Figure()

    fig6.add_trace(go.Bar(
        x=df['Day'],
        y=df['H2_Start_Hour'],
        marker_color='white',
        width=0.8,
        showlegend=False,
        hoverinfo='skip'
    ))

    hover_text = []
    for _, row in df.iterrows():
        if pd.notna(row['H2_Start_Hour']) and pd.notna(row['H2_Stop_Hour']):
            hover_text.append(f"Start: {row['H2_Start_Hour']:.1f} h, Stop: {row['H2_Stop_Hour']:.1f} h")
        else:
            hover_text.append("No H₂ production")

    fig6.add_trace(go.Bar(
        x=df['Day'],
        y=df['H2_Duration'],
        base=df['H2_Start_Hour'],
        marker_color='rgb(255, 140, 0)',
        marker_line_color='darkred',
        marker_line_width=2,
        width=0.8,
        hovertemplate=hover_text,
        hoverinfo="text",
        name="H₂ Operation"
    ))

    fig6.update_layout(
        title="Daily H₂ Start & Stop Times",
        xaxis_title="Day of Month",
        yaxis_title="Time of Day (Hours)",
        barmode='relative',
        showlegend=False,
        height=400,
        yaxis=dict(range=[0, 24], dtick=4),
        xaxis=dict(tickmode='linear', dtick=1)
    )

    for _, row in df.iterrows():
        day = row['Day']
        start = row['H2_Start_Hour']
        stop = row['H2_Stop_Hour']
        if pd.notna(start) and pd.notna(stop):
            if start <= 23:
                fig6.add_annotation(x=day, y=start - 0.8, text=f"{start:.1f}h", showarrow=False,
                                    font=dict(size=9, color="blue"), xanchor="center")
            if stop >= 1:
                fig6.add_annotation(x=day, y=stop + 0.8, text=f"{stop:.1f}h", showarrow=False,
                                    font=dict(size=9, color="red"), xanchor="center")

    st.plotly_chart(fig6, use_container_width=True)

# ====================
# Row 4: Final SOC and Battery Cycles
# ====================
st.subheader("🔋 Battery Health & Usage")

col_left4, col_right4 = st.columns(2)

# Left: Final SOC
with col_left4:
    fig7 = go.Figure()
    fig7.add_trace(go.Scatter(
        x=df['Day'],
        y=df['Final_SOC_pct'],
        mode='lines+markers',
        marker=dict(color='purple', size=8, line=dict(color='darkred', width=2)),
        line=dict(color='purple', width=3),
        hovertemplate='Day %{x}: %{y:.1f}%<extra></extra>'
    ))
    fig7.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Min (20%)")
    fig7.add_hline(y=95, line_dash="dash", line_color="green", annotation_text="Max (95%)")
    fig7.update_layout(
        title="Battery End-of-Day SOC",
        xaxis_title="Day of Month",
        yaxis_title="SOC (%)",
        xaxis=dict(tickmode='linear', dtick=1),
        height=400,
        yaxis=dict(range=[0, 100])
    )
    st.plotly_chart(fig7, use_container_width=True)

# Right: Battery Cycles
with col_right4:
    fig8 = go.Figure()
    fig8.add_trace(go.Bar(
        x=df['Day'],
        y=df['Battery_Cycles_Daily'],
        marker_color='rgb(128, 128, 128)',
        marker_line_color='black',
        marker_line_width=1.5,
        hovertemplate='Day %{x}: %{y:.1f} cycles<extra></extra>'
    ))
    fig8.update_layout(
        title="Daily Battery Cycles",
        xaxis_title="Day of Month",
        yaxis_title="Charge/Discharge Events",
        xaxis=dict(tickmode='linear', dtick=1),
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig8, use_container_width=True)

# ====================
# Show Data Table
# ====================
st.subheader("📊 Raw Data")
st.dataframe(df.style.format({
    'PV_Total_MWh': '{:.2f}',
    'PV_to_H2_kWh': '{:.1f}',
    'Batt_to_H2_kWh': '{:.1f}',
    'H2_Start_Hour': lambda x: f'{x:.1f}' if pd.notna(x) else '',
    'H2_Stop_Hour': lambda x: f'{x:.1f}' if pd.notna(x) else '',
    'H2_Produced_kg': '{:.1f}',
    'Final_SOC_pct': '{:.1f}',
    'Battery_Cycles_Daily': '{:.1f}',
    'Battery_Cycles_Cumulative': '{:.1f}'
}))

# ====================
# Download Button
# ====================
st.download_button(
    label=f"⬇️ Download {selected_month} Data",
    data=df.to_csv(index=False),
    file_name=f"solar_h2_{selected_month.lower()}_2023_detailed.csv",
    mime="text/csv"
)

# ====================
# Footer
# ====================
st.markdown("---")
st.markdown("🔋 *Dashboard by: Your Name | System: Solar + Battery + H₂ | Simulation: MATLAB MPC + Simulink*")





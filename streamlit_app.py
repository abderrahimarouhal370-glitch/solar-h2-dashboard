import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import os
from datetime import datetime
import tempfile
from weasyprint import HTML

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

    required_cols = ['Day', 'PV_Total_MWh', 'PV_to_H2_kWh', 'Batt_to_H2_kWh',
                     'H2_Start_Hour', 'H2_Stop_Hour', 'H2_Produced_kg', 'Final_SOC_pct',
                     'Battery_Cycles_Daily', 'Battery_Cycles_Cumulative']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"❌ Missing required column: '{col}' in {filename}")
            st.stop()

    df = df[pd.to_numeric(df['Day'], errors='coerce').notna()]
    df['Day'] = pd.to_numeric(df['Day'])
    df = df[df['Day'] >= 1]
    df = df.sort_values('Day').reset_index(drop=True)

    df['H2_Duration'] = df['H2_Stop_Hour'] - df['H2_Start_Hour']
    df['H2_Duration'] = df['H2_Duration'].clip(lower=0)

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
# All Charts (We'll reuse these for PDF)
# ====================
# --- Chart 1: PV Production ---
fig1 = go.Figure()
fig1.add_trace(go.Bar(x=df['Day'], y=df['PV_Total_MWh'], marker_color='rgb(70, 130, 180)', marker_line_color='darkblue', marker_line_width=2))
fig1.update_layout(title="Daily PV Production", xaxis_title="Day", yaxis_title="PV (MWh)", height=300)

# --- Chart 2: H2 Production ---
fig2 = go.Figure()
fig2.add_trace(go.Bar(x=df['Day'], y=df['H2_Produced_kg'], marker_color='rgb(46, 139, 87)', marker_line_color='darkgreen', marker_line_width=2))
fig2.update_layout(title="Daily H₂ Production", xaxis_title="Day", yaxis_title="H₂ (kg)", height=300)

# --- Chart 3: Batt → H2 ---
fig3 = go.Figure()
fig3.add_trace(go.Bar(x=df['Day'], y=df['Batt_to_H2_kWh'], marker_color='#FFD580', marker_line_color='#CC8E35', marker_line_width=2))
fig3.update_layout(title="Battery → Electrolyzer", xaxis_title="Day", yaxis_title="Energy (kWh)", height=300)

# --- Chart 4: PV → H2 ---
fig4 = go.Figure()
fig4.add_trace(go.Bar(x=df['Day'], y=df['PV_to_H2_kWh'], marker_color='#FFF9C4', marker_line_color='#F4B400', marker_line_width=2))
fig4.update_layout(title="PV → Electrolyzer", xaxis_title="Day", yaxis_title="Energy (kWh)", height=300)

# --- Chart 5: H2 Duration ---
fig5 = go.Figure()
fig5.add_trace(go.Bar(x=df['Day'], y=df['H2_Duration'], marker_color='rgb(255, 140, 0)', marker_line_color='darkred', marker_line_width=2))
fig5.update_layout(title="H₂ On Duration (Hours)", xaxis_title="Day", yaxis_title="Hours", height=300)

# --- Chart 6: Start/Stop Timeline ---
fig6 = go.Figure()
fig6.add_trace(go.Bar(x=df['Day'], y=df['H2_Start_Hour'], marker_color='white', showlegend=False, hoverinfo='skip'))
fig6.add_trace(go.Bar(x=df['Day'], y=df['H2_Duration'], base=df['H2_Start_Hour'], marker_color='rgb(255, 140, 0)', marker_line_color='darkred', width=0.8))
fig6.update_layout(title="Daily H₂ Start & Stop Times", xaxis_title="Day", yaxis_title="Time (h)", barmode='relative', height=300)

# --- Chart 7: Final SOC ---
fig7 = go.Figure()
fig7.add_trace(go.Scatter(x=df['Day'], y=df['Final_SOC_pct'], mode='lines+markers', line=dict(color='purple'), marker=dict(size=6))))
fig7.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Min (20%)")
fig7.add_hline(y=95, line_dash="dash", line_color="green", annotation_text="Max (95%)")
fig7.update_layout(title="Final Battery SOC", xaxis_title="Day", yaxis_title="SOC (%)", height=300)

# --- Chart 8: Battery Cycles ---
fig8 = go.Figure()
fig8.add_trace(go.Bar(x=df['Day'], y=df['Battery_Cycles_Daily'], marker_color='gray', marker_line_color='black')))
fig8.update_layout(title="Daily Battery Cycles", xaxis_title="Day", yaxis_title="Cycles", height=300)

# Display charts in app
st.subheader("🌤️ Daily Energy Generation & Hydrogen Production")
c1, c2 = st.columns(2)
c1.plotly_chart(fig1, use_container_width=True)
c2.plotly_chart(fig2, use_container_width=True)

st.subheader("⚡ Energy Contribution to Electrolyzer")
c3, c4 = st.columns(2)
c3.plotly_chart(fig3, use_container_width=True)
c4.plotly_chart(fig4, use_container_width=True)

st.subheader("⏱️ Electrolyzer Operation Schedule")
c5, c6 = st.columns(2)
c5.plotly_chart(fig5, use_container_width=True)
c6.plotly_chart(fig6, use_container_width=True)

st.subheader("🔋 Battery Health & Usage")
c7, c8 = st.columns(2)
c7.plotly_chart(fig7, use_container_width=True)
c8.plotly_chart(fig8, use_container_width=True)

# Raw Data
st.subheader("📊 Raw Data")
st.dataframe(df.style.format({
    'PV_Total_MWh': '{:.2f}', 'PV_to_H2_kWh': '{:.1f}', 'Batt_to_H2_kWh': '{:.1f}',
    'H2_Start_Hour': lambda x: f'{x:.1f}' if pd.notna(x) else '',
    'H2_Stop_Hour': lambda x: f'{x:.1f}' if pd.notna(x) else '',
    'H2_Produced_kg': '{:.1f}', 'Final_SOC_pct': '{:.1f}',
    'Battery_Cycles_Daily': '{:.1f}', 'Battery_Cycles_Cumulative': '{:.1f}'
}))

# ====================
# PDF Export Button
# ====================
if st.button("🖨️ Export Report as PDF"):
    with st.spinner("Generating PDF..."):

        # Save plots as images
        with tempfile.TemporaryDirectory() as tmpdir:
            img_paths = {}
            for i, fig in enumerate([fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8]):
                path = f"{tmpdir}/fig{i+1}.png"
                pio.write_image(fig, path, width=800, height=400)
                img_paths[f"fig{i+1}"] = path

            # Create HTML content
            html_content = f"""
            <h1>Solar-to-Hydrogen Report – {selected_month} 2023</h1>
            <p><strong>Generated on:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <h2>System Configuration</h2>
            <ul>
                <li><strong>PV Plant:</strong> 3.9 MW</li>
                <li><strong>Battery:</strong> 7.3 MWh</li>
                <li><strong>Electrolyzer:</strong> 1 MW</li>
            </ul>
            <h2>Summary Metrics</h2>
            <p>Total H₂ Produced: {total_h2:.0f} kg</p>
            <p>Avg Daily H₂: {avg_h2:.1f} kg</p>
            <p>Zero H₂ Days: {zero_h2_days}</p>
            <p>Days at 20% SOC: {days_at_min_soc}</p>
            <h2>Charts</h2>
            <img src="{img_paths['fig1']}" width="700"><br><br>
            <img src="{img_paths['fig2']}" width="700"><br><br>
            <img src="{img_paths['fig3']}" width="700"><br><br>
            <img src="{img_paths['fig4']}" width="700"><br><br>
            <img src="{img_paths['fig5']}" width="700"><br><br>
            <img src="{img_paths['fig6']}" width="700"><br><br>
            <img src="{img_paths['fig7']}" width="700"><br><br>
            <img src="{img_paths['fig8']}" width="700"><br><br>
            <h2>Raw Data</h2>
            {df.to_html(index=False)}
            <footer><br><br><em>Report generated with Streamlit + Python</em></footer>
            """

            # Generate PDF
            html = HTML(string=html_content)
            pdf = html.write_pdf()

            # Offer download
            st.download_button(
                label="✅ Click to Download PDF Report",
                data=pdf,
                file_name=f"solar_h2_{selected_month.lower()}_2023_report.pdf",
                mime="application/pdf"
            )

# ====================
# Download CSV Button
# ====================
st.download_button(
    label=f"⬇️ Download {selected_month} Data (CSV)",
    data=df.to_csv(index=False),
    file_name=f"solar_h2_{selected_month.lower()}_2023_detailed.csv",
    mime="text/csv"
)

# ====================
# Footer
# ====================
st.markdown("---")
st.markdown("🔋 *Dashboard by: Your Name | System: Solar + Battery + H₂ | Simulation: MATLAB MPC + Simulink*")

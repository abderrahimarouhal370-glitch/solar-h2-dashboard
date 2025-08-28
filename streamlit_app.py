import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import os
from datetime import datetime
from fpdf2 import FPDF
from matplotlib import pyplot as plt
import tempfile

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
# Generate Charts for Display and PDF
# ====================
def create_matplotlib_chart(x, y, title, ylabel, color="blue", kind="bar"):
    fig, ax = plt.subplots(figsize=(8, 4))
    if kind == "bar":
        ax.bar(x, y, color=color)
    elif kind == "line":
        ax.plot(x, y, color=color, marker='o')
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Day of Month")
    ax.grid(True, alpha=0.3)
    return fig

# --- Chart 1: PV Production ---
fig1 = create_matplotlib_chart(df['Day'], df['PV_Total_MWh'], "Daily PV Production", "PV Energy (MWh)", "skyblue")

# --- Chart 2: H2 Production ---
fig2 = create_matplotlib_chart(df['Day'], df['H2_Produced_kg'], "Daily H₂ Production", "H₂ Produced (kg)", "green")

# --- Chart 3: Batt → H2 ---
fig3 = create_matplotlib_chart(df['Day'], df['Batt_to_H2_kWh'], "Battery → Electrolyzer", "Energy (kWh)", "orange")

# --- Chart 4: PV → H2 ---
fig4 = create_matplotlib_chart(df['Day'], df['PV_to_H2_kWh'], "PV → Electrolyzer", "Energy (kWh)", "gold")

# --- Chart 5: H2 Duration ---
fig5 = create_matplotlib_chart(df['Day'], df['H2_Duration'], "H₂ On Duration (Hours)", "Hours Running", "darkorange")

# --- Chart 6: Final SOC ---
fig6 = create_matplotlib_chart(df['Day'], df['Final_SOC_pct'], "Final Battery SOC", "SOC (%)", "purple", kind="line")

# --- Chart 7: Battery Cycles ---
fig7 = create_matplotlib_chart(df['Day'], df['Battery_Cycles_Daily'], "Daily Battery Cycles", "Cycles", "gray")

# Display in app
st.subheader("🌤️ Daily Energy Generation & Hydrogen Production")
c1, c2 = st.columns(2)
c1.pyplot(fig1)
c2.pyplot(fig2)

st.subheader("⚡ Energy Contribution to Electrolyzer")
c3, c4 = st.columns(2)
c3.pyplot(fig3)
c4.pyplot(fig4)

st.subheader("⏱️ Electrolyzer Operation Schedule")
c5, c6 = st.columns(2)
c5.pyplot(fig5)
c6.pyplot(fig6)

st.subheader("🔋 Battery Health & Usage")
c7 = st.columns(1)[0]
c7.pyplot(fig7)

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
    with st.spinner("Generating PDF report..."):

        with tempfile.TemporaryDirectory() as tmpdir:
            image_paths = []

            # Save all figures as PNG
            for i, fig in enumerate([fig1, fig2, fig3, fig4, fig5, fig6, fig7]):
                path = f"{tmpdir}/chart_{i+1}.png"
                fig.savefig(path, bbox_inches='tight', dpi=150)
                plt.close(fig)
                image_paths.append(path)

            # Create PDF
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"Solar-to-Hydrogen Report – {selected_month} 2023", ln=True, align="C")

            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
            pdf.ln(5)

            # System Info
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "System Configuration", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, "• PV Plant: 3.9 MW", ln=True)
            pdf.cell(0, 6, "• Battery: 7.3 MWh", ln=True)
            pdf.cell(0, 6, "• Electrolyzer: 1 MW", ln=True)
            pdf.ln(5)

            # Summary Metrics
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Summary Metrics", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"• Total H₂ Produced: {total_h2:.0f} kg", ln=True)
            pdf.cell(0, 6, f"• Avg Daily H₂: {avg_h2:.1f} kg", ln=True)
            pdf.cell(0, 6, f"• Zero H₂ Days: {zero_h2_days}", ln=True)
            pdf.cell(0, 6, f"• Days at 20% SOC: {days_at_min_soc}", ln=True)
            pdf.ln(10)

            # Charts
            for i, img_path in enumerate(image_paths):
                pdf.image(img_path, x=10, w=190)
                pdf.ln(5)

            # Raw Data Table
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Raw Data", ln=True)
            pdf.set_font("Arial", "B", 6)
            for col in df.columns:
                pdf.cell(14, 6, str(col), border=1)
            pdf.ln(6)
            pdf.set_font("Arial", "", 6)
            for _, row in df.iterrows():
                for col in df.columns:
                    val = row[col]
                    if pd.isna(val):
                        val = ""
                    else:
                        val = str(round(val, 1)) if isinstance(val, (float, int)) else str(val)
                    pdf.cell(14, 6, val[:10], border=1)  # Truncate long values
                pdf.ln(6)

            pdf.ln(10)
            pdf.set_font("Arial", "I", 8)
            pdf.cell(0, 10, "Report generated with Streamlit + fpdf2", ln=True)

            # Output PDF
            pdf_data = pdf.output(dest="S").encode("latin1")

            st.download_button(
                label="✅ Click to Download PDF Report",
                data=pdf_data,
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




from pathlib import Path
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Suppository Calculator — Chat", layout="centered")

APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "logo.png"

if LOGO_PATH.exists():
    st.image(Image.open(LOGO_PATH), width=150)
else:
    st.warning(f"Logo not found at: {LOGO_PATH}")

st.markdown("""
<style>
/* shrink spacing under images and above/below h1 */
div.stImage { margin-bottom: 0.15rem; }
h1 { margin-top: 0.15rem; margin-bottom: 0.15rem; line-height: 1.05; }
</style>
""", unsafe_allow_html=True)

st.image(Image.open(LOGO_PATH), width=200)
st.markdown("<h1>💬 Suppository Base Calculator (GPT-style)</h1>", unsafe_allow_html=True)
st.caption("Chat with the tutor to compute the required base using the 5-step density-ratio method.")

with st.expander("Method (5 steps)", expanded=False):
    st.markdown("""
1) **Total API amount**: sum of all active ingredients for all suppositories.  
2) **Estimate blank base weight**: average blank weight × number of suppositories.  
3) **Density ratio**: ρ(API) / ρ(base).  
4) **Base displaced by APIs**: Total API weight ÷ ratio from step 3.  
5) **Required base**: Estimated blank base (step 2) − Base displaced (step 4).
""")

st.sidebar.header("Batch Settings")
n = st.sidebar.number_input("Number of suppositories", min_value=1, value=1, step=1)
blank_unit_weight_g = st.sidebar.number_input("Average blank weight per suppository (g)", min_value=0.0, value=2.0, step=0.01, format="%.4f")
base_density = st.sidebar.number_input("Base density (g/mL)", min_value=0.0001, value=1.0, step=0.01, format="%.4f")

st.sidebar.markdown("---")
st.sidebar.subheader("Active Ingredients")
max_apis = st.sidebar.number_input("Number of API components", min_value=1, max_value=5, value=1, step=1)

api_rows = []
for i in range(int(max_apis)):
    with st.sidebar.expander(f"API {i+1}", expanded=(i==0)):
        name = st.text_input(f"Name for API {i+1}", value=f"API {i+1}", key=f"name_{i}")
        unit = st.selectbox(f"Amount per suppository - unit ({i+1})", options=["mg", "g"], index=0, key=f"unit_{i}")
        amt = st.number_input(f"Amount per suppository ({unit}) - API {i+1}", min_value=0.0, value=200.0 if i==0 else 0.0, step=0.01, format="%.4f", key=f"amt_{i}")
        rho = st.number_input(f"Density ρ(API {i+1}) (g/mL)", min_value=0.0001, value=3.0 if i==0 else 1.0, step=0.01, format="%.4f", key=f"rho_{i}")
    # convert to grams
    amt_g = amt/1000.0 if unit == "mg" else amt
    api_rows.append((name, amt_g, rho))

st.markdown("### Inputs Summary")
st.write(f"- **Number of suppositories**: {n}")
st.write(f"- **Average blank weight per unit**: {blank_unit_weight_g:.4f} g")
st.write(f"- **Base density**: {base_density:.4f} g/mL")
st.write("#### APIs (per suppository)")
for name, amt_g, rho in api_rows:
    st.write(f"- **{name}**: {amt_g:.4f} g, ρ = {rho:.4f} g/mL")

# --- Calculations ---
total_api_weight = sum(amt_g for _, amt_g, _ in api_rows) * n  # g
estimated_blank_base = blank_unit_weight_g * n  # g
density_ratio = sum((amt_g for _, amt_g, _ in api_rows))  # not used; ratio is per API; but step uses a single equivalent ratio if APIs mix
# For multiple APIs, base displaced is sum over components: (m_i / rho_i) * rho_base
base_displaced = sum((amt_g / rho) * base_density for _, amt_g, rho in api_rows) * n  # g
# Using step 4 wording: total API weight ÷ (ρ(API)/ρ(base)) when a single API.
# For multiple APIs we compute component-wise displacement above.

required_base = estimated_blank_base - base_displaced

st.markdown("### Step-by-Step Results")

# Step 1
st.markdown("**Step 1: Total API amount**")
st.write(f"Total API weight = Σ(amount per unit) × {n} = **{total_api_weight:.4f} g**")

# Step 2
st.markdown("**Step 2: Estimated blank base weight**")
st.write(f"Estimated blank base = {blank_unit_weight_g:.4f} g × {n} = **{estimated_blank_base:.4f} g**")

# Step 3
st.markdown("**Step 3: Density ratios**")
for name, amt_g, rho in api_rows:
    ratio = rho / base_density
    st.write(f"- {name}: ρ(API)/ρ(base) = {rho:.4f}/{base_density:.4f} = **{ratio:.4f}**")

# Step 4
st.markdown("**Step 4: Base displaced by APIs**")
detail_lines = []
for name, amt_g, rho in api_rows:
    ratio = rho / base_density
    displaced_per_unit = amt_g / ratio  # g per suppository
    displaced_total = displaced_per_unit * n
    detail_lines.append((name, displaced_per_unit, displaced_total))
    st.write(f"- {name}: Base displaced per unit = {amt_g:.4f} g ÷ {ratio:.4f} = {displaced_per_unit:.4f} g; total = **{displaced_total:.4f} g**")

st.write(f"**Total base displaced** (sum of all APIs) = **{base_displaced:.4f} g**")

# Step 5
st.markdown("**Step 5: Required base**")
st.write(f"Required base = Estimated blank base − Base displaced = {estimated_blank_base:.4f} − {base_displaced:.4f} = **{required_base:.4f} g**")

# 3) Sanity checks
if required_base < 0:
    st.warning("The required base is negative. Your blank weight may be too small or API load too high for this mold.")
if any(rho <= 0 for _, _, rho in api_rows) or base_density <= 0:
    st.warning("Densities must be positive values.")

st.markdown("---")
st.markdown("**Tip:** For a single API, Step 4 can be written as: Base displaced = Total API × (ρ(base)/ρ(API)). "
            "This is algebraically identical to dividing by the Step-3 ratio.")

st.caption("Educational tool only; verify with your PI/Instructor")

import streamlit as st

st.set_page_config(page_title="Suppository Base Calculator — 5-Step", layout="centered")

st.title("Suppository Base Calculator — 5-Step Method")
st.caption("Implements only the five-step density-ratio calculator plus error checks/coaching.")

# Load and display the COPHS logo at the top
logo = Image.open("COPHS logo.jpg")
st.image(logo, width=200)

with st.expander("Method (5 steps)", expanded=False):
    st.markdown("""
1) **Total API amount**: Sum of all actives for all suppositories.  
2) **Estimated blank base**: Average blank weight × number of suppositories.  
3) **Density ratio**: ρ(API) / ρ(base).  
4) **Base displaced**: Total API weight ÷ ratio from Step 3 (for multiple APIs, sum per-component displacement).  
5) **Required base**: Step 2 − Step 4.
""")

# --- Inputs ---
st.markdown("### Inputs")

colA, colB, colC = st.columns(3)
with colA:
    n = st.number_input("Number of suppositories (N)", min_value=1, value=1, step=1)
with colB:
    blank_unit_weight_g = st.number_input("Average blank weight per unit (g)", min_value=0.0, value=2.0, step=0.01, format="%.4f")
with colC:
    base_density = st.number_input("Base density ρ(base) (g/mL)", min_value=0.0001, value=1.0, step=0.01, format="%.4f")

st.markdown("#### Active ingredients (per suppository)")
max_apis = st.number_input("How many API components?", min_value=1, max_value=5, value=1, step=1)
apis = []
for i in range(int(max_apis)):
    cols = st.columns([2, 1, 1, 1])
    with cols[0]:
        name = st.text_input(f"Name (API {i+1})", value=f"API {i+1}")
    with cols[1]:
        amt_value = st.number_input(f"Amount ({i+1})", min_value=0.0, value=200.0 if i==0 else 0.0, step=0.01, format="%.4f", key=f"amt_{i}")
    with cols[2]:
        unit = st.selectbox(f"Unit ({i+1})", ["mg", "g"], index=0, key=f"unit_{i}")
    with cols[3]:
        rho = st.number_input(f"ρ(API {i+1}) (g/mL)", min_value=0.0001, value=3.0 if i==0 else 1.0, step=0.01, format="%.4f", key=f"rho_{i}")
    amt_g = amt_value/1000.0 if unit == "mg" else amt_value
    apis.append({"name": name, "amt_g": amt_g, "rho": rho})

st.divider()

# --- Calculations ---
total_api_weight = sum(a["amt_g"] for a in apis) * n  # g
estimated_blank_base = blank_unit_weight_g * n  # g
# For multiple APIs: sum of component displacements = Σ (m_i / ρ_i) × ρ(base) × N
base_displaced = sum((a["amt_g"] / a["rho"]) * base_density for a in apis) * n  # g
required_base = estimated_blank_base - base_displaced

# --- Output: Stepwise ---
st.markdown("### Step-by-Step Results")
st.markdown("**Step 1: Total API amount**")
st.write(f"Σ(amount per unit) × N = **{total_api_weight:.4f} g**")

st.markdown("**Step 2: Estimated blank base**")
st.write(f"{blank_unit_weight_g:.4f} g × {n} = **{estimated_blank_base:.4f} g**")

st.markdown("**Step 3: Density ratio ρ(API)/ρ(base)**")
for a in apis:
    ratio = a["rho"] / base_density
    st.write(f"- {a['name']}: {a['rho']:.4f}/{base_density:.4f} = **{ratio:.4f}**")

st.markdown("**Step 4: Base displaced by APIs**")
for a in apis:
    ratio = a["rho"] / base_density
    displaced_per_unit = a["amt_g"] / ratio  # g per unit
    displaced_total = displaced_per_unit * n
    st.write(f"- {a['name']}: per unit = {a['amt_g']:.4f} ÷ {ratio:.4f} = {displaced_per_unit:.4f} g; total = **{displaced_total:.4f} g**")
st.write(f"**Total base displaced** = **{base_displaced:.4f} g**")

st.markdown("**Step 5: Required base**")
st.write(f"{estimated_blank_base:.4f} − {base_displaced:.4f} = **{required_base:.4f} g**")

st.markdown(
    "**Tip:** For a single API, Step 4 can be written as: Base displaced = Total API × (ρ(base)/ρ(API)). "
    "This is algebraically identical to dividing by the Step-3 ratio."
)

# Basic sanity warning
if required_base < 0:
    st.warning("The required base is negative. Your blank weight may be too small or API load too high for this mold.")

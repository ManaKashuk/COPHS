# suppository_calculator.py
# Suppository Base Calculator — 5-Step (enhanced pharmacist-friendly version)

import math
from pathlib import Path
from PIL import Image
import streamlit as st

st.set_page_config(page_title="Suppository Base Calculator — 5-Step", layout="centered")
APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "logo.png"

# CSS to reduce the space between the image block and the title
st.markdown("""
<style>
/* shrink spacing under images and above/below h1 */
div.stImage { margin-bottom: -2rem; }
h1 { margin-top: 0.15rem; margin-bottom: 0.15rem; line-height: 1.05; }
</style>
""", unsafe_allow_html=True)

st.image(Image.open(LOGO_PATH), width=150)
st.markdown("<h1>Suppository Base Calculator</h1>", unsafe_allow_html=True)
st.markdown("💬 Chat with the tutor to compute the required base using the 5-step density-ratio method.")

with st.expander("Method (5 steps)", expanded=False):
    st.markdown("""
1) **Total API amount**: Sum of all actives for all suppositories.  
2) **Estimated blank base**: Average blank weight × number of suppositories.  
3) **Density ratio**: ρ(API) / ρ(base).  
4) **Base displaced**: For a single API, `Total API ÷ (ρ(API)/ρ(base))`. For multiple APIs, sum component displacements: `Σ[(m_i/ρ_i)×ρ_base]`.  
5) **Required base**: Step 2 − Step 4.
""")

# -------------------------
# Sidebar FORM for inputs
# -------------------------
with st.sidebar.form("calc_form"):
    st.header("Batch Inputs")
    N = st.number_input("Number of suppositories (N)", min_value=1, value=12, step=1)

    # Quick-pick bases
    st.subheader("Base")
    base_options = {
        "Cocoa butter (theobroma oil) ~0.90 g/mL": 0.90,
        "PEG blend (e.g., 1450/1000) ~1.20 g/mL": 1.20,
        "Glycerinated gelatin ~1.25 g/mL": 1.25,
        "Witepsol/HBW type ~0.95 g/mL": 0.95,
        "Custom…": None,
    }
    base_choice = st.selectbox("Select base (prefill density)", list(base_options.keys()), index=0)
    base_density = (
        base_options[base_choice]
        if base_options[base_choice] is not None
        else st.number_input("ρ(base) (g/mL)", min_value=0.0001, value=1.0, step=0.01, format="%.4f")
    )
    blank_unit_weight_g = st.number_input(
        "Average blank weight per unit (g)", min_value=0.0, value=2.00, step=0.01, format="%.4f"
    )

    st.markdown("---")
    st.subheader("API Entry Mode")
    api_mode = st.radio(
        "Choose how to enter API properties",
        ["Density (ρ)", "Displacement Factor (DF)"],
        index=0,
        help="Use DF if you have mold-specific displacement factors for your APIs.",
    )

    # ===== Active Ingredients (compact grid) =====
    st.subheader("Active Ingredients (per suppository)")
    max_apis = st.number_input("How many API components?", min_value=1, max_value=6, value=1, step=1)

    # header row
    hdr = st.columns([1.9, 1.2, 0.9, 1.4])
    hdr[0].markdown("**Name**")
    hdr[1].markdown("**Amt**")
    hdr[2].markdown("**Unit**")
    hdr[3].markdown("**ρ (g/mL)**" if api_mode == "Density (ρ)" else "**DF (g/g base)**")

    apis = []
    for i in range(int(max_apis)):
        cols = st.columns([1.9, 1.2, 0.9, 1.4])

        name = cols[0].text_input("Name", value=f"API {i+1}", key=f"name_{i}", label_visibility="collapsed")
        amt_value = cols[1].number_input(
            "Amount", min_value=0.0, value=200.0 if i == 0 else 0.0, step=0.01, format="%.4f",
            key=f"amt_{i}", label_visibility="collapsed"
        )
        unit = cols[2].selectbox("Unit", ["mg", "g"], index=0, key=f"unit_{i}", label_visibility="collapsed")

        if api_mode == "Density (ρ)":
            rho = cols[3].number_input(
                "rho", min_value=0.0001, value=3.00 if i == 0 else 1.00, step=0.01, format="%.4f",
                key=f"rho_{i}", label_visibility="collapsed"
            )
            df = None
        else:
            df = cols[3].number_input(
                "DF", min_value=0.0001, value=1.50 if i == 0 else 1.00, step=0.01, format="%.4f",
                key=f"df_{i}", label_visibility="collapsed"
            )
            rho = None

        amt_g = amt_value/1000.0 if unit == "mg" else amt_value
        apis.append({"name": name, "amt_g": amt_g, "rho": rho, "df": df})

    st.markdown("---")
    st.subheader("Pharmacy Controls")
    overage_pct = st.number_input("Overage for base to cover loss (%)", min_value=0.0, value=0.0, step=0.5)
    round_step = st.selectbox("Round required base to nearest", ["none", "0.001 g", "0.01 g", "0.1 g"], index=1)

    # >>> IMPORTANT: submit button must be inside this form <<<
    submitted = st.form_submit_button("Calculate")


# -------------------------
# Calculations after submit
# -------------------------
if submitted:
    # Step 1: total API (batch)
    total_api_per_unit = sum(a["amt_g"] for a in apis)          # g per unit
    total_api_batch = total_api_per_unit * N                     # g batch

    # Step 2: estimated blank base (batch)
    est_blank_batch = blank_unit_weight_g * N                    # g batch

    # Step 3 & 4: displacement (supports Density or DF)
    displaced_per_unit = 0.0
    ratios = []  # for density mode reporting

    if api_mode == "Density (ρ)":
        for a in apis:
            if not a["rho"] or a["rho"] <= 0:
                st.error(f"{a['name']}: API density must be > 0.")
                st.stop()
            ratio = a["rho"] / base_density
            ratios.append((a["name"], ratio, a["rho"]))
            # per-unit displaced base mass for this API:
            displaced_per_unit += (a["amt_g"] / ratio)  # g base per unit
    else:  # DF mode
        # DF = grams of API that displace 1 g base => displaced base per unit for API i = m_i / DF_i
        for a in apis:
            if not a["df"] or a["df"] <= 0:
                st.error(f"{a['name']}: DF must be > 0.")
                st.stop()
            displaced_per_unit += (a["amt_g"] / a["df"])  # g base per unit

    displaced_batch = displaced_per_unit * N
    required_base_per_unit = blank_unit_weight_g - displaced_per_unit
    required_base_batch = est_blank_batch - displaced_batch

    # Apply overage to required base (batch)
    if overage_pct > 0:
        required_base_batch *= (1 + overage_pct / 100.0)

    # Rounding
    required_base_batch = round_to(required_base_batch, round_step)

    # Derived per-unit after rounding batch (approx evenly split)
    required_base_per_unit_out = required_base_batch / N

    # ===== Display results =====
    st.markdown("### Step-by-Step Results")
    st.markdown("**Step 1: Total API amount**")
    st.write(f"Per unit = **{total_api_per_unit:.4f} g**; Batch (×{N}) = **{total_api_batch:.4f} g**")

    st.markdown("**Step 2: Estimated blank base**")
    st.write(f"Per unit = **{blank_unit_weight_g:.4f} g**; Batch (×{N}) = **{est_blank_batch:.4f} g**")

    if api_mode == "Density (ρ)":
        st.markdown("**Step 3: Density ratio ρ(API)/ρ(base)**")
        st.write(f"ρ(base) = **{base_density:.4f} g/mL**")
        for name, ratio, rho_api in ratios:
            st.write(f"- {name}: {rho_api:.4f}/{base_density:.4f} = **{ratio:.4f}**")
    else:
        st.markdown("**Step 3: Displacement Factor (DF) mode**")
        for a in apis:
            st.write(f"- {a['name']}: DF = **{a['df']:.4f}** (g API per 1 g base)")

    st.markdown("**Step 4: Base displaced by APIs**")
    st.write(f"Per unit displaced base = **{displaced_per_unit:.4f} g**; Batch displaced base = **{displaced_batch:.4f} g**")

    st.markdown("**Step 5: Required base**")
    st.write(f"Per unit required base = **{required_base_per_unit_out:.4f} g**; Batch required base = **{required_base_batch:.4f} g**")

    st.divider()

    # ===== Capacity & sanity checks =====
    st.markdown("### Capacity & Sanity Checks")
    if required_base_per_unit < 0:
        st.error("**Negative base per unit (pre-overage)** — API displacement exceeds blank capacity.")
    else:
        st.success("Per-unit base amount is non-negative.")

    if displaced_per_unit > blank_unit_weight_g:
        st.warning("**API volume alone exceeds blank weight** — APIs displace more base than the mold holds.")
    if base_density <= 0:
        st.error("Base density must be > 0.")

    # ===== Error coaching (only in density mode) =====
    st.markdown("### Error Checks & Coaching")
    if api_mode == "Density (ρ)":
        wrong_displaced_per_unit = 0.0
        for a in apis:
            ratio = a["rho"] / base_density
            wrong_displaced_per_unit += a["amt_g"] * ratio  # WRONG
        wrong_displaced_batch = wrong_displaced_per_unit * N
        wrong_required_batch = est_blank_batch - wrong_displaced_batch
        diff = abs(wrong_required_batch - (est_blank_batch - displaced_batch))

        st.markdown(
            f"**Common mistake detected (reversing Step 3):** If you used ρ(base)/ρ(API) and then multiplied by the ratio in Step 4, "
            f"you'd compute base displaced = **{wrong_displaced_batch:.4f} g**, leading to required base = **{wrong_required_batch:.4f} g** "
            f"(off by **{diff:.4f} g**). Remember: Step 3 ratio is ρ(API)/ρ(base), and Step 4 is **divide** total API weight by that ratio."
        )

        direct_subtract_required_batch = est_blank_batch - total_api_batch
        st.markdown(
            f"**Another mistake:** Subtracting API weight directly from the blank base would give **{direct_subtract_required_batch:.4f} g**, "
            "which ignores displacement by density. Use the density ratio to find the base displaced, not the API weight."
        )

        st.markdown(
            "**Tip:** For a single API, Step 4 can be written as: Base displaced = Total API × (ρ(base)/ρ(API)). "
            "This is algebraically identical to dividing by the Step-3 ratio."
        )
    else:
        st.info("In **DF mode**, per-unit displaced base = Σ(m_i / DF_i). Avoid subtracting API mass directly from blank base.")

else:
    st.info("Enter inputs in the sidebar and click **Calculate** to see results.")

    # -------------------------
    # Minimal export (CSV-like text)
    # -------------------------
    st.markdown("### Export")
    lines = [
        "Suppository Base Calculator — 5-Step",
        f"N,{N}",
        f"Blank per unit (g),{blank_unit_weight_g:.4f}",
        f"Base density (g/mL),{base_density:.4f}",
        f"Mode,{api_mode}",
    ]
    for a in apis:
        if api_mode == "Density (ρ)":
            lines.append(f"{a['name']} amount per unit (g),{a['amt_g']:.4f},rho,{a['rho']:.4f}")
        else:
            lines.append(f"{a['name']} amount per unit (g),{a['amt_g']:.4f},DF,{a['df']:.4f}")
    lines += [
        f"Total API per unit (g),{total_api_per_unit:.4f}",
        f"Total API batch (g),{total_api_batch:.4f}",
        f"Estimated blank batch (g),{est_blank_batch:.4f}",
        f"Displaced base per unit (g),{displaced_per_unit:.4f}",
        f"Displaced base batch (g),{displaced_batch:.4f}",
        f"Required base batch (g) (after overage, rounded),{required_base_batch:.4f}",
        f"Required base per unit (g) (from rounded batch),{required_base_per_unit_out:.4f}",
        f"Overage (%),{overage_pct:.2f}",
        f"Rounding step,{round_step}",
    ]
    csv_text = "\n".join(lines)
    st.download_button("Download results (CSV)", data=csv_text, file_name="suppository_calculation.csv", mime="text/csv")

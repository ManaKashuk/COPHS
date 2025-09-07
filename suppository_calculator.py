
import re
import json
from PIL import Image
import streamlit as st


st.set_page_config(page_title="Suppository Calculator — Chat", layout="centered")


# --- Utilities ---
def parse_floats(pattern, text, flags=re.I):
    m = re.search(pattern, text, flags)
    if not m:
        return None
    groups = m.groupdict()
    return {k: float(v) for k, v in groups.items() if v is not None}

def parse_units_amount(s):
    # Returns grams per unit and a pretty string
    s = s.strip()
    m = re.search(r'(?P<v>\d+(?:\.\d+)?)\s*(?P<u>mg|g)\b', s, re.I)
    if not m:
        return None, None
    v = float(m.group('v'))
    u = m.group('u').lower()
    g = v/1000.0 if u == 'mg' else v
    return g, f"{v:g} {u}"

def parse_density(s):
    m = re.search(r'(?P<v>\d+(?:\.\d+)?)\s*(?:g\/?m?l|g\s*per\s*m?l)\b', s, re.I)
    if m:
        return float(m.group('v'))
    # allow bare number if user already knows it's density
    m = re.search(r'\b(?P<v>\d+(?:\.\d+)?)\b', s)
    return float(m.group('v')) if m else None

def render_summary(state):
    st.markdown("#### Current Inputs")
    st.write(f"- **Units (N)**: {state['n']}")
    st.write(f"- **Blank weight per unit**: {state['blank_g']:.4f} g")
    st.write(f"- **Base density**: {state['base_rho']:.4f} g/mL")
    if state['apis']:
        st.write("**APIs (per unit):**")
        for i, api in enumerate(state['apis'], 1):
            st.write(f"  - {api['name']}: {api['amt_g']:.4f} g, ρ={api['rho']:.4f} g/mL")

def compute(state):
    n = state['n']
    blank = state['blank_g']
    rho_base = state['base_rho']
    apis = state['apis']

    total_api_weight = sum(a['amt_g'] for a in apis) * n
    est_blank = blank * n
    # per-API displacement
    displaced = sum((a['amt_g'] / a['rho']) * rho_base for a in apis) * n
    required_base = est_blank - displaced

    details = {
        'total_api_weight': total_api_weight,
        'est_blank': est_blank,
        'displaced': displaced,
        'required_base': required_base,
        'ratios': [(a['name'], a['rho']/rho_base) for a in apis]
    }
    return details

def stepwise_explanation(state, details):
    n = state['n']
    blank = state['blank_g']
    rho_base = state['base_rho']
    apis = state['apis']

    lines = []
    lines.append(f"**Step 1 – Total API amount**: Σ(amount per unit) × {n} = **{details['total_api_weight']:.4f} g**.")
    lines.append(f"**Step 2 – Estimated blank base**: {blank:.4f} g × {n} = **{details['est_blank']:.4f} g**.")
    lines.append("**Step 3 – Density ratio** ρ(API)/ρ(base):")
    for name, ratio in details['ratios']:
        lines.append(f"- {name}: **{ratio:.4f}**")
    lines.append("**Step 4 – Base displaced** (sum over APIs): " +
                 " + ".join([f"[{a['name']}: {a['amt_g']:.4f} ÷ ({a['rho']:.4f}/{rho_base:.4f})]"
                             for a in apis]) +
                 f" × {n} = **{details['displaced']:.4f} g**.")
    lines.append(f"**Step 5 – Required base**: {details['est_blank']:.4f} − {details['displaced']:.4f} = **{details['required_base']:.4f} g**.")
    return "\n\n".join(lines)

def error_coaching(state, details):
    n = state['n']
    est_blank = details['est_blank']
    apis = state['apis']
    rho_base = state['base_rho']

    # Wrong: multiply API weight by ρ(API)/ρ(base)
    wrong_displaced = sum(a['amt_g'] * (a['rho'] / rho_base) for a in apis) * n
    wrong_required = est_blank - wrong_displaced
    direct_subtract = est_blank - sum(a['amt_g'] for a in apis) * n

    msgs = []
    msgs.append("**Common errors to avoid:**")
    if abs(wrong_displaced - details['displaced']) > 1e-9:
        msgs.append(
            f"- **Reversing Step 3**: If you multiply API weight by ρ(API)/ρ(base), you'd get base displaced = {wrong_displaced:.4f} g → required base = {wrong_required:.4f} g. "
            "Correct approach is to **divide** API weight by ρ(API)/ρ(base)."
        )
    if abs(direct_subtract - details['required_base']) > 1e-9:
        msgs.append(
            f"- **Subtracting API mass directly**: {direct_subtract:.4f} g (ignores density/volume displacement). Always compute displaced base using densities."
        )
    if details['required_base'] < 0:
        msgs.append("- **Negative required base**: Your blank weight may be too small or the API load too high for this mold.")
    return "\n\n".join(msgs)

# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role":"assistant",
        "content":(
            "Hi! Tell me your inputs and I'll compute the required base using the 5‑step method.\n\n"
            "You can paste everything in one line, e.g.:\n"
            "`N=1; blank=2 g; base=1.0 g/mL; API: 200 mg (rho=3.0)`\n\n"
            "Or we can do it piece‑by‑piece: tell me **number of suppositories**, **blank weight per unit**, **base density**, and each **API** like `Drug A 150 mg, rho 1.2`."
        )
    }]

if "state" not in st.session_state:
    st.session_state.state = {"n": None, "blank_g": None, "base_rho": None, "apis": []}

state = st.session_state.state

# Quick examples
with st.sidebar:
    st.subheader("Quick Fill")
    if st.button("Load Screenshot Example"):
        state.update({"n":1, "blank_g":2.0, "base_rho":1.0, "apis":[{"name":"API 1","amt_g":0.200,"rho":3.0}]})
        st.session_state.messages.append({"role":"assistant","content":"Loaded example: N=1, blank=2.0 g, base ρ=1.0 g/mL, API: 200 mg (ρ=3.0). Type **compute** to see the steps."})
    if st.button("Reset"):
        st.session_state.state = {"n": None, "blank_g": None, "base_rho": None, "apis": []}
        st.session_state.messages = st.session_state.messages[:1]

# Render conversation
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Type inputs (e.g., 'N=12; blank 1.8 g; base 0.95; API: Drug A 150 mg, rho 1.2; API: Drug B 50 mg, rho 2.5') or 'compute'")
if prompt:
    st.session_state.messages.append({"role":"user","content":prompt})
    reply = ""

    text = prompt.strip()

    # Parse all-in-one style
    if re.search(r'\bcompute\b', text, re.I):
        if None in (state["n"], state["blank_g"], state["base_rho"]) or len(state["apis"]) == 0:
            reply = "I still need the remaining inputs. Please provide **N**, **blank per unit**, **base density**, and at least one **API**."
        else:
            details = compute(state)
            reply = stepwise_explanation(state, details) + "\n\n" + error_coaching(state, details)

    else:
        # Try to capture specific fields
        m = re.search(r'\bN\s*=\s*(\d+)', text, re.I)
        if m: state["n"] = int(m.group(1))

        m = re.search(r'blank[^0-9]*(\d+(?:\.\d+)?)\s*(?:g)\b', text, re.I)
        if m: state["blank_g"] = float(m.group(1))

        m = re.search(r'base[^0-9]*(\d+(?:\.\d+)?)\s*(?:g\/?m?l)?', text, re.I)
        if m: state["base_rho"] = float(m.group(1))

        # Parse any number of API clauses like "API: Drug A 150 mg, rho 1.2"
        apis_found = re.findall(r'(?:API:)?\s*([A-Za-z0-9 _\-]+?)\s*(\d+(?:\.\d+)?)\s*(mg|g)\s*,?\s*(?:rho|density)\s*[:=]?\s*(\d+(?:\.\d+)?)', text, re.I)
        for name, amt, unit, rho in apis_found:
            amt_g = float(amt)/1000.0 if unit.lower()=='mg' else float(amt)
            rho = float(rho)
            # collapse duplicates by name
            found_ix = None
            for i, a in enumerate(state["apis"]):
                if a["name"].strip().lower() == name.strip().lower():
                    found_ix = i; break
            if found_ix is None:
                state["apis"].append({"name":name.strip(), "amt_g":amt_g, "rho":rho})
            else:
                state["apis"][found_ix].update({"amt_g":amt_g, "rho":rho})

        # If user pasted a minimal API (no name)
        apis_found2 = re.findall(r'API\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(mg|g)\s*\(?(?:rho|density)\s*[:=]?\s*(\d+(?:\.\d+)?)\)?', text, re.I)
        for amt, unit, rho in apis_found2:
            amt_g = float(amt)/1000.0 if unit.lower()=='mg' else float(amt)
            rho = float(rho)
            state["apis"].append({"name":f"API {len(state['apis'])+1}", "amt_g":amt_g, "rho":rho})

        # Build status message
        missing = []
        if state["n"] is None: missing.append("N")
        if state["blank_g"] is None: missing.append("blank per unit (g)")
        if state["base_rho"] is None: missing.append("base density (g/mL)")
        if len(state["apis"]) == 0: missing.append("at least one API with amount + rho")

        if missing:
            reply = "Got it! I updated what you gave me. Still need: **" + ", ".join(missing) + "**.\n\n"
        else:
            reply = "Great—inputs captured. Type **compute** to see the 5‑step solution, or keep editing values."

        # Show a compact summary
        summary_lines = [f"- **N** = {state['n']}",
                         f"- **Blank/unit** = {state['blank_g']:.4f} g",
                         f"- **ρ(base)** = {state['base_rho']:.4f} g/mL"]
        for a in state['apis']:
            summary_lines.append(f"- **{a['name']}**: {a['amt_g']:.4f} g, ρ={a['rho']:.4f} g/mL")
        reply += "\n\n" + "\n".join(summary_lines)

    st.session_state.messages.append({"role":"assistant","content":reply})
    st.rerun()

# Show a live summary panel
st.divider()
state_ready = all(v is not None for v in (state["n"], state["blank_g"], state["base_rho"])) and len(state["apis"])>0
with st.expander("Current inputs", expanded=False):
    if state_ready:
        render_summary(state)
        if st.button("Compute now"):
            details = compute(state)
            st.info(stepwise_explanation(state, details))
            st.warning(error_coaching(state, details))
    else:
        st.write("Supply N, blank weight per unit (g), base density (g/mL), and at least one API.")
st.caption("Educational aid only. Cross‑check with your institution's standard procedures.")

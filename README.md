# Suppository Base Calculator (Density-Ratio Method)

This Streamlit app walks students through the 5-step suppository base calculation and catches common mistakes
(e.g., reversing the Step-3 ratio). It supports multiple APIs per suppository and provides per-step explanations.

## Quick start
1. (Optional) Create a virtual environment
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run suppository_calculator.py
   ```

## Inputs
- Number of suppositories
- Average blank weight per suppository (g)
- Base density (g/mL)
- For each API (1–5):
  - Name
  - Amount per suppository (mg or g)
  - Density (g/mL)

## Method (5 steps)
1) **Total API amount**  
2) **Estimated blank base weight**  
3) **Density ratio** = ρ(API) / ρ(base)  
4) **Base displaced** = (Total API) ÷ ratio (or per-API displacement summed)  
5) **Required base** = Step-2 − Step-4

## Example (matches the screenshot)
- 1 suppository, blank = 2.0 g
- Base density = 1.0 g/mL
- One API: 200 mg per suppository, ρ(API)=3.0 g/mL

Expected result: Required base ≈ **1.933 g**.

## Notes
- Educational tool only. Verify with your institution’s standards.
- Aligns with the PharmCalculator Education Corner description of the density-ratio method.
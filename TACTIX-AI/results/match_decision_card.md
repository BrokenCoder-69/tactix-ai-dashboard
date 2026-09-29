
# TACTIX-AI MATCH DECISION CARD — Barcelona vs Real Madrid (hypothetical next meeting at Barcelona's ground)
*Run: FULL THESIS RUN · data: StatsBomb Open Data, La Liga 2015/2016 ·
tags: **[O]** observed · **[M]** model · **[S]** simulation · **[I]** interpretation*

### 1. Opponent profile
- [O] Style: pass share 0.57 (rank 2), directness 0.20 (rank 19), PPDA 13.30 (rank 8)
- [O] Main strengths: Points / match, npxG, Shots (non-penalty), Box entries
- [O] Main weaknesses: none in the bottom quartile — no glaring weakness

### 2. Main threats
- [O] Gareth Frank Bale — Finisher, Creator, Progressor, Wide threat, Transition threat; per-90 score 0.98; 11% of team npxG + xA; main zone Center
- [O] James David Rodríguez Rubio — Creator, Progressor, Wide threat, Transition threat; per-90 score 0.91; 7% of team npxG + xA; main zone Center
- [O] Francisco Román Alarcón Suárez — Creator, Progressor, Wide threat, Transition threat; per-90 score 0.89; 7% of team npxG + xA; main zone Center
- [O] Cristiano Ronaldo dos Santos Aveiro — Finisher, Transition threat; per-90 score 0.88; 23% of team npxG + xA; main zone Center

### 3. Recommended tactical approach
- [I] **Primary:** High press + Possession control — *the strongest evidence-supported winning scenario under the available data and model assumptions*
- [I] **Secondary:** Mid block + Possession control
- [M] Evidence tier: **Suggestive** (positive point estimate, CI includes 0)

### 4. Squad (descriptive)
- [O] Most-used Barcelona XI in its most-used formation (4-3-3): Claudio Andrés Bravo Muñoz (Goalkeeper); Gerard Piqué Bernabéu (Right Center Back); Javier Alejandro Mascherano (Left Center Back); Jordi Alba Ramos (Left Back); Daniel Alves da Silva (Right Back); Sergio Busquets i Burgos (Center Defensive Midfield); Ivan Rakitić (Right Center Midfield); Andrés Iniesta Luján (Left Center Midfield); Neymar da Silva Santos Junior (Left Wing); Lionel Andrés Messi Cuccittini (Right Wing); Luis Alberto Suárez Díaz (Center Forward)
- [I] Squad optimisation is not implemented; this is the XI the coach used most, shown for orientation only

### 5. Defensive plan
- [O] Primary threat by output share: Cristiano Ronaldo dos Santos Aveiro; defensive attention proxy on his main zone
- [S] CONDITIONAL, not recommended as evidence: IF he were held to his quiet-match level, ΔP(win) +28.8 pp — what suppression would be worth if achieved, not how to achieve it
- [I] Defensive shape: High press (main defensive-action zone x = 80–120 m)
- [M] Defensive effect vs Possession-dominant opponents: npxG against -0.70 per match

### 6. Attacking plan
- [O/I] Target channel: Center; attacking route: Possession control
- [M] Attacking effect vs Possession-dominant opponents: npxG for -0.09 per match

### 7. Expected effects
- [M] npxG for 1.89 · npxG against 0.50 (baseline 1.99 – 1.20)
- [M] npxGD effect vs group +0.61 [-0.12, +1.34]

### 8. Historical evidence
- [O] Pre-registered backtest: followed − not followed +0.052 [-0.122, +0.226]; within-team -0.046 → **pre-match predictive value not demonstrated**
- [O] Sample: 259 team-matches vs Possession-dominant opponents; 740 overall

### 9. Simulation (20,000 matches per plan)
- [S] Win 74.1% · draw 17.0% · loss 8.9% · E[goal diff] +1.57
- [S] ΔP(win) vs baseline +16.4 pp [+1.0, +30.0] — distinguishable from the baseline
- [S] Gain split: attacking -2.2 pp · defensive +18.7 pp

### 10. Limitations
- Event data only (no tracking): shapes and marking are proxies; one season; associations, not causal effects
- The backtest did not confirm that choosing these tactics in advance improves outcomes
- No direct man-marking observation; no injury prediction; no squad optimisation

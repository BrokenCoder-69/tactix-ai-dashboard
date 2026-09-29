"""
TACTIX-AI — interactive dashboard (Streamlit), beginner-friendly edition

Reads the tables and figures that TACTIX_AI_FINAL.ipynb saved in TACTIX-AI/results, TACTIX-AI/data and
TACTIX-AI/figures. Nothing is recomputed, so every number matches the thesis run.

Run:   streamlit run app.py
"""
import json
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="TACTIX-AI Dashboard", page_icon="⚽", layout="wide")

HOME, RIVAL = "Barcelona", "Real Madrid"
TEAM_COLORS = {HOME: "#A50044", RIVAL: "#1F4E9E"}
STYLE_COLORS = {"High press": "#E63946", "Mid block": "#F4A261", "Low block": "#2A9D8F", "Unclassified": "#9E9E9E"}
TIER_COLORS = {"Supported": "#2A9D8F", "Suggestive": "#F4A261", "Not supported": "#9E9E9E", "Unfavourable": "#E63946"}
PALETTE = ["#1F4E9E", "#A50044", "#2A9D8F", "#F4A261", "#E63946", "#6D597A", "#264653", "#E9C46A"]
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = PALETTE

# ------------------------------------------------------------------------------------------------------------
# Look and feel
# ------------------------------------------------------------------------------------------------------------
st.markdown("""
<style>
.block-container {padding-top: 1.6rem;}
.hero {background: linear-gradient(120deg, #1F4E9E 0%, #6D597A 55%, #A50044 100%); color: white;
       padding: 1.6rem 2rem; border-radius: 18px; margin-bottom: 1.2rem;}
.hero h1 {color: white; margin: 0 0 .3rem 0; font-size: 2.1rem;}
.hero p {color: #f1f1f1; margin: 0; font-size: 1.05rem;}
.card {border-radius: 14px; padding: 1rem 1.1rem; color: white; margin-bottom: .6rem; min-height: 112px;}
.card .lbl {font-size: .85rem; opacity: .9;}
.card .val {font-size: 1.75rem; font-weight: 700; line-height: 1.2;}
.card .sub {font-size: .8rem; opacity: .9;}
.box {border-radius: 12px; padding: .9rem 1.1rem; margin: .4rem 0 1rem 0; font-size: .98rem;}
.box.what {background: #EAF2FB; border-left: 6px solid #1F4E9E;}
.box.read {background: #FFF4E6; border-left: 6px solid #F4A261;}
.box.says {background: #E8F6F3; border-left: 6px solid #2A9D8F;}
.box.warn {background: #FDECEE; border-left: 6px solid #E63946;}
.box b.t {display: block; margin-bottom: .25rem;}
.step {background: white; border: 1px solid #e5e5e5; border-radius: 14px; padding: .9rem; text-align: center; min-height: 150px;}
.step .ico {font-size: 2rem;}
/* keep the sidebar scrollable even with long expanders */
section[data-testid="stSidebar"] > div, div[data-testid="stSidebarContent"], div[data-testid="stSidebarUserContent"]
  {overflow-y: auto !important; max-height: 100vh;}
</style>
""", unsafe_allow_html=True)


import re


def md(text):
    # Streamlit does not apply markdown inside HTML boxes, so convert **bold** and *italic* to HTML tags.
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", str(text))
    return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)


def hero(title, subtitle):
    st.markdown(f'<div class="hero"><h1>{md(title)}</h1><p>{md(subtitle)}</p></div>', unsafe_allow_html=True)


def card(col, label, value, sub="", color="#1F4E9E"):
    col.markdown(f'<div class="card" style="background:{color}"><div class="lbl">{md(label)}</div>'
                 f'<div class="val">{md(value)}</div><div class="sub">{md(sub)}</div></div>', unsafe_allow_html=True)


def box(kind, title, text):
    icons = {"what": "🔎", "read": "📖", "says": "💡", "warn": "⚠️"}
    st.markdown(f'<div class="box {kind}"><b class="t">{icons[kind]} {title}</b>{md(text)}</div>', unsafe_allow_html=True)


def what(text): box("what", "What is this?", text)
def read(text): box("read", "How to read it", text)
def says(text): box("says", "What the data says", text)
def warn(text): box("warn", "Be careful", text)


def auc_label(v):
    if v >= 0.9: return "🟢 excellent"
    if v >= 0.8: return "🟢 good"
    if v >= 0.7: return "🟡 fair"
    if v >= 0.6: return "🟠 weak"
    return "🔴 barely better than guessing"


# ------------------------------------------------------------------------------------------------------------
# Jargon buster (used in the sidebar and on the Glossary page)
# ------------------------------------------------------------------------------------------------------------
GLOSSARY = {
    "Event data": "A list of everything that happens with the ball: every pass, shot, tackle… with who did it and where on the pitch.",
    "xG (expected goals)": "How good a chance was, from 0 to 1. A penalty is about 0.78 (scored ~78% of the time); a shot from 30 m is about 0.03.",
    "npxG": "xG without penalties. Penalties depend on the referee, not on tactics, so we leave them out.",
    "npxGD": "npxG created minus npxG conceded. Positive = you created better chances than your opponent.",
    "xA (expected assists)": "The xG of the shots that a player's passes created — a measure of chance creation.",
    "Per 90": "A number scaled to one full match (90 minutes), so players with different playing time can be compared fairly.",
    "Progressive pass": "A pass that moves the ball clearly closer to the opponent's goal.",
    "Channels": "Five vertical lanes of the pitch: left wing, left half-space, centre, right half-space, right wing.",
    "PPDA": "Passes the opponent is allowed before you win the ball back or foul. LOW PPDA = you press hard.",
    "Pressing index": "One number combining how hard (PPDA) and how high up the pitch a team defends.",
    "High press / Mid block / Low block": "Three defensive styles: chase the ball high, defend in midfield, or sit deep near your own goal.",
    "Threat score": "How dangerous a player is per 90 minutes, as an average percentile of six attacking statistics (0 = least, 1 = most).",
    "Percentile": "Your position in a ranking: the 90th percentile means better than 90% of players.",
    "Expectation / residual": "Before each match we estimate what a team should produce against that opponent. The residual is what actually happened minus that expectation.",
    "Within-team comparison": "Comparing a team only with itself (its own other matches), so that 'who the team is' doesn't get mixed up with 'what the team did'.",
    "Confidence interval (CI)": "A range of plausible values. If it doesn't include 0, the effect is unlikely to be pure chance.",
    "ROC-AUC": "How well a model separates yes from no: 0.5 = coin flip, 1.0 = perfect.",
    "SHAP / LIME": "Methods that show which inputs a model relied on for a prediction. They explain the model — not football cause and effect.",
    "Backtest": "Replaying the season: before each match, make a recommendation using only earlier matches, then check what happened.",
    "Monte Carlo simulation": "Playing the same match thousands of times on the computer with realistic randomness, to see how often each result happens.",
    "Association vs cause": "'Associated with' means two things happen together. It does NOT prove one causes the other.",
}

# ------------------------------------------------------------------------------------------------------------
# Data loading
# ------------------------------------------------------------------------------------------------------------
def find_project(default="TACTIX-AI"):
    here = os.path.dirname(os.path.abspath(__file__))
    for base in [os.getcwd(), here, os.path.dirname(here)]:
        cand = os.path.join(base, default)
        if os.path.isdir(os.path.join(cand, "results")):
            return cand
    return os.path.join(os.getcwd(), default)


st.sidebar.markdown("## ⚽ TACTIX-AI")
st.sidebar.caption("Football tactics, explained with data")
PAGES = ['🏁 Start here', '🧭 Match Planner', '🔎 Scouting', '🌍 Verification (5 leagues)', '📋 Decision Card (example)', '🏟️ Team Explorer', '🛡️ Pressing Styles', '🏃 Players', '🎯 Rival & Threats', '🤖 Models & XAI', '🧪 Validation', '🎲 Simulation & Game Plans', '📖 Glossary']
page = st.sidebar.radio("Go to", PAGES)
with st.sidebar.expander("📖 Jargon buster", expanded=False):
    q = st.text_input("🔍 Search a term", "", placeholder="e.g. xG, press, SHAP")
    hits = {k: v for k, v in GLOSSARY.items() if q.lower() in (k + " " + v).lower()}
    with st.container(height=380):                      # its own scroll box, so it always scrolls
        if not hits:
            st.caption("No matching term — try another word, or open 📖 Glossary.")
        for k, v in hits.items():
            st.markdown(f"**{k}** — {v}")
    st.caption(f"{len(hits)} of {len(GLOSSARY)} terms · full list on the 📖 Glossary page")
with st.sidebar.expander("⚙️ Settings"):
    PROJECT = st.text_input("Project folder (contains results/ and figures/)", find_project())
RES, DATA, FIG = (os.path.join(PROJECT, d) for d in ("results", "data", "figures"))


@st.cache_data(show_spinner=False)
def load(folder, name):
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def table(folder, name):
    df = load(folder, name)
    if df is None:
        st.warning(f"`{name}` was not found in `{folder}` — run the notebook first.")
    return df


def show_fig(name, caption=None):
    path = os.path.join(FIG, name)
    if os.path.exists(path):
        st.image(path, caption=caption, use_container_width=True)
    else:
        st.info(f"Figure `{name}` not found.")


@st.cache_data(show_spinner=False)
def real_match_check(folder):
    # How did teams do when they ACTUALLY played High press + Possession control? (post-hoc, descriptive)
    # Fast path: the notebook (Step 55b) already saved the result.
    tm, bt = load(folder, "team_match_master.csv"), load(folder, "backtest_all_team_matches.csv")
    if tm is None or bt is None:
        return None
    bt = bt.merge(tm[["match_id", "team", "result"]], on=["match_id", "team"], how="left")
    used = bt["strategies_used"].fillna("")
    bt["plan"] = used.str.contains("High press") & used.str.contains("Possession control")
    out = {}
    saved = load(folder, "recommended_plan_real_match_check.csv")
    if saved is not None and len(saved) >= 2:
        for key, i in [("all", 0), ("vs_possession", 1)]:
            r = saved.iloc[i]
            out[key] = dict(n_a=int(r["matches plan played"]), n_b=int(r["matches not played"]),
                            win_a=r["win rate played"], win_b=r["win rate not played"],
                            diff=r["difference"], lo=r["CI low"], hi=r["CI high"])
    else:
        # Fallback: vectorised cluster bootstrap over teams (fast)
        rng = np.random.default_rng(42)
        for key, d in [("all", bt), ("vs_possession", bt[bt["opp_group"] == "Possession-dominant"])]:
            a, b = d[d["plan"]], d[~d["plan"]]
            g = d.groupby(["team", "plan"])["actual_npxgd_resid"].agg(["sum", "count"]).unstack(fill_value=0)
            teams = g.index.to_numpy()
            sa, na = g[("sum", True)].to_numpy() if ("sum", True) in g else 0, g[("count", True)].to_numpy() if ("count", True) in g else 0
            sb, nb = g[("sum", False)].to_numpy(), g[("count", False)].to_numpy()
            w = rng.multinomial(len(teams), np.ones(len(teams)) / len(teams), size=2000)
            with np.errstate(invalid="ignore", divide="ignore"):
                boots = (w @ sa) / (w @ na) - (w @ sb) / (w @ nb)
            lo, hi = np.nanpercentile(boots, [2.5, 97.5])
            out[key] = dict(n_a=len(a), n_b=len(b), win_a=np.mean(a["result"] == "W"), win_b=np.mean(b["result"] == "W"),
                            diff=a["actual_npxgd_resid"].mean() - b["actual_npxgd_resid"].mean(), lo=lo, hi=hi)
    w = bt.groupby(["team", "plan"])["actual_npxgd_resid"].mean().unstack().dropna()
    if True in w.columns and False in w.columns:
        dt = w[True] - w[False]; out["within"] = (dt.mean(), int((dt > 0).sum()), len(dt))
    return out


def confirmed(t):
    """Tests that pass their rule AND survive Benjamini–Hochberg correction (bootstrap-only tests: CI rule)."""
    t = t.copy(); t["ok"] = t["pass"].astype(str).str.lower().isin(["true", "1"])
    m = t["p"].notna()
    if m.any():
        pv = t.loc[m, "p"].to_numpy(float); n = len(pv); o = np.argsort(pv)
        adj = np.empty(n); r = pv[o] * n / (np.arange(n) + 1)
        adj[o] = np.minimum(np.minimum.accumulate(r[::-1])[::-1], 1)
        t.loc[m, "p_bh"] = adj
        t.loc[m, "ok"] = t.loc[m, "ok"] & (t.loc[m, "p_bh"] < 0.05)
    return t[t["ok"]]


def fmt(df, digits=3):
    return df.style.format(precision=digits, thousands=",", na_rep="—")


@st.cache_data(show_spinner=False)
def _league_tables(folder, names):
    out = {}
    for f in names:
        t = pd.read_csv(os.path.join(folder, f))
        q1, q2 = t["pressing_index"].quantile([1 / 3, 2 / 3])
        t["shape"] = np.where(t["pressing_index"] >= q2, "High press", np.where(t["pressing_index"] <= q1, "Low block", "Mid block"))
        pc = t["possession_control"].astype(str).str.lower().isin(["true", "1"])
        t["tactic"] = t["shape"] + " + " + np.where(pc, "Possession control", "Direct build-up")
        ps = t.groupby("team")["pass_share_tw"].mean(); lo_, hi_ = ps.quantile([1 / 3, 2 / 3])
        t["opp_group"] = t["opponent"].map(ps).map(lambda x: "possession-dominant" if x >= hi_ else ("low-possession" if x <= lo_ else "balanced"))
        t["is_home"] = t["is_home"].astype(str).str.lower().isin(["true", "1"])
        out[f[len("team_match_"):-4].replace("_", " ")] = t
    return out

@st.cache_data(show_spinner=False)
def _effects(folder, names):
    tabs = _league_tables(folder, names)
    D = pd.concat([t.assign(team=lg + " | " + t["team"]) for lg, t in tabs.items()], ignore_index=True).dropna(subset=["npxgd_resid"])
    D["r_for"] = D["npxg"] - D["exp_npxg"]; D["r_ag"] = D["npxg_conceded"] - D["exp_npxg_conceded"]
    for c in ["npxgd_resid", "r_for", "r_ag"]:
        D[c + "_d"] = D[c] - D.groupby("team")[c].transform("mean")
    rows = []
    for g in ["overall", "possession-dominant", "balanced", "low-possession"]:
        d = D if g == "overall" else D[D["opp_group"] == g]
        for tac, x in d.groupby("tactic"):
            if len(x) >= 15:
                rest = d[d["tactic"] != tac]
                rows.append({"opp_group": g, "tactic": tac, "n": len(x),
                             "advantage": x["npxgd_resid_d"].mean() - rest["npxgd_resid_d"].mean(),
                             "for": x["r_for_d"].mean(), "against": x["r_ag_d"].mean()})
    return pd.DataFrame(rows)



def suggest_for(tabs, eff, league, me, opp):
    """Match Planner suggestion: best tactic against the opponent's style, among tactics the team plays (>= 10%)."""
    T = tabs[league]; mine = T[T["team"] == me]
    share = mine["tactic"].value_counts(normalize=True)
    regular = share.index[0]; allowed = list(share[share >= 0.10].index)
    ps = T.groupby("team")["pass_share_tw"].mean(); lo_, hi_ = ps.quantile([1 / 3, 2 / 3])
    og = "possession-dominant" if ps[opp] >= hi_ else ("low-possession" if ps[opp] <= lo_ else "balanced")
    cand = eff[(eff["opp_group"] == og) & eff["tactic"].isin(allowed)]
    if cand.empty:
        cand = eff[(eff["opp_group"] == "overall") & eff["tactic"].isin(allowed)]
    suggested = cand.sort_values("advantage", ascending=False).iloc[0]["tactic"] if len(cand) else regular
    return suggested, regular, allowed, og

if not os.path.isdir(RES):
    st.error(f"No `results` folder found in `{PROJECT}`. Open ⚙️ Settings in the sidebar and paste the path of the "
             "TACTIX-AI folder created by the notebook.")
    st.stop()

# ------------------------------------------------------------------------------------------------------------
# 1. Start here
# ------------------------------------------------------------------------------------------------------------
if page == '🏁 Start here':
    hero("⚽ TACTIX-AI", "Pick your team and your opponent — TACTIX-AI suggests the tactic, shows why, and finds the players who fit it. "
         "Verified on real matches from five European competitions.")
    REP = os.path.join(PROJECT, "replication")
    svr = load(REP, "suggested_vs_regular_summary.csv") if os.path.isdir(REP) else None
    r1 = load(REP, "R1_replication.csv") if os.path.isdir(REP) else None
    sug = load(REP, "suggestions_by_opponent_type.csv") if os.path.isdir(REP) else None
    c = st.columns(4)
    if svr is not None:
        r = svr.iloc[0]
        card(c[0], "Suggested tactic beats the regular one", f"{r['advantage (npxGD vs expectation)']:+.2f}",
             f"better chance balance per match · p = {r['permutation p']:.4f}", "#2A9D8F")
        card(c[1], "Win rate with the suggestion", f"{r['win rate suggested']:.0%}", f"vs {r['win rate regular']:.0%} with the regular tactic", "#A50044")
        card(c[2], "Verified on real matches", f"{int(r['matches suggested'] + r['matches regular']):,}",
             "five competitions · suggestions made from the other leagues", "#1F4E9E")
    else:
        card(c[0], "Matches analysed", "380", "La Liga 2015/16 (main case)", "#1F4E9E")
    if sug is not None:
        per = sug.groupby(["league", "team"])["suggested"].nunique()
        card(c[3], "Adapts to the opponent", f"{(per > 1).mean():.0%}", "of teams get different tactics for different opponents", "#6D597A")
    else:
        ver = load(RES, "verification_pass_fail.csv")
        if ver is not None:
            card(c[3], "Quality checks passed", f"{int((ver['result'] == 'PASS').sum())} / {len(ver)}", "automatic checks of the whole run", "#6D597A")
    what("TACTIX-AI turns match data into decisions a coach can use: how teams play, which tactic to choose against a specific "
         "opponent, why, and which players suit it. Every number comes from real matches; the tactic suggestions were tested "
         "on matches the system had never seen.")
    st.subheader("🧭 How it works")
    steps = [("📥", "1. Collect", "Every action of five leagues"), ("📐", "2. Measure", "Pressing, possession, chances, threats"),
             ("🤖", "3. Explain", "Models + SHAP show what drives results"), ("🧭", "4. Suggest", "A tactic for each opponent"),
             ("✅", "5. Verify", "Tested on unseen leagues"), ("🔎", "6. Scout", "Players who fit the tactic"),
             ("📋", "7. Decide", "Match Planner & Decision Card")]
    cols = st.columns(len(steps))
    for col, (ico, t, d) in zip(cols, steps):
        col.markdown(f'<div class="step"><div class="ico">{ico}</div><b>{t}</b><br><small>{d}</small></div>', unsafe_allow_html=True)
    st.subheader("🏆 Main findings")
    found = []
    if svr is not None:
        r = svr.iloc[0]
        found.append(("Suggested vs regular", f"**Teams did better with TACTIX-AI’s suggested tactic than with their regular tactic**: "
                      f"{r['advantage (npxGD vs expectation)']:+.2f} per match (range {r['CI low']:+.2f} to {r['CI high']:+.2f}), won "
                      f"**{r['win rate suggested']:.0%}** instead of {r['win rate regular']:.0%}, and earned {r['points suggested']:.2f} "
                      f"instead of {r['points regular']:.2f} points per match."))
    if sug is not None:
        per = sug.groupby(["league", "team"])["suggested"].nunique()
        found.append(("Adapts", f"**The suggestion adapts to the opponent**: it changes for {(per > 1).mean():.0%} of teams and differs from "
                      f"the team’s habit in {(sug['suggested'] != sug['regular']).mean():.0%} of cases."))
    if r1 is not None and r1["league"].str.startswith("POOLED").any():
        x = r1[r1["league"].str.startswith("POOLED")].iloc[0]
        found.append(("Replicated", f"**High press + Possession control works across leagues**: {x['effect (npxGD)']:+.2f} per match "
                      f"(range {x['CI low']:+.2f} to {x['CI high']:+.2f}) in four leagues that were not used to choose it; win rate "
                      f"{x['win rate played']:.0%} vs {x['win rate not']:.0%}."))
    bat = load(REP, "validation_battery.csv") if os.path.isdir(REP) else None
    if bat is not None:
        d_ = bat[bat["note"] != "descriptive"]
        found.append(("Validated", f"**Not luck, and more is better**: {int(d_['pass after correction'].sum())} validation tests passed, including "
                      "a permutation test, a dose–response test and a split-season test."))
    here = os.path.dirname(os.path.abspath(__file__))
    for o in [os.path.join(os.path.dirname(PROJECT), "Scouting_Model", "scout_output_5leagues"), os.path.join(here, "Scouting_Model", "scout_output_5leagues"),
              os.path.join(os.path.dirname(PROJECT), "Scouting_Model", "scout_output"), os.path.join(here, "Scouting_Model", "scout_output")]:
        sv = load(o, "scout_validation_loto.csv")
        if sv is not None:
            nsig = int((sv["p_perm_two_sided"] < 0.05).sum()) if "p_perm_two_sided" in sv else 0
            found.append(("Scouting", f"**Scouting finds players who fit the tactic**: tested on {int(sv['n_teams'].max())} teams, the "
                          f"profiles recognise unseen teams' players in {int((sv['spearman_rho'] > 0).sum())} of {len(sv)} tactics"
                          + (f", significantly in {nsig} of {len(sv)}." if nsig else ".")))
            break
    if not found:
        fin = load(RES, "final_findings.csv")
        if fin is not None:
            found = [(r_["id"], r_["finding"]) for _, r_ in fin.iterrows()]
    for t, f in found:
        box("says", t, f)
    st.info("👉 Start with **🧭 Match Planner** in the sidebar: pick your team and an opponent.")
    st.caption("New to football data? Open 📖 Jargon buster in the sidebar at any time.")

elif page == '🏟️ Team Explorer':
    hero("🏟️ Team Explorer", "Compare how any two teams played over the whole season.")
    what("Each team gets a set of numbers describing its style: how much it attacks, how much it has the ball, how hard "
         "it presses. Pick two teams and choose which numbers to compare.")
    prof = table(RES, "team_season_profile.csv")
    if prof is not None:
        teams = sorted(prof["team"])
        c1, c2 = st.columns(2)
        a = c1.selectbox("🔴 Team A", teams, index=teams.index(HOME) if HOME in teams else 0)
        b = c2.selectbox("🔵 Team B", teams, index=teams.index(RIVAL) if RIVAL in teams else min(1, len(teams) - 1))
        METRICS = {"points": "Points per match", "npxg": "Chance quality created (npxG)",
                   "npxg_conceded": "Chance quality conceded (npxG)", "pass_share": "Share of passes (possession)",
                   "prog_actions": "Forward-moving actions", "final_third_entries": "Entries into the final third",
                   "box_entries": "Entries into the penalty box", "key_passes": "Passes leading to a shot",
                   "through_balls": "Through balls", "crosses": "Crosses", "verticality": "Directness",
                   "ft_wide_share": "Attacks down the wings (share)", "ppda_season": "PPDA (lower = presses harder)",
                   "def_height": "How high up the pitch it defends (m)",
                   "pressures_per_100_opp_passes": "Pressures per 100 opponent passes", "counter_npxg": "Counter-attack chances"}
        LOWER_BETTER = {"npxg_conceded", "ppda_season"}
        cols = [m for m in METRICS if m in prof.columns]
        chosen = st.multiselect("Numbers to compare", cols, default=cols[:10], format_func=lambda m: METRICS[m])
        if chosen:
            p = prof.set_index("team")
            k = st.columns(4)
            for i, (m, colr) in enumerate([("points", TEAM_COLORS[HOME]), ("npxg", "#2A9D8F"),
                                           ("npxg_conceded", "#E63946"), ("pass_share", "#6D597A")]):
                if m in p.columns:
                    card(k[i], METRICS[m], f"{p.loc[a, m]:.2f} vs {p.loc[b, m]:.2f}", f"{a} vs {b} · league {p[m].mean():.2f}", colr)
            pct = p[chosen].rank(pct=True)
            for m in chosen:
                if m in LOWER_BETTER:
                    pct[m] = 1 - pct[m] + 1 / len(p)
            long = pd.DataFrame({"measure": [METRICS[m] for m in chosen] * 2,
                                 "league percentile": list(pct.loc[a]) + list(pct.loc[b]),
                                 "team": [a] * len(chosen) + [b] * len(chosen)})
            fig = px.line_polar(long, r="league percentile", theta="measure", color="team", line_close=True,
                                range_r=[0, 1], color_discrete_sequence=[TEAM_COLORS.get(a, "#A50044"), TEAM_COLORS.get(b, "#1F4E9E")])
            fig.update_traces(fill="toself", opacity=0.55)
            st.plotly_chart(fig, use_container_width=True)
            read("Each spoke is one number, turned into a league ranking from 0 (worst of 20 teams) to 1 (best). A bigger "
                 "shape means the team ranks higher on more things. For 'chances conceded' and PPDA the scale is flipped, so "
                 "outer = better defending / harder pressing.")
            best = pct.loc[a].sort_values(ascending=False).head(3).index
            says(f"**{a}** stands out most in: " + ", ".join(METRICS[m] for m in best) + ". "
                 f"**{b}** stands out most in: " + ", ".join(METRICS[m] for m in pct.loc[b].sort_values(ascending=False).head(3).index) + ".")
            rows = []
            for m in chosen:
                rank = p[m].rank(ascending=m in LOWER_BETTER, method="min")
                rows.append({"number": METRICS[m], a: p.loc[a, m], b: p.loc[b, m], "league average": p[m].mean(),
                             f"{a} rank (1 = best)": int(rank[a]), f"{b} rank (1 = best)": int(rank[b])})
            with st.expander("📊 See the exact numbers"):
                st.dataframe(fmt(pd.DataFrame(rows)), hide_index=True, use_container_width=True)
        tm = table(RES, "team_match_master.csv")
        if tm is not None:
            st.subheader(f"📈 {a}, match by match")
            opts = {"npxg": "Chance quality created (npxG)", "npxg_conceded": "Chance quality conceded",
                    "pass_share": "Share of passes", "ppda_tw": "PPDA (lower = presses harder)",
                    "def_height_tw": "How high it defended (m)"}
            metric = st.selectbox("Number", list(opts), format_func=lambda m: opts[m])
            t = tm[tm["team"] == a].sort_values("match_date")
            fig = px.line(t, x="match_date", y=metric, markers=True, hover_data=["opponent", "result"],
                          labels={metric: opts[metric], "match_date": "Match date"},
                          color_discrete_sequence=[TEAM_COLORS.get(a, "#1F4E9E")])
            st.plotly_chart(fig, use_container_width=True)
            read("Each dot is one match. Hover over a dot to see the opponent and the result (W = win, D = draw, L = loss).")

# ------------------------------------------------------------------------------------------------------------
# 3. Pressing Styles
# ------------------------------------------------------------------------------------------------------------
elif page == '🛡️ Pressing Styles':
    hero("🛡️ Pressing Styles", "How hard, and how high up the pitch, did each team defend?")
    what("When a team loses the ball it can **press** (chase the ball near the opponent's goal), defend in the **middle**, "
         "or **sit deep** near its own goal. We measured this in every match with two numbers — how many passes the "
         "opponent was allowed (PPDA) and how far up the pitch the team made its defensive actions — and sorted each "
         "match into 🔴 High press, 🟠 Mid block or 🟢 Low block.")
    bl = table(RES, "block_labels_team_match.csv")
    if bl is not None:
        teams = ["All teams"] + sorted(bl["team"].unique())
        t = st.selectbox("Highlight a team", teams, index=teams.index(HOME) if HOME in teams else 0)
        d = bl.copy()
        d["team shown"] = "other teams" if t == "All teams" else d["team"].where(d["team"] == t, "other teams")
        fig = px.scatter(d, x="ppda_tw", y="def_height_tw", color="block", color_discrete_map=STYLE_COLORS,
                         symbol="team shown" if t != "All teams" else None, log_x=True,
                         hover_data=["team", "match_id", "pressing_index"], opacity=0.75,
                         labels={"ppda_tw": "PPDA  ← presses harder        presses less →",
                                 "def_height_tw": "How high up the pitch it defended (metres from own goal)", "block": "Style"})
        st.plotly_chart(fig, use_container_width=True)
        read("Each dot is one team in one match. **Top-left** = pressed hard and high (🔴). **Bottom-right** = sat deep and "
             "let the opponent pass (🟢).")
        share = pd.crosstab(bl["team"], bl["block"], normalize="index")
        if t != "All teams" and t in share.index:
            s = share.loc[t].sort_values(ascending=False)
            c = st.columns(len(s))
            for col, (style, v) in zip(c, s.items()):
                card(col, f"{t}: {style}", f"{v:.0%}", "of its matches", STYLE_COLORS.get(style, "#9E9E9E"))
            says(f"**{t}** played a **{s.index[0].lower()}** most often ({s.iloc[0]:.0%} of its matches).")
        long = share.reset_index().melt(id_vars="team", var_name="style", value_name="share")
        order = share.sort_values("High press", ascending=False).index.tolist() if "High press" in share else None
        fig2 = px.bar(long, x="share", y="team", color="style", orientation="h", color_discrete_map=STYLE_COLORS,
                      category_orders={"team": order} if order else None, labels={"share": "Share of matches"})
        st.plotly_chart(fig2, use_container_width=True)
        warn("These styles are estimated from where on-ball actions happened. The data has no tracking of every player, "
             "so we cannot see the team's actual shape.")

# ------------------------------------------------------------------------------------------------------------
# 4. Players
# ------------------------------------------------------------------------------------------------------------
elif page == '🏃 Players':
    hero("🏃 Players", "Find the league's top performers in any skill.")
    what("Every player's actions are counted **per 90 minutes**, so a substitute who played 900 minutes can be compared "
         "fairly with a regular who played 3,000.")
    pp = table(DATA, "player_profiles.csv")
    if pp is not None:
        NICE = {"xa_p90": "Chance creation (xA)", "xg_p90": "Shooting quality (xG)", "shots_p90": "Shots",
                "key_passes_p90": "Passes leading to a shot", "progressive_passes_p90": "Forward passes",
                "progressive_carries_p90": "Forward runs with the ball", "dribbles_p90": "Dribbles",
                "defensive_actions_p90": "Defensive actions", "pressures_p90": "Pressures on opponents",
                "def_score_p90": "Defensive score", "crosses_p90": "Crosses"}
        p90 = [c for c in NICE if c in pp.columns]
        c1, c2, c3 = st.columns(3)
        teams = ["All teams"] + sorted(pp["team"].dropna().unique())
        team = c1.selectbox("Team", teams)
        min_min = c2.slider("Minimum minutes played", 0, 3400, 900, step=100)
        metric = c3.selectbox("Skill", p90, format_func=lambda m: NICE[m])
        d = pp[pp["minutes"] >= min_min]
        if team != "All teams":
            d = d[d["team"] == team]
        top = d.sort_values(metric, ascending=False).head(15)
        if len(top):
            fig = px.bar(top, x=metric, y="player", orientation="h", color="team", hover_data=["position", "minutes"],
                         labels={metric: NICE[metric] + " per 90 minutes", "player": ""},
                         color_discrete_map=TEAM_COLORS)
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
            says(f"The leader in **{NICE[metric].lower()}** is **{top.iloc[0]['player']}** ({top.iloc[0]['team']}), "
                 f"with {top.iloc[0][metric]:.2f} per 90 minutes.")
        with st.expander("📊 Full table"):
            st.dataframe(fmt(d[["player", "team", "position", "minutes"] + p90].sort_values(metric, ascending=False)),
                         hide_index=True, use_container_width=True)
        warn("These are statistics from one season. Ranking high in one skill does not mean a player is better overall.")

# ------------------------------------------------------------------------------------------------------------
# 5. Rival & Threats
# ------------------------------------------------------------------------------------------------------------
elif page == '🎯 Rival & Threats':
    hero("🎯 Rival & Threats", "Know the opponent: where is it strong, where does it concede, and who is dangerous?")
    thr = table(RES, "threat_scores_all_players.csv")
    teams = sorted(thr["team"].unique()) if thr is not None else [RIVAL]
    rival = st.selectbox("Team", teams, index=teams.index(RIVAL) if RIVAL in teams else 0)
    if rival == RIVAL:
        rp = table(RES, "rival_profile.csv")
        if rp is not None:
            st.subheader(f"💪 {RIVAL}: strengths and weaknesses")
            what("Every number of Real Madrid is ranked against the other 19 teams. **Top 5** = a strength, **bottom 5** = a weakness.")
            s = rp[rp["verdict"] == "Strength"]["metric"].tolist()
            w = rp[rp["verdict"] == "Weakness"]["metric"].tolist()
            c1, c2 = st.columns(2)
            card(c1, "Strengths (top 5 of 20)", str(len(s)), ", ".join(s[:5]), "#2A9D8F")
            card(c2, "Weaknesses (bottom 5 of 20)", str(len(w)), ", ".join(w) if w else "none — no obvious weak spot", "#E63946")
            with st.expander("📊 Full ranking"):
                st.dataframe(rp, hide_index=True, use_container_width=True)
        zones = table(RES, "rival_zones_exploited.csv")
        if zones is not None:
            st.subheader("🗺️ Where do opponents attack Real Madrid from?")
            fig = px.bar(zones, x="channel", y="ratio", color="action", barmode="group",
                         hover_data=["share_vs_rival", "league_share", "exploited"],
                         labels={"ratio": "Compared with the league (1 = same as average)", "channel": "Lane of the pitch"})
            fig.add_hline(y=1, line_dash="dash")
            st.plotly_chart(fig, use_container_width=True)
            read("Bars **above the dashed line** mean opponents attacked from that lane more than they usually do against "
                 "other teams.")
            n_exp = int(zones["exploited"].sum())
            says("No lane stands out clearly — Real Madrid had no obvious weak zone." if n_exp == 0 else
                 f"{n_exp} lane(s) were attacked clearly more than average.")
    if thr is not None:
        t = thr[thr["team"] == rival].sort_values("threat_score", ascending=False)
        st.subheader(f"🔥 {rival}'s most dangerous players")
        what("Two ways to measure danger: **threat score** = how dangerous a player is *per minute on the pitch*; "
             "**share of team output** = how much of the team's chances he produced *over the season*.")
        if len(t):
            top_rate = t.iloc[0]; top_vol = t.sort_values("team_attacking_share", ascending=False).iloc[0]
            c1, c2 = st.columns(2)
            card(c1, "Most dangerous per minute", top_rate["player"], f"threat score {top_rate['threat_score']:.2f}", "#E63946")
            card(c2, "Biggest share of team output", top_vol["player"], f"{top_vol['team_attacking_share']:.0%} of chances created + taken", "#6D597A")
            fig = px.scatter(t, x="threat_score", y="team_attacking_share", size="minutes", text="player",
                             hover_data=["threat_types", "npxg_p90", "xa_p90"], color="pos_group",
                             labels={"threat_score": "Danger per minute (threat score)",
                                     "team_attacking_share": "Share of the team's chances", "pos_group": "Position"})
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)
            read("**Top-right** players are both dangerous per minute and important over the season. Bubble size = minutes played.")
    show_fig("rival_pass_network.png", "Real Madrid's passing network: bigger dots = more involved players; lines = frequent passes")

# ------------------------------------------------------------------------------------------------------------
# 6. Models & XAI
# ------------------------------------------------------------------------------------------------------------
elif page == '🤖 Models & XAI':
    hero("🤖 Models & XAI", "Can a computer predict what happens next — and can it tell us why?")
    what("We trained five machine-learning models to predict three things: **will a pass succeed?**, **will a possession "
         "end in losing the ball?** and **will a possession create a good chance?** They learned from the first part of the "
         "season and were tested on the last matches, which they had never seen.")
    ms = table(DATA, "model_summary.csv")
    if ms is not None:
        task = st.selectbox("Prediction task", list(ms["task"].unique()))
        d = ms[ms["task"] == task].copy()
        real = d[~d["model"].str.contains("baseline", case=False)]
        if len(real):
            best = real.sort_values("roc_auc", ascending=False).iloc[0]
            c = st.columns(3)
            card(c[0], "Best model", best["model"], task, "#1F4E9E")
            card(c[1], "Score (ROC-AUC)", f"{best['roc_auc']:.3f}", "0.5 = coin flip · 1.0 = perfect", "#6D597A")
            card(c[2], "Rating", auc_label(best["roc_auc"]).split(" ", 1)[1], "compared with guessing",
                 "#2A9D8F" if best["roc_auc"] >= 0.8 else "#F4A261" if best["roc_auc"] >= 0.6 else "#E63946")
        fig = px.bar(d, x="model", y="roc_auc", range_y=[0.4, 1.0], text_auto=".3f", color="model",
                     labels={"roc_auc": "Score (ROC-AUC)", "model": ""})
        fig.add_hline(y=0.5, line_dash="dash", annotation_text="coin flip")
        st.plotly_chart(fig, use_container_width=True)
        read("Taller bars = better predictions. The dashed line is guessing. The 'Majority baseline' always predicts the most "
             "common answer — a model is only useful if it beats it.")
        with st.expander("📊 All scores"):
            st.dataframe(fmt(d), hide_index=True, use_container_width=True)
    st.subheader("🔬 Why did the model predict that? (SHAP)")
    what("SHAP opens the 'black box': it shows which pieces of information the model relied on most.")
    key = st.selectbox("Model", {"Pass success": "pass_completion_b_pre_pass_features_",
                                 "Losing the ball": "turnover_first_n_window_",
                                 "Creating a good chance": "dangerous_attack_first_n_window_"}.items(), format_func=lambda kv: kv[0])[1]
    kind = st.radio("View", ["bar", "beeswarm", "dependence", "local"], horizontal=True,
                    format_func=lambda k: {"bar": "📊 Most important", "beeswarm": "🐝 Direction", "dependence": "📈 One input",
                                           "local": "🔎 One example"}[k])
    show_fig(f"shap_{kind}_{key}.png")
    read({"bar": "Longer bar = the model relies on that input more.",
          "beeswarm": "Each dot is one case. Dots to the right pushed the prediction up; colour shows whether the input value was high (red) or low (blue).",
          "dependence": "How the model's output changes as one input grows.",
          "local": "For one single case: which inputs pushed this particular prediction up (right) or down (left)."}[kind])
    warn("SHAP explains what the **model** uses. It does not prove that something causes a result on the pitch.")

# ------------------------------------------------------------------------------------------------------------
# 7. Validation
# ------------------------------------------------------------------------------------------------------------
elif page == '🧪 Validation':
    hero("🧪 Validation", "The honest part: do these tactics really hold up when tested?")
    tab1, tab2, tab3 = st.tabs(["📐 Which tactics go with better results?", "⏪ The backtest", "🧮 Expectation & star players"])
    with tab1:
        what("For each tactic we asked: in matches where a team used it, did the team do **better than expected** against "
             "that opponent? Each team is compared **only with itself**, so strong teams don't make a tactic look good.")
        se = table(RES, "strategy_effects.csv")
        if se is not None:
            c1, c2 = st.columns(2)
            subset = c1.selectbox("Against which opponents?", list(se["subset"].unique()))
            model = c2.selectbox("Comparison", list(se["model"].unique()))
            d = se[(se["subset"] == subset) & (se["model"] == model) & (se["outcome"] == se["outcome"].iloc[0])].copy()
            d["result"] = pd.cut(d["ci_low"], [-99, 0, 99], labels=["unclear", "better"]).astype(str)
            d.loc[d["ci_high"] < 0, "result"] = "worse"
            colors = {"better": "#2A9D8F", "worse": "#E63946", "unclear": "#9E9E9E"}
            fig = go.Figure()
            for res_, grp in d.groupby("result"):
                fig.add_trace(go.Scatter(x=grp["effect"], y=grp["strategy"], mode="markers", name=res_,
                                         marker=dict(size=14, color=colors[res_]),
                                         error_x=dict(type="data", symmetric=False, array=grp["ci_high"] - grp["effect"],
                                                      arrayminus=grp["effect"] - grp["ci_low"], color=colors[res_])))
            fig.add_vline(x=0, line_dash="dash")
            fig.update_layout(xaxis_title="Chance difference vs expectation, per match", height=430)
            st.plotly_chart(fig, use_container_width=True)
            read("Dots right of the dashed line = better than expected; left = worse. The line through each dot is the "
                 "uncertainty range. 🟢 = clearly better, 🔴 = clearly worse, ⚪ = unclear (the range crosses zero).")
            good = d[d["result"] == "better"]["strategy"].tolist(); bad = d[d["result"] == "worse"]["strategy"].tolist()
            says((f"Clearly better: **{', '.join(good)}**. " if good else "No tactic was clearly better. ") +
                 (f"Clearly worse: **{', '.join(bad)}**." if bad else ""))
            warn("These tactics *go together with* better or worse results. A team that is already dominating a match tends "
                 "to press high and keep the ball, so pressing might be a sign of dominance rather than its cause.")
    with tab2:
        what("The backtest replays the season. Before each match, the system recommended a tactic using **only earlier "
             "matches**. Afterwards we checked: when teams followed the advice, did they do better?")
        sens = table(RES, "backtest_sensitivity.csv")
        if sens is not None:
            base = sens.iloc[0]
            c = st.columns(3)
            card(c[0], "Recommendations tested", f"{int(base['with_recommendation'])}", "one per match, before kick-off", "#1F4E9E")
            card(c[1], "Followed / not followed", f"{int(base['followed'])} / {int(base['not_followed'])}", "by the teams", "#6D597A")
            card(c[2], "Advantage when followed", f"{base['diff_followed_minus_not']:+.3f}",
                 f"range {base['diff_ci_low']:+.2f} to {base['diff_ci_high']:+.2f}", "#2A9D8F" if base["diff_followed_minus_not"] > 0 else "#9E9E9E")
            if base["diff_followed_minus_not"] > 0:
                says("Following the recommendations pointed in a **positive direction** (teams did better than expected). "
                     "It is not yet statistically confirmed over one season — more seasons of data would sharpen it. "
                     "The real-match record of the recommended tactic itself is on the 📋 Decision Card page.")
            with st.expander("📊 Same test with different settings"):
                st.dataframe(fmt(sens), hide_index=True, use_container_width=True)
        bt = table(RES, "backtest_all_team_matches.csv")
        if bt is not None:
            teams = sorted(bt["team"].unique())
            team = st.selectbox("Look at one team", teams, index=teams.index(HOME) if HOME in teams else 0)
            d = bt[bt["team"] == team].copy()
            d["advice"] = d["followed"].map({True: "followed", False: "not followed"})
            fig = px.strip(d, x="advice", y="actual_npxgd_resid", color="recommended",
                           hover_data=["match_date", "opponent", "predicted_effect"],
                           labels={"actual_npxgd_resid": "How much better than expected", "advice": ""})
            fig.add_hline(y=0, line_dash="dash")
            st.plotly_chart(fig, use_container_width=True)
            read("Each dot is one match. Above the dashed line = the team did better than expected.")
    with tab3:
        what("Before every match we estimate what each team *should* produce against that opponent. This removes opponent "
             "strength and home advantage before judging any tactic.")
        ex = table(RES, "expectation_model_check.csv")
        if ex is not None:
            st.dataframe(fmt(ex), hide_index=True, use_container_width=True)
            read("Lower error (MAE) = better guess. Our estimate beats both simple guesses.")
        st.subheader("⭐ When the star is quiet, do teammates step up?")
        what("We looked at matches where a team's main attacker had a quiet game and checked whether **his teammates** "
             "produced more (compensated) or less than expected.")
        d = load(RES, "suppression_tests_league_within_team.csv")
        if d is not None:
            r = d.iloc[0]
            card(st.columns(1)[0], "Teammates' output when the star was quiet (all teams)", f"{r['within_team_diff']:+.3f}",
                 f"range {r['ci_low']:+.3f} to {r['ci_high']:+.3f} — below zero means they did NOT compensate", "#6D597A")
        warn("The data cannot see man-marking. A quiet star and quiet teammates may simply mean the opponent defended well overall.")

# ------------------------------------------------------------------------------------------------------------
# 8. Simulation & Game Plans
# ------------------------------------------------------------------------------------------------------------
elif page == '🎲 Simulation & Game Plans':
    hero("🎲 Simulation & Game Plans", "Barcelona vs Real Madrid, played 20,000 times for each tactic.")
    what("The computer replays the match using real Barcelona and Real Madrid attacks, adjusted to this exact match-up, "
         "with realistic randomness. Changing the tactic changes the chances each side creates, and we count how often "
         "each result happens.")
    mc = table(RES, "monte_carlo_scenarios.csv")
    if mc is not None:
        show_conditional = st.toggle("Show 'what if we could stop Ronaldo' scenarios", value=False)
        d = mc if show_conditional else mc[~mc["effect type"].str.contains("CONDITIONAL", case=False)]
        long = d.melt(id_vars="tactic", value_vars=["P(win)", "P(draw)", "P(loss)"], var_name="result", value_name="probability")
        long["result"] = long["result"].map({"P(win)": "Win", "P(draw)": "Draw", "P(loss)": "Loss"})
        fig = px.bar(long, x="probability", y="tactic", color="result", orientation="h",
                     color_discrete_map={"Win": "#2A9D8F", "Draw": "#E9C46A", "Loss": "#E63946"},
                     labels={"probability": "Share of simulated matches", "tactic": ""})
        st.plotly_chart(fig, use_container_width=True)
        read("Each bar is one tactic: green = Barcelona wins, yellow = draw, red = Real Madrid wins. More green = better.")
        est = mc[~mc["effect type"].str.contains("CONDITIONAL", case=False)].sort_values("P(win)", ascending=False)
        if len(est):
            says(f"In the simulations, **{est.iloc[0]['tactic']}** gave Barcelona the most wins ({est.iloc[0]['P(win)']:.0%}), "
                 f"and **{est.iloc[-1]['tactic']}** the fewest ({est.iloc[-1]['P(win)']:.0%}).")
        if show_conditional:
            warn("The Ronaldo scenarios assume he is successfully kept quiet. They show what that would be *worth*, not whether any tactic can achieve it.")
    cand = table(RES, "candidate_game_plans.csv")
    if cand is not None:
        st.subheader("🛠️ Build your own game plan")
        what("A game plan = **how to defend** + **how to attack**. Pick one of each and see how it did.")
        c1, c2 = st.columns(2)
        shape = c1.selectbox("🛡️ How to defend", sorted(cand["defensive shape"].unique()))
        route = c2.selectbox("⚔️ How to attack", sorted(cand["attacking route"].unique()))
        row = cand[(cand["defensive shape"] == shape) & (cand["attacking route"] == route) & (~cand["suppression"])]
        if len(row):
            r = row.iloc[0]
            k = st.columns(4)
            card(k[0], "Barcelona wins", f"{r['P(win)']:.0%}", f"{100 * r['ΔP(win) vs baseline']:+.1f} points vs no change", "#2A9D8F")
            card(k[1], "Draw / Real Madrid wins", f"{r['P(draw)']:.0%} / {r['P(loss)']:.0%}", "", "#6D597A")
            card(k[2], "Chances: created – conceded", f"{r['exp npxG for']:.2f} – {r['exp npxG against']:.2f}", "expected npxG", "#1F4E9E")
            card(k[3], "Strength of evidence", r["evidence tier"], "", TIER_COLORS.get(r["evidence tier"], "#9E9E9E"))
            if not r["feasible for home team"]:
                warn(f"{HOME} rarely played this way (in fewer than 20% of its matches), so this plan is not considered realistic for it.")
            read("**Evidence strength:** 🟢 Supported = clear evidence · 🟠 Suggestive = positive but uncertain · "
                 "⚪ Not supported · 🔴 Unfavourable = evidence points the wrong way.")
        with st.expander("📊 Compare all plans"):
            d = cand[~cand["suppression"]].sort_values("ΔP(win) vs baseline", ascending=False)
            st.dataframe(fmt(d[["game plan", "feasible for home team", "evidence tier", "exp npxG for", "exp npxG against",
                                "P(win)", "P(draw)", "P(loss)", "ΔP(win) vs baseline"]]), hide_index=True, use_container_width=True)
    warn("Simulations are **scenarios**, not predictions of a real future match.")

# ------------------------------------------------------------------------------------------------------------
# 9. Decision Card
# ------------------------------------------------------------------------------------------------------------
elif page == '📋 Decision Card (example)':
    hero("📋 Match Decision Card — worked example", "Barcelona vs Real Madrid: everything a coach needs on one page, with the evidence.")
    what("This is the final output: the recommended plan for Barcelona vs Real Madrid, why it was chosen, and what to watch "
         "out for. Every line is tagged: **[O]** measured in the data · **[M]** model · **[S]** simulation · **[I]** interpretation.")
    try:
        cands = load(RES, "candidate_game_plans.csv")
        if cands is not None:
            est = cands[(~cands["suppression"]) & (cands["feasible for home team"])].sort_values("ΔP(win) vs baseline", ascending=False)
            if len(est):
                sel = est.iloc[0]
                st.markdown(f'<div class="hero" style="padding:1.1rem 1.6rem"><p style="font-size:.95rem">🏆 Recommended tactic for {HOME} vs {RIVAL}</p>'
                            f'<h1 style="font-size:1.9rem">{sel["game plan"]}</h1><p>The best-supported tactic among all realistic options</p></div>',
                            unsafe_allow_html=True)
                st.subheader("🏆 Why this tactic — five pieces of evidence")
                rc = real_match_check(RES)
                eff = load(RES, "strategy_effects.csv")
                hp = None
                if eff is not None:
                    e = eff[(eff["strategy"] == "High press") & (eff["subset"] == "all team-matches") & (eff["model"].str.contains("within"))
                            & (eff["outcome"].str.startswith("npxG difference"))]
                    hp = e.iloc[0] if len(e) else None
                c = st.columns(5)
                card(c[0], "1 · Chosen fairly", "Rule fixed in advance", "realistic for Barcelona · not harmful · biggest gain", "#6D597A")
                card(c[1], "2 · Simulation", f"{sel['P(win)']:.1%} wins", f"{100 * sel['ΔP(win) vs baseline']:+.1f} pts vs no change (20,000 matches)", "#2A9D8F")
                card(c[2], "3 · History: high press", f"{hp['effect']:+.2f}" if hp is not None else "—",
                     f"better than expected per match [{hp['ci_low']:+.2f}, {hp['ci_high']:+.2f}]" if hp is not None else "", "#1F4E9E")
                if rc:
                    a = rc["all"]
                    card(c[3], "4 · Real-match record", f"{a['win_a']:.0%} vs {a['win_b']:.0%} wins",
                         f"when teams played it vs not · {a['diff']:+.2f} better than expected", "#A50044")
                card(c[4], "5 · Validated tools", "Models beat baselines", "expectation & goal models tested on real matches", "#264653")
                if rc:
                    a, v = rc["all"], rc["vs_possession"]
                    says(f"**When teams actually played this plan** in 2015/16 ({a['n_a']} matches), they did **{a['diff']:+.2f}** better than "
                         f"expected (range {a['lo']:+.2f} to {a['hi']:+.2f}) and won **{a['win_a']:.0%}** of them, against {a['win_b']:.0%} "
                         "in other matches." + (f" Comparing each team only with itself gives the same picture: positive for "
                         f"{rc['within'][1]} of {rc['within'][2]} teams." if "within" in rc else ""))
                    warn(f"Against possession-dominant opponents like {RIVAL}, the difference was {v['diff']:+.2f} but uncertain "
                         f"(range {v['lo']:+.2f} to {v['hi']:+.2f}, only {v['n_a']} matches). And the strictest test — following "
                         "pre-match recommendations across the whole season (🧪 Validation) — did not yet show a guaranteed advantage. "
                         "So this is the **best-supported** tactic, not a guaranteed win.")
    except Exception as _err:                     # never let the panel hide the rest of the page
        st.info(f"The evidence panel could not be shown ({type(_err).__name__}: {_err}). The Decision Card below is unaffected.")
    show_fig("match_plan_pitch.png", "The match plan: yellow zone = where to press, arrow = lane to attack, coloured dots = where Real Madrid's threats shoot from")
    chain = load(RES, "why_this_tactic_chain.csv")
    if chain is not None:
        st.subheader("🔗 Why this tactic? Step by step")
        colours = {"Observed": "#1F4E9E", "Model": "#6D597A", "Simulation": "#2A9D8F", "Interpretation": "#A50044"}
        for _, r in chain.iterrows():
            ev_ = str(r["evidence"]).strip()
            st.markdown(f'<div class="box" style="background:#fafafa;border-left:6px solid {colours.get(ev_, "#9E9E9E")}">'
                        f'<b>{md(r["step"])}</b> <small>[{ev_}]</small><br>{md(r["statement"])}</div>', unsafe_allow_html=True)
    card_path = os.path.join(RES, "match_decision_card.md")
    st.subheader("📄 The full Match Decision Card")
    if os.path.exists(card_path):
        with st.container(border=True):
            st.markdown(open(card_path, encoding="utf-8").read())
    else:
        st.warning("`match_decision_card.md` was not found in the results folder — run the notebook (Step 56) first.")

# ------------------------------------------------------------------------------------------------------------
# 10. Replication in four other leagues + validation battery (reads TACTIX-AI/replication, made by TACTIX_Replication.ipynb)
# ------------------------------------------------------------------------------------------------------------
elif page == '🌍 Verification (5 leagues)':
    import re as _re
    REP = os.path.join(PROJECT, "replication")
    hero("🌍 Verification in five leagues", "Do TACTIX-AI’s suggestions work on matches the system has never seen?")
    if not os.path.isdir(REP):
        st.warning("No `TACTIX-AI/replication` folder yet — run `TACTIX_Replication.ipynb` first.")
        st.stop()
    _svr = load(REP, "suggested_vs_regular_summary.csv")
    if _svr is not None:
        r = _svr.iloc[0]
        st.subheader("🧭 Suggested tactic vs regular tactic (the main test)")
        what("For every team and match, TACTIX-AI suggested a tactic for that opponent type — learned **only from the other "
             "leagues** — and we compared the team's matches with the suggested tactic against its matches with its regular tactic.")
        k = st.columns(4)
        card(k[0], "Better chance balance", f"{r['advantage (npxGD vs expectation)']:+.2f}", f"range {r['CI low']:+.2f} to {r['CI high']:+.2f}", "#2A9D8F")
        card(k[1], "Not luck", f"p = {r['permutation p']:.4f}", "within-team permutation test", "#1F4E9E")
        card(k[2], "Win rate", f"{r['win rate suggested']:.0%}", f"vs {r['win rate regular']:.0%} regular", "#A50044")
        card(k[3], "Points per match", f"{r['points suggested']:.2f}", f"vs {r['points regular']:.2f} regular", "#6D597A")
        _by = load(REP, "suggested_vs_regular_by_league.csv")
        if _by is not None:
            st.plotly_chart(px.bar(_by, x="league", y="advantage", color="advantage", color_continuous_scale=["#E9C46A", "#2A9D8F"],
                                   hover_data=["matches"], labels={"advantage": "Advantage of the suggestion", "league": ""}),
                            use_container_width=True)
        st.subheader("🌍 The recommended tactic in four other leagues")
    what("The recommended tactic (High press + Possession control) was fixed from the La Liga analysis, then tested — "
         "unchanged — in four leagues that played **no part** in choosing it. The rules for success were written down "
         "**before** the test was run.")
    r1 = load(REP, "R1_replication.csv")
    if r1 is not None:
        pooled = r1[r1["league"].str.startswith("POOLED")]
        if len(pooled):
            r = pooled.iloc[0]
            c = st.columns(4)
            card(c[0], "Better than expected (4 leagues)", f"{r['effect (npxGD)']:+.2f}",
                 f"npxG difference per match · range {r['CI low']:+.2f} to {r['CI high']:+.2f}",
                 "#2A9D8F" if r["CI low"] > 0 else "#9E9E9E")
            card(c[1], "Win rate with the tactic", f"{r['win rate played']:.0%}", f"vs {r['win rate not']:.0%} without it", "#A50044")
            card(c[2], "Points per match", f"{r['points played']:.2f}", f"vs {r['points not']:.2f} without it", "#1F4E9E")
            card(c[3], "Pre-registered test", "PASSED" if r["CI low"] > 0 else "not passed", "4 independent leagues pooled",
                 "#2A9D8F" if r["CI low"] > 0 else "#E63946")
        per = r1[~r1["league"].str.startswith("POOLED")].copy()
        per["result"] = np.where(per["CI low"] > 0, "clearly better", np.where(per["effect (npxGD)"] > 0, "better (uncertain)", "not better"))
        fig = go.Figure()
        colors = {"clearly better": "#2A9D8F", "better (uncertain)": "#F4A261", "not better": "#E63946"}
        for res_, grp in per.groupby("result"):
            fig.add_trace(go.Scatter(x=grp["effect (npxGD)"], y=grp["league"], mode="markers", name=res_,
                                     marker=dict(size=14, color=colors[res_]),
                                     error_x=dict(type="data", symmetric=False, array=grp["CI high"] - grp["effect (npxGD)"],
                                                  arrayminus=grp["effect (npxGD)"] - grp["CI low"])))
        fig.add_vline(x=0, line_dash="dash")
        fig.update_layout(height=360, xaxis_title="How much better than expected when the tactic was played (npxGD per match)")
        st.plotly_chart(fig, use_container_width=True)
        read("Each dot is one league (La Liga = where the tactic was chosen). Right of the dashed line = better than expected. "
             "The line through a dot is the uncertainty range.")
        pos = int((per[per["role"] == "test"]["effect (npxGD)"] > 0).sum()); ntest = int((per["role"] == "test").sum())
        says(f"The tactic was associated with better results in **{pos} of {ntest}** independent leagues.")
    bat = load(REP, "validation_battery.csv")
    if bat is not None:
        st.subheader("🧪 Validation battery — every pre-registered test")
        directional = bat[bat["note"] != "descriptive"]
        n_pass = int(directional["pass after correction"].sum())
        card(st.columns(1)[0], "Tests passed (after correcting for running many tests)", f"{n_pass} of {len(directional)}",
             "every test is listed below — nothing hidden", "#6D597A")
        for _, r in bat.iterrows():
            ok = bool(r["pass after correction"]) and r["note"] != "descriptive"
            kind = "says" if ok else "read"
            icon = "✅" if ok else ("ℹ️" if r["note"] == "descriptive" else "▫️")
            box(kind, f"{icon} {r['test']}", f"{r['question']} Result **{r['estimate']:+.3f}** "
                f"(range {r['CI low']:+.3f} to {r['CI high']:+.3f}). Rule: {r['success rule (fixed in advance)']}.")
        img = os.path.join(REP, "dose_response.png")
        if os.path.exists(img):
            st.image(img, caption="Dose-response: results by level of pressing + possession", use_container_width=True)
    r2 = load(REP, "R2_within_match.csv")
    if r2 is not None:
        with st.expander("⏱️ Within-match analysis (15-minute windows)"):
            what("Does pressing harder in one 15-minute period go with a better chance balance in the **next** period of the "
                 "same match? Comparing a team with itself inside one match removes team and opponent strength.")
            col = [c for c in r2.columns if "pressing (1 SD) → next" in c]
            if col:
                def _num(v):
                    x = [float(t) for t in _re.findall(r"-?\d+\.\d+(?:e-?\d+)?", str(v))]
                    return x[:3] if len(x) >= 3 else [np.nan] * 3
                vals = r2[col[0]].apply(_num)
                tab = pd.DataFrame({"league / sample": r2["league"], "effect": vals.str[0], "range low": vals.str[1], "range high": vals.str[2]})
                st.dataframe(fmt(tab), hide_index=True, use_container_width=True)
    gains = load(REP, "matchup_gains_all.csv"); real = load(REP, "suggested_tactic_real_matches.csv")
    if gains is not None or real is not None:
        st.subheader("🏆 Best match-ups")
        what("Examples of where the suggested tactic helps most. The **proof** is the comparison across all matches above; "
             "these lists show what it means for individual teams.")
        tab_a, tab_b = st.tabs(["📈 Biggest expected gains", "🏅 Best real records"])
        with tab_a:
            if gains is not None:
                lg_opts = ["All leagues"] + sorted(gains["league"].unique())
                lg_pick = st.selectbox("League", lg_opts, key="bm_league")
                g_ = gains[gains["suggested tactic"] != gains["regular tactic"]]
                if lg_pick != "All leagues":
                    g_ = g_[g_["league"] == lg_pick]
                g_ = g_.sort_values("win gain (pts)", ascending=False).head(15).copy()
                g_["match-up (home)"] = g_["team"] + " vs " + g_["opponent"]
                g_["change of tactic"] = g_["regular tactic"] + " → " + g_["suggested tactic"]
                g_["win chance"] = [f"{a:.0f}% → {b:.0f}%" for a, b in zip(g_["win % regular"], g_["win % suggested"])]
                st.dataframe(g_[["league", "match-up (home)", "change of tactic", "win chance", "win gain (pts)"]].round(1),
                             hide_index=True, use_container_width=True)
                if len(g_):
                    top = g_.iloc[0]
                    says(f"Biggest gain: **{top['match-up (home)']}** — switching to **{top['suggested tactic']}** raises the "
                         f"estimated win chance from {top['win % regular']:.0f}% to **{top['win % suggested']:.0f}%**.")
                read("Win chances are model estimates for a home match (same calculation as the 🧭 Match Planner).")
        with tab_b:
            if real is not None:
                rec = real.groupby(["league", "team"]).agg(matches=("result", "size"), wins=("result", lambda r: int((r == "W").sum())),
                                                           points_per_match=("points", "mean"),
                                                           performance=("performance vs expectation", "mean")).reset_index()
                rec = rec[rec["matches"] >= 8].sort_values("performance", ascending=False).head(12)
                fig = px.bar(rec.iloc[::-1], x="points_per_match", y="team", orientation="h", color="league",
                             hover_data=["matches", "wins", "performance"],
                             labels={"points_per_match": "Points per match with the suggested tactic", "team": ""})
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(fmt(rec.rename(columns={"points_per_match": "points / match", "performance": "performance vs expectation"})),
                             hide_index=True, use_container_width=True)
                read("Teams with at least 8 real matches played with the suggested tactic, sorted by how much better than "
                     "expected they performed in those matches.")
    warn("These are associations: teams that play this way do better, consistently across leagues. They do not prove that "
         "the tactic alone causes the wins.")

# ------------------------------------------------------------------------------------------------------------
# 11. Match Planner — any team, any opponent (reads TACTIX-AI/replication)
# ------------------------------------------------------------------------------------------------------------
elif page == '🧭 Match Planner':
    from math import factorial as _fact
    REP = os.path.join(PROJECT, "replication")
    hero("🧭 Match Planner", "Pick your team and your opponent — TACTIX-AI suggests the tactic that gives you the best chance to win.")
    files = sorted(f for f in (os.listdir(REP) if os.path.isdir(REP) else []) if f.startswith("team_match_") and f.endswith(".csv"))
    if not files:
        st.warning("No league tables found in `TACTIX-AI/replication` — run `TACTIX_Replication.ipynb` first.")
        st.stop()

    tabs = _league_tables(REP, tuple(files)); eff = _effects(REP, tuple(files))
    c1, c2, c3, c4 = st.columns(4)
    names = list(tabs)
    league = c1.selectbox("🏆 League", names, index=names.index("La Liga") if "La Liga" in names else 0)
    T = tabs[league]; teams = sorted(T["team"].unique())
    me = c2.selectbox("⚽ Your team", teams, index=teams.index(HOME) if HOME in teams else 0)
    others = [t for t in teams if t != me]
    opp = c3.selectbox("🆚 Opponent", others, index=others.index(RIVAL) if RIVAL in others else 0)
    home = c4.radio("🏟️ Venue", ["Home", "Away"], horizontal=True) == "Home"

    suggested, regular, allowed, og = suggest_for(tabs, eff, league, me, opp)

    st.markdown(f'<div class="hero" style="padding:1rem 1.6rem"><p>🧭 Suggested tactic for {me} vs {opp} ({og} opponent)</p>'
                f'<h1 style="font-size:1.8rem">{suggested}</h1>'
                f'<p>Chosen for this type of opponent from the tactics {me} can play</p></div>', unsafe_allow_html=True)

    # ---- opponent zones & passing hubs ----
    prof = load(REP, "opponent_profiles.csv")
    if prof is not None and len(prof[(prof["league"] == league) & (prof["team"] == opp)]):
        pr = prof[(prof["league"] == league) & (prof["team"] == opp)].iloc[0]
        LN = ["Left wing", "Left half-space", "Centre", "Right half-space", "Right wing"]
        st.subheader(f"🛡️ How {opp} attacks — and what to take away")
        what(f"Where {opp} plays in the final third (its **favourite lane**) and the three players who make most of its "
             f"passes (its **passing hubs**). Taking these away is the plan against them.")
        zl = pd.DataFrame({"lane": LN * 2, "share": [pr[f"share_{l}"] for l in LN] + [pr[f"league_{l}"] for l in LN],
                           "": [opp] * 5 + ["league average"] * 5})
        k = st.columns([3, 2])
        k[0].plotly_chart(px.bar(zl, x="lane", y="share", color="", barmode="group",
                                 color_discrete_sequence=["#E63946", "#BBBBBB"],
                                 labels={"share": "Share of final-third play", "lane": ""}), use_container_width=True)
        hubs = [h for h in [pr["hub_1"], pr["hub_2"], pr["hub_3"]] if isinstance(h, str) and h]
        with k[1]:
            card(st, "🚧 Protect this lane", pr["favourite_lane"], f"{pr['share_' + pr['favourite_lane']]:.0%} of {opp}'s final-third play vs {pr['league_' + pr['favourite_lane']]:.0%} league average", "#E63946")
            card(st, "🎯 Press these players", "<br>".join(hubs), f"they make {pr['hub_share']:.0%} of {opp}'s completed passes", "#1F4E9E")
        zt = load(REP, "zone_hub_tests.csv")
        if zt is not None:
            good = confirmed(zt)
            if len(good):
                lines = []
                for _, r in good.iterrows():
                    lines.append(f"✅ {r['question']} — **yes** ({r['estimate']:+.3f}, range {r['CI low']:+.3f} to {r['CI high']:+.3f})")
                box("says", "Confirmed in five leagues (after correcting for multiple tests)", "<br>".join(lines))
        read("Lane shares compare where the opponent plays in the final third with the league average. Hubs are the players "
             "who completed the most passes for the opponent this season.")

    # ---- fine-grid danger and build-up map ----
    zmap = load(REP, "opponent_zone_maps.csv")
    if zmap is not None and len(zmap[(zmap["league"] == league) & (zmap["team"] == opp)]):
        zm = zmap[(zmap["league"] == league) & (zmap["team"] == opp)]
        st.subheader(f"🗺️ Where to hold {opp} — and where to win the ball")
        what(f"The pitch in 96 zones of 10 × 10 m, seen from **your** side (you attack to the right). "
             f"🔴 **Left half:** where {opp} creates its chances — **hold them here**. "
             f"🟢 **Right half:** where {opp} builds its play — **press and win the ball here, then counter**. ★ = top 3 zones.")
        G = np.full((8, 12), np.nan); txt = np.full((8, 12), "", dtype=object)
        dz = zm[zm["cx"] >= 6].nlargest(3, "danger")["cell"].tolist(); bz = zm[zm["cx"] < 6].nlargest(3, "build")["cell"].tolist()
        dmax = max(zm[zm["cx"] >= 6]["danger"].max(), 1e-9); bmax = max(zm[zm["cx"] < 6]["build"].max(), 1e-9)
        for r in zm.itertuples():
            ox, oy = 11 - int(r.cx), 7 - int(r.cy)                  # opponent frame -> our frame
            if r.cx >= 6:
                G[oy, ox] = -r.danger / dmax; txt[oy, ox] = "★" if r.cell in dz else ""
            else:
                G[oy, ox] = r.build / bmax; txt[oy, ox] = "★" if r.cell in bz else ""
        fig = go.Figure(go.Heatmap(z=G, x=[5 + 10 * i for i in range(12)], y=[5 + 10 * j for j in range(8)], text=txt,
                                   texttemplate="%{text}", textfont={"size": 18}, zmin=-1, zmax=1, showscale=False,
                                   colorscale=[[0, "#C1121F"], [0.5, "#FFFFFF"], [1, "#2A9D8F"]], hoverinfo="skip"))
        for x0, y0, x1, y1 in [(0, 0, 120, 80), (0, 18, 18, 62), (102, 18, 120, 62), (0, 30, 6, 50), (114, 30, 120, 50)]:
            fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color="#333", width=1.5))
        fig.add_shape(type="line", x0=60, y0=0, x1=60, y1=80, line=dict(color="#333", width=1.5))
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis=dict(visible=False, range=[0, 120]), yaxis=dict(visible=False, range=[0, 80], scaleanchor="x"))
        st.plotly_chart(fig, use_container_width=True)
        zg = load(REP, "zone_grid_tests.csv")
        if zg is not None:
            good = confirmed(zg)
            if len(good):
                box("says", "Confirmed in five leagues (after correcting for multiple tests)",
                    "<br>".join(f"✅ {r['question']} — **yes** ({r['estimate']:+.3f}, range {r['CI low']:+.3f} to {r['CI high']:+.3f})"
                                for _, r in good.iterrows()))

    # ---- expected match: regular vs suggested ----
    lg = T["npxg"].mean(); c_goal = T["goals_for"].sum() / T["npxg"].sum()
    vf = {True: T[T["is_home"]]["npxg"].mean() / lg, False: T[~T["is_home"]]["npxg"].mean() / lg}
    A = T.groupby("team").agg(att=("npxg", "mean"), dfn=("npxg_conceded", "mean"))
    base_f = A.loc[me, "att"] * A.loc[opp, "dfn"] / lg * vf[home]
    base_a = A.loc[opp, "att"] * A.loc[me, "dfn"] / lg * vf[not home]
    pick = lambda tac: (eff[(eff["opp_group"] == og) & (eff["tactic"] == tac)].iloc[0]
                        if len(eff[(eff["opp_group"] == og) & (eff["tactic"] == tac)]) else
                        eff[(eff["opp_group"] == "overall") & (eff["tactic"] == tac)].iloc[0])

    def wdl(lf, la):
        g = np.arange(11); f = np.array([_fact(int(i)) for i in g], float)
        pf = np.exp(-lf * c_goal) * (lf * c_goal) ** g / f; pa = np.exp(-la * c_goal) * (la * c_goal) ** g / f
        m = np.outer(pf, pa); return np.tril(m, -1).sum(), np.trace(m), np.triu(m, 1).sum()
    er, es = pick(regular), pick(suggested)
    lf_r, la_r = max(base_f + er["for"], 0.05), max(base_a + er["against"], 0.05)
    lf_s, la_s = max(base_f + es["for"], 0.05), max(base_a + es["against"], 0.05)
    wr, ws = wdl(lf_r, la_r), wdl(lf_s, la_s)
    st.subheader("⚖️ Your regular tactic vs the suggested tactic")
    k = st.columns(2)
    card(k[0], f"Regular: {regular}", f"Win {wr[0]:.0%}", f"draw {wr[1]:.0%} · loss {wr[2]:.0%} · chances {lf_r:.2f} – {la_r:.2f}", "#6D597A")
    card(k[1], f"Suggested: {suggested}", f"Win {ws[0]:.0%}", f"draw {ws[1]:.0%} · loss {ws[2]:.0%} · chances {lf_s:.2f} – {la_s:.2f}", "#2A9D8F")
    if suggested == regular:
        says(f"**{me} already plays the best tactic for this opponent** — keep it.")
    else:
        says(f"Switching from **{regular}** to **{suggested}** changes the win chance from **{wr[0]:.0%}** to **{ws[0]:.0%}** "
             f"({100 * (ws[0] - wr[0]):+.0f} points) against a {og} opponent like {opp}.")
    long = pd.DataFrame({"plan": [f"Regular: {regular}"] * 3 + [f"Suggested: {suggested}"] * 3, "result": ["Win", "Draw", "Loss"] * 2,
                         "probability": list(wr) + list(ws)})
    st.plotly_chart(px.bar(long, x="probability", y="plan", color="result", orientation="h",
                           color_discrete_map={"Win": "#2A9D8F", "Draw": "#E9C46A", "Loss": "#E63946"},
                           labels={"probability": "Probability", "plan": ""}), use_container_width=True)
    with st.expander("🔎 How every tactic does against this type of opponent"):
        show = eff[(eff["opp_group"] == og)].copy()
        show["available to your team"] = show["tactic"].isin(allowed)
        st.dataframe(fmt(show[["tactic", "advantage", "n", "available to your team"]].sort_values("advantage", ascending=False)
                         .rename(columns={"advantage": "performance vs expectation", "n": "matches"})), hide_index=True, use_container_width=True)

    # ---- proof: suggested tactic vs regular tactic in real matches ----
    st.subheader("🏆 Proof: teams that followed the suggestion did better")
    sv = load(REP, "suggested_vs_regular_summary.csv"); by = load(REP, "suggested_vs_regular_by_league.csv")
    if sv is not None:
        r = sv.iloc[0]
        k = st.columns(3)
        card(k[0], "① Suggested beats regular", f"{r['advantage (npxGD vs expectation)']:+.2f}",
             f"better chance balance per match · range {r['CI low']:+.2f} to {r['CI high']:+.2f}", "#2A9D8F")
        card(k[1], "② Not luck", f"p = {r['permutation p']:.3f}", "random shuffles almost never match it", "#1F4E9E")
        if by is not None:
            npos = int((by["advantage"] > 0).sum())
            card(k[2], "③ Works across leagues", f"{npos} of {len(by)}", "leagues where the suggestion did better", "#A50044")
        extra = []
        if r["better-than-expected rate suggested"] > r["better-than-expected rate regular"]:
            extra.append(f"played **better than expected in {r['better-than-expected rate suggested']:.0%}** of matches "
                         f"(regular: {r['better-than-expected rate regular']:.0%})")
        if r["win rate suggested"] > r["win rate regular"]:
            extra.append(f"**won {r['win rate suggested']:.0%}** of matches (regular: {r['win rate regular']:.0%})")
        says(f"Across **{int(r['teams'])} teams** in five leagues, matches played with the suggested tactic "
             + (", ".join(extra) if extra else "showed a better chance balance than matches played with the regular tactic")
             + ". The suggestions were made using **other leagues only**, so they were tested on matches the system had never seen.")
    else:
        st.info("Run the last cell of `TACTIX_Replication.ipynb` (Suggested tactic vs regular tactic) to show the proof here.")
    st.caption("Win chances are model estimates from both teams' season records and the measured effect of each tactic.")

# ------------------------------------------------------------------------------------------------------------
# 12. Scouting — players who fit the suggested tactic (reads Scouting_Model/scout_output)
# ------------------------------------------------------------------------------------------------------------
elif page == '🔎 Scouting':
    hero("🔎 Scouting", "Which players suit the tactic TACTIX-AI suggests for your team?")
    here = os.path.dirname(os.path.abspath(__file__))
    options = [os.path.join(os.path.dirname(PROJECT), "Scouting_Model", "scout_output"), os.path.join(here, "Scouting_Model", "scout_output"),
               os.path.join(here, "scout_output"), os.path.join(PROJECT, "scout_output")]
    SCO1 = next((o for o in options if os.path.exists(os.path.join(o, "scout_player_fit_all_plans.csv"))), options[0])
    SCO5 = os.path.join(os.path.dirname(SCO1), "scout_output_5leagues")
    five = os.path.exists(os.path.join(SCO5, "scout_player_fit_all_plans.csv"))
    if five:
        pool = st.radio("Scouting pool", ["🌍 Five leagues (81 teams, 1,272 players)", "🇪🇸 La Liga only"], horizontal=True)
        five = pool.startswith("🌍")
    SCO = SCO5 if five else SCO1
    ft = load(SCO, "scout_player_fit_all_plans.csv"); req = load(SCO, "scout_role_requirements.csv")
    if ft is not None:
        ft = ft.copy()
        if five:
            ft["league"] = ft["team"].str.split(" | ", regex=False).str[0]
            ft["club"] = ft["team"].str.split(" | ", regex=False).str[-1]
            rk = ft[["league", "team", "team_league_rank"]].drop_duplicates()
            rk["own_rank"] = rk.groupby("league")["team_league_rank"].rank(method="first")
            ft = ft.merge(rk[["team", "own_rank"]], on="team", how="left")
        else:
            ft["league"] = "La Liga"; ft["club"] = ft["team"]; ft["own_rank"] = ft["team_league_rank"]
    if ft is None:
        st.warning("Scouting results not found — run Step 60 in TACTIX_AI_FINAL.ipynb (it creates `Scouting_Model/scout_output`).")
        st.stop()
    what("Scouting in **four steps**: ① what the tactic asks of each position → ② how well your squad already fits → "
         "③ which players elsewhere fit best → ④ how reliable this is. **Fit** (0–100%) = how closely a player's playing "
         "style matches what the tactic needs in his position; 100% = the closest match in the league.")
    GROUP_NAME = {"DEF": "Defenders", "DM": "Defensive midfielders", "CM": "Central midfielders", "AM/W": "Attacking mids / wingers", "FW": "Forwards"}
    tactics_ = sorted(ft["plan"].unique())
    c0, c1, c2, c3 = st.columns(4)
    lgs_ = sorted(ft["league"].unique())
    lg_ = c0.selectbox("🏆 League", lgs_, index=lgs_.index("La Liga") if "La Liga" in lgs_ else 0)
    teams_ = sorted(ft[ft["league"] == lg_]["club"].unique())
    me = c1.selectbox("⚽ Your team", teams_, index=teams_.index(HOME) if HOME in teams_ else 0)
    opps = [t for t in teams_ if t != me]
    opp = c2.selectbox("🆚 Next opponent", opps, index=opps.index(RIVAL) if RIVAL in opps else 0)
    me_key = f"{lg_} | {me}" if five else me
    default_tac, reason, allowed = None, "", []
    REP = os.path.join(PROJECT, "replication")
    files = sorted(f for f in (os.listdir(REP) if os.path.isdir(REP) else []) if f.startswith("team_match_") and f.endswith(".csv"))
    if files:
        try:
            tabs = _league_tables(REP, tuple(files)); eff = _effects(REP, tuple(files))
            if lg_ in tabs and me in set(tabs[lg_]["team"]) and opp in set(tabs[lg_]["team"]):
                default_tac, _, allowed, og = suggest_for(tabs, eff, lg_, me, opp)
                reason = f"Suggested by the 🧭 Match Planner for a {og} opponent"
        except Exception:
            default_tac = None
    if default_tac not in tactics_:
        default_tac = tactics_[0]; reason = reason or "Choose a tactic"
    tac = c3.selectbox("🧭 Tactic", tactics_, index=tactics_.index(default_tac), help=reason)
    st.markdown(f'<div class="hero" style="padding:.9rem 1.6rem"><p>{reason}</p>'
                f'<h1 style="font-size:1.7rem">{tac}</h1></div>', unsafe_allow_html=True)
    d = ft[ft["plan"] == tac].copy()

    # ---------------- ① what the tactic asks ----------------
    st.subheader("① What does this tactic ask of each position?")
    if req is not None:
        r = req[req["plan"] == tac]
        cols = st.columns(5)
        for col, g in zip(cols, ["DEF", "DM", "CM", "AM/W", "FW"]):
            x = r[r["pos_group"] == g].sort_values("beta_per_SD_usage")
            if not len(x):
                continue
            more = x.tail(2).iloc[::-1]; less = x.head(1)
            lines = [f"⬆️ {l.split(' /')[0].lower()}{' ✓' if pb < 0.05 else ''}" for l, pb in zip(more["label"], more["p_bh"]) if True]
            lines += [f"⬇️ {l.split(' /')[0].lower()}" for l in less["label"]]
            col.markdown(f'<div class="box what" style="min-height:150px"><b class="t">{GROUP_NAME[g]}</b>{"<br>".join(lines)}</div>',
                         unsafe_allow_html=True)
        read("⬆️ = players in this position do **more** of it in teams that play this tactic; ⬇️ = **less**. "
             "✓ = a clear, statistically confirmed difference.")
        with st.expander("🔬 Full picture (all statistics)"):
            hm = r.pivot(index="label", columns="pos_group", values="beta_per_SD_usage").reindex(columns=["DEF", "DM", "CM", "AM/W", "FW"])
            fig = px.imshow(hm, color_continuous_scale="RdBu", zmin=-0.6, zmax=0.6, text_auto=".2f", aspect="auto",
                            labels={"color": "more (+) / less (−)"})
            st.plotly_chart(fig, use_container_width=True)

    # ---------------- ② squad fit ----------------
    st.subheader(f"② How well does {me}'s squad fit it?")
    rows = []
    for g in ["DEF", "DM", "CM", "AM/W", "FW"]:
        own = d[(d["team"] == me_key) & (d["pos_group"] == g)]
        best = d[(d["team"] != me_key) & (d["pos_group"] == g)].nlargest(5, "fit_pct")
        if len(own) and len(best):
            rows.append({"position": GROUP_NAME[g], "group": g, "your players": own["fit_pct"].mean(), "best available": best["fit_pct"].mean()})
    gaps = pd.DataFrame(rows)
    if not len(gaps):
        st.info("No players of this team with enough minutes."); st.stop()
    gaps["room"] = gaps["best available"] - gaps["your players"]
    long = gaps.melt(id_vars="position", value_vars=["your players", "best available"], var_name="", value_name="fit")
    st.plotly_chart(px.bar(long, x="position", y="fit", color="", barmode="group", range_y=[0, 1],
                           color_discrete_sequence=[TEAM_COLORS.get(me, "#6D597A"), "#2A9D8F"],
                           labels={"fit": "Average fit (0–100%)", "position": ""}), use_container_width=True)
    strong = gaps.sort_values("your players", ascending=False).iloc[0]; need = gaps.sort_values("room", ascending=False).iloc[0]
    says(f"💪 **Already strong:** {strong['position'].lower()} ({strong['your players']:.0%}).  "
         f"🎯 **Biggest opportunity:** {need['position'].lower()} — your players {need['your players']:.0%}, "
         f"best available {need['best available']:.0%}.")

    # ---------------- ③ who would fit ----------------
    st.subheader("③ Which players would fit best?")
    pos = st.selectbox("Position to scout", list(gaps.sort_values("room", ascending=False)["position"]))
    g = gaps.set_index("position").loc[pos, "group"]
    cand = d[(d["team"] != me_key) & (d["pos_group"] == g)].copy()
    other = [t for t in allowed if t != tac and t in set(ft["plan"])][:2]
    if other:
        alt = ft[ft["plan"].isin(other) & (ft["pos_group"] == g)].groupby("pid")["fit_pct"].min()
        cand["robust"] = cand["pid"].map(alt).fillna(0).ge(0.6) & cand["fit_pct"].ge(0.6)
    else:
        cand["robust"] = False
    cand["ideal"] = cand["fit_pct"].ge(0.7) & cand["output_pct"].ge(0.6)
    cand["realistic"] = cand["own_rank"].ge(11)
    cand["badges"] = (np.where(cand["ideal"], "⭐ ", "") + np.where(cand["robust"], "🛡️ ", "") + np.where(cand["realistic"], "💰", ""))
    cand["type"] = np.where(cand["ideal"], "⭐ fits and productive", np.where(cand["fit_pct"] >= 0.7, "fits the tactic", "other"))
    fig = px.scatter(cand, x="fit_pct", y="output_pct", color="type", hover_name="player", hover_data=["club", "league", "minutes"],
                     color_discrete_map={"⭐ fits and productive": "#2A9D8F", "fits the tactic": "#F4A261", "other": "#BBBBBB"},
                     labels={"fit_pct": "Fit to the tactic →", "output_pct": "Productivity in his position →", "type": ""},
                     range_x=[0, 1.02], range_y=[0, 1.02])
    fig.add_vline(x=0.7, line_dash="dash", line_color="grey"); fig.add_hline(y=0.6, line_dash="dash", line_color="grey")
    top_names = cand.nlargest(6, "fit_pct")
    fig.add_trace(go.Scatter(x=top_names["fit_pct"], y=top_names["output_pct"], mode="text", text=top_names["player"].str.split().str[-1],
                             textposition="top center", showlegend=False))
    st.plotly_chart(fig, use_container_width=True)
    read("**Top-right corner = ideal targets:** they fit the tactic **and** are productive. Hover over a dot to see the player.")
    sl = cand.sort_values(["ideal", "fit_pct"], ascending=False).head(10)
    sl["fit range"] = [f"{a:.0%}–{b:.0%}" for a, b in zip(sl["fit_pct_ci_low"], sl["fit_pct_ci_high"])]
    st.dataframe(fmt(sl[["badges", "player", "club", "league", "minutes", "fit_pct", "fit range", "output_pct"]].rename(
        columns={"club": "team", "fit_pct": "fit", "output_pct": "productivity"})), hide_index=True, use_container_width=True)
    read("⭐ **Ideal** = fits (≥ 70%) and productive · 🛡️ **Robust** = also fits the other tactics your team plays · "
         "💰 **Realistic** = plays for a team in the bottom half of its league's table. **Fit range** = how much the fit could move with normal randomness.")
    with st.expander(f"👥 {me}'s current {pos.lower()}"):
        own = d[(d["team"] == me_key) & (d["pos_group"] == g)].sort_values("fit_pct", ascending=False)
        st.dataframe(fmt(own[["player", "position", "minutes", "fit_pct", "output_pct"]].rename(
            columns={"fit_pct": "fit", "output_pct": "productivity"})), hide_index=True, use_container_width=True)

    # ---------------- ④ reliability ----------------
    st.subheader("④ Can we trust it?")
    val = load(SCO, "scout_validation_loto.csv"); noise = load(SCO, "scout_validation_noise.csv")
    k = st.columns(3)
    if val is not None:
        nsig = int((val["p_perm_two_sided"] < 0.05).sum()) if "p_perm_two_sided" in val else 0
        card(k[0], "Works on unseen teams", f"{int((val['spearman_rho'] > 0).sum())} of {len(val)} tactics",
             (f"significant in {nsig} of {len(val)} · " if nsig else "") + f"{int(val['n_teams'].max())} teams tested", "#2A9D8F")
    if noise is not None:
        card(k[1], "Stable", f"{noise['mean_spearman_vs_noisy_draws'].mean():.0%}", "same ranking across 200 re-played seasons", "#1F4E9E")
        card(k[2], "Top players stay on top", f"{noise['top_decile_kept_in_top_quintile'].mean():.0%}",
             "of the top 10% remain in the top 20%", "#A50044")
    st.caption("Fit compares playing styles from one season of event data; age, fees and injuries are not included.")

# ------------------------------------------------------------------------------------------------------------
# 13. Glossary
# ------------------------------------------------------------------------------------------------------------
elif page == '📖 Glossary':
    hero("📖 Glossary", "Every term used in this dashboard, explained simply.")
    cols = st.columns(2)
    for i, (k, v) in enumerate(GLOSSARY.items()):
        with cols[i % 2]:
            st.markdown(f'<div class="box what"><b class="t">{k}</b>{md(v)}</div>', unsafe_allow_html=True)

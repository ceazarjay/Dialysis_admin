"""
Bemanningssituasjonen ved HUS Dialyse
Sammenligning med norske dialysesentre 2025
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HUS Dialyse – Bemanningsanalyse",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Gestalt-informed colour system ───────────────────────────────────────────
# Figure-ground: ONE salient colour for HUS (alarm red), muted slate for peers.
# Similarity: same HUS colour repeated across every chart → no need to re-learn.
HUS_COL   = "#C0392B"   # vivid red  → HUS always "pops"
PEER_COL  = "#7F8C9A"   # muted blue-grey → chart bars only (recedes into ground)
PEER_TEXT = "#2C3E50"   # dark navy-grey → peer text/labels, readable on white
BG_PAGE   = "#F7F9FC"
BG_CARD   = "#FFFFFF"
TEXT_DARK = "#1A252F"
TEXT_MID  = "#2C3E50"   # darkened from #4A6070 for legibility on white
ACCENT    = "#1A6B8A"   # deeper teal → readable on white (was #2E86AB)
WARN_BG   = "#FFF3F2"

# ── Global CSS ────────────────────────────────────────────────────────────────
# Common region (card borders) for Gestalt grouping.
st.markdown(f"""
<style>
  /* ---- typography & page background ---- */
  html, body, [class*="css"] {{
    font-family: 'Segoe UI', sans-serif;
    background-color: {BG_PAGE};
    color: {TEXT_DARK};
  }}
  h1, h2, h3 {{ color: {TEXT_DARK}; }}

  /* ---- metric cards ---- */
  .metric-card {{
    background: {BG_CARD};
    border-radius: 10px;
    padding: 18px 22px 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    text-align: center;
    border-top: 4px solid {PEER_COL};
  }}
  .metric-card.hus {{
    border-top: 4px solid {HUS_COL};
    background: {WARN_BG};
  }}
  .metric-val {{
    font-size: 2.6rem;
    font-weight: 700;
    line-height: 1.1;
  }}
  .metric-val.red {{ color: {HUS_COL}; }}
  .metric-val.grey {{ color: {PEER_TEXT}; }}
  .metric-label {{
    font-size: 0.82rem;
    color: {TEXT_MID};
    margin-top: 4px;
  }}

  /* ---- section header strip ---- */
  .section-strip {{
    background: {TEXT_DARK};
    color: #fff;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 1.05rem;
    margin-bottom: 12px;
    letter-spacing: 0.03em;
  }}

  /* ---- callout banner ---- */
  .callout {{
    background: {WARN_BG};
    border-left: 5px solid {HUS_COL};
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    font-size: 0.97rem;
    color: {TEXT_DARK};
    margin-bottom: 10px;
  }}

  /* ---- legend chip ---- */
  .chip {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-right: 6px;
  }}
  .chip-hus {{ background: {HUS_COL}; color: #fff; }}
  .chip-peer {{ background: {PEER_COL}; color: #fff; }}
</style>
""", unsafe_allow_html=True)

# ── Data ─────────────────────────────────────────────────────────────────────
hospitals = ["HUS", "VOSS", "KALNES", "DRAMMEN", "TRONDHEIM",
             "LOVISENBERG", "ULLEVÅL", "AHUS", "STAVANGER", "TROMSØ"]

# Sick leave % (HUS=23 % from sheet value 0.23, others parsed from text)
sick_leave = {
    "HUS": 23.0, "VOSS": 2.0, "KALNES": 10.0, "DRAMMEN": 15.0,
    "TRONDHEIM": 9.5, "LOVISENBERG": 4.5, "ULLEVÅL": 10.37,
    "AHUS": 9.37, "STAVANGER": None, "TROMSØ": 5.5,
}

# Patient : nurse ratio (HUS reported as 3–6 + outpost; encoded as 6 for chart)
pt_nurse = {
    "HUS": 3, "VOSS": 2.5, "KALNES": 2.5, "DRAMMEN": 2.5,
    "TRONDHEIM": 2.5, "LOVISENBERG": 2.5, "ULLEVÅL": 2.5,
    "AHUS": 2.75, "STAVANGER": 2.75, "TROMSØ": 2.5,
}

# HD patient volumes
hd_patients = {
    "HUS": 91, "VOSS": 9, "KALNES": 152, "DRAMMEN": 39,
    "TRONDHEIM": 71, "LOVISENBERG": 49, "ULLEVÅL": 53,
    "AHUS": 97, "STAVANGER": 85, "TROMSØ": 14,
}

# Staff FTEs (annual work-units)
staff_fte = {
    "HUS": 32.8, "VOSS": 4.5, "KALNES": 24.0, "DRAMMEN": 21.0,
    "TRONDHEIM": None, "LOVISENBERG": 18.0, "ULLEVÅL": 27.2,
    "AHUS": None, "STAVANGER": None, "TROMSØ": 15.0,
}

# Training weeks (0 = on-demand / no new staff)
training_weeks = {
    "HUS": 6, "VOSS": 0, "KALNES": 12, "DRAMMEN": 8,
    "TRONDHEIM": 18, "LOVISENBERG": 0, "ULLEVÅL": 12,
    "AHUS": 12, "STAVANGER": 6, "TROMSØ": 0,
}

# Fellesvakter (shared cross-ward shifts)
fellesvakter = {h: "NEI" for h in hospitals}
fellesvakter["HUS"] = "JA"

# Vacation coverage
vacation = {
    "HUS": "50% studenter",
    "VOSS": "Sykepleier",
    "KALNES": "Dialysesykepleier",
    "DRAMMEN": "Dialysesykepleier",
    "TRONDHEIM": "Faste vikarer",
    "LOVISENBERG": "Ja / faste vikarer",
    "ULLEVÅL": "Faste vikarer",
    "AHUS": "Kun dialysespl.",
    "STAVANGER": "6-ukers opplæring",
    "TROMSØ": "Eget personell",
}

# Absence replacement
absence_rep = {
    "HUS": "Student / Fellesvakt",
    "VOSS": "Nei",
    "KALNES": "Opplærte dialysespl.",
    "DRAMMEN": "Eget personell",
    "TRONDHEIM": "Opplærte dialysespl.",
    "LOVISENBERG": "Opplærte dialysespl.",
    "ULLEVÅL": "Opplærte dialysespl.",
    "AHUS": "Opplærte dialysespl.",
    "STAVANGER": "Opplærte dialysespl.",
    "TROMSØ": "Eget personell",
}

def bar_colour(h):
    return HUS_COL if h == "HUS" else PEER_COL

def make_bar(x_vals, y_vals, ylabel="", title="", hus_label=None,
             reference_line=None, ref_label="", fmt_pct=False):
    """Horizontal bar chart with figure-ground emphasis on HUS."""
    colours = [bar_colour(h) for h in x_vals]
    customdata = [("HUS" if h == "HUS" else h) for h in x_vals]
    hover = "%{customdata}: %{y:.1f}" + ("%" if fmt_pct else "")

    fig = go.Figure(go.Bar(
        x=x_vals, y=y_vals,
        marker_color=colours,
        customdata=customdata,
        hovertemplate=hover + "<extra></extra>",
        width=0.6,
    ))
    if reference_line is not None:
        fig.add_hline(
            y=reference_line, line_dash="dot",
            line_color=ACCENT, line_width=2,
            annotation_text=ref_label,
            annotation_font_color=ACCENT,
            annotation_position="top right",
        )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=TEXT_DARK), x=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(
            title=dict(text=ylabel, font=dict(size=12, color=TEXT_DARK)),
            gridcolor="#E8EDF2",
            gridwidth=1,
            ticksuffix="%" if fmt_pct else "",
            tickfont=dict(size=12, color=TEXT_DARK),
        ),
        xaxis=dict(tickfont=dict(size=13, color=TEXT_DARK), tickangle=0),
        showlegend=False,
        height=320,
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="
  background:{TEXT_DARK}; color:#fff;
  padding: 28px 36px 22px; border-radius: 12px; margin-bottom: 28px;
">
  <div style="font-size:0.8rem; text-transform:uppercase; letter-spacing:0.1em;
              color:#7F9FB0; margin-bottom:4px;">
    HUS Nyremedisinsk avdeling · Dialyseenheten
  </div>
  <h1 style="margin:0; font-size:2rem; color:#fff; font-weight:700;">
    Bemanningssituasjonen ved HUS Dialyse
  </h1>
  <p style="margin:8px 0 0; color:#B0C4CF; font-size:1rem;">
    Sammenligning med 9 dialyseenhet i Norge · Data innhentet 2025
  </p>
  <div style="margin-top:14px;">
    <span class="chip chip-hus">● HUS</span>
    <span class="chip chip-peer">● Andre Dialyse enhet</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 – KPI SCORECARD   (Gestalt: Common Region + Proximity)
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-strip">Nøkkeltallene</div>', unsafe_allow_html=True)

peers_sl = [v for k, v in sick_leave.items() if k != "HUS" and v is not None]
peer_avg_sl = round(sum(peers_sl) / len(peers_sl), 1)

cols = st.columns(4, gap="medium")

with cols[0]:
    st.markdown(f"""
    <div class="metric-card hus">
      <div class="metric-val red">23 %</div>
      <div class="metric-label">Sykefravær – HUS<br><span style="color:{HUS_COL};font-weight:700;">
        {23/peer_avg_sl:.1f}× gjennomsnittet
      </span></div>
    </div>""", unsafe_allow_html=True)

with cols[1]:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-val grey">{peer_avg_sl} %</div>
      <div class="metric-label">Sykefravær<br>gjennomsnitt andre dialyseenhet</div>
    </div>""", unsafe_allow_html=True)

with cols[2]:
    st.markdown(f"""
    <div class="metric-card hus">
      <div class="metric-val red">opptil 3-6</div>
      <div class="metric-label">Pasienter per sykepleier – HUS<br>
        <span style="color:{HUS_COL};font-weight:700;">+ 2 pasienter på utpost</span>
      </div>
    </div>""", unsafe_allow_html=True)

with cols[3]:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-val grey">2.5</div>
      <div class="metric-label">Pasienter per sykepleier<br>standard</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 – SYKEFRAVÆR   (Gestalt: Figure-ground, Similarity)
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-strip">Sykefravær – HUS skiller seg dramatisk ut</div>',
            unsafe_allow_html=True)

st.markdown(f"""
<div class="callout">
  <strong>HUS har 23 % sykefravær</strong> — det er {23/peer_avg_sl:.1f}× gjennomsnittet
  ({peer_avg_sl} %). Høyt fravær er både en konsekvens
  <em>og</em> årsak til underbemanningen.
</div>
""", unsafe_allow_html=True)

sl_hosp  = [h for h in hospitals if sick_leave[h] is not None]
sl_vals  = [sick_leave[h] for h in sl_hosp]

fig_sl = make_bar(sl_hosp, sl_vals,
                  ylabel="Sykefravær (%)", fmt_pct=True,
                  reference_line=peer_avg_sl,
                  ref_label=f"Gjennomsnitt {peer_avg_sl} %")
st.plotly_chart(fig_sl, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 – PASIENT:SYKEPLEIER-RATIO
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-strip">Pasienter per sykepleier</div>',
            unsafe_allow_html=True)

col_a, col_b = st.columns([2, 1], gap="large")

with col_a:
    pt_hosp = list(pt_nurse.keys())
    pt_vals = list(pt_nurse.values())

    # Annotate HUS bar with "+ utpost"
    fig_pt = make_bar(pt_hosp, pt_vals,
                      ylabel="Pasienter per sykepleier",
                      reference_line=2.5, ref_label="standard. 2.5")
    # Add annotation on HUS bar
    fig_pt.add_annotation(
        x="HUS", y=6.2, text="+ 2 PASIENTER PÅ UTPOST",
        showarrow=False, font=dict(color=HUS_COL, size=11, family="Segoe UI"),
    )
    st.plotly_chart(fig_pt, use_container_width=True)

with col_b:
    st.markdown(f"""
    <div class="metric-card hus" style="margin-top:30px;">
      <div class="metric-val red">3-6 pas.</div>
      <div class="metric-label">HUS – oppgitt maks pasienter  per sykepleier<br></div>
    </div>
    <br>
    <div class="metric-card" style="margin-top:0;">
      <div class="metric-val grey">2.5 pas.</div>
      <div class="metric-label">Standard ved andre<br>dialyseenhet</div>
    </div>
    <br>
    <div class="callout">
      HUS er den <strong>ENESTE</strong> dialyseenhet med 
      utpostansvar <em>uten</em> økt bemanning på avdelingen.
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 – FELLESVAKTER   (Continuity: builds on previous context)
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-strip">Fellesvakter – HUS er alene i Norge</div>',
            unsafe_allow_html=True)

st.markdown(f"""
<div class="callout">
  <strong>Fellesvakter</strong> fører til redusert spesialisert kunnskap og erfaring,
  økt forvirring og lavere faglig kompetanse. HUS er det
  <strong>eneste</strong> dialysesenteret i Norge som bruker dette.
</div>
""", unsafe_allow_html=True)

fw_cols = st.columns(len(hospitals), gap="small")
for i, (col, h) in enumerate(zip(fw_cols, hospitals)):
    is_hus = h == "HUS"
    bg = HUS_COL if is_hus else "#E8EDF2"
    fg = "#fff" if is_hus else TEXT_DARK
    icon = "✓" if is_hus else "✗"
    label = "JA" if is_hus else "NEI"
    col.markdown(f"""
    <div style="background:{bg}; color:{fg}; border-radius:8px;
                text-align:center; padding:10px 4px; font-weight:700;
                font-size:0.78rem; box-shadow:0 1px 4px rgba(0,0,0,0.1);">
      <div style="font-size:1.4rem;">{icon}</div>
      <div>{h}</div>
      <div style="font-size:0.7rem; opacity:0.85;">{label}</div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 – OPPLÆRINGSTID + FERIEAVVIKLING
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-strip">Opplæringstid & ferieavvikling</div>',
            unsafe_allow_html=True)

col_left, col_right = st.columns(2, gap="large")

with col_left:
    tw_hosp = [h for h in hospitals if training_weeks[h] > 0]
    tw_vals = [training_weeks[h] for h in tw_hosp]
    colours  = [bar_colour(h) for h in tw_hosp]

    fig_tw = go.Figure(go.Bar(
        x=tw_hosp, y=tw_vals,
        marker_color=colours,
        hovertemplate="%{x}: %{y} uker<extra></extra>",
        width=0.6,
    ))
    fig_tw.add_hline(y=12, line_dash="dot", line_color=ACCENT, line_width=2,
                     annotation_text="3 måneder (anbefalt)",
                     annotation_font_color=ACCENT,
                     annotation_position="top right")
    fig_tw.update_layout(
        title=dict(text="Opplæringstid for nye dialysesykepleiere (uker)",
                   font=dict(size=13, color=TEXT_DARK), x=0),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(title="Uker", gridcolor="#E8EDF2",
                   tickfont=dict(size=12, color=TEXT_DARK)),
        xaxis=dict(tickfont=dict(size=13, color=TEXT_DARK), tickangle=0),
        height=310,
    )
    st.plotly_chart(fig_tw, use_container_width=True)

with col_right:
    st.markdown("**Ferieavvikling – hvem dekker?**")
    rows = []
    for h in hospitals:
        is_hus = h == "HUS"
        bg  = WARN_BG if is_hus else BG_CARD
        txt = f"<strong style='color:{HUS_COL};'>{h}</strong>" if is_hus else h
        rows.append(f"""
        <tr style="background:{bg};">
          <td style="padding:6px 10px; font-weight:{'700' if is_hus else '400'}; color:{HUS_COL if is_hus else TEXT_DARK};">{txt}</td>
          <td style="padding:6px 10px; color:{HUS_COL if is_hus else TEXT_DARK};">
            {vacation[h]}
          </td>
        </tr>""")
    st.markdown(f"""
    <table style="width:100%; border-collapse:collapse; font-size:0.87rem;
                  border:1px solid #E0E7EF; border-radius:8px; overflow:hidden;">
      <thead>
        <tr style="background:{TEXT_DARK}; color:#fff;">
          <th style="padding:8px 10px; text-align:left;">Senter</th>
          <th style="padding:8px 10px; text-align:left;">Ferieavvikling</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="callout" style="margin-top:10px;">
      HUS dekker ferie med <strong>50 % studenter</strong>.
      Alle andre dialyseenhet har dialysesykepleiere eller egne faste vikarer.
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 – FRAVÆRSDEKNING (Replacement during absence)
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-strip">Hvem erstatter ved sykdom og fravær?</div>',
            unsafe_allow_html=True)

rep_rows = []
for h in hospitals:
    is_hus = h == "HUS"
    bg  = WARN_BG if is_hus else BG_CARD
    hname = f"<strong style='color:{HUS_COL};'>{h}</strong>" if is_hus else h
    rep_rows.append(f"""
    <tr style="background:{bg};">
      <td style="padding:6px 12px; color:{HUS_COL if is_hus else TEXT_DARK};">{hname}</td>
      <td style="padding:6px 12px; color:{HUS_COL if is_hus else TEXT_DARK};">
        {absence_rep[h]}
      </td>
    </tr>""")

rep_cols = st.columns([2, 1], gap="large")
with rep_cols[0]:
    st.markdown(f"""
    <table style="width:100%; border-collapse:collapse; font-size:0.87rem;
                  border:1px solid #E0E7EF; border-radius:8px; overflow:hidden;">
      <thead>
        <tr style="background:{TEXT_DARK}; color:#fff;">
          <th style="padding:8px 12px; text-align:left;">Senter</th>
          <th style="padding:8px 12px; text-align:left;">Erstatter ved ferie/fravær</th>
        </tr>
      </thead>
      <tbody>{''.join(rep_rows)}</tbody>
    </table>
    """, unsafe_allow_html=True)

with rep_cols[1]:
    # Donut chart: HUS vs rest using trained nurses
    trained_count = sum(1 for h in hospitals
                        if h != "HUS" and "opplærte" in absence_rep[h].lower()
                        or "eget" in absence_rep[h].lower()
                        or "faste" in absence_rep[h].lower())
    fig_donut = go.Figure(go.Pie(
        labels=["Opplærte/egne sykepleiere", "Studenter / Fellesvakt (HUS)"],
        values=[trained_count, 1],
        hole=0.6,
        marker_colors=[PEER_COL, HUS_COL],
        textinfo="label+percent",
        textfont=dict(color=TEXT_DARK, size=12),
        outsidetextfont=dict(color=TEXT_DARK, size=12),
        hovertemplate="%{label}: %{value} dialyseenhet<extra></extra>",
    ))
    fig_donut.update_layout(
        title=dict(text="Fraværsdekning – type vikar", font=dict(size=12, color="black"), x=0),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white", height=260,
        showlegend=False,
    )
    st.plotly_chart(fig_donut, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 – PASIENTVOLUM VS BEMANNING  (Scatterplot)
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-strip">Antall pasient vs. registrerte årsverk</div>',
            unsafe_allow_html=True)

scatter_h = [h for h in hospitals if staff_fte[h] is not None]
scatter_x = [hd_patients[h] for h in scatter_h]
scatter_y = [staff_fte[h] for h in scatter_h]
scatter_c = [bar_colour(h) for h in scatter_h]
scatter_s = [16 if h == "HUS" else 10 for h in scatter_h]

fig_sc = go.Figure()
for h, x, y, c, s in zip(scatter_h, scatter_x, scatter_y, scatter_c, scatter_s):
    label_col = HUS_COL if h == "HUS" else PEER_TEXT
    fig_sc.add_trace(go.Scatter(
        x=[x], y=[y],
        mode="markers+text",
        marker=dict(color=c, size=s, line=dict(color="white", width=1.5)),
        text=[h],
        textposition="top center",
        textfont=dict(size=10, color=label_col),
        name=h,
        hovertemplate=f"{h}: {x} HD-pas., {y} årsverk<extra></extra>",
        showlegend=False,
    ))

fig_sc.update_layout(
    xaxis=dict(title="Antall hemodialysepas.", gridcolor="#E8EDF2"),
    yaxis=dict(title="Registrerte årsverk", gridcolor="#E8EDF2"),
    plot_bgcolor="white", paper_bgcolor="white",
    margin=dict(l=10, r=10, t=20, b=10),
    height=340,
)
st.plotly_chart(fig_sc, use_container_width=True)
st.caption("Merk: HUS har 91 HD-pasienter + største antall utposter på 32,8 registrerte årsverk.")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8 – OPPSUMMERING / KRAV TIL ADMINISTRASJONEN
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background:{TEXT_DARK}; color:#fff; padding:28px 36px;
            border-radius:12px; margin-top:8px;">
  <h2 style="color:#fff; margin-top:0;">Oppsummering – hva dataene forteller</h2>
  <div style="display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:16px;">
    <div style="background:rgba(255,255,255,0.08); border-radius:8px; padding:16px;">
      <div style="color:{HUS_COL}; font-weight:700; margin-bottom:6px;">
        Sykefravær
      </div>
      23 % sykefravær — {23/peer_avg_sl:.1f}×.
      Høyt fravær og underbemanning er relatert med hverandre.
    </div>
    <div style="background:rgba(255,255,255,0.08); border-radius:8px; padding:16px;">
      <div style="color:{HUS_COL}; font-weight:700; margin-bottom:6px;">
        Pasient : sykepleier-ratio
      </div>
      Opptil 6 pasienter per sykepleier (skjer ofte under ferie), med utpostansvar i tillegg.
      Alle andre dialyseenhet holder 2,5.
    </div>
    <div style="background:rgba(255,255,255,0.08); border-radius:8px; padding:16px;">
      <div style="color:{HUS_COL}; font-weight:700; margin-bottom:6px;">
        Fellesvakter
      </div>
      HUS er det <strong style="color:#fff;">ENESTE</strong> dialysesenteret i Norge
      som fortsatt bruker fellesvakter.
    </div>
    <div style="background:rgba(255,255,255,0.08); border-radius:8px; padding:16px;">
      <div style="color:{HUS_COL}; font-weight:700; margin-bottom:6px;">
        Dekning ved fravær og ferie
      </div>
      HUS bruker studenter og fellesvakter. Alle øvrige dialyseenhet bruker opplært
      dialysesykepleiere.
    </div>
  </div>
  <div style="margin-top:22px; padding-top:18px; border-top:1px solid rgba(255,255,255,0.15);
              color:#B0C4CF; font-size:0.85rem;">
    Datakilde: Nasjonal spørreundersøkelse dialysesentre 2025 · HUS Nyremedisinsk avdeling
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

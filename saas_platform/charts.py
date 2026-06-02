# ============================================================
# charts.py  —  Plotly Chart Generators
# ============================================================
# Every function returns a go.Figure ready for:
#   st.plotly_chart(fig, use_container_width=True)
#
# Charts included:
#   bar, line, area, pie/donut, scatter, heatmap,
#   multi-line, grouped bar, funnel, gauge
# ============================================================

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from utils import PALETTE, COLOR


# ── Shared Layout ─────────────────────────────────────────────

_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=COLOR["text"], size=12),
    margin=dict(t=48, b=36, l=16, r=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=COLOR["text"])),
    xaxis=dict(showgrid=False, color=COLOR["muted"],
               linecolor="rgba(255,255,255,0.08)"),
    yaxis=dict(showgrid=True,  color=COLOR["muted"],
               gridcolor="rgba(255,255,255,0.06)"),
)


def _fig(title: str = "", height: int = 380) -> go.Figure:
    """Create a blank Figure with the shared dark theme."""
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=title, x=0.03, font=dict(size=15, color=COLOR["text"])),
        height=height,
        **_LAYOUT,
    )
    return fig


def _empty(msg: str = "No data available") -> go.Figure:
    """Return a placeholder figure when there's nothing to plot."""
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(size=16, color=COLOR["muted"]))
    fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


# ── Bar Chart ─────────────────────────────────────────────────

def bar_chart(df: pd.DataFrame, x: str, y: str,
              title: str = "", color: str = None,
              horizontal: bool = False) -> go.Figure:
    """Vertical or horizontal bar chart for categorical comparisons."""
    if df.empty or x not in df.columns or y not in df.columns:
        return _empty("No data for bar chart")

    c = color or PALETTE[0]
    fig = _fig(title)
    if horizontal:
        fig.add_trace(go.Bar(
            y=df[x], x=df[y], orientation="h",
            marker=dict(color=c, line=dict(width=0)),
            hovertemplate=f"<b>%{{y}}</b><br>{y}: %{{x:,.2f}}<extra></extra>"
        ))
    else:
        fig.add_trace(go.Bar(
            x=df[x], y=df[y],
            marker=dict(color=c, line=dict(width=0)),
            hovertemplate=f"<b>%{{x}}</b><br>{y}: %{{y:,.2f}}<extra></extra>"
        ))
    return fig


def grouped_bar(df: pd.DataFrame, x: str, y_cols: list[str],
                title: str = "") -> go.Figure:
    """Side-by-side bars comparing multiple series."""
    if df.empty:
        return _empty()
    fig = _fig(title)
    for i, col in enumerate(y_cols):
        if col in df.columns:
            fig.add_trace(go.Bar(
                name=col, x=df[x], y=df[col],
                marker_color=PALETTE[i % len(PALETTE)],
                hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:,.2f}}<extra></extra>"
            ))
    fig.update_layout(barmode="group")
    return fig


# ── Line Chart ────────────────────────────────────────────────

def line_chart(df: pd.DataFrame, x: str, y: str,
               title: str = "", color: str = None) -> go.Figure:
    """Simple line chart for time-series trends."""
    if df.empty or x not in df.columns or y not in df.columns:
        return _empty("No data for line chart")

    c = color or PALETTE[0]
    fig = _fig(title)
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y], mode="lines+markers",
        line=dict(color=c, width=2.5),
        marker=dict(size=5, color=c),
        fill="tozeroy", fillcolor=f"rgba{tuple(list(_hex_to_rgb(c)) + [0.12])}",
        hovertemplate=f"<b>%{{x}}</b><br>{y}: %{{y:,.2f}}<extra></extra>"
    ))
    return fig


def multi_line(df: pd.DataFrame, x: str, y_cols: list[str],
               title: str = "") -> go.Figure:
    """Multiple lines on one chart — good for comparing metrics."""
    if df.empty:
        return _empty()
    fig = _fig(title)
    for i, col in enumerate(y_cols):
        if col in df.columns:
            c = PALETTE[i % len(PALETTE)]
            fig.add_trace(go.Scatter(
                x=df[x], y=df[col], name=col,
                mode="lines+markers",
                line=dict(color=c, width=2),
                marker=dict(size=5),
                hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:,.2f}}<extra></extra>"
            ))
    return fig


# ── Area Chart ────────────────────────────────────────────────

def area_chart(df: pd.DataFrame, x: str, y: str,
               title: str = "", color: str = None) -> go.Figure:
    """Filled area chart, good for cumulative metrics."""
    if df.empty or x not in df.columns or y not in df.columns:
        return _empty()
    c = color or PALETTE[2]
    fig = _fig(title)
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y], mode="lines",
        line=dict(color=c, width=2),
        fill="tozeroy",
        fillcolor=f"rgba{tuple(list(_hex_to_rgb(c)) + [0.25])}",
        hovertemplate=f"<b>%{{x}}</b><br>{y}: %{{y:,.2f}}<extra></extra>"
    ))
    return fig


# ── Pie / Donut Chart ─────────────────────────────────────────

def pie_chart(labels: list, values: list,
              title: str = "", donut: bool = True) -> go.Figure:
    """Donut or pie chart for category breakdowns."""
    if not labels or not values:
        return _empty("No data for pie chart")
    fig = _fig(title, height=360)
    fig.add_trace(go.Pie(
        labels=labels, values=values,
        hole=0.45 if donut else 0,
        marker=dict(colors=PALETTE, line=dict(color="#1E293B", width=2)),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} (%{percent})<extra></extra>"
    ))
    fig.update_layout(showlegend=True,
                      legend=dict(orientation="v", x=1.02, y=0.5))
    return fig


# ── Scatter Plot ──────────────────────────────────────────────

def scatter_plot(df: pd.DataFrame, x: str, y: str,
                 color_col: str = None, size_col: str = None,
                 title: str = "") -> go.Figure:
    """Scatter plot for correlation analysis."""
    if df.empty or x not in df.columns or y not in df.columns:
        return _empty("No data for scatter plot")

    fig = _fig(title)
    kwargs = dict(
        x=df[x], y=df[y],
        mode="markers",
        marker=dict(size=8, color=PALETTE[0], opacity=0.7,
                    line=dict(color="#fff", width=0.5)),
        hovertemplate=f"<b>{x}</b>: %{{x:,.2f}}<br><b>{y}</b>: %{{y:,.2f}}<extra></extra>"
    )
    if color_col and color_col in df.columns:
        cats = df[color_col].astype(str).unique()
        fig_px = px.scatter(df, x=x, y=y, color=color_col,
                             color_discrete_sequence=PALETTE)
        fig_px.update_layout(**_LAYOUT, height=380,
                              title=dict(text=title, x=0.03))
        return fig_px

    fig.add_trace(go.Scatter(**kwargs))
    return fig


# ── Heatmap ───────────────────────────────────────────────────

def heatmap(matrix: pd.DataFrame, title: str = "") -> go.Figure:
    """
    Correlation / value heatmap.
    `matrix` should be a square DataFrame (e.g. df.corr()).
    """
    if matrix.empty:
        return _empty("No data for heatmap")

    fig = _fig(title, height=420)
    fig.add_trace(go.Heatmap(
        z=matrix.values.tolist(),
        x=list(matrix.columns),
        y=list(matrix.index),
        colorscale="Viridis",
        text=[[f"{v:.2f}" for v in row] for row in matrix.values],
        texttemplate="%{text}",
        showscale=True,
        hovertemplate="<b>%{x}</b> vs <b>%{y}</b><br>Value: %{z:.3f}<extra></extra>"
    ))
    fig.update_layout(
        xaxis=dict(side="bottom"),
        margin=dict(t=60, b=80, l=80, r=20)
    )
    return fig


# ── Gauge / KPI ───────────────────────────────────────────────

def gauge_chart(value: float, max_val: float,
                title: str = "", unit: str = "") -> go.Figure:
    """Speedometer-style gauge for single KPI display."""
    pct = min(value / max_val * 100, 150) if max_val > 0 else 0
    bar_color = (COLOR["success"] if pct < 70
                 else COLOR["warning"] if pct < 90
                 else COLOR["danger"])

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number=dict(suffix=unit, font=dict(size=28, color=COLOR["text"])),
        title=dict(text=title, font=dict(size=13, color=COLOR["muted"])),
        gauge=dict(
            axis=dict(range=[0, max_val], tickfont=dict(color=COLOR["muted"])),
            bar=dict(color=bar_color, thickness=0.7),
            bgcolor="rgba(255,255,255,0.04)",
            borderwidth=1, bordercolor="rgba(255,255,255,0.1)",
            steps=[
                dict(range=[0, max_val * 0.7],  color="rgba(16,185,129,0.08)"),
                dict(range=[max_val * 0.7, max_val], color="rgba(245,158,11,0.08)"),
            ],
            threshold=dict(line=dict(color=COLOR["danger"], width=2),
                           thickness=0.75, value=max_val)
        )
    ))
    fig.update_layout(
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR["text"]),
        margin=dict(t=40, b=20, l=30, r=30)
    )
    return fig


# ── Funnel Chart ──────────────────────────────────────────────

def funnel_chart(stages: list[str], values: list[float],
                 title: str = "") -> go.Figure:
    """Funnel for conversion / sales pipeline visualisation."""
    if not stages or not values:
        return _empty()
    fig = _fig(title, height=360)
    fig.add_trace(go.Funnel(
        y=stages, x=values,
        textinfo="value+percent initial",
        marker=dict(color=PALETTE[:len(stages)]),
        connector=dict(line=dict(color="rgba(255,255,255,0.1)", width=1))
    ))
    return fig


# ── Prediction Forecast Chart ─────────────────────────────────

def forecast_chart(hist_x, hist_y, pred_x, pred_y,
                   y_label: str = "Value", title: str = "") -> go.Figure:
    """
    Combines historical actuals (solid line) with ML predictions
    (dashed line) on one chart.
    """
    fig = _fig(title)

    fig.add_trace(go.Scatter(
        x=hist_x, y=hist_y, name="Historical",
        mode="lines+markers",
        line=dict(color=PALETTE[0], width=2.5),
        marker=dict(size=5),
        hovertemplate=f"<b>%{{x}}</b><br>Actual: %{{y:,.2f}}<extra></extra>"
    ))

    # Connect last historical point to first prediction for continuity
    if len(hist_x) > 0 and len(pred_x) > 0:
        conn_x = [hist_x[-1]] + list(pred_x)
        conn_y = [hist_y[-1]] + list(pred_y)
    else:
        conn_x, conn_y = pred_x, pred_y

    fig.add_trace(go.Scatter(
        x=conn_x, y=conn_y, name="Predicted",
        mode="lines+markers",
        line=dict(color=PALETTE[3], width=2, dash="dash"),
        marker=dict(size=7, symbol="diamond"),
        hovertemplate=f"<b>%{{x}}</b><br>Predicted: %{{y:,.2f}}<extra></extra>"
    ))

    fig.add_vline(x=hist_x[-1] if len(hist_x) > 0 else 0,
                  line=dict(color="rgba(255,255,255,0.2)",
                             dash="dot", width=1))
    fig.update_layout(
        yaxis_title=y_label,
        legend=dict(x=0.01, y=0.99, orientation="h")
    )
    return fig


# ── Segment Bar (horizontal, coloured) ───────────────────────

def segment_bar(segment_counts: pd.Series,
                title: str = "User Segments") -> go.Figure:
    """Horizontal bar chart showing segment sizes."""
    if segment_counts.empty:
        return _empty()
    fig = _fig(title, height=300)
    fig.add_trace(go.Bar(
        y=segment_counts.index.astype(str),
        x=segment_counts.values,
        orientation="h",
        marker=dict(color=PALETTE[:len(segment_counts)]),
        hovertemplate="<b>%{y}</b><br>Count: %{x:,}<extra></extra>"
    ))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig


# ── Helper ────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#RRGGBB' to (R, G, B) integers."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

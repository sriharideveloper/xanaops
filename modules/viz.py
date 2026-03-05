"""
╔══════════════════════════════════════════════════════════════╗
║  XANA OS v4.0 — VISUALIZATION ENGINE                         ║
╚══════════════════════════════════════════════════════════════╝

3D Neural Map, 2D Cluster Projection, Temporal Heatmaps,
Entity Relationship Graphs.
"""

import re
import math
import datetime
import numpy as np
import networkx as nx
import plotly.graph_objects as go
from collections import Counter, defaultdict

# ── Shared Plotly Layout Theme ───────────────────────────────

PLOTLY_DARK_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Share Tech Mono", size=10, color="rgba(200,220,240,0.7)"),
    hoverlabel=dict(
        bgcolor="rgba(10,10,20,0.95)",
        bordercolor="#00f0ff",
        font=dict(family="Share Tech Mono", size=12, color="#e0f0ff"),
    ),
)


def _extract_keywords(text, n=3):
    """Extract top keywords from text."""
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    stop = {
        'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they',
        'their', 'what', 'when', 'where', 'which', 'about', 'would', 'could',
        'should', 'there', 'these', 'those', 'than', 'then', 'them', 'your',
        'into', 'some', 'other', 'more', 'also', 'just', 'like', 'very',
        'user', 'asked', 'answered', 'here', 'will', 'each', 'make',
    }
    filtered = [w for w in words if w not in stop]
    return [w for w, _ in Counter(filtered).most_common(n)]


def build_3d_neural_map(results_data, query, n_results=20):
    """Build a full 3D force-directed semantic graph from query results."""
    docs = results_data["docs"][:n_results]
    metas = results_data["metas"][:n_results]
    distances = results_data["distances"][:n_results]

    if not docs:
        return None

    G = nx.Graph()
    G.add_node("CORE", label=query.upper(), size=30, color="#00f0ff",
               hover=f"<b>CORE QUERY</b><br>{query}", group="core")

    categories = defaultdict(list)
    node_ids = []

    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
        title = meta.get("title", "Unknown")
        date = meta.get("date", "").split(" ")[0]
        clean = doc.replace("USER ASKED:", "").replace("AI ANSWERED:", "").strip()
        snippet = clean[:40] + "…" if len(clean) > 40 else clean
        keywords = _extract_keywords(clean)
        similarity = max(0, 100 - dist * 50)

        if similarity > 80:
            color = "#00ff88"
        elif similarity > 60:
            color = "#00f0ff"
        elif similarity > 40:
            color = "#ffaa00"
        else:
            color = "#ff00ff"

        node_size = 8 + (similarity / 100) * 16
        nid = f"mem_{i}"
        hover = (f"<b>{title}</b><br>Date: {date}<br>"
                 f"Match: {similarity:.1f}%<br>"
                 f"Keywords: {', '.join(keywords)}<br><br>"
                 f"{clean[:250]}…")

        G.add_node(nid, label=snippet, size=node_size, color=color,
                   hover=hover, group=title, keywords=keywords, similarity=similarity)
        G.add_edge("CORE", nid, weight=similarity / 100)
        node_ids.append(nid)
        categories[title].append(nid)

    # Keyword cluster nodes
    all_kw = []
    for nid in node_ids:
        all_kw.extend(G.nodes[nid].get("keywords", []))
    top_keywords = [w for w, c in Counter(all_kw).most_common(8) if c > 1]

    for kw in top_keywords:
        kwid = f"kw_{kw}"
        G.add_node(kwid, label=kw.upper(), size=14, color="#ff00ff",
                   hover=f"<b>CLUSTER: {kw.upper()}</b><br>Recurring theme", group="keyword")
        for nid in node_ids:
            if kw in G.nodes[nid].get("keywords", []):
                G.add_edge(kwid, nid, weight=0.5)

    # Cross-link same-conversation memories
    for cat, nids in categories.items():
        for i in range(len(nids)):
            for j in range(i + 1, len(nids)):
                G.add_edge(nids[i], nids[j], weight=0.3)

    # 3D layout
    pos_3d = nx.spring_layout(G, dim=3, k=1.5, iterations=60, seed=42)

    edge_traces = []
    for edge in G.edges(data=True):
        x0, y0, z0 = pos_3d[edge[0]]
        x1, y1, z1 = pos_3d[edge[1]]
        weight = edge[2].get("weight", 0.3)
        opacity = min(0.7, weight * 0.8 + 0.1)
        edge_traces.append(go.Scatter3d(
            x=[x0, x1, None], y=[y0, y1, None], z=[z0, z1, None],
            mode="lines",
            line=dict(width=1.5, color=f"rgba(0,240,255,{opacity})"),
            hoverinfo="none", showlegend=False,
        ))

    node_x, node_y, node_z = [], [], []
    node_colors, node_sizes, node_texts, node_hovers = [], [], [], []
    for nid, data in G.nodes(data=True):
        x, y, z = pos_3d[nid]
        node_x.append(x); node_y.append(y); node_z.append(z)
        node_colors.append(data.get("color", "#00f0ff"))
        node_sizes.append(data.get("size", 10))
        node_texts.append(data.get("label", nid)[:20])
        node_hovers.append(data.get("hover", ""))

    node_trace = go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode="markers+text",
        text=node_texts, hovertext=node_hovers, hoverinfo="text",
        textposition="top center",
        textfont=dict(size=8, color="rgba(200,220,240,0.8)"),
        marker=dict(size=node_sizes, color=node_colors,
                    line=dict(width=0.5, color="rgba(255,255,255,0.3)"), opacity=0.9),
        showlegend=False,
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, showbackground=False),
            yaxis=dict(visible=False, showbackground=False),
            zaxis=dict(visible=False, showbackground=False),
            bgcolor="rgba(0,0,0,0)",
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.0)),
        ),
        margin=dict(l=0, r=0, t=0, b=0), height=700,
        **PLOTLY_DARK_THEME,
    )
    return fig


def build_2d_cluster_map(docs, metas, distances, query):
    """Build a 2D cluster visualization."""
    if not docs:
        return None

    titles = [m.get("title", "Unknown") for m in metas]
    unique_titles = list(set(titles))
    title_angles = {t: (2 * math.pi * i / max(len(unique_titles), 1))
                    for i, t in enumerate(unique_titles)}

    x_vals, y_vals = [], []
    for dist, title in zip(distances, titles):
        angle = title_angles[title] + np.random.normal(0, 0.3)
        radius = dist * 2 + np.random.normal(0, 0.1)
        x_vals.append(radius * math.cos(angle))
        y_vals.append(radius * math.sin(angle))

    similarities = [max(0, 100 - d * 50) for d in distances]
    colors = []
    for sim in similarities:
        if sim > 80: colors.append("#00ff88")
        elif sim > 60: colors.append("#00f0ff")
        elif sim > 40: colors.append("#ffaa00")
        else: colors.append("#ff00ff")

    snippets = []
    for doc in docs:
        clean = doc.replace("USER ASKED:", "").replace("AI ANSWERED:", "").strip()
        snippets.append(clean[:60] + "…" if len(clean) > 60 else clean)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers+text",
        marker=dict(size=20, color="#00f0ff", symbol="diamond",
                    line=dict(width=2, color="white")),
        text=[query.upper()], textposition="top center",
        textfont=dict(size=12, color="#00f0ff", family="Orbitron"),
        hoverinfo="text", hovertext=f"<b>QUERY CENTER</b><br>{query}", showlegend=False,
    ))

    hover_texts = []
    for doc, meta, sim in zip(docs, metas, similarities):
        clean = doc.replace("USER ASKED:", "").replace("AI ANSWERED:", "").strip()
        title = meta.get("title", "Unknown")
        date = meta.get("date", "").split(" ")[0]
        hover_texts.append(
            f"<b>{title}</b><br>Date: {date}<br>Match: {sim:.1f}%<br><br>{clean[:200]}…"
        )

    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals, mode="markers+text",
        marker=dict(size=[6 + s / 8 for s in similarities], color=colors,
                    line=dict(width=0.5, color="rgba(255,255,255,0.3)"), opacity=0.85),
        text=[s[:15] for s in snippets], textposition="top center",
        textfont=dict(size=7, color="rgba(200,220,240,0.6)"),
        hovertext=hover_texts, hoverinfo="text", showlegend=False,
    ))

    for x, y, sim in zip(x_vals, y_vals, similarities):
        fig.add_trace(go.Scatter(
            x=[0, x], y=[0, y], mode="lines",
            line=dict(width=0.8, color=f"rgba(0,240,255,{sim/200})"),
            hoverinfo="none", showlegend=False,
        ))

    fig.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0), height=600,
        **PLOTLY_DARK_THEME,
    )
    return fig


def build_temporal_heatmap(metas):
    """Build temporal analysis charts from metadata timestamps."""
    date_counts = Counter()
    hour_counts = Counter()
    dow_counts = Counter()

    for meta in metas:
        date_str = meta.get("date", "")
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            date_counts[dt.strftime("%Y-%m-%d")] += 1
            hour_counts[dt.hour] += 1
            dow_counts[dt.strftime("%A")] += 1
        except (ValueError, TypeError):
            continue

    if not hour_counts:
        return None

    hours = list(range(24))
    counts = [hour_counts.get(h, 0) for h in hours]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=hours, y=counts,
        marker=dict(color=counts,
                    colorscale=[[0, "#0a0a1a"], [0.5, "#00f0ff"], [1, "#ff00ff"]],
                    line=dict(width=0)),
        hovertemplate="Hour %{x}:00<br>Activity: %{y}<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(title="Hour of Day",
                   tickvals=list(range(0, 24, 3)),
                   ticktext=[f"{h:02d}:00" for h in range(0, 24, 3)],
                   gridcolor="rgba(0,240,255,0.05)", color="rgba(0,240,255,0.5)"),
        yaxis=dict(title="Message Frequency",
                   gridcolor="rgba(0,240,255,0.05)", color="rgba(0,240,255,0.5)"),
        margin=dict(l=40, r=20, t=10, b=40), height=300,
        **PLOTLY_DARK_THEME,
    )
    return fig, date_counts, dow_counts


def build_entity_graph(entities):
    """Build a network graph from extracted entities."""
    G = nx.Graph()

    colors_map = {
        "people": "#00f0ff",
        "organizations": "#ff00ff",
        "locations": "#00ff88",
        "technologies": "#ffaa00",
        "events": "#ff003c",
    }

    for category, color in colors_map.items():
        for entity in entities.get(category, []):
            G.add_node(entity, color=color, category=category,
                       size=15 + len(entity))

    for rel in entities.get("relationships", []):
        src = rel.get("source", "")
        tgt = rel.get("target", "")
        rtype = rel.get("type", "related")
        if src in G.nodes and tgt in G.nodes:
            G.add_edge(src, tgt, label=rtype)

    if len(G.nodes) < 2:
        return None

    pos = nx.spring_layout(G, k=2, seed=42)

    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]
        x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1, color="rgba(0,240,255,0.3)"),
        hoverinfo="none", showlegend=False,
    ))

    for category, color in colors_map.items():
        cat_nodes = [n for n, d in G.nodes(data=True) if d.get("category") == category]
        if not cat_nodes:
            continue
        fig.add_trace(go.Scatter(
            x=[pos[n][0] for n in cat_nodes],
            y=[pos[n][1] for n in cat_nodes],
            mode="markers+text",
            marker=dict(size=[G.nodes[n]["size"] for n in cat_nodes],
                        color=color, line=dict(width=1, color="white")),
            text=cat_nodes, textposition="top center",
            textfont=dict(size=9, color="rgba(200,220,240,0.8)", family="Share Tech Mono"),
            name=category.upper(),
            hovertext=[f"<b>{n}</b><br>Type: {category}" for n in cat_nodes],
            hoverinfo="text",
        ))

    fig.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0), height=500, showlegend=True,
        legend=dict(font=dict(color="rgba(200,220,240,0.7)", family="Share Tech Mono")),
        **PLOTLY_DARK_THEME,
    )
    return fig

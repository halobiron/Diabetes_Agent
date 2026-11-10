import networkx as nx
from collections import Counter
kb = json.loads((ROOT / "data" / "snapshots" / "diabetes_kb_snapshot.json").read_text(encoding="utf-8-sig"))
G = nx.DiGraph()
for e in kb["entities"]:
    G.add_node(e["id"], name=e["name"], label=e["label"])
for r in kb["relations"]:
    G.add_edge(r["from"], r["to"], type=r["type"])
colors = {"Condition": "#d64545", "RiskFactor": "#f0a030", "Test": "#3b73d9", "Intervention": "#2f9e6b"}
pos = nx.spring_layout(G.to_undirected(), seed=7, k=1.6, iterations=400)
import textwrap
fig, ax = plt.subplots(figsize=(8.6, 6.8)); ax.axis("off")
nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#9aa0b4", arrows=True, arrowsize=8, width=.8, alpha=.8,
                       connectionstyle="arc3,rad=0.06", node_size=2300)
nx.draw_networkx_nodes(G, pos, ax=ax, node_size=2300, node_color=[colors[G.nodes[n]["label"]] for n in G], alpha=.95)
nx.draw_networkx_labels(G, pos, labels={n: textwrap.fill(G.nodes[n]["name"], 14) for n in G},
                        font_size=5.2, ax=ax)
for lab, c in colors.items():
    ax.scatter([], [], c=c, label=lab, s=60)
ax.legend(loc="upper center", bbox_to_anchor=(.5, 0.02), ncol=4, fontsize=8, frameon=False)
fig.tight_layout(); fig.savefig(OUT / "fig_kg.png", dpi=170); plt.show()

# Bảng thống kê KB cho báo cáo
ent = Counter(e["label"] for e in kb["entities"]); rel = Counter(r["type"] for r in kb["relations"])
left = [f"{k} & {v}" for k, v in sorted(ent.items())] + ["Đoạn bằng chứng & " + str(len(kb["evidence"])), "Nguồn & " + str(len(kb["sources"]))]
right = [f"{k.replace('_', chr(92) + '_')} & {v}" for k, v in sorted(rel.items())]
n = max(len(left), len(right)); left += ["&"] * (n - len(left)); right += ["&"] * (n - len(right))
body = "\n".join(f"{a} & {b} \\\\" for a, b in zip(left, right))
tex = ("\\begin{tabular}{@{}lr@{\\hspace{2em}}lr@{}}\n\\toprule\n\\textbf{Nút / dữ liệu} & \\textbf{SL} & \\textbf{Loại quan hệ} & \\textbf{SL}\\\\\n\\midrule\n"
       + body + "\n\\bottomrule\n\\end{tabular}\n")
(TAB / "tab_kb.tex").write_text(tex, encoding="utf-8")
print(len(kb["entities"]), "thực thể,", len(kb["relations"]), "quan hệ,", len(kb["evidence"]), "bằng chứng,", len(kb["sources"]), "nguồn")

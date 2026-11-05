bands = metrics["risk_bands"]; thr = metrics["selected_threshold"]
fig, ax = plt.subplots(figsize=(7, 3.2))
bins = np.linspace(0, 1, 61)
ax.hist(p_test[y_test == 0], bins=bins, alpha=.7, color="#c9d3f2", label="Nhãn 0")
ax.hist(p_test[y_test == 1], bins=bins, alpha=.8, color="#4b3fa8", label="Nhãn 1")
ax.set_yscale("log")
ax.axvline(bands["low_max"], color="#c78a00", ls="--"); ax.axvline(bands["high_min"], color="#b3261e", ls="--")
ymax = ax.get_ylim()[1]
ax.text(bands["low_max"] + .005, ymax * .5, f"low_max = {bands['low_max']:.3f}", color="#c78a00", fontsize=8)
ax.text(bands["high_min"] + .005, ymax * .2, f"high_min = {bands['high_min']:.3f}", color="#b3261e", fontsize=8)
ax.set_xlabel("Xác suất dự đoán"); ax.set_ylabel("Số hồ sơ (thang log)"); ax.legend(fontsize=8, frameon=False)
fig.tight_layout(); fig.savefig(OUT / "fig_bands.png"); plt.show()

from tools.risk_classifier import classify_risk
level = pd.Series([classify_risk(p, bands) for p in p_test])
rows = []
for lv, name in [("Low", "Thấp"), ("Medium", "Trung bình"), ("High", "Cao")]:
    mask = (level == lv).values
    n, k = int(mask.sum()), int(y_test.values[mask].sum())
    dot = lambda v: f"{v:,}".replace(",", ".")          # dấu chấm ngăn cách hàng nghìn
    rows.append(f"{name} & {dot(n)} & {dot(k)} & {vn(100 * k / n, 1)}\\% \\\\")
tex = ("\\begin{tabular}{@{}lccc@{}}\n\\toprule\n\\textbf{Mức} & \\textbf{Số ca} & \\textbf{Nhãn 1} & \\textbf{Tỉ lệ nhãn 1}\\\\\n\\midrule\n"
       + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")
(TAB / "tab_bands.tex").write_text(tex, encoding="utf-8")
print(level.value_counts())

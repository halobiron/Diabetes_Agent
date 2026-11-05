order = ["logistic_regression", "random_forest", "lightgbm", "hist_gradient_boosting", "mlp"]
labels = {"logistic_regression": "Hồi quy\nlogistic", "random_forest": "Rừng\nngẫu nhiên", "lightgbm": "LightGBM",
          "hist_gradient_boosting": "HistGradient\nBoosting", "mlp": "MLP\n(PyTorch)"}
M = metrics["metrics"]
cv = [M[m]["cv"]["roc_auc_mean"] for m in order]
cv_sd = [M[m]["cv"]["roc_auc_std"] for m in order]
va = [M[m]["validation"]["roc_auc"] for m in order]
te = [M[m]["test"]["roc_auc"] for m in order]
x = np.arange(len(order)); w = .26
fig, ax = plt.subplots(figsize=(7.2, 3.4))
ax.bar(x - w, cv, w, yerr=cv_sd, capsize=3, label="CV 5-fold (TB ± độ lệch)", color="#c9d3f2")
ax.bar(x, va, w, label="Kiểm định", color="#8a7fd6")
ax.bar(x + w, te, w, label="Kiểm tra", color="#4b3fa8")
ax.set_ylim(.81, .838); ax.set_xticks(x, [labels[m] for m in order]); ax.set_ylabel("ROC-AUC")
ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper center")
fig.tight_layout(); fig.savefig(OUT / "fig_model_compare.png"); plt.show()

# Bảng LaTeX cho báo cáo (Bảng kết quả năm mô hình)
names_vi = {"logistic_regression": "Hồi quy logistic", "random_forest": "Rừng ngẫu nhiên", "lightgbm": "LightGBM",
            "hist_gradient_boosting": "HistGradientBoosting", "mlp": r"\textbf{MLP (được chọn)}"}
rows = []
for m in order:
    t = M[m]["test"]
    rows.append(f"{names_vi[m]} & ${vn(M[m]['cv']['roc_auc_mean'])}\\pm{vn(M[m]['cv']['roc_auc_std'])}$ & "
                f"{vn(M[m]['validation']['roc_auc'])} & {vn(t['roc_auc'])} & {vn(t['average_precision'], 3)} & {vn(t['brier_score'])} \\\\")
tex = ("\\begin{tabular}{@{}lccccc@{}}\n\\toprule\n"
       "\\textbf{Mô hình} & \\textbf{CV AUC} & \\textbf{Kiểm định} & \\textbf{Kiểm tra} & \\textbf{AP (kiểm tra)} & \\textbf{Brier}\\\\\n\\midrule\n"
       + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")
(TAB / "tab_models.tex").write_text(tex, encoding="utf-8")
print(pd.DataFrame({"cv": cv, "val": va, "test": te}, index=order).round(5))

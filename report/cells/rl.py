comp = json.loads((ROOT / "artifacts" / "policy_comparison.json").read_text(encoding="utf-8"))
keys = ["q_learning", "fixed_full_checklist", "fixed_risk_only", "random"]
names = ["Q-learning", "Bảng kiểm\ncố định", "Chỉ theo\nmức rủi ro", "Ngẫu nhiên"]
rew = [comp[k]["mean_reward"] for k in keys]; ci = [comp[k]["ci95"] for k in keys]
under = [comp[k]["under_triage_rate"] * 100 for k in keys]
fig, axes = plt.subplots(1, 2, figsize=(8, 3.3))
axes[0].bar(names, rew, yerr=ci, capsize=3, color=["#4b3fa8", "#8a7fd6", "#c9d3f2", "#d9d9d9"])
axes[0].set_ylabel("Reward trung bình (±95% CI)"); axes[0].axhline(0, color="black", lw=.6)
axes[1].bar(names, under, color=["#4b3fa8", "#8a7fd6", "#c9d3f2", "#d9d9d9"])
axes[1].set_ylabel("Bỏ sót ca cần chuyển tuyến (%)")
for a in axes: a.tick_params(axis="x", labelsize=7.5)
fig.tight_layout(); fig.savefig(OUT / "fig_rl_compare.png"); plt.show()

label = ["Q-learning", "Bảng kiểm cố định", "Chỉ theo mức rủi ro", "Ngẫu nhiên"]
rows = [f"{l} & ${vn(comp[k]['mean_reward'], 3)}\\pm{vn(comp[k]['ci95'], 3)}$ & {vn(comp[k]['mean_steps'], 2)} & "
        f"{vn(comp[k]['under_triage_rate'] * 100, 2)}\\% & {vn(comp[k]['over_escalation_rate'] * 100, 2)}\\% \\\\"
        for l, k in zip(label, keys)]
tex = ("\\begin{tabular}{@{}lcccc@{}}\n\\toprule\n\\textbf{Chiến lược} & \\textbf{Reward TB $\\pm$ 95\\% CI} & \\textbf{Số bước} & \\textbf{Bỏ sót} & \\textbf{Chuyển thừa}\\\\\n\\midrule\n"
       + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")
(TAB / "tab_rl.tex").write_text(tex, encoding="utf-8")
print(comp["q_learning"])

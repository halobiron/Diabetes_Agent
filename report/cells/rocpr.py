from sklearn.metrics import roc_curve, precision_recall_curve, roc_auc_score, average_precision_score
artifact = joblib.load(ROOT / "artifacts" / "risk_model.joblib")
model = artifact["model"]
p_test = model.predict_proba(X_test[artifact["feature_names"]])[:, 1]
print("ROC-AUC", round(roc_auc_score(y_test, p_test), 5), "AP", round(average_precision_score(y_test, p_test), 5))

fpr, tpr, _ = roc_curve(y_test, p_test)
prec, rec, _ = precision_recall_curve(y_test, p_test)
fig, axes = plt.subplots(1, 2, figsize=(8, 3.5))
axes[0].plot(fpr, tpr, color="#4b3fa8", label=f"MLP hiệu chuẩn (AUC {roc_auc_score(y_test, p_test):.3f})")
axes[0].plot([0, 1], [0, 1], "--", color="gray"); axes[0].set_xlabel("FPR"); axes[0].set_ylabel("TPR")
axes[0].set_title("Đường ROC"); axes[0].legend(fontsize=8, frameon=False, loc="lower right")
axes[1].plot(rec, prec, color="#4b3fa8", label=f"AP {average_precision_score(y_test, p_test):.3f}")
axes[1].axhline(y_test.mean(), ls="--", color="gray", label=f"tỉ lệ nền {y_test.mean():.3f}")
axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision"); axes[1].set_title("Đường Precision–Recall")
axes[1].legend(fontsize=8, frameon=False)
fig.tight_layout(); fig.savefig(OUT / "fig_roc_pr.png"); plt.show()

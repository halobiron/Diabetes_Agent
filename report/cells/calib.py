from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss
frac, mean_p = calibration_curve(y_test, p_test, n_bins=10, strategy="quantile")
fig, ax = plt.subplots(figsize=(4.4, 4))
ax.plot([0, 1], [0, 1], "--", color="gray", label="Hiệu chuẩn lý tưởng")
ax.plot(mean_p, frac, "o-", color="#4b3fa8", label=f"MLP (Brier {brier_score_loss(y_test, p_test):.4f})")
ax.set_xlabel("Xác suất dự đoán trung bình"); ax.set_ylabel("Tỉ lệ dương thực tế"); ax.legend(fontsize=8, frameon=False)
fig.tight_layout(); fig.savefig(OUT / "fig_calibration.png"); plt.show()

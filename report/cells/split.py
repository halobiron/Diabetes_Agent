from sklearn.model_selection import train_test_split
from models.training_pipeline import FEATURE_NAMES, TARGET_COLUMN, RANDOM_STATE, TEST_SIZE, VALIDATION_SIZE

df = pd.read_csv(ROOT / "data" / "training" / "diabetes_binary_health_indicators_BRFSS2015.csv")
X, y = df[FEATURE_NAMES], df[TARGET_COLUMN].astype(int)
X_dev, X_test, y_dev, y_test = train_test_split(X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y)
X_train, X_val, y_train, y_val = train_test_split(X_dev, y_dev, test_size=VALIDATION_SIZE, random_state=RANDOM_STATE, stratify=y_dev)
print(len(X_train), len(X_val), len(X_test), "| positive rate:", round(y.mean(), 4))
assert (len(X_train), len(X_val), len(X_test)) == (metrics["rows_train"], metrics["rows_validation"], metrics["rows_test"])

fig, ax = plt.subplots(figsize=(6.4, 2.6))
sizes = [len(X_train), len(X_val), len(X_test)]
pos = [y_train.sum(), y_val.sum(), y_test.sum()]
names = ["Huấn luyện (60%)", "Kiểm định (20%)", "Kiểm tra (20%)"]
ax.barh(names[::-1], sizes[::-1], color="#c9d3f2", label="Nhãn 0")
ax.barh(names[::-1], pos[::-1], color="#4b3fa8", label="Nhãn 1 (tiền ĐTĐ hoặc ĐTĐ)")
for i, (s, p) in enumerate(zip(sizes[::-1], pos[::-1])):
    ax.text(s + 2000, i, f"{s:,} ({p/s:.1%} dương)".replace(",", "."), va="center", fontsize=8)
ax.set_xlim(0, 230000); ax.set_xlabel("Số hồ sơ"); ax.legend(loc="lower right", fontsize=8, frameon=False)
fig.tight_layout(); fig.savefig(OUT / "fig_split.png"); plt.show()

from sklearn.metrics import confusion_matrix
pred = (p_test >= thr).astype(int)
tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
print(dict(tn=tn, fp=fp, fn=fn, tp=tp), "precision", round(tp/(tp+fp), 4), "recall", round(tp/(tp+fn), 4))
assert (tn, fp, fn, tp) == tuple(metrics["metrics"]["mlp"]["test"]["confusion_matrix"].values())

fig, ax = plt.subplots(figsize=(3.8, 3.4))
cm = np.array([[tn, fp], [fn, tp]])
ax.imshow(cm, cmap="Purples"); ax.grid(False)
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm[i, j]:,}".replace(",", "."), ha="center", va="center", color="white" if cm[i, j] > 20000 else "black")
ax.set_xticks([0, 1], ["Dự đoán 0", "Dự đoán 1"]); ax.set_yticks([0, 1], ["Thực tế 0", "Thực tế 1"])
ax.set_title(f"Ngưỡng {thr:.3f}", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "fig_confusion.png"); plt.show()

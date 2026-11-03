import { Sparkles } from "lucide-react";

export function EmptyState() {
  return (
    <div className="console-panel rounded-lg p-8">
      <div className="flex max-w-2xl items-start gap-4">
        <div className="rounded-md border border-borderSoft bg-info/10 p-3 text-info">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-xl font-semibold">Sẵn sàng đánh giá</h3>
          <p className="mt-2 text-sm leading-6 text-muted">
            Nhập thông tin bệnh nhân ở bảng bên trái, sau đó chọn Phân tích hồ sơ để xem kết quả.
          </p>
        </div>
      </div>
    </div>
  );
}

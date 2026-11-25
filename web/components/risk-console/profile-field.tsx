export type ProfileLookupState = {
  status: "idle" | "loading" | "loaded" | "not_found" | "error";
  message?: string;
};

export function ProfileField({ value, state, onChange, onLoad }: {
  value: string;
  state: ProfileLookupState;
  onChange: (value: string) => void;
  onLoad: () => Promise<boolean>;
}) {
  return (
    <div className="space-y-2">
      <label htmlFor="patient-id" className="field-label block">Mã hồ sơ (nếu đã có)</label>
      <div className="flex flex-wrap gap-2">
        <input
          id="patient-id"
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onBlur={() => { void onLoad(); }}
          onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void onLoad(); } }}
          maxLength={64}
          autoCapitalize="none"
          autoComplete="off"
          spellCheck={false}
          aria-describedby="patient-id-help patient-id-status"
          aria-invalid={state.status === "error"}
          className="min-h-12 w-full min-w-0 rounded-xl border-2 border-borderSoft bg-canvas px-3 text-base focus:border-info focus:outline-none sm:w-auto sm:flex-1"
          placeholder="Nhập mã để nạp hồ sơ cũ"
        />
      </div>
      <p id="patient-id-help" className="text-sm text-muted">Nhấn Enter hoặc rời ô nhập để nạp lần gần nhất. Bạn chỉ cần sửa thông tin thay đổi. Để trống để tạo hồ sơ mới.</p>
      <p id="patient-id-status" role={state.status === "error" ? "alert" : "status"} className={`text-sm ${state.status === "error" ? "text-danger" : state.status === "loaded" ? "text-success" : "text-muted"}`}>
        {state.status === "loading" ? "Đang nạp hồ sơ…" : state.message}
      </p>
    </div>
  );
}

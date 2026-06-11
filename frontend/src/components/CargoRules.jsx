// §6: подсказки документов и несовместимости грузов — общий блок для карточек.
export default function CargoRules({ r }) {
  if (!r.required_docs?.length && !r.incompatible_with?.length) return null;
  return (
    <div className="cargo-rules">
      {r.required_docs?.length > 0 && (
        <div className="docs-line">
          <span className="docs-ico">📋</span> Документы: {r.required_docs.join(" + ")}
        </div>
      )}
      {r.incompatible_with?.length > 0 && (
        <div className="incompat-line">
          ⚠ Нельзя совмещать с: {r.incompatible_with.join(", ")}
        </div>
      )}
    </div>
  );
}

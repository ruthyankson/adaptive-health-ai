import pyreadstat
import pandas as pd
from src.utils.constants import DATA_PATH, COLUMNS_OUT_PATH


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing file: {DATA_PATH.resolve()}")

    df, meta = pyreadstat.read_xport(
        str(DATA_PATH),
        encoding="latin1",
    )
    print("Loaded:", DATA_PATH)
    print("Shape:", df.shape)
    print("Total columns:", len(df.columns))
    print("First columns:", list(df.columns[:10]))
    
    # Ensure output directory exists
    COLUMNS_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Build a safe {column_name: label} mapping.
    # In some pyreadstat versions, meta.column_labels is a list aligned to df.columns.
    labels_map = {}

    if hasattr(meta, "column_labels") and meta.column_labels is not None:
        if isinstance(meta.column_labels, dict):
            labels_map = meta.column_labels
        elif isinstance(meta.column_labels, list) and len(meta.column_labels) == len(
            df.columns
        ):
            labels_map = dict(zip(df.columns, meta.column_labels))

    cols_df = pd.DataFrame(
        {
            "column_name": df.columns,
            "label": [labels_map.get(c, "") for c in df.columns],
        }
    )

    cols_df.to_csv(COLUMNS_OUT_PATH, index=False)
    print(
        f"Wrote {len(cols_df)} \
        columns with labels to {COLUMNS_OUT_PATH.resolve()}"
    )


if __name__ == "__main__":
    main()

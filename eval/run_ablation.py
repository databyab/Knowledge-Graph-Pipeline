import csv
from pathlib import Path

import yaml


def main() -> None:
    root = Path(__file__).resolve().parent
    configurations = yaml.safe_load((root / "ablations" / "baseline.yaml").read_text(encoding="utf-8"))
    with (root / "results" / "ablation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["provider", "model_env", "prompt_version", "use_ontology", "use_er", "chunk_words"])
        writer.writeheader()
        writer.writerows(configurations)
    (root / "results" / "ablation.md").write_text("|provider|model_env|prompt_version|use_ontology|use_er|chunk_words|\n|---|---|---|---|---|---|\n", encoding="utf-8")


if __name__ == "__main__":
    main()

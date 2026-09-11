"""원본 CSV를 보존하고 날짜별 시연 주문·차량 근무 CSV를 만든다. TMS 등록은 하지 않는다."""

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.days <= 31:
        parser.error("--days는 1~31이어야 합니다")
    if args.output.exists():
        parser.error("출력 폴더가 이미 있습니다. 새 폴더를 지정하세요")
    generated = {}
    for filename in ("centers.csv", "branches.csv", "delivery_orders.csv", "vehicles.csv"):
        fields, source = read_csv(ROOT / "agent/data" / filename)
        rows = [dict(row) for row in source]
        if filename in {"delivery_orders.csv", "vehicles.csv"}:
            for offset in range(args.days):
                day = args.start_date + timedelta(days=offset)
                for original in source:
                    row = dict(original)
                    row["updateDate"] = f"{day} 06:00:00"
                    if filename == "delivery_orders.csv":
                        row["deliveryDate"] = str(day)
                        row["orderId"] = f"ORD-{day:%Y%m%d}-{original['orderId'].rsplit('-', 1)[1]}"
                    else:
                        for field in ("shift_start", "shift_end"):
                            row[field] = str(day) + original[field][10:]
                    rows.append(row)
            if filename == "delivery_orders.csv":
                rows = list({row["orderId"]: row for row in rows}.values())
                for seq, row in enumerate(rows, 1):
                    row["seq"] = str(seq)
            else:
                unique = {(row["vehicleId"], row["shift_start"][:10]): row for row in rows}
                rows = list(unique.values())
        generated[filename] = fields, rows
    args.output.mkdir(parents=True)
    for filename, (fields, rows) in generated.items():
        with (args.output / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"{filename}: {len(rows)}건")
    print("생성한 CSV의 절대 경로를 BADARO_DATA_DIR에 지정하세요. 실제 TMS 등록은 별도입니다.")


if __name__ == "__main__":
    main()

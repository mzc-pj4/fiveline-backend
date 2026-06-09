"""
크롤링된 JSON을 DB에 삽입 (pod 내부에서 실행).
사용법: python scripts/insert_products.py products.json [--force]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db.session import SessionLocal
from app.models.product import Product


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    data = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    print(f"JSON 로드: {len(data)}개")

    with SessionLocal() as db:
        existing = db.query(Product).count()
        if existing > 0 and not args.force:
            print(f"이미 {existing}개 존재. --force 로 강제 실행")
            return
        if args.force:
            db.query(Product).delete()
            db.commit()
            print("기존 상품 삭제 완료")

        for item in data:
            db.add(Product(
                name=item["name"],
                description=None,
                category=item["category"],
                brand=item["brand"],
                price=item["price"],
                original_price=item.get("original_price"),
                stock_quantity=item.get("stock_quantity", 50),
                image_url=item["image_url"],
            ))
        db.commit()

    print(f"완료: {len(data)}개 삽입됨")
    cats = {}
    for item in data:
        cats[item["category"]] = cats.get(item["category"], 0) + 1
    for cat, cnt in sorted(cats.items()):
        print(f"  {cat}: {cnt}개")


if __name__ == "__main__":
    raise SystemExit(main())

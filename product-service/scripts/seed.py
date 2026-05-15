"""Seed sample products. Idempotent: skips if products already exist."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.product import Product

SAMPLE_PRODUCTS = [
    ("무선 이어폰 Air Pro", "노이즈 캔슬링 무선 이어폰", "electronics", Decimal("129000"), 50, None),
    ("기계식 키보드 87키", "체리 적축, 백라이트", "electronics", Decimal("159000"), 30, None),
    ("4K 모니터 27인치", "IPS 패널, USB-C", "electronics", Decimal("389000"), 15, None),
    ("게이밍 마우스 RGB", "16000DPI, 무선·유선 겸용", "electronics", Decimal("89000"), 80, None),
    ("USB-C 허브 7-in-1", "HDMI/USB3.0/SD/RJ45", "electronics", Decimal("45000"), 120, None),

    ("러닝화 Cloud Run", "쿠셔닝 강화, 295g", "fashion", Decimal("159000"), 40, None),
    ("백팩 25L 방수", "노트북 15인치 수납", "fashion", Decimal("79000"), 60, None),
    ("후드티 옥스포드", "겨울용 기모, 무지", "fashion", Decimal("49000"), 100, None),

    ("스탠다드 텀블러 500ml", "보온 12시간, 보냉 24시간", "kitchen", Decimal("32000"), 200, None),
    ("프렌치 프레스 1L", "스테인리스 필터", "kitchen", Decimal("28000"), 80, None),

    ("스마트 LED 전구 E26", "Wi-Fi, 1600만색", "home", Decimal("19900"), 300, None),
    ("로봇 청소기 미니", "충전 도크 포함", "home", Decimal("249000"), 20, None),
]


def main() -> int:
    with SessionLocal() as db:
        existing = db.query(Product).count()
        if existing > 0:
            print(f"products table already has {existing} rows; skipping seed.")
            return 0

        for name, desc, category, price, stock, image_url in SAMPLE_PRODUCTS:
            db.add(
                Product(
                    name=name,
                    description=desc,
                    category=category,
                    price=price,
                    stock_quantity=stock,
                    image_url=image_url,
                )
            )
        db.commit()
        print(f"seeded {len(SAMPLE_PRODUCTS)} products.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

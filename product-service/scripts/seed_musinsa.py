"""
무신사 상품 데이터 수집 후 DB 시드.
- 카테고리(상의/하의/아우터/원피스/가방): page=N URL 직접 이동, 응답 인터셉트
- 신발/액세서리: 키워드 검색 page=1 per keyword (카테고리 코드 미지원)
사용법: python scripts/seed_musinsa.py [--force]
"""
import argparse
import random
import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db.session import SessionLocal
from app.models.product import Product

CATEGORY_FETCH = {
    "상의":   ("001", 500),
    "하의":   ("003", 500),
    "아우터": ("002", 500),
    "원피스": ("100", 500),
    "가방":   ("004", 300),
}

KEYWORD_FETCH = {
    "신발":    (
        ["스니커즈", "구두", "부츠", "슬리퍼", "샌들", "운동화", "하이탑", "로퍼", "워커", "컨버스"],
        500,
    ),
    "액세서리": (
        ["모자", "지갑", "벨트", "양말", "선글라스", "귀걸이"],
        200,
    ),
}


def parse_goods(goods_list: list, category: str) -> list[dict]:
    items = []
    for g in goods_list:
        try:
            name = g.get("goodsName") or g.get("name") or g.get("title") or ""
            brand_raw = g.get("brand") or {}
            brand = (
                g.get("brandName")
                or (brand_raw.get("name") if isinstance(brand_raw, dict) else str(brand_raw))
                or "MUSINSA"
            )
            price = int(g.get("price") or g.get("salePrice") or g.get("finalPrice") or 0)
            normal_price = int(
                g.get("normalPrice") or g.get("originalPrice") or g.get("consumerPrice") or 0
            )
            image_url = (
                g.get("thumbnail") or g.get("imageUrl") or g.get("img") or g.get("image") or ""
            )
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            if image_url.startswith("http://"):
                image_url = image_url.replace("http://", "https://", 1)
            if not name or price == 0 or not image_url:
                continue
            original_price = normal_price if normal_price > price else None
            items.append({
                "name": name,
                "brand": brand,
                "price": price,
                "original_price": original_price,
                "image_url": image_url,
                "category": category,
            })
        except Exception:
            continue
    return items


def fetch_category(cat_code: str, target: int, category: str, browser) -> list[dict]:
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="ko-KR",
    )
    page = context.new_page()
    items: list[dict] = []
    page_num = 1

    while len(items) < target:
        captured: list = []

        def on_response(resp, _c=captured):
            if "api2/dp/v2/plp/goods" in resp.url and resp.status == 200:
                try:
                    data = resp.json()
                    lst = data.get("data", {}).get("list") or data.get("list") or []
                    _c.extend(lst)
                except Exception:
                    pass

        page.on("response", on_response)
        url = (
            f"https://www.musinsa.com/categories/item/{cat_code}"
            f"?d_cat_cd={cat_code}&orderby=pop_category&page={page_num}&viewType=small"
        )
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"  page {page_num}: 실패 ({e})")
            page.remove_listener("response", on_response)
            break
        page.remove_listener("response", on_response)

        batch = parse_goods(captured, category)
        items.extend(batch)
        print(f"  page {page_num}: {len(batch)}개 수집 (누적 {len(items)}개)")

        if len(captured) < 30:
            break
        page_num += 1
        time.sleep(random.uniform(0.3, 0.7))

    context.close()
    return items[:target]


def fetch_keywords(keywords: list[str], target: int, category: str, browser) -> list[dict]:
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="ko-KR",
    )
    page = context.new_page()
    items: list[dict] = []

    for keyword in keywords:
        if len(items) >= target:
            break
        print(f"  키워드: [{keyword}]")

        captured: list = []

        def on_response(resp, _c=captured):
            if "api2/dp/v2/plp/goods" in resp.url and resp.status == 200:
                try:
                    data = resp.json()
                    lst = data.get("data", {}).get("list") or data.get("list") or []
                    _c.extend(lst)
                except Exception:
                    pass

        page.on("response", on_response)
        url = f"https://www.musinsa.com/search/goods?keyword={quote(keyword)}&page=1"
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"    실패: {e}")
            page.remove_listener("response", on_response)
            continue
        page.remove_listener("response", on_response)

        batch = parse_goods(captured, category)
        items.extend(batch)
        print(f"    {len(batch)}개 수집 (누적 {len(items)}개)")
        time.sleep(random.uniform(0.3, 0.7))

    context.close()
    return items[:target]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        existing = db.query(Product).count()
        if existing > 0 and not args.force:
            print(f"이미 {existing}개 상품 존재. --force 로 강제 실행")
            return
        if args.force:
            db.query(Product).delete()
            db.commit()
            print("기존 상품 삭제 완료")

    all_items: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        for category, (cat_code, target) in CATEGORY_FETCH.items():
            print(f"\n[{category}] 카테고리 수집 중... (목표: {target}개)")
            result = fetch_category(cat_code, target, category, browser)
            all_items.extend(result)
            print(f"  → 최종: {len(result)}개")

        for category, (keywords, target) in KEYWORD_FETCH.items():
            print(f"\n[{category}] 키워드 검색 수집 중... (목표: {target}개)")
            result = fetch_keywords(keywords, target, category, browser)
            all_items.extend(result)
            print(f"  → 최종: {len(result)}개")

        browser.close()

    print(f"\n총 {len(all_items)}개 수집. DB 삽입 중...")
    with SessionLocal() as db:
        for item in all_items:
            db.add(Product(
                name=item["name"],
                description=None,
                category=item["category"],
                brand=item["brand"],
                price=item["price"],
                original_price=item.get("original_price"),
                stock_quantity=random.randint(10, 200),
                image_url=item["image_url"],
            ))
        db.commit()

    print(f"\n완료: {len(all_items)}개 무신사 상품 삽입됨")
    for cat in sorted(set(i["category"] for i in all_items)):
        cnt = sum(1 for i in all_items if i["category"] == cat)
        print(f"  {cat}: {cnt}개")


if __name__ == "__main__":
    raise SystemExit(main())

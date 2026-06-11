"""패션 상품 시드 데이터. 멱등: 이미 상품이 있으면 건너뜀."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.product import Product

# (name, description, category, brand, price, original_price, stock, image_url)
FASHION_PRODUCTS = [
    # 상의
    ("MUSINSA STANDARD 베이직 티셔츠 화이트", "고중량 200g 코튼 소재의 베이직 반소매 티셔츠", "상의", "MUSINSA STANDARD", Decimal("19900"), Decimal("24900"), 200, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Basic+Tee+White"),
    ("MUSINSA STANDARD 베이직 티셔츠 블랙", "고중량 200g 코튼 소재의 베이직 반소매 티셔츠", "상의", "MUSINSA STANDARD", Decimal("19900"), Decimal("24900"), 180, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Basic+Tee+Black"),
    ("COVERNAT 오버사이즈 맨투맨 그레이", "프랑스 국기 로고 자수, 기모 안감", "상의", "COVERNAT", Decimal("59000"), None, 80, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Covernat+Sweat"),
    ("THISISNEVERTHAT 로고 후디 네이비", "고중량 플리스 소재, 캥거루 포켓", "상의", "THISISNEVERTHAT", Decimal("89000"), Decimal("109000"), 60, "https://placehold.co/400x500/e5e7eb/9ca3af?text=TNT+Hoodie"),
    ("NIKE 드라이핏 반소매 티셔츠", "땀 배출 드라이핏 소재, 운동용", "상의", "NIKE", Decimal("35000"), Decimal("45000"), 150, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Nike+Dri-Fit"),
    ("ADIDAS 오리지널스 트레포일 티셔츠", "클래식 트레포일 로고, 100% 코튼", "상의", "ADIDAS", Decimal("39000"), Decimal("49000"), 120, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Adidas+Trefoil"),
    ("GRAMICCI 클라이밍 롱슬리브", "스트레치 소재, 아웃도어 활동 최적화", "상의", "GRAMICCI", Decimal("79000"), None, 45, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Gramicci+LS"),
    ("CARHARTT WIP 포켓 티셔츠", "헤비 저지, 가슴 포켓 디테일", "상의", "CARHARTT", Decimal("55000"), Decimal("65000"), 90, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Carhartt+Pocket"),
    ("무신사 스탠다드 스트라이프 티셔츠", "린넨 혼방 시원한 소재, 여름용", "상의", "MUSINSA STANDARD", Decimal("24900"), None, 110, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Stripe+Tee"),
    ("CHAMPION 리버스 위브 크루넥", "미국 정품, 두꺼운 기모 소재", "상의", "CHAMPION", Decimal("75000"), Decimal("89000"), 70, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Champion+Crew"),
    ("POLO RALPH LAUREN 슬림핏 옥스포드", "클래식 버튼다운 셔츠, 면 100%", "상의", "POLO RALPH LAUREN", Decimal("129000"), Decimal("159000"), 55, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Ralph+Lauren+Oxford"),
    ("THE NORTH FACE 반집업 플리스", "폴라텍 100 플리스, 가볍고 따뜻", "상의", "THE NORTH FACE", Decimal("99000"), Decimal("129000"), 40, "https://placehold.co/400x500/e5e7eb/9ca3af?text=TNF+Fleece"),

    # 하의
    ("MUSINSA STANDARD 와이드 데님 청바지", "편안한 와이드핏, 미디엄 워싱", "하의", "MUSINSA STANDARD", Decimal("49900"), Decimal("59900"), 100, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Wide+Denim"),
    ("LEVI'S 501 오리지널 청바지", "클래식 직선 핏 데님, 미드 블루", "하의", "LEVI'S", Decimal("119000"), Decimal("139000"), 85, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Levis+501"),
    ("GRAMICCI 쉘 쇼츠", "나일론 소재 등산/캐주얼 겸용", "하의", "GRAMICCI", Decimal("89000"), None, 60, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Gramicci+Shorts"),
    ("CARHARTT WIP 더블 니 팬츠", "8oz 덕 캔버스, 내구성 강화 무릎", "하의", "CARHARTT", Decimal("129000"), Decimal("149000"), 50, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Carhartt+Double+Knee"),
    ("NIKE 조거 팬츠 블랙", "드라이핏 소재, 사이드 포켓", "하의", "NIKE", Decimal("59000"), Decimal("75000"), 130, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Nike+Jogger"),
    ("ADIDAS 트랙 팬츠 네이비", "3선 클래식 트랙 팬츠, 폴리에스터", "하의", "ADIDAS", Decimal("65000"), Decimal("79000"), 95, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Adidas+Track"),
    ("무신사 스탠다드 슬랙스 차콜", "기본기 탄탄한 세미와이드 슬랙스", "하의", "MUSINSA STANDARD", Decimal("39900"), Decimal("49900"), 75, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Slacks+Charcoal"),
    ("DICKIES 874 워크 팬츠 카키", "폴리/코튼 혼방, 클래식 스트레이트 핏", "하의", "DICKIES", Decimal("69000"), None, 88, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Dickies+874"),
    ("COVERNAT 코듀로이 팬츠 브라운", "가을겨울 코듀로이 소재, 릴렉스핏", "하의", "COVERNAT", Decimal("85000"), Decimal("99000"), 42, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Corduroy+Pants"),
    ("무신사 스탠다드 린넨 반바지", "시원한 린넨 소재 여름 반바지", "하의", "MUSINSA STANDARD", Decimal("29900"), None, 120, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Linen+Shorts"),

    # 아우터
    ("THE NORTH FACE 눕시 다운 자켓 블랙", "700필파워 구스다운, 라이트웨이트", "아우터", "THE NORTH FACE", Decimal("299000"), Decimal("349000"), 30, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Nuptse+Down"),
    ("CARHARTT WIP 미시간 코트 네이비", "면 100% 체스터필드 스타일 코트", "아우터", "CARHARTT", Decimal("239000"), Decimal("279000"), 25, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Michigan+Coat"),
    ("THISISNEVERTHAT L-3B 플라이트 자켓", "밀리터리 플라이트 자켓, 나일론 소재", "아우터", "THISISNEVERTHAT", Decimal("189000"), Decimal("229000"), 35, "https://placehold.co/400x500/e5e7eb/9ca3af?text=L-3B+Flight"),
    ("COVERNAT 멀티 포켓 윈드브레이커", "방풍/발수 가공, 가벼운 착용감", "아우터", "COVERNAT", Decimal("159000"), None, 40, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Windbreaker"),
    ("MUSINSA STANDARD 무스탕 자켓", "쉐르파 플리스 안감, 클래식 스타일", "아우터", "MUSINSA STANDARD", Decimal("89900"), Decimal("109900"), 55, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Mustang+Jacket"),
    ("GRAMICCI 쉘 재킷", "나일론 쉘 소재, 경량 패커블", "아우터", "GRAMICCI", Decimal("179000"), None, 30, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Shell+Jacket"),
    ("NIKE 테크 플리스 자켓", "테크 플리스 소재, 풀집업 후드", "아우터", "NIKE", Decimal("159000"), Decimal("189000"), 65, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Tech+Fleece+Jacket"),
    ("ADIDAS 봄버 자켓 올리브", "폴리에스터 봄버, 리브 디테일", "아우터", "ADIDAS", Decimal("129000"), Decimal("159000"), 48, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Bomber+Jacket"),
    ("THE NORTH FACE 고어텍스 마운틴 재킷", "고어텍스 방수투습 소재, 등산용", "아우터", "THE NORTH FACE", Decimal("499000"), Decimal("559000"), 20, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Gore-Tex+Mountain"),

    # 원피스
    ("MUSINSA STANDARD 린넨 미디 원피스", "내추럴 린넨 100%, 허리 스트링 디테일", "원피스", "MUSINSA STANDARD", Decimal("49900"), Decimal("59900"), 60, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Linen+Dress"),
    ("무신사 스탠다드 플로럴 맥시 원피스", "꽃무늬 프린트, 여름 드레스", "원피스", "MUSINSA STANDARD", Decimal("55000"), None, 45, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Floral+Maxi"),
    ("무신사 스탠다드 니트 원피스 베이지", "부드러운 니트 소재, 미니 길이", "원피스", "MUSINSA STANDARD", Decimal("59900"), Decimal("69900"), 50, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Knit+Dress"),
    ("무신사 스탠다드 체크 셔츠 원피스", "오버사이즈 셔츠 원피스, 벨트 포함", "원피스", "MUSINSA STANDARD", Decimal("65000"), None, 40, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Shirt+Dress"),
    ("무신사 스탠다드 슬립 원피스 블랙", "새틴 소재 슬립 드레스, 레이어드 가능", "원피스", "MUSINSA STANDARD", Decimal("45000"), Decimal("55000"), 55, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Slip+Dress"),

    # 신발
    ("NIKE Air Force 1 '07 화이트", "올타임 클래식, 레더 어퍼", "신발", "NIKE", Decimal("119000"), Decimal("129000"), 100, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Air+Force+1"),
    ("ADIDAS Stan Smith 화이트/그린", "테니스 코트 유래 클래식 스니커즈", "신발", "ADIDAS", Decimal("109000"), Decimal("129000"), 90, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Stan+Smith"),
    ("NEW BALANCE 574 그레이", "574 클래식 러닝 스타일 스니커즈", "신발", "NEW BALANCE", Decimal("99000"), Decimal("119000"), 80, "https://placehold.co/400x500/e5e7eb/9ca3af?text=NB+574"),
    ("CONVERSE Chuck Taylor All Star 블랙 하이", "클래식 캔버스 하이탑", "신발", "CONVERSE", Decimal("89000"), Decimal("99000"), 110, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Chuck+Taylor+Hi"),
    ("VANS Old Skool 블랙/화이트", "사이드스트라이프 클래식 스케이트 슈즈", "신발", "VANS", Decimal("89000"), Decimal("99000"), 95, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Vans+Old+Skool"),
    ("NEW BALANCE 990v5 그레이", "메이드 인 USA, 프리미엄 러닝화", "신발", "NEW BALANCE", Decimal("289000"), Decimal("319000"), 35, "https://placehold.co/400x500/e5e7eb/9ca3af?text=NB+990v5"),
    ("NIKE Air Max 90 화이트", "에어맥스 유닛 쿠셔닝, 90년대 클래식", "신발", "NIKE", Decimal("149000"), Decimal("169000"), 55, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Air+Max+90"),
    ("ADIDAS Samba OG 화이트/블랙", "가죽 어퍼, 거미줄 아웃솔", "신발", "ADIDAS", Decimal("129000"), Decimal("149000"), 70, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Samba+OG"),
    ("SALOMON XT-6 블랙", "트레일 러닝 인스파이어드 테크 스니커즈", "신발", "SALOMON", Decimal("199000"), Decimal("229000"), 45, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Salomon+XT6"),
    ("BIRKENSTOCK Arizona 네이비 버클", "두줄 버클 스트랩, 코르크 풋베드", "신발", "BIRKENSTOCK", Decimal("159000"), Decimal("179000"), 60, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Birkenstock+Arizona"),
    ("닥터마틴 1460 8홀 블랙 부츠", "스무스 레더, 에어 쿠셔닝 솔", "신발", "DR. MARTENS", Decimal("239000"), Decimal("279000"), 40, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Doc+Martens+1460"),

    # 가방
    ("THE NORTH FACE 바저백 토트", "방수 나일론, 17L 대용량", "가방", "THE NORTH FACE", Decimal("89000"), Decimal("109000"), 55, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Borealis+Tote"),
    ("CARHARTT WIP 델타 숄더백", "폴리에스터 소재, 미니 숄더백", "가방", "CARHARTT", Decimal("79000"), None, 40, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Delta+Shoulder"),
    ("무신사 스탠다드 캔버스 에코백", "두꺼운 캔버스 소재, 오가닉 코튼", "가방", "MUSINSA STANDARD", Decimal("19900"), None, 200, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Canvas+Eco"),
    ("GRAMICCI 코듀라 힙백", "코듀라 나일론, 야외활동 힙색", "가방", "GRAMICCI", Decimal("69000"), None, 45, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Cordura+Hip"),
    ("무신사 스탠다드 미니 크로스백", "인조가죽 소재, 슬림한 미니백", "가방", "MUSINSA STANDARD", Decimal("35000"), Decimal("45000"), 70, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Mini+Cross"),
    ("THE NORTH FACE 퓨어 백팩 20L", "노트북 15인치 수납, 등판 패딩", "가방", "THE NORTH FACE", Decimal("119000"), Decimal("139000"), 50, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Pure+Backpack"),
    ("PORTER 탄커 웨이스트 백", "일본 장인이 만든 나일론 웨이스트백", "가방", "PORTER", Decimal("149000"), None, 30, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Porter+Tanker"),
    ("무신사 스탠다드 토트백 L 화이트", "캔버스 소재, 기본에 충실한 토트", "가방", "MUSINSA STANDARD", Decimal("29900"), None, 90, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Tote+Bag+L"),
    ("NIKE 짐클럽 백팩", "폴리에스터, 27L 운동 특화", "가방", "NIKE", Decimal("55000"), Decimal("65000"), 75, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Gym+Club+Backpack"),

    # 액세서리
    ("무신사 스탠다드 버킷햇 베이지", "면 소재 버킷햇, UV 차단", "액세서리", "MUSINSA STANDARD", Decimal("19900"), Decimal("24900"), 120, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Bucket+Hat"),
    ("THE NORTH FACE 로고 볼캡 블랙", "고어텍스 가공, 조절 스트랩", "액세서리", "THE NORTH FACE", Decimal("45000"), Decimal("55000"), 80, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Logo+Cap"),
    ("CARHARTT WIP 워치 비니 블랙", "100% 아크릴, 리브 니트 비니", "액세서리", "CARHARTT", Decimal("29000"), None, 150, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Watch+Beanie"),
    ("무신사 스탠다드 양말 3팩", "코튼 혼방, 발목/중목/크루 세트", "액세서리", "MUSINSA STANDARD", Decimal("12900"), None, 300, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Socks+3Pack"),
    ("NIKE 리버시블 스카프", "양면 사용 가능, 폴라플리스 소재", "액세서리", "NIKE", Decimal("35000"), Decimal("45000"), 60, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Reversible+Scarf"),
    ("무신사 스탠다드 레더 벨트 블랙", "소가죽 소재, 핀 버클", "액세서리", "MUSINSA STANDARD", Decimal("25000"), None, 100, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Leather+Belt"),
    ("VANS 올드스쿨 왈렛", "캔버스 소재, 사이드스트라이프 포인트", "액세서리", "VANS", Decimal("29000"), Decimal("35000"), 70, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Old+Skool+Wallet"),
    ("무신사 스탠다드 야구 캡 네이비", "6패널 구조, 조절가능 스냅백", "액세서리", "MUSINSA STANDARD", Decimal("22000"), None, 110, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Baseball+Cap"),
    ("PORTER 코인 지갑 블랙", "탄커 시리즈 나일론 코인파우치", "액세서리", "PORTER", Decimal("39000"), None, 45, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Coin+Wallet"),
    ("THE NORTH FACE 플리스 장갑", "폴라텍 플리스, 터치스크린 지원", "액세서리", "THE NORTH FACE", Decimal("39000"), Decimal("49000"), 85, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Fleece+Gloves"),

    # 추가 상의
    ("STUSSY 스탁 로고 티셔츠", "기본 로고 반팔, 면 100%", "상의", "STUSSY", Decimal("59000"), Decimal("69000"), 75, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Stussy+Stock+Tee"),
    ("HUF 박스 로고 후드 블랙", "스케이트 브랜드 클래식 박스로고", "상의", "HUF", Decimal("89000"), Decimal("109000"), 50, "https://placehold.co/400x500/e5e7eb/9ca3af?text=HUF+Box+Hood"),
    ("무신사 스탠다드 쿨 코튼 티셔츠", "여름용 쿨링 소재, 체온조절", "상의", "MUSINSA STANDARD", Decimal("22900"), None, 160, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Cool+Cotton+Tee"),
    ("KITH 클래식 로고 크루넥", "헤비 프렌치 테리, 자수 로고", "상의", "KITH", Decimal("159000"), Decimal("189000"), 30, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Kith+Crewneck"),
    ("무신사 스탠다드 체크 셔츠 네이비", "코튼 플란넬 체크, 오버핏", "상의", "MUSINSA STANDARD", Decimal("39900"), Decimal("49900"), 65, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Check+Shirt+Navy"),

    # 추가 하의
    ("GRAMICCI G-쇼츠 카키", "리클라이밍 특화 테이퍼드 쇼츠", "하의", "GRAMICCI", Decimal("99000"), None, 55, "https://placehold.co/400x500/e5e7eb/9ca3af?text=G-Shorts"),
    ("무신사 스탠다드 조거팬츠 블랙", "코튼 테리 소재, 밴딩 허리", "하의", "MUSINSA STANDARD", Decimal("35000"), Decimal("45000"), 95, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Jogger+Black"),
    ("DICKIES 8874 크롭 팬츠", "874의 크롭 버전, 미드 워싱", "하의", "DICKIES", Decimal("75000"), None, 40, "https://placehold.co/400x500/e5e7eb/9ca3af?text=874+Crop"),
    ("LEVI'S 550 릴렉스 청바지", "여유있는 릴렉스핏, 빈티지 워싱", "하의", "LEVI'S", Decimal("109000"), Decimal("129000"), 60, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Levis+550"),
    ("무신사 스탠다드 파자마 팬츠", "와플 소재 홈웨어 팬츠", "하의", "MUSINSA STANDARD", Decimal("32000"), None, 80, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Pajama+Pants"),

    # 추가 신발
    ("NIKE Dunk Low 판다", "화이트/블랙 클래식 컬러, 레더 어퍼", "신발", "NIKE", Decimal("129000"), Decimal("149000"), 65, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Dunk+Low+Panda"),
    ("NEW BALANCE 530 실버/화이트", "메쉬 어퍼, Y2K 레트로 디자인", "신발", "NEW BALANCE", Decimal("109000"), Decimal("129000"), 70, "https://placehold.co/400x500/e5e7eb/9ca3af?text=NB+530"),
    ("ADIDAS Gazelle 블루/화이트", "스웨이드 어퍼, 금장 로고", "신발", "ADIDAS", Decimal("119000"), Decimal("139000"), 55, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Gazelle+Blue"),
    ("VANS Authentic 블랙", "캔버스 어퍼, 와플 아웃솔 클래식", "신발", "VANS", Decimal("79000"), Decimal("89000"), 85, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Vans+Authentic"),
    ("ASICS Gel-Kayano 14 화이트/크림", "레트로 러닝, 젤 쿠셔닝", "신발", "ASICS", Decimal("149000"), Decimal("169000"), 50, "https://placehold.co/400x500/e5e7eb/9ca3af?text=Gel-Kayano+14"),
]


def main() -> int:
    with SessionLocal() as db:
        existing = db.query(Product).count()
        if existing > 0:
            print(f"상품 테이블에 이미 {existing}개 데이터 있음. 시드 건너뜀.")
            return 0

        for name, desc, category, brand, price, original_price, stock, image_url in FASHION_PRODUCTS:
            db.add(Product(
                name=name,
                description=desc,
                category=category,
                brand=brand,
                price=price,
                original_price=original_price,
                stock_quantity=stock,
                image_url=image_url,
            ))
        db.commit()
        print(f"패션 상품 {len(FASHION_PRODUCTS)}개 시드 완료.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

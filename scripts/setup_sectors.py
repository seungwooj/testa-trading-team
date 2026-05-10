"""
최초 1회 실행: data/sectors.json 초기화
  python setup_sectors.py [mock|real]

sectors.json 구조:
  {
    "섹터명": {
      "stocks": [{"code": "005930", "name": "삼성전자"}, ...]
    },
    ...
  }

이후 종목 추가/제거는 sectors.json을 직접 편집하세요.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

if len(sys.argv) < 2:
    sys.argv.append("mock")

from config import BASE_DIR

OUTPUT = BASE_DIR / "data" / "sectors.json"

INITIAL_SECTORS = {
    "반도체": {
        "index_code": "1013",
        "stocks": [
            {"code": "005930", "name": "삼성전자"},
            {"code": "000660", "name": "SK하이닉스"},
            {"code": "042700", "name": "한미반도체"},
            {"code": "009150", "name": "삼성전기"},
        ]
    },
    "2차전지": {
        "index_code": "1008",
        "stocks": [
            {"code": "006400", "name": "삼성SDI"},
            {"code": "051910", "name": "LG화학"},
            {"code": "247540", "name": "에코프로비엠"},
            {"code": "373220", "name": "LG에너지솔루션"},
        ]
    },
    "바이오": {
        "index_code": "1009",
        "stocks": [
            {"code": "068270", "name": "셀트리온"},
            {"code": "207940", "name": "삼성바이오로직스"},
            {"code": "096530", "name": "알테오젠"},
        ]
    },
    "자동차": {
        "index_code": "1015",
        "stocks": [
            {"code": "005380", "name": "현대차"},
            {"code": "012330", "name": "현대모비스"},
            {"code": "000270", "name": "기아"},
        ]
    },
    "금융": {
        "index_code": "1021",
        "stocks": [
            {"code": "105560", "name": "KB금융"},
            {"code": "055550", "name": "신한지주"},
            {"code": "086790", "name": "하나금융지주"},
            {"code": "053000", "name": "우리금융"},
        ]
    },
}

OUTPUT.parent.mkdir(exist_ok=True)
with open(OUTPUT, "w") as f:
    json.dump(INITIAL_SECTORS, f, ensure_ascii=False, indent=2)

print(f"sectors.json 생성 완료: {OUTPUT}")
print("종목 추가/제거는 해당 파일을 직접 편집하세요.")

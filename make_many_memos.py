"""비교 실습용 메모 100개 만들기 (CHAPTER 4, 강사가 나눠 주는 파일)

many_memos 폴더에 메모 100개를 만든다.
  - memos 폴더의 메모 7개를 그대로 복사한다 (실습 질문의 답은 이 7개 안에 있다)
  - 나머지 93개는 독서, 운동, 요리 같은 개인 메모를 정해 둔 규칙으로 만든다
    (실행할 때마다 똑같은 메모가 만들어진다)
  - many_memos 폴더가 이미 있으면 통째로 지우고 새로 만든다 (그 안에서 고친 파일도 지워진다)

실행: python make_many_memos.py
"""
import random
import shutil
from pathlib import Path

LAB_FOLDER = Path(__file__).resolve().parent
SOURCE = LAB_FOLDER / "memos"
TARGET = LAB_FOLDER / "many_memos"
TOTAL = 100

TOPICS = {
    "독서": ["{book} 1장 읽음. 핵심: {point}", "다음 달 독서 모임 책 후보: {book}",
             "밑줄 친 문장 정리하기", "{book} 다 읽으면 서평 쓰기"],
    "운동": ["이번 주 걷기 {num}km", "스트레칭 아침 10분 계속하기", "{weekday} 저녁 수영 강습",
             "운동화 밑창이 닳음. 새로 살지 생각해 보기"],
    "요리": ["{dish} 만들기: 양파는 약불에서 오래 볶는다", "{dish} 양념 비율 다시 확인",
             "주말에 {dish} 해 보기", "냉동실 정리하고 남은 재료 적어 두기"],
    "영화": ["보고 싶은 영화: {movie}", "{movie} 보고 나서 든 생각 적기", "{weekday} 밤 영화 보기"],
    "공부": ["영어 단어 하루 {num}개", "{course} 강의 {num}강까지 듣기", "{course} 과제 제출 확인",
             "모르는 내용은 질문 목록에 적기"],
    "가계부": ["이번 달 식비 {num}만 원", "구독 서비스 {num}개 중 안 쓰는 것 정리", "카드 명세서 확인하기"],
    "선물": ["{person} 생일 선물 후보: {gift}", "{person}에게 감사 카드 쓰기", "{gift} 가격 비교하기"],
    "병원": ["{weekday} 오후 {clinic} 예약", "{clinic} 다녀온 뒤 약 {num}일 먹기", "건강검진 결과 확인하기"],
    "모임": ["동창 모임 {weekday} 저녁", "모임 회비 {num}만 원 보내기", "{person}에게 모임 장소 물어보기"],
    "집안일": ["화분 물 주기 ({weekday})", "세탁기 필터 청소", "현관 전구 바꾸기", "재활용 내놓는 날 {weekday}"],
    "아이디어": ["사진을 날짜별로 정리하는 방법 찾아보기", "가족 앨범 만들기", "{course} 배운 것 블로그에 쓰기"],
}
FILL = {
    "book": ["작은 습관의 힘", "생각의 지도", "하루 한 장 글쓰기", "데이터로 보는 세상"],
    "point": ["작게 시작하기", "환경을 바꾸기", "매일 같은 시간에 하기", "기록이 기억을 이긴다"],
    "num": ["3", "5", "7", "10", "12", "20"],
    "weekday": ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일"],
    "dish": ["된장찌개", "카레", "잡채", "닭볶음탕", "김밥"],
    "movie": ["바다의 기억", "별을 세는 밤", "작은 도시 이야기", "마지막 기차"],
    "course": ["파이썬 기초", "엑셀 함수", "사진 보정", "글쓰기"],
    "person": ["어머니", "민수", "지영", "선배", "동생"],
    "gift": ["머그컵", "블루투스 스피커", "책갈피 세트", "향초"],
    "clinic": ["치과", "안과", "내과", "피부과"],
}


def fill(template, rng):
    for key, values in FILL.items():
        template = template.replace("{" + key + "}", rng.choice(values))
    return template


def main():
    if TARGET.exists():
        count = len(list(TARGET.iterdir()))
        print(f"  [알림] 기존 {TARGET.name} 폴더(파일 {count}개)를 지우고 새로 만든다")
        shutil.rmtree(TARGET)
    TARGET.mkdir()

    originals = sorted(SOURCE.glob("*.txt"))
    for memo in originals:
        shutil.copy(memo, TARGET / memo.name)

    rng = random.Random(4)
    made = 0
    while len(originals) + made < TOTAL:
        topic = rng.choice(list(TOPICS))
        month, day = rng.randint(4, 9), rng.randint(1, 28)
        name = f"2026-{month:02d}-{day:02d}_{topic}.txt"
        if (TARGET / name).exists():
            continue
        lines = rng.sample(TOPICS[topic], k=min(3, len(TOPICS[topic])))
        body = "\n".join("- " + fill(line, rng) for line in lines)
        (TARGET / name).write_text(f"{topic} ({month}/{day})\n{body}\n", encoding="utf-8")
        made += 1

    total_chars = sum(len(p.read_text(encoding="utf-8")) for p in TARGET.glob("*.txt"))
    print("요약 (여기만 보면 된다)")
    print(f"  만든 폴더: {TARGET}")
    print(f"  메모 {len(originals) + made}개 (memos 에서 복사 {len(originals)}개 + 새로 만든 메모 {made}개)")
    print(f"  글자 수 합계: {total_chars:,}자")


if __name__ == "__main__":
    main()

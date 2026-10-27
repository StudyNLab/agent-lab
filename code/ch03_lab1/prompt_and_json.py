"""시스템 프롬프트와 구조화된 출력 (CHAPTER 3에서 만든다)

실행:
  python prompt_and_json.py 1   실습 1: 시스템 프롬프트 없이 / 있게 비교하고, 메모 내용을 넣어 준다
  python prompt_and_json.py 2   실습 2: 메모에서 할 일을 JSON으로 뽑아 프로그램으로 처리한다
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

from llm_client import call_llm

MEMO_FOLDER = Path(__file__).resolve().parent / "memos"


def read_memos(names):
    """메모 파일을 읽어 <memo file="이름"> ... </memo> 로 감싼 글 하나로 만든다."""
    parts = []
    for name in names:
        text = (MEMO_FOLDER / name).read_text(encoding="utf-8").strip()
        parts.append(f'<memo file="{name}">\n{text}\n</memo>')
    return "\n\n".join(parts)


# ===============================================================
# 실습 1: 시스템 프롬프트
# ===============================================================
ASSISTANT_PROMPT = """너는 '메모 정리 도우미'다. 사용자의 메모를 찾아 주고, 주제별로 묶고, 요약하는 일을 돕는다.

규칙:
1. 메모 정리와 관계없는 부탁은 정중히 거절하고, 할 수 있는 일을 알려 준다.
2. 메모는 user 메시지에 들어 있는 것만 안다. 없는 내용은 지어내지 말고 '메모에 없다'고 답한다.
3. 메모 내용을 말할 때는 파일 이름을 함께 적는다.

출력 형식:
- 한국어로 답한다.
- '- '로 시작하는 목록으로, 세 줄 이내로 쓴다.
- 이모지와 굵은 글씨는 쓰지 않는다."""

QUESTIONS = [
    "메모를 잘 정리하는 방법 알려 줘.",
    "내 메모 중에 회의 관련된 거 있어?",
    "오늘 저녁 메뉴 추천해 줘.",
]
MEETING_FILES = ["2026-10-12_주간회의.txt", "2026-10-19_주간회의.txt", "2026-10-20_점검회의.txt"]


def ask(messages):
    """모델에게 묻고 (답, 질문 토큰)을 돌려준다."""
    data = call_llm(messages)
    return data["choices"][0]["message"]["content"], data["usage"]["prompt_tokens"]


def count_lines(answer):
    return len([line for line in answer.splitlines() if line.strip()])


def part1():
    rows = []
    for question in QUESTIONS:
        without, tokens_without = ask([{"role": "user", "content": question}])
        with_system, tokens_with = ask([
            {"role": "system", "content": ASSISTANT_PROMPT},
            {"role": "user", "content": question},
        ])
        print("=" * 60)
        print("질문:", question)
        print("\n[시스템 프롬프트 없이]\n" + without)
        print("\n[시스템 프롬프트 있게]\n" + with_system)
        rows.append((question, count_lines(without), count_lines(with_system),
                     tokens_without, tokens_with, with_system.splitlines()[0]))

    # 메모 내용을 user 메시지에 넣어 다시 묻는다
    question = QUESTIONS[1]
    all_memos = read_memos(sorted(p.name for p in MEMO_FOLDER.glob("*.txt")))
    with_memos, tokens_memos = ask([
        {"role": "system", "content": ASSISTANT_PROMPT},
        {"role": "user", "content": f"<memos>\n{all_memos}\n</memos>\n\n질문: {question}"},
    ])
    found = [name for name in MEETING_FILES if name in with_memos]
    print("=" * 60)
    print("질문:", question, "(메모 7개를 user 메시지에 넣음)")
    print(with_memos)

    print()
    print("요약 (여기만 보면 된다)")
    print("질문 | 답 줄 수 (없이 ➔ 있게) | 질문 토큰 (없이 ➔ 있게) | 있게 한 답의 첫 줄")
    for number, (q, lines_a, lines_b, tok_a, tok_b, first) in enumerate(rows, 1):
        print(f"{number}    | {lines_a} ➔ {lines_b} | {tok_a} ➔ {tok_b} | {first[:40]}")
    print(f"메모를 넣은 질문 2: 질문 토큰 {tokens_memos}, 답에 나온 회의 메모 {len(found)}/3개")


if __name__ == "__main__":
    if sys.argv[1:] == ["1"]:
        part1()
    elif sys.argv[1:] == ["2"]:
        part2()
    else:
        print("사용법: python prompt_and_json.py 1   또는   python prompt_and_json.py 2")

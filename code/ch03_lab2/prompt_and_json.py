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
1. 메모를 찾고 정리하는 일과 메모 정리 방법에 관한 질문에 답한다. 그 밖의 부탁은 정중히 거절하고, 할 수 있는 일을 알려 준다.
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


# ===============================================================
# 실습 2: 구조화된 출력
# ===============================================================
TODAY = date(2026, 10, 27)          # 메모의 날짜에 맞춘 '오늘'
TASK_FILES = ["2026-10-12_주간회의.txt", "2026-10-19_주간회의.txt",
              "2026-10-20_점검회의.txt", "11월_일정.txt"]
RUNS = 3

DETAILED_PROMPT = """너는 메모에서 할 일을 뽑는 도우미다.
user 메시지의 메모에서 할 일을 모두 뽑아, 아래 형식의 JSON으로만 답한다. 다른 글은 쓰지 않는다.

{"tasks": [{"task": "할 일 내용", "owner": "담당자", "due": "10/24", "file": "파일 이름"}]}

- owner: 메모에 적힌 담당자. 없으면 null
- due: 마감 날짜를 '월/일' 숫자로만 (예: 10/24). 요일이나 시각은 넣지 않는다. 없으면 null
- file: 그 할 일이 적힌 메모 파일 이름
- 이미 끝난 일은 뽑지 않는다. '조치'처럼 이미 한 일, 다른 메모에서 확정되거나 끝난 일이 그렇다"""

SHORT_PROMPT = "메모에서 할 일을 뽑아 JSON으로 알려 줘. 할 일, 담당자, 마감, 파일 이름을 넣어."

# C가 다시 요청할 때 보내는 스키마 (칸 이름과 값의 종류만. 예시 값은 없다)
SCHEMA_LINE = '{"tasks": [{"task": 글자, "owner": 글자 또는 null, "due": "월/일" 또는 null, "file": 파일 이름}]}'


def extract(messages, json_mode):
    """할 일을 뽑는 호출 한 번. 답(글자)을 돌려준다."""
    response_format = {"type": "json_object"} if json_mode else None
    # 할 일 뽑기처럼 단순한 일은 생각이 필요 없다. 생각 모드를 끄면 빠르고 싸다
    data = call_llm(messages, response_format=response_format, thinking=False)
    return data["choices"][0]["message"]["content"] or ""


def parse(text):
    """JSON 파싱: JSON 글자를 파이썬 데이터로 바꾼다. 실패하면 (None, 이유)."""
    try:
        return json.loads(text), None
    except json.JSONDecodeError as error:
        start = text.strip()[:15].replace("\n", " ")
        return None, f"JSON 파싱 오류 ({error.msg}), 답의 시작 {start!r}"


def to_date(due):
    """'10/24' 같은 글자를 TODAY 해의 날짜로 바꾼다. 형식이 다르거나 없는 날짜(13/40 등)이면 None."""
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})", due) if isinstance(due, str) else None
    if not match:
        return None
    try:
        return date(TODAY.year, int(match[1]), int(match[2]))
    except ValueError:
        return None


def validate(data):
    """유효성 검사: 정해 둔 스키마와 다른 곳의 목록을 돌려준다. 비어 있으면 통과."""
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        return ['맨 바깥은 {"tasks": [...]} 형식이어야 한다']
    problems = []
    for number, task in enumerate(data["tasks"], 1):
        if not isinstance(task, dict):
            problems.append(f"{number}번째 항목이 객체가 아니다")
            continue
        missing = [key for key in ["task", "owner", "due", "file"] if key not in task]
        if missing:
            problems.append(f"{number}번째 항목에 {', '.join(missing)} 칸이 없다")
            continue
        if not isinstance(task["task"], str) or not task["task"].strip():
            problems.append(f"{number}번째 task 는 비어 있지 않은 글자여야 한다")
        if task["owner"] is not None and not isinstance(task["owner"], str):
            problems.append(f"{number}번째 owner '{task['owner']}' 는 글자 또는 null 이어야 한다")
        if task["due"] is not None and to_date(task["due"]) is None:
            problems.append(f"{number}번째 due '{task['due']}' 는 '월/일' 형식의 실제 날짜(예: 10/24)가 아니다")
        if task["file"] not in TASK_FILES:
            problems.append(f"{number}번째 file '{task['file']}' 는 없는 파일 이름이다")
    return problems


def check(text):
    data, error = parse(text)
    return data, [error] if error else validate(data)


def method_a(prompt, memos):
    """A. 프롬프트로만"""
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": memos}]
    return extract(messages, json_mode=False), 0


def method_b(prompt, memos):
    """B. JSON 모드"""
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": memos}]
    return extract(messages, json_mode=True), 0


def method_c(prompt, memos):
    """C. JSON 모드 + 프로그램 검사 + 틀린 곳을 알려 주며 다시 요청 (최대 2번)"""
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": memos}]
    text = extract(messages, json_mode=True)
    for retry in range(1, 3):
        data, problems = check(text)
        if not problems:
            return text, retry - 1
        print(f"      검사 실패 ➔ 다시 요청 {retry}: {problems[:2]}")
        # 틀린 곳과 스키마 한 줄만 보낸다. 자세한 지시(예시, 규칙)는 보내지 않는다
        messages += [
            {"role": "assistant", "content": text},
            {"role": "user", "content": "다음 문제를 고쳐서 JSON 전체를 다시 보내라:\n- "
                                        + "\n- ".join(problems[:10])
                                        + "\n\n지켜야 할 형식: " + SCHEMA_LINE},
        ]
        text = extract(messages, json_mode=True)
    return text, 2


def due_date(task):
    if task["due"] is None:
        return date.max
    return to_date(task["due"])          # 유효성 검사를 통과했으므로 날짜로 바뀐다


def part2():
    memos = read_memos(TASK_FILES)
    results, last_good = [], None
    for prompt_label, prompt in [("자세한 지시", DETAILED_PROMPT), ("짧은 지시", SHORT_PROMPT)]:
        for method_label, method in [("A 프롬프트로만", method_a), ("B JSON 모드", method_b),
                                     ("C 검사 + 다시 요청", method_c)]:
            print("=" * 60)
            print(f"{prompt_label} / {method_label}")
            passed, retries_total = 0, 0
            for run in range(1, RUNS + 1):
                text, retries = method(prompt, memos)
                data, problems = check(text)
                retries_total += retries
                if problems:
                    print(f"  {run}번째: 실패 - {problems[0]}")
                else:
                    passed += 1
                    print(f"  {run}번째: 통과 (할 일 {len(data['tasks'])}개, 다시 요청 {retries}번)")
                    if method is method_c and prompt is DETAILED_PROMPT:
                        last_good = data          # 프로그램이 쓰는 데이터는 자세한 지시 + C 로 받는다
            results.append((prompt_label, method_label, passed, retries_total))

    if last_good:
        print("=" * 60)
        print(f"자세한 지시 + C의 결과를 프로그램이 처리: '나'의 할 일, 마감순 (오늘 {TODAY.month}/{TODAY.day})")
        mine = [task for task in last_good["tasks"] if task.get("owner") == "나"]
        for task in sorted(mine, key=due_date):
            if task.get("due"):
                left = (due_date(task) - TODAY).days
                when = f"{task['due']} ({'지남' if left < 0 else f'{left}일 남음'})"
            else:
                when = "마감 없음"
            print(f"  - {when:<14} {task['task']}  [{task['file']}]")

    print()
    print("요약 (여기만 보면 된다)")
    print("지시 | 방법 | 그대로 쓸 수 있는 답 | 다시 요청 합계")
    for prompt_label, method_label, passed, retries_total in results:
        print(f"{prompt_label} | {method_label:<14} | {passed}/{RUNS} | {retries_total}번")


if __name__ == "__main__":
    if sys.argv[1:] == ["1"]:
        part1()
    elif sys.argv[1:] == ["2"]:
        part2()
    else:
        print("사용법: python prompt_and_json.py 1   또는   python prompt_and_json.py 2")

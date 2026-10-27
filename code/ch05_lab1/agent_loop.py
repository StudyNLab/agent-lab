"""도구 3개와 Agent 루프 (CHAPTER 5에서 만든다)

"모델 호출 ➔ 도구 실행"을 모델이 답을 마칠 때(finish_reason = stop)까지 반복한다.
몇 번 반복할지는 모델이 도구 결과를 보고 정한다. 프로그램은 상한(MAX_TURNS)만 정한다.

도구 (모델이 고르고, 프로그램이 실행한다)
  - list_memos()           : 메모 파일 이름 목록
  - search_memos(keyword)  : 메모 '내용'에서 낱말 찾기
  - read_memo(file_name)   : 메모 하나 전체 읽기

실행:
  python agent_loop.py 1   실습 1: 질문 두 개로 Agent 루프를 돌린다
  python agent_loop.py 2   실습 2: 반복 상한, 도구 설명, 도구 오류를 바꿔 가며 비교한다
"""
import json
import sys
from pathlib import Path

from llm_client import call_llm

MEMO_FOLDER = Path(__file__).resolve().parent / "memos"
MAX_TURNS = 10          # 한 질문에 모델을 부르는 횟수의 상한
SHOW = True             # 호출마다 모델이 고른 도구를 화면에 찍는다


# ---------------------------------------------------------------
# 1. 도구: 프로그램이 실제로 실행할 함수
# ---------------------------------------------------------------
def memo_names():
    return [f.name for f in sorted(MEMO_FOLDER.glob("*.txt"))]


def list_memos():
    """메모 파일 이름 목록"""
    return "\n".join(memo_names())


def search_memos(keyword):
    """모든 메모의 내용에서 keyword가 들어 있는 줄을 파일 이름과 함께 돌려준다."""
    found = []
    for name in memo_names():
        for line in (MEMO_FOLDER / name).read_text(encoding="utf-8").splitlines():
            if keyword in line:
                found.append(f"{name}: {line.strip()}")
    if not found:
        return f"'{keyword}' 가 들어 있는 메모가 없다."
    return "\n".join(found)


def read_memo(file_name):
    """메모 하나의 내용. memos 폴더에 실제로 있는 이름일 때만 읽는다."""
    if file_name not in memo_names():
        return f"오류: '{file_name}' 라는 메모는 없다. list_memos 로 이름을 확인한다."
    return (MEMO_FOLDER / file_name).read_text(encoding="utf-8")


TOOL_FUNCTIONS = {
    "list_memos": list_memos,
    "search_memos": search_memos,
    "read_memo": read_memo,
}


# ---------------------------------------------------------------
# 2. 도구 정의: 모델에게 보여 주는 설명서
# ---------------------------------------------------------------
SEARCH_DESCRIPTION = ("모든 메모의 내용에서 낱말을 찾아, 그 낱말이 들어 있는 줄을 파일 이름과 함께 보여 준다. "
                      "낱말이 정확히 같아야 찾는다.")
RETRY_HINT = "못 찾으면 비슷한 다른 낱말로 다시 찾는다."
ONCE_HINT = "낱말 하나로 한 번만 찾는다. 다시 찾지 않는다."      # 실습 2의 비교용

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_memos",
            "description": "사용자의 메모 파일 이름 목록을 본다.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memos",
            "description": SEARCH_DESCRIPTION + " " + RETRY_HINT,
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "찾을 낱말. 예: 회의"},
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_memo",
            "description": "메모 파일 하나의 전체 내용을 읽는다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_name": {"type": "string", "description": "읽을 메모 파일 이름. 예: 장보기.txt"},
                },
                "required": ["file_name"],
            },
        },
    },
]

SYSTEM_PROMPT = """너는 '메모 정리 도우미'다. 사용자의 메모를 찾아 주고, 주제별로 묶고, 요약하는 일을 돕는다.

규칙:
1. 메모 정리와 관계없는 부탁은 정중히 거절하고, 할 수 있는 일을 알려 준다.
2. 메모는 도구(list_memos, search_memos, read_memo)로만 볼 수 있다. 필요한 만큼만 도구를 쓴다.
3. 메모에 없는 내용은 지어내지 말고 '메모에 없다'고 답한다.
4. 메모 내용을 말할 때는 어느 파일인지 (파일 이름) 을 함께 적는다.

출력 형식:
- 한국어로 답한다.
- '- '로 시작하는 목록으로 쓴다.
- 이모지와 굵은 글씨는 쓰지 않는다."""


# ---------------------------------------------------------------
# 3. Agent 루프
# ---------------------------------------------------------------
def run_tool_calls(tool_calls, record):
    """모델이 요청한 도구를 실행하고, 결과를 tool 메시지 목록으로 만든다.

    도구 이름이 틀리거나 인자가 잘못되어도 프로그램을 멈추지 않는다.
    오류를 결과로 돌려주면 모델이 그것을 보고 다시 시도할 수 있다.
    """
    tool_messages = []
    for call in tool_calls:
        name = call["function"]["name"]
        try:
            arguments = json.loads(call["function"]["arguments"] or "{}")
            result = TOOL_FUNCTIONS[name](**arguments)
        except Exception as error:
            arguments = {}
            result = f"오류: 도구 실행 실패 ({error})"
        record["tools"].append((name, arguments))
        if result.startswith("오류:"):
            record["tool_errors"].append((name, arguments))
        shown = result.replace("\n", " / ")
        if SHOW:
            print(f"    [프로그램] {name} 실행 ➔ {shown[:60]}")
        tool_messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    return tool_messages


def agent_turn(messages):
    """질문 하나에 대한 Agent 루프. messages 에 이어 붙이며 반복한다.

    돌려주는 것: 이 질문의 기록 (답, 호출 횟수, 쓴 도구, 오류를 돌려준 도구, 호출마다의 질문 토큰, 끝난 이유)
    """
    record = {"answer": "", "calls": 0, "tools": [], "tool_errors": [], "prompt_tokens": [], "finish": ""}
    for turn in range(1, MAX_TURNS + 1):
        data = call_llm(messages, tools=TOOLS)
        choice, usage = data["choices"][0], data["usage"]
        message = choice["message"]
        record["calls"] = turn
        record["prompt_tokens"].append(usage["prompt_tokens"])
        record["finish"] = choice["finish_reason"]
        if SHOW:
            print(f"  [{turn}번째 호출] finish_reason = {choice['finish_reason']}"
                  f" (질문 토큰 {usage['prompt_tokens']})")

        # 모델의 메시지는 고치지 않고 통째로 붙인다 (제공사에 따라 생각 내용을 다시 보내야 한다)
        messages.append(message)

        if choice["finish_reason"] == "tool_calls":
            if SHOW:
                for call in message["tool_calls"]:
                    print(f"    [모델] {call['function']['name']}({call['function']['arguments']}) 요청")
            messages.extend(run_tool_calls(message["tool_calls"], record))
            continue                          # 도구 결과를 붙여 다시 부른다

        if choice["finish_reason"] == "stop":
            record["answer"] = message.get("content") or ""
            return record                     # 모델이 답을 마쳤다

        # length(max_tokens 에서 잘림) 등: 도구 요청이 없어도 일을 마친 것이 아니다
        record["answer"] = f"(미완료: finish_reason = {choice['finish_reason']}. 답을 끝까지 받지 못했다)"
        if message.get("content"):
            record["answer"] += "\n" + message["content"]      # 잘린 데까지의 답
        return record

    record["answer"] = f"(호출 {MAX_TURNS}번 안에 끝내지 못해 멈췄다)"
    record["finish"] = "상한에 닿아 멈춤"
    return record


def run_agent(question):
    """질문마다 messages 를 새로 만들어 Agent 루프를 돌린다. (대화 기억 없음)"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    return agent_turn(messages)


def tools_text(record):
    """요약 표에 찍을 '쓴 도구' 글. 예: search(휴가) ➔ list ➔ read(11월_일정.txt)"""
    parts = []
    for name, arguments in record["tools"]:
        short = name.replace("_memos", "").replace("_memo", "")
        value = next(iter(arguments.values()), "")
        parts.append(f"{short}({value})" if value else short)
    return " ➔ ".join(parts) if parts else "(도구 안 씀)"


def print_summary(questions, records):
    print()
    print("=" * 60)
    print("요약 (여기만 보면 된다)")
    print("=" * 60)
    for number, (question, record) in enumerate(zip(questions, records), 1):
        print(f"질문 {number}: {question}")
        print(f"  쓴 도구 : {tools_text(record)}")
        print(f"  호출    : {record['calls']}번, 끝난 이유 = {record['finish']}")
        print(f"  질문 토큰: {' ➔ '.join(map(str, record['prompt_tokens']))}"
              f" (합계 {sum(record['prompt_tokens'])})")


QUESTIONS = [
    "휴가 관련 메모 있어?",
    "이대리가 맡은 일 정리해 줘.",
]


def part1():
    records = []
    for question in QUESTIONS:
        print("=" * 60)
        print("질문:", question)
        record = run_agent(question)
        print("\n[답]")
        print(record["answer"])
        records.append(record)
    print_summary(QUESTIONS, records)


# 이 파일을 직접 실행할 때만 아래를 실행한다. (CHAPTER 6에서 import 할 때는 실행하지 않는다)
if __name__ == "__main__":
    if sys.argv[1:] == ["1"]:
        part1()
    elif sys.argv[1:] == ["2"]:
        part2()
    else:
        print("사용법: python agent_loop.py 1   또는   python agent_loop.py 2")

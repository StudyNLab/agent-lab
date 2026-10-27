"""도구 호출 (CHAPTER 4에서 만든다)

모델에게 도구(read_memo)를 알려 주면, 모델은 답 대신 "이 도구를 이 값으로 실행해 줘"를 돌려줄 수 있다.
도구를 실제로 실행하는 것은 프로그램이다. 결과를 tool 메시지로 붙여 다시 부르면 모델이 답한다.

실행:
  python tool_calling.py 1   실습 1: read_memo 도구로 읽을 메모를 모델이 고르게 한다
  python tool_calling.py 2   실습 2: 메모 전체 넣기 vs 도구로 고르기 (memos 7개 / many_memos 100개)
"""
import json
import sys
from pathlib import Path

from llm_client import call_llm

LAB_FOLDER = Path(__file__).resolve().parent


# ---------------------------------------------------------------
# 1. 도구: 프로그램이 실제로 실행할 함수
# ---------------------------------------------------------------
def memo_names(folder):
    return [f.name for f in sorted(folder.glob("*.txt"))]


def read_memo(folder, file_name):
    """메모 하나의 내용. 메모 폴더에 실제로 있는 이름일 때만 읽는다."""
    if file_name not in memo_names(folder):
        return f"오류: '{file_name}' 라는 메모는 없다. 메모 파일 목록의 이름만 쓸 수 있다."
    return (folder / file_name).read_text(encoding="utf-8")


# ---------------------------------------------------------------
# 2. 도구 정의: 모델에게 보여 주는 설명서 (JSON 스키마)
# ---------------------------------------------------------------
READ_MEMO_TOOL = {
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
}

RULES = """규칙:
1. 메모에 없는 내용은 지어내지 말고 '메모에 없다'고 답한다.
2. 메모 내용을 말할 때는 파일 이름을 함께 적는다.
3. 한국어로, '- '로 시작하는 목록으로 짧게 답한다."""


def tool_prompt(folder):
    """도구로 고르게 할 때의 시스템 프롬프트: 메모 내용 없이 파일 이름 목록만 넣는다."""
    names = "\n".join(memo_names(folder))
    return (f"너는 '메모 정리 도우미'다. 메모 내용은 read_memo 도구로 읽는다. 필요한 메모만 읽는다.\n\n"
            f"{RULES}\n\n메모 파일 목록:\n{names}")


# ---------------------------------------------------------------
# 3. 도구로 고르기: 1차 호출 ➔ 도구 실행 ➔ 2차 호출
# ---------------------------------------------------------------
def ask_with_tool(folder, question, show=True):
    messages = [
        {"role": "system", "content": tool_prompt(folder)},
        {"role": "user", "content": question},
    ]
    record = {"read": [], "tokens": [], "finish": []}

    data = call_llm(messages, tools=[READ_MEMO_TOOL])                  # 1차 호출
    choice = data["choices"][0]
    record["tokens"].append(data["usage"]["prompt_tokens"])
    record["finish"].append(choice["finish_reason"])
    message = choice["message"]
    if show:
        print(f"  [1차 호출] finish_reason = {choice['finish_reason']}")

    if message.get("tool_calls"):
        messages.append(message)                    # 모델의 도구 요청을 통째로 붙인다
        for call in message["tool_calls"]:
            arguments = json.loads(call["function"]["arguments"])
            result = read_memo(folder, arguments["file_name"])          # 프로그램이 실행한다
            record["read"].append(arguments["file_name"])
            if show:
                print(f"    [모델] read_memo({arguments['file_name']}) 요청")
                print(f"    [프로그램] 실행 ➔ {result.splitlines()[0][:40]}")
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

        data = call_llm(messages, tools=[READ_MEMO_TOOL])              # 2차 호출
        choice = data["choices"][0]
        record["tokens"].append(data["usage"]["prompt_tokens"])
        record["finish"].append(choice["finish_reason"])
        message = choice["message"]
        if show:
            print(f"  [2차 호출] finish_reason = {choice['finish_reason']}")

    if message.get("tool_calls"):
        record["answer"] = "(모델이 도구를 더 요청했다. 반복해서 처리하는 것은 CHAPTER 5)"
    else:
        record["answer"] = message.get("content") or ""
    return record


# ---------------------------------------------------------------
# 실습 1
# ---------------------------------------------------------------
PART1_QUESTIONS = ["장보기 목록 알려 줘.", "회의 관련 메모 있어?", "휴가 계획 메모 있어?"]


def part1():
    folder = LAB_FOLDER / "memos"
    rows = []
    for question in PART1_QUESTIONS:
        print("=" * 60)
        print("질문:", question)
        record = ask_with_tool(folder, question)
        print("\n[답]\n" + record["answer"])
        rows.append((question, record))

    # 안전 확인: 모델이 메모 폴더 밖의 파일 이름을 보내면 어떻게 되는가 (프로그램이 직접 불러 본다)
    print("=" * 60)
    blocked = read_memo(folder, "../check_setup.py")
    print(f"[안전 확인] read_memo('../check_setup.py') ➔ {blocked}")

    print()
    print("요약 (여기만 보면 된다)")
    print("질문 | 1차 호출 끝난 이유 | 읽은 메모 | 질문 토큰 (1차 + 2차)")
    for question, record in rows:
        read = ", ".join(record["read"]) or "(읽지 않음)"
        tokens = " + ".join(map(str, record["tokens"]))
        print(f"{question} | {record['finish'][0]} | {read} | {tokens}")


if __name__ == "__main__":
    if sys.argv[1:] == ["1"]:
        part1()
    elif sys.argv[1:] == ["2"]:
        part2()
    else:
        print("사용법: python tool_calling.py 1   또는   python tool_calling.py 2")

"""메모 정리 도우미 완성본: 대화 기억 + 컨텍스트 관리 (CHAPTER 6에서 만든다)

  - 대화 기억: messages 하나를 대화 내내 이어 쓴다. 모델은 요청 사이에 기억하지 않으므로(stateless),
    프로그램이 지금까지의 대화 전체를 요청마다 다시 보낸다.
  - 컨텍스트 관리: 질문 토큰이 기준(TOKEN_LIMIT)을 넘으면 오래된 턴을 요약해 짧게 바꾼다.
    턴 = 사용자 질문 하나로 시작하는 묶음. 도구 요청과 결과의 짝이 깨지지 않게 턴 단위로 자른다.

Agent 루프와 도구는 agent_loop.py 의 것을 가져다 쓴다(import).

실행:
  python memo_assistant.py     직접 대화한다 (빈 줄 또는 '끝'을 입력하면 끝난다)
  python memo_assistant.py 1   실습 1: 대화 기억 없이 / 있게 이어서 묻는다
  python memo_assistant.py 2   실습 2: 요약 규칙 두 가지를 비교한다
"""
import re
import sys

import agent_loop
from agent_loop import SYSTEM_PROMPT, agent_turn, tools_text
from llm_client import call_llm

# 대화를 기억하면, 사용자가 대화에서 알려 준 새 사실이 메모와 다를 수 있다.
# agent_loop 의 시스템 프롬프트는 메모를 기준으로 답하게 하므로, 새 사실을 적용하라는 규칙 5를 더한다
CHAT_RULE = ("5. 사용자가 대화에서 알려 준 바뀐 사실(일정, 마감 등)은 메모보다 새로운 정보로 보고 답에 적용한다. "
             "메모와 다르면 메모에는 어떻게 적혀 있는지도 함께 알린다.")
CHAT_PROMPT = SYSTEM_PROMPT.replace("\n\n출력 형식:", "\n" + CHAT_RULE + "\n\n출력 형식:")

def chat(questions=None, rule=None, compact_on=True):
    """대화하기. messages 를 한 번만 만들고 대화가 끝날 때까지 이어 쓴다.

    questions 가 None 이면 직접 입력받고, 목록이면 그 질문을 차례로 보낸다.
    compact_on 이면 질문 토큰이 TOKEN_LIMIT 를 넘을 때 rule(없으면 SUMMARY_RULE)로 요약한다.
    """
    messages = [{"role": "system", "content": CHAT_PROMPT}]
    summary = ""
    result = {"questions": [], "records": [], "compactions": [], "summaries": [], "failures": []}

    while True:
        if questions is None:
            question = input("\n나: ").strip()
            if question in ("", "끝"):
                break
        else:
            if len(result["questions"]) == len(questions):
                break
            question = questions[len(result["questions"])]
            print(f"\n나: {question}")

        messages.append({"role": "user", "content": question})
        record = agent_turn(messages)
        record["messages"] = len(messages)
        record["summary"] = summary                # 이 질문을 보낼 때 들어 있던 요약
        print(f"\n도우미:\n{record['answer']}")
        result["questions"].append(question)
        result["records"].append(record)

        last_prompt_tokens = record["prompt_tokens"][-1]
        if compact_on and last_prompt_tokens > TOKEN_LIMIT:
            before = len(messages)
            messages, summary, problem = compact(messages, summary,
                                                 rule or SUMMARY_RULE)
            if problem:
                result["failures"].append(len(result["questions"]))
                print(f"\n  [컨텍스트 관리] 질문 토큰 {last_prompt_tokens} > 기준 {TOKEN_LIMIT}"
                      f" ➔ 요약하지 않았다: {problem}. messages {before}개 그대로")
            else:
                result["compactions"].append(len(result["questions"]))
                result["summaries"].append(summary)
                print(f"\n  [컨텍스트 관리] 질문 토큰 {last_prompt_tokens} > 기준 {TOKEN_LIMIT}"
                      f" ➔ 오래된 대화를 요약했다. messages {before}개 ➔ {len(messages)}개")

    result["message_count"] = len(messages)
    return result


def print_summary(result):
    print()
    print("=" * 60)
    print("요약 (여기만 보면 된다)")
    print("=" * 60)
    for number, (question, record) in enumerate(zip(result["questions"], result["records"]), 1):
        print(f"질문 {number}: {question}")
        print(f"  쓴 도구 : {tools_text(record)}")
        print(f"  호출    : {record['calls']}번, 끝난 이유 = {record['finish']}"
              f", 마지막 호출의 질문 토큰 {record['prompt_tokens'][-1]}")
    after = ", ".join(f"질문 {n} 뒤" for n in result["compactions"]) or "없음"
    failed = ", ".join(f"질문 {n} 뒤" for n in result["failures"]) or "없음"
    print(f"요약(컨텍스트 관리): {after}, 요약하지 않음: {failed}")
    print(f"지금 messages: {result['message_count']}개")


# ---------------------------------------------------------------
# 실습 1: 대화 기억 없이 / 있게
# ---------------------------------------------------------------
MEMORY_QUESTIONS = [
    "이대리가 맡은 일 정리해 줘.",
    "그거 언제까지야?",
    "내가 맡은 일도 같은 방식으로 정리해 줘.",
]


def part1():
    print("=" * 60)
    print("(가) 기억 없이: 두 번째 질문만 새 messages로 보낸다")
    print("=" * 60)
    without = chat(MEMORY_QUESTIONS[1:2], compact_on=False)

    print()
    print("=" * 60)
    print("(나) 기억 있게: 세 질문을 messages 하나에 이어서 보낸다")
    print("=" * 60)
    with_memory = chat(MEMORY_QUESTIONS, compact_on=False)

    print()
    print("요약 (여기만 보면 된다)")
    print("구분 | 질문 | 쓴 도구 | messages 수 | 마지막 호출의 질문 토큰")
    rows = [("(가)", without["questions"][0], without["records"][0])]
    rows += [("(나)", q, r) for q, r in zip(with_memory["questions"], with_memory["records"])]
    for label, question, record in rows:
        print(f"{label} | {question} | {tools_text(record)} | {record['messages']}"
              f" | {record['prompt_tokens'][-1]}")


if __name__ == "__main__":
    if sys.argv[1:] == ["1"]:
        part1()
    elif sys.argv[1:] == ["2"]:
        part2()
    else:
        print("메모 정리 도우미입니다. 빈 줄 또는 '끝'을 입력하면 끝납니다.")
        print_summary(chat())

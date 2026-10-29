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

TOKEN_LIMIT = 2000      # 질문 토큰이 이보다 크면 요약한다 (시연용으로 작게 잡았다)
KEEP_TURNS = 1          # 요약하지 않고 그대로 둘 최근 턴 수

SUMMARY_RULE = (        # 규칙 2: 대화에만 있는 것(질문과 결론)만 남긴다
    "다음은 메모 정리 도우미와 사용자의 대화 기록이다. 이어서 대화할 수 있도록 요약한다.\n"
    "- 사용자가 물은 것과 도우미가 낸 결론만 적는다. 결론에 나온 날짜·담당자·파일 이름은 그대로 둔다.\n"
    "- 메모 원문과 도구 결과는 옮겨 적지 않는다. (필요하면 도구로 다시 읽을 수 있다)\n"
    "- 질문 하나에 한 줄, '- '로 시작하는 목록으로 쓴다."
)
FACTS_RULE = (          # 규칙 1: 메모의 사실까지 빠짐없이 남긴다 (실습 2의 비교용)
    "다음은 메모 정리 도우미와 사용자의 대화 기록이다. 이어서 대화할 수 있도록 요약한다.\n"
    "- 사용자가 물은 것, 도우미가 읽은 메모의 내용, 도우미가 낸 결론을 빠짐없이 적는다.\n"
    "- '- '로 시작하는 목록으로 쓴다."
)


def summarize(old_messages, rule):
    """오래된 대화를 LLM에게 요약시킨다. 도구 없이 한 번만 호출한다. (요약, finish_reason)을 돌려준다."""
    lines = []
    for m in old_messages:
        if m["role"] == "user":
            lines.append(f"사용자: {m['content']}")
        elif m["role"] == "assistant":
            for call in m.get("tool_calls") or []:
                lines.append(f"도우미가 도구 요청: {call['function']['name']}"
                             f"({call['function']['arguments']})")
            if m.get("content"):
                lines.append(f"도우미: {m['content']}")
        elif m["role"] == "tool":
            lines.append(f"도구 결과: {m['content']}")
    # 요약은 단순한 일이라 생각 모드를 끈다. 켜 두면 생각에 토큰을 다 써서 요약이 잘리거나 빈다
    data = call_llm([
        {"role": "system", "content": rule},
        {"role": "user", "content": "\n".join(lines)},
    ], thinking=False)
    choice = data["choices"][0]
    return choice["message"].get("content") or "", choice["finish_reason"]


def split_turns(messages):
    """시스템 메시지를 뺀 나머지를 턴(사용자 질문 하나로 시작하는 묶음)으로 나눈다."""
    turns = []
    for m in messages[1:]:
        if m["role"] == "user":
            turns.append([m])
        else:
            turns[-1].append(m)
    return turns


def compact(messages, summary_so_far, rule):
    """오래된 턴을 요약하고 messages 를 새로 만든다.

    (새 messages, 새 요약, 문제)를 돌려준다. 문제가 있으면 messages 와 요약을 바꾸지 않는다.
    """
    turns = split_turns(messages)
    if len(turns) <= KEEP_TURNS:
        return messages, summary_so_far, "줄일 턴이 없다"

    old = [m for turn in turns[:-KEEP_TURNS] for m in turn]
    recent = [m for turn in turns[-KEEP_TURNS:] for m in turn]
    new_summary, finish = summarize(old, rule)
    # 요약이 비었거나 잘렸으면 오래된 턴을 지우지 않는다. 지우면 그 대화를 잃는다
    if finish != "stop" or not new_summary.strip():
        return (messages, summary_so_far,
                f"요약 실패 (finish_reason = {finish}, 요약 {len(new_summary)}자)")

    # 앞서 만든 요약은 다시 요약하지 않고 그대로 두고, 새로 오래된 턴의 요약만 덧붙인다.
    # (요약을 다시 요약하면 앞의 결론이 빠질 수 있다)
    summary = (summary_so_far + "\n" + new_summary).strip()

    system = (CHAT_PROMPT
              + "\n\n지금까지의 대화 요약 (오래된 대화는 이 요약으로 대신한다):\n"
              + summary)
    return [{"role": "system", "content": system}] + recent, summary, None


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


# ---------------------------------------------------------------
# 실습 2: 요약 규칙 두 가지 비교
# ---------------------------------------------------------------
# 첫 질문에서 메모에 없는 사실(바뀐 마감)을 알려 주고, 마지막 질문에서 지금의 마감 하나를 묻는다.
# 메모에는 옛 마감 10/23만 있다. 메모를 다시 찾으면 10/23, 대화를 기억해 새 마감을 적용해야 10/27 이라고 답한다
NEW_DUE, OLD_DUE = "10/27", "10/23"
COMPACT_QUESTIONS = [
    f"이대리 안내 자료 초안 마감이 {NEW_DUE}(화)로 늦춰졌대. 메모는 아직 안 고쳤어. 이대리가 맡은 일 정리해 줘.",
    "내가 맡은 일도 같은 방식으로 정리해 줘.",
    "11월 일정 알려 줘.",
    "이대리 안내 자료 초안은 지금 기준으로 언제까지 내면 돼? 마감 날짜 하나만 답해 줘.",
]


def judge_due(answer):
    """마지막 답이 새 마감을 적용했는가. 날짜를 '언급'한 것과 '마감으로 답한' 것을 나눈다.

    마감 하나만 답하라고 물었으므로 답의 첫 날짜를 답한 마감으로 보고, 나머지 날짜는 언급으로 본다.
    """
    dates = [d for d in re.findall(r"\d{1,2}/\d{1,2}", answer) if d in (NEW_DUE, OLD_DUE)]
    if not dates:
        return "마감 없음"
    other = OLD_DUE if dates[0] == NEW_DUE else NEW_DUE
    mention = f", {other}은 언급만" if other in dates else ""
    if dates[0] == NEW_DUE:
        return f"{NEW_DUE}으로 답함 (새 마감을 적용했다{mention})"
    if NEW_DUE in dates:
        return f"{OLD_DUE}으로 답함 (새 마감을 기억했지만 적용하지 않았다{mention})"
    return f"{OLD_DUE}으로 답함 (메모의 옛 마감. 대화를 잊었다)"


def part2():
    agent_loop.SHOW = False                        # 호출마다 찍는 줄은 끈다
    rows = []
    for label, rule in [("규칙 1: 메모 사실까지", FACTS_RULE), ("규칙 2: 질문과 결론만", SUMMARY_RULE)]:
        print("=" * 60)
        print(label)
        print("=" * 60)
        result = chat(COMPACT_QUESTIONS, rule=rule)
        for number, summary in zip(result["compactions"], result["summaries"]):
            print(f"\n  [질문 {number} 뒤의 요약, {len(summary)}자]")
            for line in summary.splitlines():
                print("   ", line)
        last = result["records"][-1]
        reread = [args["file_name"] for name, args in last["tools"] if name == "read_memo"]
        rows.append((label, result, last, reread))

    print()
    print("요약 (여기만 보면 된다)")
    for label, result, last, reread in rows:
        after = ", ".join(f"질문 {n} 뒤" for n in result["compactions"]) or "없음"
        failed = ", ".join(f"질문 {n} 뒤" for n in result["failures"]) or "없음"
        lengths = " ➔ ".join(f"{len(s)}자" for s in result["summaries"]) or "-"
        tokens = " ➔ ".join(str(r["prompt_tokens"][-1]) for r in result["records"])
        if not last["summary"]:
            kept = "요약 없음 (대화 원문 그대로)"
        else:
            kept = f"바뀐 마감 {NEW_DUE} {'있음' if NEW_DUE in last['summary'] else '없음'}"
        answer = judge_due(last["answer"])
        print(label)
        print(f"  요약한 때     : {after} (요약하지 않음: {failed})")
        print(f"  요약 길이     : {lengths}")
        print(f"  질문 토큰     : {tokens} (질문마다 마지막 호출)")
        print(f"  질문 4 때 요약: {kept}")
        print(f"  질문 4의 답   : {answer}, 다시 읽은 메모 {len(reread)}개")


if __name__ == "__main__":
    if sys.argv[1:] == ["1"]:
        part1()
    elif sys.argv[1:] == ["2"]:
        part2()
    else:
        print("메모 정리 도우미입니다. 빈 줄 또는 '끝'을 입력하면 끝납니다.")
        print_summary(chat())

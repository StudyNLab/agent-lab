"""LLM API 호출 (CHAPTER 2에서 만든다)

이 과정의 파일은 모두 이 파일의 call_llm() 으로 모델을 부른다.
  - 접속 값(주소, 모델 이름)은 이 파일 맨 위 한 곳에만 둔다.
  - API 키는 코드에 적지 않고 환경 변수 LLM_API_KEY 에서 읽는다.
  - 시간 초과와 일시적인 오류(429, 5xx)는 기다렸다가 다시 보낸다.
  - 답이 max_tokens 에서 잘리면(finish_reason = length) 알려 준다.

실행: python llm_client.py   (질문 하나를 보내 call_llm() 을 시험한다)
"""
import os
import time

import requests

# 1. 접속 값
BASE_URL = "https://api.deepseek.com"            # 호스트 (서버 주소)
ENDPOINT = BASE_URL + "/chat/completions"        # 엔드포인트: "대화 답 만들기" 기능의 URL
MODEL = "deepseek-flash"                         # 모델 이름
TIMEOUT = 60                                     # 응답을 기다리는 최대 시간(초)
MAX_ATTEMPTS = 3                                 # 처음 보내기 + 다시 시도
RETRY_STATUS = {429, 500, 502, 503, 504}         # 다시 보내면 될 수 있는 상태 코드
NO_THINKING = {"thinking": {"type": "disabled"}}  # 생각 모드를 끄는 본문 항목 (제공사마다 다르다)


def read_api_key():
    """API 키를 환경 변수에서 읽는다. 키는 코드와 화면에 남기지 않는다."""
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        raise RuntimeError("환경 변수 LLM_API_KEY 가 없다. (CHAPTER 1 실습 1)")
    return key


def call_llm(messages, tools=None, max_tokens=4000, response_format=None, thinking=True):
    """모델 호출 한 번. 응답 본문(JSON)을 딕셔너리로 돌려준다.

    thinking=False 이면 생각 모드를 끈다. 단순한 일에서 더 빠르고 싸다. (CHAPTER 3)
    """
    # 2. HTTP 요청 만들기: 헤더(인증, 본문 형식) + JSON 본문
    headers = {
        "Authorization": f"Bearer {read_api_key()}",
        "Content-Type": "application/json",
    }
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens}
    if tools:
        body["tools"] = tools
    if response_format:
        body["response_format"] = response_format
    if not thinking:
        body.update(NO_THINKING)

    # 3. 보내기: 시간 초과와 일시적인 오류는 기다리는 시간을 늘려 가며 다시 보낸다
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.post(ENDPOINT, headers=headers, json=body, timeout=TIMEOUT)
        except requests.exceptions.Timeout:
            problem = f"시간 초과 ({TIMEOUT}초)"
        else:
            if response.status_code == 200:
                data = response.json()
                if data["choices"][0]["finish_reason"] == "length":
                    print(f"  [주의] 답이 max_tokens({max_tokens})에서 잘렸다 (finish_reason = length)")
                return data
            if response.status_code not in RETRY_STATUS:
                # 400(요청 잘못), 401(인증 실패) 등은 다시 보내도 같다
                raise RuntimeError(f"API 오류 {response.status_code}: {response.text[:300]}")
            problem = f"상태 코드 {response.status_code}"

        if attempt < MAX_ATTEMPTS:
            wait = 2 ** attempt
            print(f"  [다시 시도] {problem} ➔ {wait}초 뒤 다시 보낸다 ({attempt}/{MAX_ATTEMPTS - 1})")
            time.sleep(wait)

    raise RuntimeError(f"API 호출 실패: {problem} ({MAX_ATTEMPTS}번 보냄)")


# 4. 시험: 이 파일을 직접 실행할 때만 아래를 실행한다 (다른 파일이 import 할 때는 실행하지 않는다)
TEST_QUESTION = "메모를 잘 정리하는 방법 세 가지만 알려 줘."
TEST_MAX_TOKENS = 4000

if __name__ == "__main__":
    started = time.time()
    try:
        data = call_llm([{"role": "user", "content": TEST_QUESTION}], max_tokens=TEST_MAX_TOKENS)
    except RuntimeError as error:
        print()
        print("요약 (여기만 보면 된다)")
        print(f"  결과: 실패 - {error}")
        print(f"  걸린 시간: {time.time() - started:.1f}초")
    else:
        choice, usage = data["choices"][0], data["usage"]
        details = usage.get("completion_tokens_details") or {}
        print(choice["message"]["content"] or "(답 내용 없음)")
        print()
        print("요약 (여기만 보면 된다)")
        print("  결과: 성공 (상태 코드 200)")
        print(f"  finish_reason: {choice['finish_reason']} (max_tokens {TEST_MAX_TOKENS})")
        print(f"  질문 토큰 {usage['prompt_tokens']}, 답 토큰 {usage['completion_tokens']}"
              f" (그중 생각 토큰 {details.get('reasoning_tokens', 0)})")
        print(f"  걸린 시간: {time.time() - started:.1f}초")

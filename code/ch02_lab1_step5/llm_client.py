"""LLM API 호출 (CHAPTER 2 실습 1: 첫 요청 보내고 요청·응답 확인하기)"""
import os

import requests
from dotenv import load_dotenv

# 1. 접속 값
BASE_URL = "https://api.deepseek.com"            # 호스트 (서버 주소)
ENDPOINT = BASE_URL + "/chat/completions"        # 엔드포인트
MODEL = "deepseek-flash"                         # 모델 이름
load_dotenv(override=True)                       # 실습 폴더의 .env 파일을 읽는다
API_KEY = os.environ["LLM_API_KEY"]              # .env 에 적은 키

# 2. 요청 만들기: 헤더 + JSON 본문
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
body = {
    "model": MODEL,
    "messages": [
        {"role": "user", "content": "메모를 잘 정리하는 방법 세 가지만 알려 줘."},
    ],
    "max_tokens": 4000,
}

def second_item(answer):
    """답에서 "2." 로 시작하는 줄(두 번째 방법)을 찾는다. 별표(**)는 뺀다."""
    for line in answer.splitlines():
        if line.startswith("2."):
            return line.replace("*", "").strip()
    return "(없음)"


# 3. 같은 요청을 세 번 보내고, 응답에서 필요한 값만 꺼낸다
results = []
for number in range(1, 4):
    response = requests.post(ENDPOINT, headers=headers, json=body, timeout=60)
    data = response.json()
    choice = data["choices"][0]
    usage = data["usage"]
    reasoning = usage["completion_tokens_details"]["reasoning_tokens"]
    answer = choice["message"]["content"]

    print(f"===== {number}번째 답 =====")
    print(answer)
    results.append((response.status_code, choice["finish_reason"],
                    usage["prompt_tokens"], usage["completion_tokens"], reasoning,
                    second_item(answer)))

# 4. 요약
print()
print("요약 (여기만 보면 된다)")
print("번호 | 상태 코드 | finish_reason | 질문 토큰 | 답 토큰 (생각) | 두 번째 방법")
for number, (status, finish, prompt, completion, reasoning, second) in enumerate(results, 1):
    print(f"{number}    | {status}       | {finish:<13} | {prompt:<9} | {completion} ({reasoning})"
          f" | {second}")

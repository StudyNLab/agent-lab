"""LLM API 호출 (CHAPTER 2 실습 1: 첫 요청 보내고 요청·응답 확인하기)"""
import json
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

# 3. 보내고 응답 받기
response = requests.post(ENDPOINT, headers=headers, json=body, timeout=60)

# 4. 보낸 요청 확인용 출력 (키는 앞부분만)
sent = response.request
print("===== 보낸 요청 =====")
print(sent.method, sent.url)
for name, value in sent.headers.items():
    if name == "Authorization":
        value = value[:10] + "...(가림)"
    print(f"{name}: {value}")
print()
print(sent.body.decode("utf-8"))

# 5. 받은 응답 확인용 출력
print()
print("===== 받은 응답 =====")
print("상태 코드:", response.status_code)
print("Content-Type:", response.headers["Content-Type"])
print(json.dumps(response.json(), ensure_ascii=False, indent=2))

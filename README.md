# agent-lab

교재 **AI Agent 개발 : AI Agent 개발 기초 (초급)** 의 실습 파일이다.

## 받기

Windows PowerShell에서 실행한다. `C:\agent-lab` 에 실습 파일이 풀린다. (교재 CHAPTER 1 실습 1 Step 1)

```powershell
$url = "https://github.com/StudyNLab/agent-lab/archive/main.zip"
curl.exe -sSL -o $env:TEMP\agent-lab.zip $url
Expand-Archive $env:TEMP\agent-lab.zip -DestinationPath C:\
Rename-Item C:\agent-lab-main agent-lab
```

- 이미 `C:\agent-lab` 이 있으면 `Rename-Item` 이 실패한다. 그 폴더를 다른 이름으로 바꾼 뒤 다시 한다.
- 명령이 막히면 브라우저로 위 주소를 열어 zip을 받고, `C:\` 에 풀어 폴더 이름을 `agent-lab` 으로 바꾼다.

## 들어 있는 것

| 경로 | 내용 | 쓰는 곳 |
|---|---|---|
| `check_setup.py` | 실습 환경 점검 | CHAPTER 1 실습 1 |
| `memos/` | 연습용 메모 7개 | CHAPTER 3 ~ 6 |
| `finished/` | 완성본 메모 정리 도우미와 메모 사본 | CHAPTER 1 실습 2, 따라 쓰다 막힐 때 비교 |
| `make_many_memos.py` | 비교 실습용 메모 100개(`many_memos/`) 만들기 | CHAPTER 4 실습 2 |

API 키는 이 파일들에 들어 있지 않다. 키는 환경 변수 `LLM_API_KEY` 에 넣는다 (CHAPTER 1 실습 1).

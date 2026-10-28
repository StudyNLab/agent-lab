# agent-lab

교재 **AI Agent 개발 : AI Agent 개발 기초 (초급)** 의 실습 파일이다.

## 받기

Windows PowerShell에서 실행한다. `C:\agent-lab` 에 실습 파일이 들어간다. (교재 CHAPTER 1 실습 1 Step 1)

```powershell
git clone https://github.com/StudyNLab/agent-lab.git C:\agent-lab
```

- Git이 없으면 먼저 설치한다: `winget install --id Git.Git -e --source winget` 또는 https://git-scm.com/install/windows 의 설치 프로그램. 설치한 뒤 PowerShell 창을 새로 연다.
- 실습 파일이 바뀌면 `C:\agent-lab` 에서 `git pull` 로 최신본을 받는다. 직접 만든 파일은 그대로 남는다.
- 이미 `C:\agent-lab` 이 있으면 받을 수 없다. 그 폴더를 다른 이름으로 바꾼 뒤 다시 한다.
- 네트워크가 막혀 `git clone` 이 안 되면 https://github.com/StudyNLab/agent-lab/archive/main.zip 을 받아 `C:\` 에 풀고, 폴더 이름을 `agent-lab-main` 에서 `agent-lab` 으로 바꾼다.

## 들어 있는 것

| 경로 | 내용 | 쓰는 곳 |
|---|---|---|
| `check_setup.py` | 실습 환경 점검 | CHAPTER 1 실습 1 |
| `memos/` | 연습용 메모 7개 | CHAPTER 3 ~ 6 |
| `finished/` | 완성본 메모 정리 도우미와 메모 사본 | CHAPTER 1 실습 2, 따라 쓰다 막힐 때 비교 |
| `code/` | 실습 단계별 전체 코드 (예: `code/ch05_lab1/agent_loop.py` = CHAPTER 5 실습 1). 교재의 `✎ 입력 내용` 이 가리키는 파일 | CHAPTER 2 ~ 6 |
| `make_many_memos.py` | 비교 실습용 메모 100개(`many_memos/`) 만들기 | CHAPTER 4 실습 2 |

API 키는 이 파일들에 들어 있지 않다. 키는 환경 변수 `LLM_API_KEY` 에 넣는다 (CHAPTER 1 실습 1).

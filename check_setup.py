"""실습 환경 점검 (CHAPTER 1 실습 1)

이 과정의 실습에 필요한 것이 이 PC에 준비되어 있는지 확인한다.
  1. 파이썬 버전
  2. 가상 환경 (실습 폴더의 .venv 를 켜고 실행했는가)
  3. requests 라이브러리 (LLM API에 HTTP 요청을 보낼 때 쓴다)
  4. python-dotenv 라이브러리 (.env 파일을 읽을 때 쓴다)
  5. API 키: 실습 폴더의 .env 파일에 LLM_API_KEY 가 있는가 (키 값은 화면에 찍지 않는다)
  6. 연습용 메모 폴더 memos (메모 7개, UTF-8)

실행: python check_setup.py   (가상 환경을 켠 뒤)
"""
import os
import sys
from pathlib import Path

LAB_FOLDER = Path(__file__).resolve().parent
MEMO_FOLDER = LAB_FOLDER / "memos"
VENV_FOLDER = LAB_FOLDER / ".venv"
KEY_FILE = LAB_FOLDER / ".env"
NEED_PYTHON = (3, 13)
NEED_MEMOS = 7

results = []        # (확인 항목, OK 여부, 찾은 값, 아니면 할 일)


# 1. 파이썬 버전
version = sys.version_info
results.append((
    "파이썬 버전",
    version >= NEED_PYTHON,
    f"{version.major}.{version.minor}.{version.micro}",
    "python.org에서 3.13 이상을 설치한다",
))

# 2. 가상 환경: 지금 실행 중인 파이썬이 실습 폴더의 .venv 것인가
in_venv = Path(sys.prefix).resolve() == VENV_FOLDER.resolve()
other_venv = not in_venv and sys.prefix != sys.base_prefix    # 다른 폴더의 가상 환경이 켜져 있다
if in_venv:
    venv_value = "사용 중 (.venv)"
elif other_venv:
    venv_value = f"다른 가상 환경 ({sys.prefix})"
else:
    venv_value = f"사용 안 함 ({sys.prefix})"
venv_todo = []
if other_venv:
    venv_todo.append("deactivate 로 끄고")
if not VENV_FOLDER.exists():
    venv_todo.append("실습 폴더에서 python -m venv .venv 로 만든 뒤")
venv_todo.append(r".\.venv\Scripts\Activate.ps1 로 켠다")
results.append(("가상 환경", in_venv, venv_value, ", ".join(venv_todo)))

# 3. requests 라이브러리
try:
    import requests
    results.append(("requests", True, requests.__version__, ""))
except ImportError:
    results.append(("requests", False, "없음", "가상 환경을 켠 뒤 python -m pip install requests"))

# 4. python-dotenv 라이브러리
try:
    from dotenv import dotenv_values
    import importlib.metadata
    results.append(("python-dotenv", True, importlib.metadata.version("python-dotenv"), ""))
except ImportError:
    dotenv_values = None
    results.append(("python-dotenv", False, "없음", "가상 환경을 켠 뒤 python -m pip install python-dotenv"))

# 5. API 키: .env 파일의 LLM_API_KEY (값은 찍지 않고 길이만 찍는다)
key_todo = r"Copy-Item .env.example .env 로 만들고, notepad .env 로 열어 = 뒤에 키를 넣고 저장한다"
if not KEY_FILE.exists():
    key_ok, key_value = False, ".env 파일 없음"
elif dotenv_values is None:
    key_ok, key_value, key_todo = False, "읽지 못함 (python-dotenv 없음)", "python-dotenv 를 먼저 설치한다"
else:
    key = (dotenv_values(KEY_FILE).get("LLM_API_KEY") or "").strip()
    key_ok = bool(key)
    key_value = f"있음 (길이 {len(key)})" if key else ".env 에 값이 비어 있음"
    key_todo = r"notepad .env 로 열어 LLM_API_KEY= 뒤에 키를 넣고 저장한다"
results.append(("LLM_API_KEY (.env)", key_ok, key_value, key_todo))

# 6. 연습용 메모 폴더
memo_files = sorted(MEMO_FOLDER.glob("*.txt"))
broken = []
for memo in memo_files:
    try:
        memo.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        broken.append(memo.name)
results.append((
    "memos 폴더",
    len(memo_files) == NEED_MEMOS and not broken,
    f"메모 {len(memo_files)}개" + (f", UTF-8 아님 {len(broken)}개" if broken else ""),
    f"실습 폴더 안에 memos 폴더와 메모 {NEED_MEMOS}개를 둔다",
))


print("=" * 60)
print("요약 (여기만 보면 된다)")
print("=" * 60)
print(f"실습 폴더: {LAB_FOLDER}")
for name, ok, value, todo in results:
    mark = "OK  " if ok else "확인"
    line = f"[{mark}] {name}: {value}"
    if not ok:
        line += f"  ➔ {todo}"
    print(line)

failed = [name for name, ok, _, _ in results if not ok]
print("-" * 60)
if failed:
    print(f"확인할 것 {len(failed)}개: {', '.join(failed)}")
else:
    print("모두 OK. 실습 환경이 준비되었다.")

# BASELINE.md

## 작업 폴더와 경로

- 작업 폴더: `C:\Users\click\upstage_mabc`
- 하위 구조(확인 시점):
  - `.git/` 있음
  - `.gitignore`
  - `README.md`
  - `BRAINSTORM.md`
  - `create_repo.py`
  - `github_token.json`

## Git 상태

- 브랜치: `main`
- 마지막 커밋: `819f5fe docs: 브레인스토밍 정제본 저장 (2026-09-11)`
- 문서 생성 전 워킹트리: clean 상태였음
- 문서 생성 후: `docs/ops/BASELINE.md`, `docs/ops/PROGRESS.md` 두 파일이 미추적(untracked) 상태

## Node.js / npm

- 실행 확인:
  - `node --version`: `v22.23.2`
  - `npm --version`: `10.9.8`
  - `npx --version`: `10.9.8`
- 실제 실행 파일 경로: 미확인(버전 명령만 실행함)
- 최신 버전 여부: 미확인
- Vercel CLI(`vercel` 명령): 명령 찾지 못함
  - Vercel 토큰 존재 여부: 이 결과만으로 판단하지 않음(미확인)

## Python

- Hermes 자체 환경(실제 확인):
  - 실행 파일: `/c/Users/click/AppData/Local/hermes/hermes-agent/venv/Scripts/python`
  - 버전: `Python 3.11.16`
- 제품용 별도 Python 환경: 미확인
- `pip list`: 실패
  - 오류: `/c/Users/click/AppData/Local/hermes/hermes-agent/venv/Scripts/pip` 없음
  - 패키지 목록: 확인하지 못함(조회를 성공으로 적지 않음)

## doc-compare 원본 위치(바탕화면 추출 폴더)

- 파일 있음(실제 read_file로 확인):
  - `C:\Users\click\Desktop\doc-compare-extracted\SKILL.md`
  - `C:\Users\click\Desktop\doc-compare-extracted\compare_docs.py`
- SKILL.md:
  - 이름: `doc-compare`
  - 내용: 두 마크다운 문서의 추가/삭제/변경/순서 변경을 비교하고 주의할 변화 요약을 제공하는 스킬 정의
  - 사용 방법: `python3 ./.pi/skills/doc-compare/compare_docs.py <구버전> <신버전>`
  - 입출력:
    - 입력: 비교 대상 마크다운 파일 2개(UTF-8)
    - 출력: 표준 출력(추가/삭제/변경/순서 변경/주의할 변화 요약/요약 통계)
- compare_docs.py:
  - 유형: Python 스크립트(`#!/usr/bin/env python3`)
  - 의존성: 표준 라이브러리만 사용(`re`, `sys`, `collections.OrderedDict`)
  - 외부 패키지 의존성은 코드상 보이지 않음(실제로 별도 설치 요구는 확인하지 않음)

## Hermes 등록/실행 구분

- 바탕화면에 원본 파일 존재: 확인됨
- SKILL.md와 compare_docs.py 내용: 확인됨(읽음)
- Hermes `doc-compare` 스킬 등록 여부: 현재 스킬 목록(`skills_list`)에 없음
  - 즉, "파일이 있다"와 "Hermes에 등록돼 있다"는 별개로 봐야 함
- 실제 비교 스크립트 실행 여부: 확인하지 않음(실행하지 않음)

## 브라우저 도구

- 존재 확인:
  - `tool_search` 결과: `drive_preview`, `desktop_preview` 도구 확인됨
- 실제 작동 확인: 미확인
  - 웹 페이지를 열거나 흐름을 실행한 단계는 진행하지 않음

## 미확인 / 주의사항

- Node.js/npm 실제 실행 파일 경로: 미확인
- Node.js/npm 최신 버전 여부: 미확인
- 제품용 Python 환경: 미확인
- pip 패키지 목록: 실패(조회를 성공으로 적지 않음)
- Vercel CLI 명령: 찾지 못함, 토큰 존재 여부는 이 결과만으로 판단하지 않음
- doc-compare 스크립트 실제 실행 결과: 미확인
- doc-compare Hermes 등록 상태: 목록 기준으로 확인되지 않음
- 브라우저 도구 실제 동작: 미확인

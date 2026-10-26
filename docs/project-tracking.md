# AJAR 작업 추적

AJAR 세 저장소(ajar-core, ajar-template, ajar-practice)의 Issue와 PR을 비공개 개인 GitHub Project 하나에 모읍니다. 브랜드·작업 코드의 자동 동기화가 아니라 사용자가 요청한 추적 메타데이터 연결입니다.

## 표시 내용

- Title과 저장소, Issue/PR 링크: GitHub 원본 항목과 연결
- Status: Todo / In Progress / Done
- Agent state: Waiting / Approved / Running / Succeeded / Failed / Cancelled / Timed out / Needs action / PR open / Closed
- Last run: 해당 Issue의 최신 AI 개발 실행 링크

열린 미승인 Issue는 Todo/Waiting, 승인 라벨이 있으면 Todo/Approved. 개발 실행이 있거나 열린 PR이면 In Progress. 실패는 Agent state에 Failed로 표시합니다. 닫힌 Issue/PR은 Done/Closed이며, 병합과 병합 없이 닫힘의 차이는 원본 PR에서 확인합니다. 테스트 통과는 원본 PR의 Checks에서 확인하며, Succeeded는 개발 workflow 완료를 뜻합니다.

## 동기화

core의 Issue 변경, 관련 workflow 시작·완료와 매시간 예약 실행, 수동 실행으로 전체를 재조회합니다. 다른 두 저장소의 변경 및 이벤트가 누락된 항목은 정기 실행에서 보충합니다. GitHub 예약 실행은 지연될 수 있어 실시간을 보장하지 않습니다. 봇이 생성한 이벤트가 후속 workflow를 만들지 않는 경우도 정기 조회로 보완합니다.
기존 닫힌 Issue와 병합 PR도 포함합니다. 페이지를 끝까지 조회하고 이미 등록된 항목은 재사용합니다. 프로젝트 항목 삭제·archive·저장소 변경은 하지 않습니다. Status와 Agent state는 자동화 관리 필드라 수동 편집하면 다음 동기화에 덮어씁니다.
각 실행의 전체 로그는 Actions에 보관되며 보드에는 최신 링크를 표시합니다. 삭제된 이슈, 대화 원문, 비밀키, 실행별 정확한 청구액은 수집하지 않습니다. 2026-10-26 첫 실패 시험 실행은 Issue #2와 명시적으로 연결합니다. 이후 개발 실행은 표시 이름에 Issue 번호를 넣습니다.

## 설정

로컬: `gh auth refresh -h github.com -s project`로 권한을 승인한 뒤 `python3 -B scripts/sync_project.py --setup`. 동일 이름 보드를 재사용하고 공개 보드는 거절합니다. 기본 Status 필드의 Todo / In Progress / Done을 유지해야 합니다.
Actions: Repository variable `AJAR_PROJECT_NUMBER`, Repository secret `AJAR_PROJECT_TOKEN`이 필요합니다. 개인 Project 쓰기와 비공개 대상 저장소·Actions 읽기를 허용한 토큰을 사용합니다. classic PAT를 사용하면 project/repo 범위가 필요하므로 전용 토큰으로 관리하고 만료·회수 시 갱신합니다. 로컬 로그인 토큰을 자동 복사하지 않습니다. 토큰은 채팅·파일·로그에 넣지 않습니다.
워크플로는 항상 main의 scripts만 checkout합니다. PR 브랜치 코드·산출물은 실행하지 않으며 OpenAI 키와 연결하지 않습니다. GITHUB_TOKEN만으로 개인 Project에 접근할 수 없습니다.

검증: `python3 -B -m unittest discover -s tests -v`. 실제 동기화는 유료 AI를 호출하지 않습니다.

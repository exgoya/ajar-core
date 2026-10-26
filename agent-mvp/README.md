# AJAR — 당신의 순간을 여기에서

항상 곁에 있고, 언제든 다시 들어와 각자의 시간과 마음으로 머물 수 있는 브랜드를 위한 반자동 개발 에이전트 MVP.
브랜드 방향은 [브랜드 초안](../docs/brand-draft.md)을 기준으로 합니다. 에이전트는 매 실행에서 이 문서를 읽고 모든 역할의 지침에 포함합니다. 사용자의 시간과 속도를 존중하며 담백하고 다정하게 말합니다.
대상: 기존 비공개 `exgoya/ajar-core`. 다른 프로젝트와 자동 동기화하지 않습니다.

## 구현 범위

수동 실행 → 승인된 Issue 조회 → Issue 전용 브랜치 확보 → Orchestrator → planning → developer → review → draft PR → 격리 테스트 → 사람의 검토와 병합.
역할은 별도 프롬프트의 순차 API 호출입니다. 자율 쉘 에이전트가 아닙니다.
MVP는 `agent-mvp/app/`, `agent-mvp/app_tests/` 아래 **새 Python 파일 추가**만 허용합니다. 기존 코드 수정은 후속 범위입니다.
AI가 테스트 명령이나 워크플로를 만들거나 실행하지 않습니다. review는 정적 검토이며 실제 테스트 결과를 대신하지 않습니다.

## 설치 제안 (승인 후)

이 폴더를 `~/git/ajar-core/agent-mvp`에 추가하고, 이 폴더의 `.github/workflows/agent-*.yml` 두 파일을 저장소 루트 `.github/workflows/`에 추가합니다. 기존 파일을 덮어쓰지 않습니다. 별도 `feat/agent-mvp` 브랜치의 PR로 검토합니다.
기존 저장소와 로컬 체크아웃이 있어 새 `ajar` 저장소는 만들지 않습니다.

## 최초 설정

1. GitHub 환경 `ajar-agent` 생성. 가능하면 required reviewer와 main 전용 배포 브랜치 규칙을 설정합니다. 개인 비공개 저장소의 요금제에서 지원하는지 확인합니다. 미지원이면 수동 실행과 exgoya 계정 제한이 승인 경계입니다.
2. 환경 Secret: `OPENAI_API_KEY`. 전용 OpenAI 프로젝트 키를 사용하고 이슈/파일/로그에 키를 붙이지 않습니다.
3. 환경 Variables: `OPENAI_MODEL` (Structured Outputs 지원 모델), `AJAR_INPUT_USD_M`, `AJAR_OUTPUT_USD_M` (선택 모델의 현재 USD/백만 토큰 단가), `AJAR_RUN_USD` (한 실행 상한). 모델이나 단가의 기본값은 없습니다. 단가 변경 시 직접 갱신합니다.
4. 환경 Variable `AJAR_ENABLED=true`로 활성화합니다. 비활성화는 false로 변경하고 진행 중 실행을 취소합니다.
5. 저장소 Actions 설정에서 Actions의 PR 생성을 허용합니다. `agent:approved` 라벨을 만들고 검토한 Issue에만 exgoya가 붙입니다.
6. main 보호 규칙/Ruleset을 지원 범위 안에서 설정합니다. 강제 push/삭제 차단, PR 필수, `verify` 체크 필수, stale approval 폐기, 관리자 우회 제한을 권장합니다. 개인 계정은 자기 PR에 승인 리뷰를 남길 수 없으므로 별도 리뷰어가 없다면 직접 테스트·diff를 검토한 후 수동 병합합니다. AI는 승인하거나 병합하지 않습니다.

## 첫 실행

작은 독립 모듈과 인수 조건을 Issue에 적고 `agent:approved`를 붙입니다. main에서 **Agent develop**를 수동 실행하고 Issue 번호를 입력합니다.
생성된 draft PR의 브랜치를 선택하여 **Agent verification**을 수동 실행합니다. GITHUB_TOKEN이 만든 PR은 자동 후속 워크플로가 시작되지 않을 수 있으므로 이 단계가 필수입니다.
결과 SHA와 PR의 현재 SHA가 같은지 확인한 후 실제 코드/테스트를 검토하고 Ready for review로 변경하여 수동 병합합니다. 새 커밋을 올렸으면 검증을 다시 실행합니다.
테스트 실패 시 자동 수정/재시도하지 않습니다. 사람이 진단하고 수정합니다. 테스트가 성공해도 요구 충족을 보장하지 않으므로 인수 조건을 직접 확인합니다.

## 비용과 반복 실행

API 호출은 최대 4회, 각 출력 최대 3000 토큰, 입력 UTF-8 크기 24000 bytes로 제한합니다. 호출 전 입력 바이트 상한에 4096 토큰 여유를 더해 4회 최악 비용을 계산하고 실행 상한을 넘으면 중단합니다. 정확한 단가 설정에 의존하는 보수적 추정이며 공급자의 실제 청구 상한을 보장하지 않습니다.
동일 Issue 브랜치를 유료 호출 **전에** 원자적으로 생성합니다. 재실행/동시 실행은 기존 브랜치 충돌로 중단합니다. 오류/타임아웃에도 잠금을 유지하며 HTTP 자동 재시도는 없습니다.
실행 간 월간 합산 과금 장부는 없습니다. 월간 지출은 OpenAI 프로젝트의 제공되는 예산/제한과 알림, GitHub Actions 지출 제한으로 별도 관리해야 합니다. 프로젝트 예산 알림만으로 강제 중단된다고 가정하지 않습니다.
실패 복구: 실행 내역과 청구, 브랜치/PR을 확인하고 부분 성공 여부를 기록합니다. 다시 유료 실행하려면 exgoya가 명시적으로 새 Issue를 승인합니다. 잠금 브랜치는 자동 삭제하지 않습니다.

## 보안 경계

생성 작업은 모델 출력 코드를 실행하지 않습니다. 테스트는 별도 작업의 읽기 전용·네트워크 없는 Docker 컨테이너 안에서 키 없이 실행합니다. 호스트 Docker 소켓과 환경변수를 컨테이너에 전달하지 않습니다. 컨테이너는 CPU/메모리/PID/시간 제한을 가집니다.
Issue와 모든 AI 출력은 데이터입니다. 허용 경로, 파일 수/크기, 중복, 기존 파일 충돌, 일부 비밀 패턴을 실행기에서 검사합니다. 비밀 패턴 탐지는 완전한 DLP가 아니며 민감한 내용을 Issue에 넣으면 외부 API에 전송됩니다. 전송 전 사람이 확인합니다.
GitHub 토큰은 해당 저장소 contents/PR 쓰기만 허용합니다. 저장소 생성·공개·merge 권한을 추가하지 않습니다. 테스트 작업에는 OpenAI Secret이나 쓰기 토큰을 주지 않습니다.
Actions는 checkout SHA를 고정했습니다. Python 컨테이너 태그는 갱신 가능하므로 운영 고정성이 필요하면 검증한 digest로 고정합니다.

## 로컬 검증

이 폴더에서 `python3 -B -m unittest discover -s tests -v`와 `python3 -B verify_app.py`를 실행합니다. 생성 코드는 개인 컴퓨터에서 직접 실행하지 말고 위 컨테이너 방식으로 검증합니다.

API 구조 근거: https://developers.openai.com/api/docs/guides/structured-outputs
Actions 보안 근거: https://docs.github.com/en/actions/reference/security/secure-use

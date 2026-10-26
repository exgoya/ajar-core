# AJAR Core

**AJAR — 언제든 열려 있는.**
일상 속 다양한 경험과 생각을 자유롭게 나누고 제안하는 라이프스타일 브랜드입니다.
[Brand Definition v1.1](docs/brand-draft.md)을 기준으로 서로 다른 프로젝트를 연결합니다.
개인 계정 `exgoya`가 운영하며, 초기 저장소와 생성되는 Sub Project는 모두 Private입니다.

## 구성
- `docs/brand-draft.md`: 브랜드 철학과 미확정 항목
- `docs/operations.md`: 설정, 실행, 승인, 복구 절차
- `proposals/`: 검토할 AI 기획 JSON
- `projects/`: 프로젝트별 JSON 등록부 (현재 빈 등록부)
- `.github/ISSUE_TEMPLATE/`: 아이디어와 회고
- `.github/workflows/`: 기획 생성, 승인 후 생성, 검증
- `scripts/ajar.py`: Python 표준 라이브러리 기반 실행기
- `tests/`: 승인·충돌·API 경계 검증

## 운영 순서
1. 새로운 실험 Issue를 만듭니다. 외부 AI에 전달할 수 있는 내용만 적습니다.
2. Actions → **Generate plan** → main → Issue 번호를 입력합니다.
3. 생성된 기획 PR의 JSON을 읽고 범위·상한·중단 조건을 수정합니다.
4. `exgoya`가 기획 파일 하나만 추가하는 PR을 main에 병합합니다. 이것이 승인 기록입니다.
5. Actions → **Create project** → main → 승인 PR 번호, apply=false로 검증합니다.
6. 결과를 확인하고 같은 입력에 apply=true를 선택합니다.
7. `ajar-template`에서 `ajar-<slug>` Private 저장소가 생성됩니다.
8. 등록부 PR을 검토·병합하고 자식 저장소의 `docs/brief.md`를 채워 실험을 시작합니다.

AI 결과만으로 생성하거나 공개하지 않습니다. 기획·생성은 수동 시작하므로 상시 비용이 없습니다.
독립 실험 코드는 core에 두지 않습니다. 계획은 등록부에도 보관되며 자식 저장소는 독립적으로 변경합니다.

## 로컬 검증
Python 3.11 이상, 외부 Python 패키지 불필요:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_registry.py
```

실제 AI 호출과 저장소 생성에는 별도 설정이 필요합니다. [운영 안내](docs/operations.md)를 먼저 읽으세요.

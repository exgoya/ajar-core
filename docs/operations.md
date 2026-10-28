# 설정과 운영
상태: MVP / 2026-10-23

## 1. 저장소 및 Actions
- `exgoya/ajar-core`: Public, 기본 브랜치 main (2026-10-28 소유자 공개 승인)
- `exgoya/ajar-template`: Private, Settings → Template repository 활성화
- core Settings → Actions → General: Actions 실행 허용. Workflow permissions에서
  **Allow GitHub Actions to create and approve pull requests**를 활성화합니다.
  워크플로 YAML은 필요한 권한을 각자 선언합니다. 기본 권한은 read로 유지해도 됩니다.
- Actions는 커밋 SHA로 고정했습니다. 업데이트는 변경 내용을 검토한 PR로 진행합니다.
- 보호 규칙은 요금제별 지원을 확인한 후 선택 적용합니다. 개인 계정의 자기 PR 승인에
  의존하지 않도록, 승인 기준은 **exgoya가 기획 PR을 main에 병합한 기록**입니다.
- PR이 변경하는 파일은 새 `proposals/<slug>.json` 하나여야 합니다.
  스크립트·워크플로 변경과 기획 승인은 별도 PR로 진행하세요.

## 2. Secrets와 Variables
core → Settings → Secrets and variables → Actions:

| 종류 | 이름 | 용도 |
|---|---|---|
| Secret | OPENAI_API_KEY | 사용자의 OpenAI API 프로젝트 키. 기획 생성에만 사용 |
| Variable | OPENAI_MODEL | 사용 가능한 Responses API 및 Structured Outputs 지원 모델 ID |
| Secret | AJAR_REPO_TOKEN | exgoya 개인 계정의 저장소 생성용 토큰. 생성 작업에만 사용 |
| 자동 제공 | GITHUB_TOKEN | core 읽기, 기획/등록부 브랜치 및 PR 생성 |

키·토큰을 파일, Issue, PR 또는 채팅에 붙여 넣지 마세요. 키를 발급해 GitHub의 Secret 입력란에 직접 저장합니다.
OpenAI 프로젝트에 예산·알림을 설정하고 모델 ID를 직접 선택하세요. 설정이 비어 있으면 중단합니다.
Issue 제목과 본문(최대 16,000자), 브랜드 초안이 OpenAI로 전송됩니다.
응답은 `store:false`, 최대 출력 3,500토큰으로 요청합니다. 모델 거절·불완전 응답은 기획 PR을 만들지 않습니다.

### 저장소 생성 토큰
기본 GITHUB_TOKEN은 core 범위이므로 다른 Private 저장소 생성·접근용으로 쓰지 않습니다.
가장 단순한 MVP 설정은 만료일을 짧게 정한 **classic PAT의 repo scope**입니다.
현재 자식 템플릿에는 실행 워크플로가 없어 workflow scope는 필요하지 않습니다.
이 권한은 계정의 다른 Private 저장소에도 넓게 적용되므로 토큰을 주기적으로 교체하세요.
Fine-grained PAT를 선택한다면 소유자 exgoya, template 읽기 및 새 저장소 Administration 쓰기 권한을
공식 API 요구사항과 대조하여 구성해야 합니다. 선택된 기존 저장소만 허용하는 토큰은 새 저장소에 접근하지 못할 수 있습니다.
자동화는 `/user` 결과가 exgoya인지 확인하고, 기존 대상 저장소가 보이면 중단합니다.
생성 API도 같은 이름의 저장소를 덮어쓰지 않습니다.

환경의 필수 검토자 기능은 이 MVP의 필수 조건이 아닙니다. 원한다면 요금제 지원을 확인하고
별도 environment를 추가하세요. 현재는 병합 승인과 소유자 한정 수동 실행이 승인 경계입니다.

## 3. 실제 사용
README 순서를 따릅니다. 워크플로는 main에서 exgoya가 수동 실행할 때만 동작합니다.
생성 작업은 PR의 **merge commit SHA**에서 기획을 읽어, 이후 파일 변경이 승인 내용을 바꾸지 못하게 합니다.
`apply=false`는 승인·JSON·등록부를 검사합니다. 이때 다른 저장소의 충돌 여부는 확인하지 않습니다
(GITHUB_TOKEN의 범위 제한). 실제 생성 시 AJAR_REPO_TOKEN으로 충돌을 검사합니다.
생성 작업은 직렬 실행됩니다. 이미 생성된 이름으로 재실행하면 중단하며 변경하지 않습니다.

로컬 실행도 가능하지만 Secret을 명령행 인자로 넣지 마세요. 환경변수로만 전달합니다:

```sh
python3 scripts/ajar.py generate --issue 1
python3 scripts/ajar.py create --pr 2
python3 scripts/ajar.py create --pr 2 --apply
```

로컬 GH_TOKEN은 core contents/pull requests 쓰기, issues 읽기 권한이 필요합니다.
apply 시에만 AJAR_REPO_TOKEN이 추가로 필요합니다. 생성된 자식의 brief는 자동 덮어쓰기하지 않습니다.
core의 등록부에 승인 기획 전체와 원본 PR/commit 링크가 있어 그대로 참고할 수 있습니다.

## 4. 실패 복구
- 401/403: 토큰 만료, scope, 저장소 접근 및 Actions PR 생성 설정을 확인합니다.
- 404: 비공개 저장소의 권한 부족일 수도 있습니다. 저장소 없음으로 단정하지 않습니다.
- 422: 같은 저장소·브랜치·파일 이름 충돌일 수 있습니다. 기존 항목을 먼저 확인합니다.
- AI 실패: PR 생성 전이면 같은 Issue로 다시 실행할 수 있습니다. 비용이 발생했는지 사용량을 확인합니다.
- PR 생성 실패: proposal/register 브랜치와 파일이 이미 생겼을 수 있습니다.
  해당 브랜치에서 main으로 직접 PR을 열고 검토합니다. 자동 삭제·강제 푸시는 하지 않습니다.
- 저장소 생성 후 등록 실패: 로그의 생성 URL과 승인 PR을 확인합니다. 재실행은 기존 저장소 때문에 중단합니다.
  `projects/<slug>.json`을 수동 PR로 추가합니다. 필드는 아래를 따릅니다:
  slug, title, status(planned), repository(https://github.com/exgoya/ajar-<slug>), private(true),
  owner(exgoya), approved_pr(URL), approved_commit(기획 PR의 merge SHA), plan(승인된 JSON 전체).
  `python3 scripts/check_registry.py`로 검증합니다. 기존 자식 저장소는 삭제하지 않습니다.
- 원격 생성 요청의 응답이 시간 초과되면 실제로는 생성됐을 수 있습니다. 먼저 GitHub에서 확인합니다.

## 5. 확장과 한계
MVP는 문서·승인·독립 저장소 생성·등록에 집중합니다. 배포, 일정 예약, 자동 콘텐츠 발행,
자식 프로젝트 상태 동기화는 포함하지 않습니다. 브랜드 문구는 Brand Definition v1.2, 로고와 웹 자산은 [BI v1.3](brand-identity.md)를 따릅니다. core 공개와 자식 프로젝트 공개는 별개입니다.
main의 스크립트·워크플로를 변경할 권한을 가진 계정은 Secret에도 영향을 줄 수 있으므로,
향후 공동 운영 시 보호 규칙·GitHub App·환경 검토자를 별도로 설계합니다.

## 공식 참고
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [GitHub template 생성 API](https://docs.github.com/en/rest/repos/repos#create-a-repository-using-a-template)
- [GITHUB_TOKEN 권한](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)

## GitHub Pages

- 주소: https://exgoya.github.io/ajar-core/
- 배포 소스: `main` 브랜치 `/docs`, 정적 HTML. `docs/.nojekyll`로 별도 Jekyll 변환을 생략합니다.
- 공개 페이지는 현재 브랜드 정의와 BI만 담습니다. 이전 비공개 Sites의 시안 비교 도구는 포함하지 않습니다.
- `brand/assets/`는 기준 자산이고 `docs/assets/bi/`는 Pages 제공용 복사본입니다. 수동으로 두 위치를 함께 반영합니다. ZIP 안의 가이드도 현재 공개 브랜드 문구와 일치시킵니다.
- 공개 승인 범위는 ajar-core입니다. `ajar-template`과 Sub Project의 Private 설정은 유지합니다.
- 공개 전 기존 Git 이력의 71개 blob 및 Issue·PR 본문에서 자격 증명 패턴이 발견되지 않았습니다. 값은 출력하지 않았습니다.
- 배포 후 GitHub Pages API의 상태와 인증 없는 HTTP 응답을 확인합니다.

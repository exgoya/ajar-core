# 구축·검증 기록 — 2026-10-23 (Asia/Seoul)

## 실제 수행
- exgoya 인증을 확인한 후 REST/GraphQL로 두 저장소가 없는 것을 확인했습니다.
- `~/git`의 기존 폴더·저장소 위치를 읽기 전용으로 검사했습니다.
  ajar-core, ajar-template 대상 폴더는 없었습니다. 다른 프로젝트 파일은 변경하지 않았습니다.
- `/Users/goya/git/ajar-core`, `/Users/goya/git/ajar-template`를 새로 만들고 초기 커밋을 업로드했습니다.
- 두 원격 저장소의 `private:true`, 기본 브랜치 main을 확인했습니다.
- ajar-template의 `is_template:true`를 확인했습니다.
- 브랜드·운영 문서는 초안으로 표시했습니다. 이전 대화의 assistant 본문은 참조 표시만 반환되어,
  사용자 요청에 제공된 철학을 기준으로 구성했습니다.

## 검증
- 로컬 Python 단위·경계 테스트 **18개 통과**. 승인자/병합/파일 검증, 불변 commit 조회,
  충돌 중단, dry-run 무변경, 생성 API의 private=true, 잘못된 토큰 소유자/템플릿 거부,
  AI 불완전 응답과 HTTP 오류를 다룹니다.
- JSON 기획/등록부 검증 통과 (초기 등록부는 비어 있음).
- 모든 YAML 문법 파싱 통과.
- 고정한 checkout v4.2.2, setup-python v5.6.0의 SHA를 GitHub 태그와 대조했습니다.
- [초기 실제 GitHub Actions Validate 실행 성공](https://github.com/exgoya/ajar-core/actions/runs/39924638281).
  이 실행은 초기 테스트 14개와 등록부 검증을 수행했습니다. 추가 테스트는 후속 Validate 실행 대상입니다.
- 테스트의 AI/프로젝트 생성 경로는 **모의 API**입니다. 예제 로그 URL은 실제 자식 저장소 생성 결과가 아닙니다.

## 미완료 및 미실행
- OPENAI_API_KEY, AJAR_REPO_TOKEN, OPENAI_MODEL은 아직 미설정입니다. 비밀을 코드에 넣지 않았습니다.
- 실제 유료 AI 호출, 기획 PR 생성, 승인 후 Sub Project 생성의 전체 연결 실행은 하지 않았습니다.
- Actions의 PR 생성·승인 허용 옵션은 자동 승인 검토가 보안 설정 변경으로 거부하여 유지했습니다.
  명시적 사용자 승인을 요청했습니다. 워크플로 자체에는 PR 자동 승인 기능이 없습니다.
- 설정 후 실제 아이디어 Issue 하나로 기획 생성부터 등록까지 운영 안내의 순서로 검증해야 합니다.
- 라이선스, 최종 브랜드·시각 정체성, 공개/배포 정책은 미확정입니다.

## 원격 링크
- https://github.com/exgoya/ajar-core
- https://github.com/exgoya/ajar-template
- 설정 및 복구: [operations.md](operations.md)

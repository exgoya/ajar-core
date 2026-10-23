# 프로젝트 등록부
`projects/<slug>.json`이 프로젝트별 원장이다. 초기 상태는 비어 있다.
생성 워크플로는 원장을 추가하는 PR을 열며, exgoya가 병합하면 등록된다.
상태: planned → active → paused / completed / archived. 전환은 PR로 기록한다.
저장소 삭제나 공개 전환은 등록부 변경만으로 실행되지 않는다.

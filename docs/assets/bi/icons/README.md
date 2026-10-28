# AJAR 앱 아이콘·파비콘 v1.0

C1 독립 심볼과 BI v1.3 컬러를 사용한다. 기본은 Deep moss `#26392D` 바탕과 Open lime `#DBEA5C` 심볼이다. 밝은 대안은 Warm paper `#F2F0E8`와 Deep moss다. 아이콘에는 전체 이름을 넣지 않는다.

## 파일 구성

- `master/`: 정사각 SVG, 256·512·1024·2048 PNG, 밝은 대안, 투명 foreground SVG와 1024 배경 PNG.
- `ios/AppIcon.appiconset/`: iPhone·iPad·App Store 크기의 PNG와 Contents.json.
- `ios/AJARSymbol.imageset/`: 앱 내부에서 색을 지정해 쓰는 SVG template 심볼.
- `ios/ajar-app-icon-1024.png`, `ios/ajar-app-icon-light-1024.png`: 불투명 PNG 원본.
- `android/res/`: 5가지 density의 일반·원형 launcher, v26 adaptive, v33 monochrome, foreground vector와 24dp 알림 심볼.
- `android/play-store-icon-512.png`: 스토어용 정사각 PNG. `adaptive-foreground.svg`, foreground/background 432 PNG도 제공한다.
- `web/`: favicon.svg, favicon.ico(16·32·48), PNG(16·32·48·64·128·256), Apple touch 180, 일반·maskable 아이콘 192·512, manifest와 head 예제.
- `ajar-icons-preview.png`: 둥근 사각·원형 마스크와 실제 파비콘 크기 비교. 마스크는 미리보기용이다.

## iOS

`AppIcon.appiconset`을 Xcode의 Assets.xcassets에 추가하고 App Icon 이름을 AppIcon으로 지정한다. 기존 아이콘 세트가 있다면 내용을 검토해 교체한다. `AJARSymbol.imageset`은 앱 내부 심볼용으로 별도 추가한다.

```swift
Image("AJARSymbol")
    .renderingMode(.template)
```

앱 아이콘 PNG는 투명도·사전 모서리 마스크·그림자를 넣지 않았다. 기본 PNG Asset Catalog를 제공하며, Icon Composer용 프로젝트 파일은 생성하지 않았다. Icon Composer를 사용하는 경우 master의 foreground SVG와 background PNG를 가져와 구성한다.

## Android

필요한 `res/` 파일을 앱의 `app/src/main/res/`에 가져온다. Manifest의 application에 아래 리소스를 지정한다.

```xml
android:icon="@mipmap/ic_launcher"
android:roundIcon="@mipmap/ic_launcher_round"
```

adaptive foreground는 108dp 캔버스에서 중앙 66dp 안전 원 안에 배치했다. 배경은 단색 리소스, 전경은 벡터다. API 33 리소스에는 monochrome 레이어를 포함했다. `ic_stat_ajar`는 알림 small icon으로 사용할 수 있는 흰색·투명 배경의 24dp 벡터다.

## 웹

도메인 루트에 web 폴더의 파일을 배치할 때 `head-snippet.html`을 참고한다. 프로젝트 하위 경로라면 링크, manifest의 id·start_url·scope를 실제 배포 경로에 맞춘다. ajar-core의 `/docs/site.webmanifest`는 GitHub Pages 프로젝트 경로에 맞춰 별도로 작성했다.

일반 아이콘과 maskable 아이콘은 별도 파일이다. maskable 원본의 중요한 획은 중앙 반지름 40%의 안전 원 안에 들어간다. manifest 연결은 오프라인 동작을 구현하지 않는다.

## 작은 크기 보정

C1의 원호·열림·세로획 경로는 그대로다. favicon.svg 및 16·32px PNG에만 선 굵기를 10에서 12로 보정했다. 일반 로고와 앱 아이콘의 선 굵기는 10이다. ICO는 각 크기의 실제 PNG를 묶었다.

## 확인 범위

파일 67개(PNG 46개), iOS 슬롯 18개를 확인했다. 픽셀 크기, PNG 불투명도, ICO 포함 크기, Xcode JSON의 파일·scale 대응, Android XML 리소스 참조·안전 원, maskable 안전 원, 웹 manifest와 링크 검증을 통과했다. iOS·Android 실제 앱 빌드, 기기 런처, Icon Composer 효과 및 스토어 업로드 검증은 실행하지 않았다.

## 공식 기준

- [Apple 앱 아이콘](https://developer.apple.com/design/human-interface-guidelines/app-icons)
- [Xcode asset catalog](https://developer.apple.com/documentation/xcode/configuring-your-app-icon)
- [Android adaptive icons](https://developer.android.com/develop/ui/compose/system/icon_design_adaptive)
- [웹 maskable 안전 영역](https://web.dev/articles/maskable-icon)

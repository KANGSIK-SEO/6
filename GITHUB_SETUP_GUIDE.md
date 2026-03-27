# 🚀 GitHub 저장소 설정 가이드

다음 단계를 따라 GitHub에 저장소를 설정하고 코드를 푸시하세요.

## 📋 단계별 설정

### 1️⃣ GitHub에서 새 저장소 생성

1. [GitHub](https://github.com/new)에 접속합니다
2. **Repository name**: `art-authentication-agent` 입력
3. **Description**: `AI-powered art authentication agent powered by Azure Quantum` (선택사항)
4. **Visibility**: `Public` (데모 링크 공유를 위해)
5. **Initialize this repository with**:
   - ✅ README 체크 해제 (우리가 이미 있음)
   - ✅ .gitignore 체크 해제 (우리가 이미 있음)
   - ✅ license 체크 해제 (필요시 나중에 추가)
6. **Create repository** 클릭

### 2️⃣ 로컬 저장소에서 푸시

다음 명령어를 터미널에서 실행하세요:

```bash
cd /Users/kangsikseo/Downloads/art-authentication-agent

# 원격 저장소 설정 (GitHub에서 생성한 저장소 URL 사용)
git remote add origin https://github.com/kangsikseoul/art-authentication-agent.git

# main 브랜치로 변경
git branch -M main

# 푸시 (PAT 인증 사용)
git push -u origin main
```

### 3️⃣ 인증 안내

- **GitHub 계정**: 본인의 GitHub 사용자명
- **Password**: 제공받은 PAT token 입력
  ```
  ghp_****....**** (개인이 생성한 Token)
  ```

### 4️⃣ 푸시 확인

```bash
git log --oneline
# 아래와 같이 표시되어야 함:
# 53a7a80 (HEAD -> main, origin/main) Add demo link to README
# e8f108b Initial commit: Art Authentication Agent with Azure AI services integration
```

## ✅ 완료 후 확인사항

- [ ] GitHub 저장소에 모든 파일이 업로드됨
- [ ] README.md에 데모 링크 포함 (https://toolofuture.github.io/evollard/)
- [ ] main 브랜치가 protected 상태 확인 (선택사항)
- [ ] 저장소가 Public 상태인지 확인

## 📖 추가 설정 옵션

### GitHub Pages 활성화 (선택사항)
저장소 Settings → Pages → Source: None 또는 다른 브랜치로 설정

### Releases 만들기 (선택사항)
GitHub Releases에서 첫 번째 버전 생성:
- Tag: `v1.0.0`
- Release name: `Art Authentication Agent v1.0.0`
- Description: 주요 기능 및 Azure Quantum 통합 설명

## 🔗 유용한 GitHub 명령어

```bash
# 원격 상태 확인
git remote -v

# 최근 커밋 확인
git log --oneline -5

# 브랜치 상태 확인
git status

# 푸시 재시도 (만약 실패한 경우)
git push -u origin main --force-with-lease
```

---

**완료되면 이 파일은 삭제해도 됩니다.** ✨

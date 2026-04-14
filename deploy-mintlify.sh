#!/bin/bash
# Mintlify 배포 브랜치 동기화 스크립트
# 사용법: ./deploy-mintlify.sh

set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMP_DIR=$(mktemp -d)

echo "📦 콘텐츠 복사 중..."
# mint.json 복사
cp "$REPO_DIR/mint.json" "$TEMP_DIR/"
cp "$REPO_DIR/README.md" "$TEMP_DIR/"

# 각 Space 콘텐츠 복사 (.git 제외)
for dir in 00-databricks-blog 01-databricks-training 20-handson-genie-code-lge-smarttv; do
  if [ -d "$REPO_DIR/$dir" ]; then
    rsync -a --exclude='.git' --exclude='.DS_Store' --exclude='.claude' "$REPO_DIR/$dir/" "$TEMP_DIR/$dir/"
    echo "  ✓ $dir"
  fi
done

echo "🔄 mintlify 브랜치 업데이트 중..."
cd "$REPO_DIR"

# mintlify 브랜치가 없으면 orphan으로 생성
if git rev-parse --verify mintlify >/dev/null 2>&1; then
  git checkout mintlify
  # 기존 파일 정리 (.git 제외)
  git rm -rf --quiet . 2>/dev/null || true
else
  git checkout --orphan mintlify
  git rm -rf --quiet . 2>/dev/null || true
fi

# 콘텐츠 복사
cp -R "$TEMP_DIR"/* .
rm -rf "$TEMP_DIR"

# 커밋 & 푸시
git add -A
if git diff --cached --quiet; then
  echo "ℹ️  변경 사항 없음"
else
  git commit -m "Sync content to mintlify branch ($(date +%Y-%m-%d))"
  git push origin mintlify
  echo "✅ mintlify 브랜치 배포 완료!"
fi

# main 브랜치로 복귀
git checkout main

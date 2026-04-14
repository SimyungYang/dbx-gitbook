#!/bin/bash
# Mintlify 배포 브랜치 동기화 스크립트
# 사용법: ./deploy-mintlify.sh

set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR=$(mktemp -d)
REMOTE_URL=$(cd "$REPO_DIR" && git remote get-url origin)

echo "📦 콘텐츠 복사 중..."

# mint.json, README 복사
cp "$REPO_DIR/mint.json" "$WORK_DIR/"
cp "$REPO_DIR/README.md" "$WORK_DIR/"

# 각 Space 콘텐츠 복사 (.git, .claude, .DS_Store 제외)
for dir in 00-databricks-blog 01-databricks-training 20-handson-genie-code-lge-smarttv; do
  if [ -d "$REPO_DIR/$dir" ]; then
    rsync -a --exclude='.git' --exclude='.DS_Store' --exclude='.claude' "$REPO_DIR/$dir/" "$WORK_DIR/$dir/"
    echo "  ✓ $dir ($(find "$WORK_DIR/$dir" -name '*.md' | wc -l | tr -d ' ') .md files)"
  fi
done

echo "🔄 mintlify 브랜치 업데이트 중..."

# 새 리포에서 작업 (서브모듈 문제 회피)
cd "$WORK_DIR"
git init
git checkout -b mintlify
git add -A
PAGES=$(find . -name '*.md' -not -path './.git/*' | wc -l | tr -d ' ')
git commit -m "Sync $PAGES pages to mintlify branch ($(date +%Y-%m-%d))"
git remote add origin "$REMOTE_URL"
git push origin mintlify --force

echo "✅ mintlify 브랜치 배포 완료! ($PAGES pages)"

# 정리
rm -rf "$WORK_DIR"

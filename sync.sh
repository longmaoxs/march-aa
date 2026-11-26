#!/usr/bin/env bash
# 把本地改动同步到 GitHub（默认 https://github.com/Longmaoxs/march-aa）
# 用法： ./sync.sh "改了什么"
set -euo pipefail
cd "$(dirname "$0")"

msg="${1:-update: $(date '+%Y-%m-%d %H:%M')}"

git add -A
if git diff --cached --quiet; then
  echo "没有要提交的改动。"
else
  git commit -m "$msg"
  echo "已提交：$msg"
fi

git push origin main
echo "已同步到 GitHub。"

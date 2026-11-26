#!/usr/bin/env bash
# march-aa 同步：提交 + 推送（身份已固定在仓库 config 里）
set -euo pipefail
cd "$(dirname "$0")"

git add -A
if git diff --cached --quiet; then
  echo "没有改动，跳过提交"
else
  git commit -q -m "${1:-update}"
  echo "已提交：$(git log --oneline -1)"
fi
git push origin main
echo "已推送：$(git log --oneline -1)"

#!/usr/bin/env bash
set -euo pipefail

REPO_NAME="${GITHUB_REPO_NAME:-amazon-ads-agents}"
VISIBILITY="${GITHUB_VISIBILITY:-private}"
COMMIT_MESSAGE="${1:-更新广告智能体规则}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

if ! command -v git >/dev/null 2>&1; then
  echo "缺少 git，请先安装 git。"
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  cat <<'EOF'
缺少 GitHub CLI: gh

请先安装并登录：

  brew install gh
  gh auth login

然后重新运行：

  ./scripts/sync_to_github.sh
EOF
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  cat <<'EOF'
GitHub CLI 尚未登录。

请先运行：

  gh auth login

登录完成后重新运行本脚本。
EOF
  exit 1
fi

if [ ! -d .git ]; then
  git init
fi

git branch -M main

OWNER="${GITHUB_OWNER:-$(gh api user --jq .login)}"
REPO_FULL="$OWNER/$REPO_NAME"

if ! git remote get-url origin >/dev/null 2>&1; then
  if gh repo view "$REPO_FULL" >/dev/null 2>&1; then
    git remote add origin "https://github.com/$REPO_FULL.git"
  else
    if [ "$VISIBILITY" = "public" ]; then
      gh repo create "$REPO_NAME" --public --source=. --remote=origin --disable-wiki --description "亚马逊广告智能体 AGENTS 规则与参考数据"
    else
      gh repo create "$REPO_NAME" --private --source=. --remote=origin --disable-wiki --description "亚马逊广告智能体 AGENTS 规则与参考数据"
    fi
  fi
fi

git add -A

if git diff --cached --quiet; then
  echo "没有需要提交的变更。"
else
  git commit -m "$COMMIT_MESSAGE"
fi

git push -u origin main
echo "同步完成: https://github.com/$REPO_FULL"

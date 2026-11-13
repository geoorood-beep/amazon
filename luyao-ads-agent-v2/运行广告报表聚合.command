#!/bin/zsh
set -u

PROJECT_DIR="/Users/leo/Documents/陆遥广告智能体"
cd "$PROJECT_DIR" || exit 1

if [[ $# -ge 3 ]]; then
  exec .venv/bin/python scripts/build_ad_decision_packet.py \
    --source-dir "$1" \
    --context "$2" \
    --output-dir "$3"
fi

echo "陆遥广告智能体 V2.1运行时｜V2.0规则集｜六表聚合"
echo "只允许 Rug；不会修改 Amazon 后台。"
echo ""
read "SOURCE_DIR?请输入六张报表所在文件夹: "
read "CONTEXT_PATH?请输入本批次 context.json 路径: "
read "OUTPUT_DIR?请输入输出文件夹: "

exec .venv/bin/python scripts/build_ad_decision_packet.py \
  --source-dir "$SOURCE_DIR" \
  --context "$CONTEXT_PATH" \
  --output-dir "$OUTPUT_DIR"

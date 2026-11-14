#!/usr/bin/env bash
# Start the Claude Code task right away (its API trigger). This is the only way Claude starts on its own: there is
# no hourly run. Needs repo secrets CLAUDE_TASK_URL (the task's "Fire URL") and CLAUDE_TASK_TOKEN.
# Usage: scripts/wake_claude.sh "<why>" [<issue number>]
#
# The call is tried 3 times (network errors, 429, 5xx). With an issue number (and GH_TOKEN + GH_REPO or
# GITHUB_REPOSITORY in the environment):
#   - `crime-busy` was added to the issue less than 2 hours ago → a Claude chat is working on it: no call and no
#     comment (result "busy");
#   - the secrets are missing or the call failed → a 🤖 comment on the issue tells the owner how to start Claude
#     (result "failed"), so the issue never waits silently.
# The result word (ok | busy | failed) is written to $WAKE_RESULT (default /tmp/wake_result): the caller words its
# own comment with it and never promises "Claude sẽ…" after "failed". Never fails the workflow (always exit 0).
set -u
N=${2:-}
REPO=${GH_REPO:-${GITHUB_REPOSITORY:-}}
RESULT=${WAKE_RESULT:-/tmp/wake_result}
BACKOFF=${WAKE_BACKOFF:-10}   # seconds; the tests set 0
finish() { echo "$1" > "$RESULT"; exit 0; }
can_comment() { [ -n "$N" ] && [ -n "$REPO" ] && [ -n "${GH_TOKEN:-}" ]; }

busy_fresh() {   # crime-busy is on the issue and was added less than 2 hours ago (the claim rule of AGENT_CRIME.md §0)
  can_comment || return 1
  gh api "repos/$REPO/issues/$N" --jq '.labels[].name' 2>/dev/null | grep -qx crime-busy || return 1
  local t
  t=$(gh api "repos/$REPO/issues/$N/events?per_page=100" --paginate \
        --jq '.[] | select(.event == "labeled" and .label.name == "crime-busy") | .created_at' 2>/dev/null | tail -1)
  [ -n "$t" ] || return 1
  python3 -c 'import sys, datetime
t = datetime.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00"))
sys.exit(0 if (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() < 7200 else 1)' "$t"
}

fail() {   # $1 = line for the log, $2 = comment for the owner
  echo "::warning::$1"
  if can_comment; then
    gh api -X POST "repos/$REPO/issues/$N/comments" -f body="$2" > /dev/null || echo "::warning::wake: không ghi được bình luận lên phiếu $N"
  fi
  finish failed
}

if busy_fresh; then
  echo "wake: phiếu $N đang có Claude làm trong chat (crime-busy dưới 2 giờ) — không gọi tác vụ Claude"
  finish busy
fi

BUTTON="${GITHUB_SERVER_URL:-https://github.com}/$REPO/actions/workflows/wake.yml"
[ -n "${CLAUDE_TASK_URL:-}" ] && [ -n "${CLAUDE_TASK_TOKEN:-}" ] || {
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    printf '\n### Chưa gọi được Claude ngay\nThêm secrets `CLAUDE_TASK_URL` và `CLAUDE_TASK_TOKEN` (API trigger của tác vụ Claude chung, cùng giá trị như repo văn học) để Claude bắt đầu ngay khi có việc. Không có lượt chạy mỗi giờ: hiện phiếu chờ đến khi làm trong chat.\n' >> "$GITHUB_STEP_SUMMARY"
  fi
  fail "Chưa cài CLAUDE_TASK_URL/CLAUDE_TASK_TOKEN: chưa gọi được Claude. Phiếu chờ đến khi thêm hai secret này rồi bấm Gọi Claude ngay, hoặc làm trong chat." \
       "🤖 Máy chưa gọi được Claude tự động vì repo này chưa cài hai khóa gọi Claude (\`CLAUDE_TASK_URL\` và \`CLAUDE_TASK_TOKEN\`), nên phiếu này đang chờ. Cách làm tiếp: mở chat với Claude và nhắn \"làm tiếp phiếu số $N\". Muốn Claude tự chạy: thêm hai khóa đó ở Settings → Secrets and variables → Actions (cùng giá trị như repo văn học)."
}
# the shared task wakes for several repos: name this channel in the message ("Phiếu vụ án (Nhật) số 3: …"), from
# prompts/channel.json, or from the repo name when the job checked out scripts/ only
CH=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["lang"])' "$(dirname "$0")/../prompts/channel.json" 2>/dev/null || true)
case "${CH:-$REPO}" in ja|*japan-crime*) TAG=Nhật ;; de|*germany-crime*) TAG=Đức ;; *) TAG= ;; esac
WHY=$(printf '%s' "${1:-}" | TAG="$TAG" python3 -c 'import json,os,sys
t = sys.stdin.read()
if os.environ["TAG"]: t = t.replace("vụ án", "vụ án (" + os.environ["TAG"] + ")", 1)
print(json.dumps({"text": t[:300]}))')
OUT=$(mktemp)
for i in 1 2 3; do
  CODE=$(curl -s -o "$OUT" -w '%{http_code}' --max-time 30 -X POST "$CLAUDE_TASK_URL" \
    -H "Authorization: Bearer $CLAUDE_TASK_TOKEN" \
    -H "anthropic-beta: experimental-cc-routine-2026-04-01" -H "anthropic-version: 2023-06-01" \
    -H "Content-Type: application/json" -d "$WHY")
  case "$CODE" in
    2*) echo "wake: Claude đã được gọi ($(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('claude_code_session_url',''))" "$OUT" 2>/dev/null))"
        finish ok ;;
    000|408|429|5*) echo "wake: lần $i không được (HTTP $CODE)"; [ "$i" = 3 ] || sleep $((BACKOFF * i)) ;;
    *) break ;;   # 401, 403, 404…: trying again cannot help
  esac
done
head -c 300 "$OUT"; echo
fail "wake: gọi Claude không được (HTTP $CODE) — bấm Gọi Claude ngay sau, hoặc làm trong chat" \
     "🤖 Máy chưa gọi được Claude tự động (thử 3 lần không được — có thể Claude đang hết lượt dùng), nên phiếu này đang chờ. Cách làm tiếp: bấm nút **Gọi Claude ngay** tại $BUTTON (Run workflow → Run workflow) sau ít phút, hoặc mở chat với Claude và nhắn \"làm tiếp phiếu số $N\"."

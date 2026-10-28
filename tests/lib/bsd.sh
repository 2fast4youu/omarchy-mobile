# SPDX-License-Identifier: MIT
# Fixture edits that behave the same on GNU and BSD userland. Source it from a
# test (`. tests/lib/bsd.sh`) and use the functions instead of the GNU spelling.
#
# GNU `sed -i 'expr' file` edits in place; BSD sed reads the argument after -i
# as a backup suffix, so the GNU spelling treats the expression as the script
# name and the file as the expression: the fixture stays unchanged and sed
# exits 1 with "invalid command code". Same class of surprise as `stat -c`.

sed_inplace() { # sed_inplace <expression> <file>
  local t rc=0
  t=$(mktemp "${TMPDIR:-/tmp}/sed-inplace.XXXXXX") || return 1
  sed "$1" "$2" >"$t" && cat "$t" >"$2" || rc=$?
  rm -f "$t"
  return $rc
}

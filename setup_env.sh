#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025-2026 Zhanpeng Huang
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSE and LICENSING.md in the repository root.
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
HELPER_BIN="$ROOT/build/tools/bin"

if [[ ! -x "$HELPER_BIN/symcc_fuzzing_helper" ]]; then
    echo "Error: build symcc_fuzzing_helper first with ./build_fuzzer_and_concolic_executor.sh." >&2
    exit 1
fi

# Cover interactive terminals and login shells, including new SSH sessions.
login_shell=${SHELL:-/bin/bash}
case "${login_shell##*/}" in
    bash)
        startup_files=("$HOME/.bashrc")
        if [[ -f "$HOME/.bash_profile" ]]; then
            startup_files+=("$HOME/.bash_profile")
        elif [[ -f "$HOME/.bash_login" ]]; then
            startup_files+=("$HOME/.bash_login")
        else
            startup_files+=("$HOME/.profile")
        fi
        ;;
    zsh)
        startup_files=("${ZDOTDIR:-$HOME}/.zshrc" "${ZDOTDIR:-$HOME}/.zprofile")
        ;;
    *)
        echo "Error: this script supports Bash and Zsh login shells." >&2
        exit 1
        ;;
esac

# Quote checkout paths containing spaces or shell metacharacters. The runtime
# guard also avoids duplicate PATH entries when both startup files are loaded.
printf -v quoted_bin '%q' "$HELPER_BIN"
path_line="case \":\${PATH-}:\" in *:${quoted_bin}:*) ;; *) export PATH=${quoted_bin}\"\${PATH:+:\$PATH}\" ;; esac"

for startup_file in "${startup_files[@]}"; do
    if [[ -f "$startup_file" ]] && grep -Fqx -- "$path_line" "$startup_file"; then
        printf 'Already configured: %s\n' "$startup_file"
    else
        printf '\n# concolic-fuzzing: installed helper\n%s\n' "$path_line" >> "$startup_file"
        printf 'Updated: %s\n' "$startup_file"
    fi
done

printf '\nNew terminals will find symcc_fuzzing_helper.\n'
printf 'For this terminal, run: source %q\n' "${startup_files[0]}"

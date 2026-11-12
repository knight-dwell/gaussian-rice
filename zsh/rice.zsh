# rice.zsh: the zsh parts of this rice. Source it from your ~/.zshrc AFTER oh-my-zsh:
#   source ~/.config/zsh/rice.zsh
# (needs oh-my-zsh for the prompt; everything else works without it)

# prompt: the `ket` theme (Ĥ|ψ⟩), or whatever Terminal Studio picked
# put zsh/ket.zsh-theme into ~/.oh-my-zsh/custom/themes/ and set ZSH_THEME="ket" before oh-my-zsh loads,
# or let Terminal Studio write ~/.config/terminal-studio/zsh-theme:
#   [[ -s ~/.config/terminal-studio/zsh-theme ]] && ZSH_THEME=$(<~/.config/terminal-studio/zsh-theme)

# bat-signal greeter: fastfetch + a random quote / joke / short story in a box.
# Terminal Studio can switch it off (it creates ~/.config/terminal-studio/no-fetch);
# RICE_NO_FETCH=1 skips it for apps the dock opens in a terminal.
[[ -e ~/.config/terminal-studio/no-fetch || -n $RICE_NO_FETCH ]] || ~/.local/bin/bat-greeter

# resize fix: the right prompt stayed on every old line and wrapped into garbage
# when the window width changed. Show it only on the current line.
setopt TRANSIENT_RPROMPT
ZLE_RPROMPT_INDENT=0

# zoxide: `z foo` jumps to the most used directory matching foo, `zi` picks interactively
command -v zoxide >/dev/null && eval "$(zoxide init zsh)"

# ── optional speed-ups (uncomment what you use) ─────────────────────────────
# conda: cache the hook (running `conda shell.zsh hook` costs ~0.5 s per shell)
# _conda_hook=~/.cache/zsh/conda-hook.zsh
# if [[ ! -s $_conda_hook || ~/miniconda3/bin/conda -nt $_conda_hook || ~/.condarc -nt $_conda_hook ]]; then
#   mkdir -p ${_conda_hook:h}; ~/miniconda3/bin/conda shell.zsh hook >| $_conda_hook 2>/dev/null
# fi
# source $_conda_hook; unset _conda_hook
#
# nvm: load lazily (~0.3 s per shell); node/npm of the newest installed version are on PATH at once
# export NVM_DIR="$HOME/.nvm"
# _nvm_node=( $NVM_DIR/versions/node/v*(N/On[1]) ); [[ -n $_nvm_node ]] && path=( $_nvm_node/bin $path ); unset _nvm_node
# nvm() { unfunction nvm; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"; nvm "$@"; }

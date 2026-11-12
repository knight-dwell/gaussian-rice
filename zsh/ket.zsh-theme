# ket.zsh-theme: an operator acting on a ket.   ~/dir  git:branch*  Ĥ|ψ⟩
# Ĥ (gold) acts on the state |ψ⟩ (blue); after a failed command the state
# turns red and the exit code appears on the right (current line only, see
# TRANSIENT_RPROMPT in .zshrc). Selected in Terminal Studio → Prompt.

ZSH_THEME_GIT_PROMPT_PREFIX="%{$fg[red]%} "
ZSH_THEME_GIT_PROMPT_SUFFIX="%{$reset_color%} "
ZSH_THEME_GIT_PROMPT_DIRTY="%{$fg[yellow]%}*"
ZSH_THEME_GIT_PROMPT_CLEAN=""

PROMPT='%{$fg_bold[blue]%}%2~%{$reset_color%} $(git_prompt_info)%{$fg_bold[yellow]%}Ĥ%(?.%{$fg_bold[blue]%}.%{$fg_bold[red]%})|ψ⟩%{$reset_color%} '
RPROMPT='%(?..%{$fg[red]%}%? ↵%{$reset_color%})'

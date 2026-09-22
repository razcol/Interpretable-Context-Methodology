# Workspace Preferences

System-level defaults configured once during `setup`. These stay the same across every skill this workspace builds or maintains.

## Default Publish Destination

{{DEFAULT_PUBLISH_DESTINATION}}

If set to "always ask", `stages/06-publish` asks the user every time. Otherwise it uses this as the default and only asks if a skill clearly needs the other option (e.g. a second workspace already needs the same skill).

## Research Depth

{{RESEARCH_DEPTH}}

Guides how much time `stages/03-research` spends exploring candidate approaches before moving to drafting. "Quick" means favor the first solid approach found. "Thorough" means always compare at least two viable paths before drafting.

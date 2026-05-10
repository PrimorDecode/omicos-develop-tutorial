# Sphinx configuration for the OmicOS developer tutorial.
# Chinese-first; uses MyST so contributors can write in Markdown
# instead of reStructuredText.

import datetime

project = "OmicOS 开发者文档"
author = "OmicOS contributors"
copyright = f"{datetime.date.today().year}, {author}"

# Tracks the documentation version, NOT the omicos-core release version.
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx.ext.autosectionlabel",
]

# MyST tweaks — we want code-friendly admonitions and deep linking.
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
    "tasklist",
    "linkify",
    "attrs_inline",
]
myst_heading_anchors = 4

# Single-file pages: each .md becomes its own page; cross-page TOCs
# live in `toctree` directives at the top of each section index.md.
source_suffix = {".md": "markdown"}

language = "zh_CN"
locale_dirs = ["locale/"]
gettext_compact = False

# autosectionlabel scoped per-document so chapter titles don't collide
# across sections.
autosectionlabel_prefix_document = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# ── HTML output ───────────────────────────────────────────────────────
html_theme = "furo"
html_title = project
html_static_path = ["_static"]
html_lang = "zh-CN"
html_show_sourcelink = False
html_theme_options = {
    "navigation_with_keys": True,
    "sidebar_hide_name": False,
    "light_css_variables": {
        "color-brand-primary": "#0d8f5e",
        "color-brand-content": "#0d8f5e",
    },
    "dark_css_variables": {
        "color-brand-primary": "#3ddc97",
        "color-brand-content": "#3ddc97",
    },
}

# Repository link in the right sidebar header.
html_theme_options["source_repository"] = (
    "https://github.com/PrimorDecode/omicos-develop-tutorial"
)
html_theme_options["source_branch"] = "main"
html_theme_options["source_directory"] = "docs/source/"

# Copybutton — strip the leading `$ ` / `>>> ` prompts on copy.
copybutton_prompt_text = r"\$ |>>> |\.\.\. |# "
copybutton_prompt_is_regexp = True

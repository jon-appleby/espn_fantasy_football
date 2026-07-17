from pathlib import Path

CURR_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURR_DIR.parent.parent
DEFAULT_OUTPUTS_DIR = REPO_ROOT / "outputs"
WEEKLY_OUTPUTS_DIR = DEFAULT_OUTPUTS_DIR / "weekly"
YEARLY_OUTPUTS_DIR = DEFAULT_OUTPUTS_DIR / "yearly"
SCRIPTS_DIR = REPO_ROOT / "scripts"
TEMPLATES_DIR = SCRIPTS_DIR / "publish_templates"
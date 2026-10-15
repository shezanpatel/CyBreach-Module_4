import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BETA_DIR = ROOT_DIR / "services" / "pod_beta"

os.chdir(ROOT_DIR)

for p in (ROOT_DIR, BETA_DIR):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

from app.campaign.api import catalog_service

catalog_service.fixtures_dir = ROOT_DIR / "fixtures" / "campaigns"
catalog_service.playbooks_fixture = (
    ROOT_DIR / "fixtures" / "playbooks" / "module1_catalog.json"
)
catalog_service.reload_all()
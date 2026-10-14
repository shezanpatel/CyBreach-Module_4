import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
os.chdir(ROOT_DIR)

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.campaign.api import catalog_service

catalog_service.fixtures_dir = ROOT_DIR / "fixtures" / "campaigns"
catalog_service.playbooks_fixture = (
    ROOT_DIR / "fixtures" / "playbooks" / "module1_catalog.json"
)
catalog_service.reload_all()

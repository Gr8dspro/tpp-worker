import re
class Robots:
    def __init__(self, txt:str):
        self.rules = []
        ua = None
        for line in txt.splitlines():
            line = line.strip()
            if not line or line.startswith("#"): continue
            if line.lower().startswith("user-agent:"):
                ua = line.split(":",1)[1].strip()
            elif line.lower().startswith("disallow:") and ua is not None:
                path = line.split(":",1)[1].strip()
                self.rules.append((ua, path))
    def allowed(self, url:str, agent:str)->bool:
        from urllib.parse import urlparse
        path = urlparse(url).path or "/"
        for ua, dis in self.rules:
            if ua in ("*", agent) and dis and path.startswith(dis):
                return False
        return True

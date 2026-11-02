import urllib.request
import json
import re

class BGPClient:
    def __init__(self):
        # Known common Bangladesh Upstream ASNs for fast local resolution
        self.as_name_cache = {
            "58717": "Summit Communications Ltd",
            "58682": "Level3 Carrier Ltd.",
            "150178": "EXABYTE LTD",
            "137453": "Orange Bangladesh",
            "135341": "Orange Communication",
            "58601": "Aamra Technologies Limited",
            "24389": "Grameenphone Ltd.",
            "24432": "Robi Axiata Limited",
            "24419": "Banglalink Digital Communications",
            "10029": "BTCL (Bangladesh Telecommunications Company)",
            "45271": "Bangla Phone Limited",
            "45758": "Mango Teleservices Ltd.",
            "58764": "Fiber@Home Global Limited",
            "132061": "Fiber@Home Limited",
            "133661": "Novocom Ltd.",
            "132602": "Plusnet Inc",
            "6939": "Hurricane Electric LLC",
            "9498": "Bharti Airtel Ltd.",
            "4755": "TATA Communications",
        }

    def resolve_asn_name(self, asn_num: str):
        num = str(asn_num).strip().replace("AS", "")
        if num in self.as_name_cache:
            return self.as_name_cache[num]
        
        try:
            url = f"https://stat.ripe.net/data/as-overview/data.json?resource=AS{num}"
            req = urllib.request.Request(url, headers={'User-Agent': 'BTRC-Audit/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                holder = data.get("data", {}).get("holder", "")
                if holder:
                    clean = re.sub(r'^[A-Z0-9\-]+\s*-\s*', '', holder)
                    self.as_name_cache[num] = clean
                    return clean
        except Exception:
            pass
        return f"AS{num}"

    def get_live_bgp_profile(self, asn: str):
        if not asn or not asn.startswith("AS"):
            return None
        
        clean_asn = asn.replace("AS", "").strip()
        result = {
            "asn": asn,
            "live_upstreams": [],
            "upstream_count": 0,
            "upstream_asns": [],
            "ipv4_visibility": "Inactive / Not Seen",
            "ipv6_visibility": "Inactive / Not Seen",
            "announced_v4_prefixes": 0,
            "announced_v6_prefixes": 0
        }

        # 1. Fetch live ASN Neighbours (Upstreams/Peers)
        try:
            url_neigh = f"https://stat.ripe.net/data/asn-neighbours/data.json?resource=AS{clean_asn}"
            req = urllib.request.Request(url_neigh, headers={'User-Agent': 'BTRC-Audit/1.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                neighbours = data.get("data", {}).get("neighbours", [])
                
                upstreams = []
                asns = []
                for n in neighbours:
                    n_asn = str(n.get("asn"))
                    name = self.resolve_asn_name(n_asn)
                    upstreams.append(name)
                    asns.append(f"AS{n_asn}")
                
                result["live_upstreams"] = sorted(list(set(upstreams)))
                result["upstream_count"] = len(result["live_upstreams"])
                result["upstream_asns"] = asns
        except Exception as e:
            print(f"[BGPClient] Error neighbours for {asn}: {e}")

        # 2. Fetch Routing Visibility
        try:
            url_stat = f"https://stat.ripe.net/data/routing-status/data.json?resource=AS{clean_asn}"
            req = urllib.request.Request(url_stat, headers={'User-Agent': 'BTRC-Audit/1.0'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())
                vis = data.get("data", {}).get("visibility", {})
                v4 = vis.get("v4", {})
                v6 = vis.get("v6", {})
                
                v4_peers = v4.get("ris_peers_seeing", 0)
                v6_peers = v6.get("ris_peers_seeing", 0)
                
                if v4_peers > 0:
                    result["ipv4_visibility"] = f"Active ({v4_peers} global peers)"
                if v6_peers > 0:
                    result["ipv6_visibility"] = f"Active ({v6_peers} global peers)"
        except Exception:
            pass

        return result

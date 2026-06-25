import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum

from app.config.settings import settings
from app.services.checklist_service import ParsedControl


class GroupingStrategy(str, Enum):
    DOMAIN = "domain"
    FIXED_BATCH = "fixed_batch"
    INDIVIDUAL = "individual"


@dataclass
class ControlGroup:
    name: str
    query: str
    controls: list[ParsedControl]
    group_index: int = 0


_EXPANSIONS: dict[str, str] = {
    "rbac": "role based access control",
    "mfa": "multi factor authentication",
    "iam": "identity and access management",
    "sso": "single sign on",
    "sdlc": "software development lifecycle",
    "bcdr": "business continuity disaster recovery",
    "dlp": "data loss prevention",
    "siem": "security information and event management",
    "pii": "personally identifiable information",
    "phi": "protected health information",
    "acls": "access control lists",
    "tpm": "third party management",
    "dpia": "data protection impact assessment",
    "pbi": "personally identifiable information",
    "hr": "human resources",
    "ir": "incident response",
    "it": "information technology",
    "sw": "software",
    "hw": "hardware",
    "sw": "software",
    "swd": "software development",
    "net": "network",
    "sec": "security",
    "aud": "audit",
    "cfg": "configuration",
    "env": "environment",
    "id": "identity",
    "pw": "password",
    "pwd": "password",
    "grp": "group",
    "usr": "user",
    "auth": "authentication",
    "acc": "access",
    "prv": "privacy",
    "enc": "encryption",
    "dev": "development",
    "res": "resources",
    "ops": "operations",
    "mon": "monitoring",
    "log": "logging",
    "inc": "incident",
    "rec": "recovery",
    "bcp": "business continuity plan",
    "drc": "disaster recovery center",
    "csm": "customer",
    "vnd": "vendor",
    "sup": "supplier",
    "brd": "board",
    "com": "compliance",
    "reg": "regulatory",
    "gbl": "global",
    "gov": "governance",
    "kyc": "know your customer",
    "kpi": "key performance indicators",
    "sla": "service level agreement",
    "kpi": "key performance indicator",
    "kpi": "key performance indicators",
    "kri": "key risk indicator",
    "sox": "sarbanes oxley",
    "gdpr": "general data protection regulation",
    "hipaa": "health insurance portability and accountability act",
    "pci": "payment card industry",
    "dss": "data security standard",
    "fedramp": "federal risk and authorization management program",
    "nist": "national institute of standards and technology",
    "iso": "international organization for standardization",
    "iec": "international electrotechnical commission",
    "soc": "system and organization controls",
    "csa": "cloud security alliance",
    "owasp": "open web application security project",
    "mitre": "mitre attack framework",
    "cve": "common vulnerabilities and exposures",
    "cwe": "common weakness enumeration",
    "cvss": "common vulnerability scoring system",
    "pentest": "penetration testing",
    "vapt": "vulnerability assessment and penetration testing",
    "ssd": "secure software development",
    "sast": "static application security testing",
    "dast": "dynamic application security testing",
    "iaas": "infrastructure as a service",
    "paas": "platform as a service",
    "saas": "software as a service",
    "ids": "intrusion detection system",
    "ips": "intrusion prevention system",
    "edr": "endpoint detection and response",
    "xdr": "extended detection and response",
    "dlp": "data loss prevention",
    "pam": "privileged access management",
    "pim": "privileged identity management",
    "rbac": "role based access control",
    "abac": "attribute based access control",
    "acl": "access control list",
    "nac": "network access control",
    "vpn": "virtual private network",
    "dmz": "demilitarized zone",
    "nat": "network address translation",
    "ips": "internet protocol security",
    "ssl": "secure sockets layer",
    "tls": "transport layer security",
    "ssh": "secure shell",
    "ftp": "file transfer protocol",
    "smtp": "simple mail transfer protocol",
    "http": "hypertext transfer protocol",
    "https": "hypertext transfer protocol secure",
    "dns": "domain name system",
    "dhcp": "dynamic host configuration protocol",
    "vlan": "virtual local area network",
    "lan": "local area network",
    "wan": "wide area network",
    "man": "metropolitan area network",
    "pan": "personal area network",
    "san": "storage area network",
    "nas": "network attached storage",
    "dss": "decision support system",
    "erp": "enterprise resource planning",
    "crm": "customer relationship management",
    "hrm": "human resource management",
    " scm": "supply chain management",
    "bi": "business intelligence",
    "ai": "artificial intelligence",
    "ml": "machine learning",
    "dl": "deep learning",
    "iot": "internet of things",
    "ot": "operational technology",
    "scada": "supervisory control and data acquisition",
    "plc": "programmable logic controller",
    "rtu": "remote terminal unit",
    "hmi": "human machine interface",
    "ics": "industrial control system",
    "dcs": "distributed control system",
    "mes": "manufacturing execution system",
    "qms": "quality management system",
    "cms": "content management system",
    "dms": "document management system",
    "rms": "rights management system",
    "pim": "personal information management",
    "pam": "privileged access management",
    "pim": "privileged identity management",
    "cim": "common information model",
    "dim": "document information management",
    "fim": "file integrity monitoring",
    "nim": "network information management",
    "sim": "security information management",
    "vam": "vulnerability assessment management",
    "iam": "identity and access management",
    "srm": "secure rights management",
    "drm": "digital rights management",
    "grm": "governance risk management",
    "grc": "governance risk and compliance",
    "gxp": "good practice",
    "gmp": "good manufacturing practice",
    "glp": "good laboratory practice",
    "gcp": "good clinical practice",
    "gvp": "good vigilance practice",
    "gpp": "good pharmacovigilance practice",
    "gdp": "good distribution practice",
    "gsp": "good storage practice",
    "gwp": "good warehouse practice",
    "glp": "good laboratory practice",
    "gcp": "good clinical practice",
    "gmp": "good manufacturing practice",
    "gvp": "good vigilance practice",
    "gpp": "good pharmacovigilance practice",
    "gdp": "good distribution practice",
    "gsp": "good storage practice",
    "gwp": "good warehouse practice",
}


def _expand_abbreviations(text: str) -> str:
    """Expand abbreviations in control text to improve retrieval."""
    words = text.lower().split()
    expanded = []
    for word in words:
        clean = re.sub(r"[^a-z]", "", word)
        if clean in _EXPANSIONS:
            expanded.append(_EXPANSIONS[clean])
        expanded.append(word)
    return " ".join(expanded)


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from a text string."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "has", "have", "had",
        "been", "being", "be", "will", "shall", "may", "might", "can", "could",
        "would", "should", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "out", "off", "over", "under", "again", "further",
        "then", "once", "and", "or", "but", "not", "no", "do", "does", "did",
        "it", "its", "this", "that", "these", "those", "all", "each", "every",
        "both", "few", "more", "most", "other", "some", "such", "than", "too",
        "very", "just", "about", "also", "if", "when", "where", "how", "what",
        "which", "who", "whom", "whose", "while", "although", "though", "since",
        "unless", "until", "whether", "whether", "their", "there", "they",
        "them", "we", "our", "us", "you", "your", "he", "him", "his", "she",
        "her", "mine", "yours", "hers", "ours", "theirs", "myself", "yourself",
        "himself", "herself", "itself", "ourselves", "yourselves", "themselves",
    }
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in stop_words and len(w) > 2]


def _build_group_query(domain_name: str, controls: list[ParsedControl]) -> str:
    """Build a deterministic retrieval query from domain + control names + descriptions."""
    parts = [domain_name]

    all_text = domain_name
    for ctrl in controls:
        all_text += " " + ctrl.name
        if ctrl.description:
            all_text += " " + ctrl.description

    keywords = _extract_keywords(all_text)
    seen = set()
    unique_keywords = []
    for kw in keywords:
        expanded = _EXPANSIONS.get(kw, kw)
        if expanded not in seen:
            seen.add(expanded)
            unique_keywords.append(expanded)
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    parts.extend(unique_keywords)
    return " ".join(parts)


class ControlGrouper:
    def __init__(self):
        self._domain_config: dict[str, list[str]] | None = None

    def _load_domain_config(self) -> dict[str, list[str]]:
        if self._domain_config is not None:
            return self._domain_config

        config_path = settings.control_groups_path
        if not os.path.isabs(config_path):
            backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(backend_root, config_path)

        if os.path.exists(config_path):
            with open(config_path) as f:
                self._domain_config = json.load(f)
            print(f"[grouper] loaded {len(self._domain_config)} domains from {config_path}")
        else:
            self._domain_config = self._default_domains()
            print(f"[grouper] no config file, using {len(self._domain_config)} default domains")

        return self._domain_config

    def _default_domains(self) -> dict[str, list[str]]:
        default_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "config", "groups_default.json"
        )
        if os.path.exists(default_path):
            with open(default_path) as f:
                return json.load(f)
        return {"General": []}

    def _match_control_to_domain(
        self, control: ParsedControl, domains: dict[str, list[str]]
    ) -> str:
        text = (control.name + " " + (control.description or "")).lower()
        for domain_name, keywords in domains.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    return domain_name
        return "General"

    def group_by_domain(
        self, controls: list[ParsedControl]
    ) -> list[ControlGroup]:
        domains = self._load_domain_config()
        groups_map: dict[str, list[ParsedControl]] = {}

        for control in controls:
            domain = self._match_control_to_domain(control, domains)
            groups_map.setdefault(domain, []).append(control)

        groups = []
        for idx, (domain_name, domain_controls) in enumerate(groups_map.items()):
            query = _build_group_query(domain_name, domain_controls)
            groups.append(ControlGroup(
                name=domain_name,
                query=query,
                controls=domain_controls,
                group_index=idx,
            ))

        print(f"[grouper] grouped {len(controls)} controls into {len(groups)} domain groups")
        for g in groups:
            print(f"[grouper]   {g.name}: {len(g.controls)} controls")

        return groups

    def group_by_fixed_batch(
        self, controls: list[ParsedControl], batch_size: int
    ) -> list[ControlGroup]:
        groups = []
        for i in range(0, len(controls), batch_size):
            batch = controls[i:i + batch_size]
            names = [c.name for c in batch]
            query = " ".join(names)
            groups.append(ControlGroup(
                name=f"Batch {len(groups) + 1}",
                query=query,
                controls=batch,
                group_index=len(groups),
            ))

        print(f"[grouper] grouped {len(controls)} controls into {len(groups)} fixed batches (size={batch_size})")
        return groups

    def group_individually(
        self, controls: list[ParsedControl]
    ) -> list[ControlGroup]:
        groups = []
        for i, control in enumerate(controls):
            query = _expand_abbreviations(control.name)
            groups.append(ControlGroup(
                name=control.name,
                query=query,
                controls=[control],
                group_index=i,
            ))
        print(f"[grouper] individual mode: {len(groups)} groups (one per control)")
        return groups

    def group(
        self,
        controls: list[ParsedControl],
        strategy: str | None = None,
        batch_size: int | None = None,
    ) -> list[ControlGroup]:
        strategy = strategy or settings.evaluation_mode
        batch_size = batch_size or settings.batch_size

        if strategy == GroupingStrategy.DOMAIN:
            return self.group_by_domain(controls)
        elif strategy == GroupingStrategy.FIXED_BATCH:
            return self.group_by_fixed_batch(controls, batch_size)
        elif strategy == GroupingStrategy.INDIVIDUAL:
            return self.group_individually(controls)
        else:
            print(f"[grouper] unknown strategy '{strategy}', falling back to individual")
            return self.group_individually(controls)


_control_grouper: ControlGrouper | None = None


def get_control_grouper() -> ControlGrouper:
    global _control_grouper
    if _control_grouper is None:
        _control_grouper = ControlGrouper()
    return _control_grouper

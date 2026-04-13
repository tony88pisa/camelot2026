#!/usr/bin/env python3
# ==============================================================================
# AI Trader - Environment Audit Script (Python)
# Created: 2026-04-02 20:45
# Purpose: Verifica tutte le dipendenze e requisiti dell'ambiente locale
# Target: Windows 11 + Python 3.11 + Ollama + MCP
# ==============================================================================
"""
Environment audit script for the AI Trader project.
Checks all required dependencies and generates status reports.
Usage: python scripts/check_environment.py
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


# --- Timestamp for reports  Updated: 2026-04-02 20:45 ---
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DOCS_DIR = PROJECT_ROOT / "docs"


class CheckResult:
    """Single check result  Created: 2026-04-02 20:45"""

    def __init__(self, component: str, status: str, detail: str, version: str = ""):
        self.component = component
        self.status = status  # OK, WARNING, FAIL, SKIP
        self.detail = detail
        self.version = version

    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "status": self.status,
            "detail": self.detail,
            "version": self.version,
        }


class Problem:
    """Problem found during audit  Created: 2026-04-02 20:45"""

    def __init__(self, description: str, suggestion: str):
        self.description = description
        self.suggestion = suggestion

    def to_dict(self) -> dict:
        return {
            "problem": self.description,
            "suggestion": self.suggestion,
        }


class EnvironmentAuditor:
    """Main auditor class  Created: 2026-04-02 20:45"""

    def __init__(self):
        self.results: list[CheckResult] = []
        self.problems: list[Problem] = []

    def add_result(self, component: str, status: str, detail: str, version: str = ""):
        """Add a check result  Updated: 2026-04-02 20:45"""
        result = CheckResult(component, status, detail, version)
        self.results.append(result)

        icons = {"OK": "", "WARNING": " ", "FAIL": "", "SKIP": " "}
        icon = icons.get(status, "?")
        ver_str = f" ({version})" if version else ""
        print(f"  {icon} {component}{ver_str} - {detail}")

    def add_problem(self, description: str, suggestion: str):
        """Register a problem  Updated: 2026-04-02 20:45"""
        self.problems.append(Problem(description, suggestion))

    def _run_cmd(self, cmd: list[str], timeout: int = 10) -> tuple[bool, str]:
        """Run a command and return (success, output)  Updated: 2026-04-02 20:45"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=(os.name == "nt"),
            )
            output = (result.stdout or "").strip()
            if result.returncode != 0 and not output:
                output = (result.stderr or "").strip()
            return result.returncode == 0, output
        except FileNotFoundError:
            return False, "command not found"
        except subprocess.TimeoutExpired:
            return False, "timeout"
        except Exception as e:
            return False, str(e)

    # ===========================================================================
    # CHECK: Windows Version  Updated: 2026-04-02 20:45
    # ===========================================================================
    def check_windows(self):
        print("\n[SECTION] Windows")
        try:
            ver = platform.version()
            release = platform.release()
            system = platform.system()
            machine = platform.machine()

            if system != "Windows":
                self.add_result("OS", "WARNING", f"Non Windows: {system}", ver)
                self.add_problem("OS non Windows", "Questo progetto  pensato per Windows 11")
                return

            self.add_result("Windows Version", "OK", f"{system} {release}", f"Build {ver}")

            # Check Windows 11 (build >= 22000)
            build_parts = ver.split(".")
            if len(build_parts) >= 1:
                try:
                    build_num = int(build_parts[0]) if len(build_parts) == 1 else int(build_parts[2]) if len(build_parts) >= 3 else 0
                    # On Windows, platform.version() returns something like "10.0.22631"
                    # The build number is the third part
                    full_build = int(build_parts[2]) if len(build_parts) >= 3 else int(build_parts[0])
                    if full_build >= 22000:
                        self.add_result("Windows 11 Check", "OK", "Build compatibile con Windows 11")
                    else:
                        self.add_result("Windows 11 Check", "WARNING", f"Build {full_build} < 22000")
                        self.add_problem(
                            f"Build {full_build} potrebbe non essere Windows 11",
                            "Verifica di avere Windows 11 (build >= 22000)",
                        )
                except (ValueError, IndexError):
                    self.add_result("Windows 11 Check", "WARNING", f"Impossibile parsare build: {ver}")

        except Exception as e:
            self.add_result("Windows Version", "FAIL", f"Errore: {e}")

    # ===========================================================================
    # CHECK: Python  Updated: 2026-04-02 20:45
    # ===========================================================================
    def check_python(self):
        print("\n[SECTION] Python")
        py_version = platform.python_version()
        py_path = sys.executable

        self.add_result("Python", "OK", f"Disponibile ({py_path})", py_version)

        # Check target version 3.11
        major, minor = sys.version_info.major, sys.version_info.minor
        if major == 3 and minor == 11:
            self.add_result("Python 3.11 Target", "OK", "Versione target corretta")
        else:
            self.add_result(
                "Python 3.11 Target",
                "WARNING",
                f"Trovato {py_version}, target: 3.11.x",
            )
            self.add_problem(
                f"Python {py_version}, ma il target  3.11.x",
                "Installa Python 3.11 da python.org o usa pyenv-win",
            )

    # ===========================================================================
    # CHECK: pip  Updated: 2026-04-02 20:45
    # ===========================================================================
    def check_pip(self):
        print("\n[SECTION] pip")
        ok, output = self._run_cmd([sys.executable, "-m", "pip", "--version"])
        if ok and output:
            # Parse: pip 23.3.1 from /path/to/pip (python 3.11)
            parts = output.split()
            version = parts[1] if len(parts) > 1 else "unknown"
            self.add_result("pip", "OK", "Disponibile", version)
        else:
            self.add_result("pip", "FAIL", f"Non disponibile: {output}")
            self.add_problem("pip non trovato", "Esegui: python -m ensurepip --upgrade")

    # ===========================================================================
    # CHECK: venv  Updated: 2026-04-02 20:45
    # ===========================================================================
    def check_venv(self):
        print("\n[SECTION] venv")
        try:
            import venv  # noqa: F401

            self.add_result("venv", "OK", "Modulo venv disponibile")
        except ImportError:
            self.add_result("venv", "FAIL", "Modulo venv non disponibile")
            self.add_problem(
                "venv non disponibile",
                "Reinstalla Python con la standard library completa",
            )

    # ===========================================================================
    # CHECK: Node.js  Updated: 2026-04-02 20:45
    # ===========================================================================
    def check_node(self):
        print("\n[SECTION] Node.js")
        if shutil.which("node"):
            ok, output = self._run_cmd(["node", "--version"])
            if ok:
                self.add_result("Node.js", "OK", "Disponibile", output)
            else:
                self.add_result("Node.js", "FAIL", f"Errore: {output}")
        else:
            self.add_result("Node.js", "WARNING", "Non trovato nel PATH")
            self.add_problem(
                "Node.js non trovato",
                "Installa da https://nodejs.org (LTS consigliato)",
            )

    # ===========================================================================
    # CHECK: npm  Updated: 2026-04-02 20:45
    # ===========================================================================
    def check_npm(self):
        print("\n[SECTION] npm")
        if shutil.which("npm"):
            ok, output = self._run_cmd(["npm", "--version"])
            if ok:
                self.add_result("npm", "OK", "Disponibile", output)
            else:
                self.add_result("npm", "FAIL", f"Errore: {output}")
        else:
            self.add_result("npm", "WARNING", "Non trovato nel PATH")
            self.add_problem("npm non trovato", "Si installa automaticamente con Node.js")

    # ===========================================================================
    # CHECK: Git  Updated: 2026-04-02 20:45
    # ===========================================================================
    def check_git(self):
        print("\n[SECTION] Git")
        if shutil.which("git"):
            ok, output = self._run_cmd(["git", "--version"])
            if ok:
                version = output.replace("git version ", "")
                self.add_result("Git", "OK", "Disponibile", version)
            else:
                self.add_result("Git", "FAIL", f"Errore: {output}")
        else:
            self.add_result("Git", "FAIL", "Non trovato nel PATH")
            self.add_problem("Git non trovato", "Installa da https://git-scm.com")

    # ===========================================================================
    # CHECK: Ollama  Updated: 2026-04-02 20:45
    # ===========================================================================
    def check_ollama(self):
        print("\n[SECTION] Ollama")

        # Binary check
        if shutil.which("ollama"):
            ok, output = self._run_cmd(["ollama", "--version"])
            if ok:
                self.add_result("Ollama Binary", "OK", "Disponibile", output.strip())
            else:
                self.add_result("Ollama Binary", "WARNING", f"Trovato ma errore: {output}")
        else:
            self.add_result("Ollama Binary", "FAIL", "Non trovato nel PATH")
            self.add_problem(
                "Ollama non installato",
                "Installa da https://ollama.com/download",
            )

        # API health check
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                model_count = len(data.get("models", []))
                self.add_result(
                    "Ollama API",
                    "OK",
                    f"Server risponde, modelli trovati: {model_count}",
                )
        except urllib.error.URLError:
            self.add_result(
                "Ollama API",
                "WARNING",
                "Server non raggiungibile (potrebbe non essere avviato)",
            )
            self.add_problem(
                "Ollama API non risponde su localhost:11434",
                "Avvia Ollama con: ollama serve",
            )
        except Exception as e:
            self.add_result("Ollama API", "WARNING", f"Errore connessione: {e}")

    # ===========================================================================
    # CHECK: PyTorch / CUDA  Updated: 2026-04-02 20:45
    # ===========================================================================
    def check_pytorch(self):
        print("\n[SECTION] PyTorch / CUDA")
        try:
            import torch

            torch_ver = torch.__version__
            self.add_result("PyTorch", "OK", "Installato", torch_ver)

            if torch.cuda.is_available():
                cuda_ver = torch.version.cuda or "unknown"
                gpu_name = torch.cuda.get_device_name(0)
                self.add_result(
                    "CUDA (via PyTorch)",
                    "OK",
                    f"GPU: {gpu_name}",
                    f"CUDA {cuda_ver}",
                )
            else:
                self.add_result(
                    "CUDA (via PyTorch)",
                    "WARNING",
                    "PyTorch presente ma CUDA non disponibile (CPU-only)",
                )

        except ImportError:
            self.add_result(
                "PyTorch",
                "WARNING",
                "Non installato (non richiesto in questa fase)",
            )
        except Exception as e:
            self.add_result("PyTorch", "WARNING", f"Errore rilevamento: {e}")

    # ===========================================================================
    # CHECK: PATH Analysis  Updated: 2026-04-02 20:45
    # ===========================================================================
    def check_path(self):
        print("\n[SECTION] PATH Analysis")
        import re

        path_entries = os.environ.get("PATH", "").split(os.pathsep)
        keywords = ["python", "node", "npm", "git", "ollama", "cuda", "torch"]
        pattern = re.compile("|".join(keywords), re.IGNORECASE)

        relevant = [p for p in path_entries if pattern.search(p)]
        if relevant:
            for p in relevant:
                self.add_result("PATH", "OK", p)
        else:
            self.add_result(
                "PATH",
                "WARNING",
                "Nessun path rilevante trovato per tool del progetto",
            )

    # ===========================================================================
    # RUN ALL CHECKS  Updated: 2026-04-02 20:45
    # ===========================================================================
    def run_all(self):
        """Execute all environment checks"""
        print("")
        print("=" * 60)
        print("  AI TRADER - Environment Audit (Python)")
        print(f"  Timestamp: {TIMESTAMP}")
        print("=" * 60)

        self.check_windows()
        self.check_python()
        self.check_pip()
        self.check_venv()
        self.check_node()
        self.check_npm()
        self.check_git()
        self.check_ollama()
        self.check_pytorch()
        self.check_path()

        self._print_summary()
        self._generate_reports()

    def _print_summary(self):
        """Print summary to console  Updated: 2026-04-02 20:45"""
        ok_count = sum(1 for r in self.results if r.status == "OK")
        warn_count = sum(1 for r in self.results if r.status == "WARNING")
        fail_count = sum(1 for r in self.results if r.status == "FAIL")
        skip_count = sum(1 for r in self.results if r.status == "SKIP")

        print("")
        print("=" * 60)
        print("  RIEPILOGO")
        print("=" * 60)
        print(f"  OK:      {ok_count}")
        print(f"  WARNING: {warn_count}")
        print(f"  FAIL:    {fail_count}")
        print(f"  SKIP:    {skip_count}")

        if self.problems:
            print("")
            print("  PROBLEMI TROVATI:")
            for prob in self.problems:
                print(f"    - {prob.description}")
                print(f"      Fix: {prob.suggestion}")

    def _generate_reports(self):
        """Generate MD and JSON reports  Updated: 2026-04-02 20:45"""
        DOCS_DIR.mkdir(parents=True, exist_ok=True)

        ok_count = sum(1 for r in self.results if r.status == "OK")
        warn_count = sum(1 for r in self.results if r.status == "WARNING")
        fail_count = sum(1 for r in self.results if r.status == "FAIL")
        skip_count = sum(1 for r in self.results if r.status == "SKIP")

        # --- Markdown Report ---
        status_icons = {"OK": "", "WARNING": "", "FAIL": "", "SKIP": ""}
        md_lines = [
            "# AI Trader  Environment Status Report",
            "",
            f"> Generated: {TIMESTAMP}",
            f"> Machine: {platform.node()}",
            f"> User: {os.getenv('USERNAME', os.getenv('USER', 'unknown'))}",
            "",
            "## Check Results",
            "",
            "| Component | Status | Version | Detail |",
            "|-----------|--------|---------|--------|",
        ]
        for r in self.results:
            icon = status_icons.get(r.status, "?")
            md_lines.append(
                f"| {r.component} | {icon} {r.status} | {r.version} | {r.detail} |"
            )

        md_lines.extend([
            "",
            "## Summary",
            "",
            f"- **OK**: {ok_count}",
            f"- **Warning**: {warn_count}",
            f"- **Fail**: {fail_count}",
            f"- **Skip**: {skip_count}",
        ])

        if self.problems:
            md_lines.extend(["", "## Problems & Recommendations", ""])
            for prob in self.problems:
                md_lines.extend([
                    f"###  {prob.description}",
                    f"**Suggestion**: {prob.suggestion}",
                    "",
                ])

        md_path = DOCS_DIR / "ENVIRONMENT_STATUS.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        print(f"\n  Report MD salvato: {md_path}")

        # --- JSON Report ---
        json_data = {
            "timestamp": TIMESTAMP,
            "machine": platform.node(),
            "user": os.getenv("USERNAME", os.getenv("USER", "unknown")),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "results": [r.to_dict() for r in self.results],
            "problems": [p.to_dict() for p in self.problems],
            "summary": {
                "ok": ok_count,
                "warning": warn_count,
                "fail": fail_count,
                "skip": skip_count,
            },
        }
        json_path = DOCS_DIR / "environment_status.json"
        json_path.write_text(
            json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  Report JSON salvato: {json_path}")

        print("")
        print("=" * 60)
        print("  Audit completato.")
        print("=" * 60)
        print("")


# ===========================================================================
# MAIN  Updated: 2026-04-02 20:45
# ===========================================================================
if __name__ == "__main__":
    auditor = EnvironmentAuditor()
    auditor.run_all()

import os
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Set, Tuple, Optional
from .models import AnalyzedFile, ProjectAnalysis

class ScannerEngine:
    def __init__(self):
        # Compiled regexes for C# files
        self.using_regex = re.compile(r'^\s*using\s+([A-Za-z0-9_.]+)(?:\s*=\s*[A-Za-z0-9_.]+)?\s*;', re.MULTILINE)
        self.namespace_regex = re.compile(r'^\s*namespace\s+([A-Za-z0-9_.]+)', re.MULTILINE)
        self.class_regex = re.compile(r'\bclass\s+([A-Za-z0-9_<>]+)\b', re.MULTILINE)
        
        # Regexes for WebForms/WCF directives in aspx/asmx/svc
        self.inherits_regex = re.compile(r'(?:Inherits|Service|Class)\s*=\s*["\']([A-Za-z0-9_.]+)["\']', re.IGNORECASE)

    def scan_directory(self, dir_path: str, target_file: Optional[str] = None) -> ProjectAnalysis:
        """Recursively scan a directory for .NET project files and analyze them."""
        analysis = ProjectAnalysis()
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"Directory {dir_path} does not exist.")

        # Supported file extensions
        supported_extensions = {'.cs', '.config', '.csproj', '.aspx', '.asmx', '.svc', '.asax'}

        if target_file:
            # Single file scan mode
            file_path = os.path.join(dir_path, target_file)
            rel_path = target_file
            _, ext = os.path.splitext(target_file.lower())

            if os.path.basename(target_file).lower() == 'global.asax':
                analysis.technologies.add('WebForms')
                if 'Global.asax File' not in analysis.detected_patterns:
                    analysis.detected_patterns['Global.asax File'] = []
                analysis.detected_patterns['Global.asax File'].append(rel_path)

            if os.path.basename(target_file).lower() == 'web.config':
                analysis.technologies.add('ASP.NET Legacy')
                if 'Web.config File' not in analysis.detected_patterns:
                    analysis.detected_patterns['Web.config File'] = []
                analysis.detected_patterns['Web.config File'].append(rel_path)

            if ext in supported_extensions:
                try:
                    analyzed_file = self._parse_file(file_path, ext, rel_path)
                    analysis.files.append(analyzed_file)
                except Exception as e:
                    analysis.files.append(AnalyzedFile(
                        file_path=rel_path,
                        extension=ext,
                        detected_patterns=[f"ParseError: {str(e)}"]
                    ))
            
            self._aggregate_analysis(analysis)
            self._calculate_complexity(analysis)
            return analysis

        for root, dirs, files in os.walk(dir_path):
            # Prune directories we don't want to scan (like backups, bin, obj, git)
            dirs[:] = [d for d in dirs if d.lower() not in {'.git', '.vs', 'bin', 'obj', 'backups', 'packages', '.venv', 'node_modules'}]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, dir_path)
                _, ext = os.path.splitext(file.lower())

                # Special checks for legacy files even if we don't parse them deeply
                if file.lower() == 'global.asax':
                    analysis.technologies.add('WebForms')
                    if 'Global.asax File' not in analysis.detected_patterns:
                        analysis.detected_patterns['Global.asax File'] = []
                    analysis.detected_patterns['Global.asax File'].append(rel_path)

                if file.lower() == 'web.config':
                    analysis.technologies.add('ASP.NET Legacy')
                    if 'Web.config File' not in analysis.detected_patterns:
                        analysis.detected_patterns['Web.config File'] = []
                    analysis.detected_patterns['Web.config File'].append(rel_path)

                if ext in supported_extensions:
                    try:
                        analyzed_file = self._parse_file(file_path, ext, rel_path)
                        analysis.files.append(analyzed_file)
                    except Exception as e:
                        # Log error and continue scanning to be resilient
                        # We can still add an empty/partially analyzed file
                        analysis.files.append(AnalyzedFile(
                            file_path=rel_path,
                            extension=ext,
                            detected_patterns=[f"ParseError: {str(e)}"]
                        ))

        # Post-scan aggregation
        self._aggregate_analysis(analysis)
        self._calculate_complexity(analysis)
        return analysis

    def _parse_file(self, file_path: str, ext: str, rel_path: str) -> AnalyzedFile:
        """Parse file depending on its extension."""
        # Read file content safely
        content = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()

        lines = content.splitlines()
        loc = len(lines)

        analyzed = AnalyzedFile(
            file_path=rel_path,
            extension=ext,
            lines_of_code=loc
        )

        if ext == '.cs':
            self._analyze_cs(content, analyzed)
        elif ext == '.csproj':
            self._analyze_csproj(content, analyzed)
        elif ext == '.config':
            self._analyze_config(content, analyzed)
        elif ext in {'.aspx', '.asmx', '.svc', '.asax'}:
            self._analyze_markup(content, ext, analyzed)

        return analyzed

    def _analyze_cs(self, content: str, file: AnalyzedFile):
        # Extract namespaces
        namespaces = self.namespace_regex.findall(content)
        file.namespaces = list(set(namespaces))

        # Extract using statements
        usings = self.using_regex.findall(content)
        file.usings = list(set(usings))

        # Extract classes
        classes = self.class_regex.findall(content)
        file.classes = list(set(classes))

        # Detect WCF patterns
        if 'ServiceContract' in content or 'OperationContract' in content:
            file.detected_patterns.append('WCF Service Contract')
        
        # Detect WebForms patterns
        # Look for inheritance from Page or UserControl
        if re.search(r':\s*(?:System\.Web\.UI\.)?Page\b', content) or 'Page_Load' in content:
            file.detected_patterns.append('WebForms Page')
        if re.search(r':\s*(?:System\.Web\.UI\.)?UserControl\b', content):
            file.detected_patterns.append('WebForms UserControl')
        if 'ViewState' in content:
            file.detected_patterns.append('WebForms ViewState Usage')

        # Detect Legacy System.Web and HttpContext
        if any('System.Web' in u for u in file.usings) or 'System.Web' in content:
            file.detected_patterns.append('System.Web Reference')
        if 'HttpContext.Current' in content:
            file.detected_patterns.append('HttpContext.Current Usage')

    def _analyze_csproj(self, content: str, file: AnalyzedFile):
        # We parse the XML and handle potential namespaces
        try:
            root = ET.fromstring(content)
            
            # Helper to recursively strip namespaces and find elements
            def strip_ns(tag):
                return tag.split('}')[-1] if '}' in tag else tag

            for elem in root.iter():
                tag = strip_ns(elem.tag)
                
                # Extract Target Framework
                if tag == 'TargetFramework':
                    if elem.text:
                        file.dependencies['TargetFramework'] = elem.text.strip()
                elif tag == 'TargetFrameworkVersion':
                    if elem.text:
                        file.dependencies['TargetFrameworkVersion'] = elem.text.strip()
                
                # Extract Package References (SDK style or package reference style)
                elif tag == 'PackageReference':
                    include = elem.attrib.get('Include')
                    version = elem.attrib.get('Version')
                    # Sometime version is a child element
                    if not version:
                        ver_elem = elem.find('{*}Version')
                        if ver_elem is None:
                            ver_elem = elem.find('Version')
                        if ver_elem is not None and ver_elem.text:
                            version = ver_elem.text.strip()
                    if include:
                        file.dependencies[include] = version or 'Unknown'

                # Extract classic References (assembly references)
                elif tag == 'Reference':
                    include_full = elem.attrib.get('Include')
                    if include_full:
                        name = include_full.split(',')[0].strip()
                        file.dependencies[f"AssemblyReference:{name}"] = 'Local/GAC'
        except Exception as e:
            file.detected_patterns.append(f"XmlParseError: {str(e)}")

    def _analyze_config(self, content: str, file: AnalyzedFile):
        # Check if packages.config
        is_packages_config = 'packages' in os.path.basename(file.file_path).lower()
        
        try:
            root = ET.fromstring(content)
            tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag

            if tag == 'packages' or is_packages_config:
                # This is a NuGet packages.config file
                for elem in root.findall('.//package') + root.findall('package'):
                    pkg_id = elem.attrib.get('id')
                    version = elem.attrib.get('version')
                    if pkg_id:
                        file.dependencies[pkg_id] = version or 'Unknown'
            else:
                # This is a web.config or app.config
                # Check for legacy tags
                if root.find('.//system.web') is not None or root.find('system.web') is not None:
                    file.detected_patterns.append('Legacy <system.web> Configuration')
                if root.find('.//system.serviceModel') is not None or root.find('system.serviceModel') is not None:
                    file.detected_patterns.append('WCF <system.serviceModel> Configuration')
        except Exception as e:
            # Config file might be raw text, or malformed XML. Let's search strings.
            if '<system.web>' in content:
                file.detected_patterns.append('Legacy <system.web> Configuration')
            if '<system.serviceModel>' in content:
                file.detected_patterns.append('WCF <system.serviceModel> Configuration')
            if '<package id=' in content:
                # Attempt regex match for packages if XML failed
                pkg_matches = re.findall(r'<package\s+id=["\']([^"\']+)["\']\s+version=["\']([^"\']+)["\']', content)
                for pkg_id, version in pkg_matches:
                    file.dependencies[pkg_id] = version

    def _analyze_markup(self, content: str, ext: str, file: AnalyzedFile):
        # For .aspx, .asmx, .svc files
        # Extract class in Inherits directive
        inherits_match = self.inherits_regex.search(content)
        if inherits_match:
            file.classes.append(inherits_match.group(1))

        if ext == '.aspx':
            file.detected_patterns.append('WebForms ASPX File')
        elif ext == '.asmx':
            file.detected_patterns.append('WebForms ASMX Web Service File')
        elif ext == '.svc':
            file.detected_patterns.append('WCF SVC Service File')

    def _aggregate_analysis(self, analysis: ProjectAnalysis):
        """Aggregate files data into project analysis level."""
        for file in analysis.files:
            # Aggregate dependencies
            for dep, ver in file.dependencies.items():
                if dep not in analysis.dependencies:
                    analysis.dependencies[dep] = ver
                elif ver != 'Unknown' and analysis.dependencies[dep] == 'Unknown':
                    analysis.dependencies[dep] = ver

            # Aggregate technologies and detected patterns
            for pattern in file.detected_patterns:
                if pattern not in analysis.detected_patterns:
                    analysis.detected_patterns[pattern] = []
                analysis.detected_patterns[pattern].append(file.file_path)

                # Map patterns to technologies
                if 'WCF' in pattern:
                    analysis.technologies.add('WCF')
                elif 'WebForms' in pattern or 'ASPX' in pattern or 'ASMX' in pattern:
                    analysis.technologies.add('WebForms')
                elif 'System.Web' in pattern or 'HttpContext' in pattern or 'web.config' in pattern.lower():
                    analysis.technologies.add('ASP.NET Legacy')

            # Handle case where file extension is WCF / WebForms
            if file.extension == '.svc':
                analysis.technologies.add('WCF')
            elif file.extension in {'.aspx', '.asmx'}:
                analysis.technologies.add('WebForms')

        # Extract target framework from aggregated dependencies
        target_framework = analysis.dependencies.get('TargetFramework') or analysis.dependencies.get('TargetFrameworkVersion')
        if target_framework:
            # E.g. net472, net48, v4.5
            if 'net4' in target_framework or 'v4.' in target_framework or 'v3.' in target_framework or 'v2.' in target_framework:
                analysis.technologies.add('.NET Framework (Legacy)')
            elif 'net8' in target_framework:
                analysis.technologies.add('.NET 8.0')
            elif 'net' in target_framework:
                analysis.technologies.add('.NET Core / .NET 5+')

    def _calculate_complexity(self, analysis: ProjectAnalysis):
        """Calculate the complexity score for the project."""
        score = 0
        total_loc = sum(f.lines_of_code for f in analysis.files)

        # Lines of code: +1 point per 1000 lines
        score += total_loc // 1000

        # Technology impacts
        if 'WCF' in analysis.technologies:
            score += 30
        if 'WebForms' in analysis.technologies:
            score += 40
        if 'ASP.NET Legacy' in analysis.technologies:
            score += 15
        if '.NET Framework (Legacy)' in analysis.technologies:
            score += 15

        # File count and types impacts
        for file in analysis.files:
            if file.extension in {'.aspx', '.svc', '.asmx'}:
                score += 5  # Markup files are hard to port
            if file.extension == '.cs':
                score += 1  # Logic complexity per C# file
            
            # Pattern specific increments
            for pattern in file.detected_patterns:
                if 'WCF' in pattern:
                    score += 5
                if 'WebForms' in pattern:
                    score += 5
                if 'HttpContext.Current' in pattern:
                    score += 2

        analysis.complexity_score = max(1, score)

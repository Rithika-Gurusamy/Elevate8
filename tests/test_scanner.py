import os
import pytest
from src.scanner.engine import ScannerEngine
from src.scanner.models import ProjectAnalysis, AnalyzedFile

def test_cs_parsing(tmp_path):
    cs_content = """
    using System;
    using System.Web;
    using MyNamespace.Services;

    namespace LegacyApp.Web
    {
        [ServiceContract]
        public class LegacyService : System.Web.UI.Page
        {
            [OperationContract]
            public void DoWork()
            {
                var ctx = HttpContext.Current;
                var state = ViewState["MyState"];
            }
        }
    }
    """
    
    file_path = tmp_path / "Service.cs"
    file_path.write_text(cs_content)
    
    engine = ScannerEngine()
    analyzed = engine._parse_file(str(file_path), ".cs", "Service.cs")
    
    assert "LegacyApp.Web" in analyzed.namespaces
    assert "System" in analyzed.usings
    assert "System.Web" in analyzed.usings
    assert "MyNamespace.Services" in analyzed.usings
    assert "LegacyService" in analyzed.classes
    assert "WCF Service Contract" in analyzed.detected_patterns
    assert "WebForms Page" in analyzed.detected_patterns
    assert "WebForms ViewState Usage" in analyzed.detected_patterns
    assert "System.Web Reference" in analyzed.detected_patterns
    assert "HttpContext.Current Usage" in analyzed.detected_patterns

def test_csproj_parsing_legacy(tmp_path):
    csproj_content = """<?xml version="1.0" encoding="utf-8"?>
    <Project ToolsVersion="15.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
      <PropertyGroup>
        <TargetFrameworkVersion>v4.7.2</TargetFrameworkVersion>
      </PropertyGroup>
      <ItemGroup>
        <Reference Include="System.Web" />
        <Reference Include="System.ServiceModel" />
      </ItemGroup>
    </Project>
    """
    
    file_path = tmp_path / "App.csproj"
    file_path.write_text(csproj_content)
    
    engine = ScannerEngine()
    analyzed = engine._parse_file(str(file_path), ".csproj", "App.csproj")
    
    assert analyzed.dependencies["TargetFrameworkVersion"] == "v4.7.2"
    assert analyzed.dependencies["AssemblyReference:System.Web"] == "Local/GAC"
    assert analyzed.dependencies["AssemblyReference:System.ServiceModel"] == "Local/GAC"

def test_csproj_parsing_sdk(tmp_path):
    csproj_content = """
    <Project Sdk="Microsoft.NET.Sdk">
      <PropertyGroup>
        <TargetFramework>net8.0</TargetFramework>
      </PropertyGroup>
      <ItemGroup>
        <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
        <PackageReference Include="Microsoft.EntityFrameworkCore">
          <Version>8.0.0</Version>
        </PackageReference>
      </ItemGroup>
    </Project>
    """
    
    file_path = tmp_path / "App.csproj"
    file_path.write_text(csproj_content)
    
    engine = ScannerEngine()
    analyzed = engine._parse_file(str(file_path), ".csproj", "App.csproj")
    
    assert analyzed.dependencies["TargetFramework"] == "net8.0"
    assert analyzed.dependencies["Newtonsoft.Json"] == "13.0.3"
    assert analyzed.dependencies["Microsoft.EntityFrameworkCore"] == "8.0.0"

def test_config_parsing(tmp_path):
    config_content = """<?xml version="1.0" encoding="utf-8"?>
    <configuration>
      <system.web>
        <compilation debug="true" targetFramework="4.7.2" />
      </system.web>
      <system.serviceModel>
        <services>
          <service name="LegacyService" />
        </services>
      </system.serviceModel>
    </configuration>
    """
    
    file_path = tmp_path / "web.config"
    file_path.write_text(config_content)
    
    engine = ScannerEngine()
    analyzed = engine._parse_file(str(file_path), ".config", "web.config")
    
    assert "Legacy <system.web> Configuration" in analyzed.detected_patterns
    assert "WCF <system.serviceModel> Configuration" in analyzed.detected_patterns

def test_packages_config_parsing(tmp_path):
    packages_content = """<?xml version="1.0" encoding="utf-8"?>
    <packages>
      <package id="Newtonsoft.Json" version="12.0.3" targetFramework="net472" />
      <package id="EntityFramework" version="6.4.4" targetFramework="net472" />
    </packages>
    """
    
    file_path = tmp_path / "packages.config"
    file_path.write_text(packages_content)
    
    engine = ScannerEngine()
    analyzed = engine._parse_file(str(file_path), ".config", "packages.config")
    
    assert analyzed.dependencies["Newtonsoft.Json"] == "12.0.3"
    assert analyzed.dependencies["EntityFramework"] == "6.4.4"

def test_markup_parsing(tmp_path):
    aspx_content = '<%@ Page Language="C#" CodeBehind="Default.aspx.cs" Inherits="LegacyApp.Default" %>'
    svc_content = '<%@ ServiceHost Language="C#" Debug="true" Service="LegacyApp.Service" %>'
    
    aspx_path = tmp_path / "Default.aspx"
    aspx_path.write_text(aspx_content)
    
    svc_path = tmp_path / "Service.svc"
    svc_path.write_text(svc_content)
    
    engine = ScannerEngine()
    
    aspx_analyzed = engine._parse_file(str(aspx_path), ".aspx", "Default.aspx")
    assert "LegacyApp.Default" in aspx_analyzed.classes
    assert "WebForms ASPX File" in aspx_analyzed.detected_patterns
    
    svc_analyzed = engine._parse_file(str(svc_path), ".svc", "Service.svc")
    assert "LegacyApp.Service" in svc_analyzed.classes
    assert "WCF SVC Service File" in svc_analyzed.detected_patterns

def test_scan_directory(tmp_path):
    # Set up a structured legacy directory
    os.makedirs(tmp_path / "SubFolder")
    
    # 1. cs file
    (tmp_path / "SubFolder" / "Home.aspx.cs").write_text("""
    using System.Web;
    public class Home : System.Web.UI.Page { }
    """)
    
    # 2. aspx file
    (tmp_path / "SubFolder" / "Home.aspx").write_text('<%@ Page Inherits="Home" %>')
    
    # 3. csproj file
    (tmp_path / "LegacyApp.csproj").write_text("""
    <Project ToolsVersion="15.0">
      <PropertyGroup>
        <TargetFrameworkVersion>v4.8</TargetFrameworkVersion>
      </PropertyGroup>
    </Project>
    """)
    
    # 4. global.asax
    (tmp_path / "Global.asax").write_text("")
    
    engine = ScannerEngine()
    analysis = engine.scan_directory(str(tmp_path))
    
    assert len(analysis.files) == 4
    assert "WebForms" in analysis.technologies
    assert "ASP.NET Legacy" in analysis.technologies
    assert ".NET Framework (Legacy)" in analysis.technologies
    assert "LegacyApp.csproj" in [f.file_path for f in analysis.files]
    assert analysis.complexity_score > 0

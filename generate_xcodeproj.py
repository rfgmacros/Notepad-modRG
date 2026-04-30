#!/usr/bin/env python3
"""Generate an Xcode project for Notepad++ macOS from the CMake-based source tree."""

import hashlib
import os
import glob

# ---------------------------------------------------------------------------
# Helper: deterministic 24-char hex IDs (Xcode convention)
# ---------------------------------------------------------------------------
_id_counter = [0]

def uid(label: str) -> str:
    """Return a deterministic 24-hex-char ID based on a label."""
    _id_counter[0] += 1
    h = hashlib.md5(f"{label}:{_id_counter[0]}".encode()).hexdigest()[:24].upper()
    return h

# ---------------------------------------------------------------------------
# Collect source files
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))

def rel(path):
    return os.path.relpath(path, ROOT)

# Scintilla core .cxx
sci_cxx = sorted(glob.glob(os.path.join(ROOT, "scintilla/src/*.cxx")))
# Scintilla cocoa .mm
sci_mm = [
    os.path.join(ROOT, "scintilla/cocoa/PlatCocoa.mm"),
    os.path.join(ROOT, "scintilla/cocoa/ScintillaCocoa.mm"),
    os.path.join(ROOT, "scintilla/cocoa/ScintillaView.mm"),
    os.path.join(ROOT, "scintilla/cocoa/InfoBar.mm"),
]

# Lexilla
lex_src = sorted(glob.glob(os.path.join(ROOT, "lexilla/src/*.cxx")))
lex_lexers = sorted(glob.glob(os.path.join(ROOT, "lexilla/lexers/*.cxx")))
# Remove upstream LexUser.cxx from lexilla/lexers
lex_lexers = [f for f in lex_lexers if not f.endswith("LexUser.cxx")]
lex_lexlib = sorted(glob.glob(os.path.join(ROOT, "lexilla/lexlib/*.cxx")))
lex_custom = [os.path.join(ROOT, "src/LexUser.cxx")]

lex_all = lex_src + lex_lexers + lex_lexlib + lex_custom

# App sources (from CMakeLists.txt lines 71-111)
app_mm = [
    "src/main.mm",
    "src/NppApplication.mm",
    "src/NppThemeManager.mm",
    "src/NppCommandLineParams.mm",
    "src/ShortcutMapperWindowController.mm",
    "src/NppLocalizer.mm",
    "src/NppLangsManager.mm",
    "src/AppDelegate.mm",
    "src/MainWindowController.mm",
    "src/EditorView.mm",
    "src/TabManager.mm",
    "src/NppTabBar.mm",
    "src/MenuBuilder.mm",
    "src/FindReplacePanel.mm",
    "src/ColumnEditorPanel.mm",
    "src/PreferencesWindowController.mm",
    "src/SidePanelHost.mm",
    "src/PanelFrame.mm",
    "src/FloatingPanelWindow.mm",
    "src/DocumentListPanel.mm",
    "src/ClipboardHistoryPanel.mm",
    "src/FunctionListPanel.mm",
    "src/DocumentMapPanel.mm",
    "src/ProjectPanel.mm",
    "src/SearchEngine.mm",
    "src/SearchResultsPanel.mm",
    "src/FindWindow.mm",
    "src/StyleConfiguratorWindowController.mm",
    "src/IncrementalSearchBar.mm",
    "src/CommandPalettePanel.mm",
    "src/GitHelper.mm",
    "src/GitPanel.mm",
    "src/FolderTreePanel.mm",
    "src/CharacterPanel.mm",
    "src/UserDefineLangManager.mm",
    "src/UserDefineDialog.mm",
    "src/UDLStylerDialog.mm",
    "src/NppPluginManager.mm",
    "src/PluginsAdminWindowController.mm",
]
app_mm = [os.path.join(ROOT, f) for f in app_mm]

# Resources
resource_files = [
    "resources/npp.icns",
    "resources/stylers.model.xml",
    "resources/langs.model.xml",
    "resources/shortcuts.xml",
    "resources/contextMenu.xml",
    "resources/tabContextMenu.xml",
    "resources/toolbarButtonsConf.xml",
    "resources/dmg-background.tiff",
]
resource_files = [os.path.join(ROOT, f) for f in resource_files]

# Folder references
resource_folders = [
    "resources/icons",
    "resources/themes",
    "resources/localization",
    "resources/functionList",
    "resources/userDefineLangs",
]
resource_folders = [os.path.join(ROOT, f) for f in resource_folders]

# en.lproj
en_lproj_file = os.path.join(ROOT, "resources/en.lproj/InfoPlist.strings")

# ---------------------------------------------------------------------------
# Build the PBX object graph
# ---------------------------------------------------------------------------

# We need:
# - PBXFileReference for every source/resource file
# - PBXBuildFile for each file in each target's build phases
# - PBXGroup hierarchy
# - PBXNativeTarget for scintilla, lexilla, app
# - PBXSourcesBuildPhase, PBXFrameworksBuildPhase, PBXResourcesBuildPhase
# - PBXShellScriptBuildPhase
# - PBXTargetDependency, PBXContainerItemProxy
# - XCBuildConfiguration, XCConfigurationList
# - PBXProject

objects = {}  # id -> dict (we'll serialize manually)

# File reference tracking
file_refs = {}  # path -> file_ref_id
build_files = {}  # (path, target_label) -> build_file_id

def file_type_for(path):
    ext = os.path.splitext(path)[1]
    types = {
        '.cxx': 'sourcecode.cpp.cpp',
        '.cpp': 'sourcecode.cpp.cpp',
        '.mm': 'sourcecode.cpp.objcpp',
        '.m': 'sourcecode.c.objc',
        '.h': 'sourcecode.c.h',
        '.swift': 'sourcecode.swift',
        '.xml': 'text.xml',
        '.icns': 'image.icns',
        '.tiff': 'image.tiff',
        '.strings': 'text.plist.strings',
        '.plist': 'text.plist.xml',
        '.a': 'archive.ar',
        '.framework': 'wrapper.framework',
        '.app': 'wrapper.application',
    }
    return types.get(ext, 'file')

def add_file_ref(path, source_tree="SOURCE_ROOT"):
    if path in file_refs:
        return file_refs[path]
    fid = uid(f"fileref:{path}")
    file_refs[path] = fid
    return fid

def add_build_file(file_ref_id, path, target_label, settings=None):
    key = (path, target_label)
    bid = uid(f"buildfile:{path}:{target_label}")
    build_files[key] = (bid, file_ref_id, settings)
    return bid

# ---------------------------------------------------------------------------
# Create file references for ALL source files
# ---------------------------------------------------------------------------

all_sci_files = sci_cxx + sci_mm
all_lex_files = lex_all
all_app_files = app_mm

for f in all_sci_files + all_lex_files + all_app_files + resource_files + resource_folders + [en_lproj_file]:
    add_file_ref(f)

# Framework references
frameworks = {
    "Cocoa.framework": ("wrapper.framework", "System/Library/Frameworks/Cocoa.framework"),
    "QuartzCore.framework": ("wrapper.framework", "System/Library/Frameworks/QuartzCore.framework"),
    "UniformTypeIdentifiers.framework": ("wrapper.framework", "System/Library/Frameworks/UniformTypeIdentifiers.framework"),
}
fw_refs = {}
for name, (ftype, path) in frameworks.items():
    fid = uid(f"fw:{name}")
    fw_refs[name] = fid

# Product references
prod_scintilla_id = uid("prod:libscintilla.a")
prod_lexilla_id = uid("prod:liblexilla.a")
prod_app_id = uid("prod:Notepad++.app")

# ---------------------------------------------------------------------------
# Build files for each target
# ---------------------------------------------------------------------------

# scintilla target
sci_build_file_ids = []
sci_mm_build_file_ids = []
for f in sci_cxx:
    bid = add_build_file(file_refs[f], f, "scintilla")
    sci_build_file_ids.append(bid)
for f in sci_mm:
    bid = add_build_file(file_refs[f], f, "scintilla", {"COMPILER_FLAGS": '"-fobjc-arc"'})
    sci_build_file_ids.append(bid)
    sci_mm_build_file_ids.append(bid)

# lexilla target
lex_build_file_ids = []
for f in all_lex_files:
    bid = add_build_file(file_refs[f], f, "lexilla")
    lex_build_file_ids.append(bid)

# app target - sources
app_build_file_ids = []
for f in all_app_files:
    bid = add_build_file(file_refs[f], f, "app", {"COMPILER_FLAGS": '"-fobjc-arc"'})
    app_build_file_ids.append(bid)

# app target - frameworks
app_fw_build_ids = {}
for name in frameworks:
    bid = uid(f"appfw:{name}")
    app_fw_build_ids[name] = bid

# app target - link with scintilla/lexilla
app_link_sci_id = uid("applink:scintilla")
app_link_lex_id = uid("applink:lexilla")

# app target - resources
app_res_build_ids = []
for f in resource_files:
    bid = uid(f"appres:{f}")
    app_res_build_ids.append((bid, file_refs[f]))

for f in resource_folders:
    bid = uid(f"appres:{f}")
    app_res_build_ids.append((bid, file_refs[f]))

en_lproj_build_id = uid("appres:en_lproj")
app_res_build_ids.append((en_lproj_build_id, file_refs[en_lproj_file]))

# ---------------------------------------------------------------------------
# Build phases
# ---------------------------------------------------------------------------

# Scintilla
sci_sources_phase_id = uid("phase:sci:sources")
sci_headers_phase_id = uid("phase:sci:headers")

# Lexilla
lex_sources_phase_id = uid("phase:lex:sources")
lex_headers_phase_id = uid("phase:lex:headers")

# App
app_sources_phase_id = uid("phase:app:sources")
app_frameworks_phase_id = uid("phase:app:frameworks")
app_resources_phase_id = uid("phase:app:resources")
app_script_phase_id = uid("phase:app:script")

# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------
target_sci_id = uid("target:scintilla")
target_lex_id = uid("target:lexilla")
target_app_id = uid("target:app")

# Target dependencies
dep_sci_id = uid("dep:sci")
dep_lex_id = uid("dep:lex")
proxy_sci_id = uid("proxy:sci")
proxy_lex_id = uid("proxy:lex")

# ---------------------------------------------------------------------------
# Build configurations
# ---------------------------------------------------------------------------
# Project-level
proj_debug_id = uid("config:proj:debug")
proj_release_id = uid("config:proj:release")
proj_configlist_id = uid("configlist:proj")

# Scintilla
sci_debug_id = uid("config:sci:debug")
sci_release_id = uid("config:sci:release")
sci_configlist_id = uid("configlist:sci")

# Lexilla
lex_debug_id = uid("config:lex:debug")
lex_release_id = uid("config:lex:release")
lex_configlist_id = uid("configlist:lex")

# App
app_debug_id = uid("config:app:debug")
app_release_id = uid("config:app:release")
app_configlist_id = uid("configlist:app")

# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------
main_group_id = uid("group:main")
sci_group_id = uid("group:scintilla")
sci_src_group_id = uid("group:scintilla:src")
sci_cocoa_group_id = uid("group:scintilla:cocoa")
lex_group_id = uid("group:lexilla")
lex_src_group_id = uid("group:lexilla:src")
lex_lexers_group_id = uid("group:lexilla:lexers")
lex_lexlib_group_id = uid("group:lexilla:lexlib")
app_group_id = uid("group:app")
res_group_id = uid("group:resources")
products_group_id = uid("group:products")
frameworks_group_id = uid("group:frameworks")

# Project
project_id = uid("project")

# ---------------------------------------------------------------------------
# Serialize
# ---------------------------------------------------------------------------

def quote(s):
    """Quote a string for pbxproj format."""
    if all(c.isalnum() or c in '._/' for c in s) and len(s) > 0:
        return s
    return f'"{s}"'

def pbx_list(items, indent=4):
    """Format a list of IDs."""
    pad = "\t" * indent
    lines = []
    for item in items:
        lines.append(f"{pad}{item} /* */,")
    return "\n".join(lines)

lines = []
def w(s=""):
    lines.append(s)

w("// !$*UTF8*$!")
w("{")
w("\tarchiveVersion = 1;")
w("\tclasses = {")
w("\t};")
w("\tobjectVersion = 56;")
w("\tobjects = {")
w("")

# --- PBXBuildFile ---
w("/* Begin PBXBuildFile section */")

# Scintilla build files
for f in sci_cxx:
    bid = build_files[(f, "scintilla")][0]
    name = os.path.basename(f)
    w(f"\t\t{bid} /* {name} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_refs[f]} /* {name} */; }};")
for f in sci_mm:
    bid, fref, settings = build_files[(f, "scintilla")]
    name = os.path.basename(f)
    w(f'\t\t{bid} /* {name} in Sources */ = {{isa = PBXBuildFile; fileRef = {fref} /* {name} */; settings = {{COMPILER_FLAGS = "-fobjc-arc"; }}; }};')

# Lexilla build files
for f in all_lex_files:
    bid = build_files[(f, "lexilla")][0]
    name = os.path.basename(f)
    w(f"\t\t{bid} /* {name} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_refs[f]} /* {name} */; }};")

# App source build files
for f in all_app_files:
    bid, fref, settings = build_files[(f, "app")]
    name = os.path.basename(f)
    w(f'\t\t{bid} /* {name} in Sources */ = {{isa = PBXBuildFile; fileRef = {fref} /* {name} */; settings = {{COMPILER_FLAGS = "-fobjc-arc"; }}; }};')

# App framework build files
for name, bid in app_fw_build_ids.items():
    w(f"\t\t{bid} /* {name} in Frameworks */ = {{isa = PBXBuildFile; fileRef = {fw_refs[name]} /* {name} */; }};")

# App link with static libs
w(f"\t\t{app_link_sci_id} /* libscintilla.a in Frameworks */ = {{isa = PBXBuildFile; fileRef = {prod_scintilla_id} /* libscintilla.a */; }};")
w(f"\t\t{app_link_lex_id} /* liblexilla.a in Frameworks */ = {{isa = PBXBuildFile; fileRef = {prod_lexilla_id} /* liblexilla.a */; }};")

# App resource build files
for bid, fref in app_res_build_ids:
    # Find the original path to get the name
    name = ""
    for path, ref_id in file_refs.items():
        if ref_id == fref:
            name = os.path.basename(path)
            break
    w(f"\t\t{bid} /* {name} in Resources */ = {{isa = PBXBuildFile; fileRef = {fref} /* {name} */; }};")

w("/* End PBXBuildFile section */")
w("")

# --- PBXContainerItemProxy ---
w("/* Begin PBXContainerItemProxy section */")
w(f"\t\t{proxy_sci_id} /* PBXContainerItemProxy */ = {{")
w(f"\t\t\tisa = PBXContainerItemProxy;")
w(f"\t\t\tcontainerPortal = {project_id} /* Project object */;")
w(f"\t\t\tproxyType = 1;")
w(f"\t\t\tremoteGlobalIDString = {target_sci_id};")
w(f'\t\t\tremoteInfo = scintilla;')
w(f"\t\t}};")
w(f"\t\t{proxy_lex_id} /* PBXContainerItemProxy */ = {{")
w(f"\t\t\tisa = PBXContainerItemProxy;")
w(f"\t\t\tcontainerPortal = {project_id} /* Project object */;")
w(f"\t\t\tproxyType = 1;")
w(f"\t\t\tremoteGlobalIDString = {target_lex_id};")
w(f'\t\t\tremoteInfo = lexilla;')
w(f"\t\t}};")
w("/* End PBXContainerItemProxy section */")
w("")

# --- PBXFileReference ---
w("/* Begin PBXFileReference section */")

# Source files
for path, fid in sorted(file_refs.items(), key=lambda x: x[0]):
    name = os.path.basename(path)
    rpath = os.path.relpath(path, ROOT)
    ftype = file_type_for(path)
    # Check if it's a folder reference
    if os.path.isdir(path):
        w(f'\t\t{fid} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = folder; name = {quote(name)}; path = {quote(rpath)}; sourceTree = SOURCE_ROOT; }};')
    else:
        w(f'\t\t{fid} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = {ftype}; name = {quote(name)}; path = {quote(rpath)}; sourceTree = SOURCE_ROOT; }};')

# Framework references
for name, (ftype, path) in frameworks.items():
    fid = fw_refs[name]
    w(f'\t\t{fid} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = {ftype}; name = {quote(name)}; path = {quote(path)}; sourceTree = SDKROOT; }};')

# Products
w(f'\t\t{prod_scintilla_id} /* libscintilla.a */ = {{isa = PBXFileReference; explicitFileType = archive.ar; includeInIndex = 0; path = libscintilla.a; sourceTree = BUILT_PRODUCTS_DIR; }};')
w(f'\t\t{prod_lexilla_id} /* liblexilla.a */ = {{isa = PBXFileReference; explicitFileType = archive.ar; includeInIndex = 0; path = liblexilla.a; sourceTree = BUILT_PRODUCTS_DIR; }};')
w(f'\t\t{prod_app_id} /* Notepad++.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = "Notepad++.app"; sourceTree = BUILT_PRODUCTS_DIR; }};')

w("/* End PBXFileReference section */")
w("")

# --- PBXFrameworksBuildPhase ---
w("/* Begin PBXFrameworksBuildPhase section */")

# Scintilla has no frameworks phase needed but we include an empty one
sci_fw_phase_id = uid("phase:sci:fw")
w(f"\t\t{sci_fw_phase_id} /* Frameworks */ = {{")
w(f"\t\t\tisa = PBXFrameworksBuildPhase;")
w(f"\t\t\tbuildActionMask = 2147483647;")
w(f"\t\t\tfiles = (")
w(f"\t\t\t);")
w(f"\t\t\trunOnlyForDeploymentPostprocessing = 0;")
w(f"\t\t}};")

lex_fw_phase_id = uid("phase:lex:fw")
w(f"\t\t{lex_fw_phase_id} /* Frameworks */ = {{")
w(f"\t\t\tisa = PBXFrameworksBuildPhase;")
w(f"\t\t\tbuildActionMask = 2147483647;")
w(f"\t\t\tfiles = (")
w(f"\t\t\t);")
w(f"\t\t\trunOnlyForDeploymentPostprocessing = 0;")
w(f"\t\t}};")

w(f"\t\t{app_frameworks_phase_id} /* Frameworks */ = {{")
w(f"\t\t\tisa = PBXFrameworksBuildPhase;")
w(f"\t\t\tbuildActionMask = 2147483647;")
w(f"\t\t\tfiles = (")
w(f"\t\t\t\t{app_link_sci_id} /* libscintilla.a in Frameworks */,")
w(f"\t\t\t\t{app_link_lex_id} /* liblexilla.a in Frameworks */,")
for name, bid in app_fw_build_ids.items():
    w(f"\t\t\t\t{bid} /* {name} in Frameworks */,")
w(f"\t\t\t);")
w(f"\t\t\trunOnlyForDeploymentPostprocessing = 0;")
w(f"\t\t}};")

w("/* End PBXFrameworksBuildPhase section */")
w("")

# --- PBXGroup ---
w("/* Begin PBXGroup section */")

# Main group
w(f"\t\t{main_group_id} /* */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
w(f"\t\t\t\t{sci_group_id} /* scintilla */,")
w(f"\t\t\t\t{lex_group_id} /* lexilla */,")
w(f"\t\t\t\t{app_group_id} /* src */,")
w(f"\t\t\t\t{res_group_id} /* resources */,")
w(f"\t\t\t\t{frameworks_group_id} /* Frameworks */,")
w(f"\t\t\t\t{products_group_id} /* Products */,")
w(f"\t\t\t);")
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# Scintilla group
w(f"\t\t{sci_group_id} /* scintilla */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
w(f"\t\t\t\t{sci_src_group_id} /* src */,")
w(f"\t\t\t\t{sci_cocoa_group_id} /* cocoa */,")
w(f"\t\t\t);")
w(f'\t\t\tname = scintilla;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# scintilla/src
w(f"\t\t{sci_src_group_id} /* src */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
for f in sci_cxx:
    w(f"\t\t\t\t{file_refs[f]} /* {os.path.basename(f)} */,")
w(f"\t\t\t);")
w(f'\t\t\tname = src;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# scintilla/cocoa
w(f"\t\t{sci_cocoa_group_id} /* cocoa */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
for f in sci_mm:
    w(f"\t\t\t\t{file_refs[f]} /* {os.path.basename(f)} */,")
w(f"\t\t\t);")
w(f'\t\t\tname = cocoa;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# Lexilla group
w(f"\t\t{lex_group_id} /* lexilla */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
w(f"\t\t\t\t{lex_src_group_id} /* src */,")
w(f"\t\t\t\t{lex_lexers_group_id} /* lexers */,")
w(f"\t\t\t\t{lex_lexlib_group_id} /* lexlib */,")
w(f"\t\t\t);")
w(f'\t\t\tname = lexilla;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# lexilla/src
w(f"\t\t{lex_src_group_id} /* src */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
for f in lex_src:
    w(f"\t\t\t\t{file_refs[f]} /* {os.path.basename(f)} */,")
w(f"\t\t\t);")
w(f'\t\t\tname = src;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# lexilla/lexers (include src/LexUser.cxx here too)
w(f"\t\t{lex_lexers_group_id} /* lexers */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
for f in lex_lexers + lex_custom:
    w(f"\t\t\t\t{file_refs[f]} /* {os.path.basename(f)} */,")
w(f"\t\t\t);")
w(f'\t\t\tname = lexers;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# lexilla/lexlib
w(f"\t\t{lex_lexlib_group_id} /* lexlib */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
for f in lex_lexlib:
    w(f"\t\t\t\t{file_refs[f]} /* {os.path.basename(f)} */,")
w(f"\t\t\t);")
w(f'\t\t\tname = lexlib;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# App group
w(f"\t\t{app_group_id} /* src */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
for f in all_app_files:
    w(f"\t\t\t\t{file_refs[f]} /* {os.path.basename(f)} */,")
w(f"\t\t\t);")
w(f'\t\t\tname = src;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# Resources group
w(f"\t\t{res_group_id} /* resources */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
for f in resource_files:
    w(f"\t\t\t\t{file_refs[f]} /* {os.path.basename(f)} */,")
for f in resource_folders:
    w(f"\t\t\t\t{file_refs[f]} /* {os.path.basename(f)} */,")
w(f"\t\t\t\t{file_refs[en_lproj_file]} /* InfoPlist.strings */,")
w(f"\t\t\t);")
w(f'\t\t\tname = resources;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# Products group
w(f"\t\t{products_group_id} /* Products */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
w(f"\t\t\t\t{prod_scintilla_id} /* libscintilla.a */,")
w(f"\t\t\t\t{prod_lexilla_id} /* liblexilla.a */,")
w(f"\t\t\t\t{prod_app_id} /* Notepad++.app */,")
w(f"\t\t\t);")
w(f'\t\t\tname = Products;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

# Frameworks group
w(f"\t\t{frameworks_group_id} /* Frameworks */ = {{")
w(f"\t\t\tisa = PBXGroup;")
w(f"\t\t\tchildren = (")
for name in frameworks:
    w(f"\t\t\t\t{fw_refs[name]} /* {name} */,")
w(f"\t\t\t);")
w(f'\t\t\tname = Frameworks;')
w(f"\t\t\tsourceTree = \"<group>\";")
w(f"\t\t}};")

w("/* End PBXGroup section */")
w("")

# --- PBXNativeTarget ---
w("/* Begin PBXNativeTarget section */")

# scintilla target
w(f"\t\t{target_sci_id} /* scintilla */ = {{")
w(f"\t\t\tisa = PBXNativeTarget;")
w(f"\t\t\tbuildConfigurationList = {sci_configlist_id} /* Build configuration list for PBXNativeTarget \"scintilla\" */;")
w(f'\t\t\tbuildPhases = (')
w(f"\t\t\t\t{sci_sources_phase_id} /* Sources */,")
w(f"\t\t\t\t{sci_fw_phase_id} /* Frameworks */,")
w(f"\t\t\t);")
w(f"\t\t\tbuildRules = (")
w(f"\t\t\t);")
w(f"\t\t\tdependencies = (")
w(f"\t\t\t);")
w(f'\t\t\tname = scintilla;')
w(f"\t\t\tproductName = scintilla;")
w(f"\t\t\tproductReference = {prod_scintilla_id} /* libscintilla.a */;")
w(f'\t\t\tproductType = "com.apple.product-type.library.static";')
w(f"\t\t}};")

# lexilla target
w(f"\t\t{target_lex_id} /* lexilla */ = {{")
w(f"\t\t\tisa = PBXNativeTarget;")
w(f"\t\t\tbuildConfigurationList = {lex_configlist_id} /* Build configuration list for PBXNativeTarget \"lexilla\" */;")
w(f'\t\t\tbuildPhases = (')
w(f"\t\t\t\t{lex_sources_phase_id} /* Sources */,")
w(f"\t\t\t\t{lex_fw_phase_id} /* Frameworks */,")
w(f"\t\t\t);")
w(f"\t\t\tbuildRules = (")
w(f"\t\t\t);")
w(f"\t\t\tdependencies = (")
w(f"\t\t\t);")
w(f'\t\t\tname = lexilla;')
w(f"\t\t\tproductName = lexilla;")
w(f"\t\t\tproductReference = {prod_lexilla_id} /* liblexilla.a */;")
w(f'\t\t\tproductType = "com.apple.product-type.library.static";')
w(f"\t\t}};")

# app target
w(f"\t\t{target_app_id} /* NotepadPlusPlusMac */ = {{")
w(f"\t\t\tisa = PBXNativeTarget;")
w(f"\t\t\tbuildConfigurationList = {app_configlist_id} /* Build configuration list for PBXNativeTarget \"NotepadPlusPlusMac\" */;")
w(f'\t\t\tbuildPhases = (')
w(f"\t\t\t\t{app_sources_phase_id} /* Sources */,")
w(f"\t\t\t\t{app_frameworks_phase_id} /* Frameworks */,")
w(f"\t\t\t\t{app_resources_phase_id} /* Resources */,")
w(f"\t\t\t\t{app_script_phase_id} /* ShellScript */,")
w(f"\t\t\t);")
w(f"\t\t\tbuildRules = (")
w(f"\t\t\t);")
w(f"\t\t\tdependencies = (")
w(f"\t\t\t\t{dep_sci_id} /* PBXTargetDependency */,")
w(f"\t\t\t\t{dep_lex_id} /* PBXTargetDependency */,")
w(f"\t\t\t);")
w(f'\t\t\tname = NotepadPlusPlusMac;')
w(f"\t\t\tproductName = NotepadPlusPlusMac;")
w(f"\t\t\tproductReference = {prod_app_id} /* Notepad++.app */;")
w(f'\t\t\tproductType = "com.apple.product-type.application";')
w(f"\t\t}};")

w("/* End PBXNativeTarget section */")
w("")

# --- PBXProject ---
w("/* Begin PBXProject section */")
w(f"\t\t{project_id} /* Project object */ = {{")
w(f"\t\t\tisa = PBXProject;")
w(f"\t\t\tbuildConfigurationList = {proj_configlist_id} /* Build configuration list for PBXProject */;")
w(f'\t\t\tcompatibilityVersion = "Xcode 14.0";')
w(f"\t\t\tdevelopmentRegion = en;")
w(f"\t\t\thasScannedForEncodings = 0;")
w(f"\t\t\tknownRegions = (")
w(f"\t\t\t\ten,")
w(f"\t\t\t\tBase,")
w(f"\t\t\t);")
w(f"\t\t\tmainGroup = {main_group_id} /* */;")
w(f"\t\t\tproductRefGroup = {products_group_id} /* Products */;")
w(f'\t\t\tprojectDirPath = "";')
w(f'\t\t\tprojectRoot = "";')
w(f"\t\t\ttargets = (")
w(f"\t\t\t\t{target_sci_id} /* scintilla */,")
w(f"\t\t\t\t{target_lex_id} /* lexilla */,")
w(f"\t\t\t\t{target_app_id} /* NotepadPlusPlusMac */,")
w(f"\t\t\t);")
w(f"\t\t}};")
w("/* End PBXProject section */")
w("")

# --- PBXResourcesBuildPhase ---
w("/* Begin PBXResourcesBuildPhase section */")
w(f"\t\t{app_resources_phase_id} /* Resources */ = {{")
w(f"\t\t\tisa = PBXResourcesBuildPhase;")
w(f"\t\t\tbuildActionMask = 2147483647;")
w(f"\t\t\tfiles = (")
for bid, fref in app_res_build_ids:
    name = ""
    for path, ref_id in file_refs.items():
        if ref_id == fref:
            name = os.path.basename(path)
            break
    w(f"\t\t\t\t{bid} /* {name} in Resources */,")
w(f"\t\t\t);")
w(f"\t\t\trunOnlyForDeploymentPostprocessing = 0;")
w(f"\t\t}};")
w("/* End PBXResourcesBuildPhase section */")
w("")

# --- PBXShellScriptBuildPhase ---
w("/* Begin PBXShellScriptBuildPhase section */")
w(f"\t\t{app_script_phase_id} /* ShellScript */ = {{")
w(f"\t\t\tisa = PBXShellScriptBuildPhase;")
w(f"\t\t\tbuildActionMask = 2147483647;")
w(f"\t\t\tfiles = (")
w(f"\t\t\t);")
w(f"\t\t\tinputFileListPaths = (")
w(f"\t\t\t);")
w(f"\t\t\tinputPaths = (")
w(f"\t\t\t);")
w(f"\t\t\toutputFileListPaths = (")
w(f"\t\t\t);")
w(f"\t\t\toutputPaths = (")
w(f"\t\t\t);")
w(f"\t\t\trunOnlyForDeploymentPostprocessing = 0;")
w(f'\t\t\tshellPath = /bin/sh;')
w(f'\t\t\tshellScript = "xattr -cr \\"$BUILT_PRODUCTS_DIR/$WRAPPER_NAME\\"\\ncodesign --force --deep --sign - \\"$BUILT_PRODUCTS_DIR/$WRAPPER_NAME\\"\\n";')
w(f"\t\t}};")
w("/* End PBXShellScriptBuildPhase section */")
w("")

# --- PBXSourcesBuildPhase ---
w("/* Begin PBXSourcesBuildPhase section */")

# Scintilla sources
w(f"\t\t{sci_sources_phase_id} /* Sources */ = {{")
w(f"\t\t\tisa = PBXSourcesBuildPhase;")
w(f"\t\t\tbuildActionMask = 2147483647;")
w(f"\t\t\tfiles = (")
for f in sci_cxx:
    bid = build_files[(f, "scintilla")][0]
    w(f"\t\t\t\t{bid} /* {os.path.basename(f)} in Sources */,")
for f in sci_mm:
    bid = build_files[(f, "scintilla")][0]
    w(f"\t\t\t\t{bid} /* {os.path.basename(f)} in Sources */,")
w(f"\t\t\t);")
w(f"\t\t\trunOnlyForDeploymentPostprocessing = 0;")
w(f"\t\t}};")

# Lexilla sources
w(f"\t\t{lex_sources_phase_id} /* Sources */ = {{")
w(f"\t\t\tisa = PBXSourcesBuildPhase;")
w(f"\t\t\tbuildActionMask = 2147483647;")
w(f"\t\t\tfiles = (")
for f in all_lex_files:
    bid = build_files[(f, "lexilla")][0]
    w(f"\t\t\t\t{bid} /* {os.path.basename(f)} in Sources */,")
w(f"\t\t\t);")
w(f"\t\t\trunOnlyForDeploymentPostprocessing = 0;")
w(f"\t\t}};")

# App sources
w(f"\t\t{app_sources_phase_id} /* Sources */ = {{")
w(f"\t\t\tisa = PBXSourcesBuildPhase;")
w(f"\t\t\tbuildActionMask = 2147483647;")
w(f"\t\t\tfiles = (")
for f in all_app_files:
    bid = build_files[(f, "app")][0]
    w(f"\t\t\t\t{bid} /* {os.path.basename(f)} in Sources */,")
w(f"\t\t\t);")
w(f"\t\t\trunOnlyForDeploymentPostprocessing = 0;")
w(f"\t\t}};")

w("/* End PBXSourcesBuildPhase section */")
w("")

# --- PBXTargetDependency ---
w("/* Begin PBXTargetDependency section */")
w(f"\t\t{dep_sci_id} /* PBXTargetDependency */ = {{")
w(f"\t\t\tisa = PBXTargetDependency;")
w(f"\t\t\ttarget = {target_sci_id} /* scintilla */;")
w(f"\t\t\ttargetProxy = {proxy_sci_id} /* PBXContainerItemProxy */;")
w(f"\t\t}};")
w(f"\t\t{dep_lex_id} /* PBXTargetDependency */ = {{")
w(f"\t\t\tisa = PBXTargetDependency;")
w(f"\t\t\ttarget = {target_lex_id} /* lexilla */;")
w(f"\t\t\ttargetProxy = {proxy_lex_id} /* PBXContainerItemProxy */;")
w(f"\t\t}};")
w("/* End PBXTargetDependency section */")
w("")

# --- XCBuildConfiguration ---
w("/* Begin XCBuildConfiguration section */")

# Project-level Debug
w(f"\t\t{proj_debug_id} /* Debug */ = {{")
w(f"\t\t\tisa = XCBuildConfiguration;")
w(f"\t\t\tbuildSettings = {{")
w(f"\t\t\t\tALWAYS_SEARCH_USER_PATHS = NO;")
w(f'\t\t\t\tCLANG_CXX_LANGUAGE_STANDARD = "gnu++17";')
w(f"\t\t\t\tCLANG_ENABLE_MODULES = YES;")
w(f"\t\t\t\tCLANG_ENABLE_OBJC_ARC = NO;")
w(f"\t\t\t\tCOPY_PHASE_STRIP = NO;")
w(f"\t\t\t\tDEBUG_INFORMATION_FORMAT = dwarf;")
w(f"\t\t\t\tENABLE_STRICT_OBJC_MSGSEND = YES;")
w(f"\t\t\t\tENABLE_TESTABILITY = YES;")
w(f"\t\t\t\tGCC_DYNAMIC_NO_PIC = NO;")
w(f"\t\t\t\tGCC_NO_COMMON_BLOCKS = YES;")
w(f"\t\t\t\tGCC_OPTIMIZATION_LEVEL = 0;")
w(f'\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = (')
w(f'\t\t\t\t\t"DEBUG=1",')
w(f'\t\t\t\t\t"$(inherited)",')
w(f'\t\t\t\t);')
w(f"\t\t\t\tGCC_WARN_64_TO_32_BIT_CONVERSION = YES;")
w(f"\t\t\t\tGCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR;")
w(f"\t\t\t\tGCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;")
w(f"\t\t\t\tGCC_WARN_UNUSED_FUNCTION = YES;")
w(f"\t\t\t\tGCC_WARN_UNUSED_VARIABLE = YES;")
w(f'\t\t\t\tMACOSX_DEPLOYMENT_TARGET = 11.0;')
w(f"\t\t\t\tMTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;")
w(f"\t\t\t\tMTL_FAST_MATH = YES;")
w(f"\t\t\t\tONLY_ACTIVE_ARCH = YES;")
w(f'\t\t\t\tSDKROOT = macosx;')
w(f"\t\t\t}};")
w(f'\t\t\tname = Debug;')
w(f"\t\t}};")

# Project-level Release
w(f"\t\t{proj_release_id} /* Release */ = {{")
w(f"\t\t\tisa = XCBuildConfiguration;")
w(f"\t\t\tbuildSettings = {{")
w(f"\t\t\t\tALWAYS_SEARCH_USER_PATHS = NO;")
w(f'\t\t\t\tCLANG_CXX_LANGUAGE_STANDARD = "gnu++17";')
w(f"\t\t\t\tCLANG_ENABLE_MODULES = YES;")
w(f"\t\t\t\tCLANG_ENABLE_OBJC_ARC = NO;")
w(f"\t\t\t\tCOPY_PHASE_STRIP = NO;")
w(f'\t\t\t\tDEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";')
w(f"\t\t\t\tENABLE_NS_ASSERTIONS = NO;")
w(f"\t\t\t\tENABLE_STRICT_OBJC_MSGSEND = YES;")
w(f"\t\t\t\tGCC_NO_COMMON_BLOCKS = YES;")
w(f"\t\t\t\tGCC_WARN_64_TO_32_BIT_CONVERSION = YES;")
w(f"\t\t\t\tGCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR;")
w(f"\t\t\t\tGCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;")
w(f"\t\t\t\tGCC_WARN_UNUSED_FUNCTION = YES;")
w(f"\t\t\t\tGCC_WARN_UNUSED_VARIABLE = YES;")
w(f'\t\t\t\tMACOSX_DEPLOYMENT_TARGET = 11.0;')
w(f"\t\t\t\tMTL_FAST_MATH = YES;")
w(f'\t\t\t\tSDKROOT = macosx;')
w(f"\t\t\t}};")
w(f'\t\t\tname = Release;')
w(f"\t\t}};")

# Scintilla Debug
w(f"\t\t{sci_debug_id} /* Debug */ = {{")
w(f"\t\t\tisa = XCBuildConfiguration;")
w(f"\t\t\tbuildSettings = {{")
w(f'\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = (')
w(f'\t\t\t\t\t"SCI_NAMESPACE=1",')
w(f'\t\t\t\t\t"SCINTILLA_QT=0",')
w(f'\t\t\t\t\t"DEBUG=1",')
w(f'\t\t\t\t\t"$(inherited)",')
w(f'\t\t\t\t);')
w(f"\t\t\t\tHEADER_SEARCH_PATHS = (")
w(f'\t\t\t\t\tscintilla/include,')
w(f'\t\t\t\t\tscintilla/src,')
w(f'\t\t\t\t\tscintilla/cocoa,')
w(f"\t\t\t\t);")
w(f"\t\t\t\tOTHER_LDFLAGS = \"-ObjC\";")
w(f'\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";')
w(f"\t\t\t\tSKIP_INSTALL = YES;")
w(f"\t\t\t}};")
w(f'\t\t\tname = Debug;')
w(f"\t\t}};")

# Scintilla Release
w(f"\t\t{sci_release_id} /* Release */ = {{")
w(f"\t\t\tisa = XCBuildConfiguration;")
w(f"\t\t\tbuildSettings = {{")
w(f'\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = (')
w(f'\t\t\t\t\t"SCI_NAMESPACE=1",')
w(f'\t\t\t\t\t"SCINTILLA_QT=0",')
w(f'\t\t\t\t\t"$(inherited)",')
w(f'\t\t\t\t);')
w(f"\t\t\t\tHEADER_SEARCH_PATHS = (")
w(f'\t\t\t\t\tscintilla/include,')
w(f'\t\t\t\t\tscintilla/src,')
w(f'\t\t\t\t\tscintilla/cocoa,')
w(f"\t\t\t\t);")
w(f"\t\t\t\tOTHER_LDFLAGS = \"-ObjC\";")
w(f'\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";')
w(f"\t\t\t\tSKIP_INSTALL = YES;")
w(f"\t\t\t}};")
w(f'\t\t\tname = Release;')
w(f"\t\t}};")

# Lexilla Debug
w(f"\t\t{lex_debug_id} /* Debug */ = {{")
w(f"\t\t\tisa = XCBuildConfiguration;")
w(f"\t\t\tbuildSettings = {{")
w(f"\t\t\t\tHEADER_SEARCH_PATHS = (")
w(f'\t\t\t\t\tlexilla/include,')
w(f'\t\t\t\t\tlexilla/src,')
w(f'\t\t\t\t\tlexilla/lexlib,')
w(f'\t\t\t\t\tlexilla/access,')
w(f'\t\t\t\t\tscintilla/include,')
w(f'\t\t\t\t\tscintilla/src,')
w(f'\t\t\t\t\tsrc,')
w(f"\t\t\t\t);")
w(f'\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";')
w(f"\t\t\t\tSKIP_INSTALL = YES;")
w(f"\t\t\t}};")
w(f'\t\t\tname = Debug;')
w(f"\t\t}};")

# Lexilla Release
w(f"\t\t{lex_release_id} /* Release */ = {{")
w(f"\t\t\tisa = XCBuildConfiguration;")
w(f"\t\t\tbuildSettings = {{")
w(f"\t\t\t\tHEADER_SEARCH_PATHS = (")
w(f'\t\t\t\t\tlexilla/include,')
w(f'\t\t\t\t\tlexilla/src,')
w(f'\t\t\t\t\tlexilla/lexlib,')
w(f'\t\t\t\t\tlexilla/access,')
w(f'\t\t\t\t\tscintilla/include,')
w(f'\t\t\t\t\tscintilla/src,')
w(f'\t\t\t\t\tsrc,')
w(f"\t\t\t\t);")
w(f'\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";')
w(f"\t\t\t\tSKIP_INSTALL = YES;")
w(f"\t\t\t}};")
w(f'\t\t\tname = Release;')
w(f"\t\t}};")

# App Debug
w(f"\t\t{app_debug_id} /* Debug */ = {{")
w(f"\t\t\tisa = XCBuildConfiguration;")
w(f"\t\t\tbuildSettings = {{")
w(f"\t\t\t\tARCHS = \"$(ARCHS_STANDARD)\";")
w(f"\t\t\t\tCLANG_ENABLE_OBJC_ARC = NO;")
w(f"\t\t\t\tCOMBINE_HIDPI_IMAGES = YES;")
w(f"\t\t\t\tHEADER_SEARCH_PATHS = (")
w(f'\t\t\t\t\tsrc,')
w(f'\t\t\t\t\tscintilla/include,')
w(f'\t\t\t\t\tscintilla/cocoa,')
w(f'\t\t\t\t\tlexilla/include,')
w(f"\t\t\t\t);")
w(f'\t\t\t\tINFOPLIST_FILE = resources/Info.plist;')
w(f"\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (")
w(f'\t\t\t\t\t"$(inherited)",')
w(f'\t\t\t\t\t"@executable_path/../Frameworks",')
w(f"\t\t\t\t);")
w(f'\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = org.notepadplusplus.mac;')
w(f'\t\t\t\tPRODUCT_NAME = "Notepad++";')
w(f'\t\t\t\tMARKETING_VERSION = 1.0.5;')
w(f'\t\t\t\tCURRENT_PROJECT_VERSION = 1.0.5;')
w(f"\t\t\t}};")
w(f'\t\t\tname = Debug;')
w(f"\t\t}};")

# App Release
w(f"\t\t{app_release_id} /* Release */ = {{")
w(f"\t\t\tisa = XCBuildConfiguration;")
w(f"\t\t\tbuildSettings = {{")
w(f"\t\t\t\tARCHS = \"$(ARCHS_STANDARD)\";")
w(f"\t\t\t\tCLANG_ENABLE_OBJC_ARC = NO;")
w(f"\t\t\t\tCOMBINE_HIDPI_IMAGES = YES;")
w(f"\t\t\t\tHEADER_SEARCH_PATHS = (")
w(f'\t\t\t\t\tsrc,')
w(f'\t\t\t\t\tscintilla/include,')
w(f'\t\t\t\t\tscintilla/cocoa,')
w(f'\t\t\t\t\tlexilla/include,')
w(f"\t\t\t\t);")
w(f'\t\t\t\tINFOPLIST_FILE = resources/Info.plist;')
w(f"\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (")
w(f'\t\t\t\t\t"$(inherited)",')
w(f'\t\t\t\t\t"@executable_path/../Frameworks",')
w(f"\t\t\t\t);")
w(f'\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = org.notepadplusplus.mac;')
w(f'\t\t\t\tPRODUCT_NAME = "Notepad++";')
w(f'\t\t\t\tMARKETING_VERSION = 1.0.5;')
w(f'\t\t\t\tCURRENT_PROJECT_VERSION = 1.0.5;')
w(f"\t\t\t}};")
w(f'\t\t\tname = Release;')
w(f"\t\t}};")

w("/* End XCBuildConfiguration section */")
w("")

# --- XCConfigurationList ---
w("/* Begin XCConfigurationList section */")

w(f"\t\t{proj_configlist_id} /* Build configuration list for PBXProject */ = {{")
w(f"\t\t\tisa = XCConfigurationList;")
w(f"\t\t\tbuildConfigurations = (")
w(f"\t\t\t\t{proj_debug_id} /* Debug */,")
w(f"\t\t\t\t{proj_release_id} /* Release */,")
w(f"\t\t\t);")
w(f"\t\t\tdefaultConfigurationIsVisible = 0;")
w(f'\t\t\tdefaultConfigurationName = Release;')
w(f"\t\t}};")

w(f"\t\t{sci_configlist_id} /* Build configuration list for PBXNativeTarget \"scintilla\" */ = {{")
w(f"\t\t\tisa = XCConfigurationList;")
w(f"\t\t\tbuildConfigurations = (")
w(f"\t\t\t\t{sci_debug_id} /* Debug */,")
w(f"\t\t\t\t{sci_release_id} /* Release */,")
w(f"\t\t\t);")
w(f"\t\t\tdefaultConfigurationIsVisible = 0;")
w(f'\t\t\tdefaultConfigurationName = Release;')
w(f"\t\t}};")

w(f"\t\t{lex_configlist_id} /* Build configuration list for PBXNativeTarget \"lexilla\" */ = {{")
w(f"\t\t\tisa = XCConfigurationList;")
w(f"\t\t\tbuildConfigurations = (")
w(f"\t\t\t\t{lex_debug_id} /* Debug */,")
w(f"\t\t\t\t{lex_release_id} /* Release */,")
w(f"\t\t\t);")
w(f"\t\t\tdefaultConfigurationIsVisible = 0;")
w(f'\t\t\tdefaultConfigurationName = Release;')
w(f"\t\t}};")

w(f"\t\t{app_configlist_id} /* Build configuration list for PBXNativeTarget \"NotepadPlusPlusMac\" */ = {{")
w(f"\t\t\tisa = XCConfigurationList;")
w(f"\t\t\tbuildConfigurations = (")
w(f"\t\t\t\t{app_debug_id} /* Debug */,")
w(f"\t\t\t\t{app_release_id} /* Release */,")
w(f"\t\t\t);")
w(f"\t\t\tdefaultConfigurationIsVisible = 0;")
w(f'\t\t\tdefaultConfigurationName = Release;')
w(f"\t\t}};")

w("/* End XCConfigurationList section */")
w("")

w("\t};")
w(f"\trootObject = {project_id} /* Project object */;")
w("}")

# ---------------------------------------------------------------------------
# Write the .xcodeproj
# ---------------------------------------------------------------------------
proj_dir = os.path.join(ROOT, "NotepadPlusPlusMac.xcodeproj")
os.makedirs(proj_dir, exist_ok=True)

pbxproj_path = os.path.join(proj_dir, "project.pbxproj")
with open(pbxproj_path, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated {pbxproj_path}")
print(f"  Scintilla sources: {len(sci_cxx)} .cxx + {len(sci_mm)} .mm = {len(sci_cxx) + len(sci_mm)} files")
print(f"  Lexilla sources: {len(all_lex_files)} files")
print(f"  App sources: {len(all_app_files)} files")
print(f"  Resources: {len(resource_files)} files + {len(resource_folders)} folders + en.lproj")

"""
MayaUIChanger Drag-and-Drop Installer

This script allows users to install the MayaUIChanger tool by simply dragging and dropping
this file into the Maya viewport.
"""

import os
import sys
import shutil
import maya.cmds as cmds
import maya.mel as mel

def onMayaDroppedPythonFile(*args):
    """
    This function is automatically called by Maya when this file is dropped into the viewport.
    """
    install()

def install():
    """
    Main installation logic.
    """
    # 1. Determine Paths
    source_file = os.path.abspath(__file__)
    source_dir = os.path.dirname(source_file)
    project_name = "MayaUIChanger"
    
    # Maya scripts directory
    user_script_dir = cmds.internalVar(userScriptDir=True)
    # Ensure no trailing slashes or mixed slashes
    user_script_dir = os.path.normpath(user_script_dir)

    target_dir = os.path.join(user_script_dir, project_name)
    target_usersetup = os.path.join(user_script_dir, "userSetup.py")

    # 2. Copy the Project Folder
    print(f"Installing {project_name} to: {target_dir}")
    
    # Remove existing installation if it exists
    if os.path.exists(target_dir):
        try:
            shutil.rmtree(target_dir)
            print("Removed existing installation.")
        except Exception as e:
            cmds.warning(f"Failed to remove existing installation: {e}")
            return

    # Copy new files
    try:
        # We want to copy everything in the source_dir EXCLUDING this install.py and maybe .git
        # But simplify: Copy the whole source_dir to target_dir, then remove install.py from target
        
        # shutil.copytree requires target dir to NOT exist (we deleted it above)
        # ignore_patterns = shutil.ignore_patterns('*.pyc', '__pycache__', '.git', '.github', '.gitignore', 'install.py')
        
        # Manually copying relevant files might be safer to avoid copying the parent dir itself if source_dir IS the repo root
        # If I drag install.py from D:\Project\MayaUIChanger\install.py
        # source_dir is D:\Project\MayaUIChanger
        # I want to copy D:\Project\MayaUIChanger -> .../scripts/MayaUIChanger
        
        shutil.copytree(source_dir, target_dir, ignore=shutil.ignore_patterns('*.pyc', '__pycache__', '.git', '.github', '.gitignore', 'install.py', 'README.md'))
        print("Files copied successfully.")

    except Exception as e:
        cmds.error(f"Installation failed during file copy: {e}")
        return

    # 3. Setup userSetup.py
    setup_code = """
# ---------------- MayaUIChanger Setup ----------------
import maya.utils

def loadUIPresetLoader():
    try:
        import MayaUIChanger.UIPresetLoader as UIPresetLoader
        UIPresetLoader.run()
    except Exception as e:
        print(f"MayaUIChanger: Error loading UI Preset Loader: {e}")

def playStartupSound():
    try:
        import MayaUIChanger.SplashLoader as splashloader
        # SplashLoader automatically plays sound on import/execution if configured
        # But let's check if we need to explicitly trigger anything or just let it run
        pass 
    except Exception as e:
        print(f"MayaUIChanger: Error loading Splash Loader: {e}")

maya.utils.executeDeferred(loadUIPresetLoader)
# SplashLoader runs on import in the original script, so just importing it might be enough if added to sys.modules
# However, let's keep it safe. The original userSetup.py had a bug calling play_custom_sound
# We will just rely on the module import side-effects or check SplashLoader implementation.
# In the analyzed SplashLoader.py:
# It calls run() or main block automatically? 
# It has `if audio_file: ... executeDeferred(play_startup_sound_once)` at top level.
# So simply importing it is sufficient.

try:
    import MayaUIChanger.SplashLoader
except ImportError:
    pass

# ---------------- End MayaUIChanger Setup ----------------
"""
    
    # Clean up the setup code logic based on analysis
    # The original userSetup.py had broken logic. We will replace it with a robust version.
    
    robust_setup_code = """
# -- MayaUIChanger Start --
import maya.utils

def mui_startup():
    try:
        import MayaUIChanger.UIPresetLoader as UIPresetLoader
        UIPresetLoader.run()
    except Exception as e:
        print(f"MayaUIChanger Error: {e}")
        
    try:
        import MayaUIChanger.SplashLoader
    except Exception as e:
        print(f"MayaUIChanger Splash Error: {e}")

maya.utils.executeDeferred(mui_startup)
# -- MayaUIChanger End --
"""

    if os.path.exists(target_usersetup):
        # Read existing to see if we already installed
        with open(target_usersetup, 'r') as f:
            content = f.read()
        
        if "MayaUIChanger" in content:
            print("userSetup.py already contains MayaUIChanger setup. Skipping append.")
        else:
            print("Appending to userSetup.py...")
            with open(target_usersetup, 'a') as f:
                f.write("\n" + robust_setup_code)
    else:
        print("Creating userSetup.py...")
        with open(target_usersetup, 'w') as f:
            f.write(robust_setup_code)

    # 4. Success Message
    cmds.confirmDialog(
        title="Installation Complete",
        message=f"MayaUIChanger has been successfully installed to:\n{target_dir}\n\nPlease restart Maya for changes to take effect.",
        button=["OK"]
    )

if __name__ == "__main__":
    # Allow manual running for testing if not dropped
    try:
        install()
    except Exception as e:
        print(f"Manual install execution: {e}")
